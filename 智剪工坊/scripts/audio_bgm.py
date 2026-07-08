# -*- coding: utf-8 -*-
"""
智剪工坊 · audio_bgm 子技能
给视频加 BGM（混音，人声不被覆盖）

⚠️ BACKWARD COMPAT（v1.4）:
   本文件已迁移至 audio/mix.py。
   所有逻辑均在 audio/mix.py 实现，本文件仅作向后兼容导入。
   新代码请用: python audio/mix.py --input v.mp4 --bgm b.mp3 --output out.mp4
"""
# v1.4 backward compat: 重导出新路径的模块
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from audio.mix import add_bgm, add_bgm_loop, main

__all__ = ["add_bgm", "add_bgm_loop", "main"]
