# -*- coding: utf-8 -*-
"""
智剪工坊 · image_to_video 子技能
把单张图片转成短视频片段(供 sequence 拼接)

用意:
  v1.3 新增:
    - 图片素材(智剪工坊-意图编辑.html photo)无法直接进 xfade_concat/concatenate_simple
    - 必须先转成视频流(h264 + aac + 30fps)
    - 支持默认时长 / 自定义时长 / 可选 Ken Burns 推近效果

用法:
  # 默认: 3秒静态图, 30fps, 1920x1080(letterbox/pad)
  python image_to_video.py --image photo.jpg --output photo.mp4

  # 自定义时长 5秒
  python image_to_video.py --image photo.jpg --output photo.mp4 --duration 5

  # Ken Burns 推近(慢推近 1.0 → 1.2 倍, 5秒)
  python image_to_video.py --image photo.jpg --output photo.mp4 --duration 5 --ken-burns-in

  # Ken Burns 拉远(1.2 → 1.0 倍, 5秒)
  python image_to_video.py --image photo.jpg --output photo.mp4 --duration 5 --ken-burns-out

  # 自定义目标分辨率(默认 1920x1080)
  python image_to_video.py --image photo.jpg --output photo.mp4 --width 1280 --height 720

📖 SKILL.md §阶段 2 2.1 索引
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    ensure_dir, log_info, log_warn, log_error, log_section, safe_run, ParamError,
)


# 支持的图片格式
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def image_to_video(
    image, output,
    duration=3.0,
    width=1920,
    height=1080,
    ken_burns_in=False,
    ken_burns_out=False,
    fps=30,
):
    """把单张图片转成短视频片段。

    Args:
        image: 输入图片路径(.jpg/.png/.webp/.bmp)
        output: 输出视频路径(.mp4)
        duration: 片段时长(秒,默认 3)
        width: 目标宽度(默认 1920)
        height: 目标高度(默认 1080)
        ken_burns_in: Ken Burns 推近(1.0 → 1.15 倍,适合静态图增动感)
        ken_burns_out: Ken Burns 拉远(1.15 → 1.0 倍)
        fps: 帧率(默认 30,与 video_normalize 保持一致)

    Returns:
        output 路径(成功);None(失败)

    行为:
        - 图片缩放适配目标比例(force_original_aspect_ratio=decrease)
        - 加黑边居中(letterbox)
        - 加静音音轨(anullsrc,保证后续 concat 不报错)
        - Ken Burns 效果:用 zoompan filter 实现(慢推近/拉远)
    """
    log_section(f"图片转视频: {Path(image).name} → {Path(output).name}")

    # ========== 参数验证 ==========
    img_path = Path(image)
    if not img_path.exists():
        log_error(f"图片不存在: {image}")
        return None

    if img_path.suffix.lower() not in IMAGE_EXTENSIONS:
        log_error(f"不支持的图片格式: {img_path.suffix}（支持: {sorted(IMAGE_EXTENSIONS)}）")
        return None

    if duration <= 0:
        log_error(f"duration 必须 > 0（当前: {duration}）")
        return None

    if width <= 0 or height <= 0:
        log_error(f"width/height 必须 > 0（当前: {width}x{height}）")
        return None

    if ken_burns_in and ken_burns_out:
        log_error(f"ken-burns-in 和 ken-burns-out 不能同时为 True")
        return None

    if fps <= 0:
        log_error(f"fps 必须 > 0（当前: {fps}）")
        return None

    # ========== 构造 filter ==========
    # 第一步: 缩放并 letterbox 到目标比例
    base_scale_pad = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,"
        f"setsar=1"
    )

    if ken_burns_in or ken_burns_out:
        # Ken Burns 效果: zoompan filter
        # 计算 zoom 表达式: 1.0 → 1.15 (推近) 或 1.15 → 1.0 (拉远)
        if ken_burns_in:
            # 用 on 帧数计算 zoom 起始值
            # zoompan 用 z 表达式计算, pzoom=0.0005 表示每帧 +0.0005
            # 从 1.0 到 1.0 + 0.0005 * (duration*fps) = 1.0 + 0.5*5 = 3.5 (太猛)
            # 实际: 1.0 + 0.0003 * 150 = 1.045 (5% 放大, 温和)
            zoom_expr = "min(zoom+0.0003,1.15)"
            start_zoom = "1.0"
        else:
            zoom_expr = "if(eq(on,0),1.15,max(1.0,zoom-0.0003))"
            start_zoom = "1.15"

        # zoompan filter: d=总帧数, s=输出尺寸, fps=输出帧率
        total_frames = int(duration * fps)
        v_filter = (
            f"scale={width*2}:{height*2}:force_original_aspect_ratio=increase,"
            f"zoompan=z='{zoom_expr}':d={total_frames}:s={width}x{height}:fps={fps},"
            f"setsar=1"
        )
    else:
        # 静态图: 图片本身只有 1 帧,需要 -loop 1 -t duration 重复
        v_filter = base_scale_pad

    # 音频: anullsrc 静音填充
    # 采样率 44100 stereo 与 video_normalize 默认对齐
    a_filter = "anullsrc=r=44100:cl=stereo"

    # ========== 拼装 ffmpeg 命令 ==========
    ensure_dir(Path(output).parent)

    if ken_burns_in or ken_burns_out:
        # Ken Burns 模式: 不需要 -loop,因为 zoompan 自带 d=N 帧
        cmd = [
            "-y", "-noautorotate",
            "-i", str(image),
            "-f", "lavfi", "-i", a_filter,
            "-filter_complex", f"[0:v]{v_filter}[v];[1:a]anull[a]",
            "-map", "[v]", "-map", "[a]",
            "-t", str(duration),  # 兜底时长限制
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-vsync", "cfr", "-r", str(fps),
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-threads", "0",
            str(output),
        ]
    else:
        # 静态图模式: -loop 1 -t duration 让图片循环时长
        cmd = [
            "-y", "-noautorotate",
            "-loop", "1", "-i", str(image),
            "-f", "lavfi", "-i", a_filter,
            "-filter_complex", f"[0:v]{v_filter}[v];[1:a]anull[a]",
            "-map", "[v]", "-map", "[a]",
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-vsync", "cfr", "-r", str(fps),
            "-pix_fmt", "yuv420p",
            "-shortest",  # 用 -t 限制
            "-movflags", "+faststart",
            "-threads", "0",
            str(output),
        ]

    run_ffmpeg(cmd)

    # 验证输出
    out_dur = get_duration(output)
    if out_dur is None or out_dur < 0.1:
        log_error(f"输出时长异常: {out_dur}s")
        return None

    log_info(f"输出: {output} ({out_dur:.1f}s, {width}x{height}@{fps}fps)")
    return str(output)


# ========== 批量转换辅助（AI 编排可能需要） ==========

def batch_image_to_video(images, output_dir, duration=3.0, **kwargs):
    """批量把一组图片转成视频片段。

    Args:
        images: 图片路径列表
        output_dir: 输出目录
        duration: 每张图片的时长(秒)
        **kwargs: 传给 image_to_video 的其他参数

    Returns:
        转换结果列表 [(input, output_path or None), ...]
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for img in images:
        img_p = Path(img)
        out_p = out_dir / f"{img_p.stem}.mp4"
        result = image_to_video(img, str(out_p), duration=duration, **kwargs)
        results.append((str(img), result))
    return results


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 图片转视频（v1.3 新增，序列中图片素材专用）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 默认 3 秒
  %(prog)s --image photo.jpg --output photo.mp4

  # 5 秒 + Ken Burns 推近
  %(prog)s --image photo.jpg --output photo.mp4 --duration 5 --ken-burns-in

  # 自定义分辨率
  %(prog)s --image photo.jpg --output photo.mp4 --width 1280 --height 720
        """,
    )
    parser.add_argument("--image", required=True, help="输入图片文件(.jpg/.png/.webp/.bmp)")
    parser.add_argument("--output", required=True, help="输出视频文件(.mp4)")
    parser.add_argument("--duration", type=float, default=3.0, help="片段时长(秒,默认 3)")
    parser.add_argument("--width", type=int, default=1920, help="输出宽度(默认 1920)")
    parser.add_argument("--height", type=int, default=1080, help="输出高度(默认 1080)")
    parser.add_argument("--fps", type=int, default=30, help="帧率(默认 30)")
    parser.add_argument("--ken-burns-in", action="store_true", help="Ken Burns 推近效果(1.0 → 1.15)")
    parser.add_argument("--ken-burns-out", action="store_true", help="Ken Burns 拉远效果(1.15 → 1.0)")
    args = parser.parse_args()

    result = image_to_video(
        image=args.image,
        output=args.output,
        duration=args.duration,
        width=args.width,
        height=args.height,
        ken_burns_in=args.ken_burns_in,
        ken_burns_out=args.ken_burns_out,
        fps=args.fps,
    )
    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    safe_run(main)()
