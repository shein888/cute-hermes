# Cute Hermes Skills

Shared Hermes Agent skills for the CUTE (National Chiao Tung University) IT team.

## Installation

```bash
hermes skills tap add shein888/cute-hermes
```

Or clone and copy:

```bash
git clone https://github.com/shein888/cute-hermes.git
cp -r cute-hermes/skills/productivity/outlook-com ~/.hermes/skills/productivity/
```

## Skills

### outlook-com

Read and search Outlook mail via PowerShell COM (MAPI). Works on Windows and WSL.

- No WSL required (uses `.cmd` wrapper)
- No password needed (uses authenticated Outlook profile)
- Search all inbox subfolders by keyword

```bash
# WSL
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\<username>\outlook-search.ps1" "keyword"

# Pure Windows
outlook-search.cmd "keyword"
```
