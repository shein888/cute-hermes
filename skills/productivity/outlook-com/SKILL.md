---
name: outlook-com
description: "Read Outlook mail via PowerShell COM (MAPI). Use when the user asks to read, search, or summarize their Outlook inbox, or mentions reading Outlook emails. Works with WSL or pure Windows."
version: 2.0.0
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

## Setup on a New PC (one-time)

Copy the bundled scripts to `C:\Users\<username>\`:

| File | Purpose |
|------|---------|
| `outlook-search.ps1` | Core search logic (PowerShell) |
| `outlook-search.cmd` | Windows command-line wrapper |

**No WSL needed.** The `.cmd` works in any Windows `cmd.exe` or PowerShell.
Use `%USERPROFILE%` instead of hardcoding the username path:

```
cmd /c "%USERPROFILE%\outlook-search.cmd 114-2"
```

The `.sh` wrapper (`outlook-search.sh`) is optional — only for WSL users.

**IMPORTANT: Replace `<username>` with the actual Windows username on the target PC.**
Use `%USERPROFILE%` (Windows) or `$env:USERNAME` (PowerShell) — never hardcode a username.

## Step 1: Kill Outlook

```bash
# WSL
/mnt/c/Windows/System32/taskkill.exe /F /IM OUTLOOK.EXE 2>&1
sleep 2

# Pure Windows
taskkill /F /IM OUTLOOK.EXE 2>nul
```

## Step 2: Run the search script

The script supports three parameters:

| Parameter | Description |
|-----------|-------------|
| `-Keyword` | Search by subject substring |
| `-Days` | Only show mail from last N days (1=24h, 3=3days) |
| `-Folder` | Limit to specific inbox subfolder |

```bash
# WSL
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\<username>\outlook-search.ps1" -Keyword "KEYWORD" -Days 1

# Pure Windows (via .cmd)
cmd /c "%USERPROFILE%\outlook-search.cmd -Keyword KEYWORD -Days 1"
```

**Common patterns:**

```bash
# Search by keyword (all time)
"C:\Users\shein\outlook-search.cmd" -Keyword "114-2"

# Last 24 hours, all mail
"C:\Users\shein\outlook-search.cmd" -Days 1

# Last 3 days, keyword search
"C:\Users\shein\outlook-search.cmd" -Keyword "法規" -Days 3

# Specific folder, last 24h
"C:\Users\shein\outlook-search.cmd" -Folder "02-圖資中心" -Days 1
```

**CRITICAL: Use the user's exact original string as the search keyword.** Do NOT
split it into smaller keywords or guess. If the user says "檢核114-2、115-1全校
法規彙編作業", search for a distinctive substring like `"114-2"` — the user's
string will still match via `.Contains()`. Subjects often have prefixes ("FW:",
"RE:", "【重要】") that break exact `-eq` matching but NOT `.Contains()`.

### Read today's inbox

```powershell
# inline (write to .ps1 file if it contains Chinese)
$outlook = New-Object -ComObject Outlook.Application
$ns = $outlook.GetNamespace('MAPI')
$account = $ns.Folders | Where-Object { $_.Name -like "*@*" } | Select-Object -First 1
$inbox = $account.Folders | Where-Object { $_.Name -eq "收件匣" -or $_.Name -eq "Inbox" } | Select-Object -First 1
if ($inbox -eq $null) { $inbox = $account.Folders | Select-Object -First 1 }

$startOfDay = (Get-Date).Date.ToString('yyyy-MM-dd')
$items = $inbox.Items.Restrict("[ReceivedTime] > '$startOfDay'")

$lines = @()
$lines += "Inbox: $($inbox.Name) | Count: $($items.Count)"
foreach ($item in $items) {
    $lines += "---"
    $lines += "From: $($item.SenderName)"
    $lines += "Date: $($item.ReceivedTime.ToString('yyyy-MM-dd HH:mm:ss'))"
    $lines += "Subject: $($item.Subject)"
    if ($item.Body) {
        $b = $item.Body.Substring(0, [Math]::Min(500, $item.Body.Length))
        $lines += "Body: $($b -replace \"`r`n\", ' | ')"
    }
    $lines += ""
}
[System.IO.File]::WriteAllLines("C:\Users\<username>\mail-result.txt", $lines, [System.Text.Encoding]::UTF8)
```

## Step 3: Read results

The script writes results to `C:\Users\<username>\search-result.txt` (UTF-8):

```bash
# WSL
cat /mnt/c/Users/<username>/search-result.txt

# Pure Windows
type C:\Users\shein\search-result.txt
```

## Step 4: Cleanup

```bash
# WSL
/mnt/c/Windows/System32/taskkill.exe /F /IM OUTLOOK.EXE 2>&1

# Pure Windows
taskkill /F /IM OUTLOOK.EXE 2>nul
```

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

1. **Outlook locks MAPI** — if Outlook is open, COM hangs or profile conflicts. Always `taskkill /F /IM OUTLOOK.EXE` first, `sleep 2`.

2. **Encoding** — inline PowerShell `-Command` with Chinese text breaks. Always write to `.ps1` file and use `-File`.

3. **Folder names vary by locale** — 收件匣 (tw), 收件箱 (zh-cn), Inbox (en). Try multiple names or just take the first folder.

4. **Large inboxes** — always use `Restrict()` filter. Iterating 13k+ items takes 60+ seconds.

5. **Timeout** — first COM call takes 10-30s (Outlook loads MAPI profile). Set `timeout=120`.

6. **Body truncation** — truncate to ~500 chars for summaries. `$item.BodyPreview` gives ~100 chars.

7. **WSL path for -File** — use `C:\Users\shein\script.ps1`, NOT `/mnt/c/Users/shein/script.ps1`. PowerShell can't resolve `/mnt/` paths.

8. **Result file** — write to a file (UTF-8) then read it. Console output from WSL calling Windows PowerShell often garbles Chinese characters.

9. **Use the user's exact original string for search** — use `.Contains()` with the user's verbatim text. Do NOT split into sub-keywords or guess.

10. **Writing .ps1 from WSL with Chinese text** — use Python with `utf-8-sig` encoding. `cat > file.ps1 << 'EOF'` heredoc will corrupt Chinese characters.

```python
with open('/mnt/c/Users/shein/search.ps1', 'w', encoding='utf-8-sig') as f:
    f.write(ps1_content)
```

## Finding the Account Name

```powershell
foreach ($f in $ns.Folders) {
    Write-Host "$($f.Name) [$($f.Items.Count)]"
}
```

The account folder is the one containing `@` in its name (e.g., `shein@cute.edu.tw`).

## Distributing to Other PCs

The skill bundles two files in `scripts/`:
- `scripts/outlook-search.ps1` — core search logic
- `scripts/outlook-search.cmd` — Windows wrapper

**To deploy on another PC:**
1. Copy both files to `C:\Users\<username>\`
2. Run `outlook-search.cmd "keyword"` — that's it
3. No WSL required, no install needed

**Via Hermes skills sync:**
- Put the skill folder in a shared GitHub repo
- On the other PC: `hermes skills tap add <github-url>`
- Or copy the skill folder to the other PC's `~/.hermes/skills/productivity/outlook-com/`
