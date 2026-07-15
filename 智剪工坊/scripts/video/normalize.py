# -*- coding: utf-8 -*-
"""
智剪工坊 · video_normalize 子技能
视频参数归一化（统一 fps / 分辨率 / 编解码 / 像素格式）

用意:
  - 解决多视频拼接时 fps/分辨率/sar/编码不一致导致的 bug
  - 在单视频处理末尾自动调用
  - 默认参数适合绝大多数 vlog 场景（30fps / 1280x720 / h264 / aac）
  - html UI 暂不允许配置（disabled），但 CLI 支持覆盖

用法:
  python scripts/video_normalize.py --input v.mp4 --output v_norm.mp4
  # 默认参数: 30fps, 按 aspect_ratio 算高度, h264, aac 44100, yuv420p

  # 扩展位（未来启用 html 配置后）
  python scripts/video_normalize.py --input v.mp4 --output v_norm.mp4 \
    --fps 60 --resolution 3840x2160 \
    --video-codec h264 --audio-codec aac \
    --audio-sample-rate 48000 --audio-channels 2 \
    --pixel-format yuv420p

意图层 op:
  - 不作为独立 op,而是 process_video() 末尾自动调用
  - intent.json.output.fps / video_codec / audio_codec 是配置入口

标准参数（v1.3 默认）:
  fps:               30
  resolution:        按 output.aspect_ratio 自动算（16:9 → 1280x720, 9:16 → 720x1280）
  video_codec:       h264 (libx264)
  audio_codec:       aac
  audio_sample_rate: 44100
  audio_channels:    2 (stereo)
  pixel_format:      yuv420p
  sar:               1:1 (正方形像素)
  moov_atom:         front (+faststart)
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    ensure_dir, log_info, log_warn, log_error, log_section, safe_run, ParamError,
)


def get_video_info_simple(video_path):
    """简易版 get_video_info: 只读 width / height / fps

    common.py 没有 get_video_info,用 ffmpeg -i 解析（ffprobe 不一定有）
    """
    import re
    import subprocess
    cmd = ["ffmpeg", "-i", str(video_path)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)
        stderr = r.stderr
        # 匹配 "1920x1080"
        wh_match = re.search(r"(\d{2,4})x(\d{2,4})", stderr)
        # 匹配 "30 fps" 或 "30000/1001"
        fps_match = re.search(r"(\d+(?:\.\d+)?)\s*fps", stderr)
        if not wh_match:
            return None
        w, h = wh_match.group(1), wh_match.group(2)
        fps = float(fps_match.group(1)) if fps_match else 30.0
        return {
            "width": int(w),
            "height": int(h),
            "fps": fps,
        }
    except Exception as e:
        log_warn(f"无法读视频信息: {e}")
        return None


# v1.3 默认标准参数
DEFAULT_FPS = 30
DEFAULT_RESOLUTIONS = {
    "16:9": (1280, 720),
    "9:16": (720, 1280),
    "1:1":  (720, 720),
    "4:3":  (960, 720),
    "3:4":  (720, 960),
    "custom": (1280, 720),  # custom 时用 16:9 兜底，aspect_ratio_custom 后续处理
}
DEFAULT_VIDEO_CODEC = "h264"
DEFAULT_AUDIO_CODEC = "aac"
DEFAULT_AUDIO_SAMPLE_RATE = 44100
DEFAULT_AUDIO_CHANNELS = 2
DEFAULT_PIXEL_FORMAT = "yuv420p"


def resolve_resolution(aspect_ratio="16:9", custom_resolution=None):
    """根据 aspect_ratio 算目标分辨率"""
    if aspect_ratio == "custom" and custom_resolution:
        w, h = custom_resolution
        return (w, h)
    return DEFAULT_RESOLUTIONS.get(aspect_ratio, DEFAULT_RESOLUTIONS["16:9"])


def video_normalize(
    in_path,
    output,
    fps=DEFAULT_FPS,
    resolution=None,                # tuple (w, h) 或 None（自动算）
    aspect_ratio="16:9",
    custom_resolution=None,
    video_codec=DEFAULT_VIDEO_CODEC,
    audio_codec=DEFAULT_AUDIO_CODEC,
    audio_sample_rate=DEFAULT_AUDIO_SAMPLE_RATE,
    audio_channels=DEFAULT_AUDIO_CHANNELS,
    pixel_format=DEFAULT_PIXEL_FORMAT,
):
    """视频参数归一化。

    Args:
        in_path: 输入视频
        output: 输出视频
        fps: 目标帧率
        resolution: (w, h) 元组，None 时按 aspect_ratio 自动算
        aspect_ratio: '16:9' / '9:16' / '1:1' / '4:3' / '3:4' / 'custom'
        custom_resolution: (w, h) 元组（aspect_ratio='custom' 时必填）
        video_codec: 'h264' / 'h265' / ...
        audio_codec: 'aac' / 'mp3' / ...
        audio_sample_rate: 44100 / 48000
        audio_channels: 1 / 2
        pixel_format: 'yuv420p' / 'yuv444p'

    Returns:
        output 路径(成功);None(失败)
    """
    log_section(f"video_normalize: {Path(in_path).name} → {fps}fps {resolution or aspect_ratio}")

    if not Path(in_path).exists():
        log_error(f"输入文件不存在: {in_path}")
        return None

    # 算分辨率
    if resolution is None:
        resolution = resolve_resolution(aspect_ratio, custom_resolution)

    # 读输入信息
    info = get_video_info_simple(in_path)
    if info is None:
        log_error(f"无法读取视频信息: {in_path}")
        return None

    src_w = info.get("width")
    src_h = info.get("height")
    src_fps = info.get("fps")
    log_info(f"源: {src_w}x{src_h}@{src_fps}fps → 目标: {resolution[0]}x{resolution[1]}@{fps}fps")

    ensure_dir(Path(output).parent)

    # 构造 vf 链: 缩放到目标分辨率 + fps 归一 + setsar=1
    target_w, target_h = resolution
    vf_chain = (
        f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
        f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black,"
        f"setsar=1,"
        f"fps={fps}"
    )

    # 构造 af 链: 重采样 + 声道归一
    af_chain = (
        f"aformat=sample_fmts=fltp:sample_rates={audio_sample_rate}:channel_layouts={'stereo' if audio_channels == 2 else 'mono'}"
    )

    # 编码器参数
    if video_codec == "h264":
        vcodec_args = ["-c:v", "libx264", "-preset", "medium", "-crf", "20"]
    elif video_codec == "h265":
        vcodec_args = ["-c:v", "libx265", "-preset", "medium", "-crf", "22"]
    else:
        vcodec_args = ["-c:v", video_codec]

    if audio_codec == "aac":
        acodec_args = ["-c:a", "aac", "-b:a", "128k"]
    elif audio_codec == "mp3":
        acodec_args = ["-c:a", "libmp3lame", "-b:a", "128k"]
    else:
        acodec_args = ["-c:a", audio_codec]

    # 拼完整命令
    cmd = [
        "-y",
        "-i", str(in_path),
        "-vf", vf_chain,
        "-af", af_chain,
        "-vsync", "cfr",      # 强制 CFR（避免 VFR）
        "-r", str(fps),       # 双重保险 fps
        *vcodec_args,
        "-ac", str(audio_channels),
        *acodec_args,
        "-pix_fmt", pixel_format,
        "-movflags", "+faststart",  # moov atom 前置
        str(output),
    ]

    try:
        run_ffmpeg(cmd)
    except Exception as e:
        log_error(f"归一化失败: {e}")
        return None

    new_info = get_video_info_simple(output)
    if new_info:
        log_info(f"输出: {output} ({new_info['width']}x{new_info['height']}@{new_info['fps']:.2f}fps)")
    else:
        log_info(f"输出: {output}")
    return str(output)


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 视频参数归一化（30fps / 标准分辨率 / h264 / aac）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
默认参数: 30fps / aspect_ratio 决定分辨率 / h264 / aac 44100 stereo / yuv420p

html UI 暂不允许配置（disabled），CLI 参数已留扩展位：
  %(prog)s --input v.mp4 --output v_norm.mp4 --fps 60 --resolution 3840x2160

意图层: 不作为独立 op，process_video() 末尾自动调用。
intent.json.output.fps / video_codec / audio_codec 是配置入口。
        """,
    )
    parser.add_argument("--input", required=True, help="输入视频")
    parser.add_argument("--output", required=True, help="输出视频")
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS, help=f"目标帧率（默认 {DEFAULT_FPS}）")
    parser.add_argument("--resolution", default=None,
                        help="目标分辨率 WxH（如 1920x1080），不指定按 aspect_ratio 自动算")
    parser.add_argument("--aspect-ratio", default="16:9",
                        help="目标比例（决定默认分辨率）：16:9 / 9:16 / 1:1 / 4:3 / 3:4 / custom")
    parser.add_argument("--custom-resolution", default=None,
                        help="自定义分辨率 WxH（aspect-ratio=custom 时必填）")
    parser.add_argument("--video-codec", default=DEFAULT_VIDEO_CODEC,
                        help=f"视频编码（默认 {DEFAULT_VIDEO_CODEC}）")
    parser.add_argument("--audio-codec", default=DEFAULT_AUDIO_CODEC,
                        help=f"音频编码（默认 {DEFAULT_AUDIO_CODEC}）")
    parser.add_argument("--audio-sample-rate", type=int, default=DEFAULT_AUDIO_SAMPLE_RATE,
                        help=f"音频采样率（默认 {DEFAULT_AUDIO_SAMPLE_RATE}）")
    parser.add_argument("--audio-channels", type=int, default=DEFAULT_AUDIO_CHANNELS,
                        help=f"音频声道数（默认 {DEFAULT_AUDIO_CHANNELS}）")
    parser.add_argument("--pixel-format", default=DEFAULT_PIXEL_FORMAT,
                        help=f"像素格式（默认 {DEFAULT_PIXEL_FORMAT}）")

    args = parser.parse_args()

    # 解析 resolution
    resolution = None
    if args.resolution:
        try:
            w, h = args.resolution.split("x")
            resolution = (int(w), int(h))
        except ValueError:
            log_error(f"--resolution 格式错误（应为 WxH，如 1920x1080）: {args.resolution}")
            sys.exit(1)

    custom_resolution = None
    if args.custom_resolution:
        try:
            w, h = args.custom_resolution.split("x")
            custom_resolution = (int(w), int(h))
        except ValueError:
            log_error(f"--custom-resolution 格式错误: {args.custom_resolution}")
            sys.exit(1)

    result = video_normalize(
        in_path=args.input,
        output=args.output,
        fps=args.fps,
        resolution=resolution,
        aspect_ratio=args.aspect_ratio,
        custom_resolution=custom_resolution,
        video_codec=args.video_codec,
        audio_codec=args.audio_codec,
        audio_sample_rate=args.audio_sample_rate,
        audio_channels=args.audio_channels,
        pixel_format=args.pixel_format,
    )

    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    safe_run(main)()