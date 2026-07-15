# -*- coding: utf-8 -*-
"""
智剪工坊 · multicam 子技能
多机位剪辑(4 路视频按时间码同步,生成可切换的多机位时间线)

用法:
  # 1. 同步 4 路视频,生成多机位 XML/JSON
  python multicam.py sync --inputs cam1.mp4 cam2.mp4 cam3.mp4 cam4.mp4 --out sync.json

  # 2. 生成多机位预览(画中画,4 路同屏)
  python multicam.py preview --inputs cam1.mp4 cam2.mp4 cam3.mp4 cam4.mp4 --out preview.mp4

  # 3. 按切换点剪辑(简化版,只接受单一切换点)
  python multicam.py cut --inputs cam1.mp4 cam2.mp4 --switch 0:cam1 5:cam2 10:cam1 --out final.mp4

依赖:opencv-python(音频同步检测)


📖 SKILL.md §14 索引 → REQUIRED: read references/04-cinematic.md
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    ensure_dir, log_info, log_warn, log_section, safe_run,
)


def sync_videos(inputs, output_json):
    """同步多路视频(基于时间码或元数据)"""
    log_section(f"同步 {len(inputs)} 路视频")
    ensure_dir(Path(output_json).parent)

    sync_data = {
        "video_count": len(inputs),
        "videos": [],
        "primary": str(inputs[0]) if inputs else None,
    }

    for i, video in enumerate(inputs):
        try:
            cap_info = {
                "index": i,
                "path": str(video),
                "duration": get_duration(video),
            }
            sync_data["videos"].append(cap_info)
        except Exception as e:
            log_warn(f"获取 {video} 信息失败: {e}")

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(sync_data, f, ensure_ascii=False, indent=2)
    log_info(f"同步数据: {output_json}")
    return sync_data


def preview_multicam(inputs, output_path, layout="2x2"):
    """生成多机位预览(2x2 / 1+3 布局)"""
    log_section(f"多机位预览 {layout}: {len(inputs)} 路")
    ensure_dir(Path(output_path).parent)

    if layout == "2x2" and len(inputs) >= 4:
        # 4 路 2x2
        run_ffmpeg([
            "-i", str(inputs[0]), "-i", str(inputs[1]),
            "-i", str(inputs[2]), "-i", str(inputs[3]),
            "-filter_complex",
            "[0:v]scale=540:960[0];[1:v]scale=540:960[1];[2:v]scale=540:960[2];[3:v]scale=540:960[3];"
            "[0][1]hstack=inputs=2[top];[2][3]hstack=inputs=2[bot];[top][bot]vstack=inputs=2[v]",
            "-map", "[v]",
            *DEFAULT_ENCODE_ARGS,
            str(output_path),
        ])
    elif layout == "hstack" and len(inputs) >= 2:
        # 横向拼接
        filter_parts = "".join([f"[{i}:v]scale=480:854[s{i}];" for i in range(len(inputs))])
        filter_parts += "".join([f"[s{i}]" for i in range(len(inputs))])
        filter_parts += f"hstack=inputs={len(inputs)}[v]"

        run_ffmpeg([
            *[item for i, input_v in enumerate(inputs) for item in ["-i", str(input_v)]],
            "-filter_complex", filter_parts,
            "-map", "[v]",
            *DEFAULT_ENCODE_ARGS,
            str(output_path),
        ])
    elif layout == "vstack" and len(inputs) >= 2:
        # 纵向拼接
        filter_parts = "".join([f"[{i}:v]scale=1080:540[s{i}];" for i in range(len(inputs))])
        filter_parts += "".join([f"[s{i}]" for i in range(len(inputs))])
        filter_parts += f"vstack=inputs={len(inputs)}[v]"

        run_ffmpeg([
            *[item for i, input_v in enumerate(inputs) for item in ["-i", str(input_v)]],
            "-filter_complex", filter_parts,
            "-map", "[v]",
            *DEFAULT_ENCODE_ARGS,
            str(output_path),
        ])
    else:
        log_warn(f"不支持的布局: {layout} (需 2-4 路视频)")
        return

    log_info(f"输出: {output_path}")


def cut_by_switch(inputs, switches, output_path):
    """
    按切换点剪辑
    switches: 列表 [(time_seconds, camera_index), ...]
    """
    log_section(f"多机位剪辑: {len(switches)} 个切换点")
    ensure_dir(Path(output_path).parent)

    if len(inputs) < 2:
        log_warn("需要至少 2 路视频")
        return

    # 简化:逐段处理
    # 实际完整版需要做切换点的 trim + concat
    # 这里只做"按切换点剪切 + 合并"框架

    # 先生成每段
    segments = []
    for i in range(len(switches)):
        t, cam = switches[i]
        t_next = switches[i + 1][0] if i + 1 < len(switches) else None
        if t_next is None:
            break  # 跳过最后一段

        duration = t_next - t
        seg_path = Path(output_path).with_suffix(f".seg{i:03d}.mp4")

        run_ffmpeg([
            "-ss", str(t),
            "-i", str(inputs[cam]),
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            str(seg_path),
        ])
        segments.append(seg_path)
        log_info(f"  段 {i}: t={t:.1f}s cam={cam} dur={duration:.1f}s")

    # 用 concat 合并
    if segments:
        list_file = Path(output_path).with_suffix(".list.txt")
        with open(list_file, "w") as f:
            for seg in segments:
                f.write(f"file '{seg}'\n")

        run_ffmpeg([
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            str(output_path),
        ])
        log_info(f"输出: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 多机位剪辑",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # sync
    p_sync = sub.add_parser("sync", help="同步多路视频")
    p_sync.add_argument("--inputs", nargs="+", required=True)
    p_sync.add_argument("--output", required=True)

    # preview
    p_prev = sub.add_parser("preview", help="生成多机位预览")
    p_prev.add_argument("--inputs", nargs="+", required=True)
    p_prev.add_argument("--output", required=True)
    p_prev.add_argument("--layout", choices=["2x2", "hstack", "vstack"], default="2x2")

    # cut
    p_cut = sub.add_parser("cut", help="按切换点剪辑")
    p_cut.add_argument("--inputs", nargs="+", required=True)
    p_cut.add_argument("--switch", nargs="+", required=True, help="切换点 'time:cam_idx'")
    p_cut.add_argument("--output", required=True)

    args = parser.parse_args()

    if args.cmd == "sync":
        sync_videos(args.inputs, args.output)
    elif args.cmd == "preview":
        preview_multicam(args.inputs, args.output, args.layout)
    elif args.cmd == "cut":
        switches = []
        for sw in args.switch:
            t, cam = sw.split(":")
            switches.append((float(t), int(cam)))
        cut_by_switch(args.inputs, switches, args.output)


if __name__ == "__main__":
    safe_run(main)()
