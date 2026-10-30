# Changelog

各電腦更新方式：照 [使用說明](docs/使用說明.md) 第 1 節重裝，然後開新對話。

## 2026-10-30
- **gmail-oauth 2.4.0**：新增「gm 新信通知」：`new` 指令只列出上次檢查後新進收件匣的信；`install-watch` + Hermes 排程（no-agent、每 5 分鐘）主動通知，沒有新信不出聲、不耗 token。
- 新增 **AGENT-SETUP.md**：一句話叫 agent「檢查 gm 授權／Outlook → 移除 → 重裝 → 驗證 → 請使用者 /new」。
- **gmail-oauth 2.3.0**：每台電腦記錄 gm 帳號、已授權功能、授權時間；缺權限時自動給授權網址（`REAUTH_REQUIRED`），不需解除綁定。`status` 可查看。

## 2026-10-29
- **gmail-oauth 2.2.2**：信件清單改成一封一個區塊（修正寄件人與主旨對錯）。
- **gmail-oauth 2.2.1**：中文主旨（`=?UTF-8?B?...`）一律解碼。
- **gmail-oauth 2.2.0**：新增 gm 雲端硬碟（列出／搜尋／讀取／下載／上傳／建資料夾／改名／搬移／丟垃圾桶），Google Cloud 專案啟用 Drive API。

## 2026-10-28
- **outlook-com 4.1.1／gmail-oauth 2.1.1**：修正 `platforms`（原本寫 `wsl`，Hermes 不認得，WSL 上 Outlook skill 會被隱藏）；新增 gmail `logout`。
- **outlook-com 4.1.0／gmail-oauth 2.1.0**：支援 Hermes Desktop（Windows／Git Bash）；gm 授權改成背景等待，agent 可以立刻把授權網址給使用者。
- **outlook-com 4.0.0／gmail-oauth 2.0.0**：改成 `skills/` 結構、移除 `curl | bash`（原本會被 Hermes 安全掃描擋下）、程式隨 skill 一起安裝；Outlook 不再強制關閉、改用預設收件匣、新增 `-Diagnose`；Gmail 改用 loopback + PKCE、修正 WSL 不會開瀏覽器、補上 `reply`。
