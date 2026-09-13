"""Shared plumbing for the Gazette producer: paths, config, time, HTTP.

Standard library only. Every path is overridable by environment for local
runs outside the container (GAZETTE_STATE, GAZETTE_EDITIONS); inside the
image the defaults are the ones the Dockerfile creates.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

HERE = pathlib.Path(__file__).resolve().parent
FONTS_DIR = HERE / "fonts"

STATE_DIR = pathlib.Path(os.environ.get("GAZETTE_STATE", "/var/lib/hermes/gazette"))
EDITIONS_DIR = pathlib.Path(os.environ.get("GAZETTE_EDITIONS", "/srv/gazette/editions"))

CONFIG_PATH = STATE_DIR / "config.json"
DRAFT_PATH = STATE_DIR / "config.draft.json"
TODAY_PATH = STATE_DIR / "today.json"
EDITION_PATH = STATE_DIR / "edition.json"

USER_AGENT = "Gazette/0.1 (+https://github.com/MAUXII/gazette)"
HTTP_TIMEOUT = 20

# Google News RSS locales by language code. Anything else falls back to en.
NEWS_LOCALES = {
    "en": ("en-US", "US", "US:en"),
    "pt": ("pt-BR", "BR", "BR:pt-419"),
    "es": ("es-419", "MX", "MX:es-419"),
    "fr": ("fr", "FR", "FR:fr"),
    "de": ("de", "DE", "DE:de"),
    "it": ("it", "IT", "IT:it"),
    "nl": ("nl", "NL", "NL:nl"),
    "ja": ("ja", "JP", "JP:ja"),
}

DEFAULT_CONFIG = {
    "version": 1,
    "owner": {"name": None},
    "masthead": None,
    "city": None,
    "location": None,  # {"name","country","lat","lon","timezone"} resolved by write_config
    "language": "en",
    "topics": [],
    "github": None,
    "delivery_time": "07:00",
    "units": "metric",
    "google": False,
    "template": "auto",
    "photos": "bw",
    "setup_complete": False,
}


def log(*parts: object) -> None:
    print(*parts, file=sys.stderr)


def read_json(path: pathlib.Path):
    with open(path, encoding="utf-8-sig") as fh:  # tolerate a BOM
        return json.load(fh)


def write_json(path: pathlib.Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def load_config() -> dict:
    """The live config, or a SystemExit naming what is missing."""
    try:
        cfg = read_json(CONFIG_PATH)
    except FileNotFoundError:
        raise SystemExit(
            f"no config at {CONFIG_PATH}. Run the gazette-setup skill first: it writes "
            "the city, topics and delivery time this producer reads."
        ) from None
    merged = dict(DEFAULT_CONFIG)
    merged.update(cfg)
    return merged


def timezone_of(cfg: dict) -> ZoneInfo:
    name = ((cfg.get("location") or {}).get("timezone")) or "UTC"
    try:
        return ZoneInfo(name)
    except Exception:  # noqa: BLE001 - an unknown zone falls back, loudly
        log(f"common: unknown timezone {name!r}, using UTC")
        return ZoneInfo("UTC")


def now_local(cfg: dict) -> dt.datetime:
    return dt.datetime.now(tz=timezone_of(cfg))


def masthead_for(cfg: dict) -> str:
    if cfg.get("masthead"):
        return str(cfg["masthead"])
    name = (cfg.get("owner") or {}).get("name")
    if name:
        return f"The {name} Gazette"
    return "The Gazette"


def http_get(url: str, headers: dict | None = None, timeout: int = HTTP_TIMEOUT) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - fixed public hosts
        return resp.read()


def http_get_json(url: str, headers: dict | None = None, timeout: int = HTTP_TIMEOUT):
    return json.loads(http_get(url, headers, timeout).decode("utf-8"))


def qs(**params) -> str:
    return urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})


def clip(text: str | None, limit: int) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rstrip()
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut + "…"


def edition_number() -> int:
    """One more than the editions already on disk."""
    try:
        return sum(1 for p in EDITIONS_DIR.iterdir() if p.suffix == ".png") + 1
    except FileNotFoundError:
        return 1


def parse_hhmm(value: str) -> tuple[int, int]:
    try:
        hh, mm = str(value).strip().split(":")
        h, m = int(hh), int(mm)
    except ValueError:
        raise SystemExit(f"delivery_time must be HH:MM, got {value!r}") from None
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise SystemExit(f"delivery_time out of range: {value!r}")
    return h, m
