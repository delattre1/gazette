"""Resolve and download news photographs.

For each story: RSS enclosure / media tag, then the article's og:image
(skipped on Google News, HN item pages, and section indexes), then a
short Wikipedia / Openverse / Commons search on the names in the
headline. DuckDuckGo Images is last — their i.js endpoint often 403s.
Failures stay empty; gather still writes today.json.

Downloads go through requests when it is installed, urllib otherwise.
The renderer crops with Pillow ImageOps.fit so the Times slot is filled
without stretching.
"""
from __future__ import annotations

import html as htmlmod
import json
import re
import urllib.parse
import urllib.request
from io import BytesIO

import common as c

BROWSER = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
JSON_UA = {"User-Agent": c.USER_AGENT, "Accept": "application/json"}
MAX_BYTES = 12 * 1024 * 1024
FETCH_TIMEOUT = 8
RESOLVE_LIMIT = 12

OG_RE = re.compile(
    r"""<meta[^>]+(?:property|name)\s*=\s*["'](?:og:image|twitter:image|og:image:url)["'][^>]+content\s*=\s*["']([^"']+)["']"""
    r"""|<meta[^>]+content\s*=\s*["']([^"']+)["'][^>]+(?:property|name)\s*=\s*["'](?:og:image|twitter:image|og:image:url)["']""",
    re.I,
)
VQD_RE = re.compile(r"""vqd=['"]([^'"]+)['"]""")
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif")
SKIP_HOSTS = (
    "news.google.com",
    "news.ycombinator.com",
    "consent.google.com",
    "accounts.google.com",
)
# Site chrome that shows up as og:image on section pages.
NOT_A_PHOTO = (
    "logo", "wordmark", "favicon", "sprite", "icon-", "/icon", "placeholder",
    "poster-", "og-default", "default-image", "site-image", "/assets/static/",
    "apple-touch",
)
# Never put these on the page, even if a headline mentioned them.
BLOCK_PHOTO = (
    "hitler", "nazi", "nazis", "swastika", "auschwitz", "holocaust",
    "mussolini", "stalin", "kkk", "isis",
)
STOP = {
    "a", "an", "the", "and", "or", "of", "in", "on", "at", "to", "for", "from",
    "with", "by", "is", "are", "was", "were", "be", "been", "being", "this",
    "that", "its", "as", "after", "before", "over", "under", "into", "about",
    "cannot", "while", "claims", "says", "said", "amid", "how", "why", "what",
    "who", "will", "not", "no", "new", "latest", "report", "reports", "update",
    "live", "winners", "losers", "winner", "loser", "breaking", "watch",
}
EXPAND = {
    "F1": "Formula One",
    "AI": "artificial intelligence",
    "GP": "Grand Prix",
}


def _get(url: str, timeout: int = FETCH_TIMEOUT, headers: dict | None = None) -> bytes:
    hdrs = {"User-Agent": BROWSER, "Accept": "*/*", **(headers or {})}
    try:
        import requests

        r = requests.get(url, timeout=timeout, headers=hdrs, allow_redirects=True)
        if r.status_code >= 400:
            raise RuntimeError(f"HTTP {r.status_code}")
        data = r.content
        if len(data) > MAX_BYTES:
            raise RuntimeError("response too large")
        return data
    except ImportError:
        req = urllib.request.Request(url, headers=hdrs)
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return resp.read(MAX_BYTES)


def _abs(base: str, url: str) -> str:
    url = htmlmod.unescape((url or "").strip())
    if url.startswith("//"):
        url = "https:" + url
    if not url:
        return ""
    return urllib.parse.urljoin(base, url)


def _host(url: str) -> str:
    try:
        return (urllib.parse.urlparse(url).hostname or "").lower()
    except Exception:  # noqa: BLE001
        return ""


def _raster_url(url: str) -> bool:
    if not url or not url.startswith("http"):
        return False
    path = urllib.parse.urlparse(url).path.lower()
    if path.endswith(".svg") or path.endswith(".svgz") or path.endswith(".pdf"):
        return False
    # Wikimedia renders SVG maps as *.svg.png — black circuit diagrams, not photos.
    if ".svg.png" in path:
        return False
    low = url.lower()
    if any(bit in low for bit in NOT_A_PHOTO):
        return False
    if any(bit in low for bit in BLOCK_PHOTO):
        return False
    # English-Wikipedia file namespace is almost always a logo or flag.
    if "/wikipedia/en/" in low:
        return False
    return True


def _strip_source(title: str) -> str:
    text = " ".join((title or "").split())
    if " - " in text:
        text = text.rsplit(" - ", 1)[0]
    return text


def _gentilic(word: str) -> bool:
    return bool(re.search(r"(ish|ian|ese)$", word, re.I))


