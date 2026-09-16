---
name: gazette-setup
description: First-run onboarding for Gazette (city, topics, GitHub, delivery time, language) and changing any of those later. Use when the config is missing or setup_complete is false on an owner DM turn, or when the owner asks to add/drop a topic, change city, masthead, delivery time, language, template (times/planet/herald), photo color, connect Google, or reset the profile. Never use from a cron turn or in a group.
---

# Gazette setup

One short exchange, then the first edition. The config lives at
`/var/lib/hermes/gazette/config.json`; you never edit it directly. You write
a **draft** with your file tool and a script validates it, resolves the city
to coordinates and a timezone, and writes the real file. That indirection is
the point: nothing the owner typed ever reaches a shell argument.

Paths, fixed:

- Draft (you write): `/var/lib/hermes/gazette/config.draft.json`
- Apply: `/opt/hermes/.venv/bin/python3 /opt/gazette/write_config.py`
- Show: `/opt/hermes/.venv/bin/python3 /opt/gazette/write_config.py --show`
- Schedule: `/opt/hermes/.venv/bin/python3 /opt/gazette/register_cron.py`

Run scripts as a single plain argv line. No `sh -c`, no heredocs, no `-c`
one-liners.

## Step 1: the opener

Introduce yourself as **Gazette**, never Spruce, never the line's display
name. Three or four lines. No `/help`, no command list. Match the owner's
language; default to English. Shape, not script:

> Morning. I'm Gazette. Every day I'll text you a one-page newspaper,
> written overnight: your weather, the topics you follow, your GitHub, one
> thing from history.
> To print the first one I need: your **city**, **two to four topics** you
> want covered, your **GitHub username** (optional), and **what time** you
> want it delivered. Reply in one message, however you like.

If the owner already supplied some of these in their first message, do not
ask for them again. Ask only for what is missing.

## Step 2: write the draft

From their answer, write `/var/lib/hermes/gazette/config.draft.json` with
your file tool. Only these keys, only the ones you learned:

```json
{
  "owner": {"name": "Ada"},
  "masthead": "The Ada Gazette",
  "city": "Campinas, Brazil",
  "language": "en",
  "topics": ["AI agents", "Formula 1", "Brazilian economy"],
  "github": "adalovelace",
  "delivery_time": "07:00",
  "units": "metric",
  "google": false,
  "template": "planet",
  "photos": "color",
  "setup_complete": true
}
```

Rules:
- `city`: the city **and country** as they said it; the geocoder resolves it.
- `language`: two letters (`en`, `pt`, `es`, …). Infer from how they write
  unless they said otherwise; it sets both the news feeds and the paper.
- `topics`: 2-8 short phrases. Keep their wording.
- `github`: a bare username or omit the key. Never a URL.
- `delivery_time`: `HH:MM`, 24h, in **their** local time. Default `07:00`.
  That is when the picture lands. The press starts about 20 minutes earlier.
- `masthead`: if they named it, use it; otherwise omit and the script derives
  "The <Name> Gazette" from `owner.name`.
- `units`: `imperial` only if they use Fahrenheit / are in the US; else omit.
- `template`: `planet` on first run. Later they can pick `times`, `herald`,
  or `auto` (rotate). First paper is always Planet, color.
- `photos`: `color` on first run. `bw` only if they asked. Herald stays sepia.
- `setup_complete: true` once city and topics are known. Missing GitHub is
  fine. The paper works without it.

## Step 3: apply and confirm

Run the apply command. It prints one JSON line: the resolved `place`,
`timezone`, `delivery_time`, `topics`. If it exits non-zero, read stderr.
Usually the city could not be found. Ask the owner for city and country,
rewrite the draft, run it again.

Then run the schedule command. It converts the local arrival time to the
container's clock and creates or edits two daily jobs (press, then
delivery); output says `created` or `edited` per job. Run it from this
turn (it needs the chat id the gateway publishes); if it complains about
`PLOW_HOME_CHANNEL`, say the schedule could not be set and that you will
retry on their next message.

Do **not** text the resolved config. If a tool failed, ask for the one
missing fact. Otherwise go straight to step 4.

## Step 4: the first edition, now

Do not ask. Do not announce that you are printing. Follow the
`gazette-edition` skill end to end in this same turn. The only message the
owner gets is that skill's caption + `MEDIA:` line.

## Changing one setting later

An owner with a finished install says things like "add Formula 1", "drop
crypto", "deliver at 6:30", "I moved to Lisbon", "call it The Daily Ada",
"switch to Portuguese", "use Fahrenheit", "use times", "use planet",
"use herald", "rotate templates", "color photos", "black and white",
"fotos coloridas", "preto e branco", "connect google".

Template draft: `{"template": "times"}` or `"planet"` or `"herald"` or
`"auto"`. Photos draft: `{"photos": "color"}` or `{"photos": "bw"}`.
If they pick Herald, still save `photos` if they asked, but tell them
Herald stays sepia.

1. Run `--show` to read the current values.
2. Write the draft with **only the keys that change**. For topics, write the
   full new list (current list plus or minus the change).
3. Run the apply command.
4. If `delivery_time` or `city` changed, run the schedule command again.
5. Confirm in one line. Offer to reprint if they want to see the change today.

**"connect google"**: write `{"google": true}` and apply. Then tell them the
calendar is read through their Plow account: they connect Google in the Plow
dashboard (Settings → Connectors), and tomorrow's edition carries the day's
events. If tomorrow's gather reports the connector is not linked, the page
says so in one line; nothing else breaks.

## Reset the profile

Owner says `reset`, `reset my profile`, `resetar`, `apagar meu perfil`,
`start over`. This is only in the owner's DM. Never from cron or a group.

1. **Ask first.** One short line: you will wipe city, topics, GitHub, name,
   masthead, schedule, and today's copy. The next `hi` starts onboarding
   again. Ask them to reply `yes` / `confirm` / `sim`.
2. If they say anything else, do not wipe. One line: nothing was deleted.
3. If they confirm, run **in this order**:
   - `/opt/hermes/.venv/bin/python3 /opt/gazette/register_cron.py --clear`
   - `/opt/hermes/.venv/bin/python3 /opt/gazette/write_config.py --reset`
4. One line: the profile is gone. Invite them to say `hi` when they want
   a new paper. Do **not** start setup in the same turn. Wait for the next
   message so the first-run opener is clean.

After that wipe, `config.json` is missing. The next owner DM (`hi` or
anything) is first contact: run this skill from the top. First edition is
Planet, color.

## Never

- Never run any of this in a group, or on a turn from someone who is not the
  owner. Say setup is something the owner starts privately.
- Never run it from a cron turn.
- Never write `config.json` directly; always the draft and the script.
- Never ask for passwords, API keys or tokens. You need none.
