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

**The agent MUST run the setup script IMMEDIATELY after installing this skill.**
This is idempotent — if the token already exists, it finishes in <1 second.

```bash
curl -sSL https://raw.githubusercontent.com/shein888/cute-hermes/main/gmail-oauth/scripts/setup-gmail-oauth.sh | bash
```

What the script does automatically:
1. Downloads `gmail_oauth.py` to the user's home directory
2. Checks for credentials in `~/.config/gmail-oauth/env`
3. If token exists → exits immediately
4. If no token → opens browser for Google sign-in, user clicks "Allow", done

**Do NOT ask the user for Client ID or Client Secret unless the setup
script can't find them.** The default credentials for this repo are
stored in the Hermes agent's memory. If the agent doesn't have them,
ask the user for:

- `GMAIL_OAUTH_CLIENT_ID` (starts with `930386946858-`)
- `GMAIL_OAUTH_CLIENT_SECRET` (starts with `GOCSPX-`)

Write them to `~/.config/gmail-oauth/env` if missing, then run the
setup script.

**Do NOT search Gmail before the setup script has run.**

If the user says "幫我查 gm 信箱" and there's no token yet:
→ Run the setup script above first, then proceed.

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

### Read a message

```bash
python3 ~/gmail_oauth.py read MESSAGE_ID
```

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

2. **Browser must be available** — the OAuth flow opens a browser and listens
   on `localhost:8080`. Headless servers need a manual redirect.

3. **Token auto-refresh** — the access token expires every 1 hour, but the
   script auto-refreshes it using the refresh token. No user action needed.

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

1. **Run the setup script** (MANDATORY, idempotent, <1s if token exists)
2. If token now exists → run the gmail_oauth.py commands
3. If no token → the setup script opened a browser; user just clicks "Allow"
4. If token expired → the script auto-refreshes, no action needed

**The Client ID and Secret are in the skill doc above. Write them to
`~/.config/gmail-oauth/env` if missing. Do NOT ask the user.**
