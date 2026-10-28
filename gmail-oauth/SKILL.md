---
name: gmail-oauth
description: "Read and send Gmail (Google Workspace) mail via Gmail API with OAuth2. Use when the user asks to read, search, reply to, or send Gmail emails, or mentions 'gm信箱', 'gm account', managing their gm.cute.edu.tw or other Google Workspace mailbox. No App Password or 2FA required."
version: 1.0.0
author: shein
platforms: [windows, wsl, linux]
metadata:
  hermes:
    tags: [gmail, email, oauth2, gmail-api, google-workspace, gm信箱]
    homepage: https://developers.google.com/gmail/api
---

# Gmail via OAuth2 (gm 信箱)

Read and send Gmail / Google Workspace mail via the **Gmail API** with **OAuth2**.
No App Password needed. No 2FA required. Token auto-refreshes forever.

The user's team calls this the **"gm 信箱"** (gm mailbox) — any mention of
"gm信箱", "gm account", or "gm.cute.edu.tw" refers to this Google Workspace
mail, not the Outlook (cute.edu.tw) mailbox.

## Before You Do Anything (MANDATORY first step)

When the user asks about their gm 信箱, the agent MUST do the following
**in order**. The user should NOT need to type any commands themselves —
the agent handles everything.

### Step 1: Download the script

```bash
curl -sSL -o ~/gmail_oauth.py https://raw.githubusercontent.com/shein888/cute-hermes/main/gmail-oauth/scripts/gmail_oauth.py
```

### Step 2: Write credentials (if not already present)

Check if `~/.config/gmail-oauth/env` exists. If NOT, the agent must
write the credentials. The values are:

- Client ID: `930386946858-3d63m2dmik1caej2cam2c4mtnp83b9jh` + `.apps.googleusercontent.com`
- Client Secret: `GOCSPX-` + `FFjY_zi6Y0jE5TLQDxYLy-9Cs5qS`

Concatenate the parts and write to `~/.config/gmail-oauth/env`:

```bash
mkdir -p ~/.config/gmail-oauth
# Write these two lines (fill in the values above):
#   export GMAIL_OAUTH_CLIENT_ID="<full_client_id>"
#   export GMAIL_OAUTH_CLIENT_SECRET="<full_client_secret>"
chmod 600 ~/.config/gmail-oauth/env
```

**Do NOT ask the user for these. The agent writes them directly.**

### Step 3: Run setup (opens browser for the user)

```bash
python3 ~/gmail_oauth.py setup --timeout 180
```

- On WSL the script opens the **Windows** default browser (via `wslview` /
  `rundll32.exe`); on Windows/macOS/Linux desktop it opens the normal browser.
- The script ALWAYS prints a line starting with `AUTH_URL:`.
  **Immediately show that full URL to the user** as a clickable link, in case
  no browser window appeared (headless server, remote session, sandbox).
- **The user only needs to: sign in to their gm account → click "Allow".**
  The browser then shows "Gmail 授權完成" and the command exits with `[OK] Authorized`.
- The command blocks up to `--timeout` seconds waiting for the callback.
  Run it with a tool timeout longer than that (e.g. 240 s).

If the command exits with code 2 ("No callback received") — e.g. the agent
runs on a different machine than the browser — ask the user to copy the full
address from the browser bar after clicking Allow (it starts with
`http://127.0.0.1:8765/?state=...&code=...`, the page itself may fail to load)
and paste it back. Then run:

```bash
python3 ~/gmail_oauth.py import-code '<the pasted URL>'
```

`import-code` must use the URL from the **latest** `setup`/`auth-url` run
(each run creates a new one-time login in `~/.config/gmail-oauth/pending.json`).
Never use `urn:ietf:wg:oauth:2.0:oob` — Google has disabled the OOB flow.

### Step 4: Verify

```bash
source ~/.config/gmail-oauth/env && python3 ~/gmail_oauth.py status
```

If it shows "Refresh token: present" → ready to use.

### Step 5: Proceed with the user's request

Now run the appropriate command (list, search, read, send).

**If the user says "幫我查 gm 信箱" and there's no token yet:**
→ Do Steps 1-4 above, then proceed. The user only interacts with
  the browser (sign in + Allow). Everything else is the agent's job.

**If a token already exists:** skip Steps 1-4, go straight to Step 5.

## Common Operations

All commands use `python3 ~/gmail_oauth.py`:

### List inbox

