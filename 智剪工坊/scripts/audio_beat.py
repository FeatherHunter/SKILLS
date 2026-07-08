# -*- coding: utf-8 -*-
"""
智剪工坊 · audio_beat 子技能
节拍卡点（分析 BGM 节拍，自动输出节拍时间戳 / 剪切点）

⚠️ BACKWARD COMPAT（v1.4）:
   本文件已迁移至 audio/beat.py。
   所有逻辑均在 audio/beat.py 实现，本文件仅作向后兼容导入。
   新代码请用: python audio/beat.py --analyze --bgm music.mp3 --output beats.json
"""
# v1.4 backward compat: 重导出新路径的模块
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from audio.beat import analyze_beats, cut_to_beats, main

__all__ = ["analyze_beats", "cut_to_beats", "main"]
