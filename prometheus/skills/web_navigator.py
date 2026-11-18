"""Web navigation, site resolution, and in-site search for Prometheus."""

from __future__ import annotations

import difflib
import os
import platform
import re
import urllib.parse
import webbrowser
from typing import Any, Dict, Optional

from prometheus.core.nlp_utils import clean_target_phrase, normalize_ascii


KNOWN_SITES: Dict[str, str] = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "yutup": "https://www.youtube.com",
    "github": "https://github.com",
    "chatgpt": "https://chatgpt.com",
    "openai": "https://chatgpt.com",
    "claude": "https://claude.ai",
    "gemini": "https://gemini.google.com",
    "arena": "https://arena.ai",
    "lmarena": "https://lmarena.ai",
    "perplexity": "https://www.perplexity.ai",
    "deepseek": "https://chat.deepseek.com",
    "netflix": "https://www.netflix.com",
    "spotify": "https://open.spotify.com",
    "twitch": "https://www.twitch.tv",
    "kick": "https://kick.com",
    "instagram": "https://www.instagram.com",
    "insta": "https://www.instagram.com",
    "twitter": "https://x.com",
    "x": "https://x.com",
    "reddit": "https://www.reddit.com",
    "linkedin": "https://www.linkedin.com",
    "facebook": "https://www.facebook.com",
    "tiktok": "https://www.tiktok.com",
    "whatsapp": "https://web.whatsapp.com",
    "whatsapp web": "https://web.whatsapp.com",
    "discord": "https://discord.com/app",
    "telegram": "https://web.telegram.org",
    "gmail": "https://mail.google.com",
    "eposta": "https://mail.google.com",
    "mail": "https://mail.google.com",
    "google drive": "https://drive.google.com",
    "drive": "https://drive.google.com",
    "maps": "https://maps.google.com",
    "google maps": "https://maps.google.com",
    "haritalar": "https://maps.google.com",
    "harita": "https://maps.google.com",
    "translate": "https://translate.google.com",
    "ceviri": "https://translate.google.com",
    "google ceviri": "https://translate.google.com",
    "wikipedia": "https://tr.wikipedia.org",
    "vikipedi": "https://tr.wikipedia.org",
    "wiki": "https://tr.wikipedia.org",
    "trendyol": "https://www.trendyol.com",
    "hepsiburada": "https://www.hepsiburada.com",
    "sahibinden": "https://www.sahibinden.com",
    "amazon": "https://www.amazon.com.tr",
    "n11": "https://www.n11.com",
    "yemeksepeti": "https://www.yemeksepeti.com",
    "getir": "https://getir.com",
    "imdb": "https://www.imdb.com",
    "stackoverflow": "https://stackoverflow.com",
    "stack overflow": "https://stackoverflow.com",
    "notion": "https://www.notion.so",
    "figma": "https://www.figma.com",
    "canva": "https://www.canva.com",
    "vercel": "https://vercel.com",
    "cloudflare": "https://dash.cloudflare.com",
    "udemy": "https://www.udemy.com",
    "coursera": "https://www.coursera.org",
    "medium": "https://medium.com",
    "eksisozluk": "https://eksisozluk.com",
    "eksi sozluk": "https://eksisozluk.com",
    "eksi": "https://eksisozluk.com",
    "haberler": "https://www.haberler.com",
    "trt haber": "https://www.trthaber.com",
    "ntv": "https://www.ntv.com.tr",
    "bbc": "https://www.bbc.com",
    "cnn": "https://www.cnn.com",
    "steam": "https://store.steampowered.com",
    "epic games": "https://store.epicgames.com",
    "binance": "https://www.binance.com",
    "tradingview": "https://www.tradingview.com",
    "huggingface": "https://huggingface.co",
    "hugging face": "https://huggingface.co",
    "pypi": "https://pypi.org",
    "npm": "https://www.npmjs.com",
}

_DOMAIN_RE = re.compile(
    r"^(?:https?://)?(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:/[^\s]*)?$"
)


class WebNavigator:
    def __init__(self, custom_sites: Optional[Dict[str, str]] = None) -> None:
        self.custom_sites: Dict[str, str] = custom_sites or {}

    def set_custom_sites(self, custom_sites: Dict[str, str]) -> None:
        self.custom_sites = dict(custom_sites)

    def has_desktop_browser(self) -> bool:
        sys_name = platform.system().lower()
        if sys_name in ("windows", "darwin"):
            return True
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

    def resolve_url(self, target: str, allow_com_fallback: bool = True) -> Optional[str]:
        raw = target.strip().strip("\"'.,!?")
        if not raw:
            return None

        # Direct http/https URL
        if raw.startswith(("http://", "https://")):
            return raw

        cleaned = clean_target_phrase(raw)
        norm = normalize_ascii(cleaned)

        # Custom sites first
        for alias, url in self.custom_sites.items():
            if normalize_ascii(alias) == norm:
                return url if url.startswith(("http://", "https://")) else f"https://{url}"

        # Exact domain in text (e.g. "github.com", "docs.python.org/3/")
        if _DOMAIN_RE.match(cleaned):
            return f"https://{cleaned}"
        # Also check raw in case suffix stripping touched something
        first_tok = raw.split()[0].strip(",.!?")
        if _DOMAIN_RE.match(first_tok):
            return f"https://{first_tok}"

        # Known sites exact
        if norm in KNOWN_SITES:
            return KNOWN_SITES[norm]

        # Fuzzy match on known sites
        close = difflib.get_close_matches(norm, list(KNOWN_SITES.keys()), n=1, cutoff=0.82)
        if close:
            return KNOWN_SITES[close[0]]

        if allow_com_fallback and norm and " " not in norm and len(norm) >= 2:
            return f"https://www.{norm}.com"

        return None

    def build_search_url(self, query: str, platform_name: str = "google", lang: str = "tr") -> str:
        q = urllib.parse.quote_plus(query.strip())
        p = normalize_ascii(platform_name)
        if p in ("youtube", "yutup", "yt"):
            return f"https://www.youtube.com/results?search_query={q}"
        if p in ("wikipedia", "vikipedi", "wiki"):
            sub = "tr" if lang == "tr" else "en"
            return f"https://{sub}.wikipedia.org/wiki/Special:Search?search={q}"
        if p in ("github",):
            return f"https://github.com/search?q={q}"
        if p in ("maps", "google maps", "harita", "haritalar"):
            return f"https://www.google.com/maps/search/{q}"
        if p in ("translate", "ceviri", "google ceviri"):
            return f"https://translate.google.com/?sl=auto&tl={'en' if lang == 'tr' else 'tr'}&text={q}"
        if p in ("spotify",):
            return f"https://open.spotify.com/search/{urllib.parse.quote(query.strip())}"
        if p in ("trendyol",):
            return f"https://www.trendyol.com/sr?q={q}"
        if p in ("hepsiburada",):
            return f"https://www.hepsiburada.com/ara?q={q}"
        if p in ("amazon",):
            return f"https://www.amazon.com.tr/s?k={q}"
        if p in ("reddit",):
            return f"https://www.reddit.com/search/?q={q}"
        if p in ("duckduckgo",):
            return f"https://duckduckgo.com/?q={q}"
        return f"https://www.google.com/search?q={q}"

    def open_url(self, url: str) -> Dict[str, Any]:
        opened_locally = False
        if self.has_desktop_browser():
            try:
                opened_locally = webbrowser.open(url, new=2)
            except Exception:
                opened_locally = False
        return {
            "ok": True,
            "url": url,
            "opened_locally": opened_locally,
            "client_action": {"type": "open_url", "url": url},
        }
