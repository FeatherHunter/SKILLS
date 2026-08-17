# -*- coding: utf-8 -*-
import subprocess, sys

rows = [
    ("居家/食品", "-84.90", "山姆极速达-Member's Mark歌剧院蛋糕1*8s x1 ¥84.90"),
    ("餐饮/食材/海鲜", "-59.90", "山姆极速达-海鲜烧烤组合(32串)500g x1 ¥59.90"),
    ("餐饮/日常采购", "-2.00", "山姆极速达-包装费 ¥2.00"),
]

for category, amount, note in rows:
    r = subprocess.run(
        [sys.executable, "scripts/write/cli.py", "add",
         "--category", category, "--amount", amount,
         "--account", "支付宝", "--time", "2026-08-14 18:44:15",
         "--note", note],
        capture_output=True, text=True, encoding="utf-8"
    )
    print(r.stdout.strip() or r.stderr.strip())
