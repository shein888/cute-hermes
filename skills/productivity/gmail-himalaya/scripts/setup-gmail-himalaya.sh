#!/usr/bin/env bash
# setup-gmail-himalaya.sh - One-click deploy of himalaya for Gmail
# Usage: curl -sSL https://raw.githubusercontent.com/shein888/cute-hermes/main/skills/productivity/gmail-himalaya/scripts/setup-gmail-himalaya.sh | bash
# Or:    bash setup-gmail-himalaya.sh <email> <app-password>

set -e

EMAIL="${1:-}"
PASSWORD="${2:-}"

# Ask for credentials if not provided
if [ -z "$EMAIL" ]; then
    echo -n "Gmail address (e.g. shein@gm.cute.edu.tw): "
    read EMAIL
fi

if [ -z "$PASSWORD" ]; then
    echo ""
    echo "Google Workspace 帳號要 App 密碼（不是帳號密碼）才能用 IMAP。"
    echo "產生方式："
    echo "  1. 先用瀏覽器登入你的 gm 帳號"
    echo "  2. 再進入 https://myaccount.google.com/apppasswords"
    echo "  3. 選「Mail」→ 產生"
    echo "  4. 會得到一個 16 位密碼，例如 abcd efgh ijkl mnop"
    echo ""
    echo -n "App Password: "
    read PASSWORD
fi

# Install himalaya
if ! command -v himalaya &>/dev/null && [ ! -x "$HOME/.local/bin/himalaya" ]; then
    echo ""
    echo "=== Installing himalaya ==="
    curl -sSL https://raw.githubusercontent.com/pimalaya/himalaya/master/install.sh | PREFIX=~/.local sh
fi

HIMALAYA="$HOME/.local/bin/himalaya"
if [ ! -x "$HIMALAYA" ]; then
    HIMALAYA=$(command -v himalaya)
fi

# Write config
mkdir -p "$HOME/.config/himalaya"
cat > "$HOME/.config/himalaya/config.toml" << EOF
[accounts.gmail]
default = true
email = "$EMAIL"
display-name = "$EMAIL"

imap.server = "imaps://imap.gmail.com:993"
imap.sasl.plain.username = "$EMAIL"
imap.sasl.plain.password.raw = "$PASSWORD"

smtp.server = "smtps://smtp.gmail.com:465"
smtp.sasl.plain.username = "$EMAIL"
smtp.sasl.plain.password.raw = "$PASSWORD"

mailbox.alias.inbox = "INBOX"
mailbox.alias.sent = "[Gmail]/Sent Mail"
mailbox.alias.drafts = "[Gmail]/Drafts"
mailbox.alias.trash = "[Gmail]/Trash"
EOF

echo ""
echo "=== Config written to ~/.config/himalaya/config.toml ==="
echo ""

# Verify
echo "=== Testing connection ==="
if "$HIMALAYA" envelope list --page-size 3 2>&1; then
    echo ""
    echo "[OK] Gmail connected!"
else
    echo ""
    echo "[FAIL] Connection failed. Check your App Password."
    echo "  'NO Application-specific password required' = you used the account password"
    echo "  Generate a new one at https://myaccount.google.com/apppasswords"
fi
