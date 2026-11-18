"""Optional local desktop microphone listener for headless/CLI Prometheus mode."""

from __future__ import annotations

import asyncio
import io
import os
import tempfile
from typing import Optional

from prometheus.config import load_config
from prometheus.core.brain import PrometheusBrain
from prometheus.core.nlp_utils import match_wake_word
from prometheus.voice.tts import EdgeTTSEngine


async def run_cli_loop(use_mic: bool = True) -> None:
    cfg = load_config()
    brain = PrometheusBrain(config=cfg)
    tts = EdgeTTSEngine()
    print("==============================================")
    print("  PROMETHEUS AI — CLI & Yerel Ses Modu")
    print("  Çıkmak için 'çıkış' veya Ctrl+C yazın.")
    print("==============================================")

    if use_mic:
        try:
            import speech_recognition as sr  # type: ignore

            recognizer = sr.Recognizer()
            recognizer.dynamic_energy_threshold = True
            recognizer.pause_threshold = 0.7
            mic = sr.Microphone()
            with mic as source:
                print("[Prometheus] Ortam gürültüsü kalibre ediliyor...")
                recognizer.adjust_for_ambient_noise(source, duration=0.8)
            print("[Prometheus] Mikrofon aktif! 'Prometheus ...' diyerek komut verin.")
            while True:
                try:
                    with mic as source:
                        audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                    transcript = recognizer.recognize_google(audio, language=cfg.speech_lang)
                    print(f"[Siz]: {transcript}")
                    if cfg.wake_word_enabled:
                        matched, cmd = match_wake_word(transcript, cfg.wake_words)
                        if not matched:
                            continue
                        transcript = cmd
                    if not transcript:
                        print("[Prometheus]: Sizi dinliyorum efendim.")
                        continue
                    resp = await brain.process(transcript)
                    print(f"[Prometheus]: {resp.text}")
                    await _play_local_tts(tts, resp.text, cfg.tts_voice_tr if resp.language == "tr" else cfg.tts_voice_en, cfg.tts_rate)
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    continue
                except KeyboardInterrupt:
                    break
            return
        except ImportError:
            print("[Uyarı] SpeechRecognition/PyAudio kurulu değil; metin CLI moduna geçiliyor.")
        except Exception as exc:
            print(f"[Uyarı] Mikrofon başlatılamadı ({exc}); metin CLI moduna geçiliyor.")

    # Text CLI fallback
    while True:
        try:
            line = input("\n[Siz] > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue
        if line.lower() in ("exit", "quit", "çıkış", "cikis"):
            print("[Prometheus]: Görüşmek üzere efendim.")
            break
        resp = await brain.process(line)
        print(f"[Prometheus]: {resp.text}")


async def _play_local_tts(tts: EdgeTTSEngine, text: str, voice: str, rate: str) -> None:
    audio_bytes = await tts.synthesize_mp3(text=text, voice=voice, rate=rate)
    if not audio_bytes:
        return
    try:
        import pyttsx3  # type: ignore  # fallback only if no media player

        _ = pyttsx3
    except ImportError:
        pass
    # Write temporary mp3 and play via OS if available
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
        fp.write(audio_bytes)
        tmp_path = fp.name
    try:
        if os.name == "nt":
            os.system(f'powershell -c "(New-Object Media.SoundPlayer \'{tmp_path}\').PlaySync()"')
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
