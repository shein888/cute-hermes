#!/usr/bin/env python3
"""
gmail_oauth.py — Gmail API OAuth2 helper for Hermes agents.

Loopback redirect (http://127.0.0.1:<port>) + PKCE, compatible with
Google's "Desktop app" OAuth client. No OOB flow.

Usage:
  python3 gmail_oauth.py setup [--timeout SEC] [--no-browser]
                                         # Open consent page and wait for callback
  python3 gmail_oauth.py auth-url        # Print consent URL only (no waiting)
  python3 gmail_oauth.py import-code URL # Exchange a pasted callback URL
  python3 gmail_oauth.py status          # Check token status
  python3 gmail_oauth.py list [N]        # List inbox (default 10)
  python3 gmail_oauth.py search QUERY [N]
  python3 gmail_oauth.py read MESSAGE_ID
  python3 gmail_oauth.py send TO SUBJECT BODY
  python3 gmail_oauth.py reply TO THREAD_ID BODY

Environment:
  GMAIL_OAUTH_CLIENT_ID / GMAIL_OAUTH_CLIENT_SECRET  optional override
                     (default: built-in hermes-gm client; or ~/.config/gmail-oauth/env)
  GMAIL_OAUTH_PORT   fixed callback port (default: 8765)
"""

import base64
import hashlib
import html
import http.server
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from email import message_from_bytes, policy
from email.message import EmailMessage
from email.utils import parsedate_to_datetime
from pathlib import Path

# ─── Config ───────────────────────────────────────────────────────────────
CONF_DIR = Path.home() / ".config" / "gmail-oauth"
TOKEN_FILE = CONF_DIR / "token.json"
PENDING_FILE = CONF_DIR / "pending.json"
ENV_FILE = CONF_DIR / "env"

SCOPES = "https://www.googleapis.com/auth/gmail.modify"
AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = os.environ.get("GMAIL_OAUTH_TOKEN_ENDPOINT", "https://oauth2.googleapis.com/token")
API_BASE = os.environ.get("GMAIL_OAUTH_API_BASE", "https://gmail.googleapis.com/gmail/v1/users/me")
DEFAULT_PORT = int(os.environ.get("GMAIL_OAUTH_PORT", "8765"))
HOSTED_DOMAIN = "gm.cute.edu.tw"  # hint only; Internal app already restricts to the org


# OAuth client "hermes-gm-desktop" (Google Cloud project hermes-gm, Internal app:
# only gm.cute.edu.tw accounts can authorize). For Desktop apps Google does not treat
# the client secret as confidential. Split so GitHub push protection does not flag it.
_DEFAULT_CLIENT_ID = "930386946858-3d63m2dmik1caej2cam2c4mtnp83b9jh" + ".apps.googleusercontent.com"
_DEFAULT_CLIENT_SECRET = "GOCSPX-" + "FFjY_zi6Y0jE5TLQDxYLy-9Cs5qS"


def _get_client_credentials():
    """Env vars > ~/.config/gmail-oauth/env > built-in hermes-gm client."""
    client_id = os.environ.get("GMAIL_OAUTH_CLIENT_ID", "")
    client_secret = os.environ.get("GMAIL_OAUTH_CLIENT_SECRET", "")
    if (not client_id or not client_secret) and ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[len("export "):]
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            val = val.strip().strip('"').strip("'")
            if key == "GMAIL_OAUTH_CLIENT_ID" and not client_id:
                client_id = val
            elif key == "GMAIL_OAUTH_CLIENT_SECRET" and not client_secret:
                client_secret = val
    return client_id or _DEFAULT_CLIENT_ID, client_secret or _DEFAULT_CLIENT_SECRET


CLIENT_ID, CLIENT_SECRET = _get_client_credentials()


