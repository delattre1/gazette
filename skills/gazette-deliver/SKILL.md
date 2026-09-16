---
name: gazette-deliver
description: Send the already-rendered Gazette PNG. Use when the gazette-deliver cron fires at the owner's chosen arrival time. Do not gather, write, or render.
---

# Gazette: drop the paper

The press already ran. This turn only delivers.

If `/srv/gazette/editions/latest.png` exists, your entire reply is two lines:

```
<caption: ≤ 140 characters, the one thing they should know before coffee>
MEDIA:/srv/gazette/editions/latest.png
```

If you can read `/var/lib/hermes/gazette/edition.json`, take the caption from the lead headline. If you cannot, one short line is enough (`Today's Gazette.`).

If `latest.png` is missing, one line only:

```
The press is late. Text print today's paper.
```

Do not gather. Do not write `edition.json`. Do not render. Do not run setup. Do not send any other chat text.
