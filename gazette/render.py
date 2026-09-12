#!/usr/bin/env python3
"""render.py — lay out edition.json as a one-page newspaper PNG.

Layout is code, content is the model's. The template is fixed so every
edition looks like a newspaper whatever the model wrote; text that does not
fit is clipped with an ellipsis and counted, never allowed to break the page.

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

from PIL import Image, ImageDraw, ImageFont

import common as c

# A4 at 150 dpi, portrait. Prints clean on A4 and Letter, reads well on a phone.
W, H = 1240, 1754
MARGIN = 56
CONTENT_W = W - 2 * MARGIN
PAPER = (244, 239, 228)
INK = (24, 22, 20)
GREY = (96, 92, 86)
RULE = (40, 36, 32)

FONT = {
    "regular": c.FONTS_DIR / "OldStandard-Regular.ttf",
    "bold": c.FONTS_DIR / "OldStandard-Bold.ttf",
    "italic": c.FONTS_DIR / "OldStandard-Italic.ttf",
    "masthead": c.FONTS_DIR / "UnifrakturMaguntia-Book.ttf",
}
_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    key = (kind, size)
    if key not in _cache:
        _cache[key] = ImageFont.truetype(str(FONT[kind]), size)
    return _cache[key]


# --- text primitives ---------------------------------------------------------

def wrap(text: str, f: ImageFont.FreeTypeFont, width: int, max_lines: int | None = None) -> list[str]:
    """Greedy word wrap. Over-long words are split. Past max_lines, the last
    kept line ends in an ellipsis."""
    words = " ".join(str(text or "").split()).split(" ")
    lines: list[str] = []
    cur = ""
    for w in words:
        if not w:
            continue
        while f.getlength(w) > width:  # a token wider than the column
            lo, hi = 1, len(w)
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if f.getlength(w[:mid] + "-") <= width:
                    lo = mid
                else:
                    hi = mid - 1
            if cur:
                lines.append(cur)
                cur = ""
            lines.append(w[:lo] + "-")
            w = w[lo:]
        trial = (cur + " " + w).strip()
        if f.getlength(trial) <= width:
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
        while last and f.getlength(last + "…") > width:
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
    if len(words) < 2 or f.getlength(line) > width * 0.98:
        draw.text((x, y), line, font=f, fill=fill)
        return
    total_words = sum(f.getlength(w) for w in words)
    gap = (width - total_words) / (len(words) - 1)
    if gap > f.size * 1.2:  # too loose to justify; ragged right reads better
        draw.text((x, y), line, font=f, fill=fill)
        return
    cx = x
    for w in words:
        draw.text((cx, y), w, font=f, fill=fill)
        cx += f.getlength(w) + gap


def draw_paragraph(draw, x, y, text, f, width, max_lines=None, fill=INK, justify=False, leading=1.32) -> int:
    lines = wrap(text, f, width, max_lines)
    lh = int(f.size * leading)
    for i, line in enumerate(lines):
        if justify and i < len(lines) - 1:
            draw_justified(draw, x, y, line, f, width, fill)
        else:
            draw.text((x, y), line, font=f, fill=fill)
        y += lh
    return y


def paragraph_height(text, f, width, max_lines=None, leading=1.32) -> int:
    return len(wrap(text, f, width, max_lines)) * int(f.size * leading)


def draw_tracked(draw, x, y, text, f, width, tracking=3, fill=INK, align="left") -> None:
    """Letter-spaced text for labels and kickers."""
    text = str(text).upper()
    total = sum(f.getlength(ch) for ch in text) + tracking * (len(text) - 1)
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


def double_rule(draw, y) -> int:
    y = rule(draw, y, weight=3)
    y += 3
    y = rule(draw, y, weight=1)
    return y


# --- the page ----------------------------------------------------------------

def render(ed: dict, out_path, date_str: str) -> dict:
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    dropped = {"lead_lines": 0, "items": 0, "sections": []}

    # Masthead band -----------------------------------------------------------
    y = MARGIN
    y = rule(d, y, weight=1)
    ears = ed.get("ears") or {}
    f_ear = font("italic", 18)
    draw_text(d, MARGIN, y + 6, c.clip(ears.get("left", ""), 40), f_ear, GREY)
    draw_text(d, MARGIN, y + 6, c.clip(ears.get("right", ""), 40), f_ear, GREY, CONTENT_W, "right")

    masthead = c.clip(ed.get("masthead") or "The Gazette", 34)
    size = 104
    f_m = font("masthead", size)
    while f_m.getlength(masthead) > CONTENT_W - 40 and size > 56:
        size -= 4
        f_m = font("masthead", size)
    draw_text(d, MARGIN, y + 8, masthead, f_m, INK, CONTENT_W, "center")
    y += int(size * 1.15) + 12
    y = double_rule(d, y)

    f_date = font("regular", 20)
    draw_tracked(d, MARGIN, y + 10, c.clip(ed.get("dateline", date_str), 90), f_date, CONTENT_W, 2, INK, "center")
    y += 10 + int(20 * 1.4)
    weather_line = c.clip(ed.get("weather_line", ""), 110)
    if weather_line:
        draw_text(d, MARGIN, y + 2, weather_line, font("italic", 20), GREY, CONTENT_W, "center")
        y += int(20 * 1.4) + 4
    y += 6
    y = double_rule(d, y)
    y += 22

    # Lead ----------------------------------------------------------------------
    lead = ed.get("lead") or {}
    kicker = c.clip(lead.get("kicker", ""), 40)
    if kicker:
        draw_tracked(d, MARGIN, y, kicker, font("bold", 17), CONTENT_W, 3, GREY)
        y += 30
    f_h1 = font("bold", 54)
    head_lines = wrap(c.clip(lead.get("headline", ""), 140), f_h1, CONTENT_W, 3)
    for line in head_lines:
        d.text((MARGIN, y), line, font=f_h1, fill=INK)
        y += int(54 * 1.12)
    y += 14

    f_lead = font("regular", 23)
    gutter = 40
    col_w = (CONTENT_W - gutter) // 2
    body_lines = wrap(c.clip(lead.get("body", ""), 1400), f_lead, col_w)
    max_per_col = 9
    if len(body_lines) > 2 * max_per_col:
        dropped["lead_lines"] = len(body_lines) - 2 * max_per_col
        body_lines = body_lines[: 2 * max_per_col]
        body_lines[-1] = wrap(body_lines[-1] + "…", f_lead, col_w, 1)[0]
    split = (len(body_lines) + 1) // 2
    cols = [body_lines[:split], body_lines[split:]]
    lh = int(23 * 1.36)
    top = y
    for i, lines in enumerate(cols):
        x = MARGIN + i * (col_w + gutter)
        yy = top
        for j, line in enumerate(lines):
            if j < len(lines) - 1:
                draw_justified(d, x, yy, line, f_lead, col_w)
            else:
                d.text((x, yy), line, font=f_lead, fill=INK)
            yy += lh
    y = top + split * lh + 6
    source = c.clip(lead.get("source", ""), 80)
    if source:
        draw_text(d, MARGIN, y, "— " + source, font("italic", 17), GREY, CONTENT_W, "right")
        y += 26
    y += 12
    y = rule(d, y, weight=2)
    y += 20

    # Footer geometry first, so the columns know where to stop ----------------
    footer = ed.get("footer") or {}
    f_q = font("italic", 22)
    f_small = font("regular", 16)
    quote = c.clip(footer.get("quote", ""), 220)
    note = c.clip(footer.get("note", ""), 220)
    footer_h = 30  # bottom line
    quote_h = paragraph_height(quote, f_q, CONTENT_W - 160, 2) if quote else 0
    attr_h = 26 if footer.get("attribution") else 0
    note_h = paragraph_height(note, f_small, CONTENT_W - 160, 2) if note else 0
    footer_h += quote_h + attr_h + note_h + (22 if (quote or note) else 0) + 16
    footer_top = H - MARGIN - footer_h
    col_bottom = footer_top - 18

    # Three columns of sections -----------------------------------------------
    ncol = 3
    gutter = 34
    colw = (CONTENT_W - gutter * (ncol - 1)) // ncol
    col_x = [MARGIN + i * (colw + gutter) for i in range(ncol)]
    col_y = [y] * ncol
    col = 0
    f_sec = font("bold", 21)
    f_ih = font("bold", 25)
    f_ib = font("regular", 19)
    f_is = font("italic", 16)
    sec_title_h = 40
    item_gap = 18

    def item_height(it) -> int:
        h = paragraph_height(c.clip(it.get("headline", ""), 110), f_ih, colw, 3, 1.15)
        body = c.clip(it.get("body", ""), 420)
        if body:
            h += 6 + paragraph_height(body, f_ib, colw, 6)
        if it.get("source"):
            h += 4 + int(16 * 1.3)
        return h

    def draw_item(x, yy, it) -> int:
        yy = draw_paragraph(d, x, yy, c.clip(it.get("headline", ""), 110), f_ih, colw, 3, INK, False, 1.15)
        body = c.clip(it.get("body", ""), 420)
        if body:
            yy = draw_paragraph(d, x, yy + 6, body, f_ib, colw, 6, INK, True)
        if it.get("source"):
            draw_text(d, x, yy + 4, c.clip(it["source"], 60), f_is, GREY)
            yy += 4 + int(16 * 1.3)
        return yy

    def tracked_width(text, f, tracking) -> float:
        text = str(text).upper()
        return sum(f.getlength(ch) for ch in text) + tracking * max(len(text) - 1, 0)

    def draw_section_title(x, yy, title) -> int:
        title = c.clip(title, 40)
        while len(title) > 4 and tracked_width(title, f_sec, 2) > colw:
            title = title[:-2].rstrip() + "…"
        draw_tracked(d, x, yy, title, f_sec, colw, 2, INK)
        rule(d, yy + 30, x, x + colw, 2)
        return yy + sec_title_h

    for sec in ed.get("sections") or []:
        title = sec.get("title") or ""
        items = list(sec.get("items") or [])
        if not items:
            continue
        # Need room for the title and the first item; otherwise next column.
        while col < ncol and col_y[col] + sec_title_h + item_height(items[0]) > col_bottom:
            col += 1
        if col >= ncol:
            dropped["items"] += len(items)
            dropped["sections"].append(title)
            continue
        col_y[col] = draw_section_title(col_x[col], col_y[col], title)
        placed = 0
        for it in items:
            if col_y[col] + item_height(it) > col_bottom:
                col += 1
                if col >= ncol:
                    break
                col_y[col] = draw_section_title(col_x[col], col_y[col], title + " (cont.)")
            col_y[col] = draw_item(col_x[col], col_y[col], it) + item_gap
            placed += 1
        if placed < len(items):
            dropped["items"] += len(items) - placed
            dropped["sections"].append(f"{title} (partial: {placed}/{len(items)})")
        elif col < ncol:
            col_y[col] += 10

    # Column separators, only across the used height.
    used_bottom = max(col_y) if any(cy > y for cy in col_y) else y
    for i in range(1, ncol):
        sx = col_x[i] - gutter // 2
        d.rectangle([sx, y - 6, sx, min(used_bottom, col_bottom)], fill=(150, 144, 134))

    # Footer --------------------------------------------------------------------
    fy = footer_top
    fy = rule(d, fy, weight=1)
    fy += 14
    if quote:
        fy = draw_paragraph(d, MARGIN + 80, fy, quote, f_q, CONTENT_W - 160, 2, INK, False, 1.3)
        if footer.get("attribution"):
            draw_text(d, MARGIN + 80, fy + 2, "— " + c.clip(footer["attribution"], 60), font("regular", 17), GREY, CONTENT_W - 160, "right")
            fy += 26
        fy += 8
    if note:
        fy = draw_paragraph(d, MARGIN + 80, fy, note, f_small, CONTENT_W - 160, 2, GREY, False, 1.3)
        fy += 6
    by = H - MARGIN - 22
    rule(d, by - 8, weight=1)
    left = c.clip(footer.get("left", f"No. {ed.get('edition_number', 1)} · Printed while you slept"), 60)
    right = c.clip(footer.get("right", "Gazette · a Hermes agent on Plow"), 80)
    draw_text(d, MARGIN, by, left, f_small, GREY)
    draw_text(d, MARGIN, by, right, f_small, GREY, CONTENT_W, "right")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    latest = out_path.parent / "latest.png"
    shutil.copyfile(out_path, latest)
    return {"path": str(out_path), "latest": str(latest), "dropped": dropped, "size": [W, H]}


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
    result = render(ed, out, date_str)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
