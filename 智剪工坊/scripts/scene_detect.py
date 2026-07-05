# -*- coding: utf-8 -*-
"""
智剪工坊 · scene_detect 子技能
AI 场景检测(用 OpenCV 检测镜头切换)

用法:
  # 1. 只检测场景变化,输出 JSON
  python scene_detect.py --input in.mp4 --out scenes.json

  # 2. 检测 + 自动切割场景片段
  python scene_detect.py --input in.mp4 --out scenes/ --mode cut

依赖:opencv-python


📖 SKILL.md §14 索引 → REQUIRED: read references/09-ai-features.md
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    ensure_dir, log_info, log_warn, log_section, safe_run,
)


def detect_scenes(video_path, threshold=0.3, min_scene_len=1.0):
    """
    检测视频场景变化(基于直方图差异)
    threshold: 0-1,越大越不敏感
    min_scene_len: 最短场景长度(秒)
    """
    log_section(f"场景检测: {Path(video_path).name}")
    ensure_dir(Path(video_path).parent)

    try:
        import cv2
        import numpy as np
    except ImportError:
        log_warn("opencv-python 未安装")
        log_warn("安装: pip install opencv-python")
        return None

    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0

    log_info(f"FPS: {fps:.1f},总帧数: {total_frames},时长: {duration:.1f}s")

    scenes = []
    prev_hist = None
    frame_idx = 0
    last_scene_end = 0.0

    # 降采样:每 0.5s 取一帧(加快检测)
    sample_interval = max(1, int(fps * 0.5))

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % sample_interval == 0:
            # 转 HSV,计算直方图
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
            cv2.normalize(hist, hist)
            hist = hist.flatten()

            if prev_hist is not None:
                # 直方图差异
                diff = cv2.compareHist(hist.astype(np.float32), prev_hist.astype(np.float32), cv2.HISTCMP_CORREL)
                similarity = max(0, diff)  # 0-1,1 表示完全一样

                if (1 - similarity) > threshold:
                    # 检测到场景变化
                    t = frame_idx / fps
                    if t - last_scene_end >= min_scene_len:
                        scenes.append({
                            "start": round(last_scene_end, 2),
                            "end": round(t, 2),
                            "duration": round(t - last_scene_end, 2),
                            "score": round(1 - similarity, 3),
                        })
                        last_scene_end = t

            prev_hist = hist

        frame_idx += 1

    cap.release()

    # 最后一段
    if last_scene_end < duration:
        scenes.append({
            "start": round(last_scene_end, 2),
            "end": round(duration, 2),
            "duration": round(duration - last_scene_end, 2),
            "score": 0.0,
        })

    log_info(f"检测到 {len(scenes)} 个场景")
    return scenes


def save_scenes(scenes, output_json):
    """保存场景检测结果"""
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump({
            "scene_count": len(scenes),
            "scenes": scenes,
        }, f, ensure_ascii=False, indent=2)
    log_info(f"场景数据: {output_json}")


def cut_scenes(video_path, scenes, output_dir):
    """按场景切割视频"""
    log_section(f"按场景切割: {len(scenes)} 段")
    ensure_dir(output_dir)

    for i, scene in enumerate(scenes):
        start = scene["start"]
        duration = scene["duration"]
        output = Path(output_dir) / f"scene_{i:03d}.mp4"

        run_ffmpeg([
            "-ss", str(start),
            "-i", str(video_path),
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            str(output),
        ])
        log_info(f"  [{i+1}/{len(scenes)}] {start:.1f}s - {start+duration:.1f}s → {output.name}")


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · AI 场景检测",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("--output", required=True, help="输出 JSON 或场景目录")
    parser.add_argument("--threshold", type=float, default=0.3, help="检测阈值 0-1")
    parser.add_argument("--min-scene-len", type=float, default=1.0, help="最短场景长度(秒)")
    parser.add_argument("--mode", choices=["detect", "cut"], default="detect",
                       help="detect=只检测,cut=检测+切割")
    args = parser.parse_args()

    scenes = detect_scenes(args.input, args.threshold, args.min_scene_len)
    if not scenes:
        return

    if args.mode == "cut":
        # 检测 + 切割(场景 JSON 也保存)
        json_out = Path(args.output) / "scenes.json" if Path(args.output).is_dir() else Path(args.output).with_suffix(".json")
        save_scenes(scenes, str(json_out))
        cut_scenes(args.input, scenes, args.output)
    else:
        save_scenes(scenes, args.output)


if __name__ == "__main__":
    safe_run(main)()
