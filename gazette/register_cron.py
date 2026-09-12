#!/usr/bin/env python3
"""register_cron.py — schedule the daily edition, idempotently.

`hermes cron` takes no per-job timezone and this image leaves the container
in UTC, so the owner's local delivery time is converted here, once, from the
timezone the geocoder resolved for their city. Re-run after a config change:
an existing job with the same name is edited, not duplicated.

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
JOB_NAME = "gazette-edition"
SKILL = "gazette-edition"
PROMPT = (
    "Print today's Gazette. Follow the gazette-edition skill exactly: run the gather "
    "step, write edition.json from today.json, run the render step, and end with the "
    "MEDIA line for the rendered PNG plus a one-line caption. Do not run setup."
)


def utc_schedule(cfg: dict) -> str:
    h, m = c.parse_hhmm(cfg.get("delivery_time") or "07:00")
    tz = c.timezone_of(cfg)
    today = dt.datetime.now(tz).date()
    local = dt.datetime.combine(today, dt.time(h, m), tzinfo=tz)
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="print the command, register nothing")
    args = ap.parse_args()

    cfg = c.load_config()
    schedule = utc_schedule(cfg)
    deliver = "plow_chat:" + (home_channel() if not args.dry_run else "${PLOW_HOME_CHANNEL}")

    existing = registered_jobs().get(JOB_NAME)
    if existing:
        argv = [HERMES, "cron", "edit", existing["id"], "--schedule", schedule, "--prompt", PROMPT,
                "--skill", SKILL, "--deliver", deliver]
        if existing.get("paused_at"):
            resume = [HERMES, "cron", "resume", existing["id"]]
        else:
            resume = None
        action = "edited"
    else:
        argv = [HERMES, "cron", "create", schedule, PROMPT, "--name", JOB_NAME, "--skill", SKILL, "--deliver", deliver]
        resume = None
        action = "created"

    if args.dry_run:
        print(json.dumps({"would": action, "argv": argv, "schedule_utc": schedule,
                          "local": cfg.get("delivery_time"), "timezone": str(c.timezone_of(cfg))}))
        return 0

    if not os.path.exists(HERMES):
        raise SystemExit(f"{HERMES} not found -- run this inside the agent container")

    proc = run(argv)
    if proc.returncode != 0:
        raise SystemExit(f"could not {action[:-1]} the cron job:\n{proc.stdout}\n{proc.stderr}")
    if resume:
        run(resume)
    print(json.dumps({"job": JOB_NAME, "action": action, "schedule_utc": schedule,
                      "local": cfg.get("delivery_time"), "timezone": str(c.timezone_of(cfg)), "deliver": deliver}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
