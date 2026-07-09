# -*- coding: utf-8 -*-
"""
智剪工坊 · batch 子技能
批量处理(剪映一辈子也做不完的事,代码 5 分钟搞定)

用法:
  # 批量剪切(所有视频保留前 30 秒)
  python batch.py --input videos/ --output out/ --task trim --duration 30

  # 批量加转场 / 封面 / 转码
  python batch.py --input videos/ --output out/ --task fadeout --duration 3
  python batch.py --input videos/ --output out/ --task cover --cover cover.jpg --duration 3
  python batch.py --input videos/ --output out/ --task convert --resolution 1280x720


📖 SKILL.md §14 索引 → REQUIRED: read references/10-batch.md
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    ensure_dir, log_info, log_warn, log_error, log_section, log_progress, safe_run,
    find_files, safe_batch, setup_logging, SkillError,
)


def batch_trim(input_dir, output_dir, duration=30, pattern="*.mp4"):
    def process(video):
        output = Path(output_dir) / video.name
        if output.exists():
            log_warn(f"跳过(已存在): {video.name}")
            return
        run_ffmpeg([
            "-i", str(video), "-t", str(duration),
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            str(output),
        ])
    log_section(f"批量剪切({duration}s)")
    ensure_dir(output_dir)
    videos = find_files(input_dir, [pattern])
    log_info(f"找到 {len(videos)} 个视频")
    s, f = safe_batch(videos, process, "剪切")
    log_info(f"完成:成功 {s},失败 {f}")


def batch_fadeout(input_dir, output_dir, duration=3, pattern="*.mp4"):
    def process(video):
        output = Path(output_dir) / video.name
        if output.exists():
            log_warn(f"跳过(已存在): {video.name}")
            return
        vid_dur = get_duration(video)
        run_ffmpeg([
            "-i", str(video),
            "-vf", f"fade=t=out:st={vid_dur - duration}:d={duration}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            "-af", f"afade=t=out:st={vid_dur - duration}:d={duration}",
            str(output),
        ])
    log_section(f"批量淡出({duration}s)")
    ensure_dir(output_dir)
    videos = find_files(input_dir, [pattern])
    log_info(f"找到 {len(videos)} 个视频")
    s, f = safe_batch(videos, process, "淡出")
    log_info(f"完成:成功 {s},失败 {f}")


def batch_cover(input_dir, output_dir, cover_path, duration=3, pattern="*.mp4"):
    def process(video):
        output = Path(output_dir) / video.name
        if output.exists():
            log_warn(f"跳过(已存在): {video.name}")
            return
        run_ffmpeg([
            "-loop", "1", "-t", str(duration), "-i", str(cover_path),
            "-i", str(video),
            "-filter_complex",
            "[0:v]scale=1080:1920[s];[1:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black[m];[s][m]concat=n=2:v=1:a=0[v];"
            "[0:a][1:a]concat=n=2:v=0:a=1[a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            str(output),
        ])
    log_section(f"批量加封面({duration}s,{Path(cover_path).name})")
    ensure_dir(output_dir)
    videos = find_files(input_dir, [pattern])
    log_info(f"找到 {len(videos)} 个视频")
    s, f = safe_batch(videos, process, "加封面")
    log_info(f"完成:成功 {s},失败 {f}")


def batch_convert(input_dir, output_dir, resolution="1280x720", pattern="*.mp4"):
    def process(video):
        output = Path(output_dir) / (video.stem + f"_{resolution}.mp4")
        if output.exists():
            log_warn(f"跳过(已存在): {output.name}")
            return
        run_ffmpeg([
            "-i", str(video), "-vf", f"scale={resolution}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            str(output),
        ])
    log_section(f"批量转码 {resolution}")
    ensure_dir(output_dir)
    videos = find_files(input_dir, [pattern])
    log_info(f"找到 {len(videos)} 个视频")
    s, f = safe_batch(videos, process, "转码")
    log_info(f"完成:成功 {s},失败 {f}")


def batch_lut(input_dir, output_dir, lut_path, pattern="*.mp4"):
    def process(video):
        output = Path(output_dir) / video.name
        if output.exists():
            log_warn(f"跳过(已存在): {video.name}")
            return
        run_ffmpeg([
            "-i", str(video), "-vf", f"lut3d=file={lut_path}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "copy", str(output),
        ])
    log_section(f"批量 LUT: {Path(lut_path).name}")
    ensure_dir(output_dir)
    videos = find_files(input_dir, [pattern])
    log_info(f"找到 {len(videos)} 个视频")
    s, f = safe_batch(videos, process, "LUT")
    log_info(f"完成:成功 {s},失败 {f}")


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 批量处理(进度条 + 失败继续)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-i", "--input", required=True, help="输入视频目录")
    parser.add_argument("-o", "--output", required=True, help="输出目录")
    parser.add_argument("--task", required=True, choices=["trim", "fadeout", "cover", "convert", "lut"])
    parser.add_argument("--duration", type=float, help="时长秒(trim/fadeout/cover)")
    parser.add_argument("--cover", help="封面图(cover)")
    parser.add_argument("--resolution", default="1280x720", help="分辨率(convert)")
    parser.add_argument("--lut", help="LUT 路径(lut)")
    parser.add_argument("--pattern", default="*.mp4")
    parser.add_argument("--verbose", action="store_true", help="显示 debug 日志")
    args = parser.parse_args()

    setup_logging(verbose=args.verbose)

    try:
        if args.task == "trim":
            if not args.duration:
                raise SkillError("trim 需要 --duration")
            batch_trim(args.input, args.output, args.duration, args.pattern)
        elif args.task == "fadeout":
            if not args.duration:
                raise SkillError("fadeout 需要 --duration")
            batch_fadeout(args.input, args.output, args.duration, args.pattern)
        elif args.task == "cover":
            if not args.cover:
                raise SkillError("cover 需要 --cover")
            batch_cover(args.input, args.output, args.cover, args.duration or 3, args.pattern)
        elif args.task == "convert":
            batch_convert(args.input, args.output, args.resolution, args.pattern)
        elif args.task == "lut":
            if not args.lut:
                raise SkillError("lut 需要 --lut")
            batch_lut(args.input, args.output, args.lut, args.pattern)
    except SkillError as e:
        log_error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    safe_run(main)()
