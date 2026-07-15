# -*- coding: utf-8 -*-
"""
智剪工坊 · cutout 子技能
AI 抠图(rembg:把人物从背景分离)

用法:
  # 单张图抠图
  python cutout.py --input in.png --out out.png

  # 视频抠图(逐帧处理,慢但效果好)
  python cutout.py --input in.mp4 --out out.mp4 --interval 5

  # 抠图 + 换背景
  python cutout.py --input in.png --bg bg.jpg --out out.png

依赖:rembg, onnxruntime(可选,加速)


📖 SKILL.md §14 索引 → REQUIRED: read references/09-ai-features.md
"""
import argparse
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    ensure_dir, log_info, log_warn, log_section, safe_run,
)


def cutout_image(input_path, output_path):
    """单张图抠图"""
    log_section(f"抠图: {Path(input_path).name}")

    try:
        from rembg import remove
    except ImportError:
        log_warn("rembg 未安装")
        log_warn("安装: pip install rembg")
        return False

    from PIL import Image

    img = Image.open(input_path)
    out = remove(img)
    out.save(output_path)
    log_info(f"输出: {output_path}")
    return True


def cutout_with_bg(input_path, bg_path, output_path):
    """抠图 + 换背景"""
    log_section(f"抠图 + 换背景: {Path(input_path).name}")

    try:
        from rembg import remove
    except ImportError:
        log_warn("rembg 未安装")
        return False

    from PIL import Image

    # 抠图
    img = Image.open(input_path)
    out = remove(img)

    # 合成背景
    bg = Image.open(bg_path)
    # 调整大小
    bg = bg.resize(out.size)
    # 合成
    bg.paste(out, (0, 0), out)

    bg.save(output_path)
    log_info(f"输出: {output_path}")
    return True


def cutout_video(input_path, output_path, interval=1):
    """视频抠图(逐帧处理,慢)"""
    log_section(f"视频抠图: {Path(input_path).name}(每 {interval} 帧)")
    ensure_dir(Path(output_path).parent)

    try:
        from rembg import remove
    except ImportError:
        log_warn("rembg 未安装")
        return False

    # 1. 抽帧
    frames_dir = Path(output_path).with_suffix(".frames")
    ensure_dir(frames_dir)
    run_ffmpeg([
        "-i", str(input_path),
        "-vf", f"select='not(mod(n\\,{interval}))'",
        "-vsync", "vfr",
        str(frames_dir / "frame_%05d.png"),
    ])

    frames = sorted(frames_dir.glob("frame_*.png"))
    log_info(f"抽帧: {len(frames)} 张")

    # 2. 抠图每帧
    out_dir = Path(output_path).with_suffix(".cutout")
    ensure_dir(out_dir)

    from PIL import Image
    for frame in frames:
        img = Image.open(frame)
        out = remove(img)
        out.save(out_dir / frame.name)
    log_info(f"抠图完成: {len(frames)} 张")

    # 3. 重组视频
    run_ffmpeg([
        "-framerate", "30",
        "-i", str(out_dir / "frame_%05d.png"),
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ])

    # 4. 加原音频
    temp_video = Path(output_path).with_suffix(".temp.mp4")
    Path(output_path).rename(temp_video)

    run_ffmpeg([
        "-i", str(temp_video),
        "-i", str(input_path),
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        str(output_path),
    ])

    log_info(f"输出: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · AI 抠图(rembg)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n  %(prog)s --input in.png --out out.png\n  %(prog)s --input in.png --bg bg.png --out out.png\n  %(prog)s --input in.mp4 --out out.mp4",
    )
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--bg", help="背景图(替换背景用)")
    parser.add_argument("--interval", type=int, default=1, help="视频抽帧间隔(视频模式)")
    args = parser.parse_args()

    is_video = args.input.lower().endswith(('.mp4', '.mov', '.mkv', '.avi'))

    if is_video:
        cutout_video(args.input, args.output, args.interval)
    elif args.bg:
        cutout_with_bg(args.input, args.bg, args.output)
    else:
        cutout_image(args.input, args.output)


if __name__ == "__main__":
    safe_run(main)()
