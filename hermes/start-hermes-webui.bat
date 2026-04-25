@echo off
setlocal enabledelayedexpansion

wsl bash -l -c "pm2 list" | findstr "hermes-web-ui" >nul 2>&1
if !errorlevel! neq 0 (
    wsl bash -l -c "pm2 start hermes-web-ui -- start"
)

echo Waiting for server.
for /L %%i in (1,1,30) do (
    wsl bash -l -c "curl -s --connect-timeout 1 http://localhost:8648" >nul 2>&1
    if !errorlevel! equ 0 goto ready
    timeout /t 1 >nul
    echo Waiting for server.
)

:ready
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" "http://localhost:8648"
endlocal
