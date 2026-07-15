# -*- coding: utf-8 -*-
"""
智剪工坊 · edit 子技能
14 个原子画面/音频编辑操作,统一 1080x1920 竖屏 + 30fps + libx264

P0 (8 个,基础画面/音频):
  remove        去头/去尾/去中间(可多段)
  volume        调音量(0=静音, 1=不变, 2=2倍)
  mute          静音/删除音轨
  letterbox     加黑边(letterbox/pillarbox)
  scale         缩放
  crop          裁剪
  rotate        旋转 90/180/270
  flip          翻转(水平/垂直)

P1 (6 个,扩展):
  extract-audio 从视频提取音频
  fade-audio    音频淡入淡出
  watermark     加 logo 水印
  multi-res     多分辨率输出(480/720/1080)
  gif           GIF 导出
  thumbnail     抽 1 帧作为缩略图

用法:
  python edit.py remove --input v.mp4 --mode head --seconds 3 --output out.mp4
  python edit.py volume --input v.mp4 --factor 0.5 --output out.mp4
  python edit.py letterbox --input v.mp4 --width 1080 --height 1920 --bg black --output out.mp4
  python edit.py watermark --input v.mp4 --logo logo.png --position topright --output out.mp4
  python edit.py multi-res --input v.mp4 --output-dir out/
  python edit.py gif --input v.mp4 --output out.gif --width 480 --fps 15
  python edit.py thumbnail --input v.mp4 --output thumb.jpg --time 5


📖 SKILL.md §14 索引 → REQUIRED: read references/16-edit.md
"""
import argparse
import sys
from pathlib import Path

# 引入公共库
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    unified_vf, ensure_dir,
    log_info, log_warn, log_error, log_section, safe_run,
)

# v1.4: extract-audio / fade-audio 重导出自 audio/extract.py（canonical 实现）
# 旧路径 edit.py extract-audio 继续工作，复用 audio/extract.py 的逻辑
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from audio.extract import extract_audio as _extract_audio
    from audio.extract import fade_audio as _fade_audio
    # 将重导出函数注入到本模块命名空间（edit.py CLI 继续用这些名字）
    extract_audio = _extract_audio
    fade_audio = _fade_audio
except ImportError:
    # fallback: 如果 audio/ 不存在，使用本文件内的本地实现（向后兼容兜底）
    pass


# ============================================================
# P0: 8 个基础原子操作
# ============================================================

def remove(input_path, mode, output_path, seconds=None, regions=None,
           resolution="1080:1920", fps=30):
    """去头/去尾/去中间

    mode:
      head  - 去头 N 秒
      tail  - 去尾 N 秒
      regions - 去多个区间,regions=[(ss, t), ...]
    """
    log_section(f"remove [{mode}] {Path(input_path).name}")
    ensure_dir(Path(output_path).parent)

    duration = get_duration(input_path)

    # 计算要保留的区间
    if mode == "head":
        if seconds is None:
            log_error("--seconds 必填"); return
        keep_intervals = [(float(seconds), max(0, duration - float(seconds)))]
    elif mode == "tail":
        if seconds is None:
            log_error("--seconds 必填"); return
        keep_intervals = [(0, max(0, duration - float(seconds)))]
    elif mode == "regions":
        if not regions:
            log_error("--exclude 必填"); return
        exclude = sorted(regions, key=lambda x: x[0])
        keep_intervals = []
        cur = 0.0
        for ss, t in exclude:
            if ss > cur:
                keep_intervals.append((cur, ss - cur))
            cur = max(cur, float(ss) + float(t))
        if cur < duration:
            keep_intervals.append((cur, duration - cur))
    else:
        log_error(f"未知 mode: {mode}"); return

    log_info(f"原时长 {duration:.1f}s → 保留 {len(keep_intervals)} 段")

    # 切多段(temp 放 output 同目录,避免跨磁盘)
    out_dir = Path(output_path).parent
    temp_files = []
    for i, (ss, t) in enumerate(keep_intervals):
        if t <= 0.01:
            continue
        tmp = out_dir / f"__edit_tmp_{i}.mp4"
        run_ffmpeg([
            "-ss", str(ss),
            "-i", str(input_path),
            "-t", str(t),
            "-vf", unified_vf(resolution, fps),
            *DEFAULT_ENCODE_ARGS,
            str(tmp),
        ])
        temp_files.append(tmp)

    # 拼接 or 单段改名
    if len(temp_files) == 0:
        log_error("没有可保留的内容"); return
    elif len(temp_files) == 1:
        temp_files[0].replace(output_path)
    else:
        list_file = out_dir / "__edit_concat.txt"
        with open(list_file, "w", encoding="utf-8") as f:
            for tf in temp_files:
                f.write(f"file '{tf}'\n")
        run_ffmpeg([
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(output_path),
        ])
        list_file.unlink(missing_ok=True)

    for tf in temp_files:
        tf.unlink(missing_ok=True)

    log_info(f"输出: {output_path} ({get_duration(output_path):.1f}s)")


