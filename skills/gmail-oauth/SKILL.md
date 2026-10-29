---
name: gmail-oauth
description: "gm 帳號 (gm.cute.edu.tw Google Workspace) via OAuth2: read/search/send/reply Gmail AND list/search/read/download/upload/organize Google Drive (雲端硬碟) files. Use when the user mentions 'gm信箱', 'gm 帳號', 'gm 雲端硬碟', 'Google Drive', 'gm drive', gm.cute.edu.tw. No App Password or 2-Step Verification needed."
version: 2.2.2
author: shein
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [gmail, email, google-drive, drive, oauth2, google-workspace, gm信箱, 雲端硬碟]
    homepage: https://developers.google.com/gmail/api
---

# gm 帳號: Gmail + Google Drive via OAuth2 (gm 信箱 / gm 雲端硬碟)

The team calls this account the **"gm 帳號"**: its mail is the "gm 信箱" and
its Google Drive is the "gm 雲端硬碟". Any mention of "gm信箱", "gm 雲端硬碟",
"Google Drive", "gm account" or "gm.cute.edu.tw" means this Google Workspace
account — NOT the Outlook (cute.edu.tw) mailbox, which is the `outlook-com` skill.
One authorization covers both Gmail and Drive.

Everything runs through one wrapper that ships with this skill. It finds a
working Python 3 by itself (Windows Git Bash, WSL, Linux, macOS):

```bash
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" <command> ...
```

Always keep the path in double quotes exactly as above (on Windows it contains
backslashes and may contain spaces). Do not call `python3` directly — on
Windows `python3` is often only a Microsoft Store stub.

The OAuth client (Google Cloud project `hermes-gm`, Internal app) is built
into the script. **Do not ask the user for a client ID or secret.**
The user's token is stored in `~/.config/gmail-oauth/token.json`, outside the
skill directory, so it survives `hermes skills update`.

## Step 1 — check authorization

```bash
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" status
```

- `Refresh token: present` and `Drive: yes` → go to Step 3.
- `Drive: NO` (authorized by an older version, Gmail only) and the user wants
  Drive → run `logout`, then Step 2 once.
- `No token` → Step 2 (one time per gm account / per PC).

## Step 2 — authorize (first time only)

```bash
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" setup
```

This returns within a few seconds. It prints a line starting with `AUTH_URL:`,
tries to open the browser, and keeps listening in the background for 10 minutes.

1. **Immediately send the user the full AUTH_URL as a clickable link** and say:
   「請點這個連結，用 gm.cute.edu.tw 帳號登入並按『允許』，完成後跟我說」.
   Do this even if the output says the browser was opened.
2. When the user says they are done (or right away), run:

   ```bash
   bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" wait --timeout 120
   ```

   | exit | meaning |
   |------|---------|
   | 0 `[OK] Authorized` | Done → Step 3 |
   | 4 `Still waiting` | User has not clicked Allow yet → ask them, run `wait` again |
   | 2 `No active login` | Timed out → run `setup` again and send the new link |
   | 1 `ERROR` | Show the message to the user (e.g. wrong account) |

3. If the browser on the user's side ends on a page that cannot load
   (`http://127.0.0.1:8765/?state=...&code=...`) — the agent runs on another
   machine than the browser — ask the user to copy that full address and paste
   it here, then run:

   ```bash
   bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" import-code '<pasted URL>'
   ```

   Only the URL from the **latest** `setup` works.

Never use `urn:ietf:wg:oauth:2.0:oob` — Google has disabled that flow.

## Step 3 — Gmail (gm 信箱)

```bash
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" list                 # newest 10 in Inbox
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" list 30
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" search "from:prac@cute.edu.tw after:2026-10-01"
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" search "subject:課程大綱 is:unread" 20
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" read MESSAGE_ID      # headers, attachments, text body
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" send "someone@cute.edu.tw" "Subject" "Body text"
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" reply "someone@cute.edu.tw" THREAD_ID "Reply body"
```

