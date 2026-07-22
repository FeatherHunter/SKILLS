#!/usr/bin/env python3
"""
私家大厨 - CLI 输出格式化工具(L3 阶段新增)
所有 manager / recipe_import / orchestrator 共用的输出工具。

设计哲学:
- 默认人类友好(中文 + emoji),加 --json 走三段式 JSON
- {status, data, message} 三段式是 AI 可解析的接口
- 不破坏现有 print() UX,只是 wrap 一下
"""

import json
import sys
from typing import Any


# ====================================================================
# 核心 API
# ====================================================================

def emit(result: dict, json_mode: bool = False) -> None:
    """根据 json_mode 输出不同格式。

    Args:
        result: {"status": "success"/"error"/"warning"/..., "data": {...}, "message": "..."}
        json_mode: True 输出 JSON,False 输出人类友好
    """
    if json_mode:
        emit_json(result)
    else:
        emit_human(result)


def emit_json(result: dict) -> None:
    """输出 JSON 三段式,indent=2 让 AI 容易看。"""
    print(json.dumps(result, ensure_ascii=False, indent=2))


def emit_human(result: dict) -> None:
    """输出人类友好格式:
    ✅ message
       key1: value1
       key2: value2
    """
    status = result.get("status", "unknown")
    message = result.get("message", "")

    if status == "success":
        icon = "✅"
    elif status == "error":
        icon = "❌"
    elif status == "warning":
        icon = "⚠️"
    elif status == "dry_run":
        icon = "🔍"
    else:
        icon = "ℹ️"

    if message:
        print(f"{icon} {message}")
    else:
        print(f"{icon} {status}")

    # 关键字段(只输出标量,避免 list/dict 洪水)
    data = result.get("data") or {}
    for k, v in data.items():
        if isinstance(v, (str, int, float, bool)):
            print(f"   {k}: {v}")
        elif isinstance(v, list):
            print(f"   {k}: {len(v)} 项")
        elif isinstance(v, dict):
            # 只输出 dict 的前 3 个 key(避免太长)
            keys = list(v.keys())[:3]
            preview = ", ".join(f"{k}={v[k]}" for k in keys)
            print(f"   {k}: {{{preview}{'...' if len(v) > 3 else ''}}}")

    # errors 字段特殊处理
    errors = result.get("errors")
    if errors and isinstance(errors, list):
        print()
        print(f"   错误明细({len(errors)} 条):")
        for err in errors[:5]:  # 最多 5 条
            if isinstance(err, dict):
                field = err.get("field", "?")
                hint = err.get("hint", err.get("error", ""))
                print(f"     - [{field}] {hint}")
            else:
                print(f"     - {err}")
        if len(errors) > 5:
            print(f"     ... 还有 {len(errors) - 5} 条(用 --json 看完整)")

    # tips_warnings 字段(L2 阶段)
    tips_w = result.get("tips_warnings")
    if tips_w and isinstance(tips_w, list):
        print()
        print(f"   ⚠️  tips 业务警告({len(tips_w)} 条):")
        for w in tips_w[:3]:
            if isinstance(w, dict):
                missing = w.get("missing", [])
                uq = w.get("user_question", "")
                print(f"     - 缺 {', '.join(missing)}: {uq[:80]}{'...' if len(uq) > 80 else ''}")


def success(data: dict = None, message: str = "操作成功") -> dict:
    """构造 success 结果 dict(给 manager 直接返回)。"""
    return {
        "status": "success",
        "data": data or {},
        "message": message
    }


def error(message: str, data: dict = None, errors: list = None) -> dict:
    """构造 error 结果 dict。"""
    result = {
        "status": "error",
        "data": data or {},
        "message": message
    }
    if errors:
        result["errors"] = errors
    return result


def warning(message: str, data: dict = None) -> dict:
    """构造 warning 结果 dict。"""
    return {
        "status": "warning",
        "data": data or {},
        "message": message
    }


def parse_json_flag(argv: list) -> bool:
    """从 argv 中检测 --json 标志(不修改 argv)。"""
    return "--json" in argv


def remove_json_flag(argv: list) -> list:
    """返回去掉 --json 后的 argv(不修改原 list)。"""
    return [a for a in argv if a != "--json"]


# ====================================================================
# 便捷装饰器
# ====================================================================

def cli_dispatch(action_handlers: dict):
    """CLI 分发装饰器:把 add/list/search/update 等函数包装成统一 main()。

    Usage:
        from cli_formatter import cli_dispatch, emit, parse_json_flag

        HANDLERS = {
            "add": add,
            "list": list_items,
            "search": search,
        }

        def main():
            if len(sys.argv) < 2:
                print_usage()
                return
            action = sys.argv[1]
            args = parse_args(sys.argv[2:])
            json_mode = parse_json_flag(sys.argv)
            argv_clean = remove_json_flag(sys.argv)
            if action not in HANDLERS:
                print(f"未知操作:{action}")
                return
            result = HANDLERS[action](args)
            emit(result, json_mode=json_mode)
    """
    # 这个装饰器是为了简化 main() 写的,实际不用,而是直接抄模式
    pass


# ====================================================================
# 单元测试 / 调试入口
# ====================================================================

def main():
    if len(sys.argv) < 2:
        print("""cli_formatter.py - 单元测试入口

用法:
    python cli_formatter.py test
    python cli_formatter.py test --json
""")
        return

    if sys.argv[1] == "test":
        json_mode = parse_json_flag(sys.argv)
        result = success(
            data={"recipe_id": "abc-123", "name": "测试菜", "tags": ["辣", "川菜"], "extra": {"a": 1, "b": 2}},
            message="测试输出"
        )
        emit(result, json_mode=json_mode)

        result2 = error(
            message="校验失败",
            errors=[
                {"field": "name", "hint": "name 必填"},
                {"field": "servings", "hint": "servings 必须是正整数"}
            ]
        )
        emit(result2, json_mode=json_mode)

        result3 = warning(
            message="tips 缺字段",
            data={"tip_count": 2}
        )
        result3["tips_warnings"] = [
            {"missing": ["step_id"], "user_question": "这条 tip 没填 step,需要问用户吗?"}
        ]
        emit(result3, json_mode=json_mode)


if __name__ == "__main__":
    main()