def volume(input_path, factor, output_path, resolution="1080:1920", fps=30):
    """调音量,factor 倍数(0=静音, 1=不变, 2=2 倍)"""
    log_section(f"volume ×{factor} {Path(input_path).name}")
    ensure_dir(Path(output_path).parent)
    run_ffmpeg([
        "-i", str(input_path),
        "-vf", unified_vf(resolution, fps),
        "-af", f"volume={factor}",
        *DEFAULT_ENCODE_ARGS,
        str(output_path),
    ])
    log_info(f"输出: {output_path}")


def mute(input_path, output_path, resolution="1080:1920", fps=30):
    """删除音轨(完全静默)"""
    log_section(f"mute {Path(input_path).name}")
    ensure_dir(Path(output_path).parent)
    run_ffmpeg([
        "-i", str(input_path),
        "-vf", unified_vf(resolution, fps),
        "-an",
        *DEFAULT_ENCODE_ARGS,
        str(output_path),
    ])
    log_info(f"输出: {output_path} (无音轨)")


def letterbox(input_path, output_path, width=1080, height=1920,
              bg="black", fps=30):
    """加黑边(letterbox / pillarbox)

    视频缩放到 w×h 内,加 bg 颜色的边保持比例
    """
    log_section(f"letterbox → {width}x{bg}×{height} {Path(input_path).name}")
    ensure_dir(Path(output_path).parent)
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:{bg},"
        f"setsar=1,fps={fps}"
    )
    run_ffmpeg([
        "-i", str(input_path),
        "-vf", vf,
        *DEFAULT_ENCODE_ARGS,
        str(output_path),
    ])
    log_info(f"输出: {output_path}")


def scale(input_path, output_path, width, height, fps=30):
    """缩放到指定尺寸(可能变形)"""
    log_section(f"scale → {width}x{height} {Path(input_path).name}")
    ensure_dir(Path(output_path).parent)
    run_ffmpeg([
        "-i", str(input_path),
        "-vf", f"scale={width}:{height},fps={fps}",
        *DEFAULT_ENCODE_ARGS,
        str(output_path),
    ])
    log_info(f"输出: {output_path}")


def crop(input_path, output_path, x, y, width, height, fps=30):
    """裁剪:从 (x, y) 起取 width × height"""
    log_section(f"crop ({x},{y}) {width}x{height} {Path(input_path).name}")
    ensure_dir(Path(output_path).parent)
    run_ffmpeg([
        "-i", str(input_path),
        "-vf", f"crop={width}:{height}:{x}:{y},fps={fps}",
        *DEFAULT_ENCODE_ARGS,
        str(output_path),
    ])
    log_info(f"输出: {output_path}")


def rotate(input_path, output_path, degrees, fps=30):
    """旋转 90 / 180 / 270 度"""
    log_section(f"rotate {degrees}° {Path(input_path).name}")
    ensure_dir(Path(output_path).parent)
    if degrees == 90:
        t = "1"  # 顺时针 90
    elif degrees == 180:
        t = "1,1"  # 两次 90
    elif degrees == 270:
        t = "2"  # 逆时针 90
    else:
        log_error("degrees 必须是 90/180/270"); return
    run_ffmpeg([
        "-i", str(input_path),
        "-vf", f"transpose={t},fps={fps}",
        *DEFAULT_ENCODE_ARGS,
        str(output_path),
    ])
    log_info(f"输出: {output_path}")


