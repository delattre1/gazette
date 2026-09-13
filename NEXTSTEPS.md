# Next steps

What is left to finish Gazette and put it on the hackathon board. The page itself is built. This is the ritual.

## Done

- Three faces (Times, Planet, Herald)
- Photos optional in the columns; type fills
- Footer floor (type does not paint the Index)
- Column ink stays inside the column (measure by bbox, not just `getlength`)
- README, MIT, reporter baked in (`AGENT_ID: gazette`)

## You do this, in order

### 1. GitHub

Public repo: `https://github.com/MAUXII/gazette` (`MAUXII`, HTTPS). `gh` is already logged in. Push from this folder:

```powershell
cd "d:\alguma ideia\gazette"
git add README.md gazette/common.py gazette/render.py gazette/sheets.py NEXTSTEPS.md .gitignore
git add docs/times.png docs/planet.png docs/herald.png
git commit -m "Clip column ink to the bbox and publish the three faces."
gh repo create gazette --public --source=. --remote=origin --push
```

Do not commit `plow-credentials`. Old `docs/sample-edition-v*.png` stay on disk only.

### 2. Your own install, reporting

```powershell
plow-agents mint ln_xxxxxxxx
docker compose up --build -d
docker compose logs -f agent
```

Text the line. Finish setup. Get today's paper as a photo. That is install #1 and the first tokens.

### 3. Register the Index page

After the repo is on GitHub:

```powershell
cd "d:\alguma ideia\gazette"
curl.exe -O https://raw.githubusercontent.com/plow-pbc/agent-index-client/main/standalone/agent_index_client.py
Get-Content .\plow-credentials | ForEach-Object {
  if ($_ -match '^([A-Z_]+)=(.*)$') { Set-Item "env:$($matches[1])" $matches[2] }
}
python agent_index_client.py --register --agent gazette --name "Gazette" --blurb "Your morning newspaper, written overnight and texted to you as a picture." --repo https://github.com/MAUXII/gazette --install-url https://github.com/MAUXII/gazette#install --runtime Hermes --image https://raw.githubusercontent.com/MAUXII/gazette/master/docs/times.png
```

Delete `agent_index_client.py` after. Do not commit it.

Page: https://aiworthusing.com/agent-index/gazette

### 4. 14 Sep — verified + one-click

On that page: **Get my agent verified**.

On Discord: **danedelattre** — Gazette is the Karen newspaper; you want it on Plow one-click. That button is theirs, not this repo.

### 5. Spread (installs, not likes)

Every morning: post **your** PNG on the hackathon Discord and on X. One photo, clone link, `mint` + `compose up`.

Ask for a screenshot of **their** first page. That is a second container.

A group chat on your number is still one install.

### 6. After the snapshot

Stories on the Index (`--story`) if you want the page to show a use case. Latch/print is later, Mac only. Do not start STR/Airbnb this week.

## Dates

| When | What |
| --- | --- |
| Now | GitHub, compose, register |
| 14 Sep | Verify, talk to Dan |
| 16 Sep 17h BRT | Submission deadline |
| 22 Sep 17h BRT | Leaderboard snapshot |
