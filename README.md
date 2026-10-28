# Cute Hermes Skills

Shared Hermes Agent skills for the CUTE (National Chiao Tung University) IT team.

## Installation

```bash
hermes skills tap add https://github.com/shein888/cute-hermes
```

That's it. When you ask Hermes to read Outlook or Gmail, it will
automatically run the setup script (idempotent) and deploy the tools.

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

### gmail-himalaya

Read and send Gmail / Google Workspace mail via Himalaya CLI.

- One-liner deploy: installs himalaya + writes config + verifies
- Requires App Password (not account password) for Google Workspace
- Ask the agent: "幫我查 gm 信箱"

```bash
# Auto-deploys on first use (agent asks for App Password if needed)
~/.local/bin/himalaya envelope list --page-size 5
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
└── gmail-himalaya/
    ├── SKILL.md
    └── scripts/
        └── setup-gmail-himalaya.sh
```
