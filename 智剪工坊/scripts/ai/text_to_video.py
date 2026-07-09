# -*- coding: utf-8 -*-
"""
智剪工坊 · text_to_video 子技能
文字成片(从文案脚本生成视频)

支持 API:
  - matrix MCP(免费,mavis 内置,优先用)
  - 可灵(Kling,快手)
  - Vidu(生数科技)
  - Runway Gen-3
  - 本地 Stable Video Diffusion

用法:
  # 用 mmx matrix MCP(默认,免费)
  python text_to_video.py --prompt "A man running on a treadmill" --api matrix --out out.mp4

  # 用可灵 API
  python text_to_video.py --prompt "..." --api kling --out out.mp4

依赖:mmx matrix MCP(默认)/ requests(其他 API)


📖 SKILL.md §14 索引 → REQUIRED: read references/14-text-to-video.md
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from common import (
    ensure_dir, log_info, log_warn, log_error, log_section, safe_run,
)

# ============================================================
# 公共:调 mmx matrix MCP
# ============================================================

def _call_mavis_mcp(tool_name: str, payload: dict, timeout: int = 1500) -> dict:
    """通过 mavis CLI 调 matrix MCP 工具,返回解析后的 JSON"""
    mavis_bin = shutil.which("mavis") or r"C:\Users\辰辰洋洋\.mavis\bin\mavis.cmd"
    tmp_json = Path(tempfile.gettempdir()) / f"mmx_{abs(hash(json.dumps(payload, sort_keys=True)))%100000}.json"
    tmp_json.write_bytes(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    try:
        result = subprocess.run(
            [mavis_bin, "mcp", "call", "matrix", tool_name, "--file", str(tmp_json)],
            capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        log_error(f"mmx {tool_name} 超时 ({timeout}s)")
        sys.exit(1)
    if result.returncode != 0:
        log_error(f"mmx {tool_name} 失败: {result.stderr[:300]}")
        sys.exit(1)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        log_error(f"mmx 返回无法解析: {e}\n{result.stdout[:300]}")
        sys.exit(1)


def _download_to(url: str, local_path: Path) -> None:
    """下载 URL 到本地"""
    if url.startswith("http"):
        log_info(f"下载:{url[:80]}...")
        try:
            urllib.request.urlretrieve(url, local_path)
        except Exception as e:
            log_error(f"下载失败: {e}")
            sys.exit(1)
    else:
        # 已经是本地路径,直接复制
        src = Path(url)
        if not src.exists():
            log_error(f"源文件不存在: {src}")
            sys.exit(1)
        shutil.copy2(src, local_path)


# ============================================================
# 各种 API handlers
# ============================================================

def text_to_video_matrix(prompt, output_path, duration=5):
    """用 mmx matrix_gen_videos(text-to-video)"""
    log_section(f"mmx 文生视频: {prompt[:50]}")
    # mmx 支持 6s / 10s
    duration_sec = 6 if duration <= 6 else 10
    # 1080P 要求 duration=6,10s 必须 768P
    resolution = "1080P" if duration_sec == 6 else "768P"
    payload = {
        "requests": [{
            "prompt": prompt,
            "duration": duration_sec,
            "resolution": resolution,
        }]
    }
    log_info(f"调 mmx matrix_gen_videos: duration={duration_sec}s, resolution={resolution}")
    data = _call_mavis_mcp("matrix_gen_videos", payload, timeout=1500)
    # 解析 output_url(success_items[].output_url)
    output_url = None
    for item in data.get("success_items") or []:
        if item.get("output_url"):
            output_url = item["output_url"]
            break
    if not output_url:
        log_error(f"mmx 未返回 output_url: {data}")
        return False
    output_path = Path(output_path)
    ensure_dir(output_path.parent)
    _download_to(output_url, output_path)
    log_info(f"输出:{output_path} ({output_path.stat().st_size // 1024} KB)")
    return True


def text_to_video_kling(prompt, output_path, duration=5, config=None):
    """可灵 API(占位,需 KLING_API_KEY)"""
    log_section(f"可灵 文生视频: {prompt[:50]}")
    if not (config or {}).get("kling", {}).get("api_key") or os.environ.get("KLING_API_KEY"):
        log_warn("需要 Kling API key:$env:KLING_API_KEY='your_key'")
        return False
    log_warn("可灵 API 完整实现待补(占位)")
    return False


def text_to_video_vidu(prompt, output_path, duration=5, config=None):
    """Vidu API(占位)"""
    log_section(f"Vidu 文生视频: {prompt[:50]}")
    if not (config or {}).get("vidu", {}).get("api_key") or os.environ.get("VIDU_API_KEY"):
        log_warn("需要 Vidu API key:$env:VIDU_API_KEY='your_key'")
        return False
    log_warn("Vidu API 完整实现待补(占位)")
    return False


def text_to_video_runway(prompt, output_path, duration=5, config=None):
    """Runway API(占位)"""
    log_section(f"Runway 文生视频: {prompt[:50]}")
    if not (config or {}).get("runway", {}).get("api_key") or os.environ.get("RUNWAY_API_KEY"):
        log_warn("需要 Runway API key:$env:RUNWAY_API_KEY='your_key'")
        return False
    log_warn("Runway API 完整实现待补(占位)")
    return False


def text_to_video_svd(prompt, output_path, duration=4):
    """本地 SVD(占位,需 GPU)"""
    log_section(f"SVD 文生视频(本地): {prompt[:50]}")
    log_warn("SVD 需要 GPU + diffusers,本机未配置(占位)")
    return False


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 文字成片",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "API 选项:\n"
            "  matrix - mmx matrix MCP(免费,默认,推荐)\n"
            "  kling  - 可灵(快手,需 key)\n"
            "  vidu   - Vidu(生数科技,需 key)\n"
            "  runway - Runway Gen-3(需 key)\n"
            "  svd    - 本地 SVD(需 GPU,慢)\n"
        ),
    )
    parser.add_argument("--prompt", required=True, help="视频描述(prompt)")
    parser.add_argument("--api", choices=["matrix", "kling", "vidu", "runway", "svd"],
                       default="matrix", help="API(默认 matrix=免费)")
    parser.add_argument("--output", required=True)
    parser.add_argument("--duration", type=int, default=6, help="视频时长秒(mmx 强制 6/10)")
    args = parser.parse_args()

    handlers = {
        "matrix": text_to_video_matrix,
        "kling": text_to_video_kling,
        "vidu": text_to_video_vidu,
        "runway": text_to_video_runway,
        "svd": text_to_video_svd,
    }
    ok = handlers[args.api](args.prompt, args.output, args.duration)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    safe_run(main)()