def flip(input_path, output_path, mode="h", fps=30):
    """翻转(水平 h / 垂直 v)"""
    log_section(f"flip {mode} {Path(input_path).name}")
    ensure_dir(Path(output_path).parent)
    vf = "hflip" if mode == "h" else "vflip"
    run_ffmpeg([
        "-i", str(input_path),
        "-vf", f"{vf},fps={fps}",
        *DEFAULT_ENCODE_ARGS,
        str(output_path),
    ])
    log_info(f"输出: {output_path}")


# ============================================================
# P1: 6 个扩展
# ============================================================

def extract_audio(input_path, output_path, fmt="mp3"):
    """从视频提取音频"""
    log_section(f"extract-audio {Path(input_path).name} → .{fmt}")
    ensure_dir(Path(output_path).parent)
    codec_map = {
        "mp3": "libmp3lame",
        "wav": "pcm_s16le",
        "aac": "aac",
    }
    codec = codec_map.get(fmt, "copy")
    run_ffmpeg([
        "-i", str(input_path),
        "-vn",
        "-acodec", codec,
        "-y", str(output_path),
    ])
    log_info(f"输出: {output_path}")


def fade_audio(input_path, output_path, fade_in=0, fade_out=0, fps=30):
    """音频淡入淡出(秒)"""
    log_section(f"fade-audio in={fade_in}s out={fade_out}s {Path(input_path).name}")
    ensure_dir(Path(output_path).parent)
    duration = get_duration(input_path)
    fade_out_st = max(0, duration - fade_out)
    af_parts = []
    if fade_in > 0:
        af_parts.append(f"afade=t=in:st=0:d={fade_in}")
    if fade_out > 0:
        af_parts.append(f"afade=t=out:st={fade_out_st}:d={fade_out}")
    af = ",".join(af_parts) if af_parts else "anull"
    run_ffmpeg([
        "-i", str(input_path),
        "-vf", f"fps={fps}",
        "-af", af,
        *DEFAULT_ENCODE_ARGS,
        str(output_path),
    ])
    log_info(f"输出: {output_path}")


def watermark(input_path, logo_path, output_path, position="topright",
              opacity=0.7, fps=30):
    """加 logo 水印

    position: topleft / topright / bottomleft / bottomright
    """
    log_section(f"watermark {position} opacity={opacity}")
    ensure_dir(Path(output_path).parent)
    pos_map = {
        "topleft": "10:10",
        "topright": "main_w-overlay_w-10:10",
        "bottomleft": "10:main_h-overlay_h-10",
        "bottomright": "main_w-overlay_w-10:main_h-overlay_h-10",
    }
    pos = pos_map.get(position, "10:10")
    run_ffmpeg([
        "-i", str(input_path),
        "-i", str(logo_path),
        "-filter_complex",
        f"[1:v]format=rgba,colorchannelmixer=aa={opacity}[logo];"
        f"[0:v][logo]overlay={pos}",
        *DEFAULT_ENCODE_ARGS,
        str(output_path),
    ])
    log_info(f"输出: {output_path}")


def multi_res(input_path, output_dir, resolutions="480:360,720:540,1080:1920", fps=30):
    """多分辨率输出(同一视频输出多种尺寸)"""
    log_section(f"multi-res {Path(input_path).name}")
    out_dir = ensure_dir(output_dir)
    res_list = [r.strip() for r in resolutions.split(",") if r.strip()]
    log_info(f"输出 {len(res_list)} 种分辨率")
    for i, res in enumerate(res_list):
        try:
            w, h = res.split(":")
        except ValueError:
            log_error(f"分辨率格式错: {res}"); continue
        out = out_dir / f"{Path(input_path).stem}_{w}x{h}.mp4"
        log_info(f"[{i+1}/{len(res_list)}] {w}x{h}")
        run_ffmpeg([
            "-i", str(input_path),
            "-vf", f"scale={w}:{h},fps={fps}",
            *DEFAULT_ENCODE_ARGS,
            str(out),
        ])
    log_info(f"全部输出: {out_dir}")


