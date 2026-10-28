---
name: outlook-com
description: "Search and read the user's Outlook (classic Outlook desktop, cute.edu.tw) mail via PowerShell COM/MAPI. Use when the user asks to read, search or summarize Outlook mail, or mentions Outlook / 學校信箱 cute.edu.tw. Works from WSL or Windows. For gm.cute.edu.tw (gm 信箱) use the gmail-oauth skill instead."
version: 4.1.1
author: shein
platforms: [windows, linux]   # "linux" = Hermes in WSL (Hermes has no "wsl" platform name)
metadata:
  hermes:
    tags: [outlook, email, mapi, com, powershell, windows]
    homepage: https://learn.microsoft.com/en-us/office/client-developer/outlook/
---

# Outlook COM (PowerShell MAPI)

Searches the already-signed-in **classic Outlook** profile through COM. No
password needed. The scripts ship with this skill — nothing to download.

One command for every setup — Hermes Desktop / Hermes for Windows (Git Bash)
and Hermes in WSL:

```bash
bash "${HERMES_SKILL_DIR}/scripts/outlook-search.sh" <args>
```

Keep the path in double quotes exactly as above (on Windows it contains
backslashes and may contain spaces). The wrapper runs `outlook-search.ps1`
with Windows PowerShell and prints the result (UTF-8); it is also saved to
`%USERPROFILE%\search-result.txt`.

**Rules**
- Never hard-code a Windows username or path such as `C:\Users\<name>`.
- Do **not** kill Outlook — the script attaches to the running Outlook or starts it.
- Use a tool timeout of at least 120 s (first COM call 10-30 s; `-Recursive` up to 2 min).

## Search

| Parameter | Description |
|-----------|-------------|
| `-Keyword` | Subject contains (case-insensitive) |
| `-Sender` | Sender e-mail or display name contains (case-insensitive) |
| `-Date` | One day, `yyyy-MM-dd` |
| `-Days` | Last N days |
| `-Folder` | One sub-folder of the Inbox, e.g. `"02-圖資中心"` |
| `-Recursive` | Every folder of the default mailbox (slower) |
| `-Max` | Stop after N matches (default 100) |
| `-Diagnose` | Check this PC instead of searching |

```bash
bash "${HERMES_SKILL_DIR}/scripts/outlook-search.sh" -Days 1
bash "${HERMES_SKILL_DIR}/scripts/outlook-search.sh" -Keyword "114-2"
bash "${HERMES_SKILL_DIR}/scripts/outlook-search.sh" -Sender "prac" -Date "2026-10-16"
bash "${HERMES_SKILL_DIR}/scripts/outlook-search.sh" -Keyword "法規" -Days 3
bash "${HERMES_SKILL_DIR}/scripts/outlook-search.sh" -Folder "02-圖資中心" -Days 1
bash "${HERMES_SKILL_DIR}/scripts/outlook-search.sh" -Keyword "test" -Recursive
```

Without `-Recursive` the search covers the Inbox and its direct sub-folders.
The Inbox is found with `GetDefaultFolder`, so any Outlook language
(收件匣 / 收件箱 / Inbox) and any account name works. Prefer `-Days`/`-Date`:
the scan stops at the first older mail, so it is fast on big mailboxes.

Use the user's own words as the keyword. Pick one distinctive substring
(e.g. `"114-2"` from 「檢核114-2、115-1全校法規彙編作業」) instead of splitting it
into several guesses. "FW:", "RE:", "【重要】" prefixes do not matter.

Exit codes: 0 = OK, 2 = bad arguments, 3 = Outlook / COM / environment
problem (the reason is printed).

## When it fails on a PC → run the diagnose

```bash
bash "${HERMES_SKILL_DIR}/scripts/outlook-search.sh" -Diagnose
```

Explain the cause to the user in plain words:

| Diagnose shows | Meaning / fix |
|----------------|---------------|
| `ComRegistered: False`, `NewOutlookInstalled: True` | The PC uses **New Outlook** (olk.exe), which has no COM. Turn off the "New Outlook" toggle to go back to classic Outlook, or install Microsoft 365 desktop Outlook. |
| `ComRegistered: False` | Classic Outlook is not installed. |
| `COM test: FAILED ... 80080005` | Outlook and PowerShell run with different privileges (one is "Run as administrator"). Run both normally. |
| `AntivirusRegistered: NONE` or `ObjectModelGuardPolicy` not default; search hangs | Outlook shows a hidden "A program is trying to access e-mail address information" prompt. Fix the antivirus status (File > Options > Trust Center > Programmatic Access) or ask IT to allow programmatic access by GPO. |
| `ExecutionPolicy: MachinePolicy=AllSigned` / `Restricted` | Group Policy blocks scripts; `-ExecutionPolicy Bypass` cannot override it. Ask IT. |
| `powershell.exe not reachable` | WSL interop is off (`/etc/wsl.conf`). |
| `Outlook COM needs Windows` | Hermes runs on Linux/macOS or a remote gateway — Outlook COM only works on the Windows PC that has Outlook. |
| Outlook asks which profile to use | Control Panel > Mail > Show Profiles > "Always use this profile". |

## Item classes (for custom PowerShell)

| Class | Type |
|-------|------|
| 43 | MailItem |
| 26 | AppointmentItem |
| 13 | ContactItem |
| 31 | TaskItem |

If you write extra PowerShell, save it as a `.ps1` with UTF-8 BOM
(Python `encoding='utf-8-sig'`) and run it with `-File`; never pass Chinese
text through `powershell.exe -Command`.
