@echo off
chcp 65001 > nul
cd /d %~dp0

REM 检查 HTTP server 是否在 8000 端口
netstat -ano | findstr :8000 > nul
if %ERRORLEVEL%==0 (
    echo [HTTP server] 已在 8000 端口运行
) else (
    echo [HTTP server] 启动中...
    start "智剪工坊-HTTP" cmd /k "wsl python3 -m http.server 8000"
    timeout /t 2 > nul
)

REM 启动 Chrome debug 模式(打开了 ?demo=1 自动装载)
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir="C:\Users\Public\chrome-debug-profile" "http://localhost:8000/%E6%99%BA%E5%89%AA%E5%B7%A5%E5%9D%8A-%E6%84%8F%E5%9B%BE%E7%BC%96%E8%BE%91.html?demo=1"

echo.
echo ============================================
echo 智剪工坊 测试已启动
echo.
echo 无 demo:  http://localhost:8000/%E6%99%BA%E5%89%AA%E5%B7%A5%E5%9D%8A-%E6%84%8F%E5%9B%BE%E7%BC%96%E8%BE%91.html
echo auto demo:  http://localhost:8000/%E6%99%BA%E5%89%AA%E5%B7%A5%E5%9D%8A-%E6%84%8F%E5%9B%BE%E7%BC%96%E8%BE%91.html?demo=1
echo ============================================
echo.
timeout /t 3 > nul
