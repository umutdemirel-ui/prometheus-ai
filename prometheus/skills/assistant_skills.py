"""Productivity, calculation, weather, Wikipedia, and free local Ollama skills."""

from __future__ import annotations

import ast
import math
import operator
import re
from datetime import datetime
from typing import Any, Dict, Optional

import httpx


_TR_DAYS = {
    0: "Pazartesi",
    1: "Salı",
    2: "Çarşamba",
    3: "Perşembe",
    4: "Cuma",
    5: "Cumartesi",
    6: "Pazar",
}

_TR_MONTHS = {
    1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan",
    5: "Mayıs", 6: "Haziran", 7: "Temmuz", 8: "Ağustos",
    9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık",
}

_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def get_current_time_str(lang: str = "tr") -> str:
    now = datetime.now()
    if lang == "tr":
        return f"Saat {now.strftime('%H:%M')}."
    return f"It is {now.strftime('%I:%M %p')}."


def get_current_date_str(lang: str = "tr") -> str:
    now = datetime.now()
    if lang == "tr":
        day_name = _TR_DAYS[now.weekday()]
        month_name = _TR_MONTHS[now.month]
        return f"Bugün {now.day} {month_name} {now.year}, {day_name}."
    return now.strftime("Today is %A, %B %d, %Y.")


def _eval_ast(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval_ast(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_eval_ast(node.left), _eval_ast(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_eval_ast(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        fn_map = {
            "sqrt": math.sqrt,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "abs": abs,
            "round": round,
        }
        if node.func.id in fn_map and len(node.args) == 1:
            return float(fn_map[node.func.id](_eval_ast(node.args[0])))
    if isinstance(node, ast.Name):
        if node.id == "pi":
            return math.pi
        if node.id == "e":
            return math.e
    raise ValueError("Desteklenmeyen ifade")


def calculate_expression(text: str) -> Optional[float]:
    expr = text.lower().strip()
    expr = re.sub(
        r"\b(hesapla|kaçtır|kactir|kaç|kac|eder|nedir|olur|calculate|what|is|equals)\b",
        " ",
        expr,
    )
    replacements = {
        "artı": "+", "arti": "+", "plus": "+",
        "eksi": "-", "minus": "-",
        "çarpı": "*", "carpi": "*", "kere": "*", "times": "*",
        "bölü": "/", "bolu": "/", "divided by": "/",
        "üssü": "**", "ussu": "**", "^": "**",
        ",": ".",
    }
    for k, v in replacements.items():
        expr = re.sub(rf"\b{re.escape(k)}\b" if k.isalpha() else re.escape(k), f" {v} ", expr)
    expr = re.sub(r"(?<=\d)\s*x\s*(?=\d)", " * ", expr)

    # Extract math-like expression
    expr = re.sub(r"[^0-9\+\-\*/\.\(\)\s%a-zA-Z]", " ", expr).strip()
    if not expr or not any(c.isdigit() for c in expr):
        return None
    # Require at least one math operator or function so plain numbers like "5" don't trigger calculator
    if not re.search(r"[\+\-\*/%]|sqrt|sin|cos|tan", expr):
        return None
    try:
        tree = ast.parse(expr, mode="eval")
        val = _eval_ast(tree)
        if abs(val - round(val)) < 1e-9:
            return int(round(val))
        return round(val, 4)
    except Exception:
        return None


async def fetch_weather(city: str = "Istanbul", lang: str = "tr") -> Dict[str, Any]:
    city_clean = city.strip() or "Istanbul"
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            geo = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city_clean, "count": 1, "language": lang},
            )
            geo_data = geo.json()
            results = geo_data.get("results") or []
            if not results:
                return {"ok": False, "error": f"'{city_clean}' için konum bulunamadı."}
            loc = results[0]
            lat, lon = loc["latitude"], loc["longitude"]
            resolved_name = loc.get("name", city_clean)

            w = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,weather_code",
                    "timezone": "auto",
                },
            )
            cur = w.json().get("current", {})
            temp = cur.get("temperature_2m")
            feels = cur.get("apparent_temperature")
            humidity = cur.get("relative_humidity_2m")
            wind = cur.get("wind_speed_10m")
            return {
                "ok": True,
                "city": resolved_name,
                "temp": temp,
                "feels_like": feels,
                "humidity": humidity,
                "wind": wind,
            }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def fetch_wikipedia_summary(topic: str, lang: str = "tr") -> Dict[str, Any]:
    clean = topic.strip()
    if not clean:
        return {"ok": False, "error": "Konu belirtilmedi."}
    sub = "tr" if lang == "tr" else "en"
    try:
        async with httpx.AsyncClient(
            timeout=6.0,
            headers={"User-Agent": "PrometheusAI/1.0 (free desktop assistant)"},
        ) as client:
            search = await client.get(
                f"https://{sub}.wikipedia.org/w/api.php",
                params={
                    "action": "opensearch",
                    "search": clean,
                    "limit": 1,
                    "format": "json",
                },
            )
            arr = search.json()
            if len(arr) >= 2 and arr[1]:
                title = arr[1][0]
            else:
                title = clean
            summary = await client.get(
                f"https://{sub}.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ', '_')}"
            )
            if summary.status_code != 200:
                return {"ok": False, "error": "Wikipedia'da bilgi bulunamadı."}
            data = summary.json()
            extract = data.get("extract", "").strip()
            if not extract:
                return {"ok": False, "error": "Özet bulunamadı."}
            # Keep concise for voice readout (first 2 sentences)
            sentences = re.split(r"(?<=[.!?])\s+", extract)
            short = " ".join(sentences[:2])
            return {
                "ok": True,
                "title": data.get("title", title),
                "summary": short,
                "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def query_ollama(
    prompt: str,
    ollama_url: str = "http://localhost:11434",
    model: str = "llama3.2",
    lang: str = "tr",
) -> Optional[str]:
    system_prompt = (
        "Sen Prometheus'sun; Tony Stark'ın JARVIS'inden ilham alan zeki, saygılı, "
        "hafif esprili ve çok hızlı bir yapay zeka asistanısın. Kullanıcıya 'efendim' diye hitap et. "
        "Yanıtların sesli okunacağı için kısa, net ve doğal Türkçe olsun (en fazla 3-4 cümle)."
        if lang == "tr"
        else "You are Prometheus, a witty, respectful AI assistant inspired by Tony Stark's JARVIS. "
        "Address the user as 'sir'. Keep replies concise and natural for speech (max 3-4 sentences)."
    )
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{ollama_url.rstrip('/')}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("message", {}).get("content", "").strip()
                if content:
                    return content
    except Exception:
        return None
    return None
