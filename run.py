"""Main entry point for Prometheus AI."""

from __future__ import annotations

import argparse
import asyncio
import os
import threading
import time
import webbrowser

import uvicorn


def _open_browser_when_ready(url: str) -> None:
    time.sleep(1.3)
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Prometheus AI — Free JARVIS-inspired Assistant")
    parser.add_argument("--host", default="0.0.0.0", help="Server host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)), help="Server port")
    parser.add_argument("--no-browser", action="store_true", help="Do not auto-open browser")
    parser.add_argument("--desktop", action="store_true", help="Launch as a standalone desktop window")
    parser.add_argument("--cli", action="store_true", help="Run in local terminal / mic CLI mode")
    parser.add_argument("--text-only", action="store_true", help="CLI mode without microphone")
    args = parser.parse_args()

    if args.desktop:
        from prometheus.desktop import launch_desktop

        launch_desktop(port=args.port if args.port != 8000 else None)
        return

    if args.cli:
        from prometheus.voice.local_stt import run_cli_loop

        asyncio.run(run_cli_loop(use_mic=not args.text_only))
        return

    if not args.no_browser:
        local_url = f"http://localhost:{args.port}"
        threading.Thread(target=_open_browser_when_ready, args=(local_url,), daemon=True).start()

    uvicorn.run(
        "prometheus.server:app",
        host=args.host,
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
