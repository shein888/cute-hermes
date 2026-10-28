---
name: outlook-com
description: "Read Outlook mail via PowerShell COM (MAPI). Use when the user asks to read, search, or summarize their Outlook inbox, or mentions reading Outlook emails. Works with WSL or pure Windows."
version: 4.0.0
author: shein
platforms: [windows, wsl]
metadata:
  hermes:
    tags: [outlook, email, mapi, com, powershell, windows]
    homepage: https://learn.microsoft.com/en-us/office/client-developer/outlook/
---

# Outlook COM (PowerShell MAPI)

Read Outlook mail via the MAPI COM object. No password needed — uses the
already-authenticated Outlook profile. The PST file is read in-place; no copy required.

**Works both with WSL and pure Windows.** The core is a PowerShell script
(`outlook-search.ps1`); the `.sh` wrapper is only for WSL convenience.

## When to Use

- "Read my inbox" / "What emails did I get today?"
- "Search my Outlook for X" / "Do I have a mail about 法規彙編?"
- "Summarize my unread mail"
- Any request to inspect Outlook mail content

## Before You Do Anything (MANDATORY first step)

Run the setup script once per session (idempotent, < 2 s). It deploys to the
**current** Windows user's profile (detected via `%USERPROFILE%`):

```bash
curl -fsSL https://raw.githubusercontent.com/shein888/cute-hermes/main/outlook-com/scripts/setup-outlook-search.sh | bash
```

| File | Where | Purpose |
|------|-------|---------|
| `outlook-search.ps1` | `%USERPROFILE%` | Core search logic (Windows PowerShell 5.1, UTF-8 BOM) |
| `outlook-search.cmd` | `%USERPROFILE%` | Wrapper for cmd / pure Windows |
| `outlook-search.sh`  | WSL `~`        | Wrapper for WSL — finds the Windows profile itself |

**NEVER hard-code a Windows username or path** (e.g. `C:\Users\shein`).
From WSL always call `bash ~/outlook-search.sh ...`; on pure Windows call
`%USERPROFILE%\outlook-search.cmd ...`.

**Do NOT kill Outlook.** v4 attaches to the running Outlook (or starts it
in the background). Killing Outlook can corrupt the OST/PST and is not needed.

## If it fails on a PC: run the diagnose first

```bash
bash ~/outlook-search.sh -Diagnose
```

Read the output and tell the user the cause in plain words:

| Diagnose shows | Meaning / fix |
|----------------|---------------|
| `ComRegistered: False` + `NewOutlookInstalled: True` | PC uses **New Outlook** (olk.exe) — it has no COM. Switch back to classic Outlook (toggle "New Outlook" off) or install Microsoft 365 desktop Outlook. |
| `ComRegistered: False` | Classic Outlook not installed. |
| `COM test: FAILED ... 80080005` | Outlook and PowerShell run with different privileges (one is "Run as administrator"). Run both normally. |
| `AntivirusRegistered: NONE` or `ObjectModelGuardPolicy` set | Outlook shows a hidden "A program is trying to access e-mail address information" prompt → script hangs. Fix antivirus status (Trust Center > Programmatic Access) or ask IT to allow programmatic access via GPO. |
| `ExecutionPolicy: MachinePolicy=AllSigned/Restricted` | Group Policy blocks scripts; `-ExecutionPolicy Bypass` cannot override it. Ask IT. |
| `powershell.exe not reachable from WSL` | WSL interop disabled (`/etc/wsl.conf` `[interop] enabled=false` or `appendWindowsPath=false`). |
| Profile chooser dialog | Control Panel > Mail > Show Profiles > "Always use this profile". |

## Search

| Parameter | Description |
|-----------|-------------|
| `-Keyword` | Subject contains (case-insensitive) |
| `-Sender` | Sender email or name contains (case-insensitive) |
| `-Date` | Exact day (yyyy-MM-dd) |
| `-Days` | Last N days |
| `-Folder` | One subfolder of the Inbox |
| `-Recursive` | All folders of the default mailbox (slower) |
| `-Max` | Stop after N matches (default 100) |
| `-Diagnose` | Environment check, no search |

