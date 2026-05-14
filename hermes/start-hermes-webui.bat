@echo off
setlocal enabledelayedexpansion
for /f "delims=" %%i in ('wsl bash -l -c "hermes-web-ui start" 2^>^&1') do (
    echo %%i | findstr /C:"?token=" >nul 2>&1
    if !errorlevel! equ 0 (
        set "URL=%%i"
    )
)

if defined URL (
    set "URL=!URL: =!"
    start "" "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" "!URL!"
) else (
    timeout /t 1 /nobreak >nul
    start "" "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" "http://localhost:8648"
)