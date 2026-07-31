#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""幂等性: 搜心愿里有没有"打扫"或"开出去转转",0 命中才 add"""
import subprocess
import sys
import json

CLI = r"D:\2Study\StudyNotes\SKILLS\备忘录\script\memo_cli.py"

# 1) 搜:分类=心愿,关键词=打扫 OR 开出去转转
print("[1] 幂等性检查:search -c 心愿 打扫 / 开出去转转")
for kw in ["打扫", "开出去", "汽车", "转转"]:
    r = subprocess.run([
        sys.executable, CLI, "search", kw, "-c", "心愿"
    ], capture_output=True, text=True, encoding="utf-8")
    try:
        data = json.loads(r.stdout)
        count = data.get("data", {}).get("count", 0) if data.get("status") == "ok" else 0
        print(f"  搜「{kw}」→ 命中 {count} 条")
        if count > 0:
            for item in data["data"].get("items", [])[:3]:
                print(f"    #{item['id']} | {item['content']}")
    except Exception as e:
        print(f"  搜「{kw}」失败: {e}")
        print(r.stdout[:200])

# 2) 0 命中 → add 心愿
print("\n[2] 假设 0 命中 → add 心愿")
content = "打扫一次汽车并且开出去转转"
r = subprocess.run([
    sys.executable, CLI, "add", content, "-c", "心愿"
], capture_output=True, text=True, encoding="utf-8")
print("STDOUT:", r.stdout)
if r.stderr:
    print("STDERR:", r.stderr)
print(f"exit: {r.returncode}")
