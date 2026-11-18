"""Completely free Neural TTS using Microsoft Edge voices (edge-tts) with LRU cache."""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from typing import Optional

try:
    import edge_tts  # type: ignore
except ImportError:
    edge_tts = None


AVAILABLE_VOICES = {
    "tr-TR-AhmetNeural": {"label": "Ahmet (Türkçe Erkek - JARVIS Tarzı)", "lang": "tr"},
    "tr-TR-EmelNeural": {"label": "Emel (Türkçe Kadın)", "lang": "tr"},
    "en-GB-RyanNeural": {"label": "Ryan (British English - Classic JARVIS)", "lang": "en"},
    "en-US-GuyNeural": {"label": "Guy (US English)", "lang": "en"},
    "en-GB-SoniaNeural": {"label": "Sonia (British English Female)", "lang": "en"},
}


class EdgeTTSEngine:
    def __init__(self, max_cache_items: int = 64) -> None:
        self._cache: OrderedDict[str, bytes] = OrderedDict()
        self._max_cache = max_cache_items

    async def synthesize_mp3(
        self,
        text: str,
        voice: str = "tr-TR-AhmetNeural",
        rate: str = "+5%",
    ) -> Optional[bytes]:
        if not text.strip() or edge_tts is None:
            return None

        key_raw = f"{voice}|{rate}|{text.strip()}"
        cache_key = hashlib.sha256(key_raw.encode("utf-8")).hexdigest()
        if cache_key in self._cache:
            self._cache.move_to_end(cache_key)
            return self._cache[cache_key]

        try:
            communicate = edge_tts.Communicate(text=text.strip(), voice=voice, rate=rate)
            chunks: list[bytes] = []
            async for chunk in communicate.stream():
                if chunk.get("type") == "audio":
                    chunks.append(chunk["data"])
            audio_bytes = b"".join(chunks)
            if not audio_bytes:
                return None
            self._cache[cache_key] = audio_bytes
            if len(self._cache) > self._max_cache:
                self._cache.popitem(last=False)
            return audio_bytes
        except Exception:
            return None
