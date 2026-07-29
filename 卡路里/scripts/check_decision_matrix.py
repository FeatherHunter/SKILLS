#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_decision_matrix.py — §完整 HTML 模板清单 一致性检查

ticket 01 · 2026-07-29 卡路里 HTML 重设计基础设施
依据:.scratch/card-html-redesign/spec.md D1 + ADR-0001/0002/0003 落地守护。

检查 3 项强制条件(对 §完整 HTML 模板清单 每个 ✅ 行):
  1. 渲染脚本存在:  scripts/render_<X>.py
  2. 模板文件存在:    templates/<X>.html
  3. mock fixture 存在(若 render 脚本支持 --mock):tests/fixtures/mock/mock_<X>.json

soft 检查(不阻断 exit 0 但打 info):
  - §04 决策矩阵 ❌ 行触发词(如 查今天喝水 ADR-0003 之前)

退出码:
  0 = 全部 ✅
  1 = 有缺失(打印缺失列表)

用法:
    python scripts/check_decision_matrix.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
SCRIPTS_DIR = SKILL_DIR / "scripts"
TEMPLATES_DIR = SKILL_DIR / "templates"
MOCK_DIR = SKILL_DIR / "tests" / "fixtures" / "mock"

# 表格行渲染器列 → 期望的 render_*.py 文件名(可推导)
# 但实际 SKILL.md 第 4 列是 渲染器,文本形式,需解析
# 例:`scripts/render_calorie_trend.py` → 取最后一个 token

ROW_RE = re.compile(
    r"^\|\s*`?(templates/[^`]+|process_progress[^`]*)?`?\s*\|"
    r"\s*([^|]+?)\s*\|"
    r"\s*([^|]+?)\s*\|"
    r"\s*([^|]+?)\s*\|",
    re.MULTILINE,
)

# 表格行提取 trigger cell 中 `/` 分隔的多 trigger
TRIGGER_SPLIT_RE = re.compile(r"[/／、\s]+")


def extract_table_rows(skill_md_text: str) -> list[dict]:
    """从 SKILL.md §完整 HTML 模板清单 提取每行

    Returns:
        [{template, triggers, data_source, renderer, raw_line}, ...]
    """
    sec = re.search(
        r"### 完整 HTML 模板清单.*?(?=^###|\n## |\Z)",
        skill_md_text, re.DOTALL | re.MULTILINE,
    )
    if not sec:
        raise ValueError("SKILL.md 找不到 §完整 HTML 模板清单 section")

    rows: list[dict] = []
    for line in sec.group(0).splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        tmpl, triggers_cell, _data, renderer = m.group(1), m.group(2), m.group(3), m.group(4)
        # 跳过表头与分隔行
        if not tmpl or tmpl.startswith("---") or "模板" in tmpl:
            continue
        # 解析 trigger cell → list
        triggers: list[str] = []
        for part in TRIGGER_SPLIT_RE.split(triggers_cell):
            t = part.strip().strip("`").strip()
            if not t or t.startswith("(") or t in ("子页", "同上"):
                continue
            # 去括号注释(口语变体)
            t = re.sub(r"[（(][^）)]*[）)]", "", t).strip()
            if t:
                triggers.append(t)
        # 解析 renderer cell → 取最后一个 `scripts/render_*.py`
        rm = re.search(r"scripts/(render_[A-Za-z_]+\.py)", renderer)
        renderer_name = rm.group(1) if rm else None

        rows.append({
            "template":   tmpl.strip().strip("`"),
            "triggers":   triggers,
            "data_source": _data.strip(),
            "renderer":   renderer_name,
            "raw_line":   line.strip(),
        })
    return rows


def _resolve_template_paths(tmpl_field: str) -> list[Path]:
    """template 字段可能含多个候选(用 / 分隔),逐一校验存在性

    例:`templates/today_diet.html` / `today_meals.html` → 解析为 2 个文件
    """
    out: list[Path] = []
    for token in re.split(r"[/／、]", tmpl_field):
        token = token.strip().strip("`").strip()
        if not token:
            continue
        if token.startswith("templates/"):
            out.append(TEMPLATES_DIR / token[len("templates/"):])
        elif token.endswith(".html"):
            out.append(TEMPLATES_DIR / token)
    return out


def _expected_mock_name(renderer_name: str | None) -> str | None:
    """render_<name>.py → mock_<name>.json(只去 render_ 前缀)"""
    if not renderer_name:
        return None
    if not renderer_name.startswith("render_"):
        return None
    return f"mock_{renderer_name[len('render_'):]}"


def main() -> int:
    text = SKILL_MD.read_text(encoding="utf-8")
    rows = extract_table_rows(text)
    if not rows:
        print("❌ §完整 HTML 模板清单 解析失败(0 行)")
        return 1

    issues: list[str] = []
    warnings: list[str] = []
    info_total = 0

    for row in rows:
        # 1. render script
        if row["renderer"]:
            rp = SCRIPTS_DIR / row["renderer"]
            if not rp.exists():
                issues.append(f"[render 缺失] {row['renderer']} ← {row['template']} 行")
        else:
            warnings.append(f"[renderer 列未识别] {row['raw_line'][:80]}")

        # 2. template file(s)
        for tp in _resolve_template_paths(row["template"]):
            if not tp.exists():
                issues.append(f"[template 缺失] {tp.relative_to(SKILL_DIR)} ← 行 {row['raw_line'][:60]}")

        # 3. mock fixture(soft check — 部分 wizard / 接通型 render 不一定有)
        mock_name = _expected_mock_name(row["renderer"])
        if mock_name:
            mp = MOCK_DIR / mock_name
            if not mp.exists():
                warnings.append(f"[mock 缺失 · soft] {mock_name} ← {row['renderer']}")

        info_total += 1

    print(f"§完整 HTML 模板清单 共 {info_total} 行")
    print(f"  强制检查: render + template")
    print(f"  soft 检查: mock fixture")
    print()
    if warnings:
        print(f"⚠ {len(warnings)} 项 soft warning:")
        for w in warnings:
            print(f"  - {w}")
        print()
    if issues:
        print(f"❌ {len(issues)} 项强制缺失:")
        for x in issues:
            print(f"  - {x}")
        return 1
    print("✅ §完整 HTML 模板清单 一致性 pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())