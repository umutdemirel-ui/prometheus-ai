"""FastAPI + WebSocket backend server for Prometheus AI HUD."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from prometheus import __version__
from prometheus.config import IS_VERCEL, load_config, save_config, update_config
from prometheus.core.brain import PrometheusBrain
from prometheus.core.nlp_utils import match_wake_word
from prometheus.voice.tts import AVAILABLE_VOICES, EdgeTTSEngine


_BASE_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
WEB_DIR = _BASE_ROOT / "web"

app = FastAPI(title="Prometheus AI", version=__version__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cfg = load_config()
brain = PrometheusBrain(config=cfg)
tts_engine = EdgeTTSEngine()


class CommandRequest(BaseModel):
    text: str
    check_wake_word: bool = False


class TTSRequest(BaseModel):
    text: str
    language: Optional[str] = None
    voice: Optional[str] = None


class CustomEntryRequest(BaseModel):
    name: str
    target: str


@app.get("/api/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "online",
        "name": "Prometheus",
        "version": __version__,
        "mode": "vercel" if IS_VERCEL else "local",
        "websocket": not IS_VERCEL,
    }


@app.get("/api/state")
async def get_state() -> Dict[str, Any]:
    current_cfg = load_config()
    brain.reload_config(current_cfg)
    due_timers = brain.memory.poll_due_timers()
    return {
        "config": current_cfg.model_dump(),
        "telemetry": brain.sys.get_telemetry(),
        "processes": brain.sys.list_top_processes(limit=8),
        "notes": brain.memory.list_notes(limit=20),
        "timers": brain.memory.list_active_timers(),
        "due_timers": due_timers,
        "history": brain.memory.get_history(limit=25),
        "voices": AVAILABLE_VOICES,
        "mode": "vercel" if IS_VERCEL else "local",
    }


@app.post("/api/command")
async def run_command(req: CommandRequest) -> Dict[str, Any]:
    current_cfg = load_config()
    brain.reload_config(current_cfg)
    raw = req.text.strip()
    if req.check_wake_word and current_cfg.wake_word_enabled:
        matched, stripped = match_wake_word(raw, current_cfg.wake_words)
        if not matched:
            return {"ignored": True, "reason": "wake_word_not_detected"}
        raw = stripped
        if not raw:
            return {
                "ignored": False,
                "wake_only": True,
                "text": "Sizi dinliyorum efendim." if current_cfg.language != "en" else "Listening, sir.",
                "intent": "wake_ack",
                "success": True,
                "language": "tr" if current_cfg.language != "en" else "en",
                "data": {},
                "client_action": None,
            }

    resp = await brain.process(raw)
    return {
        "ignored": False,
        "text": resp.text,
        "intent": resp.intent,
        "success": resp.success,
        "language": resp.language,
        "data": resp.data,
        "client_action": resp.client_action,
    }


@app.post("/api/tts")
async def synthesize_tts(req: TTSRequest) -> Response:
    current_cfg = load_config()
    lang = req.language or ("tr" if current_cfg.language != "en" else "en")
    voice = req.voice or (
        current_cfg.tts_voice_tr if lang == "tr" else current_cfg.tts_voice_en
    )
    mp3 = await tts_engine.synthesize_mp3(
        text=req.text,
        voice=voice,
        rate=current_cfg.tts_rate,
    )
    if not mp3:
        return Response(status_code=204)
    return Response(content=mp3, media_type="audio/mpeg")


@app.get("/api/config")
async def get_config() -> Dict[str, Any]:
    return load_config().model_dump()


@app.patch("/api/config")
async def patch_config(patch: Dict[str, Any]) -> Dict[str, Any]:
    updated = update_config(patch)
    brain.reload_config(updated)
    return updated.model_dump()


@app.post("/api/custom/{kind}")
async def add_custom_entry(kind: str, entry: CustomEntryRequest) -> Dict[str, Any]:
    current = load_config()
    key = entry.name.strip()
    val = entry.target.strip()
    if not key or not val:
        raise HTTPException(status_code=400, detail="İsim ve hedef boş olamaz.")
    if kind == "app":
        current.custom_apps[key] = val
    elif kind == "site":
        current.custom_sites[key] = val
    elif kind == "command":
        current.custom_commands[key] = val
    else:
        raise HTTPException(status_code=400, detail="Geçersiz tür.")
    save_config(current)
    brain.reload_config(current)
    return current.model_dump()


@app.delete("/api/custom/{kind}/{name}")
async def delete_custom_entry(kind: str, name: str) -> Dict[str, Any]:
    current = load_config()
    target_map = {
        "app": current.custom_apps,
        "site": current.custom_sites,
        "command": current.custom_commands,
    }.get(kind)
    if target_map is None:
        raise HTTPException(status_code=400, detail="Geçersiz tür.")
    target_map.pop(name, None)
    save_config(current)
    brain.reload_config(current)
    return current.model_dump()


@app.get("/api/apps")
async def list_apps(refresh: bool = False) -> Dict[str, Any]:
    if refresh:
        brain.apps.discover_apps(force_refresh=True)
    return {"apps": brain.apps.list_installed(limit=200)}


@app.get("/api/notes")
async def list_notes() -> Dict[str, Any]:
    return {"notes": brain.memory.list_notes(limit=50)}


@app.delete("/api/notes/{note_id}")
async def delete_note(note_id: int) -> Dict[str, Any]:
    ok = brain.memory.delete_note(note_id)
    return {"ok": ok}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()

    async def telemetry_loop() -> None:
        while True:
            try:
                due_timers = brain.memory.poll_due_timers()
                for t in due_timers:
                    await ws.send_json(
                        {
                            "type": "timer_fired",
                            "timer": t,
                            "text": f"Efendim, zamanlayıcı doldu: {t['label']}",
                        }
                    )
                await ws.send_json(
                    {
                        "type": "telemetry",
                        "telemetry": brain.sys.get_telemetry(),
                        "timers": brain.memory.list_active_timers(),
                    }
                )
            except Exception:
                break
            await asyncio.sleep(2.5)

    bg_task = asyncio.create_task(telemetry_loop())
    try:
        while True:
            raw_msg = await ws.receive_text()
            payload = json.loads(raw_msg)
            msg_type = payload.get("type")
            if msg_type == "command":
                text = str(payload.get("text", "")).strip()
                current_cfg = load_config()
                brain.reload_config(current_cfg)
                resp = await brain.process(text)
                await ws.send_json(
                    {
                        "type": "command_result",
                        "command": text,
                        "text": resp.text,
                        "intent": resp.intent,
                        "success": resp.success,
                        "language": resp.language,
                        "data": resp.data,
                        "client_action": resp.client_action,
                        "history": brain.memory.get_history(limit=20),
                        "notes": brain.memory.list_notes(limit=20),
                    }
                )
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        bg_task.cancel()


if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(str(WEB_DIR / "index.html"))


@app.get("/manifest.json")
async def pwa_manifest() -> FileResponse:
    return FileResponse(str(WEB_DIR / "manifest.json"), media_type="application/manifest+json")


@app.get("/sw.js")
async def service_worker() -> FileResponse:
    return FileResponse(str(WEB_DIR / "sw.js"), media_type="application/javascript")

