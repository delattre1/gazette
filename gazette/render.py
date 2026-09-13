#!/usr/bin/env python3
"""render.py — lay out edition.json as a one-page broadsheet PNG.

Layout is code, content is the model's. The template is a four-column
Times-style front: motto bar, blackletter nameplate, folio, lead with
drop cap beside a newsprint photograph, then equal columns to the footer.
Text that does not fit is clipped with an ellipsis and counted.

Usage: render.py [--edition PATH] [--out PATH] [--date YYYY-MM-DD]
Prints one JSON line: the path written and what was dropped.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import shutil
import sys

import re

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

import common as c
from images import BLOCK_PHOTO, contain, cover, fetch_photo, fit_width, photo_aspect, _person_names

# A4 at 150 dpi. Newsprint grey-tan, not cream.
W, H = 1240, 1754
MARGIN = 40
CONTENT_W = W - 2 * MARGIN
NCOL = 4
GUTTER = 16
PAPER = (232, 228, 218)
INK = (17, 17, 17)
GREY = (90, 88, 82)
RULE = (17, 17, 17)
HAIR = (204, 204, 204)  # #CCCCCC
MOTTO = "All the News That's Fit to Print"
PRICE = "Late Edition · $2.50"
CREDIT_H = 28
# Trump-style plate: a large centered square. The photo keeps its own
# ratio inside this box — a square fills 1024×1024, a 16:9 becomes 1024×576.
HERO_BOX = 1024

FONT = {
    "regular": c.FONTS_DIR / "OldStandard-Regular.ttf",
    "bold": c.FONTS_DIR / "OldStandard-Bold.ttf",
    "italic": c.FONTS_DIR / "OldStandard-Italic.ttf",
    "masthead": c.FONTS_DIR / "UnifrakturMaguntia-Book.ttf",
    "ear": c.FONTS_DIR / "Anton-Regular.ttf",
}
_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    key = (kind, size)
    if key not in _cache:
        _cache[key] = ImageFont.truetype(str(FONT[kind]), size)
    return _cache[key]


def col_geometry():
    colw = (CONTENT_W - GUTTER * (NCOL - 1)) // NCOL
    xs = [MARGIN + i * (colw + GUTTER) for i in range(NCOL)]
    return colw, xs


def span_width(n: int, colw: int) -> int:
    return n * colw + (n - 1) * GUTTER


# --- text primitives ---------------------------------------------------------

def ink_width(f: ImageFont.FreeTypeFont, text: str) -> float:
    """Ink span. getlength undershoots Baskerville and the drop cap, so type
    walked into the next column / the plate."""
    text = str(text or "")
    if not text:
        return 0.0
    try:
        box = f.getbbox(text)
        painted = float(box[2] - box[0]) if box else 0.0
    except (AttributeError, OSError, TypeError):
        painted = 0.0
    return max(float(f.getlength(text)), painted)


def fit(text: str, f: ImageFont.FreeTypeFont, width: int) -> str:
    """Clip a single line so it measures ≤ width."""
    text = " ".join(str(text or "").split())
    width = max(1, width)
    if ink_width(f, text) <= width:
        return text
    while text and ink_width(f, text + "…") > width:
        text = text[:-1].rstrip()
    return (text + "…") if text else ""


def wrap(text: str, f: ImageFont.FreeTypeFont, width: int, max_lines: int | None = None) -> list[str]:
    """Greedy word wrap. Over-long words are split. Past max_lines, the last
    kept line ends in an ellipsis."""
    width = max(1, int(width) - 2)
    words = " ".join(str(text or "").split()).split(" ")
    lines: list[str] = []
    cur = ""
    for w in words:
        if not w:
            continue
        while ink_width(f, w) > width:
            lo, hi = 1, len(w)
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if ink_width(f, w[:mid] + "-") <= width:
                    lo = mid
                else:
                    hi = mid - 1
            if cur:
                lines.append(cur)
                cur = ""
            lines.append(w[:lo] + "-")
            w = w[lo:]
        trial = (cur + " " + w).strip()
        if ink_width(f, trial) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and ink_width(f, last + "…") > width:
            last = last[:-1].rstrip()
        lines[-1] = last + "…"
    return lines


def draw_text(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, f: ImageFont.FreeTypeFont,
              fill=INK, width: int | None = None, align: str = "left") -> None:
    if align == "center" and width:
        x = x + (width - f.getlength(text)) / 2
    elif align == "right" and width:
        x = x + width - f.getlength(text)
    draw.text((x, y), text, font=f, fill=fill)


def draw_justified(draw: ImageDraw.ImageDraw, x: int, y: int, line: str, f: ImageFont.FreeTypeFont,
                   width: int, fill=INK) -> None:
    words = line.split(" ")
    widths = [ink_width(f, w) for w in words]
    total = sum(widths)
    if len(words) < 2 or total > width * 0.98:
        draw.text((x, y), fit(line, f, width), font=f, fill=fill)
        return
    gap = (width - total) / (len(words) - 1)
    if gap > f.size * 1.2 or gap < 0:
        draw.text((x, y), fit(line, f, width), font=f, fill=fill)
        return
    cx = x
    for w, ww in zip(words, widths):
        if cx + ww > x + width + 0.5:
            break
        draw.text((cx, y), w, font=f, fill=fill)
        cx += ww + gap


def line_height(f, leading: float = 1.32) -> int:
    """Advance that clears the ink. f.size * leading undershoots Baskerville."""
    try:
        ascent, descent = f.getmetrics()
        ink = ascent + descent
    except (AttributeError, OSError):
        ink = int(getattr(f, "size", 14) * 1.25)
    return max(int(f.size * leading), ink + 1)


def draw_paragraph(draw, x, y, text, f, width, max_lines=None, fill=INK, justify=False, leading=1.32, floor=None) -> int:
    lines = wrap(text, f, width, max_lines)
    lh = line_height(f, leading)
    for i, line in enumerate(lines):
        if floor is not None and y + lh > floor:
            break
        if justify and i < len(lines) - 1:
            draw_justified(draw, x, y, line, f, width, fill)
        else:
            draw.text((x, y), line, font=f, fill=fill)
        y += lh
    return y


def paragraph_height(text, f, width, max_lines=None, leading=1.32) -> int:
    return len(wrap(text, f, width, max_lines)) * line_height(f, leading)


def draw_tracked(draw, x, y, text, f, width, tracking=3, fill=INK, align="left") -> None:
    """Letter-spaced text for labels and kickers."""
    text = str(text).upper()
    total = sum(f.getlength(ch) for ch in text) + tracking * max(0, len(text) - 1)
    if align == "center":
        x = x + (width - total) / 2
    elif align == "right":
        x = x + width - total
    for ch in text:
        draw.text((x, y), ch, font=f, fill=fill)
        x += f.getlength(ch) + tracking


def rule(draw, y, x0=MARGIN, x1=W - MARGIN, weight=1, fill=RULE) -> int:
    draw.rectangle([x0, y, x1, y + weight - 1], fill=fill)
    return y + weight


def double_rule(draw, y, x0=MARGIN, x1=W - MARGIN) -> int:
    y = rule(draw, y, x0, x1, weight=1)
    y += 2
    y = rule(draw, y, x0, x1, weight=1)
    return y


def box(draw, x, y, w, h, width=1, fill=None, outline=INK) -> None:
    draw.rectangle([x, y, x + w, y + h], outline=outline, fill=fill, width=width)


def ear_box(draw, x, y, w, h, line1, line2, floor: int | None = None) -> None:
    """Boxed gothic ears. Ink stays inside; bottom sits on the nameplate rule."""
    y2 = floor if floor is not None else y + h - 1
    draw.rectangle([x, y, x + w - 1, y2], outline=INK, width=1)
    pad, gap = 8, 3
    inner_w, inner_h = w - 2 * pad, h - 2 * pad
    size, f, b1, b2 = 28, None, None, None
    while size >= 12:
        f = font("ear", size)
        b1, b2 = f.getbbox(line1), f.getbbox(line2)
        ink_w = max(b1[2] - b1[0], b2[2] - b2[0])
        ink_h = (b1[3] - b1[1]) + gap + (b2[3] - b2[1])
        if ink_w <= inner_w and ink_h <= inner_h:
            break
        size -= 1
    h1 = b1[3] - b1[1]
    total_h = h1 + gap + (b2[3] - b2[1])
    block_top = y + pad + (inner_h - total_h) // 2
    for line, b, top in (
        (line1, b1, block_top),
        (line2, b2, block_top + h1 + gap),
    ):
        ink_w = b[2] - b[0]
        tx = x + pad + (inner_w - ink_w) / 2 - b[0]
        ty = top - b[1]
        draw.text((tx, ty), line, font=f, fill=INK)


def nameplate_with_ears(draw, y, masthead: str, size: int = 88) -> int:
    """Centered blackletter between LATEST SPECIAL / FULL REPORT. Rule under."""
    ear_w = 112
    masthead = c.clip(masthead or "The Gazette", 36)
    f_m = font("masthead", size)
    while f_m.getlength(masthead) > CONTENT_W - 2 * ear_w - 28 and size > 48:
        size -= 4
        f_m = font("masthead", size)
    band_h = max(int(f_m.size * 0.98), 88)
    name_y = y + max(0, (band_h - int(f_m.size * 0.80)) // 2)
    draw_text(draw, MARGIN + ear_w + 10, name_y, masthead, f_m, INK, CONTENT_W - 2 * ear_w - 20, "center")
    rule_y = y + band_h
    ear_box(draw, MARGIN, y, ear_w, band_h, "LATEST", "SPECIAL", floor=rule_y)
    ear_box(draw, W - MARGIN - ear_w, y, ear_w, band_h, "FULL", "REPORT", floor=rule_y)
    return rule(draw, rule_y, weight=1) + 6


# --- copy helpers ------------------------------------------------------------

def weather_bits(ed: dict) -> dict:
    w = ed.get("weather") if isinstance(ed.get("weather"), dict) else {}
    line = ed.get("weather_line") or ""
    high = w.get("high")
    low = w.get("low")
    if high is None:
        m = re.search(r"(?:high|High)\s+(\d+)", line) or re.search(r"(\d+)\s*°", line)
        if m:
            high = m.group(1)
    if low is None:
        m = re.search(r"(?:low|Low)\s+(\d+)", line) or re.findall(r"(\d+)\s*°", line)
        if isinstance(m, list) and len(m) >= 2:
            low = m[1]
        elif hasattr(m, "group"):
            low = m.group(1)
    until = w.get("until")
    if not until:
        m = re.search(r"through\s+([^.,]+)", line, re.I)
        until = m.group(1).strip() if m else ""
    summary = w.get("summary") or ""
    if not summary:
        summary = line.split(".")[0] if line else ""
    return {
        "high": str(high or "–"),
        "low": str(low or ""),
        "until": until,
        "summary": c.clip(summary, 48),
        "city": ed.get("city") or "",
        "line": line,
    }


def split_dek(body: str) -> tuple[str, str]:
    """First sentence as italic dek; the rest is the lead article."""
    text = " ".join(str(body or "").split())
    parts = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)
    if len(parts) == 2 and 20 <= len(parts[0]) <= 200:
        return parts[0], parts[1]
    return "", text


_MATCH_STOP = {
    "the", "and", "for", "from", "with", "that", "this", "its", "are", "was",
    "were", "been", "being", "have", "has", "had", "not", "but", "you", "your",
    "about", "after", "over", "into", "how", "why", "what", "who", "will",
    "new", "big", "says", "said", "amid", "as", "on", "in", "to", "of", "a",
}
_WEAK_MATCH = {
    "hackathon", "hackathons", "agents", "agent", "politics", "news",
    "industry", "brazil", "china", "model", "models",
}


def _tokens(text: str) -> set[str]:
    return {
        w for w in re.findall(r"[a-z0-9]{3,}", str(text or "").lower())
        if w not in _MATCH_STOP
    }


def _today_photos() -> list[dict]:
    """Unique usable photographs from today's gather, first title wins."""
    try:
        today = c.read_json(c.TODAY_PATH)
    except (OSError, ValueError):
        return []
    seen: set[str] = set()
    rows: list[dict] = []
    blocks = list(today.get("topics") or [])
    extra = today.get("hackernews") or []
    for block in blocks:
        topic = (block.get("topic") or "") if isinstance(block, dict) else ""
        items = (block.get("items") or []) if isinstance(block, dict) else []
        for it in items:
            if not isinstance(it, dict) or not it.get("image"):
                continue
            url = it["image"]
            if url in seen or not url.startswith("http"):
                continue
            low = url.lower()
            if any(bit in low for bit in BLOCK_PHOTO):
                continue
            seen.add(url)
            rows.append({
                "url": url,
                "title": it.get("title") or it.get("headline") or "",
                "credit": it.get("source") or topic or "",
                "topic": topic,
            })
    for it in extra:
        if not isinstance(it, dict) or not it.get("image"):
            continue
        url = it["image"]
        if url in seen or not url.startswith("http"):
            continue
        seen.add(url)
        rows.append({
            "url": url,
            "title": it.get("title") or "",
            "credit": "Hacker News",
            "topic": "",
        })
    return rows


