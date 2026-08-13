#!/usr/bin/env python3
"""饼干记账 · 账本管理 CLI(数据层 · goals.json ledgers 键 · T4 #308 定稿 · wayfinder #311 T7)

子命令:
    add --name X                新增账本(账本表 = goals.json ledgers 键)
    list                        账本清单(输出对齐 account list)
    update --name X [--new-name Y | --disable | --enable]  改名 / 停用 / 启用

载体(T4 #308 契约):
    账本清单 = $DATA_DIR/goals.json 顶层 "ledgers" 键(与 budgets/savings/accounts 平级)
    结构     = [{"name": str, "disabled": bool, "created_at": "YYYY-MM-DD HH:MM:SS"}]
    缺键/空文件 → 读作 {"ledgers": []};写保留其他键(原子写 tmp+replace)
    name 规则 = 非空、≤30 字、重名拒绝;disabled=True = 停用(选择器划线置灰)
    改名同步 bills.ledger(含软删记录);「生活」不种子(write CLI 默认仍「生活」)
    转账/借贷账本不入键(规则约定账本,由 account 转账 / 写入借贷流程固定)

用法:
    python3 scripts/ledger/cli.py add --name 旅行
    python3 scripts/ledger/cli.py list
    python3 scripts/ledger/cli.py update --name 旅行 --new-name 旅游
    python3 scripts/ledger/cli.py update --name 旅行 --disable
    python3 scripts/ledger/cli.py update --name 旅行 --enable
"""

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from db import _find_db_path, DB_FILENAME  # noqa: E402
from cli_utils import reconfigure_utf8, emit_ok, emit_error  # noqa: E402

reconfigure_utf8()

GOALS_FILENAME = "goals.json"

# 规则约定账本(系统按名字写入,不可手动入键/改名,否则历史与新写入分叉)
RESERVED_LEDGERS = ("转账", "借贷")
# 写入默认账本(write CLI --ledger 默认「生活」· 存量行为零变化 → 不可被改名弃用)
DEFAULT_LEDGER = "生活"


# ── goals.json 读写(账本表 · 顶层 "ledgers" 键 · 与账户/目标域键隔离)───────────

def _goals_path() -> Path:
    return _find_db_path(_SCRIPTS.parent, DB_FILENAME).parent / GOALS_FILENAME


def _load_goals() -> dict:
    p = _goals_path()
    if not p.exists():
        return {}
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as e:
        raise RuntimeError(f"goals.json 读取失败(可能被其他域写入中): {e}")
    if not text.strip():
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"goals.json 读取失败(可能被其他域写入中): {e}")


def _save_goals(data: dict) -> None:
    """原子写:先写 .tmp 再 replace(防并发半写)"""
    p = _goals_path()
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def _ledgers() -> list:
    """账本表(ledgers 键 · 缺键读作空数组 · T4 契约)

    键型防御:键存在但非列表(dict/str 等) → 读作空数组,不崩溃不吐垃圾
    (渲染器侧同口径;损坏文件仍报错,拒绝覆盖写坏的数据)。
    """
    ledgers = _load_goals().get("ledgers", [])
    return ledgers if isinstance(ledgers, list) else []


def _save_ledgers(ledgers: list) -> None:
    data = _load_goals()
    data["ledgers"] = ledgers
    _save_goals(data)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── 新增账本 ─────────────────────────────────────────────────────────────────

def cmd_add(args):
    name = (args.name or "").strip()
    if not name:
        raise ValueError("账本名不能为空(新增账本需要 --name)")
    if len(name) > 30:
        raise ValueError(f"账本名过长({len(name)} 字,最多 30 字)")
    if name in RESERVED_LEDGERS:
        raise ValueError(f"账本「{name}」为规则约定账本(由转账/借贷流程固定),不可手动新增")
    for l in _ledgers():
        if l["name"] == name:
            raise ValueError(f"账本「{name}」已存在(重复新增需用户确认)")
    entry = {
        "name": name,
        "disabled": False,
        "created_at": _now(),
    }
    ledgers = _ledgers()
    ledgers.append(entry)
    _save_ledgers(ledgers)
    data = {"ledger": entry, "count": len(ledgers)}
    if getattr(args, 'json', False):
        emit_ok(data, f"已新增账本 {name}")
        return data
    print(f"✓ 已新增账本 {name}")
    return data


# ── 账本清单(AI 定位候选 / 选择器 options 数据源)──────────────────────────────

