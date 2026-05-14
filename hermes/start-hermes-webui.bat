@echo off
setlocal
wsl bash -l -c "pm2 list" | findstr "hermes-web-ui" >nul 2>&1
if !errorlevel! neq 0 (
    wsl bash -l -c "pm2 start hermes-web-ui -- start"
setlocal enabledelayedexpansion
for /f "delims=" %%i in ('wsl bash -l -c "hermes-web-ui start" 2^>^&1') do (
    echo %%i | findstr /C:"?token=" >nul 2>&1
    if !errorlevel! equ 0 (
        set "URL=%%i"
    )
)


if defined TOKEN (
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" "http://localhost:8648?token=%TOKEN%"
    start "" "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" "!URL!"
) else (
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" "http://localhost:8648"
)
)