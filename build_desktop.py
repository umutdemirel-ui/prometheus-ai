"""Build a standalone PrometheusAI desktop executable using PyInstaller."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main() -> None:
    sep = ";" if os.name == "nt" else ":"
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onefile",
        "--name",
        "PrometheusAI",
        "--add-data",
        f"{ROOT / 'web'}{sep}web",
        "--hidden-import",
        "prometheus.server",
        "--hidden-import",
        "uvicorn.logging",
        "--hidden-import",
        "uvicorn.loops.auto",
        "--hidden-import",
        "uvicorn.protocols.http.auto",
        "--hidden-import",
        "uvicorn.protocols.websockets.auto",
        "--hidden-import",
        "uvicorn.lifespan.on",
        str(ROOT / "prometheus" / "desktop.py"),
    ]
    icon_png = ROOT / "web" / "icon-512.png"
    if icon_png.exists() and os.name != "nt":
        cmd.extend(["--icon", str(icon_png)])

    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print("\nBuild complete! Executable is in dist/PrometheusAI")


if __name__ == "__main__":
    main()