def cmd_list(args):
    ledgers = _ledgers()
    data = {"count": len(ledgers), "ledgers": ledgers}
    if getattr(args, 'json', False):
        emit_ok(data, f"账本清单 {len(ledgers)} 个")
        return data
    if not ledgers:
        print("(账本表为空 · 先使用「新增账本」)")
        return data
    for l in ledgers:
        flag = " · 已停用" if l.get("disabled") else ""
        print(f"  {l['name']}{flag}")
    return data


# ── 修改账本(改名 / 停用 / 启用)──────────────────────────────────────────────

def _find_ledger(ledgers: list, name: str):
    for l in ledgers:
        if l["name"] == name:
            return l
    return None


def cmd_update(args):
    name = (args.name or "").strip()
    if not name:
        raise ValueError("目标账本不能为空(改账本需要 --name)")
    ledgers = _ledgers()
    target = _find_ledger(ledgers, name)
    if target is None:
        raise ValueError(f"账本「{name}」不存在(可先用 ledger list 查看账本表)")

    changes = []
    if args.new_name:
        new_name = (args.new_name or "").strip()
        if not new_name:
            raise ValueError("新账本名不能为空")
        if len(new_name) > 30:
            raise ValueError(f"新账本名过长({len(new_name)} 字,最多 30 字)")
        if new_name == name:
            raise ValueError("新账本名与原名相同,无需修改")
        if name in RESERVED_LEDGERS or new_name in RESERVED_LEDGERS:
            raise ValueError("「转账/借贷」为规则约定账本(由转账/借贷流程固定),不可改名或改名为之")
        if name == DEFAULT_LEDGER:
            raise ValueError("「生活」为写入默认账本(write CLI 默认),改名会使默认写入与历史记录分叉;如需使用新名,先调整写入默认")
        if _find_ledger(ledgers, new_name) is not None:
            raise ValueError(f"账本「{new_name}」已存在,不能改名为重名")
        # 账本表改名
        target["name"] = new_name
        changes.append(f"改名:{name} → {new_name}")
        # 历史记录保留(逐条改名,bills.ledger 跟随;含软删记录,恢复后名称一致)
        from db import init_db, TABLE_NAME
        conn = init_db()
        try:
            cur = conn.cursor()
            cur.execute(
                f"UPDATE {TABLE_NAME} SET ledger = ? WHERE ledger = ?",
                (new_name, name),
            )
            conn.commit()
            renamed_rows = cur.rowcount
        finally:
            conn.close()
        changes.append(f"历史流水改名 {renamed_rows} 笔")
    if args.disable:
        target["disabled"] = True
        changes.append("停用(历史记录保留,选择器划线置灰)")
    if args.enable:
        target["disabled"] = False
        changes.append("启用(恢复参与选择)")
    if not changes:
        raise ValueError("没有可执行的变更(至少传 --new-name / --disable / --enable 之一)")
    _save_ledgers(ledgers)
    data = {"ledger": target, "changes": changes}
    if getattr(args, 'json', False):
        emit_ok(data, f"已更新账本 {name}")
        return data
    for c in changes:
        print(f"✓ {c}")
    return data


# ── 入口 ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="饼干记账 · 账本管理(goals.json ledgers 键 · T4 定稿)")
    sub = parser.add_subparsers(dest='command', help='子命令')

    p = sub.add_parser('add', help='新增账本(写入 goals.json 账本表)')
    p.add_argument('--name', required=True, help='账本名(如:旅行 / 餐饮)')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    p = sub.add_parser('list', help='账本清单')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    p = sub.add_parser('update', help='修改账本(改名 / 停用 / 启用)')
    p.add_argument('--name', required=True, help='目标账本名')
    p.add_argument('--new-name', default=None, help='新账本名(改名)')
    p.add_argument('--disable', action='store_true', help='停用账本(历史记录保留)')
    p.add_argument('--enable', action='store_true', help='启用账本')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    commands = {'add': cmd_add, 'list': cmd_list, 'update': cmd_update}
    cmd = commands.get(args.command)
    if cmd:
        try:
            cmd(args)
        except (ValueError, RuntimeError) as e:
            emit_error(f"参数错误：{e}") if getattr(args, 'json', False) else print(f"✗ 参数错误：{e}")
        except Exception as e:
            emit_error(f"执行出错：{e}") if getattr(args, 'json', False) else print(f"✗ 执行出错：{e}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
