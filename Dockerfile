# Gazette: a Plow/Hermes agent that prints your morning newspaper.
#
# A variant of plow-pbc/plow-hermes-agent: persona + skills + one background
# service (the Agent Index reporter). The base owns boot, credentials, the
# phone line and the model; this file adds only what is Gazette's.
#
# The tag is an immutable `base-<sha>` naming one commit of the base's source
# repo. Never a moving tag: every install inherits this exact filesystem while
# holding its owner's Plow credential.
FROM public.ecr.aws/e1h7x4a2/plow-cloud-agents:base-51f83158a70a383f03a4d03dbd8b6ea102cf0361@sha256:253d7ed3409effa7fa59113d93b4b79bb731d8264cdaf4cd60294924d0110a2e

# Identity. plow-init writes the home's SOUL.md on every boot as the base
# persona followed by this file. Nothing is COPYed to /var/lib/hermes/SOUL.md.
COPY --chmod=0644 runtime/persona.md /opt/hermes/plow-seed/persona.md
COPY LICENSE /usr/share/doc/gazette/

# Skills, shipped at /opt/hermes/skills outside every home. The base runtime
# reconciles them into $HERMES_HOME/skills on boot: seeding what is missing,
# updating what the agent has not touched, leaving customised ones alone.
COPY skills/gazette-setup/   /opt/hermes/skills/gazette-setup/
COPY skills/gazette-edition/ /opt/hermes/skills/gazette-edition/
COPY skills/gazette-deliver/ /opt/hermes/skills/gazette-deliver/
RUN find /opt/hermes/skills -mindepth 1 -type d -exec chmod 0755 {} + \
 && find /opt/hermes/skills -mindepth 1 -type f -exec chmod 0644 {} +

# The producer: gather, render, cron registration, fonts. Root-owned and out
# of the agent's reach, because the cron runs it unattended: everything under
# $HERMES_HOME/skills belongs to uid 10000 in a running container, and a
# prompt-injected edit there must not become code that runs every morning.
COPY gazette/ /opt/gazette/
RUN chown -R root:root /opt/gazette \
 && find /opt/gazette -type d -exec chmod 0755 {} + \
 && find /opt/gazette -type f -exec chmod 0644 {} +

# Pillow renders the newspaper. Into the runtime's own venv so the producer
# and the agent's terminal see the same interpreter. The import check runs
# against a real font so a build without working FreeType fails here, not at
# 7am in someone's kitchen.
RUN set -eu; \
    /opt/hermes/.venv/bin/python -c 'import PIL' 2>/dev/null \
      || uv pip install --python /opt/hermes/.venv/bin/python pillow==11.1.0; \
    /opt/hermes/.venv/bin/python -c 'import requests' 2>/dev/null \
      || uv pip install --python /opt/hermes/.venv/bin/python requests==2.32.3; \
    /opt/hermes/.venv/bin/python -c 'from PIL import Image, ImageFont; ImageFont.truetype("/opt/gazette/fonts/OldStandard-Regular.ttf", 24); Image.new("RGB", (8, 8))'

# The usage reporter, fetched at build from the commit vendor/client.pin names
# and checked against the hash beside it. plow-pbc/agent-index-client owns
# that file; this repo pins a revision rather than carrying a copy.
COPY vendor/client.pin /opt/plow/agent-index-client.pin
RUN set -eu; \
    sha="$(sed -n 's/^sha=//p' /opt/plow/agent-index-client.pin)"; \
    want="$(sed -n 's/^sha256=//p' /opt/plow/agent-index-client.pin)"; \
    path="$(sed -n 's/^path=//p' /opt/plow/agent-index-client.pin)"; \
    curl -fsS --max-time 60 -o /opt/plow/agent-index-client.py \
      "https://raw.githubusercontent.com/plow-pbc/agent-index-client/${sha}/${path}"; \
    got="$(sha256sum /opt/plow/agent-index-client.py | cut -d' ' -f1)"; \
    [ "$got" = "$want" ] || { echo "agent-index client is $got, pin says $want" >&2; exit 1; }; \
    chmod 0644 /opt/plow/agent-index-client.py

# s6: the agent-index longrun (depends on plow-init) and its bundle entry.
# The run script's mode is set here rather than trusted from the checkout: a
# clone on Windows does not carry the executable bit.
COPY image/s6-overlay/ /etc/s6-overlay/
RUN chmod 0755 /etc/s6-overlay/s6-rc.d/agent-index/run

# cont-init: publishes HERMES_MEDIA_ALLOW_DIRS so the gateway will deliver the
# PNGs the producer writes under /srv/gazette.
COPY --chmod=0755 image/cont-init.d/ /etc/cont-init.d/

# State. /var/lib/hermes/gazette holds config.json and the day's gathered
# data (agent-writable; lands on the home volume). /srv/gazette/editions holds
# the rendered PNGs live outside /var/lib on purpose: Hermes refuses to deliver a
# MEDIA: path under /var/lib, /etc, /var/run and friends.
RUN install -d -o 10000 -g 10000 -m 0700 /var/lib/hermes/gazette \
 && install -d -o 10000 -g 10000 -m 0755 /srv/gazette /srv/gazette/editions
