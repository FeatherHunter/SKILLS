"""共享 pytest fixture

为 4 类测试提供统一地基：
- 临时 SQLite DB（指向临时 SKILLS_DB_PATH）
- 临时 HTML_DIR（跟随 SKILLS_DB_PATH）
- 30 条 sample_bills（含空数据 / 跨月 / 跨年）
- CLI 子进程 wrapper（调用 record_bill.py / bill_inject.py / render_help.py）

设计要点：
- SKILLS_DB_PATH 必须在 `import db` 之前设置，否则 db.py 模块顶层 DB_PATH 会被固化
  到全局 fallback。conftest 在 import 早期用 autouse monkeypatch 兜底。
- 临时 DB 与临时 HTML_DIR 同 parent（与生产布局一致：$DATA_DIR/{db, html}）。
"""

from __future__ import annotations

import os
import sys
import json
import subprocess
import tempfile
from pathlib import Path

import pytest


# ── 1. 路径常量 ──────────────────────────────────────────────────────────────

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


# ── 2. 临时 DB / HTML_DIR fixture ────────────────────────────────────────────

@pytest.fixture
def tmp_db_dir(tmp_path, monkeypatch):
    """临时 SKILLS_DB_PATH 指向 tmp_path，使 db.py / html_paths.py 都用临时目录。

    必须在每次 import db 之前 patch env；db.py 在顶层读 _find_db_path()。
    我们在 fixture 中 patch env，然后强制 reimport db / analyze 模块，
    让模块级 DB_PATH 重新解析到 tmp_path。
    """
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))

    # 强制 reimport：清掉 db / analyze / html_paths 的缓存
    for mod_name in ("db", "analyze", "html_paths"):
        if mod_name in sys.modules:
            del sys.modules[mod_name]

    import db  # noqa: F401  重新解析 DB_PATH 到 tmp_path
    import analyze  # noqa: F401
    import html_paths  # noqa: F401

    yield tmp_path

    # teardown: 清掉缓存，避免后续测试拿到 stale DB_PATH
    for mod_name in ("db", "analyze", "html_paths"):
        if mod_name in sys.modules:
            del sys.modules[mod_name]


@pytest.fixture
def empty_db(tmp_db_dir):
    """初始化一个空 DB（仅 schema，无数据）"""
    from db import init_db
    init_db()
    return tmp_db_dir


@pytest.fixture
def html_dir(tmp_db_dir):
    """临时 HTML_DIR（= $SKILLS_DB_PATH/biscuit_accountant_html/）"""
    from html_paths import html_dir as _html_dir
    return _html_dir(mkdir=True)


# ── 3. 样本数据 ─────────────────────────────────────────────────────────────

