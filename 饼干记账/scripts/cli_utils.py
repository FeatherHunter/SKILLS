"""公共 CLI 工具:编码 / 格式化 / JSON 输出(三域 cli 共享)"""

import sys
import json


def reconfigure_utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def format_validation_error(e, json_mode=False):
    """ValidationError → CLI 输出(字段名 + 当前值 + 期望值 + 怎么修)"""
    msg = str(e)
    if json_mode:
        print(json.dumps({
            "status": "error", "data": None, "message": msg
        }, ensure_ascii=False))
    else:
        print(f"✗ 参数错误：{msg}")


def format_record(r):
    """格式化单条记录"""
    time = r.get('time', 'N/A')
    category = r.get('category', 'N/A')
    amount = r.get('amount', 0)
    note = r.get('note', '')
    return f"{time} | {category} | {amount:.2f} | {note}"


def emit_ok(data, message, indent=2):
    print(json.dumps({
        "status": "ok", "data": data, "message": message
    }, ensure_ascii=False, indent=indent))


def emit_error(message, indent=2):
    print(json.dumps({
        "status": "error", "data": None, "message": message
    }, ensure_ascii=False, indent=indent))
