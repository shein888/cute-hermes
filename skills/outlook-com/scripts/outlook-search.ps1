# outlook-search.ps1 v4 - Search classic Outlook mail via COM (MAPI)
# Usage: powershell.exe -NoProfile -ExecutionPolicy Bypass -File outlook-search.ps1
#          [-Keyword "xxx"] [-Sender "xxx"] [-Date "yyyy-MM-dd"] [-Days N]
#          [-Folder "name"] [-Recursive] [-Max 50] [-OutFile path]
# Examples:
#   outlook-search.ps1 -Keyword "法規" -Days 3
#   outlook-search.ps1 -Sender "prac" -Date "2026-10-16"
#   outlook-search.ps1 -Keyword "大綱" -Folder "02-圖資中心"
#   outlook-search.ps1 -Keyword "test" -Recursive
#   outlook-search.ps1 -Diagnose          (check why it does not work on this PC)
# Output: %USERPROFILE%\search-result.txt (UTF-8). Exit code 0 = OK, 2 = usage, 3 = Outlook/COM problem.
#
# v4 changes:
#  - Does NOT kill Outlook any more: attaches to the running Outlook (or starts it).
#  - Uses the default Inbox (GetDefaultFolder) -> works with any language / account name.
#  - Sorts by ReceivedTime and stops early when a date filter is given (much faster).
#  - Clear error messages for "New Outlook" (no COM), bitness/elevation mismatch, security prompt.

param(
    [string]$Keyword = "",
    [string]$Sender = "",
    [string]$Date = "",
    [int]$Days = 0,
    [string]$Folder = "",
    [switch]$Recursive,
    [int]$Max = 100,
    [string]$OutFile = "",
    [switch]$Diagnose
)

$ErrorActionPreference = "Stop"
if ($OutFile -eq "") { $OutFile = Join-Path $env:USERPROFILE "search-result.txt" }

function Write-Result([string[]]$lines) {
    [System.IO.File]::WriteAllLines($OutFile, $lines, (New-Object System.Text.UTF8Encoding($true)))
}

function Fail([string]$msg, [int]$code = 3) {
    Write-Host "ERROR: $msg"
    Write-Result @("ERROR: $msg")
    exit $code
}

