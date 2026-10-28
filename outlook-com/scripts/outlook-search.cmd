@echo off
REM outlook-search.cmd - Search Outlook inbox
REM Usage: outlook-search.cmd [-Keyword "xxx"] [-Days 1] [-Folder "02-圖資中心"]
REM Examples:
REM   outlook-search.cmd -Keyword "法規"
REM   outlook-search.cmd -Days 3
REM   outlook-search.cmd -Keyword "法規" -Days 1 -Folder "02-圖資中心"

if "%~1"=="" (
    echo Usage: outlook-search.cmd [-Keyword "xxx"] [-Days 1] [-Folder "name"]
    exit /b 1
)

REM Step 1: Check and kill Outlook
set FOUND_OUTLOOK=0
for /f "tokens=1" %%a in ('tasklist /FI "IMAGENAME eq OUTLOOK.EXE" /NH 2^>nul ^| findstr /i "OUTLOOK"' do (
    set FOUND_OUTLOOK=1
)
if "%FOUND_OUTLOOK%"=="1" (
    echo Killing Outlook...
    taskkill /F /IM OUTLOOK.EXE
    ping -n 4 127.0.0.1 >nul
    for /f "tokens=1" %%a in ('tasklist /FI "IMAGENAME eq OUTLOOK.EXE" /NH 2^>nul ^| findstr /i "OUTLOOK"' do (
        echo WARNING: Outlook still running
        exit /b 1
    )
    echo Outlook closed.
) else (
    echo Outlook not running. OK.
)

REM Step 2: Run search (pass all args through)
powershell.exe -ExecutionPolicy Bypass -File "%~dp0outlook-search.ps1" %*

REM Step 3: Cleanup
taskkill /F /IM OUTLOOK.EXE 2>nul

REM Show results
echo.
echo === Results ===
type "%USERPROFILE%\search-result.txt"
