@echo off
title Hermes Dashboard

echo ========================================
echo   Hermes Agent Dashboard Launcher
echo ========================================
echo.

:: Check port forwarding
echo [1/3] Checking port forwarding...
netsh interface portproxy show all | findstr "9119 192.168.0.142" >nul 2>&1
if errorlevel 1 (
    echo       Port forwarding not set, configuring...
    netsh interface portproxy add v4tov4 listenport=9119 listenaddress=127.0.0.1 connectport=9119 connectaddress=192.168.0.142 >nul 2>&1
    echo       Done!
) else (
    echo       Port forwarding OK
)

:: Check if dashboard is already running
echo [2/3] Checking if Hermes Dashboard is running...
wsl ss -tlnp 2>nul | findstr "9119" >nul 2>&1
if not errorlevel 1 (
    echo       Hermes Dashboard is already running!
    set "ALREADY_RUNNING=1"
) else (
    echo       Not running, starting now...
    
    :: Kill residual processes
    for /f "tokens=5" %%a in ('wsl ss -tlnp 2^>nul ^| findstr "9119"') do wsl kill -9 %%a 2>nul
    timeout /t 1 /nobreak >nul

    :: Start hermes dashboard
    echo       Starting Hermes Dashboard...
    start /b wsl bash -c "/home/feather/.local/bin/hermes dashboard --host 0.0.0.0 --port 9119 --insecure --no-open" >nul 2>&1

    :: Wait for startup
    timeout /t 5 /nobreak >nul
)

:: Open browser
echo [3/3] Opening Chrome...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" "http://localhost:9119"

echo.
echo ========================================
echo   Done! Visit: http://localhost:9119
echo ========================================
pause
