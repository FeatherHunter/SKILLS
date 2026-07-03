# -*- coding: utf-8 -*-
"""
智剪工坊 · digital_human 子技能
AI 数字人(用真人头像 + 文字/音频 → 说话视频)

支持方案:
  - mmx matrix MCP(免费,subject 模式 + TTS 合成,优先用)
  - HeyGen / D-ID(海外,占位)
  - SadTalkers(本地,占位)

用法:
  # 用 mmx(默认,免费):头像 + 文案 → 数字人说话视频
  python digital_human.py --avatar avatar.jpg --script "大家好我是帅猎羽" --out out.mp4

  # 用 mmx:头像 + 现成音频
  python digital_human.py --avatar avatar.jpg --audio voice.mp3 --out out.mp4

依赖:mmx matrix MCP(默认)/ edge-tts(文案→音频)
"""
import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).parent))  # scripts/,让 import rewrite_audio 找得到
from common import (
    get_duration, ensure_dir, log_info, log_warn, log_error, log_section, safe_run,
)
from rewrite_audio import synthesize_via_matrix


# ============================================================
# mmx matrix 实现(优先)
# ============================================================

DIGITAL_HUMAN_PROMPT_TEMPLATE = (
    "A person speaking directly to camera, natural lip movements, "
    "engaging facial expressions, looking at viewer, professional lighting, "
    "talking head shot, smooth motion, high quality video"
)


