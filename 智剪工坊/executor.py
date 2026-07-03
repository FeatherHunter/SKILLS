#!/usr/bin/env python3
"""
智剪工坊 Executor v0.1
======================

将 intent.json 翻译成 ffmpeg 命令，输出最终 vlog。

第一性原理：
1. Per-video 独立处理（隔离错误）
2. Sequences 部分约束 + 自由视频
3. 每个 op 都有 SKILL.md 文档化的解析规则
4. 可观察（log + dry-run）

v0.1 范围：
- pin-range / cut-middle / trim-head / trim-tail / speed-up / slow-down
- mute / keep 声音
- 视频序列 + xfade 转场
- 输出 vlog_final.mp4

v0.2 范围（TODO）：
- cover AI 生图
- opening-text 文字卡
- insert-image 插图
- BGM 全局混音
- keep-with-filler-removed 去水词
"""

import json
import sys
import os
import subprocess
import shutil
import re
from pathlib import Path
from datetime import datetime


# ========== 时间解析 ==========

def parse_time(t):
    """解析多种时间格式到秒。失败返回 None。

    支持：
    - 数字（int/float） → 直接当秒
    - 'M:SS' / 'MM:SS' / 'H:MM:SS'
    - '15秒' / '15s' / '15'
    - '15分钟' / '15min'
    - '1分30秒'
    """
    if t is None:
        return None
    if isinstance(t, (int, float)):
        return float(t)
    if not isinstance(t, str):
        return None
    s = t.strip()
    if not s:
        return None

    # H:MM:SS 或 M:SS
    m = re.match(r'^(\d+):(\d{1,2})(?::(\d{1,2}))?$', s)
    if m:
        if m.group(3):
            h, mn, sc = int(m.group(1)), int(m.group(2)), int(m.group(3))
        else:
            h, mn, sc = 0, int(m.group(1)), int(m.group(2))
        return h * 3600 + mn * 60 + sc

    # 1分30秒
    m = re.match(r'^(\d+)分(?:(\d+)秒)?$', s)
    if m:
        return int(m.group(1)) * 60 + (int(m.group(2)) if m.group(2) else 0)

    # 1.5分钟
    m = re.match(r'^(\d+(?:\.\d+)?)\s*(?:分钟|分|min|m)$', s)
    if m:
        return float(m.group(1)) * 60

    # 15 / 15秒 / 15s
    m = re.match(r'^(\d+(?:\.\d+)?)\s*(?:秒|sec|s)?$', s, re.IGNORECASE)
    if m:
        return float(m.group(1))

    return None


# ========== 工具函数 ==========

