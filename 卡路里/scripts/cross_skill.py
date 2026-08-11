#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""卡路里 · 技能互联消费方（跨技能数据适配器 v1 · #274 试点）

契约: 技能互联/docs/契约规范-v1.md（#272 定稿 · 2026-08-11 用户逐条拍板）
职责:
  - read_skill(): 调技能互联 skilllink-read 命令（subprocess）读外部技能数据
    （统一信封: ok/skill/domain/meta/data/error）
  - weight_series(): 卡路里本地体重序列（weight_log，动态解析 DB 路径）
  - cs02(): CS-02「睡眠时长 vs 减重」合并逻辑（组合表定义）
    - 按天对齐睡眠时长与体重
    - 睡眠分位分组（<6h / 6-7h / 7-8h / 8-9h / >9h）→ 各组体重变化
    - 相关性: 同日 + 前 1 夜睡眠 vs 当日体重（滞后 1 天更符合因果方向）

DB 隔离红线: 本模块所有 DB 访问函数内动态解析 find_db_path，
不做模块级 DB_PATH 固化（#257 教训）——测试 SKILLS_DB_PATH 指临时目录即隔离。
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
SKILL_LINK_PY = Path(__file__).resolve().parents[2] / "技能互联" / "skilllink.py"

# CS-02 睡眠分位分组（组合表定义 · 单位分钟）
SLEEP_BUCKETS = [
    ("<6h",    lambda m: m < 360),
    ("6-7h",   lambda m: 360 <= m < 420),
    ("7-8h",   lambda m: 420 <= m < 480),
    ("8-9h",   lambda m: 480 <= m < 540),
    (">9h",    lambda m: m >= 540),
]


def read_skill(skill: str, domain: str, start: str, end: str) -> dict:
    """调技能互联 skilllink-read 命令 → 统一信封（契约 §5/§6）"""
    try:
        r = subprocess.run(
            [sys.executable, str(SKILL_LINK_PY),
             "--skill", skill, "--domain", domain,
             "--from", start, "--to", end],
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
    except FileNotFoundError:
        return {"ok": False, "error": f"技能互联命令不存在: {SKILL_LINK_PY}", "data": []}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"技能互联读取 {skill}.{domain} 超时", "data": []}
    try:
        env = json.loads(r.stdout or r.stderr)
    except json.JSONDecodeError:
        return {"ok": False, "error": f"技能互联输出解析失败: {(r.stdout or r.stderr)[:200]}", "data": []}
    return env


