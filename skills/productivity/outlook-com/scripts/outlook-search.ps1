
# outlook-search.ps1 - Search Outlook inbox by keyword and/or time range
# Usage: powershell.exe -ExecutionPolicy Bypass -File outlook-search.ps1 [-Keyword "xxx"] [-Days 1]
# Examples:
#   outlook-search.ps1 -Keyword "法規"
#   outlook-search.ps1 -Keyword "法規" -Days 1
#   outlook-search.ps1 -Days 3              (all mail in last 3 days, no keyword)
#   outlook-search.ps1 -Keyword "法規" -Days 1 -Folder "02-圖資中心"  (specific folder)
# Output: %USERPROFILE%\search-result.txt (UTF-8)

param(
    [string]$Keyword = "",
    [int]$Days = 0,
    [string]$Folder = ""
)

if ($Keyword -eq "" -and $Days -eq 0) {
    Write-Host "Usage: outlook-search.ps1 [-Keyword <text>] [-Days <n>] [-Folder <name>]"
    Write-Host "  -Keyword: search by subject substring"
    Write-Host "  -Days: only show mail from last N days (1=24h, 3=3days)"
    Write-Host "  -Folder: limit to specific inbox subfolder"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host '  outlook-search.ps1 -Keyword "法規"'
    Write-Host '  outlook-search.ps1 -Days 1'
    Write-Host '  outlook-search.ps1 -Keyword "法規" -Days 3'
    exit 1
}

# Check and kill Outlook
$proc = Get-Process -Name "OUTLOOK" -ErrorAction SilentlyContinue
if ($proc) {
    Write-Host "Killing Outlook..."
    $proc | Stop-Process -Force
    Start-Sleep -Seconds 3
    $proc2 = Get-Process -Name "OUTLOOK" -ErrorAction SilentlyContinue
    if ($proc2) {
        Write-Host "WARNING: Outlook still running"
        exit 1
    }
    Write-Host "Outlook closed."
} else {
    Write-Host "Outlook not running."
}

$outlook = New-Object -ComObject Outlook.Application
$ns = $outlook.GetNamespace('MAPI')
$account = $ns.Folders | Where-Object { $_.Name -like "*@*" } | Select-Object -First 1
if ($account -eq $null) {
    $account = $ns.Folders | Where-Object { $_.Name -eq "Outlook" -or $_.Name -eq "Microsoft Exchange" } | Select-Object -First 1
}
if ($account -eq $null) {
    $account = $ns.Folders | Select-Object -First 1
}
if ($account -eq $null) {
    Write-Host "ERROR: No account folder found"
    exit 1
}

$inbox = $account.Folders | Where-Object { $_.Name -eq "收件匣" -or $_.Name -eq "收件箱" -or $_.Name -eq "Inbox" } | Select-Object -First 1
if ($inbox -eq $null) { $inbox = $account.Folders | Select-Object -First 1 }

# Determine date filter
$dateFilter = ""
if ($Days -gt 0) {
    $cutoff = (Get-Date).AddDays(-$Days).ToString('yyyy-MM-dd')
    $dateFilter = $cutoff
}

$lines = @()
$desc = "Search"
if ($Keyword -ne "") { $desc += " keyword=$Keyword" }
if ($Days -gt 0) { $desc += " last $Days day(s)" }
if ($Folder -ne "") { $desc += " folder=$Folder" }
$lines += $desc
$lines += "Account: $($account.Name) -> $($inbox.Name)"
$lines += "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
$lines += ""

$found = 0
$folderCount = 0

foreach ($sub in $inbox.Folders) {
    # Filter by folder name if specified
    if ($Folder -ne "" -and $sub.Name -ne $Folder) { continue }
    $folderCount++
    foreach ($item in $sub.Items) {
        if ($item.Class -ne 43) { continue }
        # Date filter
        if ($dateFilter -ne "" -and $item.ReceivedTime.ToString('yyyy-MM-dd') -lt $dateFilter) { continue }
        # Keyword filter
        if ($Keyword -ne "") {
            $subj = $item.Subject
            if ($subj -and -not $subj.Contains($Keyword)) { continue }
        }
        $found++
        $lines += "=== $($sub.Name) ==="
        $lines += "From: $($item.SenderName)"
        $lines += "Date: $($item.ReceivedTime.ToString('yyyy-MM-dd HH:mm:ss'))"
        $lines += "Subject: $($item.Subject)"
        if ($item.Body) {
            $b = $item.Body.Substring(0, [Math]::Min(500, $item.Body.Length))
            $lines += "Body: " + ($b -replace [char]13 + [char]10, ' | ')
        }
        $lines += ""
    }
}

$lines += "-----"
$lines += "Searched $folderCount folders, found $found match(es)"
$resultPath = Join-Path $env:USERPROFILE "search-result.txt"
[System.IO.File]::WriteAllLines($resultPath, $lines, [System.Text.Encoding]::UTF8)
Write-Host "Done: $found match(es) in $folderCount folders"
Write-Host "Results: $resultPath"