def digital_human_matrix(avatar_path: str, audio_path: str, output_path: str):
    """
    用 mmx matrix_gen_videos (subject 模式) 生成数字人视频。
    流程:
      1. matrix_gen_videos(avatar + subject 引用)→ 静音人脸动视频
      2. ffmpeg 把视频和音频合起来
    """
    log_section(f"mmx 数字人: {Path(avatar_path).name}")
    if not Path(avatar_path).exists():
        log_error(f"头像不存在: {avatar_path}")
        return False
    if not Path(audio_path).exists():
        log_error(f"音频不存在: {audio_path}")
        return False

    output_path = Path(output_path)
    ensure_dir(output_path.parent)

    # Step 1: 调 mmx 生成人脸动视频
    mavis_bin = shutil.which("mavis") or r"C:\Users\辰辰洋洋\.mavis\bin\mavis.cmd"
    payload = {
        "requests": [{
            "prompt": DIGITAL_HUMAN_PROMPT_TEMPLATE,
            "input_image": {"file": str(avatar_path)},
            "reference_type": "subject",  # 关键:保持人脸一致
            "duration": 6,
            "resolution": "768P",  # 6s 必须 768P
        }]
    }
    log_info("调 mmx matrix_gen_videos subject 模式生成人脸动视频...")
    tmp_json = Path(tempfile.gettempdir()) / f"dh_args_{abs(hash(str(payload)))}.json"
    tmp_json.write_bytes(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    try:
        result = subprocess.run(
            [mavis_bin, "mcp", "call", "matrix", "matrix_gen_videos", "--file", str(tmp_json)],
            capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=1500,
        )
    except subprocess.TimeoutExpired:
        log_error("mmx matrix_gen_videos 超时")
        return False
    if result.returncode != 0:
        log_error(f"mmx 失败: {result.stderr[:300]}")
        return False

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        log_error(f"mmx 返回无法解析: {e}")
        return False

    silent_video_url = None
    for item in data.get("success_items") or []:
        if item.get("output_url"):
            silent_video_url = item["output_url"]
            break
    if not silent_video_url:
        log_error(f"mmx 未返回视频: {data}")
        return False

    # Step 2: 下载静音视频
    silent_video = Path(tempfile.gettempdir()) / f"dh_silent_{abs(hash(silent_video_url))%100000}.mp4"
    log_info(f"下载人脸视频: {silent_video_url[:80]}...")
    urllib.request.urlretrieve(silent_video_url, silent_video)

    # Step 3: ffmpeg 合音频
    log_info(f"合音频: {audio_path}")
    ffmpeg = shutil.which("ffmpeg") or r"D:\0Tools\Python313\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
    cmd = [
        ffmpeg, "-y",
        "-i", str(silent_video),
        "-i", str(audio_path),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        "-movflags", "+faststart",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="ignore", timeout=300)
    if result.returncode != 0:
        log_error(f"ffmpeg 合音频失败: {result.stderr[-300:]}")
        return False

    log_info(f"输出: {output_path} ({get_duration(output_path):.1f}s, "
             f"{output_path.stat().st_size // 1024} KB)")
    silent_video.unlink(missing_ok=True)
    return True


def script_to_audio(script: str, audio_path: Path) -> bool:
    """文案 → 音频(优先用 matrix TTS,fallback edge-tts)"""
    log_info(f"TTS 合成文案({len(script)} 字): {script[:50]}...")
    try:
        matrix_out = synthesize_via_matrix(script, "male-qn-qingse", speed=1.0)
        shutil.copy2(matrix_out, audio_path)
        log_info(f"TTS 输出: {audio_path}")
        return True
    except SystemExit:
        log_warn("matrix TTS 失败,试 edge-tts fallback")
    try:
        import edge_tts
        async def gen():
            communicate = edge_tts.Communicate(script, "zh-CN-XiaoxiaoNeural")
            await communicate.save(str(audio_path))
        asyncio.run(gen())
        return True
    except ImportError:
        log_error("edge-tts 也未装")
        return False


# ============================================================
# 其他 API(占位)
# ============================================================

def digital_human_heygen(avatar, audio, output_path, config=None):
    log_section(f"HeyGen 数字人: {Path(avatar).name}")
    if not (config or {}).get("heygen", {}).get("api_key") or os.environ.get("HEYGEN_API_KEY"):
        log_warn("需要 HeyGen API key:$env:HEYGEN_API_KEY='your_key'")
        return False
    log_warn("HeyGen 完整实现待补(占位)")
    return False


def digital_human_did(avatar, audio, output_path, config=None):
    log_section(f"D-ID 数字人: {Path(avatar).name}")
    if not (config or {}).get("did", {}).get("api_key") or os.environ.get("DID_API_KEY"):
        log_warn("需要 D-ID API key:$env:DID_API_KEY='your_key'")
        return False
    log_warn("D-ID 完整实现待补(占位)")
    return False


def digital_human_sadtalker(avatar, audio, output_path, config=None):
    log_section(f"SadTalkers 数字人(本地): {Path(avatar).name}")
    log_warn("SadTalkers 集成待补(占位)")
    return False


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 数字人(用真人头像 + 文案/音频)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--avatar", required=True, help="头像图片(人脸)")
    parser.add_argument("--audio", help="音频文件")
    parser.add_argument("--script", help="文本脚本(没填 audio 就 TTS 合成)")
    parser.add_argument("--out", required=True)
    parser.add_argument("--api", choices=["matrix", "heygen", "did", "sadtalker"],
                       default="matrix", help="API(默认 matrix=免费)")
    parser.add_argument("--voice", default="male-qn-qingse", help="TTS 声音(matrix 模式用)")
    args = parser.parse_args()

    if not args.audio and not args.script:
        log_error("需要 --audio 或 --script")
        sys.exit(1)

    # 处理 audio
    if not args.audio:
        # script → audio via TTS
        audio_path = Path(args.out).with_suffix(".tts.mp3")
        if not script_to_audio(args.script, audio_path):
            sys.exit(1)
        args.audio = str(audio_path)
        # 重新读 voice(避免 args 没有)
        # args.voice 在 main 里直接用

    ok = False
    if args.api == "matrix":
        ok = digital_human_matrix(args.avatar, args.audio, args.out)
    elif args.api == "heygen":
        ok = digital_human_heygen(args.avatar, args.audio, args.out)
    elif args.api == "did":
        ok = digital_human_did(args.avatar, args.audio, args.out)
    elif args.api == "sadtalker":
        ok = digital_human_sadtalker(args.avatar, args.audio, args.out)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    safe_run(main)()
