#!/bin/bash
# gmail.sh - run gmail_oauth.py with a working Python 3 (Git Bash on Windows, WSL, Linux, macOS).
# Usage: bash gmail.sh status | setup | list | search ... (same commands as gmail_oauth.py)
case "$0" in */*) HERE=$(cd "${0%/*}" && pwd -P) ;; *) HERE=$(pwd -P) ;; esac
SCRIPT="$HERE/gmail_oauth.py"
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) SCRIPT=$(cygpath -w "$SCRIPT") ;; esac
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8

# A candidate must really run Python 3 (Windows has a "python3" Store stub that only prints a hint).
works() { "$@" -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >/dev/null 2>&1; }
if [ -n "${GMAIL_OAUTH_PYTHON:-}" ] && works "$GMAIL_OAUTH_PYTHON"; then exec "$GMAIL_OAUTH_PYTHON" "$SCRIPT" "$@"; fi
for py in python3 python; do
    command -v "$py" >/dev/null 2>&1 && works "$py" && exec "$py" "$SCRIPT" "$@"
done
command -v py >/dev/null 2>&1 && works py -3 && exec py -3 "$SCRIPT" "$@"
# Hermes ships uv; it can fetch a private Python on first use (needs internet once).
for uv in uv "${HERMES_HOME:-}/bin/uv" "$HOME/.hermes/bin/uv" "${LOCALAPPDATA:-}/hermes/bin/uv.exe"; do
    command -v "$uv" >/dev/null 2>&1 && exec "$uv" run --no-project --python ">=3.9" "$SCRIPT" "$@"
done
echo "ERROR: Python 3 not found. Install it once (Windows: winget install Python.Python.3.12) and retry."
exit 3
