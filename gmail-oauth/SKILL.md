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

**Every time the agent loads this skill, it MUST run the setup script first.**
This is idempotent — if the token already exists, it finishes in <1 second:

```bash
curl -sSL https://raw.githubusercontent.com/shein888/cute-hermes/main/gmail-oauth/scripts/setup-gmail-oauth.sh | bash
```

If the user hasn't authorized yet, the script opens a browser for Google sign-in.
The user just clicks "Allow" and it's done. The token is saved to
`~/.config/gmail-oauth/token.json` and auto-refreshes.

**Do not search Gmail before confirming the token exists.**

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

The OAuth Client ID/Secret are **NOT stored in the repo** (GitHub secret
scanning blocks them). The setup script asks the user for them once and
saves to `~/.config/gmail-oauth/env`.

The user just needs to:

1. Run the setup script (asks for Client ID/Secret, then opens browser)
2. Sign in to their Google account
3. Click "Allow"
4. Done — token saved, auto-refreshes forever

No App Password. No 2FA requirement. No IMAP/SMTP config.

**For the agent:** If the user's PC doesn't have the credentials yet,
ask them for the `GMAIL_OAUTH_CLIENT_ID` and `GMAIL_OAUTH_CLIENT_SECRET`
from their Google Cloud Console project, then write them to
`~/.config/gmail-oauth/env`:

```bash
mkdir -p ~/.config/gmail-oauth
cat > ~/.config/gmail-oauth/env << 'EOF'
export GMAIL_OAUTH_CLIENT_ID="<CLIENT_ID>"
export GMAIL_OAUTH_CLIENT_SECRET="<CLIENT_SECRET>"
EOF
chmod 600 ~/.config/gmail-oauth/env
source ~/.config/gmail-oauth/env
python3 ~/gmail_oauth.py setup
```

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

1. Run the setup script (MANDATORY first step)
2. Check if `~/.config/gmail-oauth/token.json` exists
3. If YES → just run the gmail_oauth.py commands
4. If NO → the setup script will open a browser for Google sign-in
5. If token expired → the script auto-refreshes, no action needed
