---
name: gmail-oauth
description: "gm 帳號 (gm.cute.edu.tw Google Workspace) via OAuth2: read/search/send/reply Gmail, notify on new gm mail (新信通知), AND list/search/read/download/upload/organize Google Drive (雲端硬碟) files. Use when the user mentions 'gm信箱', 'gm 帳號', 'gm 雲端硬碟', 'Google Drive', 'gm drive', gm.cute.edu.tw. No App Password or 2-Step Verification needed."
version: 2.4.0
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

## Authorization is automatic — handle `AUTH_REQUIRED` / `REAUTH_REQUIRED`

Just run the command the user needs (Step 3 / 3b). The script records, per PC,
which gm account authorized which features (gmail, drive) and when. If this PC
has no authorization yet, or the command needs a feature that was not granted
before (e.g. Drive after an older Gmail-only setup), the command does NOT run;
it prints instead (exit code 5):

```
REAUTH_REQUIRED: lic@gm.cute.edu.tw authorized only gmail; 'drive' needs one more consent ...
AUTH_URL: https://accounts.google.com/o/oauth2/v2/auth?...
```

Then:

1. **Send the user the full AUTH_URL as a clickable link** and say:
   「請點這個連結，用 gm.cute.edu.tw 帳號登入並按『允許』，完成後跟我說」.
   No logout is needed — existing access is kept and the new permission is added.
2. When the user says done, run:

   ```bash
   bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" wait --timeout 120
   ```

   | exit | meaning |
   |------|---------|
   | 0 `[OK] Authorized <account> for: drive, gmail` | Re-run the user's original command |
   | 4 `Still waiting` | User has not clicked Allow yet → ask them, run `wait` again |
   | 2 `No active login` | Link expired (10 min) → re-run the original command to get a new link |
   | 1 `ERROR` | Show the message to the user (e.g. signed in with a non-gm account) |

3. If the user's browser ends on a page that cannot load
   (`http://127.0.0.1:.../?state=...&code=...`, the agent runs on another machine),
   ask for that full address and run:

   ```bash
   bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" import-code '<pasted URL>'
   ```

Never edit the script's scopes yourself and never use `urn:ietf:wg:oauth:2.0:oob`.

### Which account / permissions does this PC have?

```bash
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" status
```

Shows the gm account, `gmail: yes/NOT YET`, `drive: yes/NOT YET`, when and by
which skill version it was authorized. `~/.config/gmail-oauth/auth-history.log`
keeps one line per authorization.

To switch to a **different gm account** (only when the user asks):
`bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" logout`, then run any command and
send the new AUTH_URL.

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

## Step 3c — 新信通知 (notify the user when new gm mail arrives)

Without this, the skill only looks at Gmail when the user asks. When the user
wants to be told about new mail (「gm 有新信要通知我」), set up a **no-agent**
scheduled job: every 5 minutes it runs a script that prints only mail that
arrived since the last check. No new mail → no output → no message, no tokens.

1. Make sure Gmail is authorized (`status` shows `gmail : yes`; if not, run
   `list` once and follow the AUTH_URL flow).
2. Write the cron script into Hermes' scripts folder:

   ```bash
   bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" install-watch
   ```

3. Create the job with **your scheduled-task tool** (`cronjob_manage`), not the
   `hermes cron create` CLI (the CLI defaults to `deliver: local`, which the user
   never sees):

   ```
   action="create", name="gm-new-mail", schedule="every 5m",
   script="gm-new-mail.sh", no_agent=True, deliver="origin"
   ```

   `origin` sends the notices to this conversation. If the user prefers their
   Bot Chat or Telegram, use `deliver="bot-chat"` or `"telegram"` instead.
4. Tell the user: 「已設定 gm 新信通知：每 5 分鐘檢查一次，有新信會在這裡通知你。
   要停止請說『停止 gm 新信通知』。」

Notes:
- Mail that was already in the inbox before setup is not reported; only new arrivals.
- If the PC is off or Hermes is closed, checks pause; mail that arrived meanwhile
  is reported at the next check (up to a few days back).
- The script never opens an authorization flow. If Gmail is not authorized it
  reminds the user once a day; if Gmail is unreachable for about an hour it says so once.
- Stop: `cronjob_manage` action="remove" (or "pause") on job `gm-new-mail`.
  Change frequency: action="edit", schedule="every 10m".
- Reinstalling the skill does not break the job (same install path); do not remove it.

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
| `AUTH_REQUIRED` / `REAUTH_REQUIRED` (exit 5) | Send the AUTH_URL, then `wait` (see above) |
| `invalid_grant` | User revoked access or reset password → `logout`, then any command gives a new AUTH_URL |
| `Error 400: invalid_request` on Google's page | Old script version — run `hermes skills update gmail-oauth` |
| `access_denied` / `org_internal` | The user signed in with a non-gm.cute.edu.tw account → sign in with the gm account |
| `Gmail API error 403 ... has not been used / disabled` | Gmail API disabled in project hermes-gm → tell the IT admin |
| `Google Drive API is not enabled` | Drive API disabled in project hermes-gm → tell the IT admin |
| `Python 3 not found` | Install Python once (`winget install Python.Python.3.12`), then retry |

The access token expires every hour and is refreshed automatically.