def _score_photo(headline: str, photo: dict) -> int:
    want = _tokens(headline)
    have = _tokens(photo.get("title", "") + " " + photo.get("topic", ""))
    shared = want & have
    if not shared:
        return 0
    score = 0
    strong = False
    for w in shared:
        if w in _WEAK_MATCH:
            score += 1
            continue
        score += 3 if len(w) >= 6 else 1
        strong = True
    for n in _person_names(headline):
        if n.lower() in " ".join(have):
            score += 6
            strong = True
    return score if strong else 0


def _best_photo(headline: str, pool: list[dict], used: set[str], min_score: int = 2) -> dict | None:
    best, score = None, 0
    for p in pool:
        if p["url"] in used:
            continue
        if photo_aspect(p["url"]) < 1.05 and not _person_names(headline):
            continue
        sc = _score_photo(headline, p)
        if photo_aspect(p["url"]) >= 1.25:
            sc += 3
        if sc > score:
            best, score = p, sc
    return best if score >= min_score else None


_BUILDING = ("street", "offices", "headquarters", "building", "campus", "skyline", "facade", "third_street")


def _looks_building(photo: dict) -> bool:
    low = (photo.get("url", "") + " " + photo.get("title", "")).lower()
    return any(bit in low for bit in _BUILDING)