def run(cmd, **kwargs):
    """执行命令并返回 (returncode, stdout, stderr)。"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError as e:
        return 1, '', str(e)


def get_video_info(video_path):
    """用 ffmpeg -noautorotate -i 取视频时长 + 真实像素尺寸 + 旋转标志。

    重要：源视频是手机竖屏拍摄时，文件带 -90 旋转 metadata。
    不用 -noautorotate 会被错读为 1920x1080 显示尺寸，掩盖真实的 1080x1920 像素。
    """
    info = {'duration': None, 'width': None, 'height': None, 'has_rotation': False}
    try:
        result = subprocess.run(
            ['ffmpeg', '-noautorotate', '-i', str(video_path), '-f', 'null', '-'],
            capture_output=True, text=True, timeout=30
        )
        # Duration
        m = re.search(r'Duration:\s*(\d+):(\d+):(\d+\.?\d*)', result.stderr)
        if m:
            h, mn, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
            info['duration'] = h * 3600 + mn * 60 + s
        # 找第一个 Video 流的真实像素尺寸
        # ffmpeg 输出形如：Stream #0:0(und): Video: h264, yuv420p(progressive), 1080x1920 [SAR ...]
        for stream_line in result.stderr.split('\n'):
            if ' Video:' in stream_line:
                m = re.search(r',\s*(\d{2,4})x(\d{2,4})\s*[,\[]', stream_line)
                if not m:
                    m = re.search(r'(\d{2,4})x(\d{2,4})\s', stream_line)
                if m:
                    info['width'] = int(m.group(1))
                    info['height'] = int(m.group(2))
                    break
        # 检测旋转 metadata
        if 'displaymatrix: rotation of' in result.stderr:
            info['has_rotation'] = True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return info


# 旧名兼容
def get_duration(video_path):
    return get_video_info(video_path).get('duration')


def has_any_op(ops):
    """检查 ops dict 是否有任意 op on=True。"""
    if not ops or not isinstance(ops, dict):
        return False
    return any(isinstance(v, dict) and v.get('on') for v in ops.values())


# ========== Per-video 处理 ==========

def build_video_filter(ops, voice, input_duration=None, target_aspect='16:9',
                       input_w=None, input_h=None):
    """为单个视频构建 ffmpeg filter_complex。

    Returns: (filter_complex_str, list_of_mappings) or (None, None) 表示无 op

    input_duration: 输入视频时长（秒）。trim-tail 需要这个来算绝对 end 时间。
    input_w/input_h: 源分辨率。匹配目标时跳过 scale，节约 50% 编码时间。
    target_aspect: 目标比例。强制所有视频缩放到该比例 + 黑边补齐。
    """
    # 目标分辨率
    target_resolutions = {
        '16:9': (1920, 1080),
        '9:16': (1080, 1920),
        '1:1': (1080, 1080),
        '4:3': (1440, 1080),
        '3:4': (1080, 1440),
    }
    target_w, target_h = target_resolutions.get(target_aspect, (1920, 1080))

    # 特殊情况：cut-middle 需要分割+拼接，结构不一样
    if 'cut-middle' in ops and ops['cut-middle'].get('on') and not ('pin-range' in ops and ops['pin-range'].get('on')):
        transpose_needed = bool(input_w and input_h and input_w < input_h)
        return build_cut_middle_filter(ops['cut-middle'], target_w, target_h,
                                       transpose_needed=transpose_needed)

    v_filters = []
    a_filters = []

    # 1. pin-range：先裁出时间窗口
    if 'pin-range' in ops and ops['pin-range'].get('on'):
        pr = ops['pin-range']
        start = parse_time(pr.get('from', '0')) or 0
        end = parse_time(pr.get('to', '0')) or 0
        if end <= start:
            end = start + 1  # 至少 1 秒
        v_filters.append(f"trim=start={start}:end={end},setpts=PTS-STARTPTS")
        a_filters.append(f"atrim=start={start}:end={end},asetpts=PTS-STARTPTS")

    # 2. trim-head / trim-tail
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
        elif sec > 0:
            pass

    # 3. speed
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

    # 4. 视觉：fade in/out
    if 'fade-in' in ops and ops['fade-in'].get('on'):
        sec = ops['fade-in'].get('sec', 1) or 1
        v_filters.append(f"fade=in:st=0:d={sec}")
        a_filters.append(f"afade=in:st=0:d={sec}")
    if 'fade-out' in ops and ops['fade-out'].get('on'):
        sec = ops['fade-out'].get('sec', 1) or 1
        v_filters.append(f"fade=out:st=0:d={sec}")
        a_filters.append(f"afade=out:st=0:d={sec}")

    # 5. 调色
    if 'color' in ops and ops['color'].get('on'):
        style = ops['color'].get('style', 'cinematic')
        color_map = {
            'warm': 'eq=saturation=1.15:gamma_r=1.05',
            'cool': 'eq=saturation=0.95:gamma_b=1.08',
            'cinematic': 'eq=contrast=1.1:saturation=0.9:gamma=0.95',
            'vintage': 'eq=contrast=0.95:saturation=0.85:gamma_r=1.1:gamma_b=0.9',
            'bw': 'hue=s=0',
            'high-contrast': 'eq=contrast=1.1:saturation=1.1',
        }
        if style in color_map:
            v_filters.append(color_map[style])

    # 6. 声音处理
    if voice in ('mute', 'bgm-only'):
        a_filters.append("volume=0")

    # 7. ★ 横竖屏适配
    # 手机竖屏拍摄：源是 1080x1920 带 -90 旋转 metadata（has_rotation=True）
    # 用 transpose 物理旋转 90° (CW)，再走 scale+pad
    # 真实横屏源（has_rotation=False，input_w > input_h）：直接走 scale+pad
    transpose_needed = False
    if input_w and input_h and input_w < input_h:
        transpose_needed = True
        # transpose=1 = 顺时针 90°
        v_filters.append("transpose=1")

    # 8. ★ 始终 scale + pad（保证 16:9 + 1920x1080 标准化）
    # 即使源就是 1920x1080，也加上以保证 SAR 归一。
    v_filters.append(
        f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
        f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black,setsar=1"
    )

    if not v_filters and not a_filters:
        return None, None

    v_chain = ",".join(v_filters) if v_filters else "copy"
    a_chain = ",".join(a_filters) if a_filters else "anullsrc"

    if v_filters and a_filters:
        fc = f"[0:v]{v_chain}[v];[0:a]{a_chain}[a]"
        return fc, ["[v]", "[a]"]
    elif v_filters:
        fc = f"[0:v]{v_chain}[v];anullsrc=r=44100:cl=stereo[a]"
        return fc, ["[v]", "[a]"]
    else:
        fc = f"[0:v]copy[v];[0:a]{a_chain}[a]"
        return fc, ["[v]", "[a]"]


def build_cut_middle_filter(cm, target_w=1920, target_h=1080, transpose_needed=False):
    """cut-middle: 把视频切成 [0:cut_start] + [cut_end:end] 两段拼接。"""
    cut_start = parse_time(cm.get('from', '0')) or 0
    cut_end = parse_time(cm.get('to', '0')) or 0
    if cut_end <= cut_start:
        return None, None

    # rotate+scale_pad：始终应用，保证两段尺寸一致 + 横屏
    if transpose_needed:
        rotoscale_v1 = f",transpose=1,scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black,setsar=1"
    else:
        rotoscale_v1 = f",scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black,setsar=1"
    rotoscale_v2 = rotoscale_v1

    fc = (
        f"[0:v]trim=0:{cut_start},setpts=PTS-STARTPTS{rotoscale_v1}[v1];"
        f"[0:v]trim={cut_end}:,setpts=PTS-STARTPTS{rotoscale_v2}[v2];"
        f"[v1][v2]concat=n=2:v=1:a=0[outv];"
        f"[0:a]atrim=0:{cut_start},asetpts=PTS-STARTPTS[a1];"
        f"[0:a]atrim={cut_end}:,asetpts=PTS-STARTPTS[a2];"
        f"[a1][a2]concat=n=2:v=0:a=1[outa]"
    )
    return fc, ["[outv]", "[outa]"]


def process_video(video, workspace, work_dir, dry_run, log, target_aspect='16:9'):
    """处理单个视频。返回 (output_path, success)。"""
    idx = video.get('index', '?')
    file = video.get('file', '')
    log(f"处理 #{idx}: {file}")

    input_path = workspace / file
    output_path = work_dir / f"video_{idx:02d}.mp4"

    if not input_path.exists():
        log(f"  ❌ 文件不存在: {input_path}")
        return output_path, False

    ops = video.get('ops', {}) or {}
    voice = video.get('voice', 'keep')

    # 一次 ffmpeg -noautorotate -i 同时拿时长、真实像素、旋转标志
    if not dry_run:
        info = get_video_info(input_path)
        input_duration = info['duration']
        input_w, input_h = info['width'], info['height']
        has_rotation = info['has_rotation']
    else:
        input_duration = 30.0
        input_w, input_h = 1080, 1920
        has_rotation = True

    # 真实像素 = 竖屏(1080x1920) → 要物理旋转（不含旋转 meta 的源直接当横屏）
    transpose_needed = bool(input_w and input_h and input_w < input_h)

    if input_duration:
        rot_str = "竖屏+旋转" if transpose_needed else "横屏" if (input_w and input_h) else "?"
        log(f"  时长: {input_duration:.1f}s, 像素: {input_w}x{input_h}, {rot_str}")

    # 目标分辨率
    target_resolutions = {
        '16:9': (1920, 1080),
        '9:16': (1080, 1920),
        '1:1': (1080, 1080),
        '4:3': (1440, 1080),
        '3:4': (1080, 1440),
    }
    target_w, target_h = target_resolutions.get(target_aspect, (1920, 1080))

    # ⚡ Fast Path: 无 op + 横屏 + voice keep + 像素匹配 → 直接复制
    # 竖屏源跳过 fast-path（必须经过 transpose + scale+pad 才符合 16:9）
    if (not has_any_op(ops) and voice == 'keep'
            and not transpose_needed
            and input_w == target_w and input_h == target_h):
        if dry_run:
            log(f"  ⚡ [DRY-RUN] fast-path: 无 op + 横屏+匹配 → 直接复制")
            return output_path, True
        try:
            shutil.copy2(input_path, output_path)
            sz = output_path.stat().st_size
            log(f"  ⚡ fast-path → {output_path.name} ({sz // 1024} KB, 跳过转码)")
            return output_path, True
        except OSError as e:
            log(f"  ⚠️ fast-path 失败 ({e}), 退回完整转码")

    # 处理 cut-middle 特殊情况（要用 transpose_needed 而非 source_matches）
    if 'cut-middle' in ops and ops['cut-middle'].get('on') and not ('pin-range' in ops and ops['pin-range'].get('on')):
        fc, mappings = build_cut_middle_filter(ops['cut-middle'], target_w, target_h,
                                               transpose_needed=transpose_needed)
    else:
        fc, mappings = build_video_filter(
            ops, voice,
            input_duration=input_duration,
            target_aspect=target_aspect,
            input_w=input_w, input_h=input_h,
        )
        # 给 build_video_filter 的 transpose 信号需要重新构造，或者改用 fc+mappings
        # 上面 build_video_filter 已经看 input_w/h 自动加 transpose

    if fc is None:
        # 无 op 且已过 fast-path 检测；当前路径不应到这里
        fc = f"[0:v]copy[v];[0:a]anullsrc=r=44100:cl=stereo[a]"
        mappings = ["[v]", "[a]"]

    cmd = ['ffmpeg', '-y', '-i', str(input_path)]
    cmd.extend(['-filter_complex', fc])
    for m in mappings:
        cmd.extend(['-map', m])
    cmd.extend(['-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23'])
    cmd.extend(['-c:a', 'aac', '-b:a', '128k'])
    cmd.extend(['-max_interleave_delta', '100M'])
    cmd.extend(['-threads', '0'])
    cmd.append(str(output_path))

    log(f"  $ ffmpeg ... -filter_complex ... -o {output_path.name}")
    if dry_run:
        log(f"    [DRY-RUN] 完整命令: {' '.join(str(c) for c in cmd)}")
        return output_path, True

    rc, _, err = run(cmd)
    if rc != 0:
        log(f"  ❌ ffmpeg 失败 (rc={rc}): {err[:300] if err else 'unknown'}")
        return output_path, False

    if output_path.exists():
        size = output_path.stat().st_size
        if size < 1000:
            log(f"  ⚠️  输出文件过小 ({size} bytes)，ffmpeg 可能静默失败")
            return output_path, False
    else:
        log(f"  ❌ 输出文件未生成")
        return output_path, False

    log(f"  ✓ → {output_path.name} ({output_path.stat().st_size // 1024} KB)")
    return output_path, True


# ========== 拼接 + 转场 ==========

def xfade_concat(a_path, b_path, transition, output_path, dry_run, log):
    """两个视频用 xfade 转场拼接。"""
    duration = transition.get('duration', 0.5) or 0.5
    ttype = transition.get('type', 'fade') or 'fade'

    a_dur = get_duration(a_path) if not dry_run else 10.0
    b_dur = get_duration(b_path) if not dry_run else 10.0
    offset = max(0, (a_dur or 10) - duration)

    cmd = [
        'ffmpeg', '-y',
        '-i', str(a_path),
        '-i', str(b_path),
        '-filter_complex',
        f"[0:v][1:v]xfade=transition={ttype}:duration={duration}:offset={offset}[v];"
        f"[0:a][1:a]acrossfade=d={duration}[a]",
        '-map', '[v]', '-map', '[a]',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
        '-c:a', 'aac', '-b:a', '128k',
        '-threads', '0',  # 用全部 CPU 核心
        str(output_path)
    ]
    log(f"  $ xfade ({ttype} {duration}s)")
    if dry_run:
        log(f"    [DRY-RUN] 完整命令: {' '.join(str(c) for c in cmd)}")
        return output_path

    rc, _, err = run(cmd)
    if rc != 0:
        log(f"  ❌ xfade 失败: {err[:300] if err else 'unknown'}")
        return output_path
    return output_path


def concatenate_simple(paths, output_path, dry_run, log):
    """无转场，简单拼接。优先 stream-copy（毫秒级），失败 fallback 重编。"""
    if len(paths) == 1:
        if not dry_run:
            shutil.copy2(paths[0], output_path)
        return output_path

    # 写 concat list
    list_file = output_path.parent / "_concat_list.txt"
    if not dry_run:
        with open(list_file, 'w') as f:
            for p in paths:
                # ffmpeg concat demuxer 需要单引号包裹路径以处理空格
                f.write(f"file '{p}'\n")

    # ⚡ Fast Path: 所有片段都是 H264 1920x1080（来自 process_video 标准化输出）
    # 直接 stream copy 拼接，不重新编码。concat demuxer + -c copy = 毫秒级
    copy_cmd = [
        'ffmpeg', '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', str(list_file),
        '-c', 'copy',
        '-movflags', '+faststart',
        str(output_path)
    ]
    log(f"  $ simple concat ({len(paths)} clips) — fast-path stream-copy")
    if not dry_run:
        rc, _, err = run(copy_cmd)
        list_file.unlink(missing_ok=True)
        if rc == 0 and output_path.exists() and output_path.stat().st_size > 1000:
            log(f"  ⚡ → {output_path.name} ({output_path.stat().st_size // 1024} KB, 流复制)")
            return output_path
        log(f"  ⚠️ stream-copy 失败 (rc={rc}): {(err or '')[:200]}，退回重编")

    # Fallback: 重编（极少触发，仅当片段 codec 不一致时）
    cmd = [
        'ffmpeg', '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', str(list_file),
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
        '-c:a', 'aac', '-b:a', '128k',
        '-threads', '0',
        str(output_path)
    ]
    log(f"  $ simple concat ({len(paths)} clips) — fallback 重编")
    if dry_run:
        return output_path

    rc, _, err = run(cmd)
    list_file.unlink(missing_ok=True)
    if rc != 0:
        log(f"  ❌ concat 失败: {err[:300] if err else 'unknown'}")
        return output_path
    return output_path


# ========== 主流程 ==========

class IntentExecutor:
    def __init__(self, intent_path, workspace=None, dry_run=False):
        self.intent_path = Path(intent_path)
        with open(self.intent_path) as f:
            self.intent = json.load(f)

        if workspace:
            self.workspace = Path(workspace)
        else:
            self.workspace = self.intent_path.parent
            # 如果 intent.json 在 _meta.workspace 指示的子目录，向上找
            ws_name = self.intent.get('_meta', {}).get('workspace', '')
            if ws_name and ws_name != self.workspace.name:
                # 用 workspace 名字作为子目录名
                candidate = self.workspace / ws_name
                if candidate.exists():
                    self.workspace = candidate

        self.work_dir = self.workspace / ".zhijian_work"
        self.dry_run = dry_run
        self.log_lines = []
        self.processed = {}  # video_index -> output_path

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line)
        self.log_lines.append(line)

    def execute(self):
        self.log("=" * 60)
        self.log("智剪工坊 Executor v0.1")
        self.log(f"Intent: {self.intent_path}")
        self.log(f"Workspace: {self.workspace}")
        self.log(f"Dry-run: {self.dry_run}")
        self.log("=" * 60)

        # 1. 工作目录
        if not self.dry_run:
            self.work_dir.mkdir(exist_ok=True)
        else:
            self.log(f"[DRY-RUN] 将创建工作目录: {self.work_dir}")

        # 2. 处理每个视频
        videos = self.intent.get('videos', [])
        excluded_count = sum(1 for v in videos if v.get('exclude'))
        self.log(f"\n共 {len(videos)} 个视频，{excluded_count} 个已排除")

        # 读目标比例
        target_aspect = self.intent.get('output', {}).get('aspect_ratio', '16:9') or '16:9'
        if self.intent.get('output', {}).get('aspect_ratio_custom'):
            target_aspect = self.intent['output']['aspect_ratio_custom']
        self.log(f"目标比例: {target_aspect}")

        for video in videos:
            if video.get('exclude'):
                self.log(f"  跳过 #{video.get('index', '?')}: {video.get('file', '?')}")
                continue
            idx = video.get('index')
            output_path, success = process_video(
                video, self.workspace, self.work_dir, self.dry_run, self.log,
                target_aspect=target_aspect,
            )
            if success:
                self.processed[idx] = output_path
            else:
                self.log(f"  ⚠️  处理失败，跳过 #{idx}")

        # 3. 构建顺序
        order = self._build_order()
        self.log(f"\n视频顺序: {order}")
        if not order:
            self.log("没有可用视频，结束。")
            return

        # 4. 拼接
        if len(order) == 1:
            output = self.processed[order[0]]
        else:
            output = self._concatenate_with_transitions(order)

        if output is None:
            self.log("❌ 拼接失败")
            return

        # 5. 输出
        final_path = self.workspace / "vlog_final.mp4"
        if not self.dry_run:
            shutil.copy2(output, final_path)
        self.log(f"\n✅ 完成: {final_path}")

        # 6. TODO v0.2: cover, opening-text, insert-image, BGM
        cover = self.intent.get('cover', {})
        ending = self.intent.get('ending', {})
        if cover.get('type') or ending.get('type'):
            self.log(f"\n[TODO v0.2] cover: {cover}, ending: {ending}")

    def _build_order(self):
        """构建最终视频顺序：序列内强制 + 自由视频。"""
        sequences = self.intent.get('sequences', [])
        used = set()
        order = []

        for seq in sequences:
            for v_idx in seq.get('videos', []):
                if v_idx in self.processed and v_idx not in used:
                    order.append(v_idx)
                    used.add(v_idx)

        # 自由视频
        for video in self.intent.get('videos', []):
            idx = video.get('index')
            if idx not in used and idx in self.processed:
                order.append(idx)
                used.add(idx)

        return order

    def _get_transitions(self):
        """从 sequences 提取转场字典 {(after, next): {type, duration}}。"""
        result = {}
        for seq in self.intent.get('sequences', []):
            videos = seq.get('videos', [])
            transitions = seq.get('transitions', []) or []
            for t in transitions:
                after = t.get('after')
                if after in videos:
                    idx = videos.index(after)
                    if idx < len(videos) - 1:
                        result[(after, videos[idx + 1])] = {
                            'type': t.get('type', 'fade') or 'fade',
                            'duration': t.get('duration', 0.5) or 0.5,
                        }
        return result

    def _concatenate_with_transitions(self, order):
        """按顺序拼接，序列内用 xfade，跨序列用简单 concat。"""
        # 检查所有相邻对是否都有 transition
        transitions = self._get_transitions()

        # 简化策略：按 order 串行拼接
        # 每对相邻：如果是序列内且有 transition，用 xfade
        # 否则用简单 concat
        # 实际实现：先按序列分组（连续同序列的拼接 xfade），跨序列简单 concat

        sequences = self.intent.get('sequences', [])
        # 找出每个 video 属于哪个 sequence
        seq_of = {}
        for s_idx, seq in enumerate(sequences):
            for v_idx in seq.get('videos', []):
                seq_of[v_idx] = s_idx

        # 按 order 切分：连续的同序列 ID 是一组
        groups = []
        current_group = []
        current_seq_idx = None
        for v_idx in order:
            s_idx = seq_of.get(v_idx, -1)  # -1 表示自由视频
            if s_idx == current_seq_idx:
                current_group.append(v_idx)
            else:
                if current_group:
                    groups.append((current_seq_idx, current_group))
                current_group = [v_idx]
                current_seq_idx = s_idx
        if current_group:
            groups.append((current_seq_idx, current_group))

        self.log(f"  分组: {[(s, len(g)) for s, g in groups]}")

        # 每个组内 xfade 拼接，组间 simple concat
        group_outputs = []
        for s_idx, group in groups:
            if len(group) == 1:
                group_outputs.append(self.processed[group[0]])
            else:
                # 组内 xfade
                paths = [self.processed[i] for i in group]
                current = paths[0]
                for i in range(1, len(paths)):
                    t = transitions.get((group[i-1], group[i]), {'type': 'fade', 'duration': 0.5})
                    out = self.work_dir / f"group_{i:02d}.mp4"
                    xfade_concat(current, paths[i], t, out, self.dry_run, self.log)
                    current = out
                group_outputs.append(current)

        if len(group_outputs) == 1:
            return group_outputs[0]

        # 跨组简单 concat
        final = self.work_dir / "vlog_concat.mp4"
        return concatenate_simple(group_outputs, final, self.dry_run, self.log)


def main():
    if len(sys.argv) < 2:
        print("用法: python executor.py <intent.json> [--workspace <path>] [--dry-run]")
        sys.exit(1)

    intent_path = sys.argv[1]
    workspace = None
    dry_run = False

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == '--workspace' and i + 1 < len(args):
            workspace = args[i + 1]
            i += 2
        elif args[i] == '--dry-run':
            dry_run = True
            i += 1
        else:
            i += 1

    executor = IntentExecutor(intent_path, workspace, dry_run=dry_run)
    try:
        executor.execute()
    except Exception as e:
        print(f"❌ 致命错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