def _ok_query(q: str) -> bool:
    toks = q.split()
    if len(q) < 3:
        return False
    if len(toks) == 1 and (q.upper() in EXPAND or _gentilic(q)):
        return False
    return True


def _queries(title: str, hint: str = "") -> list[str]:
    """Short search strings. Long headlines return zero hits everywhere."""
    text = _strip_source(title)
    proper = re.findall(r"\b([A-Z][A-Za-z0-9]+|F1|AI|GP)\b", text)
    proper = [p for p in proper if p.lower() not in STOP]
    names = [p for p in proper if p not in EXPAND and len(p) >= 4 and not _gentilic(p)]
    gentilics = [p for p in proper if _gentilic(p)]
    out: list[str] = []
    if any(p in ("GP", "F1") for p in proper) or re.search(r"\bGrand Prix\b", text, re.I):
        for p in gentilics + names:
            out.append(f"{p} Grand Prix")
        out.append("Formula One")
    if names:
        out.append(" ".join(names[:4]))
        out.extend(names[:3])
    if proper:
        expanded = [EXPAND.get(p, p) for p in proper]
        out.append(" ".join(expanded[:4]))
    for p in proper:
        if p in EXPAND:
            out.append(EXPAND[p])
    if hint:
        out.append(hint)
    words = [w for w in re.findall(r"[A-Za-z0-9]+", text) if w.lower() not in STOP]
    if words:
        out.append(" ".join(words[:4]))
    seen: set[str] = set()
    uniq: list[str] = []
    for q in out:
        q = " ".join(q.split())
        key = q.lower()
        if not _ok_query(q) or key in seen:
            continue
        seen.add(key)
        uniq.append(q)
    return uniq[:5]


def _article_url(page_url: str) -> bool:
    """Section indexes rarely have a story photograph."""
    if not page_url or _host(page_url) in SKIP_HOSTS:
        return False
    if _host(page_url).endswith(".google.com"):
        return False
    parts = [p for p in urllib.parse.urlparse(page_url).path.strip("/").split("/") if p]
    if len(parts) >= 3:
        return True
    if any(re.match(r"20\d\d$", p) or len(p) >= 16 for p in parts):
        return True
    return False


def rss_image(item) -> str:
    """media:content / media:thumbnail / enclosure on a parsed RSS item."""
    for tag in (
        "{http://search.yahoo.com/mrss/}content",
        "{http://search.yahoo.com/mrss/}thumbnail",
        "content",
        "thumbnail",
    ):
        el = item.find(tag)
        if el is not None and el.get("url"):
            return el.get("url").strip()
    enc = item.find("enclosure")
    if enc is not None:
        typ = (enc.get("type") or "")
        href = (enc.get("url") or "").strip()
        if href and (typ.startswith("image") or href.lower().endswith(IMG_EXT)):
            return href
    return ""


def og_image(page_url: str) -> str:
    if not _article_url(page_url):
        return ""
    raw = _get(page_url)
    text = raw.decode("utf-8", "replace")[:200_000]
    m = OG_RE.search(text)
    if not m:
        return ""
    found = _abs(page_url, m.group(1) or m.group(2))
    return found if _raster_url(found) else ""


def wiki_image(query: str) -> str:
    if not query:
        return ""
    search = json.loads(
        _get(
            "https://en.wikipedia.org/w/api.php?"
            + c.qs(action="query", list="search", srsearch=query, srlimit=1, format="json"),
            headers=JSON_UA,
        ).decode("utf-8")
    )
    hits = (search.get("query") or {}).get("search") or []
    if not hits:
        return ""
    title = hits[0].get("title") or ""
    if not title:
        return ""
    tokens = [t.lower() for t in query.split() if len(t) >= 3 and t.lower() not in STOP]
    if tokens and not any(t in title.lower() for t in tokens):
        return ""
    slug = urllib.parse.quote(title.replace(" ", "_"), safe="")
    data = json.loads(
        _get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}",
            headers={**JSON_UA, "Accept": "application/json; charset=utf-8"},
        ).decode("utf-8")
    )
    for key in ("originalimage", "thumbnail"):
        src = ((data.get(key) or {}).get("source") or "").strip()
        if _raster_url(src):
            return src
    return ""


def commons_image(query: str) -> str:
    # Commons substring-matches file names ("OpenAI" → "Open Air"). Only
    # run on a short proper-noun query.
    tokens = query.split()
    if not query or len(tokens) > 3 or (len(tokens) == 1 and len(query) < 4):
        return ""
    data = json.loads(
        _get(
            "https://commons.wikimedia.org/w/api.php?"
            + c.qs(
                action="query",
                generator="search",
                gsrsearch=query,
                gsrnamespace=6,
                gsrlimit=5,
                prop="imageinfo",
                iiprop="url|mime|size",
                iiurlwidth=800,
                format="json",
            ),
            headers=JSON_UA,
        ).decode("utf-8")
    )
    pages = list(((data.get("query") or {}).get("pages") or {}).values())
    pages.sort(key=lambda p: p.get("index") or 99)
    for page in pages:
        title = (page.get("title") or "").lower()
        if any(bit in title for bit in NOT_A_PHOTO):
            continue
        info = (page.get("imageinfo") or [{}])[0]
        mime = (info.get("mime") or "").lower()
        if mime and not mime.startswith("image/"):
            continue
        src = (info.get("thumburl") or info.get("url") or "").strip()
        if mime in ("image/svg+xml", "image/svg"):
            src = (info.get("thumburl") or "").strip()
        if _raster_url(src):
            return src
    return ""


