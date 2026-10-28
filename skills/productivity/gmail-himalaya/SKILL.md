---
name: gmail-himalaya
description: "Read and send Gmail (Google Workspace) mail via Himalaya CLI. Use when the user asks to read, search, reply to, or send Gmail emails, or mentions managing their gm.cute.edu.tw or other Google Workspace mailbox."
version: 1.0.0
author: shein
platforms: [windows, wsl, linux]
metadata:
  hermes:
    tags: [gmail, email, himalaya, imap, smtp, google-workspace]
    homepage: https://pimalaya.org/docs/himalaya/
---

# Gmail via Himalaya CLI

Read and send Gmail / Google Workspace mail via the [Himalaya](https://github.com/pimalaya/himalaya) CLI.
Works on WSL, Windows (via WSL), and Linux.

**IMPORTANT: Google Workspace requires an App Password for IMAP/SMTP — the regular
account password will NOT work.** If the user has 2FA enabled (required for all
cute.edu.tw accounts), they must generate an App Password first.

## First-Time Setup (one-time per PC)

### Step 1: Install Himalaya

```bash
curl -sSL https://raw.githubusercontent.com/pimalaya/himalaya/master/install.sh | PREFIX=~/.local sh
```

Verify:
```bash
~/.local/bin/himalaya --version
```

### Step 2: Ask the user for their App Password

**You MUST ask the user for these two values before writing the config:**

1. **Email address** — e.g. `shein@gm.cute.edu.tw`
2. **App Password** (NOT the account password)

If the user gives you their regular account password, explain:

> Google Workspace 帳號要 **App 密碼**（不是帳號密碼）才能用 IMAP。
> 你需要去產生一個：
> 1. 開啟 https://myaccount.google.com/apppasswords
> 2. 選「Mail」→ 產生
> 3. 會得到一個 16 位密碼，例如 `abcd efgh ijkl mnop`
>
> 給我那個 App 密碼就行。

### Step 3: Write the config

Create `~/.config/himalaya/config.toml`:

```toml
[accounts.gmail]
default = true
email = "USER_EMAIL"
display-name = "USER_NAME"

imap.server = "imaps://imap.gmail.com:993"
imap.sasl.plain.username = "USER_EMAIL"
imap.sasl.plain.password.raw = "APP_PASSWORD_WITH_SPACES"

smtp.server = "smtps://smtp.gmail.com:465"
smtp.sasl.plain.username = "USER_EMAIL"
smtp.sasl.plain.password.raw = "APP_PASSWORD_WITH_SPACES"

mailbox.alias.inbox = "INBOX"
mailbox.alias.sent = "[Gmail]/Sent Mail"
mailbox.alias.drafts = "[Gmail]/Drafts"
mailbox.alias.trash = "[Gmail]/Trash"
```

**CRITICAL (v2 format):**
- Use `imap.server = "imaps://imap.gmail.com:993"` (URL format), NOT `backend.type = "imap"` + `backend.host`
- Use `imap.sasl.plain.password.raw = "..."` for the password
- Use `mailbox.alias.inbox = "INBOX"` (plural `alias`), NOT `folder.aliases.inbox`
- The App Password MUST include the space as generated (e.g. `abcd efgh ijkl mnop`)
- SMTP port 465 with `smtps://` (implicit TLS). Do NOT use port 587.

### Step 4: Verify

```bash
~/.local/bin/himalaya envelope list --page-size 5
```

If you see an error `NO Application-specific password required`, the user
gave the account password instead of the App Password. Ask again.

## Common Operations

### List inbox

```bash
~/.local/bin/himalaya envelope list                    # last 25
~/.local/bin/himalaya envelope list --page-size 50     # last 50
~/.local/bin/himalaya envelope list --page 2           # page 2
```

### Search

```bash
# By subject
~/.local/bin/himalaya envelope list --query 'SUBJECT "keyword"'

# By sender
~/.local/bin/himalaya envelope list --query 'FROM "someone@example.com"'

# By date (last 7 days)
~/.local/bin/himalaya envelope list --query 'SINCE 01-Oct-2026'

# Combined
~/.local/bin/himalaya envelope list --query 'FROM "prac@cute.edu.tw" SINCE 01-Oct-2026'
```

### Read a message

```bash
~/.local/bin/himalaya message read 14127
# Save to file (for large messages)
~/.local/bin/himalaya message read 14127 > /tmp/email.txt
```

### Send an email

```bash
cat << 'EOF' | ~/.local/bin/himalaya message send
To: recipient@example.com
Subject: Hello

Body text here.
EOF
```

### Reply

```bash
~/.local/bin/himalaya message reply 14127 << 'EOF'
Thanks, got it.
EOF
```

### Download attachments

```bash
~/.local/bin/himalaya attachment download 14127 --dir ~/Downloads
```

### List mailboxes (folders)

```bash
~/.local/bin/himalaya mailbox list
```

### Unread count

```bash
~/.local/bin/himalaya envelope list --query 'UNSEEN' --page-size 1
```

## Pitfalls

1. **App Password, not account password** — Google Workspace rejects the regular
   password with `NO Application-specific password required`. Always ask the
   user for the 16-character App Password from https://myaccount.google.com/apppasswords

2. **Himalaya v2 config format** — v2 (2025+) uses `imap.server = "imaps://host:993"`
   and `imap.sasl.plain.password.raw = "..."`. The old v1 format
   (`backend.type = "imap"`, `backend.host = "imap.gmail.com"`, `backend.auth.raw`)
   is **ignored** and will fail with `configures no supported backend`.

3. **App Password has a space** — the generated password is 4 groups of 4 chars
   separated by spaces. Keep the space. `imap.sasl.plain.password.raw = "abcd efgh ijkl mnop"`.

4. **SMTP port** — use 465 with `smtps://` (implicit TLS). Port 587 requires
   STARTTLS and a different config.

5. **Gmail folder aliases** — Gmail's "Sent" folder is `[Gmail]/Sent Mail`, not
   `Sent`. Always set `mailbox.alias.sent = "[Gmail]/Sent Mail"` or sends will
   fail to save a copy.

6. **Encoding** — when writing the config from WSL with Chinese display names,
   use Python with `utf-8-sig` encoding or just use English display names.

7. **Multiple accounts** — if the user has both cute.edu.tw (Gmail) and a
   personal Gmail, create two account sections:
   ```toml
   [accounts.work]
   email = "shein@gm.cute.edu.tw"
   ...
   
   [accounts.personal]
   email = "shein@gmail.com"
   ...
   ```
   Switch with `--account work` or `--account personal`.

8. **Timeout** — first IMAP connection takes 3-5 seconds. Set `timeout=30`.

9. **Result output** — for large outputs, redirect to a file:
   ```bash
   ~/.local/bin/himalaya envelope list > /tmp/gmail-result.txt
   cat /tmp/gmail-result.txt
   ```

10. **WSL path** — use `~/.local/bin/himalaya` or add `~/.local/bin` to PATH.

## Distributing to Other PCs

To deploy on another PC:
1. Install himalaya (Step 1 above)
2. Ask the user for their Gmail address + App Password
3. Write the config (Step 3 above)
4. Verify (Step 4 above)

No WSL required — himalaya is a single static binary that runs on
Windows (download the `.exe` release) or Linux.

## Quick Reference for the Agent

When the user asks about their Gmail:

1. Check if `~/.config/himalaya/config.toml` exists
2. If NOT → ask for email + App Password → write config → verify
3. If YES → just run the himalaya commands
4. If `NO Application-specific password required` → ask for App Password again
5. Always use `~/.local/bin/himalaya` (full path) to avoid PATH issues
