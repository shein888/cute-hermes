---
name: gmail-oauth
description: "Read, search, send and reply to Gmail (Google Workspace) mail via the Gmail API with OAuth2. Use when the user mentions 'gm信箱', 'gm 帳號', 'gm account', gm.cute.edu.tw, or asks to read/search/send Gmail. No App Password or 2-Step Verification needed."
version: 2.0.0
author: shein
platforms: [linux, wsl, windows, macos]
metadata:
  hermes:
    tags: [gmail, email, oauth2, gmail-api, google-workspace, gm信箱]
    homepage: https://developers.google.com/gmail/api
---

# Gmail via OAuth2 (gm 信箱)

The team calls this mailbox the **"gm 信箱"**. Any mention of "gm信箱",
"gm account" or "gm.cute.edu.tw" means this Google Workspace mail — NOT the
Outlook (cute.edu.tw) mailbox, which is the `outlook-com` skill.

Everything runs through one script that ships with this skill:

```bash
python3 ${HERMES_SKILL_DIR}/scripts/gmail_oauth.py <command> ...
```

The OAuth client (Google Cloud project `hermes-gm`, Internal app) is built
into the script. **Do not ask the user for a client ID or secret.**
The user's token is stored in `~/.config/gmail-oauth/token.json`, outside the
skill directory, so it survives `hermes skills update`.

## Step 1 — check authorization

```bash
python3 ${HERMES_SKILL_DIR}/scripts/gmail_oauth.py status
```

- `Refresh token: present` → go to Step 3.
- `No token` → Step 2 (one time per gm account / per PC).

## Step 2 — authorize (first time only)

Run with a tool timeout of at least 240 seconds:

```bash
python3 ${HERMES_SKILL_DIR}/scripts/gmail_oauth.py setup --timeout 180
```

1. The script opens the browser (on WSL: the Windows default browser) and
   ALWAYS prints a line starting with `AUTH_URL:`.
   **Show that full URL to the user right away as a clickable link** and tell
   them: 「請用 gm 帳號登入並按『允許』」. A browser window may not appear when
   the agent runs headless or remotely — the link is the reliable path.
2. When the user clicks Allow, the browser shows 「Gmail 授權完成」 and the
   command prints `[OK] Authorized`. Continue with Step 3.
3. If the command exits with code 2 (`No callback received`), the browser was
   on another machine. Ask the user to copy the full address from the browser
   bar after clicking Allow (it starts with `http://127.0.0.1:8765/?state=`;
   the page itself may fail to load) and paste it here, then run:

   ```bash
   python3 ${HERMES_SKILL_DIR}/scripts/gmail_oauth.py import-code '<pasted URL>'
   ```

   Only the URL from the **latest** `setup` run works.

Never use `urn:ietf:wg:oauth:2.0:oob` — Google has disabled that flow.

## Step 3 — do what the user asked

```bash
G="python3 ${HERMES_SKILL_DIR}/scripts/gmail_oauth.py"

$G list                 # newest 10 in Inbox
$G list 30
$G search "from:prac@cute.edu.tw after:2026-10-01"
$G search "subject:課程大綱 is:unread" 20
$G read MESSAGE_ID      # headers, attachment names, plain-text body
$G send "someone@cute.edu.tw" "Subject" "Body text"
$G reply "someone@cute.edu.tw" THREAD_ID "Reply body"
```

`list` / `search` print `ID`, `THREAD`, date, sender and subject
(`*` before the subject = unread). Use ID for `read`, THREAD for `reply`.

**Always show the user the recipient, subject and body and get a clear "yes"
before running `send` or `reply`.**

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

The access token expires every hour and is refreshed automatically.
