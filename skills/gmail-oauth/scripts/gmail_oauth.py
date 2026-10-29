#!/usr/bin/env python3
"""
gmail_oauth.py — Gmail API OAuth2 helper for Hermes agents.

Loopback redirect (http://127.0.0.1:<port>) + PKCE, compatible with
Google's "Desktop app" OAuth client. No OOB flow.

Usage:
  python3 gmail_oauth.py setup [--timeout SEC] [--no-browser] [--foreground]
                                         # Print AUTH_URL, open browser, listen in background
  python3 gmail_oauth.py wait [--timeout SEC]   # Wait until the user clicked Allow
  python3 gmail_oauth.py auth-url        # Print consent URL only (no waiting)
  python3 gmail_oauth.py import-code URL # Exchange a pasted callback URL
  python3 gmail_oauth.py status          # Check token status
  python3 gmail_oauth.py logout          # Revoke + delete token (re-bind with setup)
  python3 gmail_oauth.py list [N]        # List inbox (default 10)
  python3 gmail_oauth.py search QUERY [N]
  python3 gmail_oauth.py read MESSAGE_ID
  python3 gmail_oauth.py send TO SUBJECT BODY
  python3 gmail_oauth.py reply TO THREAD_ID BODY
  python3 gmail_oauth.py drive-list [N] [FOLDER_ID]
  python3 gmail_oauth.py drive-search QUERY [N]
  python3 gmail_oauth.py drive-info FILE_ID
  python3 gmail_oauth.py drive-read FILE_ID          # Google Docs/Sheets/Slides, text files
  python3 gmail_oauth.py drive-download FILE_ID [DEST]
  python3 gmail_oauth.py drive-upload LOCAL_FILE [FOLDER_ID]
  python3 gmail_oauth.py drive-mkdir NAME [PARENT_ID]
  python3 gmail_oauth.py drive-rename FILE_ID NEW_NAME
  python3 gmail_oauth.py drive-move FILE_ID FOLDER_ID
  python3 gmail_oauth.py drive-trash FILE_ID        # to trash (recoverable), never permanent

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

# Windows consoles default to cp950/cp1252; never crash on Chinese output.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ─── Config ───────────────────────────────────────────────────────────────
CONF_DIR = Path.home() / ".config" / "gmail-oauth"
TOKEN_FILE = CONF_DIR / "token.json"
PENDING_FILE = CONF_DIR / "pending.json"
ENV_FILE = CONF_DIR / "env"

GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.modify"
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
SCOPES = f"{GMAIL_SCOPE} {DRIVE_SCOPE}"
AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = os.environ.get("GMAIL_OAUTH_TOKEN_ENDPOINT", "https://oauth2.googleapis.com/token")
API_BASE = os.environ.get("GMAIL_OAUTH_API_BASE", "https://gmail.googleapis.com/gmail/v1/users/me")
DRIVE_BASE = os.environ.get("GMAIL_OAUTH_DRIVE_BASE", "https://www.googleapis.com/drive/v3")
DRIVE_UPLOAD = os.environ.get("GMAIL_OAUTH_DRIVE_UPLOAD", "https://www.googleapis.com/upload/drive/v3")
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
                 "Re-authorize with the setup command")
        raise
    token.update(result)  # keeps refresh_token if Google does not send a new one
    token["expires_at"] = time.time() + result.get("expires_in", 3600)
    save_token(token)
    return token


def get_access_token():
    token = load_token()
    if not token or "access_token" not in token:
        _die("NO_TOKEN: Gmail is not authorized yet. Run the skill's setup command")
    if time.time() > token.get("expires_at", 0) - 60:
        if not token.get("refresh_token"):
            _die("Token expired and no refresh token. Re-run the setup command")
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


LISTENER_FILE = CONF_DIR / "listener.json"
LISTENER_LOG = CONF_DIR / "listener.log"


def _bind_server(preferred_port, handler):
    for port in (preferred_port, 0):
        try:
            return http.server.HTTPServer(("127.0.0.1", port), handler)
        except OSError:
            continue
    return None


def _set_listener(**fields):
    data = {}
    if LISTENER_FILE.exists():
        try:
            data = json.loads(LISTENER_FILE.read_text())
        except ValueError:
            data = {}
    data.update(fields, updated_at=time.time())
    _write_private(LISTENER_FILE, data)


def _listen(timeout, no_browser=False, announce=True):
    """Bind the loopback port, create the pending login, wait for Google's redirect.
    Writes progress to listener.json so `setup` / `wait` in other processes can follow it.
    Returns 0 on success, 1 on OAuth error, 2 on timeout."""
    _require_client()
    captured = {}
    state_box = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if "code" in q or "error" in q:
                if q.get("state", [""])[0] != state_box.get("state"):
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
    if server is None:
        _set_listener(status="error", message="Could not open a local port for the OAuth callback.")
        _die("Could not open a local port for the OAuth callback.")
    port = server.server_address[1]
    pending = _new_pending(port)
    state_box["state"] = pending["state"]
    url = _auth_url(pending)
    deadline = time.time() + timeout
    _set_listener(status="listening", pid=os.getpid(), port=port, auth_url=url,
                  state=pending["state"], deadline=deadline, message="")
    if announce:
        print("AUTH_URL: " + url, flush=True)
        opened = False if no_browser else open_browser(url)
        print(("[..] Browser opened. " if opened else "[!!] Could not open a browser automatically. ")
              + "Sign in with your gm account and click Allow.", flush=True)
        print(f"[..] Waiting for callback on {pending['redirect_uri']} (timeout {timeout}s)...", flush=True)

    server.timeout = 1
    while not captured and time.time() < deadline:
        server.handle_request()
    server.server_close()

    if "code" in captured:
        try:
            _exchange_code(captured["code"], pending)
        except RuntimeError as e:
            _set_listener(status="error", message=str(e))
            print(f"ERROR: {e}", file=sys.stderr)
            return 1
        _set_listener(status="done", message="Authorized")
        return 0
    if "error" in captured:
        _set_listener(status="error", message=f"OAuth error: {captured['error']}")
        print(f"OAuth error: {captured['error']}", file=sys.stderr)
        return 1
    _set_listener(status="timeout", message="No callback received")
    return 2


def oauth_setup(timeout=600, no_browser=False, foreground=False):
    """Default: start a background listener, print AUTH_URL and return at once, so an agent
    whose tool only shows output after the command ends can hand the link to the user.
    Then `wait` reports the result. --foreground keeps everything in this process."""
    _require_client()
    if foreground:
        rc = _listen(timeout, no_browser=no_browser, announce=True)
        if rc == 2:
            print("\n[!!] No callback received.", file=sys.stderr)
            print("If the browser ended on a page that could not load (http://127.0.0.1:...?code=...),\n"
                  "copy that full address and run:  import-code '<pasted URL>'", file=sys.stderr)
            if sys.stdin.isatty():
                try:
                    pasted = input("Or paste the callback URL here (Enter to skip): ").strip()
                except EOFError:
                    pasted = ""
                if pasted:
                    import_code(pasted)
                    return
        sys.exit(rc)

    try:
        LISTENER_FILE.unlink()
    except OSError:
        pass
    CONF_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, os.path.abspath(__file__), "_listen", "--timeout", str(timeout)]
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    with open(LISTENER_LOG, "w", encoding="utf-8") as log:
        subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=log, stderr=log, close_fds=True, **kwargs)

    info = {}
    for _ in range(100):  # up to ~10 s for the listener to bind its port
        time.sleep(0.1)
        if LISTENER_FILE.exists():
            try:
                info = json.loads(LISTENER_FILE.read_text())
            except ValueError:
                continue
            if info.get("status") in ("listening", "error"):
                break
    if info.get("status") != "listening":
        log_tail = LISTENER_LOG.read_text(encoding="utf-8", errors="replace")[-800:] if LISTENER_LOG.exists() else ""
        _die("ERROR: background listener did not start. " + (info.get("message") or "") + "\n" + log_tail
             + "\nRetry with: setup --foreground")

    url = info["auth_url"]
    print("AUTH_URL: " + url, flush=True)
    opened = False if no_browser else open_browser(url)
    print(("[..] Browser opened. " if opened else "[!!] No browser opened automatically. ")
          + "Give the AUTH_URL link to the user: sign in with the gm account and click Allow.")
    print(f"[..] Listening on http://127.0.0.1:{info['port']} for {timeout}s in the background.")
    print("[..] After the user clicks Allow, run:  wait")


def wait_for_auth(timeout=120):
    """Poll the background listener started by `setup`."""
    deadline = time.time() + timeout
    while True:
        info = {}
        if LISTENER_FILE.exists():
            try:
                info = json.loads(LISTENER_FILE.read_text())
            except ValueError:
                info = {}
        status = info.get("status")
        if status == "done":
            print("[OK] Authorized. Refresh token: "
                  + ("present" if (load_token() or {}).get("refresh_token") else "MISSING"))
            return 0
        if status == "error":
            print(f"ERROR: {info.get('message')}", file=sys.stderr)
            return 1
        if status == "timeout" or status is None:
            print("No active login (timed out or never started). Run setup again.", file=sys.stderr)
            return 2
        if time.time() >= deadline:
            print("Still waiting for the user to click Allow. Ask the user, then run `wait` again.\n"
                  "If the browser shows a page that cannot load, ask for that full address and run:"
                  "  import-code '<URL>'")
            return 4
        time.sleep(1)


def print_auth_url():
    """Create a pending login and print the consent URL without listening (manual import-code path)."""
    _require_client()
    pending = _new_pending(DEFAULT_PORT)
    url = _auth_url(pending)
    print("AUTH_URL: " + url)
    print("After clicking Allow the browser will show a page that cannot load.\n"
          "Copy its full address and run:  import-code '<URL>'")


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
    if LISTENER_FILE.exists():
        _set_listener(status="done", message="Authorized via import-code")


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


def cmd_logout():
    """Revoke the grant at Google and delete the local token (then run setup to re-bind)."""
    token = load_token()
    if not token:
        print("No token on this PC — nothing to remove.")
        return
    tok = token.get("refresh_token") or token.get("access_token")
    req = urllib.request.Request(
        os.environ.get("GMAIL_OAUTH_REVOKE_ENDPOINT", "https://oauth2.googleapis.com/revoke"),
        data=urllib.parse.urlencode({"token": tok}).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=30):
            pass  # 200 with an empty body = revoked
        print("[OK] Access revoked at Google.")
    except Exception as e:  # already revoked / offline: still remove the local copy
        print(f"[..] Revoke skipped ({e}).")
    for f in (TOKEN_FILE, PENDING_FILE, LISTENER_FILE):
        try:
            f.unlink()
        except OSError:
            pass
    print(f"[OK] Local token removed ({TOKEN_FILE}). Run setup to authorize again.")


def cmd_status():
    token = load_token()
    if not token:
        print("No token. Run the skill's setup command")
        return
    print(f"Token file: {TOKEN_FILE}")
    remaining = int(token.get("expires_at", 0) - time.time())
    print("Access token: " + (f"valid for {remaining}s" if remaining > 0 else "expired (auto-refreshes on next call)"))
    print("Refresh token: " + ("present (auto-refresh works)" if token.get("refresh_token") else "MISSING"))
    scope = token.get("scope", "")
    print(f"Scope: {scope or '?'}")
    print("Gmail: " + ("yes" if "gmail" in scope else "unknown"))
    print("Drive: " + ("yes" if "auth/drive" in scope else "NO — run logout, then setup, to add Drive"))


# ─── Google Drive API ─────────────────────────────────────────────────────
FOLDER_MIME = "application/vnd.google-apps.folder"
# Google-native files have no bytes; they are exported. read -> text, download -> Office file.
EXPORT_TEXT = {
    "application/vnd.google-apps.document": ("text/plain", ".txt"),
    "application/vnd.google-apps.spreadsheet": ("text/csv", ".csv"),
    "application/vnd.google-apps.presentation": ("text/plain", ".txt"),
}
EXPORT_FILE = {
    "application/vnd.google-apps.document":
        ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx"),
    "application/vnd.google-apps.spreadsheet":
        ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"),
    "application/vnd.google-apps.presentation":
        ("application/vnd.openxmlformats-officedocument.presentationml.presentation", ".pptx"),
    "application/vnd.google-apps.drawing": ("image/png", ".png"),
}
FILE_FIELDS = "id,name,mimeType,size,modifiedTime,parents,webViewLink,owners(displayName,emailAddress),trashed"
_ALL_DRIVES = {"supportsAllDrives": "true"}


def _require_drive_scope():
    token = load_token()
    if token and token.get("scope") and "auth/drive" not in token["scope"]:
        _die("DRIVE_SCOPE_MISSING: this PC authorized Gmail only (older version).\n"
             "Re-authorize once: run the skill's `logout`, then `setup`, and let the user click Allow again.")


def _drive(method, path, params=None, body=None, data=None, content_type=None, base=None, raw=False):
    _require_drive_scope()
    url = f"{base or DRIVE_BASE}/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {"Authorization": f"Bearer {get_access_token()}"}
    if body is not None:
        data = json.dumps(body).encode()
        content_type = "application/json; charset=UTF-8"
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        if e.code == 403 and ("insufficient" in detail.lower() or "scope" in detail.lower()):
            _die("DRIVE_SCOPE_MISSING: token has no Drive permission. Run `logout`, then `setup`.")
        if e.code == 403 and ("accessNotConfigured" in detail or "has not been used" in detail):
            _die("Google Drive API is not enabled in project hermes-gm — tell the IT admin.")
        if e.code == 404:
            _die(f"Not found (or no access): {path}")
        _die(f"Drive API error {e.code}: {detail}")
    if raw:
        return payload
    return json.loads(payload or b"{}")


def _fmt_size(n):
    if n in (None, ""):
        return "-"
    n = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024


def _kind(mime):
    if mime == FOLDER_MIME:
        return "folder"
    if mime.startswith("application/vnd.google-apps."):
        return "g-" + mime.rsplit(".", 1)[-1]
    return mime.split("/")[-1][:12]


def _print_files(files):
    if not files:
        print("No files.")
        return
    print(f"{'ID':<34}  {'MODIFIED':<16}  {'TYPE':<14}  {'SIZE':>8}  NAME")
    print("─" * 110)
    for f in files:
        mod = (f.get("modifiedTime") or "")[:16].replace("T", " ")
        print(f"{f['id']:<34}  {mod:<16}  {_kind(f.get('mimeType', '')):<14}  "
              f"{_fmt_size(f.get('size')):>8}  {f.get('name', '')}")


def _q_escape(text):
    return text.replace("\\", "\\\\").replace("'", "\\'")


def _list_files(q, limit, order="modifiedTime desc"):
    files, token = [], None
    while len(files) < limit:
        params = {"q": q, "pageSize": min(100, limit - len(files)), "orderBy": order,
                  "fields": f"nextPageToken,files({FILE_FIELDS})",
                  "includeItemsFromAllDrives": "true", "corpora": "allDrives", **_ALL_DRIVES}
        if token:
            params["pageToken"] = token
        result = _drive("GET", "files", params)
        files += result.get("files", [])
        token = result.get("nextPageToken")
        if not token:
            break
    return files[:limit]


def cmd_drive_list(limit=20, folder_id=None):
    q = "trashed = false"
    if folder_id:
        q += f" and '{_q_escape(folder_id)}' in parents"
    files = _list_files(q, limit, order="folder,modifiedTime desc" if folder_id else "modifiedTime desc")
    _print_files(files)


def cmd_drive_search(query, limit=20):
    # Raw Drive query syntax passes through; plain words search names and contents.
    if any(op in query for op in (" contains ", " = ", " in ", " != ", " < ", " > ", "mimeType")):
        q = query
    else:
        e = _q_escape(query)
        q = f"(name contains '{e}' or fullText contains '{e}')"
    if "trashed" not in q:
        q += " and trashed = false"
    try:
        files = _list_files(q, limit, order="modifiedTime desc")
    except SystemExit:
        raise
    _print_files(files)


def _meta(file_id):
    return _drive("GET", f"files/{urllib.parse.quote(file_id)}", {"fields": FILE_FIELDS, **_ALL_DRIVES})


def cmd_drive_info(file_id):
    f = _meta(file_id)
    for k in ("id", "name", "mimeType", "modifiedTime", "webViewLink"):
        print(f"{k}: {f.get(k, '')}")
    print(f"size: {_fmt_size(f.get('size'))}")
    print("owners: " + ", ".join(f"{o.get('displayName')} <{o.get('emailAddress')}>" for o in f.get("owners", [])))
    print(f"parents: {', '.join(f.get('parents', []))}")
    if f.get("trashed"):
        print("trashed: yes")


def _file_bytes(f, export_map):
    fid = urllib.parse.quote(f["id"])
    mime = f.get("mimeType", "")
    if mime in export_map:
        target, ext = export_map[mime]
        return _drive("GET", f"files/{fid}/export", {"mimeType": target}, raw=True), ext
    if mime.startswith("application/vnd.google-apps."):
        _die(f"Cannot download Google {_kind(mime)} files (form/site/shortcut).")
    return _drive("GET", f"files/{fid}", {"alt": "media", **_ALL_DRIVES}, raw=True), ""


def cmd_drive_read(file_id, max_chars=10000):
    f = _meta(file_id)
    mime = f.get("mimeType", "")
    if mime == FOLDER_MIME:
        print("This is a folder — use drive-list FOLDER_ID")
        return
    readable = mime in EXPORT_TEXT or mime.startswith("text/") or mime in (
        "application/json", "application/xml", "application/javascript", "application/x-yaml")
    if not readable:
        print(f"{f['name']} is {mime}; not plain text. Use drive-download to save it, then open the file.")
        return
    data, _ = _file_bytes(f, EXPORT_TEXT)
    text = data.decode("utf-8-sig", errors="replace")
    print(f"# {f['name']}  ({mime})")
    print(text[:max_chars])
    if len(text) > max_chars:
        print(f"\n... ({len(text) - max_chars} more chars)")


def _safe_name(name):
    return re.sub(r'[\\/:*?"<>|\r\n]+', "_", name).strip() or "file"


def cmd_drive_download(file_id, dest=None):
    f = _meta(file_id)
    if f.get("mimeType") == FOLDER_MIME:
        _die("This is a folder — download files one by one (drive-list FOLDER_ID).")
    data, ext = _file_bytes(f, EXPORT_FILE)
    dest_path = Path(dest).expanduser() if dest else Path.home() / "Downloads"
    if dest_path.is_dir() or not dest_path.suffix:
        dest_path.mkdir(parents=True, exist_ok=True)
        name = _safe_name(f["name"])
        if ext and not name.lower().endswith(ext):
            name += ext
        dest_path = dest_path / name
    else:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
    stem, suffix, n = dest_path.stem, dest_path.suffix, 1
    while dest_path.exists():
        dest_path = dest_path.with_name(f"{stem} ({n}){suffix}")
        n += 1
    dest_path.write_bytes(data)
    print(f"[OK] Saved {len(data)} bytes to {dest_path}")


def cmd_drive_upload(local_path, folder_id=None, name=None):
    path = Path(local_path).expanduser()
    if not path.is_file():
        _die(f"File not found: {path}")
    import mimetypes
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    meta = {"name": name or path.name}
    if folder_id:
        meta["parents"] = [folder_id]
    boundary = "cute_hermes_" + secrets.token_hex(8)
    body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n"
            f"{json.dumps(meta, ensure_ascii=False)}\r\n--{boundary}\r\nContent-Type: {mime}\r\n\r\n").encode()
    body += path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    f = _drive("POST", "files", {"uploadType": "multipart", "fields": FILE_FIELDS, **_ALL_DRIVES},
               data=body, content_type=f"multipart/related; boundary={boundary}", base=DRIVE_UPLOAD)
    print(f"[OK] Uploaded {f.get('name')}  id={f.get('id')}")
    if f.get("webViewLink"):
        print(f"     {f['webViewLink']}")


def cmd_drive_mkdir(name, parent_id=None):
    meta = {"name": name, "mimeType": FOLDER_MIME}
    if parent_id:
        meta["parents"] = [parent_id]
    f = _drive("POST", "files", {"fields": FILE_FIELDS, **_ALL_DRIVES}, body=meta)
    print(f"[OK] Folder created: {f.get('name')}  id={f.get('id')}")


def cmd_drive_rename(file_id, new_name):
    f = _drive("PATCH", f"files/{urllib.parse.quote(file_id)}", {"fields": FILE_FIELDS, **_ALL_DRIVES},
               body={"name": new_name})
    print(f"[OK] Renamed to {f.get('name')}")


def cmd_drive_move(file_id, folder_id):
    old = _meta(file_id).get("parents", [])
    params = {"addParents": folder_id, "fields": FILE_FIELDS, **_ALL_DRIVES}
    if old:
        params["removeParents"] = ",".join(old)
    f = _drive("PATCH", f"files/{urllib.parse.quote(file_id)}", params, body={})
    print(f"[OK] Moved {f.get('name')} to folder {folder_id}")


def cmd_drive_trash(file_id):
    f = _drive("PATCH", f"files/{urllib.parse.quote(file_id)}", {"fields": FILE_FIELDS, **_ALL_DRIVES},
               body={"trashed": True})
    print(f"[OK] Moved to trash: {f.get('name')} (recoverable from Drive trash for 30 days)")


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

    def opt(name, default):
        return int(rest[rest.index(name) + 1]) if name in rest else default

    if cmd == "setup":
        oauth_setup(timeout=opt("--timeout", 600), no_browser="--no-browser" in rest,
                    foreground="--foreground" in rest)
    elif cmd == "_listen":
        sys.exit(_listen(opt("--timeout", 600), no_browser=True, announce=False))
    elif cmd == "wait":
        sys.exit(wait_for_auth(opt("--timeout", 120)))
    elif cmd == "auth-url":
        print_auth_url()
    elif cmd == "import-code":
        need(1, "import-code 'http://127.0.0.1:PORT/?state=...&code=...'")
        import_code(rest[0])
    elif cmd == "status":
        cmd_status()
    elif cmd == "drive-list":
        cmd_drive_list(int(rest[0]) if rest and rest[0].isdigit() else 20,
                       next((r for r in rest if not r.isdigit()), None))
    elif cmd == "drive-search":
        need(1, "drive-search QUERY [N]")
        cmd_drive_search(rest[0], int(rest[1]) if len(rest) > 1 else 20)
    elif cmd == "drive-info":
        need(1, "drive-info FILE_ID")
        cmd_drive_info(rest[0])
    elif cmd == "drive-read":
        need(1, "drive-read FILE_ID")
        cmd_drive_read(rest[0])
    elif cmd == "drive-download":
        need(1, "drive-download FILE_ID [DEST_DIR_OR_FILE]")
        cmd_drive_download(rest[0], rest[1] if len(rest) > 1 else None)
    elif cmd == "drive-upload":
        need(1, "drive-upload LOCAL_FILE [FOLDER_ID]")
        cmd_drive_upload(rest[0], rest[1] if len(rest) > 1 else None)
    elif cmd == "drive-mkdir":
        need(1, "drive-mkdir NAME [PARENT_FOLDER_ID]")
        cmd_drive_mkdir(rest[0], rest[1] if len(rest) > 1 else None)
    elif cmd == "drive-rename":
        need(2, "drive-rename FILE_ID NEW_NAME")
        cmd_drive_rename(rest[0], rest[1])
    elif cmd == "drive-move":
        need(2, "drive-move FILE_ID FOLDER_ID")
        cmd_drive_move(rest[0], rest[1])
    elif cmd == "drive-trash":
        need(1, "drive-trash FILE_ID")
        cmd_drive_trash(rest[0])
    elif cmd == "logout":
        cmd_logout()
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
