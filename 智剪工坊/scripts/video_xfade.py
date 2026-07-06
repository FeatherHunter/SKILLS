# -*- coding: utf-8 -*-
"""
智剪工坊 · xfade 子技能
两段视频之间加转场(xfade filter,支持 intent.html 9 种 type)

用法:
  python video_xfade.py --a clip1.mp4 --b clip2.mp4 --type fade --duration 1 --output joined.mp4
  python video_xfade.py --a clip1.mp4 --b clip2.mp4 --type wipe-left --duration 1 --output joined.mp4

意图: SKILL.md §G.2 声明 9 种 type,本脚本完整支持。
- 'none' / 'cut' → 短路(不调 xfade,走 ffmpeg concat 硬切)
- 其他 type → 自动映射到 ffmpeg xfade filter 的合法名
"""
import argparse
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    ensure_dir, log_info, log_warn, log_error, log_section, safe_run, ParamError,
)


# ========== 意图层 type 枚举(intent.html 9 种) ==========
# AI 看到的、用户选的、intent.json 里保存的——都是这套名。
INTENT_TYPES = [
    "none",       # 不开转场（用户没选，零猜测默认值）
    "cut",        # 直切（用户明确选"我要硬切"）
    "fade",       # 淡入淡出
    "dissolve",   # 溶解
    "wipe-left",  # 左擦除
    "wipe-right", # 右擦除
    "slide-up",   # 上滑
    "zoom-in",    # 推进
    "blur",       # 模糊过渡
]


# ========== 命名映射表(intent.html 友好名 → ffmpeg xfade 合法名) ==========
# intent.html 用户认知的是"左擦除"等友好词;ffmpeg xfade filter 只认 wipeleft。
# AI 不该做翻译,本脚本在边界层完成。
TRANSITION_MAP = {
    "none":        None,         # 短路：不调 xfade
    "cut":         None,         # 短路：不调 xfade（直切=硬切）
    "fade":        "fade",
    "dissolve":    "dissolve",
    "wipe-left":   "wipeleft",
    "wipe-right":  "wiperight",
    "slide-up":    "slideup",
    "zoom-in":     "zoomin",
    "blur":        "hblur",
}


# ========== 完整 ffmpeg xfade 列表(用于 hint 日志) ==========
FFMPEG_TRANSITIONS = [
    "fade", "wipeleft", "wiperight", "wipeup", "wipedown",
    "slideleft", "slideright", "slideup", "slidedown",
    "circlecrop", "rectcrop", "distance", "fadeblack", "fadewhite",
    "radial", "smoothleft", "smoothright", "smoothup", "smoothdown",
    "circleopen", "circleclose", "vertopen", "vertclose",
    "horzopen", "horzclose", "dissolve", "pixelize",
    "diagtl", "diagtr", "diagbl", "diagbr",
    "hlslice", "hrslice", "vuslice", "vdslice", "hblur",
    "fadegrays", "wipetl", "wipetr", "wipebl", "wipebr",
    "squeezeh", "squeezev", "zoomin", "fadefast", "fadeslow",
    "hlwind", "hrwind", "vuwind", "vdwind",
    "coverleft", "coverright", "coverup", "coverdown",
    "revealleft", "revealright", "revealup", "revealdown",
]


def is_short_circuit(transition):
    """type='none' 或 type='cut' → 短路(不调 xfade)"""
    return transition in ("none", "cut", None, "")


def resolve_transition(transition):
    """意图名 → ffmpeg 合法名。

    Args:
        transition: intent.html 友好名（"wipe-left" 等）

    Returns:
        ffmpeg xfade filter 合法名（"wipeleft" 等）
        None 表示短路
    """
    if is_short_circuit(transition):
        return None

    if transition not in TRANSITION_MAP:
        log_warn(f"意图 type '{transition}' 不在 9 种标准枚举,可能无法执行")
        log_warn(f"标准枚举: {', '.join(INTENT_TYPES)}")
        return transition  # 透传给 ffmpeg,让 ffmpeg 自己报错（fail-loud）

    return TRANSITION_MAP[transition]


