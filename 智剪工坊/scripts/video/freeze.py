# -*- coding: utf-8 -*-
"""
智剪工坊 · video_freeze 子技能
视频结尾定格（最后 N 秒帧定格，扩展视频时长）

用法:
  python video_freeze.py --in clip.mp4 --freeze 2 --output out.mp4
  python video_freeze.py --in clip.mp4 --freeze 3 --padding-mode black --output out.mp4

意图层 op: ending.type=freeze
底层: ffmpeg tpad=stop_mode=clone:stop_duration=N

参数:
  --freeze N         定格持续秒数（从最后一帧克隆 N 秒）
  --padding-mode     clone(克隆最后一帧, 默认) / black(黑屏)

注意: 克隆最后一帧画面静止不动 + 时长延长 N 秒;音频会被 apad 延长
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    ensure_dir, log_info, log_warn, log_error, log_section, safe_run, ParamError,
)


def video_freeze(in_path, freeze_sec=2.0, padding_mode="clone", output=None):
    """视频结尾定格。

    Args:
        in_path: 输入视频
        freeze_sec: 定格持续秒数
        padding_mode: clone(克隆最后一帧) / black(黑屏)
        output: 输出视频

    Returns:
        output 路径(成功);None(失败)
    """
    log_section(f"video_freeze: {Path(in_path).name} freeze={freeze_sec}s mode={padding_mode}")

    if freeze_sec <= 0:
        log_error("freeze 秒数必须 > 0")
        return None
    if padding_mode not in ("clone", "black"):
        log_error(f"padding-mode 必须是 clone 或 black（当前: {padding_mode}）")
        return None

    duration = get_duration(in_path)
    if duration is None:
        log_error(f"无法获取 {in_path} 时长")
        return None

    ensure_dir(Path(output).parent)

    if padding_mode == "clone":
        # 克隆最后一帧 N 秒
        cmd = [
            "-i", str(in_path),
            "-vf", f"tpad=stop_mode=clone:stop_duration={freeze_sec}",
            "-af", f"apad=whole_dur={duration + freeze_sec}",
            *DEFAULT_ENCODE_ARGS,
            str(output),
        ]
    else:  # black
        # 黑屏 N 秒（用 color 滤镜）
        # 先生成黑屏源，再 concat
        # 简化：用 tpad 配合 fillcolor
        cmd = [
            "-i", str(in_path),
            "-vf", f"tpad=stop_duration={freeze_sec}:stop_mode=add:color=black",
            "-af", f"apad=whole_dur={duration + freeze_sec}",
            *DEFAULT_ENCODE_ARGS,
            str(output),
        ]

    run_ffmpeg(cmd)
    log_info(f"输出: {output} ({get_duration(output):.1f}s)")
    return str(output)


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 视频结尾定格",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
意图层 op: ending.type=freeze
参数: { freeze_sec: 数字, padding_mode: 'clone' | 'black' }

示例:
  %(prog)s --in clip.mp4 --freeze 2 --output out.mp4           # 克隆最后一帧 2 秒
  %(prog)s --in clip.mp4 --freeze 3 --padding-mode black --output out.mp4   # 黑屏 3 秒
        """,
    )
    parser.add_argument("--in", dest="in_path", required=True, help="输入视频")
    parser.add_argument("--freeze", type=float, default=2.0,
                        help="定格持续秒数（默认 2）")
    parser.add_argument("--padding-mode", choices=["clone", "black"], default="clone",
                        help="定格模式：clone=克隆最后一帧 / black=黑屏")
    parser.add_argument("--output", dest="output", required=True, help="输出视频")
    args = parser.parse_args()

    result = video_freeze(args.in_path, args.freeze, args.padding_mode, args.output)
    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    safe_run(main)()