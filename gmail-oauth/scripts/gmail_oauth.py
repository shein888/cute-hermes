#!/usr/bin/env python3
"""
gmail_oauth.py — Gmail API OAuth2 helper for Hermes agents.

Usage:
  python3 gmail_oauth.py list              # List inbox (last 10)
  python3 gmail_oauth.py read MESSAGE_ID   # Read a message
  python3 gmail_oauth.py send TO SUBJECT BODY  # Send email
  python3 gmail_oauth.py reply TO REPLY_TO_ID BODY  # Reply
  python3 gmail_oauth.py search QUERY     # Search (Gmail search syntax)
  python3 gmail_oauth.py setup            # Run OAuth flow (first time)
  python3 gmail_oauth.py status           # Check token status
"""

import json
import os
import sys
import base64
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import datetime

# ─── Config ───────────────────────────────────────────────────────────────
CLIENT_ID = os.environ.get("GMAIL_OAUTH_CLIENT_ID", "930386946858-3d63m2dmik1caej2cam2c4mtnp83b9jh.apps.googleusercontent.com")
CLIENT_SECRET = os.environ.get("GMAIL_OAUTH_CLIENT_SECRET", "")
SCOPES = "https://www.googleapis.com/auth/gmail.modify"
REDIRECT_URI = "http://localhost:8080"
TOKEN_FILE = Path.home() / ".config" / "gmail-oauth" / "token.json"
API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


# ─── Token helpers ────────────────────────────────────────────────────────
def load_token():
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE) as f:
            return json.load(f)
    return None


def save_token(token_data):
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)


def get_access_token():
    """Get a valid access token, refreshing if needed."""
    token = load_token()
    if not token:
        print("No token found. Run: python3 gmail_oauth.py setup", file=sys.stderr)
        sys.exit(1)

    # Check if expired (with 60s buffer)
    now = datetime.now().timestamp()
    if token.get("expires_at") and now > token["expires_at"] - 60:
        if "refresh_token" not in token:
            print("Token expired and no refresh token. Re-run setup.", file=sys.stderr)
            sys.exit(1)
        token = refresh_token(token["refresh_token"])
    return token["access_token"]


def refresh_token(refresh_tok):
    data = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_tok,
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    result["expires_at"] = datetime.now().timestamp() + result.get("expires_in", 3600)
    result["refresh_token"] = refresh_tok
    save_token(result)
    return result


# ─── OAuth flow ──────────────────────────────────────────────────────────
def oauth_setup():
    """Run the full OAuth2 authorization code flow."""
    import http.server
    import threading

    if not CLIENT_ID:
        print("ERROR: GMAIL_OAUTH_CLIENT_ID not set.", file=sys.stderr)
        print("Set it in ~/.config/gmail-oauth/env or export it.", file=sys.stderr)
        sys.exit(1)
    if not CLIENT_SECRET:
        print("ERROR: GMAIL_OAUTH_CLIENT_SECRET not set.", file=sys.stderr)
        print("Set it in ~/.config/gmail-oauth/env or export it.", file=sys.stderr)
        sys.exit(1)

    params = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
    })
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{params}"

    print(f"\nOpening browser for Google sign-in...")
    print(f"URL: {auth_url}\n")

    # Try to open browser
    import webbrowser
    webbrowser.open(auth_url)

    # Wait for callback on localhost:8080
    captured = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/?code="):
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                if "code" in query:
                    captured["code"] = query["code"][0]
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"<html><body><h2>Gmail OAuth complete!</h2><p>You can close this tab.</p></body></html>")
                else:
                    err = query.get("error", ["unknown"])[0]
                    captured["error"] = err
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(f"<h2>Error: {err}</h2>".encode())
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format, *args):
            pass  # Suppress default logging

    server = http.server.HTTPServer(("127.0.0.1", 8080), Handler)
    server.timeout = 300  # 5 min timeout

    print("Waiting for browser callback (5 min timeout)...")
    server.handle_request()
    server.server_close()

    if "error" in captured:
        print(f"OAuth error: {captured['error']}", file=sys.stderr)
        sys.exit(1)

    if "code" not in captured:
        print("No code received. Timed out.", file=sys.stderr)
        sys.exit(1)

    # Exchange code for token
    data = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": captured["code"],
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    }).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req) as resp:
        token = json.loads(resp.read())

    token["expires_at"] = datetime.now().timestamp() + token.get("expires_in", 3600)
    save_token(token)
    print(f"\n[OK] Token saved to {TOKEN_FILE}")
    print(f"   Expires in {token.get('expires_in', 'unknown')}s")
    if token.get("refresh_token"):
        print("   Refresh token saved (auto-refreshes forever)")
    else:
        print("   WARNING: No refresh token received. Token will expire.")


# ─── API calls ───────────────────────────────────────────────────────────
def api_get(path):
    token = get_access_token()
    url = f"{API_BASE}/{path}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def api_post(path, data):
    token = get_access_token()
    url = f"{API_BASE}/{path}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def decode_mime(raw_b64):
    """Decode a Gmail raw message (MIME base64url)."""
    raw = base64.urlsafe_b64decode(raw_b64 + "==")
    # Try to decode as UTF-8, fallback to latin-1
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def extract_subject(raw_mime):
    """Extract Subject from raw MIME."""
    for line in raw_mime.split("\n"):
        if line.lower().startswith("subject:"):
            return line[8:].strip()
    return "(no subject)"


