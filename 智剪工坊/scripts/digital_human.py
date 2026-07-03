# -*- coding: utf-8 -*-
"""
智剪工坊 · digital_human 子技能
数字人(AI 生成虚拟人播报视频)

支持方案:
  - HeyGen API(海外,效果最好)
  - D-ID API(海外)
  - 国内:硅基智能 / 商汤如影 / 百度智能云数字人
  - 本地:SadTalkers(开源,但只做"口型驱动",不做"完整数字人")

用法:
  python digital_human.py --avatar avatar.jpg --audio voice.mp3 --out out.mp4 --api heygen
  python digital_human.py --avatar avatar.jpg --script "Hello world" --out out.mp4 --api heygen

依赖:requests(API 调用)
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    ensure_dir, log_info, log_warn, log_section, safe_run,
)


DEFAULT_CONFIG = {
    "heygen": {
        "api_key": os.environ.get("HEYGEN_API_KEY", ""),
        "base_url": "https://api.heygen.com",
    },
    "did": {
        "api_key": os.environ.get("DID_API_KEY", ""),
        "base_url": "https://api.d-id.com",
    },
    "sadtalker": {
        "model_dir": "",  # SadTalkers 仓库路径
    },
}


def load_config():
    config_path = Path(__file__).parent.parent / "assets" / "config.json"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_CONFIG


def digital_human_heygen(avatar, audio_or_script, output_path, config=None, voice="en-US-JennyNeural"):
    """HeyGen API(海外,效果最好)"""
    log_section(f"HeyGen 数字人: {Path(avatar).name}")
    if not config.get("heygen", {}).get("api_key"):
        log_warn("需要 HeyGen API key")
        log_warn("设置: $env:HEYGEN_API_KEY='your_key'")
        log_warn("注册: https://www.heygen.com/")
        return False
    log_warn("HeyGen API 调用需要完整实现,这里只占位")
    return False


def digital_human_did(avatar, audio_or_script, output_path, config=None):
    """D-ID API"""
    log_section(f"D-ID 数字人: {Path(avatar).name}")
    if not config.get("did", {}).get("api_key"):
        log_warn("需要 D-ID API key")
        log_warn("设置: $env:DID_API_KEY='your_key'")
        return False
    log_warn("D-ID API 调用需要完整实现,这里只占位")
    return False


def digital_human_sadtalker(avatar, audio, output_path, config=None):
    """本地 SadTalkers(只做口型驱动)"""
    log_section(f"SadTalkers 数字人(本地): {Path(avatar).name}")
    model_dir = config.get("sadtalker", {}).get("model_dir", "")
    if not model_dir:
        log_warn("需要 SadTalkers 模型路径")
        log_warn("克隆: https://github.com/OpenTalker/SadTalkers")
        log_warn("然后在 assets/config.json 配 sadtalker.model_dir")
        return False
    log_warn("SadTalkers 集成需要完整实现,这里只占位")
    return False


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 数字人(AI 虚拟人播报)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--avatar", required=True, help="头像图片(人脸)")
    parser.add_argument("--audio", help="音频文件")
    parser.add_argument("--script", help="文本脚本(会先用 TTS 合成音频)")
    parser.add_argument("--out", required=True)
    parser.add_argument("--api", choices=["heygen", "did", "sadtalker"], default="heygen",
                       help="API 选择(海外推荐 heygen)")
    args = parser.parse_args()

    if not args.audio and not args.script:
        log_warn("需要 --audio 或 --script")
        return

    audio = args.audio
    if not audio and args.script:
        # 用 edge-tts 合成
        audio_path = Path(args.out).with_suffix(".tts.mp3")
        log_info(f"TTS 合成: {args.script[:50]}")
        try:
            import edge_tts
            import asyncio

            async def gen():
                communicate = edge_tts.Communicate(args.script, "zh-CN-XiaoxiaoNeural")
                await communicate.save(str(audio_path))

            asyncio.run(gen())
            log_info(f"TTS 输出: {audio_path}")
            audio = str(audio_path)
        except ImportError:
            log_warn("edge-tts 未安装: pip install edge-tts")
            return

    config = load_config()
    handlers = {
        "heygen": digital_human_heygen,
        "did": digital_human_did,
        "sadtalker": digital_human_sadtalker,
    }

    ok = handlers[args.api](args.avatar, audio, args.out, config)

    if not ok:
        log_warn("未生成数字人视频。如需使用:")
        log_warn("  1. 注册对应 API 并获取 key")
        log_warn("  2. 在 assets/config.json 填入 key")
        log_warn("  3. 完善本脚本的 API 调用代码")


if __name__ == "__main__":
    safe_run(main)()
