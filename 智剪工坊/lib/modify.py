# -*- coding: utf-8 -*-
"""
lib.modify — 改素材操作菜单（AI 改素材的快捷按钮）

设计决策（v0.7）：AI 改 00_智剪/粗加工/ 里的素材时，不应现场写 ffmpeg。
通过本菜单调用，命令简短可靠。

操作清单（菜单）：
    speed(video, factor)        变速
    trim(video, head, tail)     剪头尾
    cut(video, start, end)      切指定时间段（保留）
    mute(video)                 静音
    replace(sequence, index, new_video)  替换某段
    insert(sequence, index, new_video)    插入新段
    delete(sequence, index)      删除某段
    swap(sequence, i, j)         交换两段
    change_transition(sequence, index, type, duration)  改某段转场

所有函数返回 (output_path, success: bool)。
"""

import subprocess
import shutil
import re
from pathlib import Path

# 缩放/像素参数（与 process_one_video.py 一致）
TARGET_W, TARGET_H = 1920, 1080
PILLARBOX_FILTER = (
    f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,"
    f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2:black,setsar=1"
)
ROTATION_BSF = ["-bsf:v", "h264_metadata=rotate=0"]
NOAUTOROTATE = ["-noautorotate"]
THREADS = ["-threads", "0"]


def _run_ffmpeg(cmd, log=None):
    """运行 ffmpeg，捕获错误。"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0 and log:
            log(f"  ffmpeg 失败: {result.stderr[:200]}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        if log:
            log(f"  ffmpeg 超时")
        return False


# ========== 单视频操作 ==========

def speed(video, factor, output=None, log=None):
    """变速。factor=0.5 慢放 2x，factor=2 加速 2x。"""
    if not output:
        p = Path(video)
        output = p.parent / f"{p.stem}_x{factor}{p.suffix}"

    # atempo 链 0.5-2.0 范围
    af = factor
    chain = []
    while af > 2.0:
        chain.append("atempo=2.0")
        af /= 2.0
    while af < 0.5:
        chain.append("atempo=0.5")
        af *= 2.0
    chain.append(f"atempo={af:.4f}")
    atempo = ",".join(chain)

    fc = f"[0:v]setpts=(1/{factor})*PTS,{PILLARBOX_FILTER}[v];[0:a]{atempo}[a]"
    cmd = ["ffmpeg", "-y", *NOAUTOROTATE, "-i", str(video),
           "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
           *ROTATION_BSF,
           "-c:a", "aac", "-b:a", "128k", *THREADS, str(output)]
    ok = _run_ffmpeg(cmd, log)
    return output, ok


def trim(video, head=0, tail=0, output=None, log=None):
    """剪头尾（秒）。head=剪掉前 N 秒，tail=剪掉后 N 秒。"""
    if not output:
        p = Path(video)
        output = p.parent / f"{p.stem}_trim{head}_{tail}{p.suffix}"

    # 总时长 - 用 ffmpeg 探
    probe = subprocess.run(
        ["ffmpeg", "-i", str(video)], capture_output=True, text=True, timeout=30
    )
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", probe.stderr)
    if not m:
        return output, False
    dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    keep = max(0.1, dur - head - tail)

    fc = (
        f"[0:v]trim=start={head}:duration={keep},setpts=PTS-STARTPTS,{PILLARBOX_FILTER}[v];"
        f"[0:a]atrim=start={head}:duration={keep},asetpts=PTS-STARTPTS[a]"
    )
    cmd = ["ffmpeg", "-y", *NOAUTOROTATE, "-i", str(video),
           "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
           *ROTATION_BSF,
           "-c:a", "aac", "-b:a", "128k", *THREADS, str(output)]
    ok = _run_ffmpeg(cmd, log)
    return output, ok


def cut(video, start, end, output=None, log=None):
    """切指定时间段保留（秒）。"""
    if not output:
        p = Path(video)
        output = p.parent / f"{p.stem}_{start}_{end}{p.suffix}"

    keep = end - start
    fc = (
        f"[0:v]trim=start={start}:duration={keep},setpts=PTS-STARTPTS,{PILLARBOX_FILTER}[v];"
        f"[0:a]atrim=start={start}:duration={keep},asetpts=PTS-STARTPTS[a]"
    )
    cmd = ["ffmpeg", "-y", *NOAUTOROTATE, "-i", str(video),
           "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
           *ROTATION_BSF,
           "-c:a", "aac", "-b:a", "128k", *THREADS, str(output)]
    ok = _run_ffmpeg(cmd, log)
    return output, ok


def mute(video, output=None, log=None):
    """静音。"""
    if not output:
        p = Path(video)
        output = p.parent / f"{p.stem}_mute{p.suffix}"

    fc = f"[0:v]{PILLARBOX_FILTER}[v];[0:a]volume=0[a]"
    cmd = ["ffmpeg", "-y", *NOAUTOROTATE, "-i", str(video),
           "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
           *ROTATION_BSF,
           "-c:a", "aac", "-b:a", "128k", *THREADS, str(output)]
    ok = _run_ffmpeg(cmd, log)
    return output, ok


# ========== 序列操作 ==========

def replace(sequence, index, new_video, output=None, log=None):
    """替换 sequence 第 index 段为 new_video。"""
    from executor import build_video_filter
    from executor import process_video  # 暂留，详见 §C 重构
    # 实际实现：见 executor.py 序列处理（待重构）
    return _not_implemented("replace")


def insert(sequence, index, new_video, output=None, log=None):
    """在 sequence 第 index 段前插入 new_video。"""
    return _not_implemented("insert")


def delete(sequence, index, output=None, log=None):
    """删除 sequence 第 index 段。"""
    return _not_implemented("delete")


def swap(sequence, i, j, output=None, log=None):
    """交换 sequence 第 i 段和第 j 段。"""
    return _not_implemented("swap")


def change_transition(sequence, index, transition_type, duration=0.5, output=None, log=None):
    """改 sequence 第 index 段的转场。type=fade/slide/wipe/dissolve。"""
    return _not_implemented("change_transition")


def _not_implemented(op_name):
    """stub：占位说明，待 executor.py 重构完成后实现"""
    return None, False


# ========== 决策报告（Step 5 主体使用） ==========

def write_decision_report(intent_path, profiles, output_md, anomalies=None,
                         user_extras=None):
    """写决策.md。

    Args:
        intent_path: intent.json 路径
        profiles: list[dict] Step 2 生成的 profile 列表
        output_md: 输出 决策.md 路径
        anomalies: list[str] 异常情况报告
        user_extras: list[str] 用户在粗加工过程中提的额外要求
    """
    import json
    intent_path = Path(intent_path)
    output_md = Path(output_md)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    intent = json.loads(intent_path.read_text(encoding="utf-8"))

    lines = ["# 决策报告", ""]

    # 整体要求摘要
    lines += ["## 整体要求摘要", ""]
    output_cfg = intent.get("output", {})
    lines.append(f"- 输出比例: {output_cfg.get('aspect', '未指定')}")
    lines.append(f"- 输出分辨率: {output_cfg.get('resolution', '未指定')}")
    lines.append(f"- 视频总数: {len(intent.get('videos', []))}")
    lines.append(f"- sequence 数: {len(intent.get('sequences', []))}")
    lines.append(f"- 整体 voice 模式: {intent.get('voice', 'keep')}")
    lines.append("")

    # Per-video 处理摘要
    lines += ["## 单视频处理摘要", ""]
    for p in profiles:
        idx = p.get("index", "?")
        ops = p.get("applied_ops", [])
        src_res = p.get("source_resolution", "?")
        out_dur = p.get("output_duration", "?")
        rot = "有 rotation" if p.get("has_rotation_metadata") else "无 rotation"
        lines.append(
            f"- #{idx}: {p.get('source_file', '?')} → "
            f"ops={ops}, src={src_res}, dur={out_dur}s, {rot}"
        )
    lines.append("")

    # 异常情况
    if anomalies:
        lines += ["## 异常情况", ""]
        for a in anomalies:
            lines.append(f"- {a}")
        lines.append("")

    # 用户额外要求
    if user_extras:
        lines += ["## 用户补充要求", ""]
        for e in user_extras:
            lines.append(f"- {e}")
        lines.append("")

    output_md.write_text("\n".join(lines), encoding="utf-8")
    return output_md
