# Cute Hermes Skills

Shared Hermes Agent skills for the CUTE (National Chiao Tung University) IT team.

## Installation

```bash
hermes skills tap add https://github.com/shein888/cute-hermes
```

That's it. When you ask Hermes to read Outlook or Gmail, it will
automatically run the setup script and deploy the tools.

## Skills

### outlook-com

Read and search Outlook mail via PowerShell COM (MAPI). Works on Windows and WSL.

- No WSL required (uses `.cmd` wrapper)
- No password needed (uses authenticated Outlook profile)
- Search inbox + subfolders by keyword, sender, date

```bash
# WSL (auto-deploys on first use)
bash ~/outlook-search.sh -Sender "prac" -Date "2026-10-16"

# Pure Windows
outlook-search.cmd -Sender "prac" -Date "2026-10-16"
```

### gmail-oauth

Read and send Gmail / Google Workspace mail via Gmail API with OAuth2.

- No App Password needed (uses OAuth2 with auto-refresh)
- No 2FA required
- First use opens browser for Google sign-in, then done forever

```bash
# Auto-deploys on first use (browser opens for auth)
python3 ~/gmail_oauth.py list
```

## Repo Structure

```
cute-hermes/
├── README.md
├── outlook-com/
│   ├── SKILL.md
│   └── scripts/
│       ├── outlook-search.ps1
│       ├── outlook-search.cmd
│       ├── outlook-search.sh
│       └── setup-outlook-search.sh
└── gmail-oauth/
    ├── SKILL.md
    └── scripts/
        ├── gmail_oauth.py
        └── setup-gmail-oauth.sh
```