```bash
# WSL
bash ~/outlook-search.sh -Keyword "114-2"
bash ~/outlook-search.sh -Sender "prac" -Date "2026-10-16"
bash ~/outlook-search.sh -Keyword "法規" -Days 3
bash ~/outlook-search.sh -Folder "02-圖資中心" -Days 1
bash ~/outlook-search.sh -Keyword "test" -Recursive

# Pure Windows
%USERPROFILE%\outlook-search.cmd -Sender "prac" -Date "2026-10-16"
```

The wrapper prints the result file. It is also saved to
`%USERPROFILE%\search-result.txt` (UTF-8). Exit code 0 = OK, 2 = bad
arguments, 3 = Outlook/COM/environment problem (message in the result file).

The Inbox is found with `GetDefaultFolder(olFolderInbox)`, so it works with
any Outlook language (收件匣 / 收件箱 / Inbox) and any account name.
Date filters stop scanning early (items are sorted newest first), so
`-Days` / `-Date` are fast even on large mailboxes — prefer them.

**Use the user's exact original string as the search keyword.** Do NOT split
it into smaller keywords. Pick a distinctive substring such as `"114-2"`;
prefixes like "FW:", "RE:", "【重要】" do not matter because matching uses
"contains".

## MailItem Class IDs

| Class ID | Type |
|----------|------|
| 43 | MailItem |
| 26 | AppointmentItem |
| 13 | ContactItem |
| 31 | TaskItem |
| 3 | PostItem |

Use `$item.Class` to check type before accessing type-specific properties.

## Common Filters

```powershell
# Today
$items = $inbox.Items.Restrict("[ReceivedTime] > '2026-10-13'")

# Unread
$items = $inbox.Items.Restrict("[Unread] = 1")

# From specific sender
$items = $inbox.Items.Restrict("[SenderEmailAddress] = 'someone@example.com'")
```

## Pitfalls

1. **Timeout** — the first COM call can take 10-30 s while Outlook loads the
   profile. Use a tool timeout of 120 s or more; `-Recursive` can take 60-120 s.
2. **Hidden security prompt** — if a search hangs, run `-Diagnose`
   (see the table above). It is a PC setting, not a script bug.
3. **Encoding** — never pass Chinese via `powershell.exe -Command`. Use the
   `.ps1` file (saved as UTF-8 with BOM) and read the UTF-8 result file.
   When writing a new .ps1 from WSL, use Python `encoding='utf-8-sig'`.
4. **WSL paths** — PowerShell cannot open `/mnt/c/...` paths; the wrapper
   converts them with `wslpath`.
5. **Body truncation** — results include the first 500 chars of the body.

## Finding the Account Name

```powershell
foreach ($f in $ns.Folders) {
    Write-Host "$($f.Name) [$($f.Items.Count)]"
}
```

The account folder is the one containing `@` in its name (e.g., `shein@cute.edu.tw`).

## Distributing to Other PCs

**One-liner deploy (agent can run this for the user):**

```bash
curl -fsSL https://raw.githubusercontent.com/shein888/cute-hermes/main/outlook-com/scripts/setup-outlook-search.sh | bash
```

This deploys `outlook-search.ps1` + `.cmd` to the current Windows user's
profile and `outlook-search.sh` to the WSL home directory. After that, the agent just runs:

```
bash ~/outlook-search.sh -Sender "prac" -Date "2026-10-16"
```

**Manual deploy (if the one-liner doesn't work):**
1. Copy `scripts/outlook-search.ps1` + `scripts/outlook-search.cmd` to `%USERPROFILE%\`
2. Run `outlook-search.cmd -Diagnose`, then `outlook-search.cmd -Days 1`
3. No WSL required, no install needed

**Via Hermes skills sync:**
- Put the skill folder in a shared GitHub repo
- On the other PC: `hermes skills tap add <github-url>`
- Or copy the skill folder to the other PC's `~/.hermes/outlook-com/`
