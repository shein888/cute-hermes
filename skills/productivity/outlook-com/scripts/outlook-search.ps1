
# outlook-search.ps1 - Search Outlook inbox by keyword
# Usage: powershell.exe -ExecutionPolicy Bypass -File outlook-search.ps1 "keyword"
# Output: %USERPROFILE%\search-result.txt (UTF-8)

param(
    [string]$Keyword = ""
)

if ($Keyword -eq "") {
    Write-Host "Usage: outlook-search.ps1 <keyword>"
    exit 1
}

# Check and kill Outlook
$proc = Get-Process -Name "OUTLOOK" -ErrorAction SilentlyContinue
if ($proc) {
    Write-Host "Killing Outlook..."
    $proc | Stop-Process -Force
    Start-Sleep -Seconds 3
    # Verify
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
    # Fallback: use Outlook root folder
    $account = $ns.Folders | Where-Object { $_.Name -eq "Outlook" -or $_.Name -eq "Microsoft Exchange" } | Select-Object -First 1
    if ($account -eq $null) {
        $account = $ns.Folders | Select-Object -First 1
    }
}
if ($account -eq $null) {
    Write-Host "ERROR: No account folder found"
    exit 1
}

$inbox = $account.Folders | Where-Object { $_.Name -eq "收件匣" -or $_.Name -eq "收件箱" -or $_.Name -eq "Inbox" } | Select-Object -First 1
if ($inbox -eq $null) { $inbox = $account.Folders | Select-Object -First 1 }

$lines = @()
$lines += "Search: $Keyword"
$lines += "Account: $($account.Name) -> $($inbox.Name)"
$lines += "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
$lines += ""

$found = 0
$folderCount = 0

foreach ($sub in $inbox.Folders) {
    $folderCount++
    foreach ($item in $sub.Items) {
        if ($item.Class -ne 43) { continue }
        $subj = $item.Subject
        if ($subj -and $subj.Contains($Keyword)) {
            $found++
            $lines += "=== $($sub.Name) ==="
            $lines += "From: $($item.SenderName)"
            $lines += "Date: $($item.ReceivedTime.ToString('yyyy-MM-dd HH:mm:ss'))"
            $lines += "Subject: $($item.Subject)"
            if ($item.Body) {
                $b = $item.Body.Substring(0, [Math]::Min(1000, $item.Body.Length))
                $lines += 'Body: ' + ($b -replace [char]13 + [char]10, ' | ')
            }
            $lines += ""
        }
    }
}

$lines += "-----"
$lines += "Searched $folderCount folders, found $found match(es)"
$resultPath = Join-Path $env:USERPROFILE "search-result.txt"
[System.IO.File]::WriteAllLines($resultPath, $lines, [System.Text.Encoding]::UTF8)
Write-Host "Done: $found match(es) in $folderCount folders"
Write-Host "Results: $resultPath"
