#!/usr/bin/env python3
"""健身计划生成器：接收采访流程输出的 JSON → 校验 → 写入 DB

输入格式（采访对话的输出）：
{
  "config": {
    "title": "...",
    "description": "...",
    "start_date": "YYYY-MM-DD",
    "user_level": "新手|中手|老手"
  },
  "weeks": [{week_number, days: [{day_of_week, sessions: [{...}]}]}]
}

校验规则：
  硬止1：动作名 ∈ 训记官方动作库
  硬止2：动作所需器材 ∈ 用户可用器材
  硬止3：同部位两次训练间隔 ≥ 48h
  软提示：单日单部位超建议组数 / 总组数超时间池 / 单部位仅1种角度
"""

import json
from datetime import date, datetime
from pathlib import Path

from db import find_db_path, get_db, init_db

SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "calorie_data.db"
DB_PATH = find_db_path(SKILL_DIR, DB_FILENAME)
CATALOG_PATH = Path.home() / ".minimax" / "训记官方动作.json"

# ── 训练科学常量 ──
LEVEL_CONFIG = {
    "新手":  {"max_per_part_per_day": 6,  "max_per_part_per_week": 10,  "rest_hours": 72},
    "中手":  {"max_per_part_per_day": 10, "max_per_part_per_week": 20,  "rest_hours": 48},
    "老手":  {"max_per_part_per_day": 99, "max_per_part_per_week": 99,  "rest_hours": 48},
}

# 器材 → 需要的训练动作关键词映射
EQUIPMENT_KEYWORDS = {
    "悍马机":    ["悍马机","悍马","坐姿器械","器械划船","器械推胸"],
    "蝴蝶机":    ["蝴蝶机"],
    "史密斯机":  ["史密斯"],
    "哑铃":      ["哑铃"],
    "杠铃":      ["杠铃","卧推","划船","硬拉","深蹲"],
    "绳索":      ["绳索","龙门架"],
    "健腹轮":    ["健腹轮"],
    "弹力带":    ["弹力带"],
    "瑜伽垫":    ["平板","俯卧撑","卷腹","臀桥","支撑"],
}


def _get_db():
    if not DB_PATH.exists():
        init_db(DB_PATH)
    return get_db(DB_PATH)


def load_catalog():
    """加载训记官方动作库"""
    if CATALOG_PATH.exists():
        with open(CATALOG_PATH, encoding='utf-8') as f:
            data = json.load(f)
            return set(data.get("actions", []))
    return set()


def infer_equipment(movement_name):
    """从动作名推断所需器材"""
    for equip, keywords in EQUIPMENT_KEYWORDS.items():
        for kw in keywords:
            if kw in movement_name:
                return equip
    return None


