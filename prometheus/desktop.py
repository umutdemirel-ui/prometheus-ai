"""Native Desktop Application wrapper for Prometheus AI."""

from __future__ import annotations

import os
import platform
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path
from typing import Optional

import uvicorn


def _find_free_port(preferred: int = 8765) -> int:
    for port in (preferred, 8766, 8767, 8000, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return s.getsockname()[1]
            except OSError:
                continue
    return 8765


def _wait_for_server(url: str, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/api/health", timeout=1.5) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.2)
    return False


def _find_chromium_app_binary() -> Optional[str]:
    sys_name = platform.system().lower()
    if sys_name == "windows":
        candidates = [
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        ]
        for c in candidates:
            if Path(c).exists():
                return c
    elif sys_name == "darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        ]
        for c in candidates:
            if Path(c).exists():
                return c
    else:
        for name in ("google-chrome", "microsoft-edge", "chromium", "chromium-browser", "brave-browser"):
            found = shutil.which(name)
            if found:
                return found
    return None


def launch_desktop(port: Optional[int] = None) -> None:
    chosen_port = port or _find_free_port(8765)
    url = f"http://127.0.0.1:{chosen_port}"

    from prometheus.server import app

    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=chosen_port,
        log_level="warning",
    )
    server = uvicorn.Server(config)

    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    if not _wait_for_server(url):
        print("[Prometheus] Yerel sunucu başlatılamadı.", file=sys.stderr)
        sys.exit(1)

    # 1. Try native PyWebView window (true desktop app with no browser dependency)
    try:
        import webview  # type: ignore

        webview.create_window(
            title="PROMETHEUS AI // Desktop Core",
            url=url,
            width=1360,
            height=860,
            min_size=(960, 640),
            background_color="#040811",
        )
        webview.start(debug=False)
        server.should_exit = True
        return
    except ImportError:
        pass
    except Exception:
        pass

    # 2. Fallback: Standalone Chromium --app window (frameless desktop app experience)
    browser_bin = _find_chromium_app_binary()
    if browser_bin:
        print(f"[Prometheus Desktop] Bağımsız pencere başlatılıyor ({url})...")
        proc = subprocess.Popen(
            [
                browser_bin,
                f"--app={url}",
                "--window-size=1360,860",
                "--class=PrometheusAI",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            proc.wait()
        except KeyboardInterrupt:
            pass
        server.should_exit = True
        return

    # 3. Last-resort fallback: default browser
    print(f"[Prometheus Desktop] Sunucu çalışıyor: {url}")
    webbrowser.open(url)
    try:
        while server_thread.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        server.should_exit = True


if __name__ == "__main__":
    launch_desktop()
