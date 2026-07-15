# -*- coding: utf-8 -*-
"""
智剪工坊 · video_fade 子技能
单视频淡入淡出（fade filter,对应 智剪工坊-意图编辑.html fade-in/fade-out op）

用法:
  python video_fade.py --in clip.mp4 --fade-in 1 --fade-out 1 --output clip_faded.mp4
  python video_fade.py --in clip.mp4 --fade-in 2 --output clip_faded.mp4
  python video_fade.py --in clip.mp4 --fade-out 2 --output clip_faded.mp4

意图层 op: videos[].ops.fade-in / videos[].ops.fade-out
底层: ffmpeg fade + afade filter 链

注意: 流水线内(step2_process.py)走 processing.py build_video_filter 链式组装;
本脚本供 AI 在流水线外手动调用(如用户临时想要某段视频淡入淡出)。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    ensure_dir, log_info, log_warn, log_error, log_section, safe_run, ParamError,
)


def video_fade(in_path, fade_in=0, fade_out=0, output=None):
    """单视频淡入淡出。

    Args:
        in_path: 输入视频
        fade_in: 淡入秒数(0=不淡入)
        fade_out: 淡出秒数(0=不淡出)
        output: 输出视频

    Returns:
        output 路径(成功);None(失败)
    """
    log_section(f"video_fade: {Path(in_path).name} in={fade_in}s out={fade_out}s")

    if fade_in < 0 or fade_out < 0:
        log_error("fade-in / fade-out 秒数必须 >= 0")
        return None
    if fade_in == 0 and fade_out == 0:
        log_warn("fade-in 和 fade-out 都是 0,直接复制原视频")
        import shutil
        shutil.copy2(in_path, output)
        return str(output)

    duration = get_duration(in_path)
    if duration is None:
        log_error(f"无法获取 {in_path} 时长")
        return None

    v_filters = []
    a_filters = []

    if fade_in > 0:
        if fade_in > duration:
            log_warn(f"fade-in {fade_in}s 超过视频时长 {duration:.2f}s,自动 clamp 到 {duration/2:.2f}s")
            fade_in = duration / 2
        v_filters.append(f"fade=t=in:st=0:d={fade_in}")
        a_filters.append(f"afade=t=in:st=0:d={fade_in}")

    if fade_out > 0:
        if fade_out > duration:
            log_warn(f"fade-out {fade_out}s 超过视频时长 {duration:.2f}s,自动 clamp 到 {duration/2:.2f}s")
            fade_out = duration / 2
        fade_out_start = max(0, duration - fade_out)
        v_filters.append(f"fade=t=out:st={fade_out_start}:d={fade_out}")
        a_filters.append(f"afade=t=out:st={fade_out_start}:d={fade_out}")

    ensure_dir(Path(output).parent)

    v_chain = ",".join(v_filters)
    a_chain = ",".join(a_filters)

    fc = f"[0:v]{v_chain}[v];[0:a]{a_chain}[a]"

    run_ffmpeg([
        "-i", str(in_path),
        "-filter_complex", fc,
        "-map", "[v]",
        "-map", "[a]",
        *DEFAULT_ENCODE_ARGS,
        str(output),
    ])
    log_info(f"输出: {output} ({get_duration(output):.1f}s)")
    return str(output)


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 单视频淡入淡出",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
意图层 op: videos[].ops.fade-in / videos[].ops.fade-out
参数语义: { on: bool, sec: 数字(秒) }

示例:
  %(prog)s --in clip.mp4 --fade-in 1 --fade-out 1 --output out.mp4
  %(prog)s --in clip.mp4 --fade-in 2 --output out.mp4
  %(prog)s --in clip.mp4 --fade-out 2 --output out.mp4
        """,
    )
    parser.add_argument("--in", dest="in_path", required=True, help="输入视频")
    parser.add_argument("--fade-in", type=float, default=0, help="淡入秒数(0=不淡入)")
    parser.add_argument("--fade-out", type=float, default=0, help="淡出秒数(0=不淡出)")
    parser.add_argument("--output", dest="output", required=True, help="输出视频")
    args = parser.parse_args()

    result = video_fade(args.in_path, args.fade_in, args.fade_out, args.output)
    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    safe_run(main)()