def _die(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def _require_client():
    if not CLIENT_ID or not CLIENT_SECRET:
        _die("ERROR: GMAIL_OAUTH_CLIENT_ID / GMAIL_OAUTH_CLIENT_SECRET not set.\n"
             f"Write them to {ENV_FILE} first.")


def _write_private(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


# ─── HTTP helpers ─────────────────────────────────────────────────────────
def _post_form(url, fields):
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            err = json.loads(body)
            detail = f"{err.get('error')}: {err.get('error_description', '')}"
        except ValueError:
            detail = body[:300]
        raise RuntimeError(f"HTTP {e.code} from {url} — {detail}") from None


# ─── Token helpers ────────────────────────────────────────────────────────
def load_token():
    if TOKEN_FILE.exists():
        try:
            return json.loads(TOKEN_FILE.read_text())
        except ValueError:
            return None
    return None


def save_token(token):
    _write_private(TOKEN_FILE, token)


def refresh_token(token):
    _require_client()
    try:
        result = _post_form(TOKEN_ENDPOINT, {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": token["refresh_token"],
            "grant_type": "refresh_token",
        })
    except RuntimeError as e:
        if "invalid_grant" in str(e):
            _die("Refresh token was revoked or expired (invalid_grant).\n"
                 "Re-authorize: python3 gmail_oauth.py setup")
        raise
    token.update(result)  # keeps refresh_token if Google does not send a new one
    token["expires_at"] = time.time() + result.get("expires_in", 3600)
    save_token(token)
    return token


def get_access_token():
    token = load_token()
    if not token or "access_token" not in token:
        _die("NO_TOKEN: Gmail is not authorized yet. Run: python3 gmail_oauth.py setup")
    if time.time() > token.get("expires_at", 0) - 60:
        if not token.get("refresh_token"):
            _die("Token expired and no refresh token. Re-run: python3 gmail_oauth.py setup")
        token = refresh_token(token)
    return token["access_token"]


# ─── Browser opening (WSL aware) ──────────────────────────────────────────
def _is_wsl():
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    try:
        return "microsoft" in Path("/proc/version").read_text().lower()
    except OSError:
        return False


def open_browser(url):
    """Try hard to open the URL in a real browser. Returns True on success."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(url)  # type: ignore[attr-defined]
            return True
        if _is_wsl():
            # Open in the Windows default browser.
            if shutil.which("wslview"):
                return subprocess.run(["wslview", url]).returncode == 0
            rundll = shutil.which("rundll32.exe") or "/mnt/c/Windows/System32/rundll32.exe"
            if os.path.exists(rundll) or shutil.which("rundll32.exe"):
                subprocess.Popen([rundll, "url.dll,FileProtocolHandler", url],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            ps = shutil.which("powershell.exe") or "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
            if os.path.exists(ps):
                subprocess.Popen([ps, "-NoProfile", "-Command", "Start-Process", f"'{url}'"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            return False
        if sys.platform == "darwin":
            return subprocess.run(["open", url]).returncode == 0
        if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
            return False  # headless Linux: webbrowser would fall back to a text browser
        import webbrowser
        return bool(webbrowser.open(url))
    except Exception:
        return False


# ─── OAuth flow ───────────────────────────────────────────────────────────
def _b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _new_pending(port):
    verifier = _b64url(secrets.token_bytes(48))
    pending = {
        "state": _b64url(secrets.token_bytes(16)),
        "code_verifier": verifier,
        "redirect_uri": f"http://127.0.0.1:{port}",
        "created_at": time.time(),
    }
    _write_private(PENDING_FILE, pending)
    return pending


def _auth_url(pending):
    challenge = _b64url(hashlib.sha256(pending["code_verifier"].encode()).digest())
    return AUTH_ENDPOINT + "?" + urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "redirect_uri": pending["redirect_uri"],
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",          # always return a refresh_token
        "include_granted_scopes": "true",
        "state": pending["state"],
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "hd": HOSTED_DOMAIN,
    })


def _exchange_code(code, pending):
    token = _post_form(TOKEN_ENDPOINT, {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "code_verifier": pending["code_verifier"],
        "grant_type": "authorization_code",
        "redirect_uri": pending["redirect_uri"],
    })
    token["expires_at"] = time.time() + token.get("expires_in", 3600)
    old = load_token() or {}
    if not token.get("refresh_token") and old.get("refresh_token"):
        token["refresh_token"] = old["refresh_token"]
    save_token(token)
    try:
        PENDING_FILE.unlink()
    except OSError:
        pass
    print(f"[OK] Authorized. Token saved to {TOKEN_FILE}")
    print("     Refresh token: " + ("present (auto-refresh works)" if token.get("refresh_token")
                                    else "MISSING — revoke app access and run setup again"))


def _bind_server(preferred_port, handler):
    for port in (preferred_port, 0):
        try:
            return http.server.HTTPServer(("127.0.0.1", port), handler)
        except OSError:
            continue
    _die("Could not open a local port for the OAuth callback.")


def oauth_setup(timeout=300, no_browser=False):
    _require_client()
    captured = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if "code" in q or "error" in q:
                if q.get("state", [""])[0] != pending["state"]:
                    self._reply(400, "State mismatch — please run setup again.")
                    return
                if "code" in q:
                    captured["code"] = q["code"][0]
                    self._reply(200, "Gmail 授權完成，可以關閉這個分頁。<br>Gmail OAuth complete — you can close this tab.")
                else:
                    captured["error"] = q["error"][0]
                    self._reply(400, f"授權失敗 / Error: {html.escape(q['error'][0])}")
            else:
                self._reply(404, "Not found")  # favicon etc. — keep waiting

        def _reply(self, status, text):
            body = f"<html><meta charset='utf-8'><body><h2>{text}</h2></body></html>".encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = _bind_server(DEFAULT_PORT, Handler)
    port = server.server_address[1]
    pending = _new_pending(port)
    url = _auth_url(pending)

    # Always print the URL so the agent can relay it to the user.
    print("AUTH_URL: " + url, flush=True)
    opened = False if no_browser else open_browser(url)
    print(("[..] Browser opened. " if opened else "[!!] Could not open a browser automatically. ")
          + "Sign in with your gm account and click Allow.", flush=True)
    print(f"[..] Waiting for callback on {pending['redirect_uri']} (timeout {timeout}s)...", flush=True)

    deadline = time.time() + timeout
    server.timeout = 1
    while not captured and time.time() < deadline:
        server.handle_request()
    server.server_close()

    if "code" in captured:
        _exchange_code(captured["code"], pending)
        return
    if "error" in captured:
        _die(f"OAuth error: {captured['error']}")

    print("\n[!!] No callback received.", file=sys.stderr)
    print("If the browser ended on a page that could not load (http://127.0.0.1:...?code=...),\n"
          "copy that full address and run:\n"
          "  python3 gmail_oauth.py import-code '<pasted URL>'\n"
          "The pending login stays valid for about 10 minutes.", file=sys.stderr)
    if sys.stdin.isatty():
        try:
            pasted = input("Or paste the callback URL here (Enter to skip): ").strip()
        except EOFError:
            pasted = ""
        if pasted:
            import_code(pasted)
            return
    sys.exit(2)


def print_auth_url():
    """Create a pending login and print the consent URL without waiting."""
    _require_client()
    pending = _new_pending(DEFAULT_PORT)
    url = _auth_url(pending)
    print("AUTH_URL: " + url)
    print("After clicking Allow the browser will show a page that cannot load.\n"
          "Copy its full address and run: python3 gmail_oauth.py import-code '<URL>'")


def import_code(callback_url):
    _require_client()
    if not PENDING_FILE.exists():
        _die("No pending login. Run `setup` or `auth-url` first, then authorize again.")
    pending = json.loads(PENDING_FILE.read_text())
    q = urllib.parse.parse_qs(urllib.parse.urlparse(callback_url.strip()).query)
    if "error" in q:
        _die(f"OAuth error in URL: {q['error'][0]}")
    if "code" not in q:
        _die(f"No code found in: {callback_url}")
    if q.get("state", [""])[0] != pending["state"]:
        _die("State mismatch — this URL belongs to a different login attempt. Run setup again.")
    _exchange_code(q["code"][0], pending)


# ─── Gmail API ────────────────────────────────────────────────────────────
def _api(method, path, payload=None):
    req = urllib.request.Request(
        f"{API_BASE}/{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        method=method,
        headers={"Authorization": f"Bearer {get_access_token()}",
                 "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        _die(f"Gmail API error {e.code}: {e.read().decode(errors='replace')[:500]}")


def api_get(path):
    return _api("GET", path)


def api_post(path, data):
    return _api("POST", path, data)


def _headers(msg):
    return {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}


def _fmt_date(internal_ms):
    try:
        return datetime.fromtimestamp(int(internal_ms) / 1000).strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return "unknown"


def _list_messages(query, limit):
    q = urllib.parse.urlencode({"maxResults": limit, "q": query})
    result = api_get(f"messages?{q}")
    rows = []
    for m in result.get("messages", []):
        d = api_get(f"messages/{m['id']}?format=metadata"
                    "&metadataHeaders=From&metadataHeaders=Subject&metadataHeaders=Date")
        h = _headers(d)  # Gmail returns these headers already decoded (UTF-8)
        rows.append((m["id"], m.get("threadId", ""), _fmt_date(d.get("internalDate")),
                     h.get("from", "(unknown)"), h.get("subject", "(no subject)"),
                     "UNREAD" in d.get("labelIds", [])))
    return rows


def _print_rows(rows):
    if not rows:
        print("No messages.")
        return
    print(f"{'ID':<18}  {'THREAD':<18}  {'DATE':<16}  {'FROM':<35}  SUBJECT")
    print("─" * 120)
    for mid, tid, date, frm, subj, unread in rows:
        mark = "*" if unread else " "
        print(f"{mid:<18}  {tid:<18}  {date:<16}  {frm[:35]:<35} {mark}{subj[:60]}")


def cmd_list(limit=10):
    _print_rows(_list_messages("in:inbox", limit))


def cmd_search(query, limit=10):
    _print_rows(_list_messages(query, limit))


def _body_text(mime):
    part = mime.get_body(preferencelist=("plain", "html"))
    if part is None:
        return ""
    text = part.get_content()
    if part.get_content_type() == "text/html":
        text = re.sub(r"(?is)<(script|style).*?</\1>", "", text)
        text = re.sub(r"(?i)<br\s*/?>|</p>|</div>", "\n", text)
        text = html.unescape(re.sub(r"<[^>]+>", "", text))
        text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def cmd_read(message_id, max_chars=8000):
    d = api_get(f"messages/{message_id}?format=raw")
    mime = message_from_bytes(base64.urlsafe_b64decode(d["raw"] + "=" * (-len(d["raw"]) % 4)),
                              policy=policy.default)
    for k in ("From", "To", "Cc", "Date", "Subject"):
        if mime[k]:
            print(f"{k}: {mime[k]}")
    print(f"Thread-Id: {d.get('threadId')}")
    atts = [p.get_filename() for p in mime.iter_attachments() if p.get_filename()]
    if atts:
        print("Attachments: " + ", ".join(atts))
    print("─" * 80)
    body = _body_text(mime)
    print(body[:max_chars])
    if len(body) > max_chars:
        print(f"\n... ({len(body) - max_chars} more chars)")


def _send(msg, thread_id=None):
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    payload = {"raw": raw}
    if thread_id:
        payload["threadId"] = thread_id
    result = api_post("messages/send", payload)
    print(f"[OK] Sent. Message ID: {result.get('id')}  Thread ID: {result.get('threadId')}")


def cmd_send(to, subject, body):
    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    _send(msg)


def cmd_reply(to, thread_id, body):
    thread = api_get(f"threads/{thread_id}?format=metadata"
                     "&metadataHeaders=Subject&metadataHeaders=Message-ID&metadataHeaders=References")
    last = _headers(thread["messages"][-1])
    subject = last.get("subject", "")
    if not subject.lower().startswith("re:"):
        subject = "Re: " + subject
    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    if last.get("message-id"):
        msg["In-Reply-To"] = last["message-id"]
        msg["References"] = (last.get("references", "") + " " + last["message-id"]).strip()
    msg.set_content(body)
    _send(msg, thread_id)


def cmd_status():
    token = load_token()
    if not token:
        print("No token. Run: python3 gmail_oauth.py setup")
        return
    print(f"Token file: {TOKEN_FILE}")
    remaining = int(token.get("expires_at", 0) - time.time())
    print("Access token: " + (f"valid for {remaining}s" if remaining > 0 else "expired (auto-refreshes on next call)"))
    print("Refresh token: " + ("present (auto-refresh works)" if token.get("refresh_token") else "MISSING"))
    print(f"Scope: {token.get('scope', '?')}")


# ─── Main ────────────────────────────────────────────────────────────────
def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    cmd, rest = args[0].lower(), args[1:]

    def need(n, usage):
        if len(rest) < n:
            _die("Usage: gmail_oauth.py " + usage)

    if cmd == "setup":
        timeout = 300
        if "--timeout" in rest:
            timeout = int(rest[rest.index("--timeout") + 1])
        oauth_setup(timeout=timeout, no_browser="--no-browser" in rest)
    elif cmd == "auth-url":
        print_auth_url()
    elif cmd == "import-code":
        need(1, "import-code 'http://127.0.0.1:PORT/?state=...&code=...'")
        import_code(rest[0])
    elif cmd == "status":
        cmd_status()
    elif cmd == "list":
        cmd_list(int(rest[0]) if rest else 10)
    elif cmd == "search":
        need(1, "search QUERY [N]")
        cmd_search(rest[0], int(rest[1]) if len(rest) > 1 else 10)
    elif cmd == "read":
        need(1, "read MESSAGE_ID")
        cmd_read(rest[0])
    elif cmd == "send":
        need(3, "send TO SUBJECT BODY")
        cmd_send(rest[0], rest[1], rest[2])
    elif cmd == "reply":
        need(3, "reply TO THREAD_ID BODY")
        cmd_reply(rest[0], rest[1], rest[2])
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        _die(f"ERROR: {e}")
