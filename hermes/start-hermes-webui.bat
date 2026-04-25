@echo off
chcp 65001 >nul 2>&1
title Hermes Web UI

echo ==========================================
echo   Hermes Web UI Launcher
echo ==========================================
echo.

set "WSL=C:\Windows\System32\wsl.exe"

echo [1/3] Checking Hermes Web UI status...
%WSL% hermes-web-ui status >nul 2>&1
if errorlevel 1 (
    echo       Not running, starting...
    %WSL% hermes-web-ui start >nul 2>&1
    echo       Started!
) else (
    echo       Already running, reusing!
)

echo [2/3] Waiting for server...
timeout /t 3 /nobreak >nul

echo       Reading auth token...
echo       DEBUG: WSL path = %WSL%
echo       DEBUG: USERPROFILE = %USERPROFILE%
%WSL% sh -c "grep 'token:' ~/.hermes-web-ui/server.log | sed 's/.*token: //'" > "%USERPROFILE%\hermes_token.txt" 2>nul
if errorlevel 1 (
    echo       ERROR: WSL command failed
    pause
    exit /b 1
)
echo       DEBUG: token file written

for /f "usebackq delims=" %%a in ("%USERPROFILE%\hermes_token.txt") do set "TOKENFILE=%%a"
echo       DEBUG: TOKENFILE = %TOKENFILE%

if not defined TOKENFILE (
    echo       ERROR: Could not get token
    echo       DEBUG: token file contents:
    type "%USERPROFILE%\hermes_token.txt"
    pause
    exit /b 1
)

echo [3/3] Opening Chrome...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" "http://localhost:8648/#/?token=%TOKENFILE%"

echo.
echo ==========================================
echo   Done! http://localhost:8648
echo ==========================================
pause
