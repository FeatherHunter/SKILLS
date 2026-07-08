# -*- coding: utf-8 -*-
"""
audio/ — 智剪工坊音频链路（L1-L5）

本目录按音频处理链路分层组织：

  L1 合成   → mix（多个音频混为一个）
  L2 变换   → voice（变声）、beat（节拍）
  L3 提取   → extract（提取音频流）
  L4 降噪/分离 → denoise（降噪）、separate（声源分离）
  L5 说话人   → diarize（说话人分离，依赖 L4 输出）

链路示例:
  # 场景：视频里人声被 BGM 盖住，ASR 准确率低
  # 正确链路：
  # 1. extract  — 提取视频音频流
  # 2. separate — Demucs 分离人声
  # 3. diarize  — 区分不同说话人
  # 4. asr/     — 用干净人声做 ASR

文件名规范:
  L1: mix.py
  L2: voice.py, beat.py
  L3: extract.py
  L4: denoise.py, separate.py
  L5: diarize.py

旧路径 backward-compat:
  scripts/audio_bgm.py   → audio/mix.py
  scripts/audio_voice.py  → audio/voice.py
  scripts/audio_beat.py  → audio/beat.py
  scripts/edit.py extract-audio → audio/extract.py
"""

# 方便外部导入: from audio import mix, voice, beat, denoise, separate, diarize
from . import mix
from . import voice
from . import beat
from . import denoise
from . import separate
from . import diarize

__all__ = ["mix", "voice", "beat", "denoise", "separate", "diarize"]
