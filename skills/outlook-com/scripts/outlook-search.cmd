@echo off
REM outlook-search.cmd - Windows wrapper for outlook-search.ps1
REM Usage: outlook-search.cmd -Keyword "xxx" -Days 1   ^|   outlook-search.cmd -Diagnose
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0outlook-search.ps1" %*
set RC=%ERRORLEVEL%
echo.
echo === Results ===
type "%USERPROFILE%\search-result.txt"
exit /b %RC%