def ddg_image(query: str) -> str:
    """First still from DuckDuckGo's i.js, using the vqd token from the HTML page."""
    q = " ".join((query or "").split())[:80]
    if not q:
        return ""
    landing = "https://duckduckgo.com/?" + urllib.parse.urlencode(
        {"q": q, "iax": "images", "ia": "images"}
    )
    html = _get(landing).decode("utf-8", "replace")
    m = VQD_RE.search(html) or re.search(r"vqd=([\d-]+)", html)
    if not m:
        return ""
    api = "https://duckduckgo.com/i.js?" + urllib.parse.urlencode(
        {"l": "us-en", "o": "json", "q": q, "vqd": m.group(1), "f": ",,,,,", "p": "1"}
    )
    data = json.loads(_get(api, headers={"Referer": "https://duckduckgo.com/"}).decode("utf-8"))
    for row in data.get("results") or []:
        src = (row.get("image") or row.get("thumbnail") or "").strip()
        if _raster_url(src):
            return src
    return ""


def openverse_image(query: str) -> str:
    q = " ".join((query or "").split())[:80]
    if not q:
        return ""
    url = "https://api.openverse.org/v1/images/?" + urllib.parse.urlencode(
        {"q": q, "page_size": 3, "mature": "false"}
    )
    data = json.loads(_get(url, headers=JSON_UA).decode("utf-8"))
    skip_title = ("collage", "mosaic", "montage", "logo", "wordmark", "icon")
    for row in data.get("results") or []:
        title = (row.get("title") or "").lower()
        if any(bit in title for bit in skip_title):
            continue
        src = (row.get("url") or row.get("thumbnail") or "").strip()
        if _raster_url(src):
            return src
    return ""


def _person_names(title: str) -> list[str]:
    """Capitalized tokens that look like a person, not a country or acronym."""
    text = _strip_source(title)
    proper = re.findall(r"\b([A-Z][A-Za-z]{3,})\b", text)
    skip = STOP | set(EXPAND) | {
        "Congress", "Senate", "House", "White", "China", "Brazil",
        "Google", "OpenAI", "Microsoft", "Apple", "BlackRock", "Institute",
        "Weekly", "News", "Times", "Post", "Reuters", "Politics",
        "Nazi", "Nazis", "Hitler", "Stalin", "Fascist", "Communist",
        "AngelHack", "Hackathon", "Hackathons",
    }
    out = []
    for p in proper:
        if p in skip or p.lower() in skip or _gentilic(p):
            continue
        out.append(p)
    return out[:3]


def _portrait_enough(url: str) -> bool:
    """A face plate, not a wide building or card."""
    try:
        im = fetch_photo(url)
        return (im.size[0] / max(1, im.size[1])) <= 1.15
    except Exception:  # noqa: BLE001
        return False


def _wiki_portrait(names: list[str]) -> str:
    for n in names:
        try:
            found = wiki_image(n)
            if found and _portrait_enough(found):
                c.log(f"images: portrait/{n!r}")
                return found
        except Exception as exc:  # noqa: BLE001
            c.log(f"images: portrait {n!r}: {type(exc).__name__}: {exc}")
    return ""


def resolve_image(link: str, title: str, already: str = "", hint: str = "") -> str:
    """One URL for this story, or empty. Failures stay empty — never raise.

    Named people get a Wikipedia portrait first. RSS/og:image on politics
    stories is usually the building behind the person.
    """
    names = _person_names(title)
    portrait = _wiki_portrait(names) if names else ""
    if portrait:
        return portrait

    if already and _raster_url(already):
        if not names or _portrait_enough(already):
            return already

    try:
        found = og_image(link) if link else ""
        if found and (not names or _portrait_enough(found)):
            c.log(f"images: og {c.clip(title, 50)}")
            return found
        if found and names:
            c.log(f"images: og skipped (wide) {c.clip(title, 50)}")
    except Exception as exc:  # noqa: BLE001
        c.log(f"images: og {title!r}: {type(exc).__name__}: {exc}")

    qs = _queries(title, hint)
    for q in qs:
        for name, fn in (
            ("wiki", wiki_image),
            ("openverse", openverse_image),
            ("commons", commons_image),
        ):
            try:
                found = fn(q)
                if not found:
                    continue
                if names and not _portrait_enough(found):
                    c.log(f"images: skip wide {name}/{q!r}")
                    continue
                c.log(f"images: {name}/{q!r} {c.clip(title, 40)}")
                return found
            except Exception as exc:  # noqa: BLE001
                c.log(f"images: {name} {q!r}: {type(exc).__name__}: {exc}")

    try:
        found = ddg_image(qs[0] if qs else title)
        if found:
            c.log(f"images: ddg {c.clip(title, 50)}")
            return found
    except Exception as exc:  # noqa: BLE001
        c.log(f"images: ddg {title!r}: {type(exc).__name__}: {exc}")
    if already and _raster_url(already):
        return already
    return ""


