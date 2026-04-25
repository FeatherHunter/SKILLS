@echo off
setlocal
wsl bash -l -c "pm2 list" | findstr "hermes-web-ui" >nul 2>&1
if !errorlevel! neq 0 (
    wsl bash -l -c "pm2 start hermes-web-ui -- start"
)
set "WSL_TOKEN_PATH=\\wsl.localhost\Ubuntu-22.04\home\feather\.hermes-web-ui\.token"

for /f "usebackq tokens=*" %%i in (`powershell.exe -NoProfile -Command "try { (Get-Content -Path '%WSL_TOKEN_PATH%' -Raw).Trim() } catch { '' }"`) do set "TOKEN=%%i"

if defined TOKEN (
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" "http://localhost:8648?token=%TOKEN%"
) else (
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" "http://localhost:8648"
)
