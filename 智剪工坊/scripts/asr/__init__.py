# -*- coding: utf-8 -*-
"""
asr/ — 智剪工坊语音识别链路（L6）

本目录按 ASR 处理链路组织：

  L6 分析 → transcribe.py（Whisper 转录 → SRT）
  L6 合成 → burn_subtitle.py（SRT 烧录到视频）
           speaker_srt.py（说话人分离 + ASR → 带说话人的 SRT）

链路:

  基础链路（单人说）:
    audio/extract.py → asr/transcribe.py → asr/burn_subtitle.py

  降噪增强链路:
    audio/denoise.py → asr/transcribe.py → asr/burn_subtitle.py

  说话人分离链路（多人对话）:
    audio/separate.py → audio/diarize.py
                       → asr/transcribe.py
                       → asr/speaker_srt.py → asr/burn_subtitle.py

文件名规范（L6）:
  transcribe.py     — 核心 ASR（Whisper）
  burn_subtitle.py  — 烧字幕（合成到视频）
  speaker_srt.py    — 说话人 + ASR 合并

旧路径 backward-compat:
  scripts/video_subtitle.py → asr/transcribe.py
"""

# 方便外部导入
from . import transcribe
from . import burn_subtitle
from . import speaker_srt

__all__ = ["transcribe", "burn_subtitle", "speaker_srt"]
