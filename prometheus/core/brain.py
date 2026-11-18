"""Prometheus Brain — Bilingual (TR/EN) Intent Engine, NLU & Skill Orchestrator."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from prometheus.config import PrometheusConfig, load_config
from prometheus.core.memory import PrometheusMemory
from prometheus.core.nlp_utils import (
    clean_target_phrase,
    detect_language,
    extract_number,
    normalize_ascii,
    tr_lower,
)
from prometheus.skills.app_launcher import AppLauncher
from prometheus.skills.assistant_skills import (
    calculate_expression,
    fetch_weather,
    fetch_wikipedia_summary,
    get_current_date_str,
    get_current_time_str,
    query_ollama,
)
from prometheus.skills.system_control import SystemControl
from prometheus.skills.web_navigator import KNOWN_SITES, WebNavigator


@dataclass
class BrainResponse:
    text: str
    intent: str
    success: bool = True
    language: str = "tr"
    data: Dict[str, Any] = field(default_factory=dict)
    client_action: Optional[Dict[str, Any]] = None


class PrometheusBrain:
    def __init__(
        self,
        config: Optional[PrometheusConfig] = None,
        memory: Optional[PrometheusMemory] = None,
        app_launcher: Optional[AppLauncher] = None,
        web_navigator: Optional[WebNavigator] = None,
        system_control: Optional[SystemControl] = None,
    ) -> None:
        self.config = config or load_config()
        self.memory = memory or PrometheusMemory()
        self.apps = app_launcher or AppLauncher(self.config.custom_apps)
        self.web = web_navigator or WebNavigator(self.config.custom_sites)
        self.sys = system_control or SystemControl()
        self.pending_power_action: Optional[str] = None

    def reload_config(self, cfg: PrometheusConfig) -> None:
        self.config = cfg
        self.apps.set_custom_apps(cfg.custom_apps)
        self.web.set_custom_sites(cfg.custom_sites)

    def _title(self, lang: str) -> str:
        return self.config.user_title_tr if lang == "tr" else self.config.user_title_en

    async def process(self, raw_text: str) -> BrainResponse:
        text = raw_text.strip()
        if not text:
            lang = "tr" if self.config.language != "en" else "en"
            return BrainResponse(
                text="Sizi dinliyorum efendim." if lang == "tr" else "I am listening, sir.",
                intent="empty",
                language=lang,
            )

        lang = (
            self.config.language
            if self.config.language in ("tr", "en") and self.config.language != "auto"
            else detect_language(text)
        )
        # Auto-adapt if user clearly speaks English while config is default tr
        detected = detect_language(text, default=lang)
        if detected != lang and self.config.language == "auto":
            lang = detected
        elif detected == "en" and any(
            w in normalize_ascii(text).split()
            for w in ("open", "close", "search", "weather", "shutdown", "restart", "hello")
        ):
            lang = "en"

        norm = normalize_ascii(text)
        title = self._title(lang)

        # 0. Pending power confirmation check
        if self.pending_power_action:
            if norm in ("evet", "onayla", "onayliyorum", "tamam", "yes", "confirm", "yap"):
                act = self.pending_power_action
                self.pending_power_action = None
                res = self.sys.power_action(act, full_authority=self.config.full_authority)
                msg = (
                    f"{act} işlemi başlatıldı, {title}."
                    if res.get("ok")
                    else res.get("error", "İşlem başarısız.")
                )
                return self._finish(text, "power_confirmed", msg, res.get("ok", False), lang, res)
            if norm in ("hayir", "iptal", "vazgec", "no", "cancel"):
                self.pending_power_action = None
                msg = f"İşlem iptal edildi, {title}." if lang == "tr" else f"Action cancelled, {title}."
                return self._finish(text, "power_cancelled", msg, True, lang)

        # 1. Custom user-defined commands
        for trigger, action_cmd in self.config.custom_commands.items():
            if normalize_ascii(trigger) == norm:
                res = self.sys.run_shell(action_cmd, full_authority=self.config.full_authority)
                msg = (
                    f"Özel komut '{trigger}' çalıştırıldı, {title}."
                    if res.get("ok")
                    else f"Özel komut hatası: {res.get('error')}"
                )
                return self._finish(text, "custom_command", msg, res.get("ok", False), lang, res)

        # 2. Greetings & Identity
        if re.match(
            r"^(merhaba|selam|gunaydin|iyi aksamlar|iyi geceler|nasilsin|ne haber|hey|hello|hi|good morning|how are you)\b",
            norm,
        ):
            msg = (
                f"Merhaba {title}. Tüm sistemler çevrimiçi ve tam yetkiyle emrinizdeyim."
                if lang == "tr"
                else f"Hello {title}. All systems are online and at your command."
            )
            return self._finish(text, "greeting", msg, True, lang)

        if any(p in norm for p in ("kimsin", "adin ne", "sen nesin", "who are you", "your name")):
            msg = (
                f"Ben Prometheus, {title}. Bilgisayarınızı yönetmek, her programı ve siteyi açmak, "
                "sesli komutlarınızı anında yerine getirmek için tasarlanmış tamamen ücretsiz kişisel yapay zeka asistanınızım."
                if lang == "tr"
                else f"I am Prometheus, {title}. Your completely free personal AI assistant built to control your computer, launch any app, and browse any site."
            )
            return self._finish(text, "identity", msg, True, lang)

        if any(p in norm for p in ("tesekkur", "sag ol", "eyvallah", "thank you", "thanks")):
            msg = (
                f"Her zaman {title}. Başka bir emriniz var mı?"
                if lang == "tr"
                else f"Always at your service, {title}."
            )
            return self._finish(text, "thanks", msg, True, lang)

        # 3. Full Authority Shell Command
        shell_match = re.match(
            r"^(?:komut calistir|terminalde calistir|powershell|cmd|bash|shell|run command|execute)\s*:?\s+(.+)$",
            norm,
        )
        if shell_match:
            # Extract original casing after trigger from raw text
            idx = text.find(":")
            raw_cmd = text[idx + 1 :].strip() if idx != -1 else re.sub(
                r"^(?:komut\s+çalıştır|komut\s+calistir|terminalde\s+çalıştır|powershell|cmd|bash|shell|run\s+command|execute)\s+",
                "",
                text,
                flags=re.IGNORECASE,
            ).strip()
            res = self.sys.run_shell(raw_cmd, full_authority=self.config.full_authority)
            if res.get("ok"):
                out = res.get("output", "")
                preview = out[:240] + ("..." if len(out) > 240 else "")
                msg = f"Komut çalıştırıldı {title}. Çıktı: {preview}"
            else:
                msg = f"Komut çalıştırılamadı {title}: {res.get('error') or res.get('output')}"
            return self._finish(text, "shell_exec", msg, res.get("ok", False), lang, res)

        # 4. Time & Date
        if any(p in norm for p in ("saat kac", "saati soyle", "what time", "current time")):
            return self._finish(text, "time", get_current_time_str(lang), True, lang)

        if any(
            p in norm
            for p in ("tarih ne", "bugun gunlerden ne", "bugun ayin kaci", "hangi gundeyiz", "what date", "today s date", "what day is")
        ):
            return self._finish(text, "date", get_current_date_str(lang), True, lang)

        # 5. Timers
        timer_match = re.search(
            r"(?:(\d+|bir|iki|uc|üç|dort|dört|bes|beş|on|onbes|yirmi|otuz)\s*(saniye|sn|dakika|dk|saat|second|seconds|minute|minutes|hour|hours))\s*(?:sonra|icinde|icin)?\s*(?:zamanlayici|sayac|alarm|timer|hatirlat)?",
            norm,
        )
        if timer_match and any(w in norm for w in ("zamanlayici", "sayac", "alarm", "timer", "kur", "baslat", "hatirlat")):
            num = extract_number(timer_match.group(1)) or 1
            unit = timer_match.group(2)
            mult = 1
            if unit.startswith(("dakika", "dk", "min")):
                mult = 60
            elif unit.startswith(("saat", "hour")):
                mult = 3600
            secs = max(1, int(num * mult))
            t = self.memory.add_timer(label=text, duration_seconds=secs)
            msg = (
                f"{int(num)} {unit} için zamanlayıcı kuruldu, {title}."
                if lang == "tr"
                else f"Timer set for {int(num)} {unit}, {title}."
            )
            return self._finish(text, "set_timer", msg, True, lang, t)

        # 6. Notes
        if re.match(r"^(not al|not ekle|kaydet|take a note|add note|note)\b", norm):
            content = re.sub(
                r"^(?:not al|not ekle|kaydet|take a note|add note|note)\s*:?\s*",
                "",
                text,
                flags=re.IGNORECASE,
            ).strip()
            if content:
                note = self.memory.add_note(content)
                msg = f"Not kaydedildi {title}: {content}" if lang == "tr" else f"Note saved, {title}."
                return self._finish(text, "add_note", msg, True, lang, note)

        if any(p in norm for p in ("notlarimi oku", "notlari listele", "notlarim", "read notes", "list notes")):
            notes = self.memory.list_notes(limit=10)
            if not notes:
                msg = f"Kayıtlı notunuz bulunmuyor {title}." if lang == "tr" else f"You have no saved notes, {title}."
            else:
                joined = "; ".join(f"{i+1}) {n['content']}" for i, n in enumerate(notes[:5]))
                msg = f"Son notlarınız {title}: {joined}"
            return self._finish(text, "list_notes", msg, True, lang, {"notes": notes})

        if any(p in norm for p in ("notlari sil", "notlari temizle", "clear notes")):
            cnt = self.memory.clear_notes()
            msg = f"{cnt} adet not temizlendi, {title}."
            return self._finish(text, "clear_notes", msg, True, lang, {"deleted": cnt})

        # 7. Volume & Media Controls
        if any(p in norm for p in ("sessize al", "sesi kapat", "sustur", "mute")):
            res = self.sys.set_volume(action="mute")
            msg = f"Sistem sesi kapatıldı, {title}." if lang == "tr" else f"System muted, {title}."
            return self._finish(text, "volume_mute", msg, res.get("ok", False), lang, res)

        if any(p in norm for p in ("sesi geri ac", "sessizden cikar", "unmute")):
            res = self.sys.set_volume(action="unmute")
            msg = f"Ses tekrar açıldı, {title}." if lang == "tr" else f"System unmuted, {title}."
            return self._finish(text, "volume_unmute", msg, res.get("ok", False), lang, res)

        if any(w in norm for w in ("ses", "sesi", "volume")):
            num = extract_number(text)
            if num is not None:
                lvl = max(0, min(100, int(num)))
                res = self.sys.set_volume(level=lvl, action="set")
                msg = f"Ses seviyesi yüzde {lvl} olarak ayarlandı, {title}." if lang == "tr" else f"Volume set to {lvl}%, {title}."
                return self._finish(text, "volume_set", msg, res.get("ok", False), lang, res)
            if any(w in norm for w in ("artir", "yukselt", "ac", "up", "increase")):
                res = self.sys.set_volume(action="up")
                msg = f"Ses yükseltildi, {title}." if lang == "tr" else f"Volume increased, {title}."
                return self._finish(text, "volume_up", msg, res.get("ok", False), lang, res)
            if any(w in norm for w in ("kis", "azalt", "dusur", "down", "decrease")):
                res = self.sys.set_volume(action="down")
                msg = f"Ses kısıldı, {title}." if lang == "tr" else f"Volume decreased, {title}."
                return self._finish(text, "volume_down", msg, res.get("ok", False), lang, res)

        if any(p in norm for p in ("muzigi durdur", "duraklat", "devam et", "oynat durdur", "play pause", "pause music")):
            res = self.sys.media_control("play_pause")
            msg = f"Medya oynatma durumu değiştirildi, {title}."
            return self._finish(text, "media_play_pause", msg, res.get("ok", False), lang, res)

        if any(p in norm for p in ("sonraki sarki", "sarkiyi gec", "next track", "next song")):
            res = self.sys.media_control("next")
            return self._finish(text, "media_next", f"Sonraki parçaya geçildi, {title}.", res.get("ok", False), lang, res)

        if any(p in norm for p in ("onceki sarki", "previous track", "previous song")):
            res = self.sys.media_control("prev")
            return self._finish(text, "media_prev", f"Önceki parçaya dönüldü, {title}.", res.get("ok", False), lang, res)

        # 8. Screenshot
        if any(p in norm for p in ("ekran goruntusu", "ss al", "screenshot")):
            res = self.sys.take_screenshot()
            msg = (
                f"Ekran görüntüsü alındı ve kaydedildi, {title}."
                if res.get("ok")
                else f"Ekran görüntüsü alınamadı: {res.get('error')}"
            )
            return self._finish(text, "screenshot", msg, res.get("ok", False), lang, res)

        # 9. System Telemetry & Running/Installed Apps
        if any(p in norm for p in ("sistem durumu", "sistem bilgisi", "cpu kac", "ram kac", "system status", "telemetry")):
            t = self.sys.get_telemetry()
            msg = (
                f"Sistem durumu {title}: İşlemci kullanımı yüzde {t['cpu_percent']}, "
                f"bellek kullanımı yüzde {t['ram_percent']} ({t['ram_used_gb']} GB / {t['ram_total_gb']} GB), "
                f"disk doluluğu yüzde {t['disk']['percent']}."
            )
            return self._finish(text, "telemetry", msg, True, lang, t)

        if any(p in norm for p in ("yuklu uygulamalar", "programlari listele", "installed apps")):
            apps = self.apps.list_installed(limit=40)
            names = ", ".join(a["name"] for a in apps[:8])
            msg = f"Sistemde {len(apps)} üzeri uygulama tespit edildi {title}. Örnekler: {names}."
            return self._finish(text, "list_apps", msg, True, lang, {"apps": apps})

        if any(p in norm for p in ("calisan uygulamalar", "acik programlar", "running processes")):
            procs = self.sys.list_top_processes(limit=10)
            names = ", ".join(p["name"] for p in procs[:6])
            msg = f"Şu an en çok kaynak kullanan süreçler {title}: {names}."
            return self._finish(text, "list_processes", msg, True, lang, {"processes": procs})

        # 10. Power Actions (Lock / Sleep / Restart / Shutdown)
        power_map = [
            (("bilgisayari kilitle", "ekrani kilitle", "lock screen", "lock pc"), "lock"),
            (("uyku modu", "uyku moduna", "bilgisayari uyut", "sleep pc"), "sleep"),
            (("yeniden baslat", "restart pc", "reboot"), "restart"),
            (("bilgisayari kapat", "sistemi kapat", "shutdown"), "shutdown"),
        ]
        for phrases, action in power_map:
            if any(p in norm for p in phrases):
                if action in ("restart", "shutdown") and self.config.confirm_power_actions:
                    self.pending_power_action = action
                    tr_label = "yeniden başlatmamı" if action == "restart" else "kapatmamı"
                    msg = f"Güvenlik onayı: Bilgisayarı {tr_label} onaylıyor musunuz {title}? Evet veya hayır deyin."
                    return self._finish(text, "power_confirm_prompt", msg, True, lang, {"pending": action})
                res = self.sys.power_action(action, full_authority=self.config.full_authority)
                msg = f"{action} komutu uygulandı, {title}." if res.get("ok") else res.get("error", "Hata")
                return self._finish(text, f"power_{action}", msg, res.get("ok", False), lang, res)

        # 11. Weather
        if any(p in norm for p in ("hava durumu", "hava nasil", "weather")):
            city = "Istanbul"
            m = re.search(r"([a-zA-ZçğıöşüÇĞİÖŞÜ]+)(?:'?(?:da|de|ta|te|in|for))?\s+(?:hava|weather)", text, re.IGNORECASE)
            if m and normalize_ascii(m.group(1)) not in ("bugun", "yarin", "simdi", "su", "an", "what", "the"):
                city = m.group(1)
            else:
                m2 = re.search(r"(?:weather\s+in|hava\s+durumu)\s+([a-zA-ZçğıöşüÇĞİÖŞÜ]+)", text, re.IGNORECASE)
                if m2:
                    city = m2.group(1)
            w = await fetch_weather(city=city, lang=lang)
            if w.get("ok"):
                msg = (
                    f"{w['city']} için hava şu an {w['temp']} derece {title}. "
                    f"Hissedilen {w['feels_like']} derece, nem yüzde {w['humidity']}, rüzgar {w['wind']} km/s."
                )
            else:
                msg = f"Hava durumu alınamadı {title}: {w.get('error')}"
            return self._finish(text, "weather", msg, w.get("ok", False), lang, w)

        # 12. Calculator
        calc_val = calculate_expression(text)
        if calc_val is not None:
            msg = f"Sonuç {calc_val}, {title}." if lang == "tr" else f"The result is {calc_val}, {title}."
            return self._finish(text, "calculate", msg, True, lang, {"result": calc_val})

        # 13. In-Site Search (e.g. "youtube'da lofi çal", "google'da python ara", "haritalarda kadıköy ara")
        in_site = self._parse_in_site_search(text)
        if in_site:
            platform_name, query = in_site
            url = self.web.build_search_url(query, platform_name=platform_name, lang=lang)
            res = self.web.open_url(url)
            msg = (
                f"{platform_name.capitalize()} üzerinde '{query}' aranıyor, {title}."
                if lang == "tr"
                else f"Searching '{query}' on {platform_name.capitalize()}, {title}."
            )
            return self._finish(
                text,
                "web_search",
                msg,
                True,
                lang,
                res,
                client_action=res.get("client_action"),
            )

        # 14. Open Folder
        if any(p in norm for p in ("masaustunu ac", "indirilenleri ac", "indirilenler klasoru", "belgeleri ac", "open downloads", "open desktop", "open documents")):
            folder_key = "desktop"
            if "indir" in norm or "download" in norm:
                folder_key = "downloads"
            elif "belge" in norm or "document" in norm:
                folder_key = "documents"
            res = self.sys.open_folder(folder_key)
            msg = f"Klasör açıldı, {title}." if res.get("ok") else res.get("error", "Klasör açılamadı.")
            return self._finish(text, "open_folder", msg, res.get("ok", False), lang, res)

        # 15. Close App
        close_target = self._extract_close_target(text)
        if close_target:
            res = self.apps.close_app(close_target)
            msg = (
                f"{close_target} kapatıldı, {title}."
                if res.get("ok")
                else res.get("error", f"{close_target} kapatılamadı.")
            )
            return self._finish(text, "close_app", msg, res.get("ok", False), lang, res)

        # 16. Open Website OR Application (Smart Disambiguation!)
        open_target, explicit_kind = self._extract_open_target(text)
        if open_target:
            return self._handle_open_target(text, open_target, explicit_kind, lang, title)

        # 17. Direct URL or Domain typed alone (e.g. "github.com" or "youtube")
        if re.match(r"^(https?://)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,}", text.strip()):
            url = self.web.resolve_url(text.strip())
            if url:
                res = self.web.open_url(url)
                return self._finish(
                    text, "open_website", f"{url} açılıyor, {title}.", True, lang, res, res.get("client_action")
                )

        # 18. Generic Search ("ara: ...", "... google'da ara", "... araştır")
        search_m = re.match(r"^(?:ara|arastir|search|google)\s*:?\s+(.+)$", norm)
        if search_m:
            q = re.sub(r"^(?:ara|araştır|arastir|search|google)\s*:?\s*", "", text, flags=re.IGNORECASE).strip()
            url = self.web.build_search_url(q, "google", lang)
            res = self.web.open_url(url)
            msg = f"Google'da '{q}' aranıyor, {title}."
            return self._finish(text, "web_search", msg, True, lang, res, res.get("client_action"))

        # 19. Wikipedia Knowledge Questions ("... nedir", "... kimdir", "what is ...")
        wiki_m = re.match(
            r"^(.+?)\s+(?:nedir|kimdir|ne demek|hakkinda bilgi)\??$",
            norm,
        ) or re.match(r"^(?:what is|who is|tell me about)\s+(.+?)\??$", norm)
        if wiki_m:
            topic = re.sub(
                r"\s*(?:nedir|kimdir|ne demek|hakkında bilgi|hakkinda bilgi|\?)\s*$",
                "",
                text,
                flags=re.IGNORECASE,
            )
            topic = re.sub(r"^(?:what is|who is|tell me about)\s+", "", topic, flags=re.IGNORECASE).strip()
            wk = await fetch_wikipedia_summary(topic, lang=lang)
            if wk.get("ok"):
                return self._finish(text, "knowledge_wiki", wk["summary"], True, lang, wk)

        # 20. Free Local Ollama LLM Fallback
        if self.config.ollama_enabled:
            ai_reply = await query_ollama(
                text,
                ollama_url=self.config.ollama_url,
                model=self.config.ollama_model,
                lang=lang,
            )
            if ai_reply:
                return self._finish(text, "ollama_chat", ai_reply, True, lang)

        # 21. Graceful Fallback
        fallback = (
            f"Anladım {title}, ancak '{text}' için yerel bir komut eşleşmesi bulamadım. "
            "İsterseniz 'Google'da ... ara', '... sitesini aç' veya '... uygulamasını aç' diyebilirsiniz."
            if lang == "tr"
            else f"Understood {title}, I didn't find a direct local command for '{text}'. Try 'open ...' or 'search ...'."
        )
        return self._finish(text, "fallback", fallback, True, lang)

    def _parse_in_site_search(self, text: str) -> Optional[tuple[str, str]]:
        # Pattern: "<site>'da <query> ara/çal/aç/bul"
        platforms = (
            "youtube|yutup|google|wikipedia|vikipedi|wiki|github|haritalar|harita|"
            "maps|ceviri|çeviri|translate|spotify|trendyol|hepsiburada|amazon|reddit"
        )
        m = re.match(
            rf"^({platforms})(?:'?(?:da|de|ta|te|dan|den))?\s+(.+?)\s+(?:ara|arat|bul|cal|çal|oynat|ac|aç|izle|cevir|çevir|search)$",
            text.strip(),
            flags=re.IGNORECASE,
        )
        if m:
            return m.group(1), m.group(2).strip()

        # Pattern: "search <query> on <site>"
        m2 = re.match(
            rf"^(?:search|play|find)\s+(.+?)\s+(?:on|in)\s+({platforms})$",
            text.strip(),
            flags=re.IGNORECASE,
        )
        if m2:
            return m2.group(2), m2.group(1).strip()
        return None

    def _extract_close_target(self, text: str) -> Optional[str]:
        m = re.match(
            r"^(?:kapat|sonlandir|sonlandır|durdur|close|kill|exit|quit)\s+(.+)$",
            text.strip(),
            flags=re.IGNORECASE,
        )
        if m:
            target = clean_target_phrase(m.group(1))
            if normalize_ascii(target) not in ("bilgisayari", "sistemi", "pc", "sesi", "ses"):
                return target

        m2 = re.match(
            r"^(.+?)\s+(?:kapat|sonlandir|sonlandır|kapatir misin|kapatır mısın)$",
            text.strip(),
            flags=re.IGNORECASE,
        )
        if m2:
            target = clean_target_phrase(m2.group(1))
            if normalize_ascii(target) not in ("bilgisayari", "sistemi", "pc", "sesi", "ses"):
                return target
        return None

    def _extract_open_target(self, text: str) -> tuple[Optional[str], str]:
        """Returns (target_phrase, explicit_kind: 'site'|'app'|'auto')."""
        low = tr_lower(text.strip())
        explicit_kind = "auto"
        if any(k in low for k in ("site", "sayfa", "web", "adres", ".com", ".org", ".net", ".tr", ".io", ".ai", "http", "gir", "git")):
            explicit_kind = "site"
        elif any(k in low for k in ("program", "uygulama", "app", "başlat", "baslat", "çalıştır", "calistir")):
            explicit_kind = "app"

        # Prefix patterns: "aç youtube", "open chrome", "gir github.com"
        m_pre = re.match(
            r"^(?:aç|ac|gir|git|başlat|baslat|çalıştır|calistir|open|launch|start|visit|go to)\s+(.+)$",
            text.strip(),
            flags=re.IGNORECASE,
        )
        if m_pre:
            return clean_target_phrase(m_pre.group(1)), explicit_kind

        # Suffix patterns: "youtube'u aç", "youtube'a gir", "discord başlat", "chrome.exe aç"
        m_suf = re.match(
            r"^(.+?)\s+(?:aç|ac|gir|git|başlat|baslat|çalıştır|calistir|açar mısın|acar misin|girer misin)$",
            text.strip(),
            flags=re.IGNORECASE,
        )
        if m_suf:
            return clean_target_phrase(m_suf.group(1)), explicit_kind

        return None, "auto"

    def _handle_open_target(
        self,
        raw_text: str,
        target: str,
        explicit_kind: str,
        lang: str,
        title: str,
    ) -> BrainResponse:
        norm = normalize_ascii(target)
        has_domain = bool(re.search(r"\.[a-z]{2,}", target.lower()))

        # Decide whether this is a website or a desktop app
        is_known_site = norm in KNOWN_SITES or norm in {normalize_ascii(k) for k in self.config.custom_sites}
        app_entry = self.apps.resolve_app(target)

        # If explicitly site, or has domain, or is primarily a web service (and not explicitly app)
        if explicit_kind == "site" or has_domain or (is_known_site and explicit_kind != "app" and app_entry is None):
            url = self.web.resolve_url(target, allow_com_fallback=True)
            if url:
                res = self.web.open_url(url)
                msg = (
                    f"{target} açılıyor, {title}."
                    if lang == "tr"
                    else f"Opening {target}, {title}."
                )
                return self._finish(
                    raw_text, "open_website", msg, True, lang, res, res.get("client_action")
                )

        # Try launching desktop app
        if app_entry is not None or explicit_kind == "app":
            res = self.apps.launch(target)
            if res.get("ok"):
                sim_note = " (Önizleme/headless ortamda simüle edildi)" if res.get("simulated") else ""
                msg = (
                    f"{res['app']} başlatılıyor, {title}.{sim_note}"
                    if lang == "tr"
                    else f"Launching {res['app']}, {title}.{sim_note}"
                )
                return self._finish(raw_text, "open_app", msg, True, lang, res)
            # If app launch failed but a known website matches (e.g. Discord / Spotify / WhatsApp web)
            if is_known_site:
                url = self.web.resolve_url(target, allow_com_fallback=False)
                if url:
                    web_res = self.web.open_url(url)
                    msg = f"Masaüstü uygulaması bulunamadı, web sürümü açılıyor: {url}, {title}."
                    return self._finish(
                        raw_text, "open_website", msg, True, lang, web_res, web_res.get("client_action")
                    )
            return self._finish(raw_text, "open_app_failed", res.get("error", "Uygulama açılamadı."), False, lang, res)

        # Fallback: try site resolution if user said e.g. "reddit'i aç" or "trendyol aç"
        url = self.web.resolve_url(target, allow_com_fallback=True)
        if url:
            res = self.web.open_url(url)
            msg = f"{target} web adresi açılıyor, {title}."
            return self._finish(
                raw_text, "open_website", msg, True, lang, res, res.get("client_action")
            )

        msg = f"'{target}' adlı program veya site bulunamadı, {title}."
        return self._finish(raw_text, "open_not_found", msg, False, lang)

    def _finish(
        self,
        command: str,
        intent: str,
        response: str,
        success: bool,
        language: str,
        data: Optional[Dict[str, Any]] = None,
        client_action: Optional[Dict[str, Any]] = None,
    ) -> BrainResponse:
        self.memory.log_command(command=command, intent=intent, response=response, success=success)
        return BrainResponse(
            text=response,
            intent=intent,
            success=success,
            language=language,
            data=data or {},
            client_action=client_action,
        )
