---
name: gmail-oauth
description: "Read, search, send and reply to Gmail (Google Workspace) mail via the Gmail API with OAuth2. Use when the user mentions 'gm信箱', 'gm 帳號', 'gm account', gm.cute.edu.tw, or asks to read/search/send Gmail. No App Password or 2-Step Verification needed."
version: 2.1.0
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

- `Refresh token: present` → go to Step 3.
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

## Step 3 — do what the user asked

```bash
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" list                 # newest 10 in Inbox
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" list 30
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" search "from:prac@cute.edu.tw after:2026-10-01"
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" search "subject:課程大綱 is:unread" 20
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" read MESSAGE_ID      # headers, attachments, text body
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" send "someone@cute.edu.tw" "Subject" "Body text"
bash "${HERMES_SKILL_DIR}/scripts/gmail.sh" reply "someone@cute.edu.tw" THREAD_ID "Reply body"
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
| `Python 3 not found` | Install Python once (`winget install Python.Python.3.12`), then retry |

The access token expires every hour and is refreshed automatically.
