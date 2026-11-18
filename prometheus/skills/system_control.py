"""System telemetry, OS controls, media/volume, files, and full-authority shell execution."""

from __future__ import annotations

import os
import platform
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

from prometheus.config import DATA_DIR


class SystemControl:
    def __init__(self) -> None:
        self.system = platform.system().lower()
        self.boot_time = psutil.boot_time()

    def get_telemetry(self) -> Dict[str, Any]:
        cpu_percent = psutil.cpu_percent(interval=0.05)
        vm = psutil.virtual_memory()
        disk_root = "C:\\" if self.system == "windows" else "/"
        try:
            disk = psutil.disk_usage(disk_root)
            disk_data = {
                "percent": round(disk.percent, 1),
                "used_gb": round(disk.used / (1024**3), 1),
                "total_gb": round(disk.total / (1024**3), 1),
            }
        except Exception:
            disk_data = {"percent": 0.0, "used_gb": 0.0, "total_gb": 0.0}

        battery_info = None
        try:
            bat = psutil.sensors_battery()
            if bat:
                battery_info = {
                    "percent": round(bat.percent, 1),
                    "plugged": bool(bat.power_plugged),
                }
        except Exception:
            battery_info = None

        uptime_sec = int(time.time() - self.boot_time)
        hours, rem = divmod(uptime_sec, 3600)
        minutes, _ = divmod(rem, 60)

        return {
            "os": f"{platform.system()} {platform.release()}",
            "hostname": platform.node(),
            "cpu_percent": round(cpu_percent, 1),
            "cpu_cores": psutil.cpu_count(logical=True) or 1,
            "ram_percent": round(vm.percent, 1),
            "ram_used_gb": round(vm.used / (1024**3), 2),
            "ram_total_gb": round(vm.total / (1024**3), 2),
            "disk": disk_data,
            "battery": battery_info,
            "uptime": f"{hours}s {minutes}d" if hours else f"{minutes}d",
            "process_count": len(psutil.pids()),
        }

    def list_top_processes(self, limit: int = 10) -> List[Dict[str, Any]]:
        procs: List[Dict[str, Any]] = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = p.info
                procs.append(
                    {
                        "pid": info["pid"],
                        "name": info["name"] or "unknown",
                        "cpu": round(info["cpu_percent"] or 0.0, 1),
                        "ram": round(info["memory_percent"] or 0.0, 1),
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        procs.sort(key=lambda x: (x["ram"], x["cpu"]), reverse=True)
        return procs[:limit]

    def set_volume(self, level: Optional[int] = None, action: str = "set") -> Dict[str, Any]:
        """action: set | up | down | mute | unmute"""
        if level is not None:
            level = max(0, min(100, int(level)))

        try:
            if self.system == "windows":
                if action == "mute":
                    ps = "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"
                elif action == "unmute":
                    ps = "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"
                elif action == "up":
                    ps = "$w=New-Object -ComObject WScript.Shell; 1..5 | % { $w.SendKeys([char]175) }"
                elif action == "down":
                    ps = "$w=New-Object -ComObject WScript.Shell; 1..5 | % { $w.SendKeys([char]174) }"
                else:
                    # Windows CoreAudio set exact volume via AudioDeviceCmdlets or SoundVolumeView or PowerShell C# P/Invoke
                    vol_float = (level or 50) / 100.0
                    ps = f"""
                    Add-Type -TypeDefinition @'
                    using System.Runtime.InteropServices;
                    [Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
                    interface IAudioEndpointVolume {{
                        int f(); int g(); int h(); int i();
                        int SetMasterVolumeLevelScalar(float fLevel, System.Guid pguidEventContext);
                    }}
                    [Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
                    interface IMMDevice {{ int Activate(ref System.Guid id, int clsCtx, int activationParams, out IAudioEndpointVolume aev); }}
                    [Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
                    interface IMMDeviceEnumerator {{ int f(); int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice endpoint); }}
                    [ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] class MMDeviceEnumeratorComObject {{}}
                    public class Audio {{
                        public static void SetVol(float v) {{
                            var enumerator = new MMDeviceEnumeratorComObject() as IMMDeviceEnumerator;
                            IMMDevice dev; enumerator.GetDefaultAudioEndpoint(0, 1, out dev);
                            var iid = typeof(IAudioEndpointVolume).GUID;
                            IAudioEndpointVolume aev; dev.Activate(ref iid, 1, 0, out aev);
                            aev.SetMasterVolumeLevelScalar(v, System.Guid.Empty);
                        }}
                    }}
'@
                    [Audio]::SetVol({vol_float})
                    """
                subprocess.Popen(
                    ["powershell", "-NoProfile", "-Command", ps],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return {"ok": True, "action": action, "level": level}

            if self.system == "darwin":
                if action == "mute":
                    cmd = "set volume with output muted"
                elif action == "unmute":
                    cmd = "set volume without output muted"
                elif action == "up":
                    cmd = "set volume output volume ((output volume of (get volume settings)) + 10)"
                elif action == "down":
                    cmd = "set volume output volume ((output volume of (get volume settings)) - 10)"
                else:
                    cmd = f"set volume output volume {level}"
                subprocess.run(["osascript", "-e", cmd], check=False, capture_output=True)
                return {"ok": True, "action": action, "level": level}

            # Linux (pactl / amixer)
            if action == "mute":
                subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1"], check=False, capture_output=True)
            elif action == "unmute":
                subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"], check=False, capture_output=True)
            elif action == "up":
                subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+10%"], check=False, capture_output=True)
            elif action == "down":
                subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-10%"], check=False, capture_output=True)
            elif level is not None:
                subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%"], check=False, capture_output=True)
            return {"ok": True, "action": action, "level": level}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def media_control(self, action: str) -> Dict[str, Any]:
        """action: play_pause | next | prev"""
        try:
            if self.system == "windows":
                key_map = {"play_pause": 179, "next": 176, "prev": 177}
                code = key_map.get(action, 179)
                ps = f"(New-Object -ComObject WScript.Shell).SendKeys([char]{code})"
                subprocess.Popen(["powershell", "-NoProfile", "-Command", ps], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return {"ok": True, "action": action}
            if self.system == "darwin":
                script = {
                    "play_pause": 'tell application "System Events" to key code 16',
                    "next": 'tell application "System Events" to key code 17',
                    "prev": 'tell application "System Events" to key code 18',
                }.get(action, "")
                if script:
                    subprocess.run(["osascript", "-e", script], check=False, capture_output=True)
                return {"ok": True, "action": action}
            cmd = {"play_pause": "play-pause", "next": "next", "prev": "previous"}.get(action, "play-pause")
            subprocess.run(["playerctl", cmd], check=False, capture_output=True)
            return {"ok": True, "action": action}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def set_brightness(self, level: int) -> Dict[str, Any]:
        lvl = max(0, min(100, int(level)))
        try:
            if self.system == "windows":
                ps = f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {lvl})"
                subprocess.Popen(["powershell", "-NoProfile", "-Command", ps], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return {"ok": True, "level": lvl}
            if self.system == "darwin":
                subprocess.run(["osascript", "-e", f"tell application \"System Events\" to set value of slider 1 of group 1 of window 1 of process \"ControlCenter\" to {lvl/100}"], check=False, capture_output=True)
                return {"ok": True, "level": lvl}
            subprocess.run(["brightnessctl", "set", f"{lvl}%"], check=False, capture_output=True)
            return {"ok": True, "level": lvl}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def create_folder(self, name: str, location: str = "desktop") -> Dict[str, Any]:
        base = self._resolve_special_folder(location)
        target = base / name.strip()
        try:
            target.mkdir(parents=True, exist_ok=True)
            return {"ok": True, "path": str(target)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def find_files(self, query: str, limit: int = 8) -> List[str]:
        q = query.strip().lower()
        if not q:
            return []
        found: List[str] = []
        roots = [
            self._resolve_special_folder("desktop"),
            self._resolve_special_folder("documents"),
            self._resolve_special_folder("downloads"),
        ]
        for root in roots:
            if not root.exists():
                continue
            for item in root.rglob("*"):
                if q in item.name.lower():
                    found.append(str(item))
                    if len(found) >= limit:
                        return found
        return found

    def type_text(self, content: str) -> Dict[str, Any]:
        try:
            import pyautogui  # type: ignore

            pyautogui.write(content, interval=0.02)
            return {"ok": True, "typed": content}
        except Exception as exc:
            return {"ok": False, "error": f"Yazma otomasyonu için pyautogui gerekli: {exc}"}

    def take_screenshot(self) -> Dict[str, Any]:
        shot_dir = DATA_DIR / "screenshots"
        shot_dir.mkdir(parents=True, exist_ok=True)
        filename = f"prometheus_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        out_path = shot_dir / filename

        try:
            import pyautogui  # type: ignore

            img = pyautogui.screenshot()
            img.save(str(out_path))
            return {"ok": True, "path": str(out_path)}
        except Exception:
            pass

        if self.system == "windows":
            ps = f"""
            Add-Type -AssemblyName System.Windows.Forms,System.Drawing
            $bounds = [System.Windows.Forms.SystemInformation]::VirtualScreen
            $bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
            $graphics = [System.Drawing.Graphics]::FromImage($bmp)
            $graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
            $bmp.Save('{out_path}')
            """
            proc = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
            if proc.returncode == 0 and out_path.exists():
                return {"ok": True, "path": str(out_path)}
        elif self.system == "darwin":
            subprocess.run(["screencapture", "-x", str(out_path)], check=False)
            if out_path.exists():
                return {"ok": True, "path": str(out_path)}
        else:
            if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
                for tool in (["gnome-screenshot", "-f", str(out_path)], ["scrot", str(out_path)]):
                    try:
                        subprocess.run(tool, check=True, capture_output=True)
                        if out_path.exists():
                            return {"ok": True, "path": str(out_path)}
                    except Exception:
                        continue
            return {
                "ok": False,
                "error": "Ekran görüntüsü için masaüstü oturumu veya pyautogui bulunamadı.",
            }
        return {"ok": False, "error": "Ekran görüntüsü alınamadı."}

    def _resolve_special_folder(self, key: str) -> Path:
        norm = key.strip().lower()
        alias_to_win = {
            "desktop": ("Desktop", "Desktop"),
            "masaustu": ("Desktop", "Desktop"),
            "downloads": ("{374DE290-123F-4565-9164-39C4925E467B}", "Downloads"),
            "indirilenler": ("{374DE290-123F-4565-9164-39C4925E467B}", "Downloads"),
            "documents": ("Personal", "Documents"),
            "belgeler": ("Personal", "Documents"),
            "pictures": ("My Pictures", "Pictures"),
            "resimler": ("My Pictures", "Pictures"),
            "music": ("My Music", "Music"),
            "muzik": ("My Music", "Music"),
            "home": ("", ""),
            "kullanici": ("", ""),
        }
        if norm in alias_to_win:
            reg_key, fallback_sub = alias_to_win[norm]
            if not fallback_sub:
                return Path.home()
            if self.system == "windows" and reg_key:
                try:
                    import winreg  # type: ignore

                    with winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER,
                        r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
                    ) as k:
                        val, _ = winreg.QueryValueEx(k, reg_key)
                        p = Path(os.path.expandvars(str(val)))
                        if p.exists():
                            return p
                except OSError:
                    pass
                # OneDrive fallback check
                onedrive = os.environ.get("OneDrive") or os.environ.get("OneDriveConsumer")
                if onedrive:
                    od_path = Path(onedrive) / fallback_sub
                    if od_path.exists():
                        return od_path
            return Path.home() / fallback_sub
        return Path(os.path.expandvars(key)).expanduser()

    def open_folder(self, folder_name: str) -> Dict[str, Any]:
        target = self._resolve_special_folder(folder_name)
        if not target.exists():
            return {"ok": False, "error": f"Klasör bulunamadı: {target}"}

        if self.system == "windows":
            os.startfile(str(target))  # type: ignore[attr-defined]
        elif self.system == "darwin":
            subprocess.Popen(["open", str(target)])
        elif os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
            subprocess.Popen(["xdg-open", str(target)])
        return {"ok": True, "path": str(target)}

    def power_action(self, action: str, full_authority: bool = True) -> Dict[str, Any]:
        """action: lock | sleep | restart | shutdown"""
        if not full_authority:
            return {
                "ok": False,
                "error": "Güç işlemleri için Tam Yetki modu aktif olmalıdır.",
            }

        if action == "lock":
            if self.system == "windows":
                subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])
            elif self.system == "darwin":
                subprocess.Popen(["pmset", "displaysleepnow"])
            elif os.environ.get("DISPLAY"):
                subprocess.Popen(["loginctl", "lock-session"])
            else:
                return {"ok": True, "action": "lock", "simulated": True}
            return {"ok": True, "action": "lock"}

        if action == "sleep":
            if self.system == "windows":
                subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
            elif self.system == "darwin":
                subprocess.Popen(["pmset", "sleepnow"])
            else:
                return {"ok": True, "action": "sleep", "simulated": True}
            return {"ok": True, "action": "sleep"}

        if action == "restart":
            if self.system == "windows":
                subprocess.Popen(["shutdown", "/r", "/t", "5"])
            elif self.system == "darwin":
                subprocess.Popen(["osascript", "-e", 'tell app "System Events" to restart'])
            else:
                return {"ok": True, "action": "restart", "simulated": True}
            return {"ok": True, "action": "restart"}

        if action == "shutdown":
            if self.system == "windows":
                subprocess.Popen(["shutdown", "/s", "/t", "5"])
            elif self.system == "darwin":
                subprocess.Popen(["osascript", "-e", 'tell app "System Events" to shut down'])
            else:
                return {"ok": True, "action": "shutdown", "simulated": True}
            return {"ok": True, "action": "shutdown"}

        return {"ok": False, "error": f"Bilinmeyen güç işlemi: {action}"}

    def run_shell(
        self,
        command: str,
        full_authority: bool = True,
        timeout: int = 20,
    ) -> Dict[str, Any]:
        if not full_authority:
            return {
                "ok": False,
                "error": "Terminal komutu çalıştırmak için Tam Yetki modu açık olmalıdır.",
            }
        cmd = command.strip()
        if not cmd:
            return {"ok": False, "error": "Boş komut."}
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            stdout = (proc.stdout or "").strip()
            stderr = (proc.stderr or "").strip()
            output = stdout if stdout else stderr
            if len(output) > 4000:
                output = output[:4000] + "\n... (kısaltıldı)"
            return {
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
                "output": output or "(Çıktı yok)",
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": f"Komut {timeout} saniye içinde tamamlanamadı."}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
