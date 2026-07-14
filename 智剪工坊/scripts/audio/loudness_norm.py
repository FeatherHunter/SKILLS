# -*- coding: utf-8 -*-
"""
智剪工坊 · audio/loudness_norm 子技能（v1.5 新增）

用 ffmpeg loudnorm 把音频统一到 EBU R128 标准响度。
适合 podcast / 流媒体 / 跨平台播放。

链路位置: L4 → L6 之间（保证 ASR 输入音量稳定）

用法:
  # 默认 EBU R128 标准 (-23 LUFS)
  python scripts/audio/loudness_norm.py -i audio.wav -o normalized.wav

  # 自定义目标响度（流媒体常用 -16 LUFS）
  python scripts/audio/loudness_norm.py -i audio.wav -o out.wav --target -16

  # 处理视频（先提取音频，归一后再合并）
  python scripts/audio/loudness_norm.py -i video.mp4 -o video_normalized.mp4
"""
import argparse
import sys
from pathlib import Path

# 设置 sys.path：保证 SKILL_ROOT 和 lib 都在 path（但 append，不覆盖）
_SKILL_ROOT = Path(__file__).parent.parent.parent  # SKILL_ROOT/
_LIB_DIR = _SKILL_ROOT / "lib"

# 用 append（不会覆盖），并且只在路径里不存在时才加入
def _ensure_in_path(p):
    p = str(p)
    if p not in sys.path:
        sys.path.append(p)

_ensure_in_path(str(_SKILL_ROOT))
_ensure_in_path(str(_LIB_DIR))

from common import (
    run_ffmpeg, get_duration, ensure_dir,
    log_info, log_section, log_error, safe_run,
)
from ffmpeg.audio.normalize import normalize_loudnorm
from ffmpeg.audio.extract import extract_audio


def normalize(input_path, output_path, target_lufs=-23, true_peak=-2, lra=7):
    """归一化音频响度。

    Args:
        input_path: 输入音频/视频
        output_path: 输出
        target_lufs: 目标响度 LUFS（默认 -23，EBU R128 标准）
        true_peak: 真峰值上限 dBTP（默认 -2）
        lra: 响度范围 LRA（默认 7）
    Returns:
        output_path (成功) / None (失败)
    """
    log_section(f"响度归一: {Path(input_path).name} → {Path(output_path).name}")
    log_info(f"目标: {target_lufs} LUFS, peak {true_peak} dBTP, LRA {lra}")
    ensure_dir(Path(output_path).parent)

    # 判断输入是视频还是音频
    video_exts = {'.mp4', '.mov', '.mkv', '.avi', '.flv', '.webm', '.wmv'}
    is_video = Path(input_path).suffix.lower() in video_exts

    if is_video:
        # 视频处理：提取音频 → 归一（输出 wav） → 替换音频回视频
        # 注意：lib.normalize_loudnorm 强制输出 wav 格式，所以中间文件必须是 wav
        import tempfile
        tmp_extracted = Path(tempfile.gettempdir()) / f"loudnorm_ext_{Path(input_path).stem}.wav"
        tmp_normalized = Path(tempfile.gettempdir()) / f"loudnorm_norm_{Path(input_path).stem}.wav"
        try:
            log_info("步骤 1/3: 提取音频")
            success, _ = extract_audio(str(input_path), str(tmp_extracted), fmt="wav")
            if not success:
                log_error("音频提取失败")
                return None

            log_info("步骤 2/3: 响度归一")
            success, out = normalize_loudnorm(str(tmp_extracted), str(tmp_normalized),
                                              target_lufs=target_lufs,
                                              true_peak=true_peak, lra=lra)
            if not success:
                log_error("响度归一失败")
                return None

            log_info("步骤 3/3: 替换视频音轨")
            # 用归一后的 wav 音频替换原视频的音轨
            final_output = str(output_path) + ".tmp.mp4"
            run_ffmpeg([
                "-i", str(input_path),
                "-i", str(out),
                "-map", "0:v",
                "-map", "1:a",
                "-c:v", "copy",  # 视频流直接复制
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                "-y", final_output,
            ])
            Path(final_output).replace(output_path)
            log_info(f"输出: {output_path}")
            return str(output_path)
        finally:
            # 清理所有临时文件
            for tmp in (tmp_extracted, tmp_normalized):
                try:
                    tmp.unlink()
                except Exception:
                    pass
    else:
        # 音频处理：直接归一
        success, out = normalize_loudnorm(input_path, output_path,
                                          target_lufs=target_lufs,
                                          true_peak=true_peak, lra=lra)
        if success:
            log_info(f"输出: {out}")
            return out
        log_error("响度归一失败")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 响度归一（EBU R128 标准）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""EBU R128 响度标准:
  -23 LUFS  广播标准（Europe/UK）
  -16 LUFS  流媒体（Spotify/Apple Music 推荐）
  -14 LUFS  YouTube
  -20 LUFS  播客常用

真峰值 (true-peak):
  -1 dBTP   严格（高响度音乐）
  -2 dBTP   标准（默认）
  -3 dBTP   保守（避免削波）

示例:
  %(prog)s -i audio.wav -o normalized.wav
  %(prog)s -i audio.wav -o out.wav --target -16
  %(prog)s -i podcast.mp3 -o podcast_loud.mp3 --target -20
        """,
    )
    parser.add_argument("-i", "--input", required=True, help="输入音频/视频")
    parser.add_argument("-o", "--output", required=True, help="输出文件")
    parser.add_argument("--target", type=float, default=-23,
                        help="目标响度 LUFS（默认 -23，EBU R128）")
    parser.add_argument("--true-peak", type=float, default=-2,
                        help="真峰值上限 dBTP（默认 -2）")
    parser.add_argument("--lra", type=float, default=7,
                        help="响度范围 LRA（默认 7）")
    args = parser.parse_args()

    result = normalize(args.input, args.output, args.target, args.true_peak, args.lra)
    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    safe_run(main)()