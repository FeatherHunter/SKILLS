# -*- coding: utf-8 -*-
"""
智剪工坊 · audio/mix 子技能（v1.5 迁移版本）

调用 lib/ffmpeg/audio 的混音能力（amix/adelay/apad/afade）。
本文件作为用户入口 CLI + 业务参数封装（match_mode 4 种时长处理）。

音频链路层级: L1 合成

用法:
  python audio/mix.py --input v.mp4 --bgm b.mp3 --volume 0.18 --output out.mp4
  python audio/mix.py --input v.mp4 --bgm b.mp3 --bgm-fade-in 1 --bgm-fade-out 2 --output out.mp4

依赖: lib.ffmpeg.audio.{mix_streams, adelay, apad, fade_in_out}
"""
import argparse
import sys
import tempfile
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
    """给视频加 BGM（v1.5 迁移版本：基于 lib/ffmpeg/audio 链路）。

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

    Returns:
        output 路径（成功）；None（失败 / ask 模式需用户决定）
    """
    log_section(f"加 BGM: {Path(bgm).name} → {Path(video).name} (mode={match_mode})")

    # ========== 参数验证（严格，失败不调 ffmpeg）==========
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
        log_error(f"bgm-fade-in/fade-out 必须 >= 0")
        return None
    if start < 0:
        log_error(f"start 必须 >= 0")
        return None
    if end is not None and end <= start:
        log_error(f"end 必须 > start")
        return None

    video_dur = get_duration(video)
    bgm_dur = get_duration(bgm)
    if video_dur is None or bgm_dur is None:
        log_error(f"无法获取视频或 BGM 时长")
        return None

    if end is None:
        end = video_dur
        log_info(f"end 未指定，使用视频结尾: {end:.1f}s")
    if end > video_dur:
        log_error(f"end 超过视频时长")
        return None

    bgm_segment_dur = end - start
    if bgm_segment_dur <= 0:
        log_error(f"BGM 段时长 <= 0")
        return None
    if bgm_fade_in + bgm_fade_out > bgm_segment_dur:
        log_error(f"fade-in + fade-out 超过 BGM 段时长")
        return None

    log_info(f"视频: {video_dur:.1f}s, BGM: {bgm_dur:.1f}s, BGM 段: [{start:.1f}s, {end:.1f}s]")
    log_info(f"淡入: {bgm_fade_in}s, 淡出: {bgm_fade_out}s, match-mode: {match_mode}")

    if match_mode == "ask":
        log_warn("match-mode='ask': AI 必须先问用户")
        return None

    ensure_dir(Path(output).parent)

    # ========== 调用 lib/ffmpeg/audio 链路 ==========
    # v1.5 迁移说明：
    #   - BGM 链路有 4 步（时长匹配 + 淡入淡出 + 音量 + 延迟），全用单一 filter_complex 完成
    #   - lib 里没有 1:1 对应的「BGM 链路封装」函数（业务层职责，不下沉）
    #   - 实际调 lib 的只有两步：mix_streams + extract_audio
    from ffmpeg.audio.channel import mix_streams as lib_mix
    from ffmpeg.audio.utility import adelay, apad  # noqa: 用于业务字符串拼装参考

    # 步骤 1: 处理 BGM 到目标段（filter_complex 一次性完成所有变换）
    bgm_processed = Path(tempfile.gettempdir()) / f"mix_bgm_{Path(video).stem}_{Path(bgm).stem}.wav"

    bgm_filter_parts = []

    # 1a: 时长匹配处理（核心业务逻辑：loop / truncate / silence-end）
    if match_mode == "loop":
        if bgm_dur <= bgm_segment_dur:
            bgm_filter_parts.append(f"aloop=loop=-1:size=2e9:start=0,atrim=0:{bgm_segment_dur},asetpts=PTS-STARTPTS")
        else:
            bgm_filter_parts.append(f"atrim=0:{bgm_segment_dur},asetpts=PTS-STARTPTS")
    elif match_mode == "truncate":
        bgm_filter_parts.append(f"atrim=0:{min(bgm_dur, bgm_segment_dur)},asetpts=PTS-STARTPTS")
    elif match_mode == "silence-end":
        bgm_filter_parts.append(f"apad=whole_dur={bgm_segment_dur}")  # apad in lib/ffmpeg/audio/utility.py

    # 1c: 淡入淡出
    if bgm_fade_in > 0:
        bgm_filter_parts.append(f"afade=t=in:st=0:d={bgm_fade_in}")
    if bgm_fade_out > 0:
        fade_out_start = max(0, bgm_segment_dur - bgm_fade_out)
        bgm_filter_parts.append(f"afade=t=out:st={fade_out_start}:d={bgm_fade_out}")

    # 1b: 音量
    bgm_filter_str = f"volume={bgm_volume}," + ",".join(bgm_filter_parts)

    # 1d: 延迟到 start（业务需求，不直接调 lib.adelay 因为它在 filter_complex 链中）
    delay_ms = int(start * 1000)
    if delay_ms > 0:
        bgm_filter_str += f",adelay={delay_ms}|{delay_ms}"

    # 执行 BGM 处理
    log_info(f"BGM filter: {bgm_filter_str}")

    # loop 模式需要 stream_loop
    cmd = ["-i", str(bgm)]
    if match_mode == "loop" and bgm_dur < bgm_segment_dur:
        cmd = ["-stream_loop", "-1"] + cmd

    cmd.extend([
        "-af", bgm_filter_str,
        "-c:a", "pcm_s16le",
        "-y", str(bgm_processed),
    ])

    # v1.10 重写:不再需要 video_a_processed 中间 wav,filter_complex 一次性搞定
    try:
        run_ffmpeg(cmd)  # 处理 BGM

        # 步骤 3: 混合两轨 → 输出（v1.10 重写：直接用原视频 + filter_complex，
        #         不再用 video_a_processed 中间 wav，避免 -map 0:v 在 wav 上失败的 BUG）
        cmd = [
            "-i", str(video),                 # 原视频（带 video + audio 流）
            "-i", str(bgm_processed),         # 处理后的 BGM
            "-filter_complex", (
                f"[0:a]volume={video_volume}[v0];"
                f"[1:a]volume={bgm_volume}[v1];"
                f"[v0][v1]amix=inputs=2:duration=first:dropout_transition=0[a]"
            ),
            "-map", "0:v",                    # 从原视频取 video 流
            "-map", "[a]",                    # 从 filter_complex 取混合 audio
            *DEFAULT_ENCODE_ARGS,
            "-y", str(output),
        ]
        run_ffmpeg(cmd)

        log_info(f"输出: {output} ({get_duration(output):.1f}s)")
        return str(output)
    finally:
        # 确保清理临时文件（即使中途出错）
        for tmp in (bgm_processed,):
            try:
                tmp.unlink()
            except Exception:
                pass


