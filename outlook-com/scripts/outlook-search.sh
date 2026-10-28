#!/bin/bash
# outlook-search.sh - WSL wrapper for outlook-search.ps1 (runs Windows PowerShell, prints UTF-8 result)
# Usage: bash ~/outlook-search.sh -Keyword "法規" -Days 3
#        bash ~/outlook-search.sh -Diagnose
set -u

win() { local p; for p in "$1" "/mnt/c/Windows/System32/$2"; do command -v "$p" >/dev/null 2>&1 && { echo "$p"; return; }; [ -x "$p" ] && { echo "$p"; return; }; done; return 1; }
PS=$(win powershell.exe WindowsPowerShell/v1.0/powershell.exe) || { echo "ERROR: powershell.exe not reachable from WSL (check [interop] in /etc/wsl.conf)"; exit 3; }
CMD=$(win cmd.exe cmd.exe) || { echo "ERROR: cmd.exe not reachable from WSL"; exit 3; }

WIN_PROFILE=$(cd /mnt/c 2>/dev/null; "$CMD" /c 'echo %USERPROFILE%' 2>/dev/null | tr -d '\r')
[ -n "$WIN_PROFILE" ] || { echo "ERROR: cannot read Windows %USERPROFILE%"; exit 3; }
PROFILE_LX=$(wslpath -u "$WIN_PROFILE")
PS1="$WIN_PROFILE\\outlook-search.ps1"
[ -f "$PROFILE_LX/outlook-search.ps1" ] || { echo "ERROR: $PS1 missing — run setup-outlook-search.sh first"; exit 3; }

RESULT="$PROFILE_LX/search-result.txt"
rm -f "$RESULT"
# cd to a Windows path to avoid the UNC-path warning
cd "$PROFILE_LX" || exit 3
"$PS" -NoProfile -ExecutionPolicy Bypass -File "$PS1" "$@" | tr -d '\r'
rc=${PIPESTATUS[0]}
echo
echo "=== Results ($WIN_PROFILE\\search-result.txt) ==="
[ -f "$RESULT" ] && sed '1s/^\xEF\xBB\xBF//' "$RESULT" | tr -d '\r'
exit $rc