def _topic_fallback(headline: str, pool: list[dict], used: set[str]) -> dict | None:
    """A photo from a matching topic, never a stranger's portrait or a HQ."""
    want = _tokens(headline)
    for p in pool:
        if p["url"] in used:
            continue
        if not (_tokens(p.get("topic", "")) & want):
            continue
        if _looks_building(p):
            continue
        names = _person_names(p.get("title") or "")
        if names and not any(n.lower() in headline.lower() for n in names):
            continue
        if photo_aspect(p["url"]) < 1.05 and not _person_names(headline):
            continue
        return p
    return None


def backfill_photos(ed: dict) -> None:
    """The model often writes edition.json with no image URLs. Fill them from
    today.json so the page is never a single leftover building."""
    pool = _today_photos()
    if not pool:
        return
    used: set[str] = set()

    def assign(obj: dict, headline: str, fallback: bool = False) -> None:
        current = obj.get("image") or ""
        if current and current not in used:
            used.add(current)
            return
        hit = _best_photo(headline, pool, used, min_score=2)
        if not hit and fallback:
            hit = _topic_fallback(headline, pool, used)
        if hit:
            obj["image"] = hit["url"]
            obj.setdefault("image_credit", hit["credit"])
            used.add(hit["url"])

    lead = ed.setdefault("lead", {})
    assign(lead, lead.get("headline") or "", fallback=True)

    feat = ed.get("feature")
    if isinstance(feat, dict) and feat.get("headline"):
        assign(feat, feat.get("headline") or "", fallback=True)

    for sec in ed.get("sections") or []:
        for it in sec.get("items") or []:
            if isinstance(it, dict):
                assign(it, it.get("headline") or "")


