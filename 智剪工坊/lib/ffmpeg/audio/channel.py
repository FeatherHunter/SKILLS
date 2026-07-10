# -*- coding: utf-8 -*-
"""
lib/ffmpeg/audio/channel.py — 空间 / 立体声

封装 ffmpeg 声道处理:
  - stereowiden       立体声扩展（让单声道变宽）
  - extrastereo       增强立体声分离度
  - channelmap        声道映射
  - channelsplit      声道拆分
  - pan               声相调整
  - surround          环绕声（upmix）
  - a3dscope/aphasemeter 立体声分析
"""
import sys
from pathlib import Path

_LIB_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_LIB_DIR))
from common import run_ffmpeg, log_ffmpeg_call  # noqa: E402


@log_ffmpeg_call
def widen_stereo(input_path, output_path, amount=1.0):
    """立体声扩展（stereowiden）。

    Args:
        amount: 扩展强度（0=不变，1=中等，3=最强）
    """
    # ffmpeg 7.1: stereowiden 用 drymix 替代 dry，参数范围不同
    delay_val = int(15 * amount)
    feedback_val = min(0.95, 0.3 + amount * 0.1)
    crossfeed_val = min(1.0, 0.1 + amount * 0.2)
    drymix_val = min(1.0, 0.5 + amount * 0.2)  # drymix 范围 [0-1]
    af = (
        f"stereowiden=delay={delay_val}:feedback={feedback_val}:"
        f"crossfeed={crossfeed_val}:drymix={drymix_val}"
    )
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def enhance_stereo(input_path, output_path, strength=2.0):
    """增强立体声（extrastereo）。

    Args:
        strength: 分离强度（默认 2.0，范围 [0, 10]）
    """
    af = f"extrastereo=m={strength}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def map_channels(input_path, output_path, channel_layout="stereo"):
    """声道映射（aformat）。

    Args:
        channel_layout: 'mono' / 'stereo' / '5.1' / '7.1'
    """
    af = f"aformat=channel_layouts={channel_layout}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def split_channels(input_path, output_path_left, output_path_right):
    """拆分左右声道（channelsplit）。

    Returns:
        (success_left, success_right)
    """
    af_left = "channelsplit=channel_layout=stereo:channels=FL"
    af_right = "channelsplit=channel_layout=stereo:channels=FR"

    run_ffmpeg(["-i", str(input_path), "-af", af_left, "-c:a", "pcm_s16le", "-y", str(output_path_left)])
    run_ffmpeg(["-i", str(input_path), "-af", af_right, "-c:a", "pcm_s16le", "-y", str(output_path_right)])
    return True, True


@log_ffmpeg_call
def pan_audio(input_path, output_path, pan="stereo|c0=c1"):
    """声相调整（pan）。

    Args:
        pan: pan 表达式，第一个字符必须是合法 layout
                合法前缀：'mono' / 'stereo' / '5.1' / '7.1' 等
                范例: "stereo|c0=c1"（右移）, "stereo|c0=c0"（中央）,
                     "mono|c0=0.5*c0+0.5*c1"（单声道混合）
    """
    # ffmpeg 7.1: pan= 必须以合法 channel layout 开头（不是数字 like "0.5"）
    af = f"pan={pan}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def upmix_to_surround(input_path, output_path, surround_type="5.1"):
    """环绕声 upmix（surround）。

    Args:
        surround_type: '5.1' / '7.1'
    """
    # ffmpeg 7.1: surround 用 chl_out (output layout) + chl_in (input layout)
    # chl_out 默认为 "5.1"，chl_in 默认为 "stereo"
    af = f"surround=chl_out={surround_type}:chl_in=stereo"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def merge_streams(input_path_1, input_path_2, output_path, layout="stereo"):
    """合并多音频流（amerge）⭐ 胶水级。

    Args:
        input_path_1, input_path_2: 两个输入音频
        output_path: 输出多通道音频
        layout: 输出声道布局（默认 stereo）
    """
    af = f"amerge=inputs=2,aformat=channel_layouts={layout}"
    run_ffmpeg([
        "-i", str(input_path_1), "-i", str(input_path_2),
        "-filter_complex", af, "-c:a", "pcm_s16le", "-y", str(output_path),
    ])
    return True, str(output_path)


@log_ffmpeg_call
def mix_streams(input_paths, output_path, weights=None, duration="longest"):
    """多音频流混合（amix）⭐ 胶水级。

    Args:
        input_paths: 输入音频路径列表
        output_path: 输出音频
        weights: 各流权重（默认全 1.0）
        duration: 'longest'（最长） / 'shortest'（最短） / 'first'（第一个）
    """
    if weights is None:
        weights = [1.0] * len(input_paths)

    if len(weights) != len(input_paths):
        raise ValueError("weights 必须与 input_paths 长度一致")

    inputs = []
    for p in input_paths:
        inputs.extend(["-i", str(p)])

    weights_str = " ".join(f"-{w}" for w in weights)
    af = f"amix=inputs={len(input_paths)}:duration={duration}:dropout_transition=0"
    run_ffmpeg(inputs + ["-filter_complex", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def multiply_streams(input_path_1, input_path_2, output_path):
    """两流相乘（amultiply）— 侧链调制。

    用一轨音频去调制另一轨的振幅。
    """
    af = "amultiply"
    run_ffmpeg([
        "-i", str(input_path_1), "-i", str(input_path_2),
        "-filter_complex", af, "-c:a", "pcm_s16le", "-y", str(output_path),
    ])
    return True, str(output_path)


@log_ffmpeg_call
def interleave_streams(input_paths, output_path):
    """多流交叉混合（ainterleave）。

    把多路音频按时间片交叉混合成一轨。
    """
    af = f"ainterleave=inputs={len(input_paths)}"
    inputs = []
    for p in input_paths:
        inputs.extend(["-i", str(p)])
    run_ffmpeg(inputs + ["-filter_complex", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)