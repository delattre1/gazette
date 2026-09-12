#!/usr/bin/env python3
"""write_config.py — turn the onboarding draft into the live config.

The model writes what the owner said to a fixed handoff file
(config.draft.json) with its file tool; this script validates it, resolves
the city to coordinates and a timezone (Open-Meteo geocoding, no key), merges
it over the existing config, and writes config.json. Nothing here takes the
owner's words as arguments, so a prompt-injected turn has no argv to steer.

Usage: write_config.py            # apply the draft
       write_config.py --show     # print the live config
"""
from __future__ import annotations

import argparse
import json
import sys

import common as c

ALLOWED = set(c.DEFAULT_CONFIG) - {"version", "location"} | {"city"}


def geocode(city: str, language: str) -> dict:
    url = "https://geocoding-api.open-meteo.com/v1/search?" + c.qs(name=city, count=5, language=language, format="json")
    data = c.http_get_json(url)
    results = data.get("results") or []
    if not results:
        raise SystemExit(f"could not find a place called {city!r}. Ask the owner for the city and country, e.g. 'Campinas, Brazil'.")
    r = results[0]
    name = r["name"]
    admin = r.get("admin1")
    country = r.get("country")
    return {
        "name": name,
        "region": admin,
        "country": country,
        "lat": r["latitude"],
        "lon": r["longitude"],
        "timezone": r.get("timezone") or "UTC",
    }


def validate(draft: dict) -> dict:
    if not isinstance(draft, dict):
        raise SystemExit("config.draft.json must be a JSON object")
    unknown = set(draft) - ALLOWED
    if unknown:
        raise SystemExit(f"unknown keys in draft: {sorted(unknown)}; allowed: {sorted(ALLOWED)}")
    out = {}
    if "owner" in draft:
        owner = draft["owner"] if isinstance(draft["owner"], dict) else {"name": draft["owner"]}
        name = str(owner.get("name") or "").strip()
        out["owner"] = {"name": c.clip(name, 40) or None}
    if "masthead" in draft:
        out["masthead"] = c.clip(str(draft["masthead"] or ""), 34) or None
    if "city" in draft:
        out["city"] = c.clip(str(draft["city"] or ""), 80) or None
    if "language" in draft:
        lang = str(draft["language"] or "en").strip().lower()[:2]
        out["language"] = lang or "en"
    if "topics" in draft:
        topics = draft["topics"]
        if isinstance(topics, str):
            topics = [t.strip() for t in topics.split(",")]
        if not isinstance(topics, list):
            raise SystemExit("topics must be a list of strings")
        out["topics"] = [c.clip(str(t), 60) for t in topics if str(t).strip()][:8]
    if "github" in draft:
        gh = str(draft["github"] or "").strip().lstrip("@")
        if gh and not all(ch.isalnum() or ch == "-" for ch in gh):
            raise SystemExit(f"github must be a plain username, got {gh!r}")
        out["github"] = gh or None
    if "delivery_time" in draft:
        h, m = c.parse_hhmm(draft["delivery_time"])
        out["delivery_time"] = f"{h:02d}:{m:02d}"
    if "units" in draft:
        units = str(draft["units"] or "metric").lower()
        if units not in ("metric", "imperial"):
            raise SystemExit("units must be 'metric' or 'imperial'")
        out["units"] = units
    if "google" in draft:
        out["google"] = bool(draft["google"])
    if "setup_complete" in draft:
        out["setup_complete"] = bool(draft["setup_complete"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()

    if args.show:
        try:
            print(json.dumps(c.read_json(c.CONFIG_PATH), indent=2, ensure_ascii=False))
        except FileNotFoundError:
            print("{}")
        return 0

    try:
        draft = c.read_json(c.DRAFT_PATH)
    except FileNotFoundError:
        raise SystemExit(f"no draft at {c.DRAFT_PATH}; write it first") from None

    changes = validate(draft)
    try:
        current = c.read_json(c.CONFIG_PATH)
    except FileNotFoundError:
        current = dict(c.DEFAULT_CONFIG)
    merged = dict(current)
    merged.update(changes)

    city = merged.get("city")
    if city and (changes.get("city") or not merged.get("location")):
        merged["location"] = geocode(city, merged.get("language") or "en")

    c.write_json(c.CONFIG_PATH, merged)
    try:
        c.DRAFT_PATH.unlink()
    except FileNotFoundError:
        pass

    loc = merged.get("location") or {}
    print(json.dumps({
        "wrote": str(c.CONFIG_PATH),
        "changed": sorted(changes),
        "masthead": c.masthead_for(merged),
        "place": ", ".join(p for p in (loc.get("name"), loc.get("region"), loc.get("country")) if p) or None,
        "timezone": loc.get("timezone"),
        "delivery_time": merged.get("delivery_time"),
        "topics": merged.get("topics"),
        "github": merged.get("github"),
        "language": merged.get("language"),
        "setup_complete": merged.get("setup_complete"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
