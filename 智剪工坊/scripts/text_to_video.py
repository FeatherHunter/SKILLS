# -*- coding: utf-8 -*-
"""
智剪工坊 · text_to_video 子技能
文字成片(从文案脚本生成视频)

支持 API:
  - 可灵(Kling,快手)
  - Vidu(生数科技)
  - Runway Gen-3
  - 本地 Stable Video Diffusion

用法:
  # 用可灵 API 生成
  python text_to_video.py --prompt "A man running on a treadmill in a gym, cinematic" --api kling --out out.mp4

  # 用本地 SVD(慢但免费)
  python text_to_video.py --prompt "A man running" --api svd --out out.mp4

依赖:requests(API 调用)
"""
import argparse
import json
import os
import sys
import time
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    ensure_dir, log_info, log_warn, log_section, safe_run,
)


# API 配置(用户需要填自己的 key)
# 建议写到 D:\2Study\StudyNotes\SKILLS\智剪工坊\assets\config.json
DEFAULT_CONFIG = {
    "kling": {
        "api_key": os.environ.get("KLING_API_KEY", ""),
        "base_url": "https://api.klingai.com/v1",
    },
    "vidu": {
        "api_key": os.environ.get("VIDU_API_KEY", ""),
        "base_url": "https://api.vidu.studio/v1",
    },
    "runway": {
        "api_key": os.environ.get("RUNWAY_API_KEY", ""),
        "base_url": "https://api.runwayml.com/v1",
    },
    "svd": {
        "model_path": "stabilityai/stable-video-diffusion-img2vid",
    },
}


def load_config():
    """从环境变量或配置文件加载 API key"""
    config_path = Path(__file__).parent.parent / "assets" / "config.json"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_CONFIG


def text_to_video_kling(prompt, output_path, duration=5, config=None):
    """可灵 API"""
    log_section(f"可灵 文生视频: {prompt[:50]}")
    if not config.get("kling", {}).get("api_key"):
        log_warn("需要 Kling API key")
        log_warn("设置环境变量: $env:KLING_API_KEY='your_key'")
        return False
    # 实际调用:POST 到 /videos/generations
    # 简化:返回占位
    log_warn("可灵 API 调用需要真实实现,这里只占位")
    return False


def text_to_video_vidu(prompt, output_path, duration=5, config=None):
    """Vidu API"""
    log_section(f"Vidu 文生视频: {prompt[:50]}")
    if not config.get("vidu", {}).get("api_key"):
        log_warn("需要 Vidu API key")
        log_warn("设置环境变量: $env:VIDU_API_KEY='your_key'")
        return False
    log_warn("Vidu API 调用需要真实实现,这里只占位")
    return False


def text_to_video_runway(prompt, output_path, duration=5, config=None):
    """Runway Gen-3 API"""
    log_section(f"Runway 文生视频: {prompt[:50]}")
    if not config.get("runway", {}).get("api_key"):
        log_warn("需要 Runway API key")
        log_warn("设置环境变量: $env:RUNWAY_API_KEY='your_key'")
        return False
    log_warn("Runway API 调用需要真实实现,这里只占位")
    return False


def text_to_video_svd(prompt, output_path, duration=4):
    """本地 Stable Video Diffusion(慢但免费)"""
    log_section(f"SVD 文生视频(本地): {prompt[:50]}")
    log_warn("SVD 需要 GPU + diffusers + 大量显存(>8GB)")
    log_warn("安装: pip install diffusers transformers accelerate torch")
    log_warn("模型: stabilityai/stable-video-diffusion-img2vid")
    log_warn("当前为占位脚本,实际使用请参考 diffusers 官方文档")
    return False


def text_to_video_matrix(prompt, output_path, duration=5):
    """用 matrix MCP(免费,但目前只支持图生视频,不是文生)"""
    log_section(f"matrix 图生视频(占位): {prompt[:50]}")
    log_warn("matrix 当前主要支持图像和音乐生成")
    log_warn("文生视频需要 Kling/Vidu/Runway API,或者本地 SVD")
    return False


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 文字成片(从文案生成视频)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="API 选项:\n  kling  - 可灵(快手,推荐)\n  vidu   - Vidu(生数科技)\n  runway - Runway Gen-3\n  svd    - 本地 Stable Video Diffusion(慢但免费)\n  matrix - matrix MCP(图生视频,占位)\n\n示例:\n  %(prog)s --prompt 'A man running' --api kling --out out.mp4",
    )
    parser.add_argument("--prompt", required=True, help="视频描述(prompt)")
    parser.add_argument("--api", choices=["kling", "vidu", "runway", "svd", "matrix"],
                       default="matrix", help="API 选择")
    parser.add_argument("--out", required=True)
    parser.add_argument("--duration", type=int, default=5, help="视频时长(秒)")
    args = parser.parse_args()

    config = load_config()
    handlers = {
        "kling": text_to_video_kling,
        "vidu": text_to_video_vidu,
        "runway": text_to_video_runway,
        "svd": text_to_video_svd,
        "matrix": text_to_video_matrix,
    }

    ok = handlers[args.api](args.prompt, args.out, args.duration, config)

    if not ok:
        log_warn("未生成视频。如需使用,需要:")
        log_warn("  1. 注册对应 API 并获取 key")
        log_warn("  2. 在 assets/config.json 填入 key(或设环境变量)")
        log_warn("  3. 完善本脚本的 API 调用代码")


if __name__ == "__main__":
    safe_run(main)()
