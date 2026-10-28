#!/bin/bash
# setup-outlook-search.sh - Deploy outlook-search to the CURRENT Windows user (run from WSL)
# Usage: curl -fsSL https://raw.githubusercontent.com/shein888/cute-hermes/main/outlook-com/scripts/setup-outlook-search.sh | bash
set -euo pipefail

REPO="https://raw.githubusercontent.com/shein888/cute-hermes/main/outlook-com/scripts"
fetch() { curl -fsSL --retry 2 -o "$2.tmp" "$REPO/$1" && mv "$2.tmp" "$2"; }   # -f: never save a 404 page

CMD=/mnt/c/Windows/System32/cmd.exe
command -v cmd.exe >/dev/null 2>&1 && CMD=cmd.exe
if [ ! -x "$CMD" ] && ! command -v "$CMD" >/dev/null 2>&1; then
    echo "[FAIL] Not running in WSL with Windows interop. On pure Windows, copy outlook-search.ps1 and outlook-search.cmd to %USERPROFILE% manually."
    exit 1
fi
WIN_PROFILE=$(cd /mnt/c && "$CMD" /c 'echo %USERPROFILE%' 2>/dev/null | tr -d '\r')
PROFILE_LX=$(wslpath -u "$WIN_PROFILE")
[ -d "$PROFILE_LX" ] || { echo "[FAIL] Windows profile not found: $WIN_PROFILE"; exit 1; }

echo "=== Deploying outlook-search to $WIN_PROFILE ==="
fetch outlook-search.ps1 "$PROFILE_LX/outlook-search.ps1"
fetch outlook-search.cmd "$PROFILE_LX/outlook-search.cmd"
fetch outlook-search.sh  "$HOME/outlook-search.sh"
chmod +x "$HOME/outlook-search.sh"
head -c3 "$PROFILE_LX/outlook-search.ps1" | grep -q $'\xEF\xBB\xBF' || echo "[WARN] outlook-search.ps1 has no UTF-8 BOM — Chinese may break in Windows PowerShell 5.1"
echo "[OK] $WIN_PROFILE\\outlook-search.ps1"
echo "[OK] $WIN_PROFILE\\outlook-search.cmd"
echo "[OK] $HOME/outlook-search.sh"
echo
echo "Check this PC:  bash ~/outlook-search.sh -Diagnose"
echo "Search:         bash ~/outlook-search.sh -Days 1"