def what_skill(skill: str) -> dict:
    """问能力（契约 §7 --what）：返回注册表内容"""
    try:
        r = subprocess.run(
            [sys.executable, str(SKILL_LINK_PY), "--skill", skill, "--what"],
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
    except FileNotFoundError:
        return {"ok": False, "error": f"技能互联命令不存在: {SKILL_LINK_PY}"}
    try:
        return json.loads(r.stdout or r.stderr)
    except json.JSONDecodeError:
        return {"ok": False, "error": f"技能互联输出解析失败: {(r.stdout or r.stderr)[:200]}"}


def weight_series(start: str, end: str) -> list[dict]:
    """卡路里本地体重序列（weight_log · 按 date 升序）"""
    from db import find_db_path, get_db

    db_path = find_db_path(SKILL_DIR)
    if not db_path.exists():
        return []
    conn = get_db(db_path)
    try:
        rows = conn.execute(
            "SELECT date, weight_kg FROM weight_log "
            "WHERE date >= ? AND date <= ? ORDER BY date, id",
            (start, end),
        ).fetchall()
    finally:
        conn.close()
    return [{"date": r["date"], "weight_kg": float(r["weight_kg"])} for r in rows]


def _pearson(pairs: list[tuple[float, float]]) -> float | None:
    """皮尔逊相关系数（≥2 对且分母非 0）"""
    n = len(pairs)
    if n < 2:
        return None
    sx = sy = sxy = sx2 = sy2 = 0.0
    for x, y in pairs:
        sx += x; sy += y; sxy += x * y; sx2 += x * x; sy2 += y * y
    denom = ((n * sx2 - sx * sx) * (n * sy2 - sy * sy)) ** 0.5
    if denom == 0:
        return None
    r = (n * sxy - sx * sy) / denom
    return round(max(-1.0, min(1.0, r)), 3)


def _bucket_of(sleep_min: int) -> str | None:
    for label, cond in SLEEP_BUCKETS:
        if cond(sleep_min):
            return label
    return None


def cs02(start: str, end: str) -> dict:
    """CS-02 合并逻辑：睡眠时长 vs 减重（按天对齐 → 分位分组 → 相关性）"""
    sleep_env = read_skill("作息管家", "sleep", start, end)
    if not sleep_env.get("ok"):
        return {
            "ok": False,
            "start": start,
            "end": end,
            "error": sleep_env.get("error", "作息管家取数失败"),
            "skill_error": sleep_env,
            "data": [],
        }
    sleep_by_date = {d["date"]: int(d["sleep_min"]) for d in sleep_env.get("data", [])}
    weights = weight_series(start, end)

    # 按天对齐（双边有值）
    series = [
        {"date": w["date"], "sleep_min": sleep_by_date[w["date"]], "weight_kg": w["weight_kg"]}
        for w in weights
        if w["date"] in sleep_by_date
    ]
    series.sort(key=lambda x: x["date"])

    # 分位分组统计
    groups = {label: {"label": label, "days": 0, "sleep_avg": None,
                      "weight_delta": None, "weight_avg": None}
              for label, _ in SLEEP_BUCKETS}
    for s in series:
        label = _bucket_of(s["sleep_min"])
        if not label:
            continue
        g = groups[label]
        g["days"] += 1
    # 组内净变化（组首日 → 组末日）与平均睡眠
    for label, _ in SLEEP_BUCKETS:
        g = groups[label]
        if g["days"] == 0:
            continue
        rows = [s for s in series if _bucket_of(s["sleep_min"]) == label]
        sleeps = [r["sleep_min"] for r in rows]
        g["sleep_avg"] = round(sum(sleeps) / len(sleeps), 0)
        g["weight_avg"] = round(sum(r["weight_kg"] for r in rows) / len(rows), 2)
        if len(rows) >= 2:
            g["weight_delta"] = round(rows[-1]["weight_kg"] - rows[0]["weight_kg"], 2)
        else:
            g["weight_delta"] = 0.0

    active_groups = [g for g in groups.values() if g["days"] > 0]

    # 相关性: 同日 + 滞后 1 天（前夜睡眠 vs 当日体重）
    same_pairs = [(s["sleep_min"], s["weight_kg"]) for s in series]
    lag_pairs = []
    for i in range(1, len(series)):
        if series[i]["date"] == series[i - 1]["date"]:
            continue
        lag_pairs.append((series[i - 1]["sleep_min"], series[i]["weight_kg"]))
    r_same = _pearson(same_pairs)
    r_lag1 = _pearson(lag_pairs)

    # 一句话洞察（规则生成）
    insight = _insight(len(series), active_groups, r_same, r_lag1)

    return {
        "ok": True,
        "start": start,
        "end": end,
        "days": len(series),
        "sleep_days": len(sleep_by_date),
        "weight_days": len(weights),
        "series": series,
        "groups": active_groups,
        "correlation": {"same_day": r_same, "lag_1day": r_lag1},
        "insight": insight,
    }


def _insight(days: int, groups: list[dict], r_same, r_lag1) -> str:
    """一句话洞察（#274 对抗审查决策 A/B 落地 · 2026-08-12）

    A: 组内净变化口径透明化——文案明示「组内净变化 = 该组首日→末日体重差」
       （保持现状算法，靠标注防误读，不换算法）
    B: 样本少标注——分组天数 < 5 时自动加「样本少，仅供参考」
    """
    def _low_sample_note() -> str:
        low = [g["label"] for g in groups if g["days"] < 5]
        return f"其中 {'、'.join(low)} 样本少（<5 天），仅供参考。" if low else ""

    if days < 5:
        return f"对齐天数不足（{days} 天），需要更多「同天有睡眠+体重」的数据才能看趋势。"
    if len(groups) < 2:
        g = groups[0]
        return (f"窗口内 {days} 天睡眠时长集中在 {g['label']}（日均 {g['sleep_avg']:.0f} 分钟），"
                f"体重净变化 {g['weight_delta']:+.2f} kg（组内净变化 = 该组首日→末日体重差），"
                f"暂无法跨睡眠水平对比。")
    best = max(groups, key=lambda g: abs(g["weight_delta"] or 0))
    worst = min(groups, key=lambda g: abs(g["weight_delta"] or 0))
    r_label = f"同日相关 r={r_same:+.2f}" if r_same is not None else "同日数据不足"
    lag_label = f"前夜相关 r={r_lag1:+.2f}" if r_lag1 is not None else "前夜数据不足"
    if best["weight_delta"] is not None and worst["weight_delta"] is not None:
        diff = best["weight_delta"] - worst["weight_delta"]
        return (f"窗口内 {days} 天：睡 {best['label']} 的日子体重净变化 {best['weight_delta']:+.2f} kg "
                f"vs 睡 {worst['label']} 的日子 {worst['weight_delta']:+.2f} kg"
                f"（组间差 {diff:+.2f} kg · 组内净变化 = 该组首日→末日体重差）。"
                f"{r_label} · {lag_label}。{_low_sample_note()}")
    return f"窗口内 {days} 天，{r_label} · {lag_label}。{_low_sample_note()}"


def default_window(days: int = 30) -> tuple[str, str]:
    end = date.today().isoformat()
    start = (date.today() - timedelta(days=days - 1)).isoformat()
    return start, end


if __name__ == "__main__":
    import argparse

    from _io_guard import guard_io

    guard_io()

    parser = argparse.ArgumentParser(description="卡路里 · 技能互联消费方（CS-02 睡眠 vs 减重）")
    parser.add_argument("--domain", default="sleep", help="要读的域（默认 sleep）")
    parser.add_argument("--from", dest="from_", default=None, help="开始日期 YYYY-MM-DD（默认近 30 天）")
    parser.add_argument("--to", default=None, help="结束日期 YYYY-MM-DD（默认今天）")
    parser.add_argument("--what", action="store_true", help="问作息管家能力（契约 §7）")
    args = parser.parse_args()

    if args.what:
        print(json.dumps(what_skill("作息管家"), ensure_ascii=False, indent=2))
    else:
        start = args.from_ or default_window()[0]
        end = args.to or default_window()[1]
        result = cs02(start, end)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result.get("ok") else 1)
