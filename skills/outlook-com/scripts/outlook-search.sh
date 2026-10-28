#!/bin/bash
# outlook-search.sh - WSL wrapper for outlook-search.ps1 (ships with the outlook-com skill)
# Copies the .ps1 next to this file to %USERPROFILE%\.cute-hermes\ (PowerShell cannot run it
# from the Linux filesystem reliably), runs it with Windows PowerShell and prints the UTF-8 result.
# Usage: bash outlook-search.sh -Keyword "法規" -Days 3
#        bash outlook-search.sh -Diagnose
set -u
HERE=$(cd "$(dirname "$(readlink -f "$0")")" && pwd)

find_win() {   # $1 = exe name, $2 = fallback path under C:\Windows\System32
    if command -v "$1" >/dev/null 2>&1; then command -v "$1"; return 0; fi
    [ -x "/mnt/c/Windows/System32/$2" ] && { echo "/mnt/c/Windows/System32/$2"; return 0; }
    return 1
}
PS=$(find_win powershell.exe WindowsPowerShell/v1.0/powershell.exe) || {
    echo "ERROR: powershell.exe not reachable. This must run in WSL with Windows interop enabled"
    echo "       (check [interop] in /etc/wsl.conf), or on Windows use outlook-search.cmd."; exit 3; }
CMD=$(find_win cmd.exe cmd.exe) || { echo "ERROR: cmd.exe not reachable from WSL"; exit 3; }

WIN_PROFILE=$(cd /mnt/c 2>/dev/null; "$CMD" /c 'echo %USERPROFILE%' 2>/dev/null | tr -d '\r')
[ -n "$WIN_PROFILE" ] || { echo "ERROR: cannot read the Windows %USERPROFILE%"; exit 3; }
PROFILE_LX=$(wslpath -u "$WIN_PROFILE")
DEST_LX="$PROFILE_LX/.cute-hermes"
mkdir -p "$DEST_LX" || { echo "ERROR: cannot create $WIN_PROFILE\\.cute-hermes"; exit 3; }
if ! cmp -s "$HERE/outlook-search.ps1" "$DEST_LX/outlook-search.ps1"; then
    cp "$HERE/outlook-search.ps1" "$DEST_LX/outlook-search.ps1" || { echo "ERROR: cannot copy outlook-search.ps1"; exit 3; }
fi
PS1_WIN="$WIN_PROFILE\\.cute-hermes\\outlook-search.ps1"

RESULT="$PROFILE_LX/search-result.txt"
rm -f "$RESULT"
cd "$PROFILE_LX" || exit 3          # a Windows working dir avoids the UNC-path warning
"$PS" -NoProfile -ExecutionPolicy Bypass -File "$PS1_WIN" "$@" | tr -d '\r'
rc=${PIPESTATUS[0]}
echo
echo "=== Results ($WIN_PROFILE\\search-result.txt) ==="
[ -f "$RESULT" ] && sed '1s/^\xEF\xBB\xBF//' "$RESULT" | tr -d '\r'
exit "$rc"
