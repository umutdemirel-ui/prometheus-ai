"""Configuration management for Prometheus AI."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent.parent
IS_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"))
IS_FROZEN = bool(getattr(sys, "frozen", False))


def _resolve_default_data_dir() -> Path:
    if IS_VERCEL:
        return Path("/tmp/prometheus_data")
    if IS_FROZEN:
        if os.name == "nt":
            base = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
            return base / "PrometheusAI"
        return Path.home() / ".prometheus_ai"
    return BASE_DIR / "data"


_DEFAULT_DATA_DIR = _resolve_default_data_dir()
DATA_DIR = Path(os.environ.get("PROMETHEUS_DATA_DIR", str(_DEFAULT_DATA_DIR)))
CONFIG_PATH = DATA_DIR / "config.json"


class PrometheusConfig(BaseModel):
    assistant_name: str = "Prometheus"
    user_title_tr: str = "efendim"
    user_title_en: str = "sir"
    language: str = "tr"  # "tr" or "en" or "auto"
    speech_lang: str = "tr-TR"
    wake_word_enabled: bool = True
    wake_words: List[str] = Field(
        default_factory=lambda: [
            "prometheus",
            "hey prometheus",
            "ok prometheus",
            "prometyus",
            "prometeus",
            "prometüs",
            "promethius",
            "jarvis",
        ]
    )
    continuous_listening: bool = False
    full_authority: bool = True  # Tam Yetki mode
    confirm_power_actions: bool = True  # Confirm shutdown/restart unless bypassed
    tts_enabled: bool = True
    tts_engine: str = "edge"  # "edge" (free neural) or "browser"
    tts_voice_tr: str = "tr-TR-AhmetNeural"
    tts_voice_en: str = "en-GB-RyanNeural"
    tts_rate: str = "+5%"
    ollama_enabled: bool = True
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    custom_apps: Dict[str, str] = Field(default_factory=dict)
    custom_sites: Dict[str, str] = Field(default_factory=dict)
    custom_commands: Dict[str, str] = Field(default_factory=dict)


def load_config(path: Path = CONFIG_PATH) -> PrometheusConfig:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return PrometheusConfig(**raw)
        except Exception:
            pass
    cfg = PrometheusConfig()
    save_config(cfg, path)
    return cfg


def save_config(cfg: PrometheusConfig, path: Path = CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(cfg.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def update_config(patch: Dict[str, Any], path: Path = CONFIG_PATH) -> PrometheusConfig:
    cfg = load_config(path)
    data = cfg.model_dump()
    for k, v in patch.items():
        if k in data:
            data[k] = v
    updated = PrometheusConfig(**data)
    save_config(updated, path)
    return updated
