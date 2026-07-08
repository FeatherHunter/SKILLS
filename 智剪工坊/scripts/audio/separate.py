# -*- coding: utf-8 -*-
"""
智剪工坊 · audio/separate 子技能（音频链路 L4: 声源分离）
把混合音频分离成人声 / 伴奏 / 其他声音

本文件为新增文件（v1.4）。

链路位置:
  L1 合成 → L2 变换 → L3 提取 → L4 降噪/分离 ← 本文件
  → L5 说话人分离（diarize.py）→ L6 ASR

声源分离（Sound Source Separation）= 把一段混合音频拆成多个独立音轨。
典型场景：视频 BGM 大 → ASR 准确率低 → 先分离出人声再 ASR。

用法:
  # Demucs 分离（推荐，需要 demucs）
  python audio/separate.py --input audio.wav --output-dir ./separated --backend demucs

  # Demucs 输出结构:
  #   ./separated/htdemucs/audio.wav/
  #     ├── vocals.wav    （人声）
  #     ├── drums.wav     （鼓点）
  #     ├── bass.wav      （低音）
  #     └── other.wav     （其他）

  # 直接指定输出（跳过 drums/bass/other）
  python audio/separate.py --input audio.wav --output vocals.wav --stem vocals --backend demucs

依赖:
  - demucs（pip install demucs）：Meta 开源，支持 htdemucs / mdx 等模型
  - ffmpeg（必需）
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))
from common import (
    get_duration, ensure_dir,
    log_info, log_warn, log_error, log_section, safe_run, get_ffmpeg_path,
)


# 分离模式
BACKENDS = {
    "demucs": {
        "description": "Demucs（Meta 开源，支持 htdemucs / mdx_extra / mdx 等模型）",
        "model_default": "htdemucs",
        "models": ["htdemucs", "htdemucs_ft", "mdx", "mdx_extra", "mdx_extra_q", "sdx耀"],
    },
    "spleeter": {
        "description": "Spleeter（Deezer 开源，2/4/5 轨分离）",
        "models": ["2stems", "4stems", "5stems"],
    },
}

# Demucs 默认输出目录结构
DEMUCS_DEFAULT_MODEL = "htdemucs"


def separate_demucs(input_path, output_dir, model=None, stem=None):
    """用 Demucs 分离音频。

    Args:
        input_path: 输入音频/视频文件
        output_dir: Demucs 输出目录（默认在 input 同目录下）
        model: 模型名（默认 htdemucs）
        stem: 只提取某个音轨（vocals / drums / bass / other）
    Returns:
        {stem: path} dict（成功）；None（失败）
    """
    model = model or DEMUCS_DEFAULT_MODEL
    log_section(f"Demucs 分离: {Path(input_path).name} (model={model})")

    # 检查 demucs 是否安装
    demucs_bin = shutil.which("demucs") or shutil.which("demucs.bat")
    if not demucs_bin:
        log_error("demucs 未安装")
        log_error("安装: pip install demucs")
        return None

    ensure_dir(output_dir)

    # 构建命令
    cmd = [
        sys.executable, "-m", "demucs",
        "--out", str(output_dir),
        "--model", model,
        str(input_path),
    ]
    log_info(f"运行: demucs --out {output_dir} --model {model} {Path(input_path).name}")

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="ignore", timeout=600,
        )
    except subprocess.TimeoutExpired:
        log_error("Demucs 超时（超过 10 分钟）")
        return None

    if result.returncode != 0:
        log_error(f"Demucs 失败: {result.stderr[-500:]}")
        return None

    # 找输出文件
    input_stem = Path(input_path).stem
    # Demucs 按 <out_dir>/<model>/<stem>/<file>.wav 结构输出
    sep_dir = Path(output_dir) / model / input_stem
    if not sep_dir.exists():
        log_error(f"Demucs 未生成输出目录: {sep_dir}")
        return None

    stems = {
        "vocals": sep_dir / "vocals.wav",
        "drums": sep_dir / "drums.wav",
        "bass": sep_dir / "bass.wav",
        "other": sep_dir / "other.wav",
    }

    for name, path in stems.items():
        status = "✓" if path.exists() else "✗"
        log_info(f"  {status} {name}: {path.name}")

    if stem:
        if stem in stems and stems[stem].exists():
            log_info(f"返回音轨: {stem} → {stems[stem]}")
            return {stem: stems[stem]}
        else:
            log_error(f"音轨 {stem} 不存在")
            return None

    return {name: path for name, path in stems.items() if path.exists()}


def separate_spleeter(input_path, output_dir, model="4stems"):
    """用 Spleeter 分离音频（占位）。"""
    log_section(f"Spleeter 分离: {Path(input_path).name} (model={model})")
    try:
        import spleeter
    except ImportError:
        log_error("spleeter 未安装，安装: pip install spleeter")
        return None

    log_warn("Spleeter 集成待补（当前推荐用 Demucs）")
    # TODO: 实现 spleeter CLI 调用
    return None


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 声源分离（Demucs / Spleeter）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""用法示例:
  # 完整分离（输出 vocals / drums / bass / other 4 个音轨）
  %(prog)s --input audio.wav --output-dir ./separated

  # 只提取人声（跳过其他音轨）
  %(prog)s --input audio.wav --output vocals.wav --stem vocals

  # 指定模型
  %(prog)s --input audio.wav --output-dir ./separated --model htdemucs_ft

  # 4 轨分离（Spleeter）
  %(prog)s --input audio.wav --output-dir ./separated --backend spleeter --model 4stems
        """,
    )
    parser.add_argument("-i", "--input", required=True, help="输入音频/视频")
    parser.add_argument("--output", help="输出文件（--stem 指定时必填）")
    parser.add_argument("--output-dir", help="分离输出目录（默认在 input 同目录下）")
    parser.add_argument("--backend", default="demucs",
                        choices=list(BACKENDS.keys()),
                        help="分离后端（默认 demucs）")
    parser.add_argument("--model", default=None,
                        help="模型（demucs: htdemucs/mdx_extra；spleeter: 2stems/4stems）")
    parser.add_argument("--stem",
                        choices=["vocals", "drums", "bass", "other"],
                        help="只提取指定音轨（输出到 --output）")

    args = parser.parse_args()

    # 确定 output_dir
    if args.output_dir:
        output_dir = args.output_dir
    else:
        output_dir = str(Path(args.input).parent / "separated")

    # 确定 output（stem 指定时）
    output_path = args.output
    if args.stem and not output_path:
        stem_file = Path(input_path).stem + f"_{args.stem}.wav"
        output_path = str(Path(output_dir) / stem_file)

    ensure_dir(output_dir)

    if args.backend == "demucs":
        result = separate_demucs(args.input, output_dir, args.model, args.stem)
    elif args.backend == "spleeter":
        result = separate_spleeter(args.input, output_dir, args.model)

    if result is None:
        sys.exit(1)

    log_info(f"分离完成: {result}")


if __name__ == "__main__":
    safe_run(main)
