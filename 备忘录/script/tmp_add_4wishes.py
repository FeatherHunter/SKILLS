# -*- coding: utf-8 -*-
import subprocess, sys

wishes = [
    ("修复 opencode 调色板 bug", None),  # 无时间锚点 → 不传 due
    ("给 prompt 插件扩展模板(做场景提示 每个模板的适用场景)", None),
    ("prompt 插件的 prompt 信息润色", None),
    ("mattskills 插件 prompt 需要符合 matt 的教学视频,每个技能提供5～10使用注意点和实战场景", None),
]

for content, due in wishes:
    cmd = [sys.executable, "script/memo_cli.py", "add", content, "-c", "心愿"]
    if due:
        cmd += ["--due", due]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    out = r.stdout.strip() or r.stderr.strip()
    # 提取 id
    import re, json
    try:
        d = json.loads(r.stdout)
        nid = d.get('data', {}).get('id', '?')
        print(f"  [{content[:30]}] id={nid} {out[:150]}")
    except Exception:
        print(f"  [{content[:30]}] {out[:200]}")