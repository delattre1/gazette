"""Newspaper faces that wrap type around photographs — not posters.

Times stays in render.py. Planet and Herald live here: same folio and pack,
different plates. Herald is the 1912 cafe-paper face — stacked display hed,
landscape plate in the middle, walnut ink on a real 1902 sheet.
"""
from __future__ import annotations

import pathlib
import random
import shutil

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

import common as c
import render as r
from images import photo_aspect

_PAPER_TEX = c.HERE / "assets" / "paper-aged.jpg"
_CREST = c.HERE / "assets" / "herald-crest.png"
_HERALD_PAL = {
    "INK": (44, 28, 16),
    "GREY": (98, 72, 46),
    "RULE": (56, 36, 20),
    "HAIR": (148, 122, 90),
    "PHOTO_WHITE": (216, 196, 164),
}


def draw(name: str, ed: dict, out_path, date_str: str) -> dict:
    if name == "herald":
        return _draw_herald(ed, out_path, date_str)
    img = r.Image.new("RGB", (r.W, r.H), r.PAPER)
    d = r.ImageDraw.Draw(img)
    dropped = {"lead_lines": 0, "items": 0, "sections": []}
    stories = _stories(ed)
    photos = _photos(stories)
    y = _masthead(d, ed, date_str, name)
    band = _footer_band()
    y, used, skip = _planet_wrap(img, d, y, stories, photos, band - 8)
    placed = _pack(img, d, y, stories, photos, used, band - 8, 4, skip)
    _footer(d, ed, placed)
    return _save(img, out_path, dropped, name)


def _draw_herald(ed: dict, out_path, date_str: str) -> dict:
    old = {k: getattr(r, k) for k in _HERALD_PAL}
    old_tone = r.PHOTO_TONE
    for k, v in _HERALD_PAL.items():
        setattr(r, k, v)
    r.PHOTO_TONE = "sepia"
    try:
        img = cafe_sheet(r.W, r.H)
        d = r.ImageDraw.Draw(img)
        dropped = {"lead_lines": 0, "items": 0, "sections": []}
        stories = _stories(ed)
        photos = _photos(stories)
        y = _herald_masthead(img, d, ed, date_str)
        band = _footer_band()
        y, used, skip = _herald_wrap(img, d, y, stories, photos, band - 8)
        placed = _pack(img, d, y, stories, photos, used, band - 8, 3, skip)
        _footer(d, ed, placed)
        return _save(img, out_path, dropped, "herald")
    finally:
        for k, v in old.items():
            setattr(r, k, v)
        r.PHOTO_TONE = old_tone


def cafe_sheet(w: int, h: int) -> Image.Image:
    """Aged cafe paper: 1902 brown sheet, fiber, coffee rings, burned edges."""
    base = Image.new("RGB", (w, h), (210, 188, 152))
    if _PAPER_TEX.exists():
        tex = Image.open(_PAPER_TEX).convert("RGB")
        tex = ImageOps.fit(tex, (w, h), method=Image.Resampling.LANCZOS)
        tex = ImageEnhance.Color(tex).enhance(0.8)
        tex = ImageEnhance.Contrast(tex).enhance(0.9)
        base = Image.blend(base, tex, 0.84)
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    rng = random.Random(1912)
    for _ in range(5):
        cx, cy = rng.randint(-30, w - 20), rng.randint(-30, h - 20)
        rad = rng.randint(36, 110)
        od.ellipse([cx, cy, cx + rad, cy + rad], outline=(92, 52, 22, 32), width=4)
        od.ellipse([cx + 6, cy + 6, cx + rad - 6, cy + rad - 6], outline=(92, 52, 22, 16), width=2)
    base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    shade = Image.new("RGB", (w, h), (72, 44, 24))
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.rectangle([0, 0, w, h], fill=48)
    md.rectangle([30, 24, w - 30, h - 24], fill=0)
    mask = mask.filter(ImageFilter.GaussianBlur(26))
    return Image.composite(shade, base, mask)


# --- edition flattening ------------------------------------------------------

