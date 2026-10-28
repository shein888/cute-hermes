# Cute Hermes Skills

Hermes Agent skills for the CUTE (中國科技大學, China University of Technology) IT team.

| Skill | What it does |
|-------|--------------|
| `outlook-com` | Search / read classic Outlook mail (cute.edu.tw) via PowerShell COM. WSL or Windows. |
| `gmail-oauth` | Read / search / send / reply gm 信箱 (gm.cute.edu.tw) via Gmail API + OAuth2. |

## Install (each PC, once)

```bash
hermes skills tap add shein888/cute-hermes
hermes skills install shein888/cute-hermes/skills/outlook-com
hermes skills install shein888/cute-hermes/skills/gmail-oauth
```

- Use `owner/repo` (`shein888/cute-hermes`) for `tap add`, **not** the full
  `https://github.com/...` URL — Hermes stores the text as-is and the URL form
  finds nothing. If you already added the URL form, remove it:
  `hermes skills tap remove https://github.com/shein888/cute-hermes`
- `tap add` only registers this repo as a source (`hermes skills search outlook`
  will then list the skills); `install` is what copies them to `~/.hermes/skills/`.
- Scripts are installed together with each skill. Nothing is downloaded with curl.

Then just ask Hermes: 「幫我查 Outlook 最近三天的信」 or 「幫我看 gm 信箱有沒有新信」.
The first gm request opens a Google sign-in page once per PC.

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
            └── gmail_oauth.py
```

Rules for editing:
- Reference scripts in SKILL.md as `${HERMES_SKILL_DIR}/scripts/...`.
- Do **not** put `curl ... | bash` (or any remote download-and-run) in SKILL.md or
  scripts: the Hermes install scanner rates it critical and blocks the install,
  even with `--force`.
- Keep user data (tokens, results) outside the skill folder; `update` replaces the folder.
