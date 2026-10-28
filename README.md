# Cute Hermes Skills

Hermes Agent skills for the CUTE (中國科技大學, China University of Technology) IT team.

| Skill | What it does |
|-------|--------------|
| `outlook-com` | Search / read classic Outlook mail (cute.edu.tw) via PowerShell COM. WSL or Windows. |
| `gmail-oauth` | Read / search / send / reply gm 信箱 (gm.cute.edu.tw) via Gmail API + OAuth2. |

## Install (each PC, once)

Install from a terminal or the Desktop app — **not by asking the agent in chat**
(`hermes skills install` asks for confirmation, and a chat cannot answer it).

### Hermes Desktop (Windows) — easiest

Open these two links on the PC (Win+R, paste, Enter) and click **Install** in Hermes:

```
hermes://skill/install?identifier=shein888%2Fcute-hermes%2Fskills%2Foutlook-com
hermes://skill/install?identifier=shein888%2Fcute-hermes%2Fskills%2Fgmail-oauth
```

(Needs a recent Desktop build. If the link does nothing, use the commands below.)

### Terminal (PowerShell on Windows, or WSL / Linux shell)

```bash
hermes skills tap add shein888/cute-hermes
hermes skills install shein888/cute-hermes/skills/outlook-com --yes
hermes skills install shein888/cute-hermes/skills/gmail-oauth --yes
hermes skills list
```

- Use `owner/repo` (`shein888/cute-hermes`) for `tap add`, **not** the full
  `https://github.com/...` URL — Hermes stores the text as-is and the URL form
  finds nothing. If you already added the URL form, remove it:
  `hermes skills tap remove https://github.com/shein888/cute-hermes`
- `tap add` only registers this repo as a source; `install` copies the skill
  (with its scripts) into the Hermes skills folder
  (`%LOCALAPPDATA%\hermes\skills` on Windows, `~/.hermes/skills` on WSL/Linux).
- Start a **new chat** afterwards, then ask: 「幫我查 Outlook 最近三天的信」
  or 「幫我看 gm 信箱有沒有新信」. The first gm request gives a Google sign-in link once per PC.

### Requirements on the PC

- outlook-com: Windows with **classic** Outlook (not "New Outlook"). Works with
  Hermes for Windows/Desktop (Git Bash) and Hermes in WSL.
- gmail-oauth: Python 3.8+ (`python`, `py -3`, or Hermes' bundled `uv` is used
  automatically; otherwise `winget install Python.Python.3.12`).

## Update (after this repo changes)

```bash
hermes skills update            # all outdated hub skills
hermes skills update outlook-com
```

If a skill was edited locally on that PC, `update` skips it; use
`hermes skills update outlook-com --force` to overwrite.

## Repo layout (required by `hermes skills tap`)

Taps scan **one level under `skills/`**, so every skill lives in its own folder there:

```
cute-hermes/
├── README.md
└── skills/
    ├── outlook-com/
    │   ├── SKILL.md
    │   └── scripts/
    │       ├── outlook-search.ps1   # core (Windows PowerShell 5.1, UTF-8 BOM)
    │       ├── outlook-search.cmd   # Windows wrapper
    │       └── outlook-search.sh    # WSL wrapper
    └── gmail-oauth/
        ├── SKILL.md
        └── scripts/
            ├── gmail.sh             # finds a working Python, runs gmail_oauth.py
            └── gmail_oauth.py
```

Rules for editing:
- Reference scripts in SKILL.md as `bash "${HERMES_SKILL_DIR}/scripts/..."` — always
  in double quotes: on Windows the path has backslashes and may contain spaces.
- Do **not** put `curl ... | bash` (or any remote download-and-run) in SKILL.md or
  scripts: the Hermes install scanner rates it critical and blocks the install,
  even with `--force`.
- Keep user data (tokens, results) outside the skill folder; `update` replaces the folder.
