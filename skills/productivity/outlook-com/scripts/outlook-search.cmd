@echo off
REM outlook-search.cmd - Search Outlook inbox by keyword
REM Usage: outlook-search.cmd "keyword"
REM Example: outlook-search.cmd "法规汇编"

if "%~1"=="" (
    echo Usage: outlook-search.cmd "keyword"
    echo Example: outlook-search.cmd "法规汇编"
    exit /b 1
)

REM Kill Outlook if running
taskkill /F /IM OUTLOOK.EXE 2>nul
ping -n 3 127.0.0.1 >nul

REM Run search
powershell.exe -ExecutionPolicy Bypass -File "%~dp0outlook-search.ps1" "%~1"

REM Kill Outlook again (COM launches it)
taskkill /F /IM OUTLOOK.EXE 2>nul

REM Show results
echo.
echo === Results ===
type "%USERPROFILE%\search-result.txt"
