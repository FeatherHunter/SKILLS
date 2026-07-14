@echo off
REM ============================================================
REM  智剪工坊 · Windows 一键安装脚本
REM  作用:装 Python 依赖 + 探测/装 ffmpeg + 创建目录 + 写配置
REM  用法:setup.bat
REM ============================================================
setlocal EnableDelayedExpansion

echo.
echo ============================================================
echo   智剪工坊 - Windows 安装程序
echo ============================================================
echo.

REM ----- 1. 探测 Python -----
echo [1/5] 探测 Python...
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    where py >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] 找不到 Python。请先装 Python 3.10+:https://www.python.org/downloads/
        echo         安装时勾选 "Add Python to PATH"
        exit /b 1
    ) else (
        set PY=py -3
    )
) else (
    set PY=python
)

for /f "tokens=2" %%v in ('%PY% --version 2^>^&1') do set PYVER=%%v
echo   [OK] Python !PYVER! (%PY%)

REM 检查版本 >= 3.10
for /f "tokens=1,2 delims=." %%a in ("!PYVER!") do (
    set MAJOR=%%a
    set MINOR=%%b
)
if !MAJOR! LSS 3 (
    echo [ERROR] Python 3.10+ 才支持,当前 !PYVER!
    exit /b 1
)
if !MAJOR! EQU 3 if !MINOR! LSS 10 (
    echo [ERROR] Python 3.10+ 才支持,当前 !PYVER!
    exit /b 1
)

REM ----- 2. 装依赖(清华源) -----
echo.
echo [2/5] 装 Python 依赖(清华源加速)...
%PY% -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] 清华源失败,改用默认源...
    %PY% -m pip install --upgrade pip
)

%PY% -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] 依赖安装失败。可手动重试:pip install -r requirements.txt
    exit /b 1
)
echo   [OK] 核心依赖装好

REM ----- 3. 装 imageio_ffmpeg(自带 ffmpeg 二进制) -----
echo.
echo [3/5] 装 ffmpeg(imageio_ffmpeg 自带)...
%PY% -m pip install imageio-ffmpeg -i https://pypi.tuna.tsinghua.edu.cn/simple
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] 清华源失败,改用默认源...
    %PY% -m pip install imageio-ffmpeg
)
%PY% -c "import imageio_ffmpeg; print('  [OK] ffmpeg:', imageio_ffmpeg.get_ffmpeg_exe())"

REM ----- 4. 装 ffprobe（imageio_ffmpeg 只有 ffmpeg 没 ffprobe）-----
echo.
echo [4/6] 装 ffprobe...
%PY% tools/install_ffprobe.py

REM ----- 5. 创建目录 + 写 config.json -----
echo.
echo [5/6] 创建目录结构...
if not exist assets\fonts        mkdir assets\fonts
if not exist assets\luts         mkdir assets\luts
if not exist assets\templates    mkdir assets\templates
if not exist assets\test_videos  mkdir assets\test_videos
if not exist assets\output       mkdir assets\output
if not exist assets\cache        mkdir assets\cache
echo   [OK] 目录就位

REM 写 config.json
%PY% -c "import imageio_ffmpeg, json, os; print('  [OK] config.json:', json.dumps({'ffmpeg_path': imageio_ffmpeg.get_ffmpeg_exe(), 'python_version': '!PYVER!', 'platform': 'windows'}, ensure_ascii=False, indent=2))" > config.json.tmp
move /Y config.json.tmp config.json >nul 2>&1

REM ----- 5. 跑 verify.py 验证 -----
echo.
echo [6/6] 跑 verify.py 验证环境...
%PY% verify.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [WARN] verify.py 有失败项,但安装已完成。看上面输出排查。
) else (
    echo.
    echo ============================================================
    echo   [DONE] 智剪工坊安装完成!
    echo ============================================================
    echo.
    echo   下一步:
    echo     1. cd %CD%
    echo     2. python verify.py    ^<^-- 再跑一遍确认
    echo     3. python scripts\cut.py --help    ^<^-- 看看能用啥
    echo.
    echo   详细文档:README.md / docs\GETTING_STARTED.md
    echo ============================================================
)

endlocal