def extract_from(raw_mime):
    for line in raw_mime.split("\n"):
        if line.lower().startswith("from:"):
            return line[5:].strip()
    return "(unknown)"


def cmd_list(limit=10):
    result = api_get(f"messages?maxResults={limit}&q=is:inbox")
    messages = result.get("messages", [])
    if not messages:
        print("Inbox is empty.")
        return

    print(f"{'ID':<30}  {'DATE':<22}  {'FROM':<35}  SUBJECT")
    print("─" * 120)
    for msg in messages:
        detail = api_get(f"messages/{msg['id']}")
        headers = detail.get("payload", {}).get("headers", [])
        subj = extract_subject(decode_mime(detail["raw"]))
        frm = extract_from(decode_mime(detail["raw"]))
        date = detail.get("internalDate", "")
        if date:
            date_str = datetime.fromtimestamp(int(date) / 1000).strftime("%Y-%m-%d %H:%M")
        else:
            date_str = "unknown"
        print(f"{msg['id']:<30}  {date_str:<22}  {frm[:35]:<35}  {subj[:50]}")


def cmd_read(message_id):
    detail = api_get(f"messages/{message_id}?format=raw")
    raw = decode_mime(detail["raw"])
    # Print full message
    print(raw[:5000])
    if len(raw) > 5000:
        print(f"\n... ({len(raw) - 5000} more chars)")


def cmd_send(to, subject, body):
    mime = (
        f"To: {to}\r\n"
        f"Subject: {subject}\r\n"
        f"Content-Type: text/plain; charset=utf-8\r\n"
        f"\r\n"
        f"{body}\r\n"
    )
    raw_b64 = base64.urlsafe_b64encode(mime.encode("utf-8")).decode("ascii")
    result = api_post("messages/send", {"raw": raw_b64})
    print(f"[OK] Sent. Message ID: {result.get('id')}")
    print(f"     Thread ID: {result.get('threadId')}")


def cmd_reply(to, thread_id, body):
    # Get original message for headers
    mime = (
        f"To: {to}\r\n"
        f"Subject: Re: (reply)\r\n"
        f"References: {thread_id}\r\n"
        f"Content-Type: text/plain; charset=utf-8\r\n"
        f"\r\n"
        f"{body}\r\n"
    )
    raw_b64 = base64.urlsafe_b64encode(mime.encode("utf-8")).decode("ascii")
    result = api_post("messages/send", {"raw": raw_b64, "threadId": thread_id})
    print(f"[OK] Replied. Message ID: {result.get('id')}")


def cmd_search(query, limit=10):
    result = api_get(f"messages?maxResults={limit}&q={urllib.parse.quote(query)}")
    messages = result.get("messages", [])
    if not messages:
        print(f"No results for: {query}")
        return

    print(f"{'ID':<30}  {'DATE':<22}  SUBJECT")
    print("─" * 90)
    for msg in messages:
        detail = api_get(f"messages/{msg['id']}")
        subj = extract_subject(decode_mime(detail["raw"]))
        date = detail.get("internalDate", "")
        if date:
            date_str = datetime.fromtimestamp(int(date) / 1000).strftime("%Y-%m-%d %H:%M")
        else:
            date_str = "unknown"
        print(f"{msg['id']:<30}  {date_str:<22}  {subj[:50]}")


def cmd_status():
    token = load_token()
    if not token:
        print("No token. Run: python3 gmail_oauth.py setup")
        return

    print(f"Token file: {TOKEN_FILE}")
    print(f"Email: {token.get('email', 'unknown')}")
    if token.get("expires_at"):
        now = datetime.now().timestamp()
        remaining = int(token["expires_at"] - now)
        if remaining > 0:
            print(f"Access token: valid for {remaining}s")
        else:
            print("Access token: EXPIRED (will auto-refresh)")
    if token.get("refresh_token"):
        print("Refresh token: present (auto-refresh works)")
    else:
        print("Refresh token: MISSING (token will expire permanently)")


# ─── Main ────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd == "setup":
        oauth_setup()
    elif cmd == "status":
        cmd_status()
    elif cmd == "list":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        cmd_list(limit)
    elif cmd == "read":
        if len(sys.argv) < 3:
            print("Usage: gmail_oauth.py read MESSAGE_ID")
            sys.exit(1)
        cmd_read(sys.argv[2])
    elif cmd == "send":
        if len(sys.argv) < 5:
            print("Usage: gmail_oauth.py send TO SUBJECT BODY")
            sys.exit(1)
        cmd_send(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "reply":
        if len(sys.argv) < 4:
            print("Usage: gmail_oauth.py reply TO THREAD_ID BODY")
            sys.exit(1)
        cmd_reply(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "(reply)")
    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: gmail_oauth.py search QUERY")
            sys.exit(1)
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        cmd_search(sys.argv[2], limit)
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
