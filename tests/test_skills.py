"""Tests for Prometheus skills: AppLauncher, WebNavigator, SystemControl, Memory."""

from __future__ import annotations

import time
from pathlib import Path

from prometheus.core.memory import PrometheusMemory
from prometheus.skills.app_launcher import AppLauncher
from prometheus.skills.system_control import SystemControl
from prometheus.skills.web_navigator import WebNavigator


def test_app_launcher_custom_and_aliases():
    launcher = AppLauncher(custom_apps={"benim aracım": "/usr/bin/python3"})
    entry = launcher.resolve_app("benim aracım")
    assert entry is not None
    assert entry.launch_target == "/usr/bin/python3"

    calc = launcher.resolve_app("hesap makinesi")
    assert calc is not None


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
