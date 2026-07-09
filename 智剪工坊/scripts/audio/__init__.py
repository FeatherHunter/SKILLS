# -*- coding: utf-8 -*-
"""
audio/ — 智剪工坊音频链路（L1-L5）

本目录按音频处理链路分层组织：

  L1 合成   → mix（多个音频混为一个）
  L2 变换   → voice（变声）、beat（节拍）
  L3 提取   → extract（提取音频流）
  L4 降噪/分离 → denoise（降噪）、separate（声源分离）
  L5 说话人   → diarize（说话人分离，依赖 L4 输出）

v1.5 重大变化:
  - 本目录作为用户入口 CLI（用户可见）
  - 底层 ffmpeg 调用已下沉到 lib/ffmpeg/audio/
  - 每个脚本调 lib/ffmpeg/audio/*.py 的对应函数

调用规范（v1.5 起）:
  # 推荐：从 SKILL_ROOT 运行，sys.path 自动设置
  python scripts/audio/denoise.py --input audio.wav --output clean.wav

  # 或 import（注意 lib 路径）
  import sys
  sys.path.insert(0, "scripts")  # 才能 from audio import ...
  from audio.denoise import denoise
"""

# 方便外部导入: from audio import mix, voice, beat, denoise, separate, diarize
from . import mix
from . import voice
from . import beat
from . import denoise
from . import separate
from . import diarize

__all__ = ["mix", "voice", "beat", "denoise", "separate", "diarize"]
