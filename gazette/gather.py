#!/usr/bin/env python3
"""gather.py — collect today's raw material into today.json.

Deterministic and model-free: weather, headlines per topic, Hacker News, the
owner's GitHub, the calendar when Google is connected, and "on this day".
Every source is independent; one failing is recorded in its slot and the rest
still land. The model reads the result and writes the edition; it never
fetches anything itself.

Sizes are bounded on purpose. Everything here ends up in the model's context.
"""
from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
import xml.etree.ElementTree as ET

import common as c
from images import enrich_items, rss_image

TOPIC_ITEMS = 6
HN_ITEMS = 10
GITHUB_REPOS = 8
GITHUB_ISSUES = 10
CALENDAR_EVENTS = 15
ON_THIS_DAY = 3

WMO = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "rime fog",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    56: "freezing drizzle", 57: "heavy freezing drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain",
    66: "freezing rain", 67: "heavy freezing rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
    80: "light showers", 81: "showers", 82: "violent showers",
    85: "snow showers", 86: "heavy snow showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "severe thunderstorm with hail",
}

CONNECTOR = "/var/lib/hermes/skills/productivity/plow-connectors/plow_connector.py"


def _attempt(name: str, fn):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 - one source failing must not sink the edition
        c.log(f"gather: {name} failed: {type(exc).__name__}: {exc}")
        return {"error": f"{type(exc).__name__}: {c.clip(str(exc), 160)}"}


# --- weather -----------------------------------------------------------------

def weather(cfg: dict, today: dt.date) -> dict:
    loc = cfg.get("location") or {}
    if not loc.get("lat"):
        return {"skipped": "no location in config"}
    imperial = cfg.get("units") == "imperial"
    url = "https://api.open-meteo.com/v1/forecast?" + c.qs(
        latitude=loc["lat"], longitude=loc["lon"], timezone=loc.get("timezone", "auto"),
        daily="weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset",
        hourly="precipitation_probability,weather_code",
        forecast_days=1,
        temperature_unit="fahrenheit" if imperial else "celsius",
    )
    data = c.http_get_json(url)
    d, h = data["daily"], data["hourly"]
    rain_hours = [
        t[11:16] for t, p in zip(h["time"], h["precipitation_probability"]) if (p or 0) >= 50
    ]
    code = d["weather_code"][0]
    return {
        "date": d["time"][0],
        "summary": WMO.get(code, f"code {code}"),
        "code": code,
        "high": round(d["temperature_2m_max"][0]),
        "low": round(d["temperature_2m_min"][0]),
        "unit": "°F" if imperial else "°C",
        "precip_prob_max": d["precipitation_probability_max"][0],
        "rain_likely_hours": rain_hours[:12],
        "sunrise": d["sunrise"][0][11:16],
        "sunset": d["sunset"][0][11:16],
    }


# --- news --------------------------------------------------------------------

def _rss_items(url: str, limit: int) -> list[dict]:
    root = ET.fromstring(c.http_get(url))
    out = []
    for item in root.iter("item"):
        title = item.findtext("title") or ""
        source = item.findtext("source") or ""
        # Google News titles end in " - Source"; keep the source once.
        if source and title.endswith(" - " + source):
            title = title[: -(len(source) + 3)]
        row = {
            "title": c.clip(title, 160),
            "source": c.clip(source, 60),
            "link": (item.findtext("link") or "").strip(),
            "published": (item.findtext("pubDate") or "").strip(),
        }
        thumb = rss_image(item)
        if thumb:
            row["image"] = thumb
        out.append(row)
        if len(out) >= limit:
            break
    return out


