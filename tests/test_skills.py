"""Tests for Prometheus skills: AppLauncher, WebNavigator, SystemControl, Memory."""

from __future__ import annotations

import time
from pathlib import Path

from prometheus.core.memory import PrometheusMemory
from prometheus.skills.app_launcher import AppLauncher, split_command_target
from prometheus.skills.system_control import SystemControl
from prometheus.skills.web_navigator import WebNavigator


def test_split_windows_paths_with_spaces():
    exe1, args1 = split_command_target(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    assert exe1 == r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    assert args1 == []

    exe2, args2 = split_command_target(
        r"C:\Users\Umut Demirel\AppData\Local\Discord\Update.exe --processStart Discord.exe"
    )
    assert exe2 == r"C:\Users\Umut Demirel\AppData\Local\Discord\Update.exe"
    assert args2 == ["--processStart", "Discord.exe"]

    exe3, args3 = split_command_target(r'"C:\Riot Games\Riot Client\RiotClientServices.exe" --launch-product=valorant')
    assert exe3 == r"C:\Riot Games\Riot Client\RiotClientServices.exe"
    assert args3 == ["--launch-product=valorant"]


def test_app_launcher_custom_and_aliases(monkeypatch):
    launcher = AppLauncher(custom_apps={"benim aracım": "/usr/bin/python3"})
    entry = launcher.resolve_app("benim aracım")
    assert entry is not None
    assert entry.launch_target == "/usr/bin/python3"

    monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/gnome-calculator" if cmd == "gnome-calculator" else None)
    calc = launcher.resolve_app("hesap makinesi")
    assert calc is not None
    assert calc.launch_target == "gnome-calculator"


def test_web_navigator_resolution():
    nav = WebNavigator(custom_sites={"okul": "https://obs.example.edu.tr"})
    assert nav.resolve_url("okul") == "https://obs.example.edu.tr"
    assert nav.resolve_url("reddit") == "https://www.reddit.com"
    assert nav.resolve_url("openai.com") == "https://openai.com"
    assert "google.com/search" in nav.build_search_url("prometheus ai", "google")


def test_system_telemetry_and_memory_timers(tmp_path: Path):
    sys_ctrl = SystemControl()
    tel = sys_ctrl.get_telemetry()
    assert "cpu_percent" in tel
    assert "ram_percent" in tel
    assert tel["ram_total_gb"] > 0

    mem = PrometheusMemory(db_path=tmp_path / "mem.db")
    mem.add_timer("Test", duration_seconds=0)
    time.sleep(0.05)
    due = mem.poll_due_timers()
    assert len(due) == 1
    assert due[0]["label"] == "Test"


def test_folder_create_and_find(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / "Desktop").mkdir()
    sys_ctrl = SystemControl()
    res = sys_ctrl.create_folder("PrometheusTest", location="desktop")
    assert res["ok"] is True
    target = tmp_path / "Desktop" / "PrometheusTest"
    assert target.exists()
    (target / "rapor.txt").write_text("ok", encoding="utf-8")
    found = sys_ctrl.find_files("rapor")
    assert len(found) == 1