def validate_plan(plan_json):
    """校验计划，返回 (errors: list[str], warnings: list[str])"""
    errors = []
    warnings = []
    catalog = load_catalog()
    config = plan_json.get("config", {})
    level = config.get("user_level", "中手")
    available_equip = config.get("available_equipment", [])
    lvl = LEVEL_CONFIG.get(level, LEVEL_CONFIG["中手"])
    weeks = plan_json.get("weeks", [])

    if not weeks:
        errors.append("weeks 为空")
        return errors, warnings

    total_weeks = len(weeks)

    # 收集所有部位出现日期
    from collections import defaultdict
    part_dates = defaultdict(list)  # part → [(week, dow)]
    part_day_sets = defaultdict(lambda: defaultdict(int))  # (week,dow) → {part: sets}

    for week in weeks:
        wn = week.get("week_number", 0)
        for day in week.get("days", []):
            dow = day.get("day_of_week", 0)
            for sess in day.get("sessions", []):
                if sess.get("is_rest_day"):
                    continue
                for m in sess.get("movements", []):
                    name = m.get("name", "")
                    p = m.get("part", "")

                    # 硬止1：动作名在校验库中
                    if catalog and name not in catalog:
                        errors.append(f"动作不在训记官方库：{name}")

                    # 硬止2：器材检查
                    equip = infer_equipment(name)
                    if equip and equip not in available_equip:
                        errors.append(f"缺少器材 {equip}（动作：{name}）")

                    # 统计部位组数
                    total_sets = len(m.get("sets", []))
                    part_day_sets[(wn, dow)][p] += total_sets
                    part_dates[p].append((wn, dow))

    # 硬止3：同部位间隔 ≥ 48h
    rest_hours = lvl["rest_hours"]
    min_days = max(rest_hours // 24, 2)  # 至少间1天
    for p, occurrences in part_dates.items():
        occurrences.sort()
        for i in range(1, len(occurrences)):
            prev_wn, prev_dow = occurrences[i-1]
            curr_wn, curr_dow = occurrences[i]
            gap = (curr_wn - prev_wn) * 7 + (curr_dow - prev_dow)
            if gap < min_days:
                errors.append(f"部位「{p}」间隔仅 {gap} 天，建议 ≥ {min_days} 天（第{prev_wn}周周{prev_dow} → 第{curr_wn}周周{curr_dow}）")

    # 软提示：单日单部位超出建议组数
    for (wn, dow), parts in part_day_sets.items():
        for p, sets in parts.items():
            if sets > lvl["max_per_part_per_day"]:
                warnings.append(f"第{wn}周周{dow}·{p} {sets} 组，建议 ≤ {lvl['max_per_part_per_day']} 组")

    # 软提示：单部位仅 1 种角度
    for week in weeks:
        wn = week.get("week_number", 0)
        for day in week.get("days", []):
            dow = day.get("day_of_week", 0)
            day_parts = defaultdict(list)
            for sess in day.get("sessions", []):
                if sess.get("is_rest_day"):
                    continue
                for m in sess.get("movements", []):
                    day_parts[m.get("part", "?")].append(m.get("type", "?"))
            for p, types in day_parts.items():
                if len(types) >= 2 and all(t == types[0] for t in types):
                    warnings.append(f"第{wn}周周{dow}·{p} 仅一种训练类型({types[0]})，建议增加不同角度")

    return errors, warnings


def write_plan(plan_json, dry_run=False):
    """校验 + 写入 DB。

    Args:
        plan_json: 采访流程输出的完整计划
        dry_run: True 时只校验不写入

    Returns:
        dict: {errors, warnings, inserted_count, total_weeks}
    """
    errors, warnings = validate_plan(plan_json)

    if dry_run:
        return {"errors": errors, "warnings": warnings, "inserted_count": 0, "dry_run": True}

    if errors:
        return {"errors": errors, "warnings": warnings, "inserted_count": 0, "status": "failed"}

    config = plan_json.get("config", {})
    weeks = plan_json.get("weeks", [])
    total_weeks = len(weeks)

    conn = _get_db()
    c = conn.cursor()

    # 写入 workout_plan_config（覆盖旧计划）
    c.execute('DELETE FROM workout_plan_config')
    c.execute('''
        INSERT INTO workout_plan_config (title, version, description, total_weeks, start_date)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        config.get("title", ""),
        config.get("version", "v1"),
        config.get("description", ""),
        total_weeks,
        config.get("start_date", date.today().strftime("%Y-%m-%d")),
    ))

    # 写入 workout_plans（先清旧数据再插入新计划）
    c.execute('DELETE FROM workout_plans')
    inserted = 0
    for week in weeks:
        wn = week.get("week_number", 0)
        for day in week.get("days", []):
            dow = day.get("day_of_week", 0)
            for si, sess in enumerate(day.get("sessions", []), 1):
                movements_json = json.dumps(sess.get("movements", []), ensure_ascii=False)
                c.execute('''
                    INSERT INTO workout_plans
                        (week_number, day_of_week, session_index, session_label,
                         time_start, time_end, is_rest_day, total_sets, movements)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    wn, dow, si,
                    sess.get("session_label", ""),
                    sess.get("time_start"),
                    sess.get("time_end"),
                    1 if sess.get("is_rest_day") else 0,
                    sess.get("total_sets"),
                    movements_json,
                ))
                inserted += 1

    conn.commit()
    conn.close()
    return {
        "errors": [], "warnings": warnings,
        "inserted_count": inserted, "total_weeks": total_weeks,
        "status": "ok",
    }


# ═══════════════════════════════════════════════════════════
# 增量 CRUD（不重写全表）
# ═══════════════════════════════════════════════════════════

def update_config(**fields):
    """更新 workout_plan_config 的一个或多个字段。

    fields: title, version, description, start_date
    Returns: True if updated, False if config not found.
    """
    allowed = {'title', 'version', 'description', 'start_date'}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return False

    sets = ', '.join(f'{k}=?' for k in updates)
    values = list(updates.values())

    conn = _get_db()
    c = conn.cursor()
    c.execute(f'UPDATE workout_plan_config SET {sets}, updated_at=CURRENT_TIMESTAMP WHERE id=1', values)
    affected = c.rowcount > 0
    conn.commit()
    conn.close()
    return affected


