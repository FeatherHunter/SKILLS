"""lib.processing — v1.1 单视频处理 + 拼接共享逻辑

从 executor.py v0.7 抽出，适配 v1.1 路径约定（00_智剪/粗加工/）。

对外函数:
    build_video_filter(ops, voice, ...) -> (fc_str, mappings)
    build_cut_middle_filter(cm, target_w, target_h) -> (fc_str, mappings)
    process_video(video, workspace, output_dir, ...) -> (output_path, profile_dict, success)
    xfade_concat(a_path, b_path, transition, output_path, ...) -> output_path
    concatenate_simple(paths, output_path, ...) -> output_path
"""
import json
import re
import shutil
import subprocess
from pathlib import Path


# ========== 时间解析 ==========

def parse_time(t):
    """解析多种时间格式到秒。失败返回 None。"""
    if t is None:
        return None
    if isinstance(t, (int, float)):
        return float(t)
    if not isinstance(t, str):
        return None
    s = t.strip()
    if not s:
        return None

    m = re.match(r'^(\d+):(\d{1,2})(?::(\d{1,2}))?$', s)
    if m:
        if m.group(3):
            h, mn, sc = int(m.group(1)), int(m.group(2)), int(m.group(3))
        else:
            h, mn, sc = 0, int(m.group(1)), int(m.group(2))
        return h * 3600 + mn * 60 + sc

    m = re.match(r'^(\d+)分(?:(\d+)秒)?$', s)
    if m:
        return int(m.group(1)) * 60 + (int(m.group(2)) if m.group(2) else 0)

    m = re.match(r'^(\d+(?:\.\d+)?)\s*(?:分钟|分|min|m)$', s)
    if m:
        return float(m.group(1)) * 60

    m = re.match(r'^(\d+(?:\.\d+)?)\s*(?:秒|sec|s)?$', s, re.IGNORECASE)
    if m:
        return float(m.group(1))

    return None


# ========== 工具函数 ==========

def run(cmd, **kwargs):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError as e:
        return 1, '', str(e)


def get_video_info(video_path):
    """ffmpeg -noautorotate -i 拿真实像素。"""
    info = {'duration': None, 'width': None, 'height': None, 'rotation': 0}
    try:
        result = subprocess.run(
            ['ffmpeg', '-noautorotate', '-i', str(video_path), '-f', 'null', '-'],
            capture_output=True, text=True, timeout=30
        )
        m = re.search(r'Duration:\s*(\d+):(\d+):(\d+\.?\d*)', result.stderr)
        if m:
            h, mn, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
            info['duration'] = h * 3600 + mn * 60 + s
        for stream_line in result.stderr.split('\n'):
            if ' Video:' in stream_line:
                m = re.search(r',\s*(\d{2,4})x(\d{2,4})\s*[,\[]', stream_line)
                if not m:
                    m = re.search(r'(\d{2,4})x(\d{2,4})\s', stream_line)
                if m:
                    info['width'] = int(m.group(1))
                    info['height'] = int(m.group(2))
                    break
        m = re.search(r'displaymatrix: rotation of (-?\d+(?:\.\d+)?) degrees', result.stderr)
        if m:
            info['rotation'] = int(round(float(m.group(1))))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return info


def has_any_op(ops):
    if not ops or not isinstance(ops, dict):
        return False
    return any(isinstance(v, dict) and v.get('on') for v in ops.values())


# ========== Filter 构建 ==========

TARGET_RESOLUTIONS = {
    '16:9': (1920, 1080),
    '9:16': (1080, 1920),
    '1:1': (1080, 1080),
    '4:3': (1440, 1080),
    '3:4': (1080, 1440),
}


def build_rotation_filter(rotation):
    if rotation == 0:
        return ''
    if rotation == 90:
        return 'transpose=1,'
    if rotation in (-90, 270):
        return 'transpose=2,'
    if abs(rotation) == 180:
        return 'transpose=1,transpose=1,'
    return ''