def _stories(ed) -> list[dict]:
    out = []
    lead = ed.get("lead") or {}
    dek, body = r.split_dek(c.clip(lead.get("body", ""), 2400))
    out.append({
        "kicker": lead.get("kicker") or "",
        "headline": lead.get("headline") or "",
        "dek": dek,
        "body": body,
        "source": lead.get("source") or "",
        "image": lead.get("image") or "",
        "image_credit": lead.get("image_credit") or "",
        "kind": "lead",
    })
    feat = ed.get("feature") if isinstance(ed.get("feature"), dict) else {}
    if feat.get("headline"):
        out.append({
            "kicker": "",
            "headline": feat.get("headline") or "",
            "dek": feat.get("dek") or "",
            "body": feat.get("body") or "",
            "source": feat.get("source") or "",
            "image": feat.get("image") or "",
            "image_credit": feat.get("image_credit") or "",
            "kind": "feature",
        })
    for sec in ed.get("sections") or []:
        for it in sec.get("items") or []:
            out.append({
                "kicker": sec.get("title") or "",
                "headline": it.get("headline") or "",
                "dek": "",
                "body": it.get("body") or "",
                "source": it.get("source") or "",
                "image": it.get("image") or "",
                "image_credit": it.get("image_credit") or it.get("source") or "",
                "kind": "item",
                "section": sec.get("title") or "",
            })
    return out


def _photos(stories) -> list[tuple[str, str, float]]:
    seen, rows = set(), []
    for s in stories:
        url = s.get("image") or ""
        if url and url not in seen:
            rows.append((url, s.get("image_credit") or s.get("source") or "", photo_aspect(url)))
            seen.add(url)
    return rows


def _pick(photos, used, prefer="any"):
    rest = [p for p in photos if p[0] not in used]
    if not rest:
        return ("", "", 1.0)
    if prefer == "portrait":
        tall = [p for p in rest if p[2] < 1.05]
        return min(tall or rest, key=lambda p: p[2])
    if prefer == "land":
        wide = [p for p in rest if p[2] >= 1.05]
        return max(wide or rest, key=lambda p: p[2])
    return rest[0]


def _lead(stories):
    return next((s for s in stories if s["kind"] == "lead"), stories[0])


def _feat(stories):
    return next((s for s in stories if s["kind"] == "feature"), None)


def _items(stories, skip_heads: set[str]):
    return [s for s in stories if s["kind"] == "item" and s.get("headline") not in skip_heads]


# --- chrome ------------------------------------------------------------------

