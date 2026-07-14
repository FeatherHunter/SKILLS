# -*- coding: utf-8 -*-
"""
智剪工坊 · cut 子技能
剪切 / 拼接视频,统一 1080x1920 竖屏 + 30 fps + libx264 编码

用法:
  # 剪切
  python cut.py trim --input video.mp4 --ss 0 --t 30 --output clip.mp4

  # 拼接(用文件列表)
  python cut.py concat --list clips.txt --output joined.mp4


📖 SKILL.md §14 索引 → REQUIRED: read references/01-cutting.md

v1.10 新增(B2/B4 修复):
- `remux_clean_residual_metadata()`:清掉 -an 处理后残留的 audio metadata
- `concat()` 加 pre-process:自动检测并清理,防止拼接时 PTS 错乱
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

# 引入公共库
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    unified_vf, ensure_dir, require_param, validate_resolution,
    log_info, log_warn, log_error, log_section, safe_run, ParamError, SKILL_ROOT,
)


# ============================================================
# v1.10 新增:残留 metadata 检测 + 清理(B2/B4 修复)
# ============================================================

def has_residual_audio_metadata(video_path):
    """检测 mp4 是否残留 audio metadata(即使 -an 处理过)

    现象:`-c:v copy -an` 处理后的 mp4, moov atom 里 audio trak 的
    tkhd duration / sample count 等 metadata 没被清除,后续 concat 时
    ffmpeg 会按这些 metadata 推算 audio duration,导致 video 被压缩/拉长。

    v1.10 修复:用 ffprobe 检测 audio stream 的 nb_frames / nb_read_packets。
    - 有 audio packets → 真正的 audio stream,不动
    - 只有 metadata 没 packets → 残留,需要清理

    Returns:
        bool: True 表示有残留 audio metadata(需要清理), False 表示干净
    """
    try:
        # 用 ffprobe 看 audio stream 是否有 packets
        r = subprocess.run(
            ["ffprobe", "-v", "error",
             "-select_streams", "a",
             "-show_entries", "stream=nb_read_frames,codec_type",
             "-of", "csv=p=0",
             str(video_path)],
            capture_output=True, text=True, encoding="utf-8", errors="ignore",
            timeout=30,
        )
        # 如果没有任何 audio stream 行 → 没有残留
        if not r.stdout.strip():
            return False
        # 解析 "audio,1234" 这种输出,1234 是 packet 数
        for line in r.stdout.strip().split("\n"):
            parts = line.strip().split(",")
            if len(parts) >= 2 and parts[0].strip().lower() == "audio":
                try:
                    nb_packets = int(parts[1].strip() or "0")
                    if nb_packets == 0:
                        # 只有 metadata 没 packets → 残留
                        return True
                except ValueError:
                    pass
        return False
    except FileNotFoundError:
        log_warn(f"ffprobe 不在 PATH,fallback 到 ffmpeg 检测")
        # fallback: 用 ffmpeg -i 检测
        return _has_residual_audio_metadata_fallback(video_path)
    except Exception as e:
        log_warn(f"检测残留 metadata 失败({video_path}): {e}")
        return False


def _has_residual_audio_metadata_fallback(video_path):
    """ffprobe 不可用时的 fallback:用 ffmpeg -i"""
    try:
        r = subprocess.run(
            ["ffmpeg", "-i", str(video_path)],
            capture_output=True, text=True, encoding="utf-8", errors="ignore",
            timeout=30,
        )
        # 检测 audio stream 但没有 audio packet 数据 → 残留
        # ffmpeg -i 输出里如果 muted,会有 "Stream #0:1.*Audio:" 但没有 packet 计数
        audio_lines = [l for l in r.stderr.split("\n") if re.search(r"Stream\s+#\d+:\d+.*Audio:", l)]
        if not audio_lines:
            return False
        # 进一步检测是否有 audio packets(用 ffprobe -show_packets)
        try:
            r2 = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "a",
                 "-show_entries", "packet=pts", "-of", "csv=p=0",
                 str(video_path)],
                capture_output=True, text=True, timeout=30,
            )
            return not r2.stdout.strip()  # 没 packets 就是残留
        except FileNotFoundError:
            # 真没 ffprobe,fallback 看 ffmpeg 输出的 "Duration" 是不是异常大
            return False
    except Exception:
        return False


def remux_clean_residual_metadata(video_path):
    """remux mp4 强制清残留 audio metadata

    v1.10 修复:分两种情况:
    - muted video (audio stream 无 packets) → -an 完全去掉 audio,重写 moov
    - with audio video → 保留所有 stream,只重写 moov atom

    Args:
        video_path: 视频文件路径(原地修改)
    """
    video_path = Path(video_path)
    tmp = video_path.with_suffix(".clean.mp4")
    log_warn(f"清理残留 audio metadata: {video_path.name}")

    # 检测是否真的没有 audio packets
    has_real_audio = not has_residual_audio_metadata(video_path)

    if has_real_audio:
        # 视频有真实 audio,只重写 moov atom,保留所有 stream
        log_info(f"  → 检测到真实 audio stream,保留 audio,只重写 moov")
        run_ffmpeg([
            "-y", "-i", str(video_path),
            "-map", "0",            # 保留所有 stream
            "-c", "copy",
            "-map_metadata", "-1",  # 清空 metadata
            "-movflags", "+faststart",
            str(tmp),
        ])
    else:
        # muted video,残留 audio metadata,完全去掉 audio
        log_info(f"  → muted video(残留 audio metadata),-an 完全去掉")
        run_ffmpeg([
            "-y", "-i", str(video_path),
            "-map", "0:v",          # 只保留 video stream
            "-c", "copy",
            "-map_metadata", "-1",
            "-movflags", "+faststart",
            str(tmp),
        ])
    # 替换原文件
    tmp.replace(video_path)
    log_info(f"清理完成: {video_path.name}")


def _parse_concat_segments(list_file):
    """从 concat 文件列表里解析 segment 路径"""
    segments = []
    list_path = Path(list_file)
    if not list_path.exists():
        return segments
    for line in list_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("file "):
            # 格式: file 'path' 或 file "path"
            path_str = line[5:].strip().strip("'\"")
            segments.append(Path(path_str))
    return segments


def trim(input_path, ss, t, output_path, resolution="1080:1920", fps=30):
    """剪切单段视频"""
    log_section(f"剪切 {Path(input_path).name} (ss={ss}, t={t})")
    ensure_dir(Path(output_path).parent)

    run_ffmpeg([
        "-ss", str(ss),
        "-i", str(input_path),
        "-t", str(t),
        "-vf", unified_vf(resolution, fps),
        *DEFAULT_ENCODE_ARGS,
        str(output_path),
    ])
    log_info(f"输出: {output_path} ({get_duration(output_path):.1f}s)")


def _has_audio_stream(video_path):
    """检测 video 是否有真实 audio stream(用 ffmpeg -i 简单判断)"""
    try:
        r = subprocess.run(
            ["ffmpeg", "-i", str(video_path)],
            capture_output=True, text=True, encoding="utf-8", errors="ignore",
            timeout=30,
        )
        for line in r.stderr.split("\n"):
            if re.search(r"Stream\s+#\d+:\d+.*Audio:", line):
                return True
        return False
    except Exception:
        return False


def _add_silent_audio(video_path):
    """给 muted video 加 silent audio track,长度 = video 长度"""
    video_path = Path(video_path)
    tmp = video_path.with_suffix(".with_audio.mp4")
    duration = get_duration(video_path)
    if duration is None:
        log_warn(f"无法获取 {video_path.name} 时长,跳过 silent audio 添加")
        return
    run_ffmpeg([
        "-y",
        "-i", str(video_path),
        "-f", "lavfi", "-i", f"anullsrc=cl=stereo:r=44100",
        "-t", f"{duration:.3f}",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        "-movflags", "+faststart",
        str(tmp),
    ])
    tmp.replace(video_path)
    log_info(f"  → {video_path.name} 已添加 silent audio (duration={duration:.2f}s)")


def concat(list_file, output_path, resolution="1080:1920", fps=30):
    """按文件列表拼接

    v1.10 重写:从 concat demuxer 改为 filter_complex concat。

    原因:ffmpeg concat demuxer 在 inputs 音频流不一致(部分有 audio 部分
    没有,或 audio metadata 异常)时,会自动创建空 audio stream placeholder,
    导致输出时长异常(如 7811 秒)。filter_complex 拼接不会有这个问题。

    流程:
    1. pre-process: 检测残留 audio metadata 并清理
    2. pre-process: 给 muted segments 加 silent audio (兜底)
    3. filter_complex concat (用每个 input 的 [i:v] [i:a],绕开 demuxer)
    """
    log_section(f"拼接 {list_file} → {output_path}")
    ensure_dir(Path(output_path).parent)

    segments = _parse_concat_segments(list_file)

    # 第一遍:清理残留 metadata
    cleaned_count = 0
    for seg in segments:
        if not seg.exists():
            log_warn(f"segment 不存在: {seg}")
            continue
        if has_residual_audio_metadata(seg):
            remux_clean_residual_metadata(seg)
            cleaned_count += 1
    if cleaned_count:
        log_info(f"metadata 清理完成: {cleaned_count}/{len(segments)} segments")

    # 第二遍:给 muted video 加 silent audio(兜底,虽然 filter_complex 不需要)
    for seg in segments:
        if not seg.exists():
            continue
        if not _has_audio_stream(seg):
            _add_silent_audio(seg)

    # filter_complex concat(绕开 concat demuxer 的 7811s bug)
    valid_segments = [s for s in segments if s.exists()]
    n = len(valid_segments)
    if n == 0:
        log_error("没有有效的 segment,无法拼接")
        return

    filter_parts = []
    concat_inputs = []
    for i in range(n):
        # 每个 video 单独 scale + pad
        v_filter = (
            f"[{i}:v]scale={resolution}:force_original_aspect_ratio=decrease,"
            f"pad={resolution}:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps={fps}[v{i}]"
        )
        filter_parts.append(v_filter)
        # 用各 input 的真实 audio stream
        concat_inputs.append(f"[v{i}][{i}:a]")
    filter_parts.append(
        f"{''.join(concat_inputs)}concat=n={n}:v=1:a=1[outv][outa]"
    )
    filter_complex = ";".join(filter_parts)

    cmd = ["-y"]
    for seg in valid_segments:
        cmd.extend(["-i", str(seg)])
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "[outa]",
        *DEFAULT_ENCODE_ARGS,
        str(output_path),
    ])
    log_info(f"使用 filter_complex concat({n} segments)")
    run_ffmpeg(cmd)
    log_info(f"输出: {output_path} ({get_duration(output_path):.1f}s)")


def _parse_time(s: str) -> float:
    """解析时间字符串: '5' / '1:30' / '00:01:30' → 秒"""
    s = s.strip()
    if ":" in s:
        parts = s.split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        raise ParamError(f"时间格式错误: {s}")
    return float(s)


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 视频剪切/拼接",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s trim --input in.mp4 --ss 0 --t 30 --out clip.mp4
  %(prog)s concat --list clips.txt --out joined.mp4

v1.10 新增: concat 自动检测并清理 muted video 残留 audio metadata,
            防止拼接时 PTS 错乱(详见 SKILL.md ⚠️ muted 拼接风险)。
        """,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # trim
    p_trim = sub.add_parser("trim", help="剪切单段(支持 --ss --t 或 --from --to)")
    p_trim.add_argument("-i", "--input", required=True, help="输入视频")
    p_trim.add_argument("--start", type=float, default=0, help="起始时间(秒)")
    p_trim.add_argument("--t", type=float, required=False, help="时长(秒)")
    p_trim.add_argument("--from", dest="from_", help="起始时间(M:SS 或 HH:MM:SS)")
    p_trim.add_argument("--to", help="结束时间(M:SS 或 HH:MM:SS)")
    p_trim.add_argument("-o", "--output", required=True, help="输出视频")
    p_trim.add_argument("--resolution", default="1080:1920", help="输出分辨率")
    p_trim.add_argument("--fps", type=int, default=30, help="帧率")

    # concat
    p_concat = sub.add_parser("concat", help="拼接多段(用文件列表)")
    p_concat.add_argument("--list", required=True, help="文件列表 txt(每行 file 'path')")
    p_concat.add_argument("-o", "--output", required=True, help="输出视频")
    p_concat.add_argument("--resolution", default="1080:1920", help="输出分辨率")
    p_concat.add_argument("--fps", type=int, default=30, help="帧率")

    args = parser.parse_args()

    if args.cmd == "trim":
        # 支持 --from --to（转为 --start --t）
        from_sec = args.start
        t = args.t
        if args.from_ is not None or args.to is not None:
            from_sec = _parse_time(args.from_) if args.from_ else 0
            to_sec = _parse_time(args.to) if args.to else 0
            if to_sec <= from_sec:
                raise ParamError(f"--to ({to_sec}s) 必须 > --from ({from_sec}s)")
            t = to_sec - from_sec
        if t is None:
            raise ParamError("请提供 --t 或 --from + --to")
        trim(args.input, from_sec, t, args.output, args.resolution, args.fps)
    elif args.cmd == "concat":
        concat(args.list, args.output, args.resolution, args.fps)


if __name__ == "__main__":
    safe_run(main)()