def add_bgm_loop(video, bgm, output, video_volume=1.0, bgm_volume=0.18, fade_out=0):
    """v1.2 旧 API：固定 loop 模式（短 BGM 循环）"""
    log_warn("add_bgm_loop 是 v1.2 旧 API，建议改用 add_bgm + --match-mode=loop")
    return add_bgm(video, bgm, output, video_volume, bgm_volume,
                   bgm_fade_out=fade_out, match_mode="loop")


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 给视频加 BGM（v1.5 调 lib/ffmpeg/audio 链路）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
参数:
  --start / --end         BGM 在视频的哪段时间播放（默认全段）
  --bgm-fade-in / -out    BGM 淡入淡出（秒）
  --match-mode            4 种时长不匹配处理

match-mode (v1.3):
  loop         短 BGM 循环(默认);长 BGM 截短到视频长
  truncate     BGM 截到视频长
  silence-end  BGM 播完就静
  ask          AI 必须先问用户

示例:
  %(prog)s --input v.mp4 --bgm b.mp3 --volume 0.18 --output o.mp4
  %(prog)s --input v.mp4 --bgm b.mp3 --start 10 --end 20 --output o.mp4
  %(prog)s --input v.mp4 --bgm b.mp3 --bgm-fade-in 1 --bgm-fade-out 2 --output o.mp4
        """,
    )
    parser.add_argument("--input", dest="video", required=True, help="输入视频")
    parser.add_argument("--bgm", required=True, help="BGM 文件")
    parser.add_argument("--volume", type=float, default=0.18, help="BGM 音量(0-2,默认 0.18)")
    parser.add_argument("--video-volume", type=float, default=1.0, help="原声音量(0-2,默认 1.0)")
    parser.add_argument("--start", type=float, default=0, help="BGM 起始时间(秒)")
    parser.add_argument("--end", type=float, default=None, help="BGM 结束时间(秒)")
    parser.add_argument("--bgm-fade-in", type=float, default=0, help="BGM 起始淡入(秒)")
    parser.add_argument("--bgm-fade-out", type=float, default=0, help="BGM 结束淡出(秒)")
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