# ── Environment checks ───────────────────────────────────────────────────
function Get-OutlookInfo {
    $info = [ordered]@{}
    $clsid = (Get-ItemProperty "Registry::HKEY_CLASSES_ROOT\Outlook.Application\CLSID" -ErrorAction SilentlyContinue)."(default)"
    $info.ComRegistered = [bool]$clsid
    $exe = (Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\OUTLOOK.EXE" -ErrorAction SilentlyContinue)."(default)"
    $info.ClassicOutlookExe = $exe
    $info.NewOutlookInstalled = [bool](Get-AppxPackage -Name "Microsoft.OutlookForWindows" -ErrorAction SilentlyContinue)
    $useNew = (Get-ItemProperty "HKCU:\Software\Microsoft\Office\16.0\Outlook\Preferences" -ErrorAction SilentlyContinue).UseNewOutlook
    $info.UseNewOutlookToggle = ($useNew -eq 1)
    $p = Get-Process OUTLOOK -ErrorAction SilentlyContinue | Select-Object -First 1
    $info.ClassicRunning = [bool]$p
    $info.PowerShellIs64Bit = [Environment]::Is64BitProcess
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $info.PowerShellElevated = (New-Object Security.Principal.WindowsPrincipal($id)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    $info.ExecutionPolicy = (Get-ExecutionPolicy -List | Where-Object { $_.ExecutionPolicy -ne "Undefined" } | ForEach-Object { "$($_.Scope)=$($_.ExecutionPolicy)" }) -join ", "
    $sec = Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Office\16.0\Outlook\Security" -ErrorAction SilentlyContinue
    $info.ObjectModelGuardPolicy = if ($sec -and $null -ne $sec.ObjectModelGuard) { $sec.ObjectModelGuard } else { "default" }
    $av = Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntiVirusProduct -ErrorAction SilentlyContinue
    $info.AntivirusRegistered = if ($av) { ($av | ForEach-Object displayName) -join ", " } else { "NONE (Outlook may show a security prompt)" }
    return $info
}

if ($Diagnose) {
    $info = Get-OutlookInfo
    $lines = @("Outlook COM diagnose  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
    foreach ($k in $info.Keys) { $lines += ("{0,-24}: {1}" -f $k, $info[$k]) }
    try {
        $o = New-Object -ComObject Outlook.Application
        $ns = $o.GetNamespace("MAPI")
        $inbox = $ns.GetDefaultFolder(6)
        $lines += "COM test                : OK  store=$($inbox.Store.DisplayName) inbox=$($inbox.Name) items=$($inbox.Items.Count)"
    } catch {
        $lines += "COM test                : FAILED  $($_.Exception.Message)"
    }
    $lines | ForEach-Object { Write-Host $_ }
    Write-Result $lines
    exit 0
}

if ($Keyword -eq "" -and $Sender -eq "" -and $Date -eq "" -and $Days -eq 0) {
    Write-Host "Usage: outlook-search.ps1 [-Keyword <text>] [-Sender <text>] [-Date yyyy-MM-dd] [-Days <n>] [-Folder <name>] [-Recursive] [-Max <n>] [-Diagnose]"
    exit 2
}

# ── Connect to Outlook ───────────────────────────────────────────────────
$outlook = $null
try {
    $outlook = [Runtime.InteropServices.Marshal]::GetActiveObject("Outlook.Application")
} catch {
    try {
        $outlook = New-Object -ComObject Outlook.Application
    } catch {
        $info = Get-OutlookInfo
        $hr = "{0:X8}" -f $_.Exception.HResult
        if (-not $info.ComRegistered) {
            if ($info.NewOutlookInstalled) {
                Fail "Classic Outlook COM is not available. This PC uses the NEW Outlook (olk.exe), which has no COM/VBA support. Install/switch back to classic Outlook (Microsoft 365 desktop) or use Graph/IMAP instead."
            }
            Fail "Outlook.Application is not registered (HRESULT 0x$hr). Classic Outlook (Office desktop) is not installed on this PC."
        }
        if ($hr -eq "80080005") {
            Fail "Cannot start/attach to Outlook (0x80080005). Usually Outlook and this PowerShell run with different privileges (one 'Run as administrator'). Run both normally, or close Outlook and retry."
        }
        Fail "Cannot create Outlook.Application (HRESULT 0x$hr): $($_.Exception.Message)"
    }
}

try {
    $ns = $outlook.GetNamespace("MAPI")
    $inbox = $ns.GetDefaultFolder(6)   # olFolderInbox — language independent
} catch {
    Fail "Outlook started but MAPI is not ready: $($_.Exception.Message). If Outlook asks to choose a profile, set a default profile (Control Panel > Mail > Always use this profile)."
}
$store = $inbox.Store
$root = $store.GetRootFolder()

# ── Date window ──────────────────────────────────────────────────────────
$startDate = $null; $endDate = $null
if ($Date -ne "") {
    try { $startDate = [datetime]::ParseExact($Date, "yyyy-MM-dd", $null) } catch { Fail "Bad -Date '$Date' (use yyyy-MM-dd)" 2 }
    $endDate = $startDate.AddDays(1)
} elseif ($Days -gt 0) {
    $startDate = (Get-Date).AddDays(-$Days)
}

# ── Folders to search ────────────────────────────────────────────────────
$folders = New-Object System.Collections.ArrayList
function Add-Recursive($f, [int]$depth) {
    if ($depth -gt 12) { return }
    [void]$folders.Add($f)
    foreach ($s in $f.Folders) { Add-Recursive $s ($depth + 1) }
}

if ($Recursive) {
    foreach ($top in $root.Folders) { Add-Recursive $top 0 }
} elseif ($Folder -ne "") {
    $target = $null
    foreach ($s in $inbox.Folders) { if ($s.Name -eq $Folder) { $target = $s; break } }
    if ($null -eq $target) {
        $names = ($inbox.Folders | ForEach-Object { $_.Name }) -join ", "
        Fail "Folder '$Folder' not found under $($inbox.Name). Available: $names" 2
    }
    [void]$folders.Add($target)
} else {
    [void]$folders.Add($inbox)
    foreach ($s in $inbox.Folders) { [void]$folders.Add($s) }
}

# ── Search ───────────────────────────────────────────────────────────────
$lines = New-Object System.Collections.Generic.List[string]
$desc = "Search"
if ($Keyword) { $desc += " keyword=$Keyword" }
if ($Sender)  { $desc += " sender=$Sender" }
if ($Date)    { $desc += " date=$Date" }
if ($Days)    { $desc += " last $Days day(s)" }
if ($Folder)  { $desc += " folder=$Folder" }
if ($Recursive) { $desc += " [recursive]" }
$lines.Add($desc)
$lines.Add("Store: $($store.DisplayName) -> $($inbox.Name)")
$lines.Add("Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
$lines.Add("")

$found = 0; $scanned = 0; $folderCount = 0
$kw = $Keyword.ToLowerInvariant(); $sd = $Sender.ToLowerInvariant()

:outer foreach ($f in $folders) {
    try {
        if ($f.DefaultItemType -ne 0) { continue }   # mail folders only
        $items = $f.Items
        $items.Sort("[ReceivedTime]", $true)          # newest first
    } catch { continue }
    $folderCount++
    $item = $items.GetFirst()
    while ($null -ne $item) {
        $scanned++
        try {
            if ($item.Class -eq 43) {
                $rt = $item.ReceivedTime
                if ($startDate -and $rt -lt $startDate) { break }   # sorted: everything after is older
                $ok = $true
                if ($endDate -and $rt -ge $endDate) { $ok = $false }
                if ($ok -and $kw) { $ok = ([string]$item.Subject).ToLowerInvariant().Contains($kw) }
                $addr = ""; $sname = ""
                if ($ok -and $sd) {
                    $sname = [string]$item.SenderName
                    try { $addr = [string]$item.SenderEmailAddress } catch {}
                    $ok = ("$addr $sname").ToLowerInvariant().Contains($sd)
                }
                if ($ok) {
                    $found++
                    if (-not $sname) { $sname = [string]$item.SenderName }
                    if (-not $addr) { try { $addr = [string]$item.SenderEmailAddress } catch {} }
                    $lines.Add("=== $($f.Name) ===")
                    $lines.Add("From: $sname <$addr>")
                    $lines.Add("Date: $($rt.ToString('yyyy-MM-dd HH:mm:ss'))")
                    $lines.Add("Subject: $([string]$item.Subject)")
                    $lines.Add("Unread: $($item.UnRead)")
                    $body = [string]$item.Body
                    if ($body) {
                        $b = $body.Substring(0, [Math]::Min(500, $body.Length))
                        $lines.Add("Body: " + ($b -replace "\r?\n", " | "))
                    }
                    $lines.Add("")
                    if ($found -ge $Max) { $lines.Add("(stopped at -Max $Max results)"); break outer }
                }
            }
        } catch {}
        $item = $items.GetNext()
    }
}

$lines.Add("-----")
$lines.Add("Searched $folderCount folders ($scanned items), found $found match(es)")
Write-Result $lines.ToArray()
Write-Host "Done: $found match(es) in $folderCount folders ($scanned items scanned)"
Write-Host "Results: $OutFile"
exit 0
