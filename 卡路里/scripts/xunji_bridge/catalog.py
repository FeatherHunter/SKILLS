#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""训记官方动作名库 —— 加载与校验。

数据源:`~/.minimax/训记官方动作.json
来源:https://github.com/Foveluy/Xunji-movements

文件结构(实际):
    {"actions": ["动作1", "动作2", ...]}

公开 API:
    load_catalog() -> set[str]            # 返回合法动作名集合(空集表示库缺失)
    verify(name) -> dict                  # 校验单个动作名
    verify_many(names) -> dict            # 批量校验
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

CATALOG_PATH = Path.home() / ".minimax" / "训记官方动作.json"


def load_catalog() -> set[str]:
    """加载动作名集合。

    库文件缺失或解析失败时返回空集(不抛错)。
    返回空集时,verify 应当报告"无法验证"而非"动作不合法"。
    """
    if not CATALOG_PATH.exists():
        return set()
    try:
        with open(CATALOG_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return set()
    actions = data.get("actions", [])
    if not isinstance(actions, list):
        return set()
    return {str(a) for a in actions}


def verify(name: str) -> dict:
    """校验单个动作名是否在训记官方库中。

    Returns:
        {
            "name": 原动作名,
            "valid": bool | None,   # True=合法,False=不在库,None=库缺失无法验证
            "catalog_loaded": bool, # 库是否成功加载
            "suggestion": str | None,  # 简单建议(若不在库)
        }
    """
    catalog = load_catalog()
    name = (name or "").strip()
    if not name:
        return {
            "name": name,
            "valid": False,
            "catalog_loaded": bool(catalog),
            "suggestion": "动作名为空",
        }
    if not catalog:
        return {
            "name": name,
            "valid": None,
            "catalog_loaded": False,
            "suggestion": f"训记官方动作库缺失或损坏({CATALOG_PATH}),无法验证",
        }
    if name in catalog:
        return {
            "name": name,
            "valid": True,
            "catalog_loaded": True,
            "suggestion": None,
        }
    # 简单建议:找最长公共前缀匹配(给一个 hint,不保证)
    suggestion = None
    for cat_name in catalog:
        if cat_name.startswith(name[:2]) and len(cat_name) > len(name):
            suggestion = f"是否想用『{cat_name}』?"
            break
    return {
        "name": name,
        "valid": False,
        "catalog_loaded": True,
        "suggestion": suggestion,
    }


def verify_many(names: Iterable[str]) -> dict:
    """批量校验。

    Returns:
        {
            "catalog_loaded": bool,
            "total": int,
            "valid_count": int,
            "invalid_count": int,
            "results": [verify() 输出的列表],
        }
    """
    results = [verify(n) for n in names]
    valid = sum(1 for r in results if r["valid"] is True)
    invalid = sum(1 for r in results if r["valid"] is False)
    return {
        "catalog_loaded": bool(load_catalog()),
        "total": len(results),
        "valid_count": valid,
        "invalid_count": invalid,
        "results": results,
    }


if __name__ == "__main__":
    # 单独跑 catalog.py 打印库摘要
    import json
    catalog = load_catalog()
    print(json.dumps({
        "path": str(CATALOG_PATH),
        "exists": CATALOG_PATH.exists(),
        "count": len(catalog),
    }, ensure_ascii=False, indent=2))
