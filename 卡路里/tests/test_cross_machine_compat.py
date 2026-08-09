#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_cross_machine_compat.py — 跨机器兼容防回归(#242/#235 配套 · 2026-08-09)

覆盖(seam 守门):
  1. _io_guard.guard_io():GBK 严格流下 print emoji 不崩(errors=replace 生效)
  2. check_trigger_consistency 对照 3:description ≤1024 + HELP 锚点 + 触发词有效性
  3. check_trigger_consistency 对照 4:全部入口脚本(有 __main__)必须带 _io_guard
  4. 触发词权威源:_triggers.py 唯一权威(HTML 表/docstring ⊆ 权威源)
"""
from __future__ import annotations

import io
import re
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
SKILL_MD = SKILL_DIR / "SKILL.md"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def test_io_guard_gbk_emoji_no_crash():
    """#242:guard_io 后 GBK 严格流 print emoji 不崩(核心修复)"""
    sys.path.insert(0, str(SCRIPTS_DIR))
    from _io_guard import guard_io

    old_stdout, old_stderr = sys.stdout, sys.stderr
    try:
        # 模拟 GBK 严格流(改动前 print ✅ 必崩)
        sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding="gbk", errors="strict")
        sys.stderr = io.TextIOWrapper(io.BytesIO(), encoding="gbk", errors="strict")
        guard_io()
        print("✅ 测试")
        print("⚠️ 警告", file=sys.stderr)
        # 不抛异常 = 通过
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr
    assert True


def test_io_guard_utf8_content_preserved():
    """#242:guard 后中文内容在 UTF-8 解码下完整保留(消费端对齐)"""
    sys.path.insert(0, str(SCRIPTS_DIR))
    from _io_guard import guard_io

    old_stdout = sys.stdout
    try:
        buf = io.BytesIO()
        sys.stdout = io.TextIOWrapper(buf, encoding="gbk", errors="strict")
        guard_io()
        print("卡路里_HELP_20260809.html")
        sys.stdout.flush()
        data = buf.getvalue()
        # 消费端(opencode)按 UTF-8 解码 → 中文完整
        assert data.decode("utf-8").strip() == "卡路里_HELP_20260809.html"
    finally:
        sys.stdout = old_stdout


def test_description_contract():
    """#235:description ≤1024 + HELP 锚点 + 触发词全部可定位"""
    text = _read(SKILL_MD)
    m = re.search(r"^description:.*?(?=\nmetadata:|\n---)", text, re.M | re.S)
    assert m, "frontmatter description 缺失"
    desc = m.group(0)
    flat = "".join(desc.split())
    assert len(flat) <= 1024, f"description {len(flat)} 字符 > 1024 上限(#235)"

    # HELP 锚点必须存在
    help_pos = flat.find("卡路里HELP")
    assert help_pos >= 0, "description 缺 卡路里HELP 锚点"
    assert help_pos < 200, f"HELP 应在路由锚点区(现 {help_pos} 字符处,#235)"

    # 触发词必须能在权威源定位(精确或裸词别名)
    sys.path.insert(0, str(SCRIPTS_DIR))
    from _triggers import TRIGGERS

    authority = {t["wake_word"] for t in TRIGGERS}
    seg_m = re.search(r"触发词:(.+?)(?:完整触发词|\Z)", desc, re.S)
    seg = seg_m.group(1) if seg_m else ""
    words = [w.strip() for w in seg.split("、") if w.strip()]
    assert words, "description 触发词段为空"
    for w in words:
        if w in authority:
            continue
        is_alias = any(
            a.startswith(w) and a[len(w):].startswith(("：", "（", "(", ":"))
            for a in authority
        )
        assert is_alias, f"description 触发词无法在权威源定位: {w}"


def test_all_entry_scripts_have_io_guard():
    """#242 防回归:所有有 __main__ 块的 scripts/*.py 必须带 _io_guard"""
    import ast

    missing = []
    for f in sorted(SCRIPTS_DIR.glob("*.py")):
        t = _read(f)
        if "_io_guard" in t:
            continue
        try:
            tree = ast.parse(t)
        except SyntaxError:
            continue
        is_entry = any(
            isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
            and isinstance(n.test.left, ast.Name) and n.test.left.id == "__name__"
            for n in ast.walk(tree)
        )
        if is_entry:
            missing.append(f.name)
    assert not missing, f"入口脚本缺 _io_guard(#242): {missing}"


def test_trigger_authority_consistency():
    """#235 配套:权威源迁移后 check 三边一致(HTML 表/docstring ⊆ _triggers.py)"""
    r = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "check_trigger_consistency.py")],
        cwd=SKILL_DIR, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=30,
    )
    assert r.returncode == 0, (
        f"check_trigger_consistency.py exit={r.returncode}\n"
        f"stdout: {r.stdout[-500:]}\nstderr: {r.stderr[-300:]}"
    )