Use only these commands to read mail — never write your own Gmail/MIME parsing
code. If a subject still looks like `=?UTF-8?B?...` the skill is outdated:
tell the user to update it (README 標準流程).

`list` / `search` print one block per message:

```
[1] 2026-10-28 19:11  (UNREAD)
    From:    darch darch (透過 Google 試算表) <drive-shares-dm-noreply@google.com>
    Subject: 有人與你共用了試算表：「個資盤點清冊-建築系115年」
    ID: 19a2...    THREAD: 19a2...
```

When you show mail to the user, copy `From` and `Subject` from the **same block**
— never re-pair them. Use ID for `read`, THREAD for `reply`.

**Always show the user the recipient, subject and body and get a clear "yes"
before running `send` or `reply`.**

## Step 3b — Google Drive (gm 雲端硬碟)

```bash
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" drive-list                      # 20 most recently modified
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" drive-list 50
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" drive-list FOLDER_ID            # contents of a folder
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" drive-search "課程大綱"          # name or content contains
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" drive-search "mimeType = 'application/pdf' and modifiedTime > '2026-10-01'"
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" drive-info FILE_ID
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" drive-read FILE_ID              # text of Docs/Sheets(CSV)/Slides/txt
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" drive-download FILE_ID          # to ~/Downloads (Docs->docx, Sheets->xlsx, Slides->pptx)
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" drive-download FILE_ID "C:/Users/me/Desktop"
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" drive-upload "C:/path/report.pdf" [FOLDER_ID]
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" drive-mkdir "新資料夾" [PARENT_FOLDER_ID]
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" drive-rename FILE_ID "新名稱"
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" drive-move FILE_ID FOLDER_ID
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" drive-trash FILE_ID             # to trash, recoverable 30 days
```

- Listings print `ID  MODIFIED  TYPE  SIZE  NAME`; `g-document` / `g-spreadsheet` /
  `g-presentation` are Google files, `folder` is a folder. Use the ID for other commands.
- Shared drives (共用雲端硬碟) and files shared with the user are included.
- `drive-read` only handles text-like files; for PDF/Word/Excel use
  `drive-download`, then open the saved file with your own file tools.
- Use forward slashes in Windows paths (`C:/Users/...`) and keep them in quotes.
- **Before `drive-upload`, `drive-mkdir`, `drive-rename`, `drive-move` or
  `drive-trash`, tell the user exactly what will change and get a clear "yes".**
  There is no permanent-delete command on purpose.
- `DRIVE_SCOPE_MISSING` → this PC was authorized for Gmail only: run `logout`,
  then Step 2, and ask the user to click Allow again.

## Gmail search syntax

| Query | Meaning |
|-------|---------|
| `from:address` / `to:address` | Sender / recipient |
| `subject:keyword` | Subject contains |
| `after:YYYY-MM-DD` / `before:YYYY-MM-DD` | Date range |
| `newer_than:2d` | Last 2 days |
| `is:unread` / `is:starred` | Flags |
| `has:attachment` | Has attachments |
| `label:name` | In label |

## Errors

| Output | Meaning / action |
|--------|------------------|
| `NO_TOKEN` | Not authorized yet → Step 2 |
| `invalid_grant` | User revoked access or reset password → Step 2 again |
| `Error 400: invalid_request` on Google's page | Old script version — run `hermes skills update gmail-oauth` |
| `access_denied` / `org_internal` | The user signed in with a non-gm.cute.edu.tw account → sign in with the gm account |
| `Gmail API error 403 ... has not been used / disabled` | Gmail API disabled in project hermes-gm → tell the IT admin |
| `Google Drive API is not enabled` | Drive API disabled in project hermes-gm → tell the IT admin |
| `DRIVE_SCOPE_MISSING` | Authorized before Drive was added → `logout`, then Step 2 |
| `Python 3 not found` | Install Python once (`winget install Python.Python.3.12`), then retry |

The access token expires every hour and is refreshed automatically.

To switch to another gm account or start over (only when the user asks, or
`status` shows `Refresh token: MISSING` / `invalid_grant`):

```bash
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" logout
```

then run Step 2 again.
