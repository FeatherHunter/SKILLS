# -*- coding: utf-8 -*-
"""
智剪工坊 · audio/mix 子技能（音频链路 L1: 合成）
给视频加 BGM（混音，人声不被覆盖）

来源: scripts/audio_bgm.py（v1.3，281 行）
本文件为 audio/ 链路主入口，old 路径 audio_bgm.py 保留 backward-compat。

音频链路层级:
  L1 合成   → mix（多个音频混为一个）
  L2 变换   → voice, fade, normalize
  L3 提取   → extract
  L4 分离   → denoise（降噪）, separate（声源分离）
  L5 说话人 → diarize（说话人分离，依赖 L4）
  L6 分析   → asr/transcribe（L5 输出做 ASR）

依赖: ffmpeg
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    ensure_dir, log_info, log_warn, log_error, log_section, safe_run, ParamError,
)


# ========== v1.3 常量 ==========
MATCH_MODES = ["loop", "truncate", "silence-end", "ask"]
DEFAULT_MATCH_MODE = "loop"


def add_bgm(
    video, bgm, output,
    video_volume=1.0,
    bgm_volume=0.18,
    bgm_fade_in=0,
    bgm_fade_out=0,
    start=0,
    end=None,
    match_mode=DEFAULT_MATCH_MODE,
):
    """给视频加 BGM，支持时间段 + 4 种时长不匹配处理。

    Args:
        video: 输入视频
        bgm: BGM 音频文件
        output: 输出视频
        video_volume: 原声音量（默认 1.0）
        bgm_volume: BGM 音量（默认 0.18）
        bgm_fade_in: BGM 起始淡入秒数（默认 0）
        bgm_fade_out: BGM 结束淡出秒数（默认 0）
        start: BGM 在视频的起始时间（秒，默认 0）
        end: BGM 在视频的结束时间（秒，None=视频结尾）
        match_mode: 时长不匹配处理
            - loop: 短 BGM 循环；长 BGM 截短（默认，向 v1.2 兼容）
            - truncate: BGM 截到视频长
            - silence-end: BGM 播完就静
            - ask: AI 必须先问用户

    Returns:
        output 路径（成功）；None（失败 / ask 模式需用户决定）
    """
    log_section(f"加 BGM: {Path(bgm).name} → {Path(video).name} (mode={match_mode})")

    # 参数验证
    if match_mode not in MATCH_MODES:
        log_error(f"match-mode 必须是 {MATCH_MODES} 之一（当前: {match_mode}）")
        return None
    if not (0 <= video_volume <= 2):
        log_error(f"video-volume 必须在 [0, 2]（当前: {video_volume}）")
        return None
    if not (0 <= bgm_volume <= 2):
        log_error(f"bgm-volume 必须在 [0, 2]（当前: {bgm_volume}）")
        return None
    if bgm_fade_in < 0 or bgm_fade_out < 0:
        log_error(f"bgm-fade-in/fade-out 必须 >= 0（当前: in={bgm_fade_in}, out={bgm_fade_out}）")
        return None
    if start < 0:
        log_error(f"start 必须 >= 0（当前: {start}）")
        return None
    if end is not None and end <= start:
        log_error(f"end 必须 > start（当前: start={start}, end={end}）")
        return None

    video_dur = get_duration(video)
    bgm_dur = get_duration(bgm)
    if video_dur is None or bgm_dur is None:
        log_error(f"无法获取视频或 BGM 时长（video={video_dur}, bgm={bgm_dur}）")
        return None

    if end is None:
        end = video_dur
        log_info(f"end 未指定，使用视频结尾: {end:.1f}s")
    if end > video_dur:
        log_error(f"end ({end:.1f}s) 超过视频时长 ({video_dur:.1f}s)")
        return None

    bgm_segment_dur = end - start
    if bgm_segment_dur <= 0:
        log_error(f"BGM 段时长 <= 0（{start:.1f}s 到 {end:.1f}s）")
        return None
    if bgm_fade_in + bgm_fade_out > bgm_segment_dur:
        log_error(f"fade-in + fade-out 超过 BGM 段时长 ({bgm_segment_dur}s)")
        return None

    log_info(f"视频: {video_dur:.1f}s, BGM: {bgm_dur:.1f}s, BGM 段: [{start:.1f}s, {end:.1f}s]")
    log_info(f"淡入: {bgm_fade_in}s, 淡出: {bgm_fade_out}s, match-mode: {match_mode}")

    if match_mode == "ask":
        log_warn("match-mode='ask': AI 必须先问用户如何处理时长不匹配")
        return None

    ensure_dir(Path(output).parent)

    # 构造 BGM filter
    if match_mode == "loop":
        if bgm_dur <= bgm_segment_dur:
            bgm_core = f"aloop=loop=-1:size=2e9:start=0,atrim=0:{bgm_segment_dur},asetpts=PTS-STARTPTS"
        else:
            bgm_core = f"atrim=0:{bgm_segment_dur},asetpts=PTS-STARTPTS"
    elif match_mode == "truncate":
        bgm_core = f"atrim=0:{min(bgm_dur, bgm_segment_dur)},asetpts=PTS-STARTPTS"
    elif match_mode == "silence-end":
        bgm_core = f"apad=whole_dur={bgm_segment_dur}"

    if bgm_fade_in > 0:
        bgm_core += f",afade=t=in:st=0:d={bgm_fade_in}"
    if bgm_fade_out > 0:
        fade_out_start = max(0, bgm_segment_dur - bgm_fade_out)
        bgm_core += f",afade=t=out:st={fade_out_start}:d={bgm_fade_out}"

    bgm_filter = f"volume={bgm_volume},{bgm_core}"
    delay_ms = int(start * 1000)
    bgm_filter_with_delay = f"{bgm_filter},adelay={delay_ms}|{delay_ms}"

    filter_complex = (
        f"[0:a]volume={video_volume}[a0];"
        f"[1:a]{bgm_filter_with_delay}[a1];"
        f"[a0][a1]amix=inputs=2:duration=first:dropout_transition=0[a]"
    )

    cmd = ["-i", str(video)]
    if match_mode == "loop" and bgm_dur < bgm_segment_dur:
        cmd.extend(["-stream_loop", "-1"])
    cmd.extend(["-i", str(bgm)])
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "0:v", "-map", "[a]",
        *DEFAULT_ENCODE_ARGS,
        str(output),
    ])

    run_ffmpeg(cmd)
    log_info(f"输出: {output} ({get_duration(output):.1f}s)")
    return str(output)


# ========== v1.2 旧 API（向后兼容）==========
def add_bgm_loop(video, bgm, output, video_volume=1.0, bgm_volume=0.18, fade_out=0):
    """v1.2 旧 API: 固定 loop 模式（短 BGM 循环）"""
    log_warn("add_bgm_loop 是 v1.2 旧 API，建议改用 add_bgm + --match-mode=loop")
    return add_bgm(video, bgm, output, video_volume, bgm_volume,
                   bgm_fade_out=fade_out, match_mode="loop")


# ========== CLI ==========
def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 给视频加 BGM（v1.3，支持时间段 + 4 种时长不匹配处理）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
参数:
  --start / --end         BGM 在视频的哪段时间播放（默认全段）
  --bgm-fade-in / -out   BGM 淡入淡出（秒）
  --match-mode            loop / truncate / silence-end / ask

示例:
  %(prog)s --input v.mp4 --bgm b.mp3 --volume 0.18 --output o.mp4
  %(prog)s --input v.mp4 --bgm b.mp3 --start 10 --end 20 --output o.mp4
  %(prog)s --input v.mp4 --bgm b.mp3 --bgm-fade-in 1 --bgm-fade-out 2 --output o.mp4
  %(prog)s --input v.mp4 --bgm b.mp3 --start 5 --end 15 --match-mode truncate --bgm-fade-out 1 --output o.mp4
        """,
    )
    parser.add_argument("--input", dest="video", required=True, help="输入视频")
    parser.add_argument("--bgm", required=True, help="BGM 文件")
    parser.add_argument("--volume", type=float, default=0.18, help="BGM 音量（0-2，默认 0.18）")
    parser.add_argument("--video-volume", type=float, default=1.0, help="原声音量（0-2，默认 1.0）")
    parser.add_argument("--start", type=float, default=0, help="BGM 起始时间（秒，默认 0）")
    parser.add_argument("--end", type=float, default=None, help="BGM 结束时间（秒，默认视频结尾）")
    parser.add_argument("--bgm-fade-in", type=float, default=0, help="BGM 起始淡入（秒）")
    parser.add_argument("--bgm-fade-out", type=float, default=0, help="BGM 结束淡出（秒）")
    parser.add_argument("--match-mode", default=DEFAULT_MATCH_MODE,
                        choices=MATCH_MODES,
                        help=f"时长不匹配处理（默认 {DEFAULT_MATCH_MODE}）")
    parser.add_argument("--output", required=True, help="输出视频")
    args = parser.parse_args()

    result = add_bgm(
        args.video, args.bgm, args.output,
        video_volume=args.video_volume,
        bgm_volume=args.volume,
        bgm_fade_in=args.bgm_fade_in,
        bgm_fade_out=args.bgm_fade_out,
        start=args.start,
        end=args.end,
        match_mode=args.match_mode,
    )
    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    safe_run(main)
