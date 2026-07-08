# -*- coding: utf-8 -*-
"""
智剪工坊 · audio_voice 子技能
音频变声（老人 / 小孩 / 机器人 / 女声 / 男声）

⚠️ BACKWARD COMPAT（v1.4）:
   本文件已迁移至 audio/voice.py。
   所有逻辑均在 audio/voice.py 实现，本文件仅作向后兼容导入。
   新代码请用: python audio/voice.py --input in.mp4 --type old_man --output out.mp4
"""
# v1.4 backward compat: 重导出新路径的模块
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from audio.voice import change_voice, PRESETS, main

__all__ = ["change_voice", "PRESETS", "main"]