def gif(input_path, output_path, width=480, fps=15, start=0, duration=None):
    """GIF 导出(用 palette 优化质量)"""
    log_section(f"gif → {output_path}")
    ensure_dir(Path(output_path).parent)
    duration_arg = str(duration) if duration else "999999"
    palette = "__gif_palette.png"
    vf_base = f"fps={fps},scale={width}:-1:flags=lanczos"
    try:
        # 1. 生成 palette
        run_ffmpeg([
            "-ss", str(start),
            "-i", str(input_path),
            "-t", duration_arg,
            "-vf", f"{vf_base},palettegen",
            "-y", palette,
        ])
        # 2. 用 palette 生成 gif
        run_ffmpeg([
            "-ss", str(start),
            "-i", str(input_path),
            "-t", duration_arg,
            "-i", palette,
            "-filter_complex", f"{vf_base} [x]; [x][1:v] paletteuse",
            "-loop", "0",
            "-y", str(output_path),
        ])
    finally:
        Path(palette).unlink(missing_ok=True)
    log_info(f"输出: {output_path}")


def thumbnail(input_path, output_path, time=0, width=None):
    """抽 1 帧作为缩略图(默认第 0 秒)"""
    log_section(f"thumbnail @ {time}s {Path(input_path).name}")
    ensure_dir(Path(output_path).parent)
    cmd = [
        "-ss", str(time),
        "-i", str(input_path),
        "-vframes", "1",
    ]
    if width:
        cmd.extend(["-vf", f"scale={width}:-1"])
    cmd.extend(["-y", str(output_path)])
    run_ffmpeg(cmd)
    log_info(f"输出: {output_path}")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · edit(14 个原子操作,P0 8 + P1 6)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s remove --input v.mp4 --mode head --seconds 3 --output out.mp4
  %(prog)s volume --input v.mp4 --factor 0.5 --output out.mp4
  %(prog)s letterbox --input v.mp4 --width 1080 --height 1920 --output out.mp4
  %(prog)s watermark --input v.mp4 --logo logo.png --position topright --output out.mp4
  %(prog)s multi-res --input v.mp4 --output-dir out/
  %(prog)s gif --input v.mp4 --output out.gif --width 480 --fps 15
  %(prog)s thumbnail --input v.mp4 --output thumb.jpg --time 5
        """,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # 1. remove
    p = sub.add_parser("remove", help="去头/去尾/去中间")
    p.add_argument("-i", "--input", required=True)
    p.add_argument("--mode", choices=["head", "tail", "regions"], required=True)
    p.add_argument("--seconds", type=float, help="head/tail 模式:秒数")
    p.add_argument("--exclude", help="regions 模式:逗号分隔 'ss1-t1,ss2-t2'")
    p.add_argument("-o", "--output", required=True)

    # 2. volume
    p = sub.add_parser("volume", help="调音量")
    p.add_argument("-i", "--input", required=True)
    p.add_argument("--factor", type=float, required=True, help="倍数(0=静音, 1=不变, 2=2倍)")
    p.add_argument("-o", "--output", required=True)

    # 3. mute
    p = sub.add_parser("mute", help="静音/删除音轨")
    p.add_argument("-i", "--input", required=True)
    p.add_argument("-o", "--output", required=True)

    # 4. letterbox
    p = sub.add_parser("letterbox", help="加黑边")
    p.add_argument("-i", "--input", required=True)
    p.add_argument("--width", type=int, default=1080)
    p.add_argument("--height", type=int, default=1920)
    p.add_argument("--bg", default="black", help="背景色,默认 black")
    p.add_argument("-o", "--output", required=True)

    # 5. scale
    p = sub.add_parser("scale", help="缩放")
    p.add_argument("-i", "--input", required=True)
    p.add_argument("--width", type=int, required=True)
    p.add_argument("--height", type=int, required=True)
    p.add_argument("-o", "--output", required=True)

    # 6. crop
    p = sub.add_parser("crop", help="裁剪")
    p.add_argument("--input", required=True)
    p.add_argument("--x", type=int, default=0)
    p.add_argument("--y", type=int, default=0)
    p.add_argument("--width", type=int, required=True)
    p.add_argument("--height", type=int, required=True)
    p.add_argument("-o", "--output", required=True)

    # 7. rotate
    p = sub.add_parser("rotate", help="旋转 90/180/270")
    p.add_argument("-i", "--input", required=True)
    p.add_argument("--degrees", type=int, choices=[90, 180, 270], required=True)
    p.add_argument("-o", "--output", required=True)

    # 8. flip
    p = sub.add_parser("flip", help="翻转(水平/垂直)")
    p.add_argument("--input", required=True)
    p.add_argument("--mode", choices=["h", "v"], default="h")
    p.add_argument("-o", "--output", required=True)

    # 9. extract-audio
    p = sub.add_parser("extract-audio", help="提取音频")
    p.add_argument("-i", "--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--format", default="mp3", choices=["mp3", "wav", "aac"])

    # 10. fade-audio
    p = sub.add_parser("fade-audio", help="音频淡入淡出")
    p.add_argument("--input", required=True)
    p.add_argument("--fade-in", type=float, default=0)
    p.add_argument("--fade-out", type=float, default=0)
    p.add_argument("--output", required=True)

    # 11. watermark
    p = sub.add_parser("watermark", help="加 logo 水印")
    p.add_argument("--input", required=True)
    p.add_argument("--logo", required=True, help="logo 图片")
    p.add_argument("--position", choices=["topleft", "topright", "bottomleft", "bottomright"], default="topright")
    p.add_argument("--opacity", type=float, default=0.7)
    p.add_argument("--output", required=True)

    # 12. multi-res
    p = sub.add_parser("multi-res", help="多分辨率输出")
    p.add_argument("--input", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--resolutions", default="480:360,720:540,1080:1920")

    # 13. gif
    p = sub.add_parser("gif", help="GIF 导出")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--width", type=int, default=480)
    p.add_argument("--fps", type=int, default=15)
    p.add_argument("--start", type=float, default=0)
    p.add_argument("--duration", type=float, help="时长(秒),默认全片")

    # 14. thumbnail
    p = sub.add_parser("thumbnail", help="抽 1 帧作为缩略图")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--time", type=float, default=0)
    p.add_argument("--width", type=int, help="输出宽度(默认原图)")

    args = parser.parse_args()

    if args.cmd == "remove":
        regions = None
        if args.mode == "regions":
            if not args.exclude:
                log_error("--exclude 必填"); return
            regions = []
            for r in args.exclude.split(","):
                ss, t = r.strip().split("-")
                regions.append((float(ss), float(t)))
        remove(args.input, args.mode, args.output, args.seconds, regions)
    elif args.cmd == "volume":
        volume(args.input, args.factor, args.output)
    elif args.cmd == "mute":
        mute(args.input, args.output)
    elif args.cmd == "letterbox":
        letterbox(args.input, args.output, args.width, args.height, args.bg)
    elif args.cmd == "scale":
        scale(args.input, args.output, args.width, args.height)
    elif args.cmd == "crop":
        crop(args.input, args.output, args.x, args.y, args.width, args.height)
    elif args.cmd == "rotate":
        rotate(args.input, args.output, args.degrees)
    elif args.cmd == "flip":
        flip(args.input, args.output, args.mode)
    elif args.cmd == "extract-audio":
        extract_audio(args.input, args.output, args.format)
    elif args.cmd == "fade-audio":
        fade_audio(args.input, args.output, args.fade_in, args.fade_out)
    elif args.cmd == "watermark":
        watermark(args.input, args.logo, args.output, args.position, args.opacity)
    elif args.cmd == "multi-res":
        multi_res(args.input, args.output_dir, args.resolutions)
    elif args.cmd == "gif":
        gif(args.input, args.output, args.width, args.fps, args.start, args.duration)
    elif args.cmd == "thumbnail":
        thumbnail(args.input, args.output, args.time, args.width)


if __name__ == "__main__":
    safe_run(main)()