def topics(cfg: dict) -> list[dict]:
    lang = (cfg.get("language") or "en").lower()[:2]
    hl, gl, ceid = c.NEWS_LOCALES.get(lang, c.NEWS_LOCALES["en"])
    result = []
    for topic in (cfg.get("topics") or [])[:8]:
        url = "https://news.google.com/rss/search?" + c.qs(q=topic, hl=hl, gl=gl, ceid=ceid)
        items = _attempt(f"topic {topic!r}", lambda: _rss_items(url, TOPIC_ITEMS))
        result.append({"topic": topic, "items": items} if isinstance(items, list)
                      else {"topic": topic, **items})
    return result


def hackernews() -> list[dict]:
    data = c.http_get_json("https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=%d" % HN_ITEMS)
    return [{
        "title": c.clip(hit.get("title"), 140),
        "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
        "points": hit.get("points"),
        "comments": hit.get("num_comments"),
    } for hit in data.get("hits", [])]


# --- github ------------------------------------------------------------------

def github(cfg: dict, since: dt.datetime) -> dict:
    user = cfg.get("github")
    if not user:
        return {"skipped": "no github username in config"}
    headers = {"Accept": "application/vnd.github+json"}
    base = "https://api.github.com"
    repos = c.http_get_json(f"{base}/users/{user}/repos?" + c.qs(sort="pushed", per_page=GITHUB_REPOS, type="owner"), headers)
    repo_rows = [{
        "name": r["full_name"],
        "stars": r["stargazers_count"],
        "open_issues": r["open_issues_count"],
        "pushed_at": r["pushed_at"],
        "language": r.get("language"),
        "description": c.clip(r.get("description"), 120),
    } for r in repos]

    since_q = since.date().isoformat()
    def search(q):
        data = c.http_get_json(f"{base}/search/issues?" + c.qs(q=q, sort="created", order="desc", per_page=GITHUB_ISSUES), headers)
        return [{
            "repo": it["repository_url"].rsplit("/", 2)[-2] + "/" + it["repository_url"].rsplit("/", 1)[-1],
            "number": it["number"],
            "title": c.clip(it["title"], 120),
            "author": (it.get("user") or {}).get("login"),
            "created_at": it["created_at"],
            "url": it["html_url"],
            "labels": [l["name"] for l in it.get("labels", [])][:4],
        } for it in data.get("items", [])]

    new_issues = _attempt("github new issues", lambda: search(f"user:{user} is:issue is:open created:>={since_q}"))
    open_prs = _attempt("github open prs", lambda: search(f"user:{user} is:pr is:open"))

    events = _attempt("github events", lambda: c.http_get_json(f"{base}/users/{user}/events/public?per_page=30", headers))
    recent = []
    if isinstance(events, list):
        for ev in events:
            created = dt.datetime.fromisoformat(ev["created_at"].replace("Z", "+00:00"))
            if created < since:
                continue
            kind = ev["type"].replace("Event", "")
            detail = ""
            payload = ev.get("payload", {})
            if kind == "Push":
                detail = f"{len(payload.get('commits', []))} commit(s)"
            elif kind in ("Issues", "PullRequest"):
                detail = f"{payload.get('action')} #{(payload.get('issue') or payload.get('pull_request') or {}).get('number')}"
            elif kind == "Watch":
                detail = "starred"
            recent.append({"type": kind, "repo": ev["repo"]["name"], "detail": detail, "at": ev["created_at"]})
    return {"user": user, "repos": repo_rows, "new_issues": new_issues, "open_prs": open_prs, "recent_activity": recent[:15]}


# --- calendar (optional, via the Plow connector helper) -----------------------