def build_video_filter(ops, voice, input_duration=None, target_aspect='16:9', rotation=0):
    """为单个视频构建 ffmpeg filter_complex。"""
    target_w, target_h = TARGET_RESOLUTIONS.get(target_aspect, (1920, 1080))

    if 'cut-middle' in ops and ops['cut-middle'].get('on') and not ('pin-range' in ops and ops['pin-range'].get('on')):
        return build_cut_middle_filter(ops['cut-middle'], target_w, target_h)

    # 不旋转像素（v0.7 设计），只用 pillarbox + 清 metadata
    v_filters = []
    a_filters = []

    if 'pin-range' in ops and ops['pin-range'].get('on'):
        pr = ops['pin-range']
        start = parse_time(pr.get('from', '0')) or 0
        end = parse_time(pr.get('to', '0')) or 0
        if end <= start:
            end = start + 1
        v_filters.append(f"trim=start={start}:end={end},setpts=PTS-STARTPTS")
        a_filters.append(f"atrim=start={start}:end={end},asetpts=PTS-STARTPTS")

    if 'trim-head' in ops and ops['trim-head'].get('on'):
        sec = ops['trim-head'].get('sec', 0) or 0
        if sec > 0:
            v_filters.append(f"trim=start={sec},setpts=PTS-STARTPTS")
            a_filters.append(f"atrim=start={sec},asetpts=PTS-STARTPTS")
    if 'trim-tail' in ops and ops['trim-tail'].get('on'):
        sec = ops['trim-tail'].get('sec', 0) or 0
        if sec > 0 and input_duration and input_duration > sec:
            keep = input_duration - sec
            v_filters.append(f"trim=duration={keep},setpts=PTS-STARTPTS")
            a_filters.append(f"atrim=duration={keep},asetpts=PTS-STARTPTS")

    factor = None
    if 'speed-up' in ops and ops['speed-up'].get('on'):
        factor = ops['speed-up'].get('factor', 1.0)
    elif 'slow-down' in ops and ops['slow-down'].get('on'):
        factor = ops['slow-down'].get('factor', 1.0)
    if factor and factor != 1.0:
        v_filters.append(f"setpts=(1/{factor})*PTS")
        af = factor
        atempo_chain = []
        while af > 2.0:
            atempo_chain.append("atempo=2.0")
            af /= 2.0
        while af < 0.5:
            atempo_chain.append("atempo=0.5")
            af *= 2.0
        atempo_chain.append(f"atempo={af:.4f}")
        a_filters.append(",".join(atempo_chain))

    if voice in ('mute', 'bgm-only'):
        a_filters.append("volume=0")

    v_filters.append(
        f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
        f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black,setsar=1"
    )

    # 拼装 v 链：用户 op → standard pillarbox（不旋转）
    v_chain = ",".join(v_filters)
    # 注意: 用 [0:a]anull 而不是 anullsrc，因为 anullsrc + aac 编码在某些情况下会卡死
    a_chain = ",".join(a_filters) if a_filters else "[0:a]anull"

    fc = f"[0:v]{v_chain}[v];{a_chain}[a]"
    return fc, ["[v]", "[a]"]


def build_cut_middle_filter(cm, target_w=1920, target_h=1080):
    cut_start = parse_time(cm.get('from', '0')) or 0
    cut_end = parse_time(cm.get('to', '0')) or 0
    if cut_end <= cut_start:
        return None, None

    rotoscale = f",scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black,setsar=1"

    fc = (
        f"[0:v]trim=0:{cut_start},setpts=PTS-STARTPTS{rotoscale}[v1];"
        f"[0:v]trim={cut_end}:,setpts=PTS-STARTPTS{rotoscale}[v2];"
        f"[v1][v2]concat=n=2:v=1:a=0[outv];"
        f"[0:a]atrim=0:{cut_start},asetpts=PTS-STARTPTS[a1];"
        f"[0:a]atrim={cut_end}:,asetpts=PTS-STARTPTS[a2];"
        f"[a1][a2]concat=n=2:v=0:a=1[outa]"
    )
    return fc, ["[outv]", "[outa]"]


# ========== 处理单个视频 ==========

