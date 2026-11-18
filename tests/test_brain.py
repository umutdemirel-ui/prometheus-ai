"""Tests for Prometheus NLU, wake-word detection, and Brain command routing."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from prometheus.config import PrometheusConfig
from prometheus.core.brain import PrometheusBrain
from prometheus.core.memory import PrometheusMemory
from prometheus.core.nlp_utils import extract_number, match_wake_word


def _make_brain(tmp_path: Path, full_authority: bool = True) -> PrometheusBrain:
    cfg = PrometheusConfig(
        full_authority=full_authority,
        ollama_enabled=False,
        confirm_power_actions=True,
    )
    mem = PrometheusMemory(db_path=tmp_path / "test.db")
    return PrometheusBrain(config=cfg, memory=mem)


def test_wake_word_phonetic_variants():
    matched, rest = match_wake_word("Prometheus YouTube'u aç")
    assert matched is True
    assert rest == "YouTube'u aç"

    matched2, rest2 = match_wake_word("Hey Prometyus saat kaç")
    assert matched2 is True
    assert rest2 == "saat kaç"

    matched3, rest3 = match_wake_word("Prometeus")
    assert matched3 is True
    assert rest3 == ""

    matched4, _ = match_wake_word("bugün hava güzel")
    assert matched4 is False


def test_turkish_number_extraction():
    assert extract_number("sesi yüzde elli yap") == 50
    assert extract_number("5 dakika kur") == 5
    assert extract_number("volume 75") == 75


def test_websites_and_in_site_search(tmp_path: Path):
    brain = _make_brain(tmp_path)

    r1 = asyncio.run(brain.process("YouTube'u aç"))
    assert r1.intent == "open_website"
    assert r1.client_action["url"] == "https://www.youtube.com"

    r2 = asyncio.run(brain.process("github.com'a gir"))
    assert r2.intent == "open_website"
    assert r2.client_action["url"] == "https://github.com"

    r3 = asyncio.run(brain.process("YouTube'da Duman ara"))
    assert r3.intent == "web_search"
    assert "youtube.com/results?search_query=Duman" in r3.client_action["url"]


def test_calculator_time_notes_timers(tmp_path: Path):
    brain = _make_brain(tmp_path)

    rc = asyncio.run(brain.process("25 çarpı 4 kaç"))
    assert rc.intent == "calculate"
    assert rc.data["result"] == 100

    rt = asyncio.run(brain.process("saat kaç"))
    assert rt.intent == "time"

    rn1 = asyncio.run(brain.process("not al: Toplantı saat 3te"))
    assert rn1.intent == "add_note"
    rn2 = asyncio.run(brain.process("notlarımı oku"))
    assert rn2.intent == "list_notes"
    assert len(rn2.data["notes"]) == 1

    rtim = asyncio.run(brain.process("2 dakika zamanlayıcı kur"))
    assert rtim.intent == "set_timer"
    assert rtim.data["duration_seconds"] == 120


def test_full_authority_shell_and_power_confirmation(tmp_path: Path):
    brain = _make_brain(tmp_path, full_authority=True)
    rs = asyncio.run(brain.process("komut çalıştır: echo prometheus_ok"))
    assert rs.intent == "shell_exec"
    assert rs.success is True
    assert "prometheus_ok" in rs.data["output"]

    # Power confirmation prompt then cancel
    rp = asyncio.run(brain.process("bilgisayarı kapat"))
    assert rp.intent == "power_confirm_prompt"
    rc = asyncio.run(brain.process("iptal"))
    assert rc.intent == "power_cancelled"

    # Without full_authority, shell exec is blocked
    restricted = _make_brain(tmp_path, full_authority=False)
    rr = asyncio.run(restricted.process("komut çalıştır: echo test"))
    assert rr.intent == "shell_exec"
    assert rr.success is False
