# -*- coding: utf-8 -*-
"""
智剪工坊 · pipeline_vlog 子技能
7 步 vlog 流水线(从零散素材到发布版)

用法:
  # 完整流水线
  python pipeline_vlog.py run --input videos/ --output day1/ --theme "Day 1"

  # 分步调用
  python pipeline_vlog.py step1 --input 4k.mp4 --output 1080p.mp4
  python pipeline_vlog.py step2 --input videos/ --output subtitles/
  python pipeline_vlog.py step3 --input videos/ --output frames/
  python pipeline_vlog.py step6 --input clips/ --concat-list list.txt --output joined.mp4 --bgm bgm.mp3
  python pipeline_vlog.py step7 --prompt "..." --text "184" --output cover.jpg
"""
import argparse
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS, unified_vf,
    ensure_dir, log_info, log_warn, log_error, log_section, safe_run,
)


# ============================================================
# Step 1: 4K → 1080p 降分辨率
# ============================================================
def step1_downscale(input_path, output_path, fps=30):
    log_section(f"Step 1: 降分辨率 {Path(input_path).name}")
    run_ffmpeg([
        "-i", str(input_path),
        "-vf", unified_vf("1080:1920", fps),
        *DEFAULT_ENCODE_ARGS,
        str(output_path),
    ])
    log_info(f"输出: {output_path}")