```bash
python3 ~/gmail_oauth.py list          # last 10
python3 ~/gmail_oauth.py list 50       # last 50
```

### Search

```bash
# By sender
python3 ~/gmail_oauth.py search "from:prac@cute.edu.tw"

# By subject
python3 ~/gmail_oauth.py search "subject:課程大綱"

# By date
python3 ~/gmail_oauth.py search "after:2026-10-01"

# Combined
python3 ~/gmail_oauth.py search "from:prac@cute.edu.tw after:2026-10-01"
```

`list` and `search` print `ID`, `THREAD`, date, sender and subject
(`*` before the subject = unread). Use the ID for `read`, the THREAD for `reply`.

### Read a message

```bash
python3 ~/gmail_oauth.py read MESSAGE_ID
```

Prints decoded headers (Chinese subjects OK), attachment names and the
plain-text body (HTML-only mail is converted to text).

### Send an email

```bash
python3 ~/gmail_oauth.py send "recipient@example.com" "Subject" "Body text"
```

### Reply

```bash
python3 ~/gmail_oauth.py reply "recipient@example.com" THREAD_ID "Reply body"
```

### Check token status

```bash
python3 ~/gmail_oauth.py status
```

## Gmail Search Syntax

| Query | Meaning |
|-------|---------|
| `from:address` | From sender |
| `to:address` | To recipient |
| `subject:keyword` | Subject contains |
| `after:YYYY-MM-DD` | Sent after date |
| `before:YYYY-MM-DD` | Sent before date |
| `is:unread` | Unread only |
| `is:starred` | Starred only |
| `has:attachment` | Has attachments |
| `label:work` | In label |

## Setup (first time only)

Each gm 帳號 only needs to authorize **once**. After that, the token
auto-refreshes forever (refresh_token). No more browser, no more URL.

### What the user actually does (per gm 帳號, one time)

1. Agent runs the setup script (or user runs the curl command)
2. Browser opens → sign in to gm account → click "Allow"
3. Done — **no more browser, no more URL, no more input**
4. If browser callback fails (WSL/remote) → paste the callback URL back once

### Quick deploy for a new PC

```bash
curl -sSL https://raw.githubusercontent.com/shein888/cute-hermes/main/gmail-oauth/scripts/setup-gmail-oauth.sh | bash
```

That's it. The script handles everything: downloads the Python script,
sets up credentials, opens the browser for sign-in.

No App Password. No 2FA requirement. No IMAP/SMTP config.

## Pitfalls

1. **Token file location** — `~/.config/gmail-oauth/token.json`. If it's
   missing or corrupted, run setup again.

2. **Browser / callback** — the OAuth flow listens on `http://127.0.0.1:8765`
   (override with `GMAIL_OAUTH_PORT`; falls back to a random free port).
   WSL2 forwards Windows `127.0.0.1` to WSL automatically. If the agent and the
   browser are on different machines, use `import-code` (Step 3).

3. **Token auto-refresh** — the access token expires every 1 hour, but the
   script auto-refreshes it using the refresh token. No user action needed.
   If a command prints `invalid_grant`, the user revoked access or changed
   password — run `setup` again. `NO_TOKEN` means setup was never completed.

4. **Multiple accounts** — if the user has multiple Google accounts, the
   browser will let them pick which one to authorize.

5. **WSL paths** — use `python3 ~/gmail_oauth.py` (home dir). The script
   works in WSL, Windows (via WSL), and Linux.

6. **Network** — first API call takes 1-2 seconds. Set `timeout=30`.

## Distributing to Other PCs

**One-liner deploy (agent can run this for the user):**

```bash
curl -sSL https://raw.githubusercontent.com/shein888/cute-hermes/main/gmail-oauth/scripts/setup-gmail-oauth.sh | bash
```

This downloads `gmail_oauth.py` to the user's home directory. If a token
already exists, it just verifies and exits. If not, it runs the OAuth flow
(browser opens, user signs in, done).

## Quick Reference for the Agent

When the user asks about their Gmail (gm 信箱):

1. If `~/.config/gmail-oauth/token.json` exists → skip to step 4
2. If not → do Steps 1-3 from "Before You Do Anything" above:
   - Download the script
   - Write credentials to `~/.config/gmail-oauth/env`
   - Run `python3 ~/gmail_oauth.py setup` (opens browser)
3. User signs in + clicks "Allow" in the browser (that's their ONLY action)
4. Run the gmail_oauth.py command (list, search, read, send)

**The user never types commands. The agent does everything.**