def process_video(video, workspace, output_path, target_aspect='16:9'):
    """处理单个视频。返回 (output_path, profile_dict, success)。

    Args:
        video: intent.videos[i] dict
        workspace: 工作区根目录
        output_path: 输出 mp4 路径
        target_aspect: 目标比例
    """
    idx = video.get('index', '?')
    file = video.get('file', '')
    src = workspace / file
    ops = video.get('ops', {}) or {}
    voice = video.get('voice', 'keep')

    if not src.exists():
        return output_path, {"index": idx, "error": "source missing"}, False

    output_path.parent.mkdir(parents=True, exist_ok=True)
    info = get_video_info(src)
    duration = info['duration']
    width, height = info['width'], info['height']
    rotation = info['rotation']
    is_portrait = bool(width and height and width < height)

    target_w, target_h = TARGET_RESOLUTIONS.get(target_aspect, (1920, 1080))

    # fast-path: 无 op + voice keep + 像素匹配 + 无 rotation → 直接复制
    # 重要：如果源带 rotation metadata，fast-path 会保留 rotation，导致播放器二次旋转
    # 所以 has_rotation_metadata=True 必须走完整转码清掉
    if (not has_any_op(ops) and voice == 'keep'
            and width == target_w and height == target_h
            and rotation == 0):
        try:
            shutil.copy2(src, output_path)
            return output_path, {
                "index": idx,
                "source_file": file,
                "source_resolution": f"{width}x{height}",
                "has_rotation_metadata": False,
                "rotation_applied": 0,
                "applied_ops": [],
                "output_resolution": f"{width}x{height}",
                "output_duration": duration,
                "voice_mode": voice,
                "output_path": str(output_path),
                "fast_path": True,
            }, True
        except OSError:
            pass  # 退回完整转码

    # cut-middle 特殊
    if 'cut-middle' in ops and ops['cut-middle'].get('on') and not ('pin-range' in ops and ops['pin-range'].get('on')):
        fc, mappings = build_cut_middle_filter(ops['cut-middle'], target_w, target_h)
    else:
        fc, mappings = build_video_filter(ops, voice,
                                          input_duration=duration,
                                          target_aspect=target_aspect,
                                          rotation=rotation)

    if fc is None:
        fc = "[0:v]copy[v];anullsrc=r=44100:cl=stereo[a]"
        mappings = ["[v]", "[a]"]

    cmd = ['ffmpeg', '-y', '-noautorotate', '-i', str(src)]
    cmd.extend(['-filter_complex', fc])
    for m in mappings:
        cmd.extend(['-map', m])
    cmd.extend(['-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23'])
    cmd.extend(['-bsf:v', 'h264_metadata=rotate=0'])
    cmd.extend(['-c:a', 'aac', '-b:a', '128k'])
    cmd.extend(['-max_interleave_delta', '100M'])
    cmd.extend(['-threads', '0'])
    cmd.append(str(output_path))

    rc, _, err = run(cmd, timeout=600)
    if rc != 0:
        return output_path, {
            "index": idx, "error": f"ffmpeg failed: {(err or '')[:200]}"
        }, False

    if not output_path.exists() or output_path.stat().st_size < 1000:
        return output_path, {
            "index": idx, "error": "output too small"
        }, False

    out_info = get_video_info(output_path)
    profile = {
        "index": idx,
        "source_file": file,
        "source_resolution": f"{width}x{height}",
        "has_rotation_metadata": rotation != 0,
        "rotation_applied": rotation,
        "applied_ops": [k for k, op in ops.items()
                        if isinstance(op, dict) and op.get('on')],
        "output_resolution": f"{out_info['width']}x{out_info['height']}",
        "output_duration": round(out_info['duration'], 2) if out_info['duration'] else None,
        "voice_mode": voice,
        "output_path": str(output_path),
    }
    return output_path, profile, True


# ========== 拼接 ==========

def xfade_concat(a_path, b_path, transition, output_path):
    """两个视频用 xfade 转场拼接。"""
    duration = transition.get('duration', 0.5) or 0.5
    ttype = transition.get('type', 'fade') or 'fade'

    a_info = get_video_info(a_path)
    b_info = get_video_info(b_path)
    a_dur = a_info['duration'] or 10
    b_dur = b_info['duration'] or 10
    offset = max(0, a_dur - duration)

    fc = (
        f"[0:v][1:v]xfade=transition={ttype}:duration={duration}:offset={offset}[v];"
        f"[0:a][1:a]acrossfade=d={duration}[a]"
    )

    cmd = [
        'ffmpeg', '-y', '-noautorotate', '-r', '30',
        '-i', str(a_path), '-noautorotate', '-r', '30',
        '-i', str(b_path),
        '-filter_complex', fc,
        '-map', '[v]', '-map', '[a]',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
        '-c:a', 'aac', '-b:a', '128k',
        '-threads', '0',
        str(output_path)
    ]

    rc, _, err = run(cmd, timeout=600)
    return output_path if rc == 0 else None


def concatenate_simple(paths, output_path):
    """无转场，简单拼接。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if len(paths) == 1:
        shutil.copy2(paths[0], output_path)
        return output_path

    list_file = output_path.parent / "_concat_list.txt"
    with open(list_file, 'w', encoding='utf-8') as f:
        for p in paths:
            f.write(f"file '{p}'\n")

    # 流复制快路径
    copy_cmd = [
        'ffmpeg', '-y', '-noautorotate',
        '-f', 'concat', '-safe', '0',
        '-i', str(list_file),
        '-c', 'copy', '-movflags', '+faststart',
        str(output_path)
    ]
    rc, _, err = run(copy_cmd, timeout=300)
    list_file.unlink(missing_ok=True)
    if rc == 0 and output_path.exists() and output_path.stat().st_size > 1000:
        return output_path

    # Fallback: 重编
    cmd = [
        'ffmpeg', '-y', '-noautorotate', '-r', '30',
        '-f', 'concat', '-safe', '0',
        '-i', str(list_file),
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
        '-c:a', 'aac', '-b:a', '128k',
        '-threads', '0',
        str(output_path)
    ]
    rc, _, err = run(cmd, timeout=600)
    list_file.unlink(missing_ok=True)
    return output_path if rc == 0 else None