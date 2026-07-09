# -*- coding: utf-8 -*-
"""
智剪工坊 · lib/demucs 底层库

Demucs（Meta 开源声源分离）封装:
  - separate_vocals      主入口：分离人声（最常用）
  - separate_full        完整分离（vocals + drums + bass + other）

调用示例:
    from lib.demucs import separate_vocals
    vocals_path = separate_vocals("audio.wav", "output_dir/")

依赖: demucs (pip install demucs)
"""
import shutil
import subprocess
import sys
from pathlib import Path

_LIB_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))  # lib/ 在 path（找 common）
from common import get_duration, log_info, log_warn, log_error, log_section, ensure_dir  # noqa: E402


# 默认模型（精度 + 速度平衡）
DEFAULT_MODEL = "htdemucs"


def check_demucs():
    """检查 demucs 是否安装。

    Returns:
        bool: True=已安装, False=未安装

    只检查 Python 模块（统一标准），不查命令行。
    """
    try:
        import demucs  # noqa: F401
        return True
    except ImportError:
        return False


def separate_vocals(input_path, output_dir, model=DEFAULT_MODEL):
    """Demucs 分离人声（最常用）。

    Args:
        input_path: 输入音频/视频
        output_dir: 输出目录
        model: 模型（htdemucs / htdemucs_ft / mdx_extra / ...）

    Returns:
        str: vocals.wav 路径（成功）/ None（失败）
    """
    log_section(f"Demucs 分离人声: {Path(input_path).name} (model={model})")
    ensure_dir(output_dir)

    if not check_demucs():
        log_error("demucs 未安装")
        log_error("安装: pip install demucs")
        return None

    input_stem = Path(input_path).stem
    cmd = [
        sys.executable, "-m", "demucs",
        "--out", str(output_dir),
        "--model", model,
        "--two-stems", "vocals",  # ⭐ 只输出 vocals，节省一半空间
        str(input_path),
    ]
    log_info(f"运行: demucs --two-stems vocals --model {model}")

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="ignore", timeout=600,
        )
    except subprocess.TimeoutExpired:
        log_error("Demucs 超时（>10 分钟）")
        return None

    if result.returncode != 0:
        log_error(f"Demucs 失败: {result.stderr[-500:]}")
        return None

    # --two-stems vocals 输出结构:
    #   <output_dir>/<model>/<input_stem>/vocals.wav
    vocals_path = Path(output_dir) / model / input_stem / "vocals.wav"
    if not vocals_path.exists():
        log_error(f"Demucs 未生成 vocals: {vocals_path}")
        return None

    log_info(f"人声: {vocals_path}")
    return str(vocals_path)


def separate_full(input_path, output_dir, model=DEFAULT_MODEL):
    """Demucs 完整分离（vocals + drums + bass + other）。

    Args:
        input_path: 输入音频/视频
        output_dir: 输出目录
        model: 模型名

    Returns:
        dict: {stem_name: path}（成功）/ None（失败）
    """
    log_section(f"Demucs 完整分离: {Path(input_path).name} (model={model})")
    ensure_dir(output_dir)

    if not check_demucs():
        log_error("demucs 未安装")
        log_error("安装: pip install demucs")
        return None

    input_stem = Path(input_path).stem
    cmd = [
        sys.executable, "-m", "demucs",
        "--out", str(output_dir),
        "--model", model,
        str(input_path),
    ]
    log_info(f"运行: demucs --model {model}")

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="ignore", timeout=600,
        )
    except subprocess.TimeoutExpired:
        log_error("Demucs 超时")
        return None

    if result.returncode != 0:
        log_error(f"Demucs 失败: {result.stderr[-500:]}")
        return None

    sep_dir = Path(output_dir) / model / input_stem
    if not sep_dir.exists():
        log_error(f"Demucs 未生成目录: {sep_dir}")
        return None

    stems = {
        "vocals": sep_dir / "vocals.wav",
        "drums": sep_dir / "drums.wav",
        "bass": sep_dir / "bass.wav",
        "other": sep_dir / "other.wav",
    }

    found = {}
    for name, path in stems.items():
        if path.exists():
            found[name] = str(path)
            log_info(f"  ✓ {name}: {path.name}")
        else:
            log_warn(f"  ✗ {name}: 未生成")

    if not found:
        return None
    return found