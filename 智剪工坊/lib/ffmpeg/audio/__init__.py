# -*- coding: utf-8 -*-
"""
智剪工坊 · lib/ffmpeg/audio 底层库

ffmpeg 音频能力封装（按业务分类）：
  - denoise     降噪 / 去噪（afftdn/afwtdn/arnndn/adeclick/adeclip）
  - enhance     人声增强（dialoguenhance/deesser/bandpass/equalizer）
  - detect      检测 / 分析（silencedetect/astats/volumedetect/aphasemeter）
  - normalize   归一化 / 动态（loudnorm/dynaudnorm/volume/afade）
  - transform   变换 / 效果（asetrate/atempo/chorus/tremolo 等）
  - channel     空间 / 立体声（stereowiden/extrastereo/channelmap）
  - visualize   可视化（showwaves/showspectrum/showcqt 等）
  - effect      其他效果（aecho/compand/dcshift/crystalizer 等）

调用示例:
    from lib.ffmpeg.audio.denoise import denoise_fft
    from lib.ffmpeg.audio.enhance import enhance_dialog
    from lib.ffmpeg.audio.detect import detect_silence
    from lib.ffmpeg.audio.normalize import normalize_loudnorm
    from lib.ffmpeg.audio.transform import change_pitch
    from lib.ffmpeg.audio.visualize import waveform_video

所有 lib 函数返回 (success: bool, output_path: str or dict)。
"""
import sys
from pathlib import Path

# 让 lib/common.py 可被 import
_LIB_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_LIB_DIR))


# 统一导出（方便上层调用）
from .denoise import (
    denoise_fft,
    denoise_wavelet,
    denoise_rnn,
    remove_click,
    remove_clip,
    aap_denoise,
)
from .enhance import (
    enhance_dialog,
    deess,
    bandpass,
    highpass,
    lowpass,
    equalize,
    dynamic_equalizer,
)
from .detect import (
    detect_silence,
    detect_volume,
    detect_astats,
    detect_phase,
)
from .normalize import (
    normalize_loudnorm,
    normalize_dynamic,
    adjust_volume,
    adjust_volume_db,
    fade_in_out,
)
from .transform import (
    change_pitch,
    change_speed,
    add_chorus,
    add_tremolo,
    add_phaser,
    add_echo,
    add_flanger,
    compress,
    limit,
    gate,
    excite,
    crusher,
)
from .channel import (
    widen_stereo,
    enhance_stereo,
    map_channels,
    split_channels,
    pan_audio,
    upmix_to_surround,
    merge_streams,
    mix_streams,
    multiply_streams,
    interleave_streams,
)
from .visualize import (
    waveform_video,
    waveform_image,
    spectrum_video,
    spectrum_image,
    cqt_video,
    freqs_video,
    volume_meter_video,
    histogram_image,
)
from .effect import (
    echo_advanced,
    compand_multi,
    dc_shift,
    crystalizer,
    pulsator,
    spectral_tilt,
    sidechain_gate,
    virtual_bass,
    drmeter,
)
from .utility import (
    adelay,
    apad,
    compensation_delay,
)
from .measure import (
    measure_psnr,
    measure_sdr,
    measure_si_sdr,
    measure_correlation,
)

__all__ = [
    # denoise (6)
    "denoise_fft", "denoise_wavelet", "denoise_rnn", "remove_click", "remove_clip", "aap_denoise",
    # enhance (7)
    "enhance_dialog", "deess", "bandpass", "highpass", "lowpass", "equalize", "dynamic_equalizer",
    # detect (4)
    "detect_silence", "detect_volume", "detect_astats", "detect_phase",
    # normalize (5)
    "normalize_loudnorm", "normalize_dynamic", "adjust_volume", "adjust_volume_db", "fade_in_out",
    # transform (12)
    "change_pitch", "change_speed", "add_chorus", "add_tremolo", "add_phaser",
    "add_echo", "add_flanger", "compress", "limit", "gate", "excite", "crusher",
    # channel (10)
    "widen_stereo", "enhance_stereo", "map_channels", "split_channels",
    "pan_audio", "upmix_to_surround", "merge_streams", "mix_streams",
    "multiply_streams", "interleave_streams",
    # visualize (8)
    "waveform_video", "waveform_image", "spectrum_video", "spectrum_image",
    "cqt_video", "freqs_video", "volume_meter_video", "histogram_image",
    # effect (9)
    "echo_advanced", "compand_multi", "dc_shift", "crystalizer", "pulsator",
    "spectral_tilt", "sidechain_gate", "virtual_bass", "drmeter",
    # utility (3) ⭐ 新增
    "adelay", "apad", "compensation_delay",
    # measure (4) ⭐ 新增
    "measure_psnr", "measure_sdr", "measure_si_sdr", "measure_correlation",
]