def calendar(cfg: dict, start: dt.datetime, end: dt.datetime) -> dict:
    if not cfg.get("google"):
        return {"skipped": "google not connected (say 'connect google' to add your calendar)"}
    body = json.dumps({"time_min": start.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
                       "time_max": end.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
                       "max_results": CALENDAR_EVENTS})
    proc = subprocess.run([sys.executable, CONNECTOR, "gmail", "calendar.events.list", body],
                          capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        raise RuntimeError(c.clip(proc.stderr.strip() or "connector exited non-zero", 200))
    data = json.loads(proc.stdout)
    events = data.get("data") or data.get("events") or data
    rows = []
    for ev in (events if isinstance(events, list) else [])[:CALENDAR_EVENTS]:
        rows.append({
            "summary": c.clip(ev.get("summary") or "(no title)", 100),
            "start": (ev.get("start") or {}).get("dateTime") or (ev.get("start") or {}).get("date") or ev.get("start"),
            "end": (ev.get("end") or {}).get("dateTime") or (ev.get("end") or {}).get("date") or ev.get("end"),
            "location": c.clip(ev.get("location"), 80),
            "attendees": len(ev.get("attendees") or []),
        })
    return {"events": rows}


# --- on this day -------------------------------------------------------------

def on_this_day(today: dt.date, lang: str) -> list[dict]:
    lang = lang if lang in ("en", "pt", "es", "fr", "de", "it") else "en"
    url = f"https://api.wikimedia.org/feed/v1/wikipedia/{lang}/onthisday/events/{today.month:02d}/{today.day:02d}"
    data = c.http_get_json(url, {"Api-User-Agent": c.USER_AGENT})
    rows = [{"year": e.get("year"), "text": c.clip(e.get("text"), 200)} for e in data.get("events", [])]
    # Prefer a spread of eras over the first three, which skew recent.
    rows.sort(key=lambda r: r["year"] or 0)
    if len(rows) > ON_THIS_DAY:
        step = len(rows) // ON_THIS_DAY
        rows = [rows[i * step] for i in range(ON_THIS_DAY)]
    return rows


# --- main --------------------------------------------------------------------

def main() -> int:
    cfg = c.load_config()
    now = c.now_local(cfg)
    today = now.date()
    since = now - dt.timedelta(hours=24)
    lang = (cfg.get("language") or "en").lower()[:2]

    out = {
        "generated_at": now.isoformat(timespec="seconds"),
        "local_date": today.isoformat(),
        "local_date_long": now.strftime("%A, %B %-d, %Y") if sys.platform != "win32" else now.strftime("%A, %B %d, %Y").replace(" 0", " "),
        "weekday": now.strftime("%A"),
        "edition_number": c.edition_number(),
        "masthead": c.masthead_for(cfg),
        "owner": cfg.get("owner"),
        "city": (cfg.get("location") or {}).get("name") or cfg.get("city"),
        "language": lang,
        "units": cfg.get("units"),
        "template": cfg.get("template") or "auto",
        "photos": cfg.get("photos") or "bw",
        "weather": _attempt("weather", lambda: weather(cfg, today)),
        "topics": topics(cfg),
        "hackernews": _attempt("hackernews", hackernews),
        "github": _attempt("github", lambda: github(cfg, since)),
        "calendar": _attempt("calendar", lambda: calendar(cfg, now.replace(hour=0, minute=0, second=0, microsecond=0),
                                                          now.replace(hour=23, minute=59, second=59, microsecond=0))),
        "on_this_day": _attempt("on_this_day", lambda: on_this_day(today, lang)),
    }
    attached = 0
    for block in out.get("topics") or []:
        if isinstance(block, dict) and isinstance(block.get("items"), list):
            attached += enrich_items(block["items"], limit=4, hint=block.get("topic") or "")
    if isinstance(out.get("hackernews"), list):
        attached += enrich_items(out["hackernews"], limit=4)
    c.write_json(c.TODAY_PATH, out)
    sizes = {k: (len(v) if isinstance(v, list) else ("error" if isinstance(v, dict) and "error" in v else "ok"))
             for k, v in out.items() if k in ("topics", "hackernews", "github", "calendar", "on_this_day", "weather")}
    print(json.dumps({"wrote": str(c.TODAY_PATH), "edition_number": out["edition_number"],
                      "local_date": out["local_date"], "sources": sizes, "images": attached}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
