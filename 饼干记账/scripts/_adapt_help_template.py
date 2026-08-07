# -*- coding: utf-8 -*-
"""饼干记账 help.html 适配脚本:居家管家 B2 模板 → 饼干记账文案(一次性)"""
from pathlib import Path

p = Path(r"D:\2Study\StudyNotes\SKILLS\饼干记账\templates\help.html")
raw = p.read_bytes()
has_bom = raw[:3] == b"\xef\xbb\xbf"
text = raw.decode("utf-8-sig")

repls = [
    ("<title>居家管家 · 使用手册(HELP)</title>", "<title>饼干记账 · 使用手册(HELP)</title>"),
    ('<div class="eyebrow">Home Manager Help</div>', '<div class="eyebrow">Biscuit Accounting Help</div>'),
    ("<h1>居家管家 · 使用手册</h1>", "<h1>饼干记账 · 使用手册</h1>"),
    ("🚀 第一次用居家管家?", "🚀 第一次用饼干记账?"),
    (
        "从「首次使用」开始 — 自动检测环境、建库建分类,全程零决策,一次成功。完成初始化后,本区域将不再出现。",
        "从「初始化」开始 — 自动检测环境、确认数据目录、建库、验证,全程零决策。完成初始化后,本区域将不再出现。",
    ),
    ("s.scenario_id==='first_use'", "s.scenario_id==='setup_init_wizard'"),
    (
        "粘贴给 AI,居家管家技能会自动执行这个流程,完成后你会拿到结果 HTML + 一句话总结。",
        "粘贴给 AI,饼干记账技能会自动执行这个流程,完成后你会拿到结果 HTML + 一句话总结。",
    ),
    ("'居家管家 v2.0 HELP · 使用手册'", "'饼干记账 v2.0 HELP · 使用手册'"),
]

miss = []
for old, new in repls:
    if old in text:
        text = text.replace(old, new, 1)
    else:
        miss.append(old[:50])

out = text.encode("utf-8-sig") if has_bom else text.encode("utf-8")
p.write_bytes(out)
print("BOM:", has_bom)
print("未命中:", miss if miss else "无(全部替换成功)")
print("残留'居家管家'检查:", "居家管家" in text)
