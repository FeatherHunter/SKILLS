# -*- coding: utf-8 -*-
import subprocess, sys, os

items = [
    {"amount": "-84.90", "category": "居家/食品",
     "note": "山姆极速达-Member's Mark歌剧院蛋糕1*8s x1 ¥84.90"},
    {"amount": "-59.90", "category": "餐饮/食材/海鲜",
     "note": "山姆极速达-海鲜烧烤组合(32串)500g x1 ¥59.90"},
    {"amount": "-2.00", "category": "餐饮/日常采购",
     "note": "山姆极速达-包装费 ¥2.00"},
]

import json
r = subprocess.run(
    [sys.executable, "scripts/render_write.py", "batch",
     "--items", json.dumps(items, ensure_ascii=False),
     "--ledger", "生活",
     "--out", r"C:\Users\辰辰洋洋\.minimax\workspace\拍账单_确认_山姆20260814.html"],
    capture_output=True, text=True, encoding="utf-8"
)
print(r.stdout)
if r.stderr:
    print("STDERR:", r.stderr)
sys.exit(r.returncode)
