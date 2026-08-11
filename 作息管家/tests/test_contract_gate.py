# -*- coding: utf-8 -*-
"""作息管家 · 技能互联契约全局门禁（#273）

#271 拍板硬约束：校验器进各已接入技能 pytest——漏接 = 测试红 = commit 被拒。
本测试跑真 registry（默认路径），验证全仓库契约一致。
不依赖 conn fixture：check_public_contract 是纯静态检查 + --what（不执行 fetch，
不碰任何 DB），安全无隔离负担。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
LINK_DIR = SKILL_DIR.parent / "技能互联"


def test_public_contract_gate():
    """技能互联 · check_public_contract.py 全局门禁 exit 0（契约一致才放行）"""
    r = subprocess.run(
        [sys.executable, str(LINK_DIR / "check_public_contract.py")],
        cwd=str(SKILL_DIR), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60,
    )
    assert r.returncode == 0, (
        f"check_public_contract.py exit={r.returncode}\n"
        f"stdout: {r.stdout}\nstderr: {r.stderr}"
    )
