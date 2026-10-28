#!/bin/bash
# setup-gmail-oauth.sh - One-click deploy of gmail_oauth.py
# Usage: curl -sSL https://raw.githubusercontent.com/shein888/cute-hermes/main/gmail-oauth/scripts/setup-gmail-oauth.sh | bash
# Or:    bash setup-gmail-oauth.sh

set -e

REPO="https://raw.githubusercontent.com/shein888/cute-hermes/main/gmail-oauth/scripts"
DEST="$HOME"
CONF_DIR="$HOME/.config/gmail-oauth"

echo "=== Deploying gmail-oauth to $DEST ==="

# Check for Python
if command -v python3 &>/dev/null; then
    PYTHON="python3"
elif command -v python &>/dev/null; then
    PYTHON="python"
else
    echo "[FAIL] Python not found. Install Python 3.8+ first."
    exit 1
fi

# Create config dir
mkdir -p "$CONF_DIR"

# Check if credentials file exists
if [ ! -f "$CONF_DIR/env" ]; then
    echo ""
    echo "=== OAuth Credentials Setup ==="
    echo "The OAuth Client ID and Secret are NOT stored in the repo"
    echo "(GitHub blocks them via secret scanning)."
    echo ""
    echo -n "GMAIL_OAUTH_CLIENT_ID (from Google Cloud Console): "
    read GMAIL_CLIENT_ID
    echo -n "GMAIL_OAUTH_CLIENT_SECRET: "
    read GMAIL_CLIENT_SECRET

    cat > "$CONF_DIR/env" << ENVEOF
export GMAIL_OAUTH_CLIENT_ID="$GMAIL_CLIENT_ID"
export GMAIL_OAUTH_CLIENT_SECRET="$GMAIL_CLIENT_SECRET"
ENVEOF
    chmod 600 "$CONF_DIR/env"
    echo "[OK] Credentials saved to $CONF_DIR/env"
else
    echo "[OK] Credentials already exist in $CONF_DIR/env"
fi

# Source credentials
source "$CONF_DIR/env"

# Download the Python script
curl -sSL -o "$DEST/gmail_oauth.py" "$REPO/gmail_oauth.py"
chmod +x "$DEST/gmail_oauth.py"
echo "[OK] gmail_oauth.py -> $DEST/gmail_oauth.py"

# Check if token already exists
if [ -f "$CONF_DIR/token.json" ]; then
    echo "[OK] Token already exists — ready to use."
    echo ""
    echo "Test it:"
    echo "  source $CONF_DIR/env && $PYTHON $DEST/gmail_oauth.py list"
    echo ""
    echo "Or tell your Hermes agent:"
    echo "  '幫我查 gm 信箱最近的信'"
    exit 0
fi

# No token — run setup
echo ""
echo "No existing token found. Starting OAuth setup..."
echo "A browser window will open for Google sign-in."
echo ""
$PYTHON "$DEST/gmail_oauth.py" setup

echo ""
echo "=== Deploy complete ==="
echo ""
echo "Test it:"
echo "  source $CONF_DIR/env && $PYTHON $DEST/gmail_oauth.py list"
echo ""
echo "Or tell your Hermes agent:"
echo "  '幫我查 gm 信箱最近的信'"