# ============================================================
# Step 2: Whisper GPU 转录(复用 faster-whisper)
# ============================================================
def step2_transcribe(input_dir, output_dir, model="medium", device="cuda"):
    log_section(f"Step 2: Whisper GPU 转录")
    ensure_dir(output_dir)
    input_dir = Path(input_dir)
    videos = sorted(input_dir.glob("*.mp4")) + sorted(input_dir.glob("*.mov"))
    log_info(f"找到 {len(videos)} 个视频")

    for video in videos:
        srt_out = Path(output_dir) / (video.stem + ".srt")
        log_info(f"转录: {video.name}")
        cmd = [
            "faster-whisper", str(video),
            "--model", model,
            "--device", device,
            "--output_dir", str(output_dir),
            "--output_format", "srt",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if result.returncode != 0:
            log_warn(f"转录失败: {video.name}")
            continue
        log_info(f"  → {srt_out.name}")


# ============================================================
# Step 3: 抽关键帧
# ============================================================
def step3_extract_frames(input_dir, output_dir, interval=15):
    log_section(f"Step 3: 抽关键帧(每 {interval}s 一帧)")
    ensure_dir(output_dir)
    videos = sorted(Path(input_dir).glob("*.mp4"))

    for video in videos:
        video_out_dir = Path(output_dir) / video.stem
        ensure_dir(video_out_dir)
        log_info(f"抽帧: {video.name}")
        run_ffmpeg([
            "-i", str(video),
            "-vf", f"fps=1/{interval}",
            "-q:v", "2",
            str(video_out_dir / "frame_%03d.jpg"),
        ])


# ============================================================
# Step 6: 拼接 + 烧字幕 + BGM 混合
# ============================================================
def step6_assemble(concat_list, subtitle_srt, output_path, bgm_path=None, bgm_volume=0.18):
    log_section(f"Step 6: 拼接 + 烧字幕 + BGM")
    srt_escaped = str(subtitle_srt).replace("\\", "/").replace(":", r"\:")

    if bgm_path and Path(bgm_path).exists():
        # 有 BGM
        filter_complex = (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,setsar=1,"
            f"subtitles='{srt_escaped}':"
            "force_style='FontName=Microsoft YaHei,FontSize=22,PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,Outline=2,Shadow=1,MarginV=30'[v];"
            f"[0:a]volume=1.0[a0];"
            f"[1:a]volume={bgm_volume},aloop=loop=-1:size=2e9[a1];"
            f"[a0][a1]amix=inputs=2:duration=first:dropout_transition=0[a]"
        )
        inputs = ["-i", str(concat_list).replace("concat:", ""), "-stream_loop", "-1", "-i", str(bgm_path)]
        # 用 concat demuxer 需要 -f concat -safe 0
        inputs = ["-f", "concat", "-safe", "0", "-i", str(concat_list), "-stream_loop", "-1", "-i", str(bgm_path)]
    else:
        # 无 BGM
        filter_complex = (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,setsar=1,"
            f"subtitles='{srt_escaped}':"
            "force_style='FontName=Microsoft YaHei,FontSize=22,PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,Outline=2,Shadow=1,MarginV=30'[v];"
            "[0:a]anull[a]"
        )
        inputs = ["-f", "concat", "-safe", "0", "-i", str(concat_list)]

    # 修正:上面 inputs 重复了,重新组织
    if bgm_path and Path(bgm_path).exists():
        inputs = ["-f", "concat", "-safe", "0", "-i", str(concat_list), "-stream_loop", "-1", "-i", str(bgm_path)]
    else:
        inputs = ["-f", "concat", "-safe", "0", "-i", str(concat_list)]

    run_ffmpeg(inputs + [
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "[a]",
        *DEFAULT_ENCODE_ARGS,
        str(output_path),
    ])
    log_info(f"输出: {output_path} ({get_duration(output_path):.1f}s)")


# ============================================================
# Step 7: 抽封面 + AI 生图(委托 cover_ai.py)
# ============================================================
def step7_cover(prompt, output_jpg, title=None, subtitle=None):
    log_section(f"Step 7: AI 封面")
    cover_script = Path(__file__).parent / "cover_ai.py"
    cmd = ["python", str(cover_script), "--prompt", prompt, "--out", str(output_jpg)]
    if title:
        cmd += ["--title-main", title]
    if subtitle:
        cmd += ["--subtitle", subtitle]
    subprocess.run(cmd)


# ============================================================
# 完整 7 步流水线
# ============================================================
def run_full_pipeline(input_dir, output_dir, theme, bgm_path=None, subtitle_srt=None, concat_list=None):
    log_section(f"完整 vlog 流水线: {input_dir} → {output_dir}")
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    ensure_dir(output_dir)

    sub_dir = output_dir / "_subtitles"
    frames_dir = output_dir / "_frames"
    raw_dir = output_dir / "_raw"
    ensure_dir(sub_dir)
    ensure_dir(frames_dir)
    ensure_dir(raw_dir)

    # Step 1: 4K → 1080p(若需要,这里简化跳过,假设素材已 1080p)
    log_progress(1, 7, "Step 1 降分辨率")
    log_info("Step 1: 跳过(假设输入已是 1080p 或更低)")

    # Step 2: 转录
    log_progress(2, 7, "Step 2 Whisper 转录")
    step2_transcribe(input_dir, sub_dir)

    # Step 3: 抽帧
    log_progress(3, 7, "Step 3 抽帧")
    step3_extract_frames(input_dir, frames_dir)

    # Step 4-5: AI 分析 + 用户勾选(本脚本不实现,提示用户做)
    log_progress(4, 7, "Step 4-5 AI 分析 + 勾选")
    log_info("Step 4-5: AI 分析 + 用户勾选 - 请人工完成")

    # Step 6: 拼接(需要用户给 concat_list)
    log_progress(5, 7, "Step 6 拼接")
    if concat_list and Path(concat_list).exists() and subtitle_srt and Path(subtitle_srt).exists():
        final = output_dir / f"{theme}_vlog.mp4"
        step6_assemble(concat_list, subtitle_srt, final, bgm_path)
    else:
        log_warn("Step 6: 跳过(需要 --concat-list 和 --subtitle-srt)")

    # Step 7: 封面
    log_progress(6, 7, "Step 7 封面")
    cover_jpg = output_dir / f"{theme}_cover.jpg"
    step7_cover(
        prompt=f"{theme} vlog cover, cinematic dramatic lighting, dark background, motivational atmosphere, NO TEXT",
        output_jpg=cover_jpg,
        title=theme,
        subtitle="Day 1",
    )
    log_progress(7, 7, "完成")


# ============================================================
# CLI
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="智剪工坊 · 7 步 vlog 流水线")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # 完整流水线
    p_run = sub.add_parser("run", help="跑完整 7 步流水线")
    p_run.add_argument("--input", required=True, help="输入视频目录")
    p_run.add_argument("--output", required=True, help="输出目录")
    p_run.add_argument("--theme", required=True, help="视频主题(如 'Day 1')")
    p_run.add_argument("--bgm", help="BGM 文件(可选)")
    p_run.add_argument("--concat-list", help="剪切后的 concat 列表 txt(给 Step 6)")
    p_run.add_argument("--subtitle-srt", help="成片 SRT 字幕(给 Step 6)")

    # 分步
    p_s1 = sub.add_parser("step1", help="Step 1: 4K → 1080p")
    p_s1.add_argument("--input", required=True)
    p_s1.add_argument("--output", required=True)
    p_s1.add_argument("--fps", type=int, default=30)

    p_s2 = sub.add_parser("step2", help="Step 2: Whisper 转录")
    p_s2.add_argument("--input", required=True, help="视频目录")
    p_s2.add_argument("--output", required=True, help="SRT 输出目录")

    p_s3 = sub.add_parser("step3", help="Step 3: 抽关键帧")
    p_s3.add_argument("--input", required=True)
    p_s3.add_argument("--output", required=True)
    p_s3.add_argument("--interval", type=int, default=15)

    p_s6 = sub.add_parser("step6", help="Step 6: 拼接 + 烧字幕 + BGM")
    p_s6.add_argument("--concat-list", required=True, help="concat_list.txt")
    p_s6.add_argument("--subtitle-srt", required=True)
    p_s6.add_argument("--output", required=True)
    p_s6.add_argument("--bgm", help="BGM 文件")
    p_s6.add_argument("--bgm-volume", type=float, default=0.18)

    p_s7 = sub.add_parser("step7", help="Step 7: AI 封面")
    p_s7.add_argument("--prompt", required=True)
    p_s7.add_argument("--output", required=True)
    p_s7.add_argument("--title", help="主标题")
    p_s7.add_argument("--subtitle", help="副标题")

    args = parser.parse_args()

    if args.cmd == "run":
        run_full_pipeline(args.input, args.output, args.theme, args.bgm, args.subtitle_srt, args.concat_list)
    elif args.cmd == "step1":
        step1_downscale(args.input, args.output, args.fps)
    elif args.cmd == "step2":
        step2_transcribe(args.input, args.output)
    elif args.cmd == "step3":
        step3_extract_frames(args.input, args.output, args.interval)
    elif args.cmd == "step6":
        step6_assemble(args.concat_list, args.subtitle_srt, args.output, args.bgm, args.bgm_volume)
    elif args.cmd == "step7":
        step7_cover(args.prompt, args.output, args.title, args.subtitle)


if __name__ == "__main__":
    safe_run(main)()
