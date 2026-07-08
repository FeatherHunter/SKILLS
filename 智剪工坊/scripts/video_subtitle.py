# -*- coding: utf-8 -*-
"""
智剪工坊 · video_subtitle 子技能
AI 字幕自动生成（Whisper 转录 + 烧录到视频）

⚠️ BACKWARD COMPAT（v1.4）:
   本文件已迁移至 asr/transcribe.py（转录） + asr/burn_subtitle.py（烧字幕）。
   所有逻辑均在新路径实现，本文件仅作向后兼容导入。
   新代码请用:
     python asr/transcribe.py --input in.mp4 --srt subtitles.srt
     python asr/burn_subtitle.py --video in.mp4 --srt subtitles.srt --output out_subtitled.mp4
"""
# v1.4 backward compat: 重导出新路径的模块
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from asr.transcribe import transcribe_to_srt, fmt_ts, main

# burn_subtitle 也要重导出（兼容旧 CLI 用法）
from asr.burn_subtitle import burn_subtitle

__all__ = ["transcribe_to_srt", "fmt_ts", "burn_subtitle", "main"]
