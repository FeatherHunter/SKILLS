# -*- coding: utf-8 -*-
"""作息管家 · 技能互联注册表（提供方侧 · #274 试点）

契约: 技能互联/docs/契约规范-v1.md（#272 定稿 · 2026-08-11 用户逐条拍板）
形态: 本文件只放注册表 + 取数函数；命令真身（skilllink-read）住技能互联 Base。

域:
  sleep — 每日睡眠时长（主睡眠段 · 分钟）
    数据源: daily_summary（date/category/total_minutes）
    主睡眠段 = category 为「睡眠」（旧一级）或「*.睡眠」（新二级，如 维持.睡眠）；
    排除「午睡」等非主睡眠段（组合表 CS-02 定义: 主睡眠段）。
"""

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def fetch_sleep(start: str, end: str) -> list[dict]:
    """取 [start, end] 每日主睡眠时长（分钟），按 date 升序。

    fetch 签名契约（技能互联）: fetch(start, end) -> list[dict]（一行一条）。
    注意: get_connection 必须**函数内动态取**（import schedule_db 后属性访问），
    不能模块级 from-import 绑定——否则测试 fixture 的 monkeypatch 在后续
    import 缓存下失效（#274 实测坑：跨用例连到旧临时 DB）。
    """
    import schedule_db

    conn = schedule_db.get_connection()
    try:
        rows = conn.execute(
            "SELECT date, SUM(total_minutes) AS sleep_min FROM daily_summary "
            "WHERE date >= ? AND date <= ? "
            "AND (category = '睡眠' OR category LIKE '%.睡眠') "
            "GROUP BY date ORDER BY date",
            (start, end),
        ).fetchall()
    finally:
        conn.close()
    # 注意: 作息管家 get_connection 不设 row_factory → 返回普通 tuple，
    # 必须用位置索引访问（Row/tuple 都兼容）。
    return [{"date": r[0], "sleep_min": int(r[1] or 0)} for r in rows]


PUBLIC_DOMAINS = {
    "sleep": {
        "name": "睡眠",
        "desc": "每日睡眠时长（主睡眠段 · 分钟）",
        "fields": [
            {"name": "date", "type": "date", "unit": "", "desc": "日期（YYYY-MM-DD）"},
            {"name": "sleep_min", "type": "number", "unit": "分钟", "desc": "当日主睡眠总时长"},
        ],
        "fetch": fetch_sleep,
    },
}
