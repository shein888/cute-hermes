# AGENT-SETUP — install / update the cute-hermes skills on this PC

**For the Hermes agent.** The user asked you to follow this file. Do the steps in
order, run every command yourself in your terminal, and reply to the user in
Traditional Chinese (繁體中文). Do not restart Hermes or its gateway. Do not
edit any skill files. Never print tokens or secrets.

The three messages marked **【原文】** below must be sent to the user **exactly as
written** (copy them character for character, do not translate or reword).

---

## Step 0 — Tell the user what this is (before running anything)

Send this message first, then continue with Step 1:

> 【原文】這是中國科大 CUTe Hermes專屬OA skill套件, 提供Outlook API 及GM帳號授權綁定功能, 請放心下載更新

---

## Step 1 — Check the current state (read-only)

Run each command and keep the results for the report in Step 5.

```bash
hermes --version
hermes skills list
hermes skills tap list
```

From `hermes skills list`, note whether `outlook-com` and `gmail-oauth` are
installed and their versions (or "not installed").

### 1a. gm authorization on this PC

The authorization is stored outside the skill folder and is **kept** when the
skill is removed and reinstalled. Read only the safe fields:

```bash
if [ -f ~/.config/gmail-oauth/token.json ]; then
  grep -oE '"(account|scope|authorized_at|authorized_by_skill)": "[^"]*"' ~/.config/gmail-oauth/token.json
  grep -q '"refresh_token"' ~/.config/gmail-oauth/token.json && echo '"refresh_token": present'
else
  echo "gm: not authorized on this PC"
fi
```

Interpret:
- no file → this PC has never authorized a gm account (fine; the first use will show a link).
- `scope` contains `gmail.modify` only → Gmail only; Drive will ask for one more
  consent on first use (automatic, no logout needed).
- `scope` contains `gmail.modify` and `auth/drive` → Gmail + Drive ready.
- `account` missing → authorized by an older version; it is filled in on next use.

Do **not** delete or edit this file.

### 1b. Outlook on this PC

```bash
powershell.exe -NoProfile -Command '$c = Test-Path "Registry::HKEY_CLASSES_ROOT\Outlook.Application\CLSID"; $n = [bool](Get-AppxPackage -Name Microsoft.OutlookForWindows -ErrorAction SilentlyContinue); "ClassicOutlookCOM=$c  NewOutlookInstalled=$n"'
```

(In WSL, if `powershell.exe` is not found, use `/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe`.)

Interpret:
- `ClassicOutlookCOM=True` → the outlook-com skill can work.
- `ClassicOutlookCOM=False` and `NewOutlookInstalled=True` → the PC uses **New Outlook**,
  which outlook-com cannot read. Still install the skill, but tell the user they must
  switch back to classic Outlook (turn off the "New Outlook" toggle) to use it.
- both `False` → no Outlook desktop app; outlook-com will not work on this PC.

## Step 2 — Remove the old skills

Before removing anything, send this message:

> 【原文】更新後對話會重新整理, 還請見諒

Removing first is **required**: `hermes skills install` refuses to install over
an existing copy ("already installed … use --force"). Errors such as
`Tap not found`, `not found` or `not a hub-installed skill` are normal — continue.

```bash
hermes skills tap remove https://github.com/shein888/cute-hermes
hermes skills tap add shein888/cute-hermes
hermes skills uninstall outlook-com --yes
hermes skills uninstall gmail-oauth --yes
```

## Step 3 — Install the current versions

```bash
hermes skills install shein888/cute-hermes/skills/outlook-com --yes
hermes skills install shein888/cute-hermes/skills/gmail-oauth --yes
hermes skills list
```

If an install says `already installed`, run the same install line again with
`--force` added. If it says `Blocked` or a network error, stop, show the
user the exact message, and do **not** send 「已下載並更新完成」.

## Step 4 — Verify

In `hermes skills list`, both skills must be listed. Compare their versions with
the newest entries in
https://github.com/shein888/cute-hermes/blob/main/CHANGELOG.md
(at the time of writing: outlook-com 4.1.1, gmail-oauth 2.3.0 or newer).

## Step 5 — Report and ask for a new conversation

Start the reply with this message:

> 【原文】已下載並更新完成

Then, in Traditional Chinese:

1. Versions before → after for `outlook-com` and `gmail-oauth`.
2. gm: which account and which features (信箱／雲端硬碟) are authorized on this PC,
   or 「尚未授權，第一次使用時會給授權網址」.
3. Outlook: 可用（傳統版 Outlook）／這台是新版 Outlook，需要切回傳統版／沒有安裝 Outlook.
4. This sentence, exactly:
   「更新完成。請開一個新的對話（Hermes 指令列輸入 /new，或在 Desktop 開新對話分頁）再使用，
   舊的對話還會用舊版的 skill 內容。」

You cannot start the new conversation yourself — the user must do it.

## After the new conversation (for the user)

- 「gm 授權狀態」 — shows the gm account and permissions.
- 「把 gm 雲端硬碟最近的檔案列出來」 — first use may give a Google link: sign in with
  the gm account, click 允許, then tell the agent 「好了」.
- 「幫我查 Outlook 最近三天的信」 — if it fails: 「執行 outlook-search 的 -Diagnose，告訴我原因」.
