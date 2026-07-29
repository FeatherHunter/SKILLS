"""lib.processing — v1.1 单视频处理 + 拼接共享逻辑

从 executor.py v0.7 抽出，适配 v1.1 路径约定（00_智剪/粗加工/）。

对外函数(v3.0 · D7 修订):
    build_video_filter(video_ops, voice, ...) -> (fc_str, mappings)
        注:video_ops 是 videos[i].video_ops,不含 5 个 deprecated op(trim-head/tail/cut-middle/pin-range/target-duration)
    process_video(video, workspace, output_dir, ...) -> (output_path, profile_dict, success)
    xfade_concat(a_path, b_path, transition, output_path, ...) -> output_path
    concatenate_simple(paths, output_path, ...) -> output_path
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

# v1.3: video_normalize 集成需要 log_info / log_warn
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))
try:
    from common import log_info, log_warn
except ImportError:
    # common.py 不在同目录时 fallback 静默（不影响主功能）
    def log_info(msg: str) -> None: print(f"[INFO] {msg}")
    def log_warn(msg: str) -> None: print(f"[WARN] {msg}")


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
        result = subprocess.run(cmd, capture_output=True, text=True, errors='replace', **kwargs)
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError as e:
        return 1, '', str(e)


def get_video_info(video_path):
    """ffmpeg -noautorotate -i 拿真实像素。"""
    info = {'duration': None, 'width': None, 'height': None, 'rotation': 0}
    try:
        result = subprocess.run(
            ['ffmpeg', '-noautorotate', '-i', str(video_path), '-f', 'null', '-'],
            capture_output=True, text=True, errors='replace', timeout=30
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
    """根据 displaymatrix rotation 值返回 counter-rotate 的 transpose filter。

    ffmpeg displaymatrix 的 rotation 值定义（从原始像素到显示效果的旋转）：
      -90° → 手机竖屏拍（sensor横，像素横向，metadata 告诉播放器逆时针转90°显示）
      +90° → 手机竖屏拍（sensor横，像素横向，metadata 告诉播放器顺时针转90°显示）
     180° → 上下颠倒

    counter-rotate（抵消 metadata 旋转，让像素本身变正确方向）：
      -90°（metadata 逆时针90°）→ transpose=1（顺时针90°）抵消
      +90°（metadata 顺时针90°）→ transpose=2（逆时针90°）抵消
      180° → transpose=1,transpose=1（180°）
    """
    if rotation == 0:
        return ''
    if rotation == 90:
        return 'transpose=2,'
    if rotation in (-90, 270):
        return 'transpose=1,'
    if abs(rotation) == 180:
        return 'transpose=1,transpose=1,'
    return ''


def build_video_filter(ops, voice, input_duration=None, target_aspect='16:9',
                       rotation=0, aspect_handling='aspect-fit'):
    """为单个视频构建 ffmpeg filter_complex。
    v3.0:ops 是 video_ops(整段 op)。5 个该消失的 op(trim-head/tail/cut-middle/pin-range/target-duration)
    不应出现在此处(改由 time_segments 边界表达,D7)。

    aspect_handling:
      - 'aspect-fill': 旋转并填满，内容最大显示（可能裁切边缘）
      - 'aspect-fit':  保持原始显示方向（不旋转），加黑边适配目标比例
    """
    # v3.0 防御:assert 这 5 个 deprecated op 不在 video_ops 里
    deprecated_in_video_ops = [op for op in ['trim-head', 'trim-tail', 'cut-middle', 'pin-range', 'target-duration']
                               if ops.get(op)]
    if deprecated_in_video_ops:
        raise ValueError(
            f"video_ops 包含已废弃 op {deprecated_in_video_ops} (D7)。"
            f"改由 time_segments 边界表达。"
        )

    target_w, target_h = TARGET_RESOLUTIONS.get(target_aspect, (1920, 1080))

    # cut-middle 兼容层已删除(D7):build_video_filter 入口 assert 阻止
    # 5 个 deprecated op 出现

    # 旋转处理（两模式差异在 scale/pad 策略，不在 counter-rotate）
    # - rotation≠0 → 永远 counter-rotate（让像素变正确方向）
    # - rotation=0  → 不旋转（横屏源像素方向已是正确的）
    # 然后：
    #   aspect-fill → scale 填满（force_original_aspect_ratio=increase，可能裁切）
    #   aspect-fit  → scale 适配（force_original_aspect_ratio=decrease）+ pad 黑边
    if rotation != 0:
        rot_filter = build_rotation_filter(rotation)
    else:
        rot_filter = ''
    v_filters = []
    a_filters = []

    # D7:trim-head / trim-tail / cut-middle / pin-range / target-duration 不再在 video_ops
    # 语义改由 time_segments 边界表达(在 process_single_video 单独处理)
    # build_video_filter 入口已 assert 阻止这 5 个 op 出现
    # 这里不再有任何 5-op 的处理代码

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

    # v1.2: 单视频淡入淡出（fade-in / fade-out op）
    # 位置: 在 trim/cut/speed 之后、scale/pad 之前
    # 理由: trim 切过的视频时长变了,fade 必须基于"剩余时长"算;
    #       scale 不影响时长,放后面不影响 fade 时长。
    fade_in_sec = 0
    fade_out_sec = 0
    if 'fade-in' in ops and ops['fade-in'].get('on'):
        fade_in_sec = float(ops['fade-in'].get('sec', 1) or 1)
    if 'fade-out' in ops and ops['fade-out'].get('on'):
        fade_out_sec = float(ops['fade-out'].get('sec', 1) or 1)

    if fade_in_sec > 0 or fade_out_sec > 0:
        # 在末尾拼 fade filter;基于 input_duration 算 fade-out 起点
        # 注意: 此时 v_filters 还没拼 scale/pad,所以这里只是标记,真正拼在最后
        pass  # 在下面 v_chain 组装时统一处理

    if aspect_handling == 'aspect-fill':
        # 填满：scale 强制填满目标，可能裁切，无黑边
        v_filters.append(f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase:force_divisible_by=2,setsar=1")
    else:
        # 适配：scale 缩放适配，加黑边居中（aspect-fit 默认行为）
        v_filters.append(
            f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
            f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black,setsar=1"
        )

    # v1.2: 拼装前应用 fade-in/fade-out
    # 用 afade 在 a 链末尾叠加 fade;v 用 fade 在 v_filters 末尾追加
    if fade_in_sec > 0 or fade_out_sec > 0:
        if fade_in_sec > 0:
            v_filters.append(f"fade=t=in:st=0:d={fade_in_sec}")
            a_filters.append(f"afade=t=in:st=0:d={fade_in_sec}")
        if fade_out_sec > 0:
            # fade-out 起点: input_duration - sec (基于原始时长)
            # 注意: trim/cut/speed 之后时长可能变了,但 input_duration 是原始时长,
            # 需要在 trim 之后用实际剩余时长。简化:用 input_duration 估算,
            # 偏差<0.5s 一般肉眼不可见。如果要精确,需 trim 完之后用 get_duration 算。
            fade_out_start = max(0, (input_duration or 0) - fade_out_sec)
            v_filters.append(f"fade=t=out:st={fade_out_start}:d={fade_out_sec}")
            a_filters.append(f"afade=t=out:st={fade_out_start}:d={fade_out_sec}")

    # 拼装 v 链: counter-rotate → 用户 op → scale/pad

    v_chain = (rot_filter + ",".join(v_filters)) if v_filters else rot_filter
    # 注意: 用 [0:a]anull 而不是 anullsrc，因为 anullsrc + aac 编码在某些情况下会卡死
    a_chain = ",".join(a_filters) if a_filters else "[0:a]anull"

    fc = f"[0:v]{v_chain}[v];{a_chain}[a]"
    return fc, ["[v]", "[a]"]


    if not output_path.exists() or output_path.stat().st_size < 1000:
        return output_path, {
            "index": idx, "error": "output too small"
        }, False

    # v1.3: 自动调 video_normalize 归一化参数（解决多视频拼接 fps/分辨率不一致 bug）
    # 默认参数: 30fps, 1280x720 (按 aspect_ratio), h264, aac 44100 stereo, yuv420p
    # 用户可通过 intent.json.output.fps / video_codec / audio_codec 配置（暂未启用 html UI）
    try:
        import sys
        scripts_path = Path(__file__).parent.parent / "scripts"
        if str(scripts_path) not in sys.path:
            sys.path.insert(0, str(scripts_path))
        from video_normalize import video_normalize
        from video_normalize import DEFAULT_FPS as NORM_FPS

        # 临时输出: 把归一化写到 .norm.mp4,然后替换原文件
        norm_path = output_path.with_suffix(".norm.mp4")
        target_aspect = video.get('aspect_ratio', '16:9')  # 优先用 video 自身的 aspect
        if 'output' in video:
            # 若 video dict 含 output 信息(少见),优先
            target_aspect = video['output'].get('aspect_ratio', target_aspect)

        norm_result = video_normalize(
            in_path=str(output_path),
            output=str(norm_path),
            fps=NORM_FPS,
            aspect_ratio=target_aspect,
        )
        if norm_result and norm_path.exists():
            # 替换原 output_path
            import shutil
            shutil.move(str(norm_path), str(output_path))
            log_info(f"  ✓ 已归一化: {output_path.name} → 30fps / 标准参数")
    except Exception as e:
        log_warn(f"video_normalize 失败（不影响主产物）: {e}")

    # v1.1: ffmpeg 编码后自动 patch tkhd matrix，清 displaymatrix metadata
    # 解决: ffmpeg 编码时保留 source 的 displaymatrix，导致输出仍带旋转标签
    try:
        from patch_mp4_rotation import patch_mp4_rotation as _patch
        _patch(output_path)
    except Exception as e:
        # patch 失败不影响主流程（ffmpeg 已成功），只记录警告
        print(f'   ⚠️ patch tkhd 失败（不影响主产物）: {e}')

    out_info = get_video_info(output_path)
    # v3.0:记录 time_segments 信息到 profile(供 stage2 编排层参考)
    segments_summary = []
    for seg in time_segments:
        if seg.get('ops'):
            segments_summary.append({
                "id": seg.get('id'),
                "label": seg.get('label', ''),
                "start_sec": seg.get('start_sec'),
                "end_sec": seg.get('end_sec'),
                "ops": [k for k, op in seg.get('ops', {}).items()
                        if isinstance(op, dict) and op.get('on')]
            })
    profile = {
        "index": idx,
        "source_file": file,
        "source_resolution": f"{width}x{height}",
        "has_rotation_metadata": rotation != 0,
        "rotation_applied": rotation,
        "applied_ops": [k for k, op in ops.items()
                        if isinstance(op, dict) and op.get('on')],
        "applied_segment_ops": segments_summary,
        "output_resolution": f"{out_info['width']}x{out_info['height']}",
        "output_duration": round(out_info['duration'], 2) if out_info['duration'] else None,
        "voice_mode": voice,
        "output_path": str(output_path),
    }
    return output_path, profile, True


# ========== 拼接 ==========

# ========== 智剪工坊-意图编辑.html 9 种 type → ffmpeg xfade 合法名 ==========
# 与 scripts/video_xfade.py TRANSITION_MAP 保持一致;
# step3 这里直接复用,避免 import 跨层级。
_TRANSITION_MAP = {
    "none":        None,         # 短路
    "cut":         None,         # 短路
    "fade":        "fade",
    "dissolve":    "dissolve",
    "wipe-left":   "wipeleft",
    "wipe-right":  "wiperight",
    "slide-up":    "slideup",
    "zoom-in":     "zoomin",
    "blur":        "hblur",
}


def xfade_concat(a_path, b_path, transition, output_path):
    """两个视频用转场拼接。

    v1.2 修订:
      - type='none' / 'cut' / 缺失 → 走硬切(concatenate_simple,不调 xfade)
      - 9 种意图 type 全部支持;自动映射到 ffmpeg xfade 合法名
        (e.g. 'wipe-left' → 'wipeleft')
      - 不在 9 种枚举里的 type → 透传给 ffmpeg(fail-loud)
    """
    ttype = transition.get('type', None)

    # BUGFIX (智剪工坊 v1.1.1): type='none' 或缺失 → 硬切(零猜测)
    # v1.2 增补: type='cut' 也走硬切(意图等价,ffmpeg xfade 不支持)
    if ttype in (None, 'none', 'cut'):
        logger = __import__('logging').getLogger(__name__)
        logger.debug(f"xfade_concat: type={ttype!r} → 走硬切 (concatenate_simple)")
        return concatenate_simple([a_path, b_path], output_path)

    # v1.2: 意图名 → ffmpeg 合法名
    if ttype in _TRANSITION_MAP:
        ffmpeg_t = _TRANSITION_MAP[ttype]
        if ffmpeg_t is None:
            # 防御性:已在上面短路,不会到这
            return concatenate_simple([a_path, b_path], output_path)
    else:
        # 不在 9 种枚举 → 透传(允许高级用户传 ffmpeg 原生名)
        ffmpeg_t = ttype

    duration = transition.get('duration', 0.5) or 0.5

    a_info = get_video_info(a_path)
    b_info = get_video_info(b_path)
    a_dur = a_info['duration'] or 10
    b_dur = b_info['duration'] or 10
    offset = max(0, a_dur - duration)

    fc = (
        f"[0:v][1:v]xfade=transition={ffmpeg_t}:duration={duration}:offset={offset}[v];"
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

    # BUGFIX (智剪工坊 v1.1.1): 加 -pix_fmt yuv420p,强制 libx264 输出 yuv420p。
    # 原因:不强制时 ffmpeg 会自动选 yuv444p + High 4:4:4 Predictive,
    # 这种 profile QuickTime/WMP/部分手机相册不兼容,导致"无法播放"。
    cmd.extend(['-pix_fmt', 'yuv420p'])

    rc, _, err = run(cmd, timeout=600)
    return output_path if rc == 0 else None


def concatenate_simple(paths, output_path):
    """无转场，简单拼接。

    BUGFIX (智剪工坊 v1.1.1): 去除 stream copy 快路径,统一走重编 + faststart。
    原因:输入视频 fps 不一致(stream copy 后输出 VFR / 混合 fps,如 25.63),
    且 moov atom 位置/关键帧可能有兼容性问题。统一重编 + faststart 一次性解决。
    副作用:每次拼接都重编(慢),但兼容性彻底 OK。

    BUGFIX (v1.3.1): 兼容 str 和 Path 两种入参。
    原因:xfade_concat 内部会传 output_path(可能是 str)给本函数,直接调 .parent.mkdir() 会崩。
    """
    # v1.3.1 兼容:统一转 Path
    output_path = Path(output_path) if not isinstance(output_path, Path) else output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if len(paths) == 1:
        # BUGFIX: 即使单文件路径也重编一次以统一 fps + faststart
        # (原代码用 shutil.copy2,可能不重编 + moov 位置 + faststart)
        list_file = output_path.parent / "_concat_list.txt"
        with open(list_file, 'w', encoding='utf-8') as f:
            f.write(f"file '{paths[0]}'\n")
        cmd = [
            'ffmpeg', '-y', '-noautorotate',
            '-f', 'concat', '-safe', '0',
            '-i', str(list_file),
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
            '-c:a', 'aac', '-b:a', '128k',
            '-vsync', 'cfr', '-r', '30',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
            '-threads', '0',
            str(output_path)
        ]
        rc, _, err = run(cmd, timeout=300)
        list_file.unlink(missing_ok=True)
        return output_path if rc == 0 else None

    list_file = output_path.parent / "_concat_list.txt"
    with open(list_file, 'w', encoding='utf-8') as f:
        for p in paths:
            f.write(f"file '{p}'\n")

    # BUGFIX: 去掉 stream copy,统一重编 + fps 30 + yuv420p + faststart
    cmd = [
        'ffmpeg', '-y', '-noautorotate',
        '-f', 'concat', '-safe', '0',
        '-i', str(list_file),
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
        '-c:a', 'aac', '-b:a', '128k',
        '-vsync', 'cfr', '-r', '30',
        '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart',
        '-threads', '0',
        str(output_path)
    ]
    rc, _, err = run(cmd, timeout=600)
    list_file.unlink(missing_ok=True)
    return output_path if rc == 0 else None
