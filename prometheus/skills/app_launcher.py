"""Cross-platform application discovery, launching, and termination for Prometheus."""

from __future__ import annotations

import difflib
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

from prometheus.core.nlp_utils import clean_target_phrase, normalize_ascii


@dataclass
class AppEntry:
    name: str
    launch_target: str
    kind: str = "executable"  # executable | shortcut | uwp | desktop | mac_app | uri
    aliases: tuple[str, ...] = ()


# Comprehensive built-in aliases for Windows, macOS, and Linux (Turkish + English)
BUILTIN_APP_ALIASES: Dict[str, Dict[str, Any]] = {
    "chrome": {
        "aliases": ["google chrome", "chrome", "krom", "tarayici", "browser"],
        "win": ["chrome", r"%ProgramFiles%\Google\Chrome\Application\chrome.exe", r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe", r"%LocalAppData%\Google\Chrome\Application\chrome.exe"],
        "mac": ["Google Chrome"],
        "linux": ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"],
    },
    "edge": {
        "aliases": ["microsoft edge", "edge", "edg"],
        "win": ["msedge", r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe", r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"],
        "mac": ["Microsoft Edge"],
        "linux": ["microsoft-edge", "microsoft-edge-stable"],
    },
    "firefox": {
        "aliases": ["mozilla firefox", "firefox", "tilki"],
        "win": ["firefox", r"%ProgramFiles%\Mozilla Firefox\firefox.exe"],
        "mac": ["Firefox"],
        "linux": ["firefox"],
    },
    "brave": {
        "aliases": ["brave", "brave browser"],
        "win": ["brave", r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe", r"%LocalAppData%\BraveSoftware\Brave-Browser\Application\brave.exe"],
        "mac": ["Brave Browser"],
        "linux": ["brave-browser", "brave"],
    },
    "opera": {
        "aliases": ["opera", "opera gx"],
        "win": ["opera", r"%LocalAppData%\Programs\Opera\opera.exe", r"%LocalAppData%\Programs\Opera GX\opera.exe"],
        "mac": ["Opera", "Opera GX"],
        "linux": ["opera"],
    },
    "vscode": {
        "aliases": ["vs code", "vscode", "visual studio code", "kod editoru", "code"],
        "win": ["code", r"%LocalAppData%\Programs\Microsoft VS Code\Code.exe", r"%ProgramFiles%\Microsoft VS Code\Code.exe"],
        "mac": ["Visual Studio Code"],
        "linux": ["code"],
    },
    "cursor": {
        "aliases": ["cursor", "cursor ai"],
        "win": ["cursor", r"%LocalAppData%\Programs\cursor\Cursor.exe"],
        "mac": ["Cursor"],
        "linux": ["cursor"],
    },
    "discord": {
        "aliases": ["discord", "diskord", "dc"],
        "win": [r"%LocalAppData%\Discord\Update.exe --processStart Discord.exe", "discord"],
        "mac": ["Discord"],
        "linux": ["discord"],
    },
    "spotify": {
        "aliases": ["spotify", "spotifay", "muzik"],
        "win": ["spotify", r"%AppData%\Spotify\Spotify.exe"],
        "mac": ["Spotify"],
        "linux": ["spotify"],
    },
    "steam": {
        "aliases": ["steam", "stim"],
        "win": [r"%ProgramFiles(x86)%\Steam\steam.exe", "steam"],
        "mac": ["Steam"],
        "linux": ["steam"],
    },
    "epic_games": {
        "aliases": ["epic games", "epic", "epic games launcher"],
        "win": [r"%ProgramFiles(x86)%\Epic Games\Launcher\Portal\Binaries\Win32\EpicGamesLauncher.exe", r"%ProgramFiles(x86)%\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe"],
        "mac": ["Epic Games Launcher"],
        "linux": ["heroic", "legendary"],
    },
    "valorant": {
        "aliases": ["valorant", "valo"],
        "win": [r"C:\Riot Games\Riot Client\RiotClientServices.exe --launch-product=valorant --launch-patchline=live"],
        "mac": [],
        "linux": [],
    },
    "telegram": {
        "aliases": ["telegram", "tg"],
        "win": [r"%AppData%\Telegram Desktop\Telegram.exe", "telegram"],
        "mac": ["Telegram"],
        "linux": ["telegram-desktop", "telegram"],
    },
    "whatsapp": {
        "aliases": ["whatsapp", "vatsap", "watsap"],
        "win": ["whatsapp:"],
        "mac": ["WhatsApp"],
        "linux": ["whatsapp-for-linux"],
    },
    "obs": {
        "aliases": ["obs", "obs studio"],
        "win": [r"%ProgramFiles%\obs-studio\bin\64bit\obs64.exe", "obs64"],
        "mac": ["OBS"],
        "linux": ["obs"],
    },
    "vlc": {
        "aliases": ["vlc", "vlc media player"],
        "win": [r"%ProgramFiles%\VideoLAN\VLC\vlc.exe", "vlc"],
        "mac": ["VLC"],
        "linux": ["vlc"],
    },
    "calculator": {
        "aliases": ["calculator", "calc", "hesap makinesi", "hesap"],
        "win": ["calc.exe"],
        "mac": ["Calculator"],
        "linux": ["gnome-calculator", "kcalc", "galculator", "xcalc"],
    },
    "notepad": {
        "aliases": ["notepad", "not defteri", "notdefteri"],
        "win": ["notepad.exe"],
        "mac": ["TextEdit"],
        "linux": ["gedit", "kate", "mousepad", "nano"],
    },
    "paint": {
        "aliases": ["paint", "mspaint", "resim"],
        "win": ["mspaint.exe"],
        "mac": ["Preview"],
        "linux": ["gimp", "kolourpaint"],
    },
    "explorer": {
        "aliases": ["explorer", "file explorer", "dosya gezgini", "dosyalar", "bilgisayarim"],
        "win": ["explorer.exe"],
        "mac": ["Finder"],
        "linux": ["nautilus", "dolphin", "thunar", "nemo", "pcmanfm"],
    },
    "terminal": {
        "aliases": ["terminal", "cmd", "command prompt", "komut istemi", "powershell", "konsol", "kabuk"],
        "win": ["wt.exe", "powershell.exe", "cmd.exe"],
        "mac": ["Terminal"],
        "linux": ["gnome-terminal", "konsole", "xfce4-terminal", "alacritty", "kitty", "xterm"],
    },
    "task_manager": {
        "aliases": ["task manager", "taskmgr", "gorev yoneticisi", "gorev"],
        "win": ["taskmgr.exe"],
        "mac": ["Activity Monitor"],
        "linux": ["gnome-system-monitor", "ksysguard", "htop"],
    },
    "settings": {
        "aliases": ["settings", "ayarlar", "sistem ayarlari"],
        "win": ["ms-settings:"],
        "mac": ["System Settings", "System Preferences"],
        "linux": ["gnome-control-center", "systemsettings5"],
    },
    "control_panel": {
        "aliases": ["control panel", "denetim masasi"],
        "win": ["control.exe"],
        "mac": ["System Settings"],
        "linux": ["gnome-control-center"],
    },
    "word": {
        "aliases": ["word", "microsoft word"],
        "win": ["winword.exe"],
        "mac": ["Microsoft Word"],
        "linux": ["libreoffice --writer"],
    },
    "excel": {
        "aliases": ["excel", "microsoft excel"],
        "win": ["excel.exe"],
        "mac": ["Microsoft Excel"],
        "linux": ["libreoffice --calc"],
    },
    "powerpoint": {
        "aliases": ["powerpoint", "microsoft powerpoint", "sunum"],
        "win": ["powerpnt.exe"],
        "mac": ["Microsoft PowerPoint"],
        "linux": ["libreoffice --impress"],
    },
    "photoshop": {
        "aliases": ["photoshop", "adobe photoshop", "ps"],
        "win": ["Photoshop.exe"],
        "mac": ["Adobe Photoshop 2024", "Adobe Photoshop 2025", "Adobe Photoshop"],
        "linux": ["gimp"],
    },
    "notion": {
        "aliases": ["notion"],
        "win": [r"%LocalAppData%\Programs\Notion\Notion.exe"],
        "mac": ["Notion"],
        "linux": ["notion-app"],
    },
    "zoom": {
        "aliases": ["zoom"],
        "win": [r"%AppData%\Zoom\bin\Zoom.exe"],
        "mac": ["zoom.us"],
        "linux": ["zoom"],
    },
    "snipping_tool": {
        "aliases": ["snipping tool", "ekran alintisi", "ekran alintisi araci"],
        "win": ["ms-screenclip:"],
        "mac": ["Screenshot"],
        "linux": ["gnome-screenshot", "flameshot", "spectacle"],
    },
}


class AppLauncher:
    """Discovers and launches applications across Windows, macOS, and Linux."""

    def __init__(self, custom_apps: Optional[Dict[str, str]] = None) -> None:
        self.system = platform.system().lower()  # windows | darwin | linux
        self.custom_apps: Dict[str, str] = custom_apps or {}
        self._discovered_cache: Optional[Dict[str, AppEntry]] = None

    def set_custom_apps(self, custom_apps: Dict[str, str]) -> None:
        self.custom_apps = dict(custom_apps)

    def has_desktop_display(self) -> bool:
        if self.system in ("windows", "darwin"):
            return True
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

    def discover_apps(self, force_refresh: bool = False) -> Dict[str, AppEntry]:
        if self._discovered_cache is not None and not force_refresh:
            return self._discovered_cache

        apps: Dict[str, AppEntry] = {}

        if self.system == "windows":
            self._discover_windows(apps)
        elif self.system == "darwin":
            self._discover_macos(apps)
        else:
            self._discover_linux(apps)

        self._discovered_cache = apps
        return apps

    def _discover_windows(self, apps: Dict[str, AppEntry]) -> None:
        start_dirs = [
            Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData"))
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs",
            Path(os.environ.get("APPDATA", ""))
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs",
            Path.home() / "Desktop",
        ]
        for root in start_dirs:
            if not root.exists():
                continue
            for item in root.rglob("*"):
                if item.suffix.lower() in (".lnk", ".url", ".exe"):
                    key = normalize_ascii(item.stem)
                    if key and key not in apps:
                        apps[key] = AppEntry(
                            name=item.stem,
                            launch_target=str(item),
                            kind="shortcut",
                        )

        # Windows Registry App Paths
        try:
            import winreg  # type: ignore

            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    reg_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
                    with winreg.OpenKey(hive, reg_path) as key_handle:
                        i = 0
                        while True:
                            try:
                                sub_name = winreg.EnumKey(key_handle, i)
                                i += 1
                                with winreg.OpenKey(key_handle, sub_name) as sub_key:
                                    val, _ = winreg.QueryValueEx(sub_key, "")
                                    stem = normalize_ascii(Path(sub_name).stem)
                                    if stem and val and stem not in apps:
                                        apps[stem] = AppEntry(
                                            name=Path(sub_name).stem,
                                            launch_target=str(val).strip('"'),
                                            kind="executable",
                                        )
                            except OSError:
                                break
                except OSError:
                    continue
        except ImportError:
            pass

        # UWP / Store apps via PowerShell Get-StartApps
        try:
            proc = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-StartApps | ForEach-Object { \"$($_.Name)|$($_.AppID)\" }",
                ],
                capture_output=True,
                text=True,
                timeout=6,
            )
            if proc.returncode == 0:
                for line in proc.stdout.splitlines():
                    if "|" not in line:
                        continue
                    name, app_id = line.split("|", 1)
                    key = normalize_ascii(name)
                    if key and app_id.strip() and key not in apps:
                        apps[key] = AppEntry(
                            name=name.strip(),
                            launch_target=f"shell:AppsFolder\\{app_id.strip()}",
                            kind="uwp",
                        )
        except Exception:
            pass

    def _discover_macos(self, apps: Dict[str, AppEntry]) -> None:
        for base in (
            Path("/Applications"),
            Path("/System/Applications"),
            Path.home() / "Applications",
        ):
            if not base.exists():
                continue
            for item in base.glob("*.app"):
                key = normalize_ascii(item.stem)
                if key:
                    apps[key] = AppEntry(
                        name=item.stem,
                        launch_target=str(item),
                        kind="mac_app",
                    )

    def _discover_linux(self, apps: Dict[str, AppEntry]) -> None:
        desktop_dirs = [
            Path("/usr/share/applications"),
            Path("/usr/local/share/applications"),
            Path.home() / ".local" / "share" / "applications",
            Path("/var/lib/snapd/desktop/applications"),
            Path("/var/lib/flatpak/exports/share/applications"),
        ]
        for d in desktop_dirs:
            if not d.exists():
                continue
            for file in d.rglob("*.desktop"):
                name = file.stem
                exec_cmd = ""
                try:
                    for line in file.read_text(encoding="utf-8", errors="ignore").splitlines():
                        if line.startswith("Name=") and name == file.stem:
                            name = line.split("=", 1)[1].strip()
                        elif line.startswith("Exec=") and not exec_cmd:
                            raw_exec = line.split("=", 1)[1].strip()
                            # Remove %u %F etc.
                            exec_cmd = " ".join(
                                p for p in raw_exec.split() if not p.startswith("%")
                            )
                except Exception:
                    continue
                key = normalize_ascii(name)
                if key and exec_cmd and key not in apps:
                    apps[key] = AppEntry(
                        name=name,
                        launch_target=exec_cmd,
                        kind="desktop",
                    )

    def resolve_app(self, query: str) -> Optional[AppEntry]:
        cleaned = clean_target_phrase(query)
        norm = normalize_ascii(cleaned)
        if not norm:
            return None

        # 1. User custom apps (highest priority)
        for alias, target in self.custom_apps.items():
            if normalize_ascii(alias) == norm or norm in normalize_ascii(alias):
                return AppEntry(name=alias, launch_target=target, kind="custom")

        # 2. Built-in alias table
        os_key = "win" if self.system == "windows" else ("mac" if self.system == "darwin" else "linux")
        for canonical, spec in BUILTIN_APP_ALIASES.items():
            aliases_norm = [normalize_ascii(a) for a in spec["aliases"]]
            if norm == canonical or norm in aliases_norm or any(
                difflib.SequenceMatcher(None, norm, a).ratio() >= 0.86 for a in aliases_norm
            ):
                candidates = spec.get(os_key, [])
                for cand in candidates:
                    expanded = os.path.expandvars(cand)
                    if expanded.endswith(":"):
                        return AppEntry(name=canonical, launch_target=expanded, kind="uri")
                    if self.system == "darwin":
                        return AppEntry(name=expanded, launch_target=expanded, kind="mac_app")
                    exe_part = expanded.split()[0]
                    if Path(exe_part).exists() or shutil.which(exe_part):
                        return AppEntry(name=canonical, launch_target=expanded, kind="executable")
                # Check discovered installed apps by canonical name before falling back
                discovered = self.discover_apps()
                if canonical in discovered:
                    return discovered[canonical]
                # Return bare command name only if it has no missing explicit path separator
                if candidates and ("\\" not in candidates[0] and "/" not in candidates[0]):
                    return AppEntry(
                        name=canonical,
                        launch_target=os.path.expandvars(candidates[0]),
                        kind="executable",
                    )

        # 3. Discovered installed apps (exact, substring, fuzzy)
        discovered = self.discover_apps()
        if norm in discovered:
            return discovered[norm]

        # Substring match
        matches = [entry for k, entry in discovered.items() if norm in k or k in norm]
        if matches:
            matches.sort(key=lambda e: len(e.name))
            return matches[0]

        # Fuzzy match
        if discovered:
            best_keys = difflib.get_close_matches(norm, list(discovered.keys()), n=1, cutoff=0.72)
            if best_keys:
                return discovered[best_keys[0]]

        # 4. Direct binary on PATH
        direct = shutil.which(cleaned) or shutil.which(norm.replace(" ", "-"))
        if direct:
            return AppEntry(name=cleaned, launch_target=direct, kind="executable")

        return None

    def launch(self, query: str) -> Dict[str, Any]:
        entry = self.resolve_app(query)
        target_name = entry.name if entry else clean_target_phrase(query)

        if entry is None:
            # On Windows, `start "" "<query>"` can still launch protocol/registered executables
            if self.system == "windows" and target_name:
                try:
                    subprocess.Popen(
                        f'start "" "{target_name}"',
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return {
                        "ok": True,
                        "app": target_name,
                        "target": target_name,
                        "simulated": False,
                    }
                except Exception as exc:
                    return {"ok": False, "app": target_name, "error": str(exc)}
            return {
                "ok": False,
                "app": target_name,
                "error": f"'{target_name}' sistemde bulunamadı. Özel Uygulama Ekle bölümünden yolunu tanımlayabilirsiniz.",
            }

        if not self.has_desktop_display():
            return {
                "ok": True,
                "app": entry.name,
                "target": entry.launch_target,
                "simulated": True,
                "note": "Headless ortam algılandı; masaüstü ekranı bağlı olmadığı için komut simüle edildi. Kendi bilgisayarınızda doğrudan açılacaktır.",
            }

        try:
            if self.system == "windows":
                if entry.kind in ("shortcut", "uri") or entry.launch_target.startswith("shell:"):
                    os.startfile(entry.launch_target)  # type: ignore[attr-defined]
                else:
                    subprocess.Popen(
                        entry.launch_target,
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
            elif self.system == "darwin":
                subprocess.Popen(
                    ["open", "-a", entry.launch_target],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.Popen(
                    entry.launch_target,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            return {
                "ok": True,
                "app": entry.name,
                "target": entry.launch_target,
                "simulated": False,
            }
        except Exception as exc:
            return {"ok": False, "app": entry.name, "error": str(exc)}

    def close_app(self, query: str) -> Dict[str, Any]:
        cleaned = clean_target_phrase(query)
        norm = normalize_ascii(cleaned)
        if not norm:
            return {"ok": False, "error": "Uygulama adı belirtilmedi."}

        # Map alias to process keywords
        search_terms = {norm}
        for canonical, spec in BUILTIN_APP_ALIASES.items():
            if norm == canonical or norm in [normalize_ascii(a) for a in spec["aliases"]]:
                search_terms.add(canonical)
                for a in spec["aliases"]:
                    search_terms.add(normalize_ascii(a))

        killed: List[str] = []
        current_pid = os.getpid()
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if proc.info["pid"] == current_pid:
                    continue
                pname = normalize_ascii((proc.info["name"] or "").replace(".exe", ""))
                if any(term in pname or pname in term for term in search_terms if len(term) >= 2):
                    proc.terminate()
                    killed.append(proc.info["name"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if killed:
            return {"ok": True, "app": cleaned, "terminated": sorted(set(killed))}
        return {"ok": False, "app": cleaned, "error": f"Çalışan '{cleaned}' süreci bulunamadı."}

    def list_installed(self, limit: int = 100) -> List[Dict[str, str]]:
        discovered = self.discover_apps()
        items = [
            {"name": e.name, "target": e.launch_target, "kind": e.kind}
            for e in sorted(discovered.values(), key=lambda x: x.name.lower())
        ]
        for alias, target in self.custom_apps.items():
            items.insert(0, {"name": alias, "target": target, "kind": "custom"})
        return items[:limit]
