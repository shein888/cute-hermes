@echo off
REM outlook-search.cmd - Search Outlook inbox by keyword
REM Usage: outlook-search.cmd "keyword"

if "%~1"=="" (
    echo Usage: outlook-search.cmd "keyword"
    exit /b 1
)

REM Step 1: Check and kill Outlook
set FOUND_OUTLOOK=0
for /f "tokens=1" %%a in ('tasklist /FI "IMAGENAME eq OUTLOOK.EXE" /NH 2^>nul ^| findstr /i "OUTLOOK"') do (
    set FOUND_OUTLOOK=1
)
if "%FOUND_OUTLOOK%"=="1" (
    echo Killing Outlook...
    taskkill /F /IM OUTLOOK.EXE
    ping -n 4 127.0.0.1 >nul
    REM Verify it's dead
    for /f "tokens=1" %%a in ('tasklist /FI "IMAGENAME eq OUTLOOK.EXE" /NH 2^>nul ^| findstr /i "OUTLOOK"') do (
        echo WARNING: Outlook still running. Try closing it manually.
        exit /b 1
    )
    echo Outlook closed.
) else (
    echo Outlook not running. OK.
)

REM Step 2: Run search
powershell.exe -ExecutionPolicy Bypass -File "%~dp0outlook-search.ps1" "%~1"

REM Step 3: Cleanup
taskkill /F /IM OUTLOOK.EXE 2>nul

REM Show results
echo.
echo === Results ===
type "%USERPROFILE%\search-result.txt"
