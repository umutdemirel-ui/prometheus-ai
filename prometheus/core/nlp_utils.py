"""Turkish & English NLP utilities, wake-word matching, and number parsing."""

from __future__ import annotations

import difflib
import re
from typing import Iterable, List, Optional, Tuple


_TR_LOWER_MAP = str.maketrans({
    "İ": "i",
    "I": "ı",
    "Ş": "ş",
    "Ğ": "ğ",
    "Ü": "ü",
    "Ö": "ö",
    "Ç": "ç",
})

_TR_TO_ASCII_MAP = str.maketrans({
    "ı": "i",
    "İ": "i",
    "I": "i",
    "ş": "s",
    "Ş": "s",
    "ğ": "g",
    "Ğ": "g",
    "ü": "u",
    "Ü": "u",
    "ö": "o",
    "Ö": "o",
    "ç": "c",
    "Ç": "c",
})

_TR_SUFFIX_RE = re.compile(
    r"(?:'|’)?(nın|nin|nun|nün|yın|yin|yun|yün|dan|den|tan|ten|"
    r"nda|nde|ına|ine|una|üne|ını|ini|unu|ünü|ya|ye|yı|yi|yu|yü|"
    r"da|de|ta|te|la|le|a|e|ı|i|u|ü)$",
    re.IGNORECASE,
)

_TR_CHARS = set("çğıöşüÇĞİÖŞÜ")
_TR_HINT_WORDS = {
    "aç", "kapat", "gir", "git", "ara", "çal", "oynat", "dur", "durdur",
    "ses", "sesi", "bilgisayar", "saat", "kaç", "tarih", "hava", "durumu",
    "ekran", "görüntü", "görüntüsü", "kilitle", "uyku", "yeniden", "başlat",
    "not", "al", "hatırlat", "zamanlayıcı", "kur", "çalıştır", "komut",
    "merhaba", "selam", "nasılsın", "kimsin", "teşekkür", "yardım", "nedir",
    "kimdir", "ne", "kadar", "hesapla", "yaz", "sil", "açık", "liste",
    "uygulama", "program", "site", "dosya", "klasör", "efendim", "lütfen",
}

_TR_NUMBERS = {
    "sıfır": 0, "sifir": 0,
    "bir": 1, "iki": 2, "üç": 3, "uc": 3, "dört": 4, "dort": 4,
    "beş": 5, "bes": 5, "altı": 6, "alti": 6, "yedi": 7, "sekiz": 8,
    "dokuz": 9, "on": 10, "yirmi": 20, "otuz": 30, "kırk": 40, "kirk": 40,
    "elli": 50, "altmış": 60, "altmis": 60, "yetmiş": 70, "yetmis": 70,
    "seksen": 80, "doksan": 90, "yüz": 100, "yuz": 100, "bin": 1000,
    "yarım": 0.5, "yarim": 0.5, "buçuk": 0.5, "bucuk": 0.5,
}

_EN_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20,
    "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90, "hundred": 100,
}

_WAKE_PHONETIC_VARIANTS = {
    "prometheus", "prometyus", "prometeus", "prometius", "promethius",
    "prometus", "prametyus", "promete", "promethe", "promethes",
    "brometheus", "frometheus", "jarvis", "carvis", "cervis",
}


def tr_lower(text: str) -> str:
    return text.translate(_TR_LOWER_MAP).lower()


def normalize_ascii(text: str) -> str:
    lowered = tr_lower(text).translate(_TR_TO_ASCII_MAP)
    cleaned = re.sub(r"[^a-z0-9\s\.\-\_:/]", " ", lowered)
    return re.sub(r"\s+", " ", cleaned).strip()


def strip_turkish_suffix(token: str) -> str:
    """Strip common Turkish noun suffixes (e.g. youtube'u -> youtube, discordu -> discord)."""
    if "'" in token or "’" in token:
        base = re.split(r"['’]", token, maxsplit=1)[0]
        if len(base) >= 2:
            return base
    # Only strip attached suffix if stem stays meaningful (>= 3 chars)
    m = _TR_SUFFIX_RE.search(token)
    if m and len(token) - len(m.group(0)) >= 3:
        # Don't strip if word is a known whole word ending in vowels (like google, apple, edge, vscode)
        low = tr_lower(token)
        if low in {
            "google", "apple", "edge", "vscode", "code", "youtube", "adobe",
            "chrome", "brave", "opera", "skype", "claude", "figma", "canva",
            "office", "onenote", "sublime", "eclipse", "console", "terminal",
            "binance", "sahibinden", "hepsiburada", "wikipedia", "vikipedi",
            "insta", "instagram", "twitch", "nvidia", "spotify", "discord",
        }:
            return token
        return token[: m.start()]
    return token


