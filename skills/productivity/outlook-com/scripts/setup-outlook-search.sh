#!/bin/bash
# setup-outlook-search.sh - One-click deploy of outlook-search.ps1
# Usage: curl -sSL https://raw.githubusercontent.com/shein888/cute-hermes/main/skills/productivity/outlook-com/scripts/setup-outlook-search.sh | bash
# Or:    bash setup-outlook-search.sh

set -e

REPO="https://raw.githubusercontent.com/shein888/cute-hermes/main/skills/productivity/outlook-com/scripts"
DEST="$HOME"
WIN_DEST="/mnt/c/Users"

echo "=== Deploying outlook-search to $DEST ==="

# Check if already deployed (idempotent)
if [ -f "$DEST/outlook-search.ps1" ] && [ -f "$DEST/outlook-search.cmd" ]; then
    echo "[OK] Already deployed — checking for updates..."
fi

# Download the PowerShell script
curl -sSL -o "$DEST/outlook-search.ps1" "$REPO/outlook-search.ps1"
echo "[OK] outlook-search.ps1 -> $DEST/outlook-search.ps1"

# Create the .cmd wrapper
cat > "$DEST/outlook-search.cmd" << 'CMDEOF'
@echo off
powershell.exe -ExecutionPolicy Bypass -File "%USERPROFILE%\outlook-search.ps1" %*
CMDEOF
echo "[OK] outlook-search.cmd -> $DEST/outlook-search.cmd"

# Also copy to Windows user profile if WSL mount exists
if [ -d "$WIN_DEST" ]; then
    for userdir in "$WIN_DEST"/*/; do
        win_user="${userdir%/}"
        win_user="${win_user##*/}"
        # Convert to Windows path: /mnt/c/Users/shein -> C:\Users\shein
        win_path="/mnt/c/Users/$win_user"
        if [ -d "$win_path" ]; then
            cp "$DEST/outlook-search.ps1" "$win_path/outlook-search.ps1" 2>/dev/null && \
            cp "$DEST/outlook-search.cmd" "$win_path/outlook-search.cmd" 2>/dev/null && \
            echo "[OK] Also copied to $win_path/"
        fi
    done
fi

# Download the WSL wrapper
curl -sSL -o "$DEST/outlook-search.sh" "$REPO/outlook-search.sh" 2>/dev/null || true
chmod +x "$DEST/outlook-search.sh" 2>/dev/null || true

echo ""
echo "=== Deploy complete ==="
echo ""
echo "Test it:"
echo "  bash $HOME/outlook-search.sh -Days 1"
echo ""
echo "Or tell your Hermes agent:"
echo "  '用 outlook-search 幫我查 Outlook 最近的信'"