def enrich_items(items: list[dict], limit: int = RESOLVE_LIMIT, hint: str = "") -> int:
    """Attach `image` on up to `limit` dicts that have a title and a link/url."""
    n = 0
    for it in items:
        if n >= limit:
            break
        if not isinstance(it, dict):
            continue
        title = it.get("title") or it.get("headline") or ""
        link = it.get("link") or it.get("url") or ""
        if not title and not link:
            continue
        url = resolve_image(link, title, already=it.get("image") or "", hint=hint)
        if url:
            it["image"] = url
            n += 1
        else:
            c.log(f"images: miss {c.clip(title, 50)}")
    return n


def _wiki_thumb(url: str, width: int) -> str:
    """Wikimedia originals can be 10MB+; thumbs must use their allowed widths."""
    u = url.split("?")[0]
    if "wikimedia.org" not in u and "wikipedia.org" not in u:
        return url
    w = 1280
    if "/thumb/" in u:
        return re.sub(r"/\d+px-", f"/{w}px-", u)
    if "/commons/" not in u:
        return url
    rest = u.split("/commons/", 1)[-1]
    name = rest.rsplit("/", 1)[-1]
    if not name:
        return url
    return f"https://upload.wikimedia.org/wikipedia/commons/thumb/{rest}/{w}px-{name}"


_PHOTO_CACHE: dict[str, object] = {}


def fetch_photo(url: str):
    """Download `url` once and return an RGB PIL image, uncropped."""
    from PIL import Image, ImageOps

    if not url:
        raise ValueError("empty photo url")
    if url in _PHOTO_CACHE:
        return _PHOTO_CACHE[url].copy()
    fetch_url = _wiki_thumb(url, 1280)
    try:
        import requests

        response = requests.get(
            fetch_url,
            timeout=12,
            headers={"User-Agent": BROWSER, "Accept": "image/*,*/*"},
            allow_redirects=True,
        )
        response.raise_for_status()
        if len(response.content) > MAX_BYTES:
            raise RuntimeError("response too large")
        photo = Image.open(BytesIO(response.content))
    except ImportError:
        photo = Image.open(BytesIO(_get(fetch_url, timeout=12)))
    photo = ImageOps.exif_transpose(photo)
    if photo.mode not in ("RGB", "L"):
        photo = photo.convert("RGB")
    elif photo.mode == "L":
        photo = photo.convert("RGB")
    _PHOTO_CACHE[url] = photo
    return photo.copy()


def contain(photo, max_w: int, max_h: int):
    """Scale `photo` to fit inside (max_w, max_h). Never crops. Never stretches."""
    from PIL import Image

    pw, ph = photo.size
    if pw < 1 or ph < 1:
        raise ValueError("empty photo")
    scale = min(max_w / pw, max_h / ph)
    nw, nh = max(1, int(pw * scale)), max(1, int(ph * scale))
    return photo.resize((nw, nh), Image.Resampling.LANCZOS)


def fit_width(photo, width: int):
    """Scale so the plate is exactly `width` wide. Height follows the ratio."""
    from PIL import Image

    pw, ph = photo.size
    if pw < 1 or ph < 1:
        raise ValueError("empty photo")
    nh = max(1, int(round(ph * width / pw)))
    return photo.resize((width, nh), Image.Resampling.LANCZOS)


def cover(photo, width: int, height: int):
    """Fill (width, height) exactly. Crops the overflow, never stretches."""
    from PIL import Image, ImageOps

    if width < 1 or height < 1:
        raise ValueError("empty cover box")
    return ImageOps.fit(photo, (width, height), method=Image.Resampling.LANCZOS)


def photo_aspect(url: str) -> float:
    """width / height, or 1.0 if the fetch fails."""
    try:
        im = fetch_photo(url)
        return im.size[0] / max(1, im.size[1])
    except Exception:  # noqa: BLE001
        return 1.0


def download_photo(url: str, width: int, height: int):
    """Fetch and scale into (width, height) without cropping — letterboxed by the caller."""
    return contain(fetch_photo(url), width, height)
