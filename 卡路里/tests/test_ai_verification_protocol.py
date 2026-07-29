#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_ai_verification_protocol.py — ADR-0007 seam 8 守门

ticket 08 · 2026-07-29

覆盖 SKILL.md §⚠️ 强制性规定 第 7 条 + §核心原则 第 7 条 + ADR-0007
存在性的契约断言。
"""
from __future__ import annotations

import re
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
ADR_DIR = SKILL_DIR / "docs" / "adr"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def test_skill_md_has_section_7_ai_verification():
    """§⚠️ 强制性规定 编号到 7 条,第 7 条是 AI 验证协议"""
    text = _read(SKILL_MD)
    # 找 §⚠️ 强制性规定 段,断言有 "7. " 开头的条目
    m = re.search(r"## ⚠️ 强制性规定.*?(?=^## |\Z)", text, re.DOTALL | re.MULTILINE)
    assert m, "未找到 §⚠️ 强制性规定 段"
    section = m.group(0)
    # 第 7 条必须含 AI 验证 + SELECT 关键词
    seven_re = re.search(r"^7\.\s.*?$", section, re.MULTILINE)
    assert seven_re, "§⚠️ 强制性规定 缺第 7 条"
    assert "AI 验证" in seven_re.group(0) or "SELECT" in seven_re.group(0), (
        f"第 7 条应谈 AI 验证 / SELECT,实得: {seven_re.group(0)[:80]}"
    )
    # 含 3 个 fail mode 红线
    assert "写脏数据" in section and "空值" in section and "类型" in section, (
        "第 7 条应含 3 个 fail mode 红线(写脏数据 / 空值 / 类型)"
    )


def test_skill_md_has_7th_core_principle():
    """§核心原则 至少 7 条 bullet,最后一条是 AI 验证"""
    text = _read(SKILL_MD)
    # §核心原则 段到下一个 ###/## 标题为止
    m = re.search(r"## 核心原则(.*?)(?=^### |^## |\Z)", text, re.DOTALL | re.MULTILINE)
    assert m, "未找到 §核心原则 段"
    section = m.group(1)
    bullets = re.findall(r"^\-\s.*?$", section, re.MULTILINE)
    assert len(bullets) >= 7, (
        f"§核心原则 至少 7 条 bullet,实得 {len(bullets)}: {bullets}"
    )
    # 最后一条要含 AI 验证协议关键词
    last = bullets[-1]
    assert "AI 验证" in last or "SELECT" in last, (
        f"§核心原则 最后一条应是 AI 验证,实得: {last[:80]}"
    )


def test_adr_0007_exists():
    """ADR-0007 文件存在 + Status: accepted + 含 SELECT 关键词"""
    adr_path = ADR_DIR / "0007-ai-verification-protocol.md"
    assert adr_path.exists(), f"ADR-0007 文件缺失: {adr_path}"
    text = _read(adr_path)
    assert "Status: accepted" in text, "ADR-0007 应标 Status: accepted"
    assert "SELECT" in text, "ADR-0007 应谈 SELECT 验证"