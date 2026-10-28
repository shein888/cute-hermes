
# outlook-search.ps1 - Search Outlook mail by keyword, sender, date, and/or time range
# Usage: powershell.exe -ExecutionPolicy Bypass -File outlook-search.ps1 [-Keyword "xxx"] [-Sender "xxx"] [-Date "yyyy-MM-dd"] [-Days N] [-Folder "name"] [-Recursive]
# Examples:
#   outlook-search.ps1 -Keyword "法規"
#   outlook-search.ps1 -Keyword "法規" -Days 1
#   outlook-search.ps1 -Days 3              (all mail in last 3 days, no keyword)
#   outlook-search.ps1 -Sender "prac@cute.edu.tw"          (search by sender)
#   outlook-search.ps1 -Sender "prac" -Date "2026-10-16"   (sender + specific date)
#   outlook-search.ps1 -Keyword "大綱" -Folder "02-圖資中心"  (specific folder)
#   outlook-search.ps1 -Keyword "test" -Recursive           (search all folders recursively)
# Output: %USERPROFILE%\search-result.txt (UTF-8)

param(
    [string]$Keyword = "",
    [string]$Sender = "",
    [string]$Date = "",
    [int]$Days = 0,
    [string]$Folder = "",
    [switch]$Recursive
)

# Require at least one search criterion
if ($Keyword -eq "" -and $Sender -eq "" -and $Date -eq "" -and $Days -eq 0) {
    Write-Host "Usage: outlook-search.ps1 [-Keyword <text>] [-Sender <email>] [-Date yyyy-MM-dd] [-Days <n>] [-Folder <name>] [-Recursive]"
    Write-Host ""
    Write-Host "  -Keyword: search by subject substring"
    Write-Host "  -Sender: search by sender email/name (partial match)"
    Write-Host "  -Date: exact date (yyyy-MM-dd)"
    Write-Host "  -Days: only show mail from last N days (1=24h, 3=3days)"
    Write-Host "  -Folder: limit to specific inbox subfolder"
    Write-Host "  -Recursive: search ALL folders recursively (slower)"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host '  outlook-search.ps1 -Keyword "法規"'
    Write-Host '  outlook-search.ps1 -Sender "prac@cute.edu.tw"'
    Write-Host '  outlook-search.ps1 -Sender "prac" -Date "2026-10-16"'
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
if ($Date -ne "") {
    $dateFilter = $Date
} elseif ($Days -gt 0) {
    $dateFilter = (Get-Date).AddDays(-$Days).ToString('yyyy-MM-dd')
}

# Build search description
$lines = @()
$desc = "Search"
if ($Keyword -ne "") { $desc += " keyword=$Keyword" }
if ($Sender -ne "") { $desc += " sender=$Sender" }
if ($Date -ne "") { $desc += " date=$Date" }
if ($Days -gt 0) { $desc += " last $Days day(s)" }
if ($Folder -ne "") { $desc += " folder=$Folder" }
if ($Recursive) { $desc += " [recursive]" }
$lines += $desc
$lines += "Account: $($account.Name) -> $($inbox.Name)"
$lines += "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
$lines += ""

# Build folder list to search
$foldersToSearch = @()

if ($Recursive) {
    # Search ALL folders recursively (account level)
    Write-Host "Searching all folders recursively (slower)..."
    
    function Get-FoldersRecursive($folder, $depth = 0) {
        if ($depth -gt 10) { return }
        $folderList = @()
        foreach ($sub in $folder.Folders) {
            $folderList += ,@{ Name=$sub.Name; Folder=$sub }
            $folderList += Get-FoldersRecursive $sub ($depth + 1)
        }
        return $folderList
    }
    
    foreach ($top in $account.Folders) {
        # Always include the top folder itself
        $foldersToSearch += ,@{ Name=$top.Name; Folder=$top }
        # And all subfolders
        foreach ($sub in Get-FoldersRecursive $top) {
            $foldersToSearch += $sub
        }
    }
} else {
    # Default: search inbox root + subfolders
    if ($Folder -ne "") {
        # Specific subfolder only
        $targetFolder = $inbox.Folders | Where-Object { $_.Name -eq $Folder } | Select-Object -First 1
        if ($targetFolder -eq $null) {
            Write-Host "ERROR: Folder '$Folder' not found in inbox"
            exit 1
        }
        $foldersToSearch += ,@{ Name=$targetFolder.Name; Folder=$targetFolder }
    } else {
        # Inbox root (FIX: was missing before) + all subfolders
        $foldersToSearch += ,@{ Name=$inbox.Name; Folder=$inbox }
        foreach ($sub in $inbox.Folders) {
            $foldersToSearch += ,@{ Name=$sub.Name; Folder=$sub }
        }
    }
}

# Helper: match an item against all filters
function Test-Match($item) {
    if ($item.Class -ne 43) { return $false }
    
    # Date filter
    if ($dateFilter -ne "") {
        if ($Date -ne "") {
            # Exact date match
            $rt = $item.ReceivedTime
            if ($rt -eq $null) { return $false }
            if ($rt.ToString('yyyy-MM-dd') -ne $Date) { return $false }
        } else {
            # Date range (last N days)
            if ($item.ReceivedTime -eq $null) { return $false }
            if ($item.ReceivedTime.ToString('yyyy-MM-dd') -lt $dateFilter) { return $false }
        }
    }
    
    # Keyword filter (subject)
    if ($Keyword -ne "") {
        $subj = [string]$item.Subject
        if (-not $subj.Contains($Keyword)) { return $false }
    }
    
    # Sender filter
    if ($Sender -ne "") {
        $addr = ""
        $name = ""
        try { $addr = [string]$item.SenderEmailAddress } catch {}
        try { $name = [string]$item.SenderName } catch {}
        $combined = "$addr $name"
        if (-not $combined.Contains($Sender)) { return $false }
    }
    
    return $true
}

# Search
$found = 0
$scanned = 0
$folderCount = 0

foreach ($fs in $foldersToSearch) {
    $folderName = $fs.Name
    $folder = $fs.Folder
    
    try {
        $itemCount = $folder.Items.Count
    } catch {
        continue
    }
    
    $folderCount++
    $scanned += $itemCount
    
    foreach ($item in $folder.Items) {
        if (-not (Test-Match $item)) { continue }
        
        $found++
        $lines += "=== $folderName ==="
        $addr = ""
        $sname = ""
        try { $addr = [string]$item.SenderEmailAddress } catch {}
        try { $sname = [string]$item.SenderName } catch {}
        $lines += "From: $sname <$addr>"
        $lines += "Date: $($item.ReceivedTime.ToString('yyyy-MM-dd HH:mm:ss'))"
        $lines += "Subject: $([string]$item.Subject)"
        if ($item.Body) {
            $b = $item.Body.Substring(0, [Math]::Min(500, $item.Body.Length))
            $lines += "Body: " + ($b -replace [char]13 + [char]10, ' | ')
        }
        $lines += ""
    }
}

$lines += "-----"
$lines += "Searched $folderCount folders ($scanned items), found $found match(es)"
$resultPath = Join-Path $env:USERPROFILE "search-result.txt"
[System.IO.File]::WriteAllLines($resultPath, $lines, [System.Text.Encoding]::UTF8)
Write-Host "Done: $found match(es) in $folderCount folders ($scanned items scanned)"
Write-Host "Results: $resultPath"
