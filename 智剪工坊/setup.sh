#!/usr/bin/env bash
# ============================================================
#  智剪工坊 · Mac/Linux 一键安装脚本
#  作用:装 Python 依赖 + 探测/装 ffmpeg + 创建目录 + 写配置
#  用法:bash setup.sh
# ============================================================
set -e

echo
echo "============================================================"
echo "  智剪工坊 - Mac/Linux 安装程序"
echo "============================================================"
echo

# ----- 1. 探测 Python -----
echo "[1/5] 探测 Python..."
if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    echo "[ERROR] 找不到 python3。请先装 Python 3.10+:"
    echo "  Mac:   brew install python@3.11"
    echo "  Linux: sudo apt install python3 python3-pip"
    exit 1
fi

PYVER=$($PY --version 2>&1 | awk '{print $2}')
echo "  [OK] Python $PYVER ($PY)"

# 检查版本 >= 3.10
MAJOR=$(echo "$PYVER" | cut -d. -f1)
MINOR=$(echo "$PYVER" | cut -d. -f2)
if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]); then
    echo "[ERROR] Python 3.10+ 才支持,当前 $PYVER"
    exit 1
fi

# ----- 2. 装依赖(清华源) -----
echo
echo "[2/5] 装 Python 依赖(清华源加速)..."
$PY -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple || {
    echo "[WARN] 清华源失败,改用默认源..."
    $PY -m pip install --upgrade pip
}

$PY -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple || {
    echo "[ERROR] 依赖安装失败。可手动重试:pip install -r requirements.txt"
    exit 1
}
echo "  [OK] 核心依赖装好"

# ----- 3. 装 imageio_ffmpeg(自带 ffmpeg 二进制) -----
echo
echo "[3/5] 装 ffmpeg(imageio_ffmpeg 自带)..."
$PY -m pip install imageio-ffmpeg -i https://pypi.tuna.tsinghua.edu.cn/simple || {
    echo "[WARN] 清华源失败,改用默认源..."
    $PY -m pip install imageio-ffmpeg
}
FFMPEG_PATH=$($PY -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())")
echo "  [OK] ffmpeg: $FFMPEG_PATH"

# Mac 额外建议装 ffmpeg(支持硬件编码)
if [[ "$OSTYPE" == "darwin"* ]]; then
    if ! command -v ffmpeg &>/dev/null; then
        echo "  [INFO] Mac 建议用 brew 装 ffmpeg(支持 VideoToolbox 硬件加速):"
        echo "         brew install ffmpeg"
    fi
fi

# Linux 字体提示
if [[ "$OSTYPE" == "linux"* ]]; then
    if ! fc-list :lang=zh 2>/dev/null | grep -qi "noto\|wqy"; then
        echo "  [INFO] Linux 没装中文字体,烧字幕会乱码。建议:"
        echo "         sudo apt install fonts-noto-cjk"
    fi
fi

# ----- 4. 创建目录 + 写 config.json -----
echo
echo "[4/5] 创建目录结构..."
mkdir -p assets/fonts assets/luts assets/templates assets/test_videos assets/output assets/cache
echo "  [OK] 目录就位"

# 写 config.json
$PY -c "
import imageio_ffmpeg, json, sys
config = {
    'ffmpeg_path': imageio_ffmpeg.get_ffmpeg_exe(),
    'python_version': '$PYVER',
    'platform': sys.platform,
}
print(json.dumps(config, ensure_ascii=False, indent=2))
" > config.json
echo "  [OK] config.json 写好"

# ----- 5. 跑 verify.py 验证 -----
echo
echo "[5/5] 跑 verify.py 验证环境..."
if $PY verify.py; then
    echo
    echo "============================================================"
    echo "  [DONE] 智剪工坊安装完成!"
    echo "============================================================"
    echo
    echo "  下一步:"
    echo "    1. cd $(pwd)"
    echo "    2. python3 verify.py    # 再跑一遍确认"
    echo "    3. python3 scripts/cut.py --help    # 看看能用啥"
    echo
    echo "  详细文档:README.md / docs/GETTING_STARTED.md"
    echo "============================================================"
else
    echo
    echo "[WARN] verify.py 有失败项,但安装已完成。看上面输出排查。"
    exit 0
fi
