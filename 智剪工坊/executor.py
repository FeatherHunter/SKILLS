#!/usr/bin/env python3
"""
智剪工坊 Executor v0.7
======================

将 intent.json 翻译成 ffmpeg 命令，按 5 步粗加工流水线生成 00_智剪/粗加工/ 下的素材。

第一性原理（v0.7）：
1. 粗加工是实质工作，每步生成文件
2. 模板是工作流脚本（不是 config），由 AI 按 stage 引导用户
3. 用户主导决策，每 stage 用户点头
4. 单视频失败不退出主体，记入决策.md

5 步粗加工（详细见 SKILL.md §主体流程）：
  Step 1: 解析 + 自检 → 中间产物/自检报告.json
  Step 2: 单视频处理 → 单视频/video_{idx}.mp4 + profile + 单视频汇总.md
  Step 3: sequence 拼接 → 组合/seq_{name}.mp4
  Step 4: ASR 文字稿 → 文字稿/视频_{idx}.md + 全部.md
  Step 5: 决策报告 → 决策.md

对外入口：run_coarse(intent_path, workspace, log)
CLI 用法：python executor.py <intent.json> --workspace <path>

依赖：lib/asr.py (whisper 包装), lib/modify.py (改素材菜单)
对应设计：SKILL.md + 架构.md + 模板/<name>.yaml
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
    """用 ffmpeg -noautorotate -i 取视频时长 + 真实像素尺寸。

    重要：用 -noautorotate 拿真实像素（不应用 rotation metadata）。
    """
    info = {'duration': None, 'width': None, 'height': None}
    try:
        result = subprocess.run(
            ['ffmpeg', '-noautorotate', '-i', str(video_path), '-f', 'null', '-'],
            capture_output=True, text=True, timeout=30
        )
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


def _probe_duration(video_path):
    """快速探测视频时长（秒），不依赖 ffprobe。"""
    try:
        result = subprocess.run(
            ['ffmpeg', '-i', str(video_path), '-f', 'null', '-'],
            capture_output=True, text=True, timeout=30
        )
        m = re.search(r'Duration:\s*(\d+):(\d+):(\d+\.?\d*)', result.stderr)
        if m:
            h, mn, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
            return h * 3600 + mn * 60 + s
    except Exception:
        pass
    return None


# ========== Per-video 处理 ==========

def build_video_filter(ops, voice, input_duration=None, target_aspect='16:9'):
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
        return build_cut_middle_filter(ops['cut-middle'], target_w, target_h)

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

    # 7. ★ 横竖屏适配（pillarbox 方案）
    # 决策：竖屏源（1080x1920 或带 rotation metadata 的横屏像素）保持原 orientation，
    #       通过 scale+pad 加入左右黑边变为 16:9 横屏帧。**不旋转像素**也不传 rotation metadata。
    # 理由：transpose 会把 rotation metadata 也带过去，导致播放器再旋转回来变成竖屏。
    #       pillarbox 简单、稳定、符合 YouTube/B站标准 16:9 输出要求。
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


def build_cut_middle_filter(cm, target_w=1920, target_h=1080):
    """cut-middle: 把视频切成 [0:cut_start] + [cut_end:end] 两段拼接。

    每段都过 scale+pad 标准化到 16:9（pillarbox 方案，竖屏源保持原 orientation）。
    """
    cut_start = parse_time(cm.get('from', '0')) or 0
    cut_end = parse_time(cm.get('to', '0')) or 0
    if cut_end <= cut_start:
        return None, None

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
    """处理单个视频。返回 (output_path, success)。

    ★ Pillarbox 策略：竖屏源（1080x1920）保持原 orientation，通过 scale+pad 变成 16:9
        上下不动，左右加黑边。**绝不旋转**，避免 rotation metadata 让播放器二次旋转。
    """
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

    # 真实像素（用 -noautorotate + 解析 stderr）
    if not dry_run:
        info = get_video_info(input_path)
        input_duration = info['duration']
        input_w, input_h = info['width'], info['height']
    else:
        input_duration = 30.0
        input_w, input_h = 1920, 1080

    # Source is portrait? → 需要 pillarbox；landscape → 直接 fill
    is_portrait = bool(input_w and input_h and input_w < input_h)
    orientation = "竖屏(pillarbox)" if is_portrait else "横屏(fill)" if (input_w and input_h) else "?"

    if input_duration:
        log(f"  时长: {input_duration:.1f}s, 像素: {input_w}x{input_h}, {orientation}")

    # 目标分辨率
    target_resolutions = {
        '16:9': (1920, 1080),
        '9:16': (1080, 1920),
        '1:1': (1080, 1080),
        '4:3': (1440, 1080),
        '3:4': (1080, 1440),
    }
    target_w, target_h = target_resolutions.get(target_aspect, (1920, 1080))

    # ⚡ Fast Path: 无 op + voice keep + 像素匹配 → 直接复制
    # 竖屏源也可用 fast-path（虽然 fast-path 跳过了 scale+pad，但同样是 1920x1080 + 黑边
    # 会让 fast-path 失去意义。所以 fast-path 只在「无需任何处理」且像素已匹配时触发。）
    if (not has_any_op(ops) and voice == 'keep'
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

    # cut-middle 特殊情况
    if 'cut-middle' in ops and ops['cut-middle'].get('on') and not ('pin-range' in ops and ops['pin-range'].get('on')):
        fc, mappings = build_cut_middle_filter(ops['cut-middle'], target_w, target_h)
    else:
        fc, mappings = build_video_filter(
            ops, voice,
            input_duration=input_duration,
            target_aspect=target_aspect,
        )

    if fc is None:
        fc = f"[0:v]copy[v];[0:a]anullsrc=r=44100:cl=stereo[a]"
        mappings = ["[v]", "[a]"]

    # ★ 关键：-noautorotate 让输入不被自动旋转
    #     + -bsf:v "h264_metadata=rotate=0" 强制清除 H264 流中可能附带的 display orientation SEI
    # 这两个一起确保输出是「真·16:9 横屏」：像素无旋转 + 流标识无旋转
    cmd = ['ffmpeg', '-y', '-noautorotate', '-i', str(input_path)]
    cmd.extend(['-filter_complex', fc])
    for m in mappings:
        cmd.extend(['-map', m])
    cmd.extend(['-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23'])
    cmd.extend(['-bsf:v', 'h264_metadata=rotate=0'])  # 关键！清掉 rotation SEI
    cmd.extend(['-c:a', 'aac', '-b:a', '128k'])
    cmd.extend(['-max_interleave_delta', '100M'])
    cmd.extend(['-threads', '0'])
    cmd.append(str(output_path))

    log(f"  $ ffmpeg -noautorotate ... → {output_path.name}")
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
    """两个视频用 xfade 转场拼接。

    现在 per-video 输出已经是无 rotation metadata 的 1920x1080（pillarbox 后），
    所以这里只用 -r 30 保证 CFR，xfade 不会再维度冲突。
    """
    duration = transition.get('duration', 0.5) or 0.5
    ttype = transition.get('type', 'fade') or 'fade'

    a_dur = get_duration(a_path) if not dry_run else 10.0
    b_dur = get_duration(b_path) if not dry_run else 10.0
    offset = max(0, (a_dur or 10) - duration)

    fc = (
        f"[0:v][1:v]xfade=transition={ttype}:duration={duration}:offset={offset}[v];"
        f"[0:a][1:a]acrossfade=d={duration}[a]"
    )

    cmd = [
        'ffmpeg', '-y',
        '-noautorotate',
        '-r', '30',
        '-i', str(a_path),
        '-noautorotate',
        '-r', '30',
        '-i', str(b_path),
        '-filter_complex', fc,
        '-map', '[v]', '-map', '[a]',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
        '-c:a', 'aac', '-b:a', '128k',
        '-threads', '0',
        str(output_path)
    ]
    log(f"  $ xfade ({ttype} {duration}s)")
    if dry_run:
        log(f"    [DRY-RUN] 完整命令: {' '.join(str(c) for c in cmd)}")
        return output_path

    rc, _, err = run(cmd)
    if rc != 0:
        log(f"  ❌ xfade 失败: {(err or '')[:300]}")
        return output_path
    return output_path


def concatenate_simple(paths, output_path, dry_run, log):
    """无转场，简单拼接。所有 per-video 输出已是统一 1920x1080 无 rotation，
    优先 stream copy（毫秒级）。
    """
    if len(paths) == 1:
        if not dry_run:
            shutil.copy2(paths[0], output_path)
        return output_path

    list_file = output_path.parent / "_concat_list.txt"
    if not dry_run:
        with open(list_file, 'w') as f:
            for p in paths:
                f.write(f"file '{p}'\n")

    # ⚡ Fast Path: 流复制（同源同 codec，应该直接成功）
    copy_cmd = [
        'ffmpeg', '-y',
        '-noautorotate',
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

    # Fallback: 重编（理论上不会触发，因为 per-video 输出都一致）
    cmd = [
        'ffmpeg', '-y',
        '-noautorotate',
        '-r', '30',
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
        log(f"  ❌ concat 失败: {(err or '')[:300]}")
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


# ========== v0.7 粗加工 5 原子函数 + run_coarse 编排 ==========

# 输出目录约定（v0.7）
SINGLE_DIR = "单视频"        # 单视频处理结果
CHUNKS_DIR = "组合"          # sequence 拼好的组
TRANSCRIPTS_DIR = "文字稿"   # ASR 结果
INTERMEDIATE_DIR = "中间产物"  # log / profile / 汇总
DECISION_MD = "决策.md"


def step1_check_intent(intent_path, work_dir, log=None):
    """Step 1: 解析 intent.json + 自检。

    Returns:
        intent: dict
        anomalies: list[str]  异常清单（不抛错）
    """
    import json
    log = log or (lambda m: print(m))
    intent = json.loads(Path(intent_path).read_text(encoding="utf-8"))

    anomalies = []
    workspace = intent.get("_workspace", ".")
    videos = intent.get("videos", [])

    # 检查源文件
    missing = []
    for v in videos:
        if v.get("exclude"):
            continue
        f = v.get("file", "")
        if not (Path(workspace) / f).exists():
            missing.append(f)
    if missing:
        anomalies.append(f"源视频缺失 {len(missing)} 个: {missing[:3]}...")

    # 写自检报告
    report_path = Path(work_dir) / INTERMEDIATE_DIR / "自检报告.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps({
            "videos_count": len(videos),
            "excluded": sum(1 for v in videos if v.get("exclude")),
            "sequences_count": len(intent.get("sequences", [])),
            "missing_sources": missing,
            "anomalies": anomalies,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    log(f"  [Step 1] {len(videos)} videos, {len(anomalies)} anomalies")
    return intent, anomalies


def step2_process_videos(intent, work_dir, log=None):
    """Step 2: 遍历每个视频 → 单视频处理。

    Returns:
        profiles: list[dict]  每个视频的 profile
    """
    import json
    log = log or (lambda m: print(m))
    workspace = intent.get("_workspace", ".")
    videos = intent.get("videos", [])
    out_dir = Path(work_dir) / SINGLE_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    profiles = []
    for v in videos:
        if v.get("exclude"):
            continue
        # 调用现有 process_video，但 output 路径改为约定位置
        out_path = out_dir / f"video_{int(v.get('index', 0)):02d}.mp4"
        # 复用 process_video 逻辑（用 monkey patch 改 output 路径不优雅，
        # 这里直接调 process_video 然后移动）
        original_log_sink = []
        def capture_log(m): original_log_sink.append(m)
        # 调用 process_video，输出到 .zhijian_work 默认位置
        result_path, ok = process_video(
            v, Path(workspace),
            Path(work_dir) / "_tmp_process",
            dry_run=False, log=capture_log,
            target_aspect=intent.get("output", {}).get("aspect", "16:9")
        )
        if ok and result_path.exists():
            shutil.copy2(result_path, out_path)
            profile = {
                "index": v.get("index"),
                "source_file": v.get("file"),
                "applied_ops": [k for k, op in (v.get("ops") or {}).items()
                                if isinstance(op, dict) and op.get("on")],
                "voice_mode": v.get("voice", "keep"),
                "output_duration": _probe_duration(out_path),
                "output_path": str(out_path),
            }
            # 探源信息
            src_info = get_video_info(Path(workspace) / v.get("file", ""))
            profile["source_resolution"] = (
                f"{src_info['width']}x{src_info['height']}"
                if src_info.get("width") else "?"
            )
            profile["has_rotation_metadata"] = False  # 简化
            profiles.append(profile)
            log(f"  [Step 2] #{v.get('index')} → {out_path.name}")
        else:
            log(f"  [Step 2] #{v.get('index')} ❌ 失败（已记录到主流程异常）")

    # Step 2 汇总报告（A 决策）
    summary_path = Path(work_dir) / INTERMEDIATE_DIR / "单视频汇总.md"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8") as f:
        f.write("# 单视频处理汇总\n\n")
        f.write(f"共 {len(profiles)} 个视频处理完成\n\n")
        f.write("| # | 源文件 | 应用的 op | 源分辨率 | 输出时长 |\n")
        f.write("|---|--------|----------|---------|---------|\n")
        for p in profiles:
            f.write(f"| {p['index']} | {p['source_file']} | "
                    f"{p['applied_ops']} | {p['source_resolution']} | "
                    f"{p['output_duration']}s |\n")
    log(f"  [Step 2] 汇总报告: {summary_path}")

    return profiles


def step3_assemble_sequences(intent, work_dir, profiles, log=None):
    """Step 3: 遍历每个 sequence → 用 xfade 拼接 → 组合/seq_{name}.mp4。

    Returns:
        chunk_paths: dict[seq_name, output_path]
    """
    log = log or (lambda m: print(m))
    sequences = intent.get("sequences", [])
    out_dir = Path(work_dir) / CHUNKS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    chunk_paths = {}
    profile_by_idx = {p["index"]: p for p in profiles}

    for seq in sequences:
        name = seq.get("name", f"seq_{len(chunk_paths)}")
        indices = seq.get("videos", [])
        # 拼出每个视频的 单视频/ 路径
        single_paths = []
        for idx in indices:
            p = profile_by_idx.get(idx)
            if p:
                single_paths.append(Path(p["output_path"]))
            else:
                log(f"  [Step 3] {name}: 缺 video #{idx} 跳过")
        if not single_paths:
            continue

        # 用 concatenate_simple 简单拼（无转场）
        # TODO: 后续支持 per-adjacent 转场（用 xfade_concat 链）
        seq_out = out_dir / f"{name}.mp4"
        concatenate_simple(single_paths, seq_out, dry_run=False, log=log)
        if seq_out.exists():
            chunk_paths[name] = seq_out
            log(f"  [Step 3] {name} → {seq_out.name}")
    return chunk_paths


def step4_asr_transcripts(work_dir, profiles, log=None):
    """Step 4: 用 lib.asr 给每个 单视频出文字稿。

    Returns:
        transcript_paths: dict[video_idx, md_path]
    """
    log = log or (lambda m: print(m))
    from lib.asr import transcribe, merge_to_md

    out_dir = Path(work_dir) / TRANSCRIPTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    transcript_paths = {}
    for p in profiles:
        video_path = Path(p["output_path"])
        md_path = out_dir / f"视频_{p['index']:02d}.md"
        srt_path = out_dir / f"视频_{p['index']:02d}.srt"
        # ASR → SRT → 简单转 md
        if transcribe(video_path, srt_path):
            # 简化：直接 md（用文件本身标记位置）
            md_path.write_text(
                f"# 视频 {p['index']:02d} 文字稿\n\n"
                f"（源：{p['source_file']}）\n\n"
                f"SRT：{srt_path}\n",
                encoding="utf-8"
            )
            transcript_paths[p["index"]] = md_path
            log(f"  [Step 4] #{p['index']} → {md_path.name}")
        else:
            log(f"  [Step 4] #{p['index']} ❌ ASR 失败")
    # 合并
    merge_md = out_dir / "全部.md"
    merge_to_md(out_dir, merge_md)
    log(f"  [Step 4] 合并 → {merge_md.name}")
    return transcript_paths


def step5_decision_report(intent_path, work_dir, profiles,
                          anomalies=None, user_extras=None):
    """Step 5: 写决策.md（用 lib/modify.write_decision_report）。"""
    from lib.modify import write_decision_report
    output_md = Path(work_dir) / DECISION_MD
    return write_decision_report(
        intent_path, profiles, output_md,
        anomalies=anomalies or [],
        user_extras=user_extras or []
    )


def run_coarse(intent_path, workspace, log=None):
    """v0.7 粗加工编排：5 步流水线。

    Args:
        intent_path: intent.json 路径
        workspace: 工作区根目录
        log: 日志函数
    Returns:
        dict: {
            "single_videos": list[paths],
            "chunks": dict[name, path],
            "transcripts": dict[idx, path],
            "decision_md": path,
            "anomalies": list[str],
        }
    """
    import json
    log = log or (lambda m: print(m))
    work_dir = Path(workspace) / "00_智剪" / "粗加工"
    work_dir.mkdir(parents=True, exist_ok=True)

    log(f"=== 粗加工 v0.7: {intent_path} ===")

    # 把 workspace 注入 intent（让其他步骤能定位源文件）
    intent = json.loads(Path(intent_path).read_text(encoding="utf-8"))
    intent["_workspace"] = str(workspace)

    # Step 1
    intent, anomalies = step1_check_intent(intent_path, work_dir, log)

    # Step 2（单视频处理 — 失败不中断，记入 anomalies）
    profiles = step2_process_videos(intent, work_dir, log)
    failed_videos = [v for v in intent.get("videos", [])
                     if not v.get("exclude")
                     and not any(p["index"] == v.get("index") for p in profiles)]
    for fv in failed_videos:
        anomalies.append(f"video #{fv.get('index')} 处理失败（{fv.get('file')}）")

    # Step 3
    chunks = step3_assemble_sequences(intent, work_dir, profiles, log)

    # Step 4
    transcripts = step4_asr_transcripts(work_dir, profiles, log)

    # Step 5
    decision_md = step5_decision_report(intent_path, work_dir, profiles, anomalies)

    log(f"=== 粗加工完成: {work_dir} ===")
    return {
        "work_dir": str(work_dir),
        "single_videos": [p["output_path"] for p in profiles],
        "chunks": chunks,
        "transcripts": transcripts,
        "decision_md": str(decision_md),
        "anomalies": anomalies,
    }


def main():
    if len(sys.argv) < 2:
        print("用法: python executor.py <intent.json> [--workspace <path>] [--dry-run] [--step N]")
        sys.exit(1)

    intent_path = sys.argv[1]
    workspace = None
    dry_run = False
    step = None  # None = 全部 5 步

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == '--workspace' and i + 1 < len(args):
            workspace = args[i + 1]
            i += 2
        elif args[i] == '--dry-run':
            dry_run = True
            i += 1
        elif args[i] == '--step' and i + 1 < len(args):
            step = int(args[i + 1])
            i += 2
        else:
            i += 1

    # v0.7 默认走 run_coarse
    if workspace and not dry_run:
        # 注入 workspace 给 IntentExecutor
        import json
        intent = json.loads(Path(intent_path).read_text(encoding="utf-8"))
        intent["_workspace"] = workspace
        Path(intent_path).write_text(
            json.dumps(intent, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        result = run_coarse(intent_path, workspace, log=print)
        print(f"\n汇总:")
        print(f"  work_dir: {result['work_dir']}")
        print(f"  single_videos: {len(result['single_videos'])}")
        print(f"  chunks: {len(result['chunks'])}")
        print(f"  transcripts: {len(result['transcripts'])}")
        print(f"  decision_md: {result['decision_md']}")
        print(f"  anomalies: {len(result['anomalies'])}")
        return

    # 旧执行路径（保留兼容）
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