def clean_target_phrase(phrase: str) -> str:
    """Clean target app or site name from polite words and Turkish suffixes."""
    text = phrase.strip().strip("\"'.,!?")
    # Remove trailing polite/filler tokens
    text = re.sub(
        r"\b(lütfen|lutfen|please|hemen|şimdi|simdi|now|programını|programini|"
        r"uygulamasını|uygulamasini|sitesini|sayfasını|sayfasini|tarayıcısını)\b",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s+", " ", text).strip()
    parts = text.split()
    if parts:
        parts[-1] = strip_turkish_suffix(parts[-1])
    return " ".join(parts).strip()


def detect_language(text: str, default: str = "tr") -> str:
    if any(ch in _TR_CHARS for ch in text):
        return "tr"
    tokens = set(normalize_ascii(text).split())
    tr_ascii_hints = {normalize_ascii(w) for w in _TR_HINT_WORDS}
    if tokens & tr_ascii_hints:
        return "tr"
    en_hints = {
        "open", "close", "launch", "start", "search", "play", "volume",
        "mute", "unmute", "what", "time", "weather", "lock", "shutdown",
        "restart", "sleep", "screenshot", "hello", "hi", "help", "run",
    }
    if tokens & en_hints:
        return "en"
    return default if default in ("tr", "en") else "tr"


def extract_number(text: str) -> Optional[float]:
    """Extract numeric value from digits or Turkish/English number words."""
    m = re.search(r"-?\d+(?:[.,]\d+)?", text)
    if m:
        return float(m.group(0).replace(",", "."))

    tokens = normalize_ascii(text).split()
    total = 0.0
    found = False
    for tok in tokens:
        if tok in _TR_NUMBERS:
            val = _TR_NUMBERS[tok]
            if val == 100 and total > 0:
                total *= 100
            elif val == 1000 and total > 0:
                total *= 1000
            else:
                total += val
            found = True
        elif tok in _EN_NUMBERS:
            val = _EN_NUMBERS[tok]
            if val == 100 and total > 0:
                total *= 100
            else:
                total += val
            found = True
    return total if found else None


def fuzzy_ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, normalize_ascii(a), normalize_ascii(b)).ratio()


def match_wake_word(
    transcript: str,
    wake_words: Optional[Iterable[str]] = None,
) -> Tuple[bool, str]:
    """Check if transcript contains a wake word (exact or phonetic fuzzy).

    Returns (matched, remaining_command_text).
    """
    raw = transcript.strip()
    if not raw:
        return False, ""

    candidates = set(_WAKE_PHONETIC_VARIANTS)
    if wake_words:
        for w in wake_words:
            candidates.add(normalize_ascii(w))

    # First check multi-word prefixes like "hey prometheus", "ok prometheus"
    norm = normalize_ascii(raw)
    words_raw = raw.split()
    words_norm = [normalize_ascii(w) for w in words_raw]

    for prefix in ("hey", "ok", "okay", "merhaba", "selam", "alo", "yo"):
        if len(words_norm) >= 2 and words_norm[0] == prefix:
            second = re.sub(r"[^a-z]", "", words_norm[1])
            if _is_wake_token(second, candidates):
                rest = " ".join(words_raw[2:]).lstrip(" ,.:;!?-")
                return True, rest

    # Check if the first word or any early word is the wake word
    for idx in range(min(3, len(words_norm))):
        tok = re.sub(r"[^a-z]", "", words_norm[idx])
        if _is_wake_token(tok, candidates):
            rest_tokens = words_raw[idx + 1 :]
            rest = " ".join(rest_tokens).lstrip(" ,.:;!?-")
            # Also support "aç prometheus" or trailing wake word if nothing after
            if not rest and idx > 0:
                rest = " ".join(words_raw[:idx]).strip(" ,.:;!?-")
            return True, rest

    # Whole phrase check
    compact = re.sub(r"[^a-z]", "", norm)
    if _is_wake_token(compact, candidates):
        return True, ""

    return False, raw


def _is_wake_token(tok: str, candidates: set[str]) -> bool:
    if not tok or len(tok) < 5:
        return False
    if tok in candidates:
        return True
    for target in ("prometheus", "prometyus", "jarvis"):
        if difflib.SequenceMatcher(None, tok, target).ratio() >= 0.76:
            return True
    return False