def _masthead(d, ed, date_str, name) -> int:
    bits = r.weather_bits(ed)
    number = ed.get("edition_number") or 1
    y = 24
    r.draw_tracked(d, r.MARGIN, y, r.MOTTO, r.font("regular", 11), r.CONTENT_W // 3, 2)
    r.draw_text(d, r.MARGIN, y, (ed.get("dateline") or date_str), r.font("regular", 11), r.INK, r.CONTENT_W, "center")
    r.draw_tracked(
        d, r.MARGIN + 2 * (r.CONTENT_W // 3), y,
        (ed.get("ears") or {}).get("right") or r.PRICE,
        r.font("regular", 11), r.CONTENT_W // 3, 2, align="right",
    )
    y += 18
    y = r.rule(d, y, weight=1) + 4
    y = r.nameplate_with_ears(d, y, ed.get("masthead") or "The Gazette", 84)
    raw = ed.get("dateline") or date_str
    date_part = raw.split("·")[0].strip() if "·" in raw else raw
    city = (raw.split("·")[1].strip() if "·" in raw else bits.get("city") or "")
    f_f = r.font("regular", 12)
    r.draw_text(d, r.MARGIN, y, f"VOL. I    No. {number}", f_f, r.INK)
    r.draw_text(d, r.MARGIN, y, date_part.upper(), f_f, r.INK, r.CONTENT_W, "center")
    r.draw_text(d, r.MARGIN, y, city.upper(), f_f, r.INK, r.CONTENT_W, "right")
    y += 18
    return r.double_rule(d, y) + 12


def _split_flag(mast: str) -> tuple[str, str]:
    parts = str(mast or "The Gazette").split()
    if len(parts) >= 2:
        return " ".join(parts[:-1]), parts[-1]
    return "The", parts[0]


def _herald_masthead(img, d, ed, date_str) -> int:
    """London Herald nameplate: stacked ears, split blackletter, winged crest."""
    bits = r.weather_bits(ed)
    number = ed.get("edition_number") or 1
    mast = c.clip(ed.get("masthead") or "The Gazette", 36)
    left_name, right_name = _split_flag(mast)
    year = str(date_str)[:4] if str(date_str)[:4].isdigit() else "2026"

    y = 16
    ear_w, crest_w, gap = 112, 128, 28
    cx = r.W // 2
    name_room = (r.CONTENT_W - ear_w * 2 - crest_w - gap * 2) // 2
    size = 68
    f_m = r.font("masthead", size)
    while (f_m.getlength(left_name) > name_room or f_m.getlength(right_name) > name_room) and size > 44:
        size -= 4
        f_m = r.font("masthead", size)

    band_h = max(int(f_m.size * 0.95), 92)
    name_y = y + max(0, (band_h - int(f_m.size * 0.82)) // 2)
    left_box = f_m.getbbox(left_name)
    right_box = f_m.getbbox(right_name)
    d.text((cx - crest_w // 2 - gap - left_box[2], name_y), left_name, font=f_m, fill=r.INK)
    d.text((cx + crest_w // 2 + gap - right_box[0], name_y), right_name, font=f_m, fill=r.INK)
    _crest(img, d, cx, y + band_h // 2 - 8, year)

    rule_y = y + band_h
    box_h = rule_y - y
    _ear_box(d, r.MARGIN, y, ear_w, box_h, "LATEST", "SPECIAL", floor=rule_y)
    _ear_box(d, r.W - r.MARGIN - ear_w, y, ear_w, box_h, "FULL", "REPORT", floor=rule_y)
    y = r.rule(d, rule_y, weight=1) + 6
    raw = ed.get("dateline") or date_str
    date_part = raw.split("·")[0].strip() if "·" in raw else raw
    city = (raw.split("·")[1].strip() if "·" in raw else bits.get("city") or "")
    wx = f"{bits['high']}° / {bits['low']}°" if bits.get("low") else f"{bits['high']}°"
    right = "  ·  ".join(p for p in (city, wx) if p)
    f_f = r.font("regular", 12)
    r.draw_text(d, r.MARGIN, y, f"No. {number}", f_f, r.INK)
    r.draw_text(d, r.MARGIN, y, date_part.upper(), f_f, r.INK, r.CONTENT_W, "center")
    r.draw_text(d, r.MARGIN, y, right.upper(), f_f, r.INK, r.CONTENT_W, "right")
    y += 16
    return r.double_rule(d, y) + 10


def _ear_box(d, x, y, w, h, line1, line2, floor: int | None = None) -> None:
    r.ear_box(d, x, y, w, h, line1, line2, floor)


def _crest(img, d, cx, cy, year: str) -> None:
    """Winged open book, stamped into the cafe paper."""
    mark = 72
    if _CREST.exists():
        raw = Image.open(_CREST).convert("L")
        raw = ImageOps.contain(raw, (mark + 6, mark), method=Image.Resampling.LANCZOS)
        inked = ImageOps.colorize(raw, black=r.INK, white=(255, 255, 255))
        x = int(cx - inked.width / 2)
        y = int(cy - inked.height / 2 - 4)
        sheet = img.crop((x, y, x + inked.width, y + inked.height))
        img.paste(ImageChops.multiply(sheet, inked), (x, y))
        est_y = y + inked.height + 1
    else:
        est_y = cy + 22
    f = r.font("regular", 9)
    label = f"Est. {year}"
    tw = f.getlength(label)
    d.text((cx - tw / 2, est_y), label, font=f, fill=r.INK)


def _banner_hed(d, y, text, width) -> int:
    """Two or three stacked display lines — Titanic-paper scale."""
    text = c.clip(text or "", 70)
    for size in (54, 48, 42, 36):
        f = r.font("bold", size)
        lines = r.wrap(text, f, width, 3)
        if len(lines) <= 3:
            lh = int(size * 0.94)
            for line in lines:
                d.text((r.MARGIN, y), line, font=f, fill=r.INK)
                y += lh
            return y + 6
    return y


def _footer_band() -> int:
    """Y of the rule above the index box. Pack must stop a hair above this."""
    return r.H - 24 - 58 - 18


def _footer(d, ed, placed: list[str]) -> None:
    footer = ed.get("footer") or {}
    number = ed.get("edition_number") or 1
    box_h = 58
    fy = _footer_band()
    r.rule(d, fy, weight=1)
    fy += 6
    r.box(d, r.MARGIN, fy, r.CONTENT_W, box_h, 1)
    cell, pad = r.CONTENT_W // 3, 8
    r.draw_tracked(d, r.MARGIN + pad, fy + 6, "Index", r.font("bold", 11), cell - 16, 2)
    r.draw_paragraph(
        d, r.MARGIN + pad, fy + 20,
        "  ·  ".join(r.short_title(t) for t in placed[:8]),
        r.font("regular", 12), cell - 16, 2, r.GREY, False, 1.2,
    )
    if footer.get("quote"):
        r.draw_paragraph(
            d, r.MARGIN + cell + pad, fy + 8,
            c.clip(footer["quote"], 160), r.font("italic", 14), cell - 16, 2, r.INK, False, 1.2,
        )
        if footer.get("attribution"):
            r.draw_text(
                d, r.MARGIN + cell + pad, fy + box_h - 16,
                "— " + c.clip(footer["attribution"], 32),
                r.font("regular", 11), r.GREY, cell - 16, "right",
            )
    r.draw_tracked(d, r.MARGIN + 2 * cell + pad, fy + 6, "On This Day", r.font("bold", 11), cell - 16, 2)
    if footer.get("note"):
        r.draw_paragraph(
            d, r.MARGIN + 2 * cell + pad, fy + 20,
            c.clip(footer["note"], 140), r.font("regular", 12), cell - 16, 2, r.GREY, False, 1.2,
        )
    by = r.H - 18
    r.draw_text(d, r.MARGIN, by, f"No. {number}", r.font("regular", 12), r.GREY)
    r.draw_text(d, r.MARGIN, by, str(number), r.font("bold", 13), r.INK, r.CONTENT_W, "center")
    r.draw_text(d, r.MARGIN, by, "Gazette · Plow", r.font("regular", 12), r.GREY, r.CONTENT_W, "right")


def _save(img, out_path, dropped, template: str) -> dict:
    out_path = pathlib.Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    result = {"path": str(out_path), "dropped": dropped, "size": [r.W, r.H], "template": template}
    if out_path.parent == c.EDITIONS_DIR:
        latest = out_path.parent / "latest.png"
        shutil.copyfile(out_path, latest)
        result["latest"] = str(latest)
    return result


# --- type helpers ------------------------------------------------------------

def _hed(d, x, y, text, size, width, max_lines=5) -> int:
    f = r.font("bold", size)
    for line in r.wrap(c.clip(text, 90), f, width, max_lines):
        d.text((x, y), line, font=f, fill=r.INK)
        y += int(size * 1.04)
    return y


def _kicker(d, x, y, text, width) -> int:
    if not text:
        return y
    r.draw_tracked(d, x, y, str(text), r.font("bold", 11), width, 2)
    return y + 16


def _body_cols(d, x, y, text, width, ncols, lines_each, drop=False, size=15) -> int:
    gutter = 12
    colw = (width - gutter * (ncols - 1)) // ncols
    f = r.font("regular", size)
    words = " ".join(str(text or "").split()).split()
    if not words:
        return y
    all_lines = r.wrap(" ".join(words), f, colw)
    cap = min(len(all_lines), ncols * lines_each)
    chunk = max(1, (cap + ncols - 1) // ncols)
    bottoms = []
    for i in range(ncols):
        part = all_lines[i * chunk:(i + 1) * chunk]
        xx = x + i * (colw + gutter)
        if i == 0 and drop and part:
            # rebuild a slice of words so the drop cap has a sentence
            n = max(1, len(words) * min(len(part), chunk) // max(1, len(all_lines)))
            bottoms.append(r.draw_drop_cap(d, xx, y, " ".join(words[:n]), f, colw, lines_each))
        else:
            yy = y
            for j, line in enumerate(part):
                if j < len(part) - 1:
                    r.draw_justified(d, xx, yy, line, f, colw)
                else:
                    d.text((xx, yy), line, font=f, fill=r.INK)
                yy += int(size * 1.26)
            bottoms.append(yy)
    return max(bottoms + [y])


def _story_stack(d, x, y, w, story, hed_size, body_lines, drop=False) -> int:
    y = _kicker(d, x, y, story.get("kicker") or "", w)
    y = _hed(d, x, y, story.get("headline") or "", hed_size, w)
    if story.get("dek"):
        y = r.draw_paragraph(d, x, y + 4, story["dek"], r.font("italic", 15), w, 3, r.INK, False, 1.2)
    body = c.clip(story.get("body") or "", 1400)
    if body:
        if drop:
            y = r.draw_drop_cap(d, x, y + 6, body, r.font("regular", 15), w, body_lines)
        else:
            y = r.draw_paragraph(d, x, y + 6, body, r.font("regular", 15), w, body_lines, r.INK, True, 1.26)
    if story.get("source"):
        r.draw_text(d, x, y + 2, c.clip(story["source"], 42), r.font("italic", 11), r.GREY)
        y += 14
    return y


# --- faces -------------------------------------------------------------------

def _tribune_wrap(img, d, y, stories, photos, floor) -> tuple[int, set[str]]:
    """NYT Trump wrap: lead on the left, tall plate, side story, feature in the L."""
    used: set[str] = set()
    lead = _lead(stories)
    feat = _feat(stories)
    side = next((s for s in stories if s["kind"] == "item"), lead)
    gutter = 16
    # Portrait plate large enough to run through the feature, like the Trump wrap.
    left_w, plate_w = 440, 440
    right_w = r.CONTENT_W - left_w - plate_w - 2 * gutter
    left_x = r.MARGIN
    photo_x = left_x + left_w + gutter
    right_x = photo_x + plate_w + gutter
    y0 = y

    hero = _pick(photos, used, "portrait")
    photo_bottom = y0
    if hero[0]:
        photo_bottom = r.place_photo(img, d, photo_x, y0, plate_w, 0, hero[0], hero[1], floor=floor)
        used.add(hero[0])
    d.line([(photo_x - gutter // 2, y0), (photo_x - gutter // 2, min(photo_bottom, floor))], fill=r.HAIR, width=1)
    d.line([(right_x - gutter // 2, y0), (right_x - gutter // 2, min(photo_bottom, floor))], fill=r.HAIR, width=1)

    ly = _kicker(d, left_x, y0, lead.get("kicker") or "", left_w)
    ly = _hed(d, left_x, ly, lead.get("headline") or "", 38, left_w, 5)
    if lead.get("dek"):
        ly = r.draw_paragraph(d, left_x, ly + 4, lead["dek"], r.font("italic", 16), left_w, 3, r.INK, False, 1.2)
    ly = _body_cols(d, left_x, ly + 8, lead.get("body") or "", left_w, 2, 10, drop=True)
    if lead.get("source"):
        r.draw_text(d, left_x, ly + 2, c.clip("— " + lead["source"], 70), r.font("italic", 12), r.GREY, left_w, "right")
        ly += 16

    ry = _story_stack(d, right_x, y0, right_w, side, 20, 24)

    if feat and ly + 16 < photo_bottom:
        ly = r.rule(d, ly + 6, left_x, left_x + left_w, 1) + 8
        ly = _hed(d, left_x, ly, feat.get("headline") or "", 32, left_w, 4)
        if feat.get("dek"):
            ly = r.draw_paragraph(d, left_x, ly + 4, feat["dek"], r.font("italic", 15), left_w, 2, r.INK, False, 1.2)
        remain = max(4, (photo_bottom - ly - 8) // int(15 * 1.26))
        ly = _body_cols(d, left_x, ly + 6, feat.get("body") or "", left_w, 2, min(8, remain))

    y = max(ly, photo_bottom, ry) + 8
    y = r.rule(d, y, weight=2) + 10

    # Hockey / basketball band: plate | story | plate | story
    mid_items = _items(stories, {side.get("headline"), lead.get("headline")})
    a = _pick(photos, used, "land")
    b = _pick(photos, used, "any")
    skip_mid = set()
    if a[0] or b[0]:
        y = _photo_pair(img, d, y, a, b, mid_items[:2], used, floor)
        skip_mid = {s.get("headline") for s in mid_items[:2]}
        y = r.rule(d, y, weight=1) + 8
    return y, used, {side.get("headline")} | skip_mid


def _herald_wrap(img, d, y, stories, photos, floor) -> tuple[int, set[str]]:
    """1912 Herald: huge stacked hed, landscape plate in the well, type both sides."""
    used: set[str] = set()
    lead = _lead(stories)
    feat = _feat(stories)
    side = next((s for s in stories if s["kind"] == "item"), lead)
    gutter = 16
    plate_w = int(r.CONTENT_W * 0.44)
    side_w = (r.CONTENT_W - plate_w - 2 * gutter) // 2
    left_x = r.MARGIN
    photo_x = left_x + side_w + gutter
    right_x = photo_x + plate_w + gutter

    if lead.get("kicker"):
        y = _kicker(d, left_x, y, lead["kicker"], r.CONTENT_W)
    y = _banner_hed(d, y, lead.get("headline") or "", r.CONTENT_W)
    y = r.rule(d, y, weight=2) + 10
    y0 = y

    hero = _pick(photos, used, "land")
    photo_h = min(300, r.plate_h(hero[0], plate_w, ceiling=300)) if hero[0] else 220
    photo_bottom = y0 + photo_h
    if hero[0]:
        photo_bottom = r.place_photo(
            img, d, photo_x, y0, plate_w, photo_h, hero[0], hero[1],
            floor=floor, mode="natural",
        )
        used.add(hero[0])

    extra = [s.get("body") or "" for s in stories if s is not lead and s is not side and s.get("body")]
    ly = y0
    if lead.get("dek"):
        ly = r.draw_paragraph(d, left_x, ly, lead["dek"], r.font("italic", 14), side_w, 3, r.INK, False, 1.2)
        ly += 4
    ly = _fill_to(d, left_x, ly, side_w, [lead.get("body") or "", *extra], photo_bottom, drop=True)

    ry = _hed(d, right_x, y0, side.get("headline") or "", 20, side_w, 4)
    ry = _fill_to(
        d, right_x, ry + 4, side_w,
        [side.get("body") or "", *extra, lead.get("body") or ""],
        photo_bottom,
    )

    d.line([(photo_x - gutter // 2, y0), (photo_x - gutter // 2, photo_bottom)], fill=r.HAIR, width=1)
    d.line([(right_x - gutter // 2, y0), (right_x - gutter // 2, photo_bottom)], fill=r.HAIR, width=1)

    y = max(ly, photo_bottom, ry) + 8
    y = r.rule(d, y, weight=2) + 8
    if feat:
        y = _feature_band(img, d, y, feat, photos, used, floor)
    return y, used, {side.get("headline")}


def _fill_to(d, x, y, w, texts, target, size=15, drop=False) -> int:
    """Keep writing until `target` — pour extra copy if one story runs out."""
    if y >= target:
        return y
    if isinstance(texts, str):
        pool = [texts] if texts else []
    else:
        pool = [t for t in (texts or []) if t]
    f = r.font("regular", size)
    lh = r.line_height(f, 1.26)
    for i, text in enumerate(pool):
        if y + lh > target:
            break
        n = max(0, (target - y) // lh)
        if n < 1:
            break
        if drop and i == 0:
            y = r.draw_drop_cap(d, x, y, text, f, w, n)
        else:
            y = r.draw_paragraph(d, x, y, text, f, w, n, r.INK, True, 1.26, floor=target)
    return min(y, target)


def _planet_wrap(img, d, y, stories, photos, floor) -> tuple[int, set[str]]:
    """Thumb in the middle: a square plate as tall as the side stories.

    Left and right type run to the bottom of that plate — no strip of skyline
    floating in a short box, no paper beside a tall one.
    """
    used: set[str] = set()
    lead = _lead(stories)
    feat = _feat(stories)
    side = next((s for s in stories if s["kind"] == "item"), lead)
    gutter = 16
    side_w = 268
    thumb = r.CONTENT_W - 2 * side_w - 2 * gutter
    left_x = r.MARGIN
    photo_x = left_x + side_w + gutter
    right_x = photo_x + thumb + gutter
    y0 = y

    hero = _pick(photos, used, "land")
    photo_bottom = y0 + thumb
    if hero[0]:
        photo_bottom = r.place_photo(
            img, d, photo_x, y0, thumb, thumb, hero[0], hero[1], floor=floor, mode="cover",
        )
        used.add(hero[0])

    extra = [
        s.get("body") or ""
        for s in stories
        if s is not lead and s is not side and s.get("body")
    ]
    ly = _kicker(d, left_x, y0, lead.get("kicker") or "", side_w)
    ly = _hed(d, left_x, ly, lead.get("headline") or "", 28, side_w, 5)
    if lead.get("dek"):
        ly = r.draw_paragraph(d, left_x, ly + 4, lead["dek"], r.font("italic", 14), side_w, 3, r.INK, False, 1.2)
    ly = _fill_to(d, left_x, ly + 6, side_w, [lead.get("body") or "", *extra], photo_bottom, drop=True)

    ry = _kicker(d, right_x, y0, side.get("kicker") or "", side_w)
    ry = _hed(d, right_x, ry, side.get("headline") or "", 22, side_w, 4)
    ry = _fill_to(
        d, right_x, ry + 6, side_w,
        [side.get("body") or "", *extra, lead.get("body") or ""],
        photo_bottom,
    )

    d.line([(photo_x - gutter // 2, y0), (photo_x - gutter // 2, photo_bottom)], fill=r.HAIR, width=1)
    d.line([(right_x - gutter // 2, y0), (right_x - gutter // 2, photo_bottom)], fill=r.HAIR, width=1)

    y = max(ly, photo_bottom, ry) + 8
    y = r.rule(d, y, weight=2) + 10
    if feat:
        y = _feature_band(img, d, y, feat, photos, used, floor)
    return y, used, {side.get("headline")}


def _tabloid_wrap(img, d, y, stories, photos, floor) -> tuple[int, set[str]]:
    """Three-column punch: stacked hed left, plate right, type underneath."""
    used: set[str] = set()
    lead = _lead(stories)
    feat = _feat(stories)
    gutter = 16
    ncol = 3
    colw = (r.CONTENT_W - gutter * (ncol - 1)) // ncol
    left_w = colw * 2 + gutter
    plate_w = colw
    y0 = y
    ly = _kicker(d, r.MARGIN, y0, lead.get("kicker") or "", left_w)
    ly = _hed(d, r.MARGIN, ly, lead.get("headline") or "", 44, left_w, 4)
    if lead.get("dek"):
        ly = r.draw_paragraph(d, r.MARGIN, ly + 4, lead["dek"], r.font("italic", 16), left_w, 2, r.INK, False, 1.2)
    hero = _pick(photos, used, "any")
    py = y0
    if hero[0]:
        py = r.place_photo(img, d, r.MARGIN + left_w + gutter, y0, plate_w, 0, hero[0], hero[1], floor=floor)
        used.add(hero[0])
    ly = _body_cols(d, r.MARGIN, ly + 8, lead.get("body") or "", left_w, 2, 9, drop=True)
    y = max(ly, py) + 8
    y = r.rule(d, y, weight=2) + 10
    if feat:
        y = _hed(d, r.MARGIN, y, feat.get("headline") or "", 26, r.CONTENT_W - colw - gutter, 3)
        if feat.get("dek"):
            y = r.draw_paragraph(d, r.MARGIN, y + 4, feat["dek"], r.font("italic", 14), r.CONTENT_W - colw - gutter, 2, r.INK, False, 1.2)
        extra = _pick(photos, used, "any")
        feat_y0 = y
        py = feat_y0
        if extra[0]:
            py = r.place_photo(img, d, r.MARGIN + left_w + gutter, feat_y0, plate_w, 0, extra[0], extra[1], floor=floor)
            used.add(extra[0])
        y = _body_cols(d, r.MARGIN, y + 6, feat.get("body") or "", left_w, 2, 6)
        y = max(y, py)
        y = r.rule(d, y + 4, weight=1) + 8
    return y, used, set()


def _feature_band(img, d, y, feat, photos, used, floor) -> int:
    """Display hed spanning three columns, a plate in the fourth — no overlap."""
    gutter = 16
    colw = (r.CONTENT_W - gutter * 3) // 4
    feat_w = colw * 3 + gutter * 2
    y0 = y
    y = _hed(d, r.MARGIN, y, feat.get("headline") or "", 28, feat_w, 3)
    extra = _pick(photos, used, "any")
    photo_bottom = y0
    if extra[0]:
        photo_bottom = r.place_photo(
            img, d, r.MARGIN + feat_w + gutter, y0, colw, 150, extra[0], extra[1], floor=floor,
        )
        used.add(extra[0])
    if feat.get("dek"):
        y = r.draw_paragraph(d, r.MARGIN, y + 4, feat["dek"], r.font("italic", 15), feat_w, 2, r.INK, False, 1.2)
    y = _body_cols(d, r.MARGIN, y + 6, feat.get("body") or "", feat_w, 3, 6)
    y = max(y, photo_bottom)
    return r.rule(d, y + 6, weight=1) + 8


def _photo_pair(img, d, y, a, b, items, used, floor) -> int:
    """Plate | story | plate | story — the mid-page band on the Trump front."""
    gutter = 16
    colw = (r.CONTENT_W - gutter * 3) // 4
    xs = [r.MARGIN + i * (colw + gutter) for i in range(4)]
    bottoms = []
    pairs = (
        (xs[0], xs[1], a, items[0] if items else None),
        (xs[2], xs[3], b, items[1] if len(items) > 1 else None),
    )
    for px, tx, photo, story in pairs:
        py = y
        if photo[0]:
            py = r.place_photo(img, d, px, y, colw, 140, photo[0], photo[1], floor=floor)
            used.add(photo[0])
        ty = y
        if story:
            ty = _hed(d, tx, y, story.get("headline") or "", 18, colw, 4)
            if story.get("body"):
                ty = r.draw_paragraph(d, tx, ty + 3, c.clip(story["body"], 360), r.font("regular", 14), colw, 8, r.INK, True, 1.24)
            if story.get("source"):
                r.draw_text(d, tx, ty + 2, c.clip(story["source"], 36), r.font("italic", 11), r.GREY)
                ty += 14
        bottoms.append(max(py, ty))
    return max(bottoms + [y]) + 8


def _pack(img, d, y, stories, photos, used, floor, ncol: int, skip_heads=None) -> list[str]:
    """Fill remaining columns with leftover items; drop leftover photos into the grid."""
    gutter = 16
    colw = (r.CONTENT_W - gutter * (ncol - 1)) // ncol
    xs = [r.MARGIN + i * (colw + gutter) for i in range(ncol)]
    ys = [y] * ncol
    skip = {s.get("headline") for s in stories if s["kind"] in ("lead", "feature")}
    skip |= set(skip_heads or ())
    leftovers = [s for s in stories if s["kind"] == "item" and s.get("headline") not in skip]
    photos_left = [p for p in photos if p[0] not in used]
    last_sec = None
    placed: list[str] = []
    photos_placed = 0
    f_sec, f_ih, f_ib = r.font("bold", 12), r.font("bold", 18), r.font("regular", 14)
    f_is = r.font("italic", 11)
    band_top = y
    hed_lh = r.line_height(f_ih, 1.1)
    body_lh = r.line_height(f_ib, 1.24)
    src_lh = r.line_height(f_is, 1.2)

    def col_for(need: int):
        fits = [i for i in range(ncol) if ys[i] + need <= floor]
        return min(fits, key=lambda i: ys[i]) if fits else None

    for s in leftovers:
        sec = s.get("section") or ""
        need_sec = 22 if (sec and sec != last_sec) else 0
        col = col_for(need_sec + hed_lh + 2 * body_lh + 16)
        if col is None:
            continue
        if need_sec:
            t = r.fit(r.short_title(sec).upper(), f_sec, colw)
            d.text((xs[col], ys[col]), t, font=f_sec, fill=r.INK)
            r.rule(d, ys[col] + 14, xs[col], xs[col] + colw, 1)
            ys[col] += 22
            last_sec = sec
            if sec not in placed:
                placed.append(sec)
        nhed = min(3, max(1, (floor - 12 - ys[col] - 2 * body_lh) // hed_lh))
        ys[col] = r.draw_paragraph(
            d, xs[col], ys[col], c.clip(s.get("headline", ""), 90),
            f_ih, colw, nhed, r.INK, False, 1.1, floor=floor,
        )
        if photos_left and photos_placed < 2:
            p = photos_left[0]
            ph = r.plate_h(p[0], colw)
            slot = r.photo_slot_h(p[0], colw, p[1], box_h=ph)
            if slot and ys[col] + 4 + slot + 2 * body_lh + 16 <= floor:
                photos_left.pop(0)
                photos_placed += 1
                ys[col] = r.place_photo(
                    img, d, xs[col], ys[col] + 4, colw, ph, p[0], p[1], floor=floor, mode="natural",
                )
                used.add(p[0])
        nbody = min(12, max(0, (floor - src_lh - 8 - ys[col]) // body_lh))
        if nbody >= 2 and s.get("body"):
            ys[col] = r.draw_paragraph(
                d, xs[col], ys[col] + 3, c.clip(s["body"], 520),
                f_ib, colw, nbody, r.INK, True, 1.24, floor=floor,
            )
        if s.get("source") and ys[col] + src_lh <= floor:
            r.draw_text(d, xs[col], ys[col] + 2, c.clip(s["source"], 36), f_is, r.GREY)
            ys[col] += src_lh
        ys[col] = min(ys[col] + 8, floor)

    for i in range(1, ncol):
        sx = xs[i] - gutter // 2
        d.line([(sx, band_top), (sx, min(max(ys), floor))], fill=r.HAIR, width=1)
    return placed
