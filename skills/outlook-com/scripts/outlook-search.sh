#!/bin/bash
# outlook-search.sh - run outlook-search.ps1 from Hermes' shell and print the UTF-8 result.
# Works in:  Git Bash (Hermes for Windows / Hermes Desktop)  and  WSL.
# Usage: bash outlook-search.sh -Keyword "法規" -Days 3
#        bash outlook-search.sh -Diagnose
set -u
case "$0" in */*) HERE=$(cd "${0%/*}" && pwd -P) ;; *) HERE=$(pwd -P) ;; esac

case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*) MODE=gitbash ;;
    *) if grep -qi microsoft /proc/version 2>/dev/null; then MODE=wsl; else MODE=other; fi ;;
esac

if [ "$MODE" = gitbash ]; then
    PS=$(command -v powershell.exe || echo "$SYSTEMROOT/System32/WindowsPowerShell/v1.0/powershell.exe")
    PS1_WIN=$(cygpath -w "$HERE/outlook-search.ps1")      # run straight from the skill folder
    PROFILE_UX=$(cygpath -u "$USERPROFILE")
    WIN_PROFILE=$USERPROFILE
elif [ "$MODE" = wsl ]; then
    find_win() {
        if command -v "$1" >/dev/null 2>&1; then command -v "$1"; return 0; fi
        [ -x "/mnt/c/Windows/System32/$2" ] && { echo "/mnt/c/Windows/System32/$2"; return 0; }
        return 1
    }
    PS=$(find_win powershell.exe WindowsPowerShell/v1.0/powershell.exe) || {
        echo "ERROR: powershell.exe not reachable from WSL (check [interop] in /etc/wsl.conf)"; exit 3; }
    CMD=$(find_win cmd.exe cmd.exe) || { echo "ERROR: cmd.exe not reachable from WSL"; exit 3; }
    WIN_PROFILE=$(cd /mnt/c 2>/dev/null; "$CMD" /c 'echo %USERPROFILE%' 2>/dev/null | tr -d '\r')
    [ -n "$WIN_PROFILE" ] || { echo "ERROR: cannot read the Windows %USERPROFILE%"; exit 3; }
    PROFILE_UX=$(wslpath -u "$WIN_PROFILE")
    # PowerShell cannot reliably run a script from the Linux filesystem: copy it to the Windows profile.
    mkdir -p "$PROFILE_UX/.cute-hermes" || { echo "ERROR: cannot create $WIN_PROFILE\\.cute-hermes"; exit 3; }
    cmp -s "$HERE/outlook-search.ps1" "$PROFILE_UX/.cute-hermes/outlook-search.ps1" || \
        cp "$HERE/outlook-search.ps1" "$PROFILE_UX/.cute-hermes/outlook-search.ps1" || {
        echo "ERROR: cannot copy outlook-search.ps1"; exit 3; }
    PS1_WIN="$WIN_PROFILE\\.cute-hermes\\outlook-search.ps1"
    cd "$PROFILE_UX" || exit 3     # Windows working dir avoids the UNC-path warning
else
    echo "ERROR: Outlook COM needs Windows (Git Bash from Hermes for Windows, or WSL)."; exit 3
fi

RESULT="$PROFILE_UX/search-result.txt"
rm -f "$RESULT"
"$PS" -NoProfile -ExecutionPolicy Bypass -File "$PS1_WIN" "$@" | tr -d '\r'
rc=${PIPESTATUS[0]}
echo
echo "=== Results ($WIN_PROFILE\\search-result.txt) ==="
[ -f "$RESULT" ] && sed '1s/^\xEF\xBB\xBF//' "$RESULT" | tr -d '\r'
exit "$rc"