# 30 条 sample_bills：含跨月（2025-11/12 + 2026-01）、跨年、空备注、收入/支出混搭
SAMPLE_BILLS = [
    # 2025-11（5 条，跨年之前）
    {"category": "餐饮/外卖/午餐", "amount": -35.0,  "time": "2025-11-15 12:00:00", "note": "午饭",        "account": "支付宝", "ledger": "生活", "currency": "人民币"},
    {"category": "出行/网约车",    "amount": -20.0,  "time": "2025-11-20 18:30:00", "note": "下班打车",     "account": "微信",   "ledger": "生活", "currency": "人民币"},
    {"category": "玩乐/影音游戏",  "amount": -58.0,  "time": "2025-11-22 20:00:00", "note": "电影",         "account": "",       "ledger": "生活", "currency": "人民币"},
    {"category": "工资/基本工资",  "amount": 8000.0, "time": "2025-11-10 09:00:00", "note": "11月工资",     "account": "招行",   "ledger": "生活", "currency": "人民币"},
    {"category": "居家/房租水电",  "amount": -2500.0,"time": "2025-11-01 10:00:00", "note": "",             "account": "招行",   "ledger": "生活", "currency": "人民币"},

    # 2025-12（6 条，跨年边缘）
    {"category": "餐饮/堂食/晚餐", "amount": -120.0, "time": "2025-12-31 19:00:00", "note": "跨年饭",       "account": "支付宝", "ledger": "生活", "currency": "人民币"},
    {"category": "玩乐/旅游",      "amount": -800.0, "time": "2025-12-25 14:00:00", "note": "圣诞节",       "account": "信用卡", "ledger": "旅行", "currency": "人民币"},
    {"category": "穿着/上衣",      "amount": -399.0, "time": "2025-12-20 15:00:00", "note": "羽绒服",       "account": "",       "ledger": "生活", "currency": "人民币"},
    {"category": "投资/分红",      "amount": 300.0,  "time": "2025-12-15 10:00:00", "note": "基金分红",     "account": "招行",   "ledger": "生活", "currency": "人民币"},
    {"category": "健康/看病",      "amount": -200.0, "time": "2025-12-10 09:00:00", "note": "挂号",         "account": "",       "ledger": "生活", "currency": "人民币"},
    {"category": "社交/礼物",      "amount": -88.0,  "time": "2025-12-05 11:00:00", "note": "",             "account": "微信",   "ledger": "生活", "currency": "人民币"},

    # 2026-01（5 条，跨年之后）
    {"category": "餐饮/外卖/早餐", "amount": -15.0,  "time": "2026-01-02 08:00:00", "note": "豆浆包子",     "account": "支付宝", "ledger": "生活", "currency": "人民币"},
    {"category": "学习/书籍",      "amount": -58.0,  "time": "2026-01-05 19:00:00", "note": "Python 书",    "account": "",       "ledger": "生活", "currency": "人民币"},
    {"category": "居家/通讯",      "amount": -99.0,  "time": "2026-01-10 10:00:00", "note": "话费",         "account": "支付宝", "ledger": "生活", "currency": "人民币"},
    {"category": "宠物/食物",      "amount": -200.0, "time": "2026-01-15 16:00:00", "note": "狗粮",         "account": "",       "ledger": "生活", "currency": "人民币"},
    {"category": "其他",          "amount": -10.0,  "time": "2026-01-20 12:00:00", "note": "杂项",         "account": "",       "ledger": "生活", "currency": "人民币"},

    # 2026-02（3 条，节后淡季）
    {"category": "餐饮/外卖/午餐", "amount": -25.0,  "time": "2026-02-03 12:00:00", "note": "午饭",         "account": "微信",   "ledger": "生活", "currency": "人民币"},
    {"category": "餐饮/咖啡奶茶/奶茶","amount": -18.0, "time": "2026-02-08 15:00:00","note": "下午茶",       "account": "支付宝", "ledger": "生活", "currency": "人民币"},
    {"category": "出行/公共交通/地铁","amount": -4.0, "time": "2026-02-10 08:00:00", "note": "",             "account": "",       "ledger": "生活", "currency": "人民币"},

    # 2026-03（4 条）
    {"category": "餐饮/外卖/晚餐", "amount": -45.0,  "time": "2026-03-01 19:00:00", "note": "加班餐",       "account": "支付宝", "ledger": "生活", "currency": "人民币"},
    {"category": "居家/日用品/洗护", "amount": -80.0,"time": "2026-03-05 14:00:00", "note": "洗发水",       "account": "",       "ledger": "生活", "currency": "人民币"},
    {"category": "玩乐/运动健身",  "amount": -3000.0,"time": "2026-03-10 18:00:00", "note": "健身年卡",     "account": "信用卡", "ledger": "生活", "currency": "人民币"},
    {"category": "奖金/项目奖金",  "amount": 5000.0, "time": "2026-03-15 10:00:00", "note": "项目奖",       "account": "招行",   "ledger": "生活", "currency": "人民币"},

    # 2026-04（3 条）
    {"category": "餐饮/外卖/午餐", "amount": -32.0,  "time": "2026-04-02 12:00:00", "note": "午饭",         "account": "微信",   "ledger": "生活", "currency": "人民币"},
    {"category": "出行/网约车",    "amount": -28.0,  "time": "2026-04-10 22:00:00", "note": "深夜打车",     "account": "支付宝", "ledger": "生活", "currency": "人民币"},
    {"category": "兼职/副业",      "amount": 2000.0, "time": "2026-04-15 20:00:00", "note": "副业收入",     "account": "招行",   "ledger": "生活", "currency": "人民币"},

    # 2026-05（2 条，少数据月）
    {"category": "餐饮/堂食/午餐", "amount": -38.0,  "time": "2026-05-01 12:00:00", "note": "五一",         "account": "支付宝", "ledger": "旅行", "currency": "人民币"},
    {"category": "玩乐/旅游",      "amount": -1500.0,"time": "2026-05-02 10:00:00", "note": "景点门票",     "account": "信用卡", "ledger": "旅行", "currency": "人民币"},

    # 2026-07（2 条，当月）
    {"category": "餐饮/咖啡奶茶/咖啡","amount": -28.0,"time": "2026-07-01 09:00:00","note": "美式",         "account": "支付宝", "ledger": "生活", "currency": "人民币"},
    {"category": "其他收入/红包",  "amount": 100.0,  "time": "2026-07-15 14:00:00", "note": "生日红包",     "account": "微信",   "ledger": "生活", "currency": "人民币"},
]


@pytest.fixture
def seeded_db(tmp_db_dir):
    """初始化 DB + 注入 30 条样本数据（跨月/跨年/空备注/收入支出混搭）"""
    from db import init_db, TABLE_NAME
    import sqlite3
    conn = init_db()
    try:
        cur = conn.cursor()
        for b in SAMPLE_BILLS:
            cur.execute(
                f"INSERT INTO {TABLE_NAME} (category, time, amount, account, ledger, currency, note) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (b["category"], b["time"], b["amount"], b["account"], b["ledger"], b["currency"], b["note"]),
            )
        conn.commit()
    finally:
        conn.close()
    return tmp_db_dir


# ── 4. CLI 子进程 wrapper ────────────────────────────────────────────────────

@pytest.fixture
def run_cli(tmp_db_dir):
    """子进程 wrapper：跑 record_bill.py / bill_inject.py / render_help.py

    传入 SKILLS_DB_PATH 给子进程，确保与父进程用同一个临时 DB。
    返回 (returncode, stdout, stderr)。

    用法：
        rc, out, err = run_cli(["record_bill.py", "summary", "--json"])
        rc, out, err = run_cli(["bill_inject.py", "summary"])
    """
    env = os.environ.copy()
    env["SKILLS_DB_PATH"] = str(tmp_db_dir)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    def _runner(script_args, timeout=30):
        script_name = script_args[0]
        script_path = SCRIPTS_DIR / script_name
        if not script_path.exists():
            raise FileNotFoundError(f"脚本不存在: {script_path}")
        cmd = [sys.executable, str(script_path)] + script_args[1:]
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", env=env, timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr

    return _runner


@pytest.fixture
def parse_cli_json(run_cli):
    """便捷 wrapper：跑 record_bill.py <subcmd> --json，返回解析后的 dict

    用法：
        data = parse_cli_json(["summary"])
        data = parse_cli_json(["list", "--date", "2026-07-01"])
    """
    def _parser(subcmd_args):
        args = ["record_bill.py"] + subcmd_args + ["--json"]
        rc, out, err = run_cli(args)
        assert rc == 0, f"CLI 失败 rc={rc}: {err}\nstdout: {out}"
        return json.loads(out)
    return _parser
