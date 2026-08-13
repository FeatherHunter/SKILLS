# -*- coding: utf-8 -*-
"""饼干记账 · smartSelect 三字段 selector 块构建（T6 #312 · 契约 公共组件 §6.9 + .scratch/selector-proto/contract.md）

render_write.py / link/cli.py 两个采集渲染器共用，避免同源副本漂移。

数据契约: form.selector.<fieldKey> = {options, inferred?, recommended_new?, initial?}
- options:            [{name, disabled}] 已有项
  - account  = goals.json 顶层 accounts 键（与 ledgers 同构；T6 依赖注记: 原无人读, 本模块补建读取）
  - category = 历史分类 + L1 固定树（去重保序, 复用现有 categories_history / categories_all 数据）
  - ledger   = goals.json 顶层 ledgers 键（#311 已落地）
- inferred:           AI 推断的已有项（组件标「AI 推断」）
- recommended_new:    AI 推荐新建项（不在 options 中, 组件标「AI 推荐·新建」）
- initial:            {name, source} 显式初始选中（source 白名单 inferred|recommended_new|existing|history|custom）

来源语义（#306「不得编造」+ 契约 §4）:
- AI 未传字段值 → 该字段块只含 options（不预置）; 历史预填由 input.value 通道走（组件推导 source=history）
- AI 传值 + --<field>-source 显式来源 → 按来源填 inferred / recommended_new / initial
- AI 传值无来源（缺省）→ 值在 options 内 = initial{existing}; 不在 = recommended_new
- AI 只给分类 hint → 走分类建议兜底: 已有 = inferred; 全新 = recommended_new

只读 goals.json / 历史, 不写库（DB 红线: 测试全走 SKILLS_DB_PATH 临时目录）。
"""

from __future__ import annotations

import json
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent.resolve()
SKILL_DIR = _SCRIPT_DIR.parent

SOURCE_CHOICES = ("inferred", "recommended_new", "existing", "history", "custom")


def _goals_list(key: str) -> list:
    """读 goals.json 顶层键 → list; 缺键/缺文件/损坏/键型非法 → []（只读, 不写）"""
    from db import _find_db_path, DB_FILENAME
    p = _find_db_path(SKILL_DIR, DB_FILENAME).parent / "goals.json"
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, dict):
        return []
    v = data.get(key, [])
    return v if isinstance(v, list) else []


def account_options() -> list:
    """账户候选: goals.json accounts 键 → [{name, disabled}]（T6 依赖注记: 原无人读, 本模块补建）"""
    return [{"name": str(a.get("name") or ""), "disabled": bool(a.get("disabled"))}
            for a in _goals_list("accounts")
            if str(a.get("name") or "").strip()]


def ledger_options() -> list:
    """账本候选: goals.json ledgers 键 → [{name, disabled}]（#311 契约）"""
    return [{"name": str(l.get("name") or ""), "disabled": bool(l.get("disabled"))}
            for l in _goals_list("ledgers")
            if str(l.get("name") or "").strip()]


def category_options(records: list) -> list:
    """分类候选: 历史分类 + L1 固定树（去重保序）→ [{name}]"""
    from validators import ALL_L1
    seen, out = set(), []
    for c in [str(r.get("category") or "") for r in records] + [str(x) for x in ALL_L1]:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return [{"name": c} for c in out]


def _field_block(key: str, options: list, ai_fields: dict, sources: dict) -> dict:
    """单字段块: 按来源语义填 inferred / recommended_new / initial"""
    block = {"options": options}
    raw = ai_fields.get(key)
    val = str(raw or "").strip()
    if not val:
        return block
    src = sources.get(key)
    if src == "inferred":
        block["inferred"] = val
    elif src == "recommended_new":
        block["recommended_new"] = val
    elif src:
        block["initial"] = {"name": val, "source": src}
    else:
        names = {o["name"] for o in options}
        if val in names:
            block["initial"] = {"name": val, "source": "existing"}
        else:
            block["recommended_new"] = val
    return block


def build_selector(ai_fields: dict, records: list, sources: dict = None,
                   category_suggestions: list = None) -> dict:
    """三字段 selector 块（账户/分类/账本 · smartSelect 数据契约 v1）

    ai_fields: AI 显式传的字段值（预填前原始值; 历史预填走 input.value, 不在此处）
    sources:   {field: source}（CLI --<field>-source）
    category_suggestions: 分类建议（kind existing/new）; 仅当 AI 未直接给分类时兜底
    """
    sources = sources or {}
    out = {
        "account": _field_block("account", account_options(), ai_fields, sources),
        "category": _field_block("category", category_options(records), ai_fields, sources),
        "ledger": _field_block("ledger", ledger_options(), ai_fields, sources),
    }
    # 分类建议兜底（AI 只给 hint 时）: 已有 → inferred; 全新 → recommended_new
    if not str(ai_fields.get("category") or "").strip() and category_suggestions:
        s = category_suggestions[0]
        if s.get("kind") == "new":
            out["category"].setdefault("recommended_new", s["name"])
        else:
            out["category"].setdefault("inferred", s["name"])
    return out