def xfade(a, b, transition, duration, output, offset=None, custom_offset=None):
    """两段视频加转场拼接。

    Args:
        transition: intent.html 友好名（'fade'/'wipe-left'/'none'/'cut' 等）
        duration: 转场时长(秒)
        offset: 转场起始时间(相对 A);None=默认 A 末尾
        custom_offset: 自定义 offset(优先级高于 offset)

    Returns:
        output 路径（成功）;None（失败）
    """
    log_section(f"xfade: {Path(a).name} + {transition} + {Path(b).name}")

    # Step 1: 解析意图名 → ffmpeg 合法名
    ffmpeg_t = resolve_transition(transition)
    if ffmpeg_t is None:
        log_info(f"type='{transition}' → 短路(硬切,不走 xfade)")
        return _concat_hard_cut(a, b, output)

    # Step 2: 校验 ffmpeg 合法名(防 typo)
    if ffmpeg_t not in FFMPEG_TRANSITIONS:
        log_warn(f"ffmpeg xfade 可能不支持 '{ffmpeg_t}'")
        log_warn(f"完整列表: ffmpeg -h filter=xfade")

    # Step 3: 计算 offset
    duration_a = get_duration(a)
    duration_b = get_duration(b)
    if offset is None:
        offset = max(0, duration_a - duration)
        log_info(f"自动 offset: {offset:.2f}s (A 末尾)")
    if custom_offset is not None:
        offset = custom_offset

    ensure_dir(Path(output).parent)

    # Step 4: 调 ffmpeg xfade filter
    run_ffmpeg([
        "-i", str(a),
        "-i", str(b),
        "-filter_complex",
        f"[0:v][1:v]xfade=transition={ffmpeg_t}:duration={duration}:offset={offset}[v];"
        f"[0:a][1:a]acrossfade=d={duration}[a]",
        "-map", "[v]",
        "-map", "[a]",
        *DEFAULT_ENCODE_ARGS,
        str(output),
    ])
    log_info(f"输出: {output} ({get_duration(output):.1f}s)")
    return str(output)


def _concat_hard_cut(a, b, output):
    """type='none'/'cut' 短路路径: 用 ffmpeg concat 协议硬切拼接。

    不用 stream copy: 输入可能 fps 不一致,stream copy 后 VFR 导致兼容性 bug。
    统一走重编 + faststart 一次性解决。
    """
    ensure_dir(Path(output).parent)
    list_file = Path(output).parent / f"_concat_{Path(output).stem}.txt"
    list_file.write_text(
        f"file '{Path(a).resolve()}'\nfile '{Path(b).resolve()}'\n",
        encoding='utf-8'
    )
    try:
        run_ffmpeg([
            "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            "-vsync", "cfr", "-r", "30",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(output),
        ])
    finally:
        if list_file.exists():
            list_file.unlink()
    log_info(f"硬切输出: {output} ({get_duration(output):.1f}s)")
    return str(output)


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 视频转场(xfade)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
意图层 type(9 种, intent.html 默认):
  {', '.join(INTENT_TYPES)}

底层 ffmpeg xfade 60+ 种(完整列表): ffmpeg -h filter=xfade

示例:
  %(prog)s --a clip1.mp4 --b clip2.mp4 --type fade --duration 1 --output joined.mp4
  %(prog)s --a a.mp4 --b b.mp4 --type wipe-left --duration 1 --output out.mp4
  %(prog)s --a a.mp4 --b b.mp4 --type none --output out.mp4  # 硬切(短路)
        """,
    )
    parser.add_argument("--a", required=True, help="视频 A(先)")
    parser.add_argument("--b", required=True, help="视频 B(后)")
    parser.add_argument("--type", default="fade",
                        help=f"转场类型(意图名, 默认 fade, 9 种: {', '.join(INTENT_TYPES)})")
    parser.add_argument("--duration", type=float, default=1.0,
                        help="转场时长(秒, 默认 1)")
    parser.add_argument("--offset", type=float, default=None,
                        help="转场起始时间(相对 A, 默认 A 末尾)")
    parser.add_argument("--output", dest="output", required=True, help="输出视频")
    args = parser.parse_args()

    result = xfade(args.a, args.b, args.type, args.duration, args.output, args.offset)
    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    safe_run(main)