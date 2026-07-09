# -*- coding: utf-8 -*-
"""
智剪工坊 · lib/ffmpeg/video 底层库

ffmpeg 视频能力封装（按业务分类）：
  - subtitle.py    字幕烧录（SRT/ASS/drawtext）
  - transition.py  转场（xfade 30+ 种）
  - color.py       调色（亮度/对比度/曲线/LUT）
  - timing.py      速度/时间（变速/截取/倒放/冻结）
  - transform.py   缩放/裁剪/旋转/翻转/黑边
  - watermark.py   水印（logo / 文字）

调用示例:
    from lib.ffmpeg.video.subtitle import burn_subtitle
    from lib.ffmpeg.video.transition import xfade_transition
    from lib.ffmpeg.video.transform import scale_video

所有函数返回 (success: bool, output_path: str)。
"""
import sys
from pathlib import Path

# 让 lib/common.py 可被 import
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common import run_ffmpeg, get_duration  # noqa: E402


# 统一导出
from .subtitle import (
    burn_subtitle,
    burn_ass_subtitle,
    draw_text,
)
from .transition import (
    xfade_transition,
    concat_simple,
    XFADE_TYPES,
)
from .color import (
    adjust_brightness_contrast,
    color_balance,
    hue_shift,
    apply_lut,
    vibrance,
    curves_adjust,
)
from .timing import (
    change_speed,
    trim_clip,
    reverse_video,
    freeze_frame,
    set_fps,
)
from .transform import (
    scale_video,
    crop_video,
    rotate_video,
    flip_video,
    pad_video,
    letterbox,
)
from .watermark import (
    add_watermark,
    add_text_watermark,
    POSITIONS,
)

__all__ = [
    # subtitle (3)
    "burn_subtitle", "burn_ass_subtitle", "draw_text",
    # transition (2 + XFADE_TYPES dict)
    "xfade_transition", "concat_simple", "XFADE_TYPES",
    # color (6)
    "adjust_brightness_contrast", "color_balance", "hue_shift",
    "apply_lut", "vibrance", "curves_adjust",
    # timing (5)
    "change_speed", "trim_clip", "reverse_video", "freeze_frame", "set_fps",
    # transform (6)
    "scale_video", "crop_video", "rotate_video",
    "flip_video", "pad_video", "letterbox",
    # watermark (2 + POSITIONS dict)
    "add_watermark", "add_text_watermark", "POSITIONS",
]