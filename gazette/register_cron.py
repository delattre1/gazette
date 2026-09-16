#!/usr/bin/env python3
"""register_cron.py: schedule production and delivery, idempotently.

`delivery_time` is when the picture should land on the phone. The press
starts PRESS_LEAD_MIN earlier so gather + the model + render finish first.
A second job, at the chosen minute, only sends latest.png.

`hermes cron` takes no per-job timezone and this image leaves the container
in UTC, so the owner's local time is converted here from the timezone the
geocoder resolved for their city. Re-run after a config change: existing
jobs with the same names are edited, not duplicated.

Runs INSIDE the container, where /opt/hermes/bin/hermes lives.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys

import common as c

HERMES = "/opt/hermes/bin/hermes"
JOBS_FILE = pathlib.Path(os.environ.get("HERMES_HOME", "/var/lib/hermes")) / "cron" / "jobs.json"
PRESS_LEAD_MIN = 20

PRODUCE_NAME = "gazette-edition"
PRODUCE_SKILL = "gazette-edition"
PRODUCE_PROMPT = (
    "Produce today's Gazette. Follow the gazette-edition skill steps 1-3 only: "
    "gather, write edition.json, render. Do not send MEDIA. Do not text the owner. "
    "Your entire reply is NO_REPLY. Do not run setup."
)

DELIVER_NAME = "gazette-deliver"
DELIVER_SKILL = "gazette-deliver"
DELIVER_PROMPT = (
    "Deliver today's Gazette. Do not gather. Do not write edition.json. Do not render. "
    "If /srv/gazette/editions/latest.png exists, send one caption line then "
    "MEDIA:/srv/gazette/editions/latest.png. If it is missing, one line only: "
    "The press is late. Text print today's paper."
)


def utc_schedule(cfg: dict, offset_min: int = 0) -> str:
    h, m = c.parse_hhmm(cfg.get("delivery_time") or "07:00")
    tz = c.timezone_of(cfg)
    today = dt.datetime.now(tz).date()
    local = dt.datetime.combine(today, dt.time(h, m), tzinfo=tz) + dt.timedelta(minutes=offset_min)
    utc = local.astimezone(dt.timezone.utc)
    return f"{utc.minute} {utc.hour} * * *"


def home_channel() -> str:
    chan = (os.environ.get("PLOW_HOME_CHANNEL") or "").strip()
    if not chan:
        raise SystemExit(
            "PLOW_HOME_CHANNEL is not set in this environment. Run this from an agent turn "
            "(the gateway publishes it), not from a bare docker exec."
        )
    return chan


def registered_jobs() -> dict:
    try:
        jobs = json.loads(JOBS_FILE.read_text())["jobs"]
    except FileNotFoundError:
        return {}
    return {j["name"]: j for j in jobs if j.get("name")}


def run(argv: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True)


def upsert(name: str, skill: str, prompt: str, schedule: str, deliver: str) -> dict:
    existing = registered_jobs().get(name)
    if existing:
        argv = [
            HERMES, "cron", "edit", existing["id"],
            "--schedule", schedule, "--prompt", prompt,
            "--skill", skill, "--deliver", deliver,
        ]
        action = "edited"
        resume = [HERMES, "cron", "resume", existing["id"]] if existing.get("paused_at") else None
    else:
        argv = [
            HERMES, "cron", "create", schedule, prompt,
            "--name", name, "--skill", skill, "--deliver", deliver,
        ]
        action = "created"
        resume = None
    return {"name": name, "action": action, "argv": argv, "resume": resume, "schedule_utc": schedule}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="print the commands, register nothing")
    ap.add_argument("--clear", action="store_true", help="remove Gazette cron jobs")
    args = ap.parse_args()

    if args.clear:
        removed = []
        for name, job in list(registered_jobs().items()):
            if name not in (PRODUCE_NAME, DELIVER_NAME):
                continue
            proc = run([HERMES, "cron", "remove", job["id"]])
            if proc.returncode != 0:
                raise SystemExit(f"could not remove {name}:\n{proc.stdout}\n{proc.stderr}")
            removed.append(name)
        print(json.dumps({"cleared": removed}))
        return 0

    cfg = c.load_config()
    produce_at = utc_schedule(cfg, -PRESS_LEAD_MIN)
    deliver_at = utc_schedule(cfg, 0)
    dest = "plow_chat:" + (home_channel() if not args.dry_run else "${PLOW_HOME_CHANNEL}")

    plans = [
        upsert(PRODUCE_NAME, PRODUCE_SKILL, PRODUCE_PROMPT, produce_at, dest),
        upsert(DELIVER_NAME, DELIVER_SKILL, DELIVER_PROMPT, deliver_at, dest),
    ]

    if args.dry_run:
        print(json.dumps({
            "jobs": [{k: p[k] for k in ("name", "action", "schedule_utc") if k in p} | {"argv": p["argv"]}
                     for p in plans],
            "local": cfg.get("delivery_time"),
            "timezone": str(c.timezone_of(cfg)),
            "press_lead_min": PRESS_LEAD_MIN,
        }))
        return 0

    if not os.path.exists(HERMES):
        raise SystemExit(f"{HERMES} not found -- run this inside the agent container")

    results = []
    for plan in plans:
        proc = run(plan["argv"])
        if proc.returncode != 0:
            raise SystemExit(
                f"could not {plan['action'][:-1]} {plan['name']}:\n{proc.stdout}\n{proc.stderr}"
            )
        if plan["resume"]:
            run(plan["resume"])
        results.append({
            "job": plan["name"],
            "action": plan["action"],
            "schedule_utc": plan["schedule_utc"],
        })

    print(json.dumps({
        "jobs": results,
        "local": cfg.get("delivery_time"),
        "timezone": str(c.timezone_of(cfg)),
        "press_lead_min": PRESS_LEAD_MIN,
        "deliver": dest,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