def add_session(session):
    """新增一个训练时段。

    session 必含: week_number, day_of_week, session_label, movements
    可选: time_start, time_end, is_rest_day, total_sets

    会自动分配 session_index（取当天最大值+1）。
    """
    conn = _get_db()
    c = conn.cursor()

    wn = session['week_number']
    dow = session['day_of_week']
    c.execute('SELECT COALESCE(MAX(session_index),0)+1 FROM workout_plans WHERE week_number=? AND day_of_week=?', (wn, dow))
    si = c.fetchone()[0]

    c.execute('''
        INSERT INTO workout_plans
            (week_number, day_of_week, session_index, session_label,
             time_start, time_end, is_rest_day, total_sets, movements)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        wn, dow, si,
        session.get('session_label', ''),
        session.get('time_start'),
        session.get('time_end'),
        1 if session.get('is_rest_day') else 0,
        session.get('total_sets'),
        json.dumps(session.get('movements', []), ensure_ascii=False),
    ))
    conn.commit()
    conn.close()
    return {'week_number': wn, 'day_of_week': dow, 'session_index': si}


def update_session(wn, dow, si, **fields):
    """更新一个训练时段的部分字段。

    fields 可含: session_label, time_start, time_end, is_rest_day, total_sets, movements
    Returns: True if updated, False if not found.
    """
    allowed = {'session_label', 'time_start', 'time_end', 'is_rest_day', 'total_sets', 'movements'}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return False

    if 'movements' in updates and not isinstance(updates['movements'], str):
        updates['movements'] = json.dumps(updates['movements'], ensure_ascii=False)
    if 'is_rest_day' in updates:
        updates['is_rest_day'] = 1 if updates['is_rest_day'] else 0

    sets = ', '.join(f'{k}=?' for k in updates)
    values = list(updates.values()) + [wn, dow, si]

    conn = _get_db()
    c = conn.cursor()
    c.execute(f'UPDATE workout_plans SET {sets}, updated_at=CURRENT_TIMESTAMP WHERE week_number=? AND day_of_week=? AND session_index=?', values)
    affected = c.rowcount > 0
    conn.commit()
    conn.close()
    return affected


def delete_session(wn, dow, si):
    """删除一个训练时段。"""
    conn = _get_db()
    c = conn.cursor()
    c.execute('DELETE FROM workout_plans WHERE week_number=? AND day_of_week=? AND session_index=?', (wn, dow, si))
    affected = c.rowcount > 0
    conn.commit()
    conn.close()
    return affected


def copy_week(from_wn, to_wn):
    """复制一整周数据到新周号（覆盖目标周已有数据）。

    from_wn: 源周号
    to_wn: 目标周号
    Returns: 复制的行数
    """
    conn = _get_db()
    c = conn.cursor()
    c.execute('DELETE FROM workout_plans WHERE week_number=?', (to_wn,))
    c.execute('''
        INSERT INTO workout_plans
            (week_number, day_of_week, session_index, session_label,
             time_start, time_end, is_rest_day, total_sets, movements)
        SELECT ?, day_of_week, session_index, session_label,
               time_start, time_end, is_rest_day, total_sets, movements
        FROM workout_plans WHERE week_number=?
    ''', (to_wn, from_wn))
    count = c.rowcount

    # 更新 total_weeks 如果目标周超出范围
    c.execute('UPDATE workout_plan_config SET total_weeks=MAX(total_weeks,?) WHERE id=1', (to_wn,))
    conn.commit()
    conn.close()
    return {'copied_rows': count, 'from_week': from_wn, 'to_week': to_wn}


def delete_week(wn):
    """删除一整周。

    注意事项：
    - 删除后，week_number > wn 的行会减 1 以保持连续
    - total_weeks 会减 1
    """
    conn = _get_db()
    c = conn.cursor()
    c.execute('DELETE FROM workout_plans WHERE week_number=?', (wn,))
    c.execute('''
        UPDATE workout_plans
        SET week_number = week_number - 1
        WHERE week_number > ?
    ''', (wn,))
    c.execute('UPDATE workout_plan_config SET total_weeks=total_weeks-1 WHERE id=1 AND total_weeks>1')
    conn.commit()
    conn.close()
    return {'deleted_week': wn}


def insert_week(wn):
    """在第 wn 周前插入空白周。

    当前第 wn 周及之后的周次全部后移 1 位，total_weeks+1。
    新插入的周为空白（0 行），需要后续 add_session 填充。
    """
    conn = _get_db()
    c = conn.cursor()
    c.execute('''
        UPDATE workout_plans
        SET week_number = week_number + 1
        WHERE week_number >= ?
    ''', (wn,))
    c.execute('UPDATE workout_plan_config SET total_weeks=total_weeks+1 WHERE id=1')
    conn.commit()
    conn.close()
    return {'inserted_at_week': wn}