def pick_hero(ed: dict) -> tuple[str, str]:
    """Lead photograph URL + credit. Prefers edition.json, then today.json."""
    lead = ed.get("lead") or {}
    if lead.get("image"):
        return lead["image"], lead.get("image_credit") or lead.get("source") or ""
    for sec in ed.get("sections") or []:
        for it in sec.get("items") or []:
            if it.get("image"):
                return it["image"], it.get("image_credit") or it.get("source") or ""
    try:
        today = c.read_json(c.TODAY_PATH)
    except (OSError, ValueError):
        return "", ""
    for block in today.get("topics") or []:
        for it in (block.get("items") or [] if isinstance(block, dict) else []):
            if isinstance(it, dict) and it.get("image"):
                return it["image"], it.get("source") or ""
    for it in today.get("hackernews") or []:
        if isinstance(it, dict) and it.get("image"):
            return it["image"], "Hacker News"
    return "", ""


# Photo highlights stay a step darker than the page. A white racing suit
# or studio wall must still read as paper-in-the-plate, not vanish.
PHOTO_WHITE = (204, 200, 190)
PHOTO_TONE = "ink"


def to_newsprint(photo: Image.Image) -> Image.Image:
    """Plate on paper. Herald is sepia; Times/Planet are ink or color."""
    if PHOTO_TONE == "color":
        rgb = photo.convert("RGB")
        rgb = ImageEnhance.Contrast(rgb).enhance(1.08)
        rgb = ImageEnhance.Color(rgb).enhance(0.94)
        rgb = ImageEnhance.Sharpness(rgb).enhance(1.06)
        return rgb
    gray = photo.convert("L")
    gray = ImageEnhance.Brightness(gray).enhance(0.86)
    gray = ImageOps.autocontrast(gray, cutoff=0.3)
    gray = ImageEnhance.Contrast(gray).enhance(1.10)
    gray = ImageEnhance.Sharpness(gray).enhance(1.08)
    small = gray.resize(
        (max(1, gray.width // 2), max(1, gray.height // 2)),
        Image.Resampling.BILINEAR,
    )
    dots = small.convert("1").convert("L").resize(gray.size, Image.Resampling.NEAREST)
    blended = Image.blend(gray, dots, 0.14)
    if PHOTO_TONE == "sepia":
        return ImageOps.colorize(blended, black=(46, 26, 12), white=(216, 196, 164))
    return ImageOps.colorize(blended, black=(24, 22, 20), white=PHOTO_WHITE)


def plate_h(url: str, width: int, ceiling: int = 420) -> int:
    """Full-width plate height at the photo's own ratio (portrait stays tall)."""
    if not url:
        return 0
    return min(ceiling, max(80, int(round(width / max(0.45, photo_aspect(url))))))


def photo_slot_h(url: str, width: int, caption: str = "", box_h: int = 0) -> int:
    """Pixels a plate occupies, including the credit line."""
    if not url:
        return 0
    photo_h = box_h if box_h else plate_h(url, width)
    return photo_h + (CREDIT_H if caption else 6)


def place_photo(img: Image.Image, draw, x, y, max_w, max_h, url: str, caption: str = "",
                align: str = "left", floor: int | None = None, mode: str = "cover") -> int:
    """Paste a newsprint photograph.

    mode='cover' — fill (max_w × max_h) exactly. Used for the Planet thumb.
    mode='natural' — widget is always `max_w` wide. Height follows the photo's
    own ratio (portrait stays tall). If a ceiling would shrink the plate,
    crop instead of letterboxing so the column box stays filled.
    """
    cap = CREDIT_H if caption else 8
    try:
        if not url:
            raise ValueError("no photograph url")
        raw = fetch_photo(url)
        if mode == "natural":
            cap_h = max_h if max_h and max_h > 40 else 420
            if floor is not None:
                cap_h = min(cap_h, max(48, floor - y - cap))
            fitted = fit_width(raw, max_w)
            if fitted.height > cap_h:
                photo = to_newsprint(cover(raw, max_w, cap_h))
            else:
                photo = to_newsprint(fitted)
            pw, ph = max_w, photo.height
            ox = x
        else:
            ph = max(48, int(max_h) if max_h and max_h > 40 else 160)
            photo = to_newsprint(cover(raw, max_w, ph))
            pw, ox = max_w, x
        slot = ph + cap
        if floor is not None and y + slot > floor:
            return y
        if PHOTO_TONE == "sepia":
            sheet = img.crop((ox, y, ox + pw, y + ph))
            img.paste(Image.blend(photo, sheet, 0.18), (ox, y))
        else:
            img.paste(photo, (ox, y))
        draw.rectangle([ox, y, ox + pw - 1, y + ph - 1], outline=HAIR)
        cap_x, cap_w = ox, pw
    except Exception as exc:  # noqa: BLE001
        c.log(f"render: photo failed ({type(exc).__name__}: {exc})")
        ph = max(48, int(max_h) if max_h and max_h > 40 else 160)
        if floor is not None and y + ph + cap > floor:
            return y
        box(draw, x, y, max_w, ph, 1)
        draw_text(draw, x, y + ph // 2 - 8, "Photograph unavailable", font("italic", 14), GREY, max_w, "center")
        cap_x, cap_w = x, max_w
    cap_y = y + ph + 3
    if caption:
        draw_text(draw, cap_x, cap_y, fit(caption, font("italic", 12), cap_w), font("italic", 12), GREY)
        rule(draw, cap_y + 15, cap_x, cap_x + cap_w, 1, HAIR)
        return cap_y + 18
    return y + ph + 6


def place_hero(img: Image.Image, draw, y, url: str, caption: str = "", floor: int | None = None) -> int:
    """Large centered plate. Longest side ≤ 1024; the photo's ratio is untouched."""
    box = min(HERO_BOX, W - 16)
    x = (W - box) // 2
    max_h = box
    if floor is not None:
        max_h = min(max_h, max(160, floor - y - 24))
    return place_photo(img, draw, x, y, box, max_h, url, caption, align="center")


def draw_hero_photo(img: Image.Image, draw, x, y, w, h, url: str, caption: str) -> int:
    """Back-compat wrapper: contained photo, returns the bottom y."""
    return place_photo(img, draw, x, y, w, h, url, caption)


def wrap_drop(text: str, f: ImageFont.FreeTypeFont, width: int, cap_w: int,
              cap_lines: int, max_lines: int | None) -> list[tuple[str, int]]:
    """Lines of (text, x-indent). First `cap_lines` are indented by cap_w."""
    words = " ".join(str(text or "").split()).split()
    lines: list[tuple[str, int]] = []
    cur = ""
    i = 0

    def flush(indent: int):
        nonlocal cur
        if cur:
            lines.append((cur, indent))
            cur = ""

    while i < len(words):
        indent = cap_w if len(lines) < cap_lines else 0
        avail = max(1, width - indent - 2)
        w = words[i]
        trial = (cur + " " + w).strip()
        if ink_width(f, trial) <= avail:
            cur = trial
            i += 1
            continue
        if cur:
            flush(indent)
            continue
        # single token wider than the line — split it
        lo, hi = 1, len(w)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if ink_width(f, w[:mid] + "-") <= avail:
                lo = mid
            else:
                hi = mid - 1
        lines.append((w[:lo] + "-", indent))
        words[i] = w[lo:]
        if not words[i]:
            i += 1
    if cur:
        indent = cap_w if len(lines) < cap_lines else 0
        lines.append((cur, indent))
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        last, ind = lines[-1]
        avail = max(1, width - ind - 2)
        while last and ink_width(f, last + "…") > avail:
            last = last[:-1].rstrip()
        lines[-1] = (last + "…", ind)
    return lines


def draw_drop_cap(draw, x, y, text, body_f, width, max_lines=None, leading=1.30) -> int:
    """Large first letter, body wrapping around it, then full-width justified."""
    text = " ".join(str(text or "").split())
    if not text:
        return y
    cap, rest = text[0], text[1:].lstrip()
    if not cap.isalpha():
        return draw_paragraph(draw, x, y, text, body_f, width, max_lines, INK, True, leading)
    cap_f = font("bold", int(body_f.size * 3.6))
    cap_lines = 3
    lh = line_height(body_f, leading)
    try:
        box = cap_f.getbbox(cap)
        cap_w = int(box[2] - box[0]) + 10 if box else int(cap_f.getlength(cap)) + 10
    except (AttributeError, OSError, TypeError):
        cap_w = int(cap_f.getlength(cap)) + 10
    draw.text((x, y - 6), cap, font=cap_f, fill=INK)
    lines = wrap_drop(rest, body_f, width, cap_w, cap_lines, max_lines)
    for i, (line, indent) in enumerate(lines):
        xx = x + indent
        ww = width - indent
        if i < len(lines) - 1:
            draw_justified(draw, xx, y, line, body_f, ww)
        else:
            draw.text((xx, y), line, font=body_f, fill=INK)
        y += lh
    return y


TEMPLATES = ("times", "planet", "herald")


def _pref(ed: dict, key: str, default: str) -> str:
    raw = str((ed or {}).get(key) or "").strip().lower()
    if raw:
        return raw
    try:
        cfg = c.read_json(c.CONFIG_PATH)
        return str(cfg.get(key) or default).strip().lower()
    except (OSError, FileNotFoundError, ValueError, TypeError):
        return default


def pick_template(ed: dict) -> str:
    """Owner pick from config/edition, else rotate the three faces."""
    forced = _pref(ed, "template", "auto")
    if forced in TEMPLATES:
        return forced
    n = int(ed.get("edition_number") or 1)
    return TEMPLATES[(n - 1) % len(TEMPLATES)]


def pick_photos(ed: dict, template: str) -> str:
    """Herald is always sepia. Times/Planet: ink or color."""
    if template == "herald":
        return "sepia"
    want = _pref(ed, "photos", "bw")
    if want in ("color", "colour", "colorido"):
        return "color"
    return "ink"


def render(ed: dict, out_path, date_str: str, template: str | None = None) -> dict:
    backfill_photos(ed)
    name = (template or pick_template(ed)).lower()
    if name not in TEMPLATES:
        name = "times"
    global PHOTO_TONE
    prev = PHOTO_TONE
    PHOTO_TONE = pick_photos(ed, name)
    try:
        if name != "times":
            import sheets

            return sheets.draw(name, ed, out_path, date_str)
        return render_times(ed, out_path, date_str)
    finally:
        PHOTO_TONE = prev


# --- Times (four-column broadsheet) -----------------------------------------

def render_times(ed: dict, out_path, date_str: str) -> dict:
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    dropped = {"lead_lines": 0, "items": 0, "sections": []}
    bits = weather_bits(ed)
    ears = ed.get("ears") or {}
    number = ed.get("edition_number") or 1
    colw, col_x = col_geometry()
    lead = ed.get("lead") or {}
    sections = [s for s in (ed.get("sections") or []) if isinstance(s, dict) and s.get("items")]

    # Motto / dateline / price ----------------------------------------------
    y = 28
    f_meta = font("regular", 12)
    third = CONTENT_W // 3
    wx = f"{bits['high']}° / {bits['low']}°" if bits.get("low") else (bits.get("high") + "°")
    dateline = fit(
        "  ·  ".join(p for p in (ed.get("dateline") or date_str, wx) if p),
        f_meta,
        third - 8,
    )
    price = (ears.get("right") or "").strip() or PRICE
    draw_tracked(d, MARGIN, y, MOTTO, f_meta, third, 1, INK, "left")
    draw_text(d, MARGIN + third, y, dateline, f_meta, INK, third, "center")
    draw_tracked(d, MARGIN + 2 * third, y, price, f_meta, third, 1, INK, "right")
    y += 20
    y = rule(d, y, weight=1) + 6
    y = nameplate_with_ears(d, y, ed.get("masthead") or "The Gazette", 88)

    # Folio: volume · long date · city --------------------------------------
    f_folio = font("regular", 13)
    vol = f"VOL. I    No. {number}"
    raw_date = ed.get("dateline") or date_str
    if "·" in raw_date:
        date_part, city_part = [p.strip() for p in raw_date.split("·", 1)]
    else:
        date_part, city_part = raw_date, bits.get("city") or ed.get("city") or ""
    long_date = fit(date_part, f_folio, CONTENT_W // 2)
    city = fit(city_part or bits.get("city") or "", f_folio, third)
    draw_text(d, MARGIN, y, vol, f_folio, INK)
    draw_text(d, MARGIN, y, long_date.upper() if long_date else "", f_folio, INK, CONTENT_W, "center")
    draw_text(d, MARGIN, y, city.upper(), f_folio, INK, CONTENT_W, "right")
    y += 20
    y = double_rule(d, y)
    y += 14

    # Lead: hed + type on the left, photograph on the right (the Times wrap).
    left_w = span_width(2, colw)
    right_x = col_x[2]
    right_w = span_width(2, colw)
    kicker = (lead.get("kicker") or "Today").strip()
    f_h1 = font("bold", 44)
    head_lines = wrap(c.clip(lead.get("headline", ""), 90), f_h1, left_w, 4)
    draw_tracked(d, col_x[0], y, kicker, font("bold", 11), left_w, 3, INK, "left")
    yy = y + 18
    for line in head_lines:
        d.text((col_x[0], yy), line, font=f_h1, fill=INK)
        yy += int(44 * 1.04)
    dek, article = split_dek(c.clip(lead.get("body", ""), 2600))
    if dek:
        yy += 6
        yy = draw_paragraph(d, col_x[0], yy, dek, font("italic", 18), left_w, 3, INK, False, 1.22)

    hero_url, hero_credit = pick_hero(ed)
    if not hero_credit:
        hero_credit = (lead.get("source") or "").split("·")[0].strip()
    photo_bottom = place_photo(
        img, d, right_x, y, right_w, 380, hero_url, hero_credit, floor=H - 200, mode="natural",
    )

    wx_box_h = 40
    box(d, right_x, photo_bottom + 6, right_w, wx_box_h, 1)
    f_box, f_boxb = font("regular", 13), font("bold", 13)
    temps = f"{bits['high']}° / {bits['low']}°" if bits.get("low") else f"{bits['high']}°"
    draw_text(d, right_x + 10, photo_bottom + 16, fit(f"Weather  {bits['city']}".strip(), f_boxb, right_w // 2), f_boxb)
    draw_text(d, right_x + right_w // 2, photo_bottom + 16, fit("  ·  ".join(p for p in (temps, bits.get("summary")) if p), f_box, right_w // 2 - 12), f_box, INK, right_w // 2 - 10, "right")
    right_bottom = photo_bottom + 6 + wx_box_h

    f_body = font("regular", 16)
    body_top = yy + 10
    body_w = (left_w - 12) // 2
    max_body_h = max(right_bottom, body_top + 8) - body_top
    lh = int(16 * 1.30)
    max_per_col = max(4, max_body_h // lh)
    words = " ".join(article.split()).split()
    all_lines = wrap(article, f_body, body_w)
    if len(all_lines) > 2 * max_per_col:
        dropped["lead_lines"] = len(all_lines) - 2 * max_per_col
        all_lines = all_lines[: 2 * max_per_col]
    split = max(1, (len(all_lines) + 1) // 2)
    n0 = max(1, len(words) * split // max(1, len(all_lines)))
    col0_text = " ".join(words[:n0])
    col1_text = " ".join(words[n0:])
    y0 = draw_drop_cap(d, col_x[0], body_top, col0_text, f_body, body_w, max_per_col)
    y1 = draw_paragraph(d, col_x[0] + body_w + 12, body_top, col1_text, f_body, body_w, max_per_col, INK, True, 1.30) if col1_text else body_top
    src_y = max(y0, y1) + 4
    source = c.clip(lead.get("source", ""), 80)
    if source:
        draw_text(d, col_x[0], src_y, fit("— " + source, font("italic", 13), left_w), font("italic", 13), GREY, left_w, "right")
        src_y += 18
    lead_bottom = max(right_bottom, src_y)
    d.line([(col_x[2] - GUTTER // 2, y), (col_x[2] - GUTTER // 2, lead_bottom)], fill=HAIR, width=1)
    used_n = n0 + (len(col1_text.split()) if col1_text else 0)
    rest = " ".join(words[used_n:])
    y = lead_bottom + 10
    if rest:
        cont = wrap(rest, f_body, colw)
        max_cont = 6
        if len(cont) > NCOL * max_cont:
            dropped["lead_lines"] += len(cont) - NCOL * max_cont
            cont = cont[: NCOL * max_cont]
        chunk = (len(cont) + NCOL - 1) // NCOL
        bottoms = []
        for i in range(NCOL):
            lines = cont[i * chunk:(i + 1) * chunk]
            yy = y
            for j, line in enumerate(lines):
                if j < len(lines) - 1:
                    draw_justified(d, col_x[i], yy, line, f_body, colw)
                else:
                    d.text((col_x[i], yy), line, font=f_body, fill=INK)
                yy += lh
            bottoms.append(yy)
        y = max(bottoms + [y]) + 8
    y = rule(d, y, weight=2)
    y += 10

    # Footer reserved so columns know the floor ------------------------------
    footer = ed.get("footer") or {}
    f_q = font("italic", 16)
    f_small = font("regular", 13)
    quote = c.clip(footer.get("quote", ""), 200)
    note = c.clip(footer.get("note", ""), 200)
    placed_titles: list[str] = []
    box_h = 72
    footer_top = H - 28 - box_h - 22
    col_bottom = footer_top - 10

    # Four even columns ------------------------------------------------------
    # Optional second-display hed, Times-style, before the four-column pack.
    feat = ed.get("feature") if isinstance(ed.get("feature"), dict) else None
    if feat and feat.get("headline"):
        f_fh = font("bold", 30)
        feat_w = span_width(3, colw)
        flines = wrap(c.clip(feat.get("headline", ""), 80), f_fh, feat_w, 3)
        fy0 = y
        for line in flines:
            d.text((col_x[0], y), line, font=f_fh, fill=INK)
            y += int(30 * 1.05)
        fdek = c.clip(feat.get("dek") or "", 240)
        if fdek:
            y = draw_paragraph(d, col_x[0], y + 4, fdek, font("italic", 16), feat_w, 2, INK, False, 1.2)
            y += 4
        furl = feat.get("image") or ""
        fcap = feat.get("image_credit") or feat.get("source") or ""
        feat_photo_b = fy0
        if furl:
            feat_photo_b = place_photo(img, d, col_x[3], fy0, colw, 150, furl, fcap, floor=col_bottom)
        fbody = c.clip(feat.get("body", ""), 900)
        if fbody:
            fw = (feat_w - 12) // 2
            fl = wrap(fbody, font("regular", 15), fw)
            max_fl = 7
            if len(fl) > 2 * max_fl:
                fl = fl[: 2 * max_fl]
            split_f = (len(fl) + 1) // 2
            fwords = fbody.split()
            n_f = max(1, len(fwords) * split_f // max(1, len(fl)))
            b1 = draw_paragraph(d, col_x[0], y, " ".join(fwords[:n_f]), font("regular", 15), fw, max_fl, INK, True, 1.26)
            b2 = draw_paragraph(d, col_x[0] + fw + 12, y, " ".join(fwords[n_f:]), font("regular", 15), fw, max_fl, INK, True, 1.26)
            y = max(b1, b2, feat_photo_b) + 8
        elif furl:
            y = max(y, feat_photo_b) + 8
        y = rule(d, y, weight=1)
        y += 10

    col_y = [y] * NCOL
    f_sec = font("bold", 13)
    f_ih = font("bold", 20)
    f_ib = font("regular", 15)
    f_is = font("italic", 12)
    sec_title_h = 30
    item_gap = 12
    item_chars, item_lines = 560, 7
    photo_ids: set[int] = set()
    for sec in sections:
        for it in sec.get("items") or []:
            if it.get("image") and len(photo_ids) < 2:
                photo_ids.add(id(it))

    def item_has_photo(it) -> bool:
        return id(it) in photo_ids

    def item_photo_h(it) -> int:
        url = it.get("image") or ""
        cap = it.get("image_credit") or it.get("source") or ""
        if not url:
            return 0
        return plate_h(url, colw) + (CREDIT_H if cap else 6)

    def item_height(it) -> int:
        hgt = paragraph_height(c.clip(it.get("headline", ""), 110), f_ih, colw, 3, 1.10)
        if item_has_photo(it):
            hgt += item_photo_h(it) + 6
        body = c.clip(it.get("body", ""), item_chars)
        if body:
            hgt += 3 + paragraph_height(body, f_ib, colw, item_lines)
        if it.get("source"):
            hgt += 3 + int(12 * 1.2)
        return hgt

    def draw_item(x, yy, it) -> int:
        yy = draw_paragraph(d, x, yy, c.clip(it.get("headline", ""), 110), f_ih, colw, 3, INK, False, 1.10, floor=col_bottom)
        if item_has_photo(it):
            cap = it.get("image_credit") or it.get("source") or ""
            nxt = place_photo(
                img, d, x, yy + 4, colw, plate_h(it["image"], colw),
                it["image"], cap, floor=col_bottom, mode="natural",
            )
            if nxt > yy:
                yy = nxt
        body = c.clip(it.get("body", ""), item_chars)
        if body:
            lh = line_height(f_ib, 1.26)
            n = min(item_lines, max(0, (col_bottom - yy - 22) // lh))
            if n:
                yy = draw_paragraph(d, x, yy + 3, body, f_ib, colw, n, INK, True, 1.26, floor=col_bottom)
        if it.get("source") and yy + line_height(f_is, 1.2) <= col_bottom:
            draw_text(d, x, yy + 2, c.clip(it["source"], 40), f_is, GREY)
            yy += 2 + line_height(f_is, 1.2)
        return min(yy, col_bottom)

    def draw_section_title(x, yy, title) -> int:
        title = fit(short_title(title).upper(), f_sec, colw)
        d.text((x, yy), title, font=f_sec, fill=INK)
        rule(d, yy + 16, x, x + colw, 1)
        return yy + sec_title_h

    def pick_col(need: int):
        fits = [i for i in range(NCOL) if col_y[i] + need <= col_bottom]
        if not fits:
            return None
        return min(fits, key=lambda i: col_y[i])

    band_top = y
    for sec in sections:
        title = sec.get("title") or ""
        items = list(sec.get("items") or [])
        col = pick_col(sec_title_h + item_height(items[0]))
        if col is None:
            dropped["items"] += len(items)
            dropped["sections"].append(title)
            continue
        col_y[col] = draw_section_title(col_x[col], col_y[col], title)
        placed = 0
        for it in items:
            if col_y[col] + item_height(it) > col_bottom:
                nxt = pick_col(item_height(it))
                if nxt is None:
                    break
                col = nxt
            col_y[col] = draw_item(col_x[col], col_y[col], it) + item_gap
            placed += 1
        if placed:
            placed_titles.append(title)
        if placed < len(items):
            dropped["items"] += len(items) - placed
            dropped["sections"].append(f"{title} (partial: {placed}/{len(items)})")
        else:
            col_y[col] += 4

    for i in range(1, NCOL):
        sx = col_x[i] - GUTTER // 2
        d.line([(sx, band_top), (sx, col_bottom)], fill=HAIR, width=1)

    # Boxed footer: index · quote · on this day ------------------------------
    fy = footer_top
    y = rule(d, fy, weight=1)
    y += 8
    box(d, MARGIN, y, CONTENT_W, box_h, 1)
    cell = CONTENT_W // 3
    pad = 10
    draw_tracked(d, MARGIN + pad, y + 8, "Index", font("bold", 11), cell - 2 * pad, 2)
    index = "  ·  ".join(short_title(t) for t in placed_titles[:8])
    if index:
        draw_paragraph(d, MARGIN + pad, y + 24, index, f_small, cell - 2 * pad, 2, GREY, False, 1.25)
    if quote:
        draw_paragraph(d, MARGIN + cell + pad, y + 10, quote, f_q, cell - 2 * pad, 2, INK, False, 1.24)
        if footer.get("attribution"):
            draw_text(
                d, MARGIN + cell + pad, y + box_h - 22,
                fit("— " + c.clip(footer["attribution"], 40), f_small, cell - 2 * pad),
                f_small, GREY, cell - 2 * pad, "right",
            )
    if note:
        draw_tracked(d, MARGIN + 2 * cell + pad, y + 8, "On This Day", font("bold", 11), cell - 2 * pad, 2)
        draw_paragraph(d, MARGIN + 2 * cell + pad, y + 24, note, f_small, cell - 2 * pad, 2, GREY, False, 1.25)
    # inner verticals in the footer box
    for i in (1, 2):
        fx = MARGIN + i * cell
        d.line([(fx, y + 6), (fx, y + box_h - 6)], fill=HAIR, width=1)

    by = H - 22
    draw_text(d, MARGIN, by, fit(f"No. {number}", f_small, 120), f_small, GREY)
    draw_text(d, MARGIN, by, str(number), font("bold", 14), INK, CONTENT_W, "center")
    draw_text(d, MARGIN, by, "Gazette · Plow", f_small, GREY, CONTENT_W, "right")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    result = {"path": str(out_path), "dropped": dropped, "size": [W, H], "template": "times"}
    if out_path.parent == c.EDITIONS_DIR:
        latest = out_path.parent / "latest.png"
        shutil.copyfile(out_path, latest)
        result["latest"] = str(latest)
    return result


def short_title(title: str) -> str:
    title = str(title or "")
    for long, short in (
        ("Also on the Front Page", "Also"),
        ("Hackathons in Brazil", "Hackathons"),
        ("Your Repos", "Repos"),
    ):
        if title.lower() == long.lower():
            return short
    return title


def validate(ed: dict) -> list[str]:
    problems = []
    if not isinstance(ed, dict):
        return ["edition.json is not an object"]
    lead = ed.get("lead")
    if not isinstance(lead, dict) or not lead.get("headline"):
        problems.append("lead.headline is required")
    if not isinstance(ed.get("sections"), list):
        problems.append("sections must be a list")
    else:
        for i, s in enumerate(ed["sections"]):
            if not isinstance(s, dict) or not s.get("title") or not isinstance(s.get("items"), list):
                problems.append(f"sections[{i}] needs a title and an items list")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--edition", default=str(c.EDITION_PATH))
    ap.add_argument("--out", default=None)
    ap.add_argument("--date", default=None, help="YYYY-MM-DD for the filename; default: today per config")
    ap.add_argument("--template", default=None, choices=list(TEMPLATES),
                    help="Force a page design. Default: pick from the lead photo.")
    args = ap.parse_args()

    ed = c.read_json(pathlib.Path(args.edition))
    problems = validate(ed)
    if problems:
        raise SystemExit("edition.json is not renderable:\n  - " + "\n  - ".join(problems))

    if args.date:
        date_str = args.date
    else:
        try:
            date_str = c.now_local(c.load_config()).date().isoformat()
        except SystemExit:
            date_str = dt.date.today().isoformat()
    out = pathlib.Path(args.out) if args.out else c.EDITIONS_DIR / f"{date_str}.png"
    if "edition_number" not in ed:
        ed["edition_number"] = c.edition_number()
    result = render(ed, out, date_str, template=args.template)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
