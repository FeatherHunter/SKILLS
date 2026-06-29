#!/usr/bin/env python3
"""运动记录 — 运动添加/查询/汇总

数据存储：exercise_log 表
- exercise_type, duration_minutes, calories_burned, reps
- 支持 reps（次数）字段，如俯卧撑 20 个

注意：exercise_tracker.py 是更完整的 CLI（add/update/list/summary/stats/trend），
本模块仅提供 calorie_tracker.py 内部需要的核心 add/list/summary。
"""

import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from db import find_db_path, get_db, init_db

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "calorie_data.db"
DB_PATH = find_db_path(SKILL_DIR, DB_FILENAME)


def _get_db():
    if not DB_PATH.exists():
        init_db(DB_PATH)
    return get_db(DB_PATH)


def add_exercise(exercise_type, calories_burned, duration_minutes=None, reps=None,
                 note='', target_date=None, target_time=None):
    """记录运动消耗

    Args:
        exercise_type: 运动类型，如 '跑步'、'钻石俯卧撑'
        calories_burned: 消耗卡路里
        duration_minutes: 运动时长（分钟），可选
        reps: 动作次数，如 20 个，可选
        note: 备注
        target_date: 目标日期（YYYY-MM-DD），默认今天
        target_time: 目标时间（HH:MM:SS），可选
    """
    if target_date is None:
        target_date = date.today().strftime('%Y-%m-%d')

    conn = _get_db()
    c = conn.cursor()
    c.execute('''
        INSERT INTO exercise_log (date, time, exercise_type, duration_minutes, calories_burned, note, reps)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (target_date, target_time or '', exercise_type, duration_minutes, calories_burned, note, reps))
    conn.commit()
    conn.close()

    reps_str = f" {reps}个" if reps else ""
    dur_str = f" {duration_minutes}分钟" if duration_minutes else ""
    print(f"✓ 已记录运动：{exercise_type}{reps_str}{dur_str} {calories_burned}卡")


def get_exercise_log(target_date=None, days=7):
    """获取运动记录

    Args:
        target_date: 查询日期（单日），可选
        days: 查询近 N 天（默认 7）

    Returns:
        list of Row
    """
    conn = _get_db()
    c = conn.cursor()

    if target_date:
        c.execute('''
            SELECT date, time, exercise_type, duration_minutes, calories_burned, note, reps
            FROM exercise_log
            WHERE date = ?
            ORDER BY time DESC
        ''', (target_date,))
    else:
        c.execute('''
            SELECT date, time, exercise_type, duration_minutes, calories_burned, note, reps
            FROM exercise_log
            WHERE date >= date('now', ?)
            ORDER BY date DESC, time DESC
        ''', (f'-{days} days',))

    rows = c.fetchall()
    conn.close()
    return rows


def print_exercise_summary(days=7):
    """显示近 N 天运动汇总（按日聚合 + 类型明细 + 日均）"""
    rows = get_exercise_log(days=days)
    if not rows:
        print(f"\n近{days}天无运动记录")
        return

    daily = defaultdict(list)
    for row in rows:
        daily[row[0]].append({
            'type': row[2],
            'cal': row[4],
            'dur': row[3],
            'reps': row[6]
        })

    total_cal = sum(sum(r['cal'] for r in items) for items in daily.values())
    total_days = len(daily)

    print(f"\n近{days}天运动汇总：{total_cal}卡 / {total_days}天")
    print("-" * 50)
    for d, items in sorted(daily.items()):
        detail = []
        for r in items:
            s = f"{r['type']}"
            if r['reps']:
                s += f" {r['reps']}个"
            if r['dur']:
                s += f" {r['dur']}分钟"
            s += f" {r['cal']}卡"
            detail.append(s)
        print(f"  {d}: {' | '.join(detail)}")
    print(f"\n  日均: {total_cal / total_days:.0f}卡/天" if total_days else "")


# ============================================================
# 运动功能扩展 · 卡路里推算 / 强度估测 / 口语映射（2026-06-29）
# ============================================================

def _lookup_met(exercise_type):
    """查 METs 值（基于动作名关键词匹配，无数据库表）

    Returns:
        float: METs 值，兜底 3.0
    """
    if not exercise_type:
        return 3.0
    et = exercise_type.lower()

    # 力量训练（负重）
    if any(k in et for k in ['哑铃', '杠铃', '史密斯', '弯举', '推举', '推肩',
                             '平举', '深蹲', '卧推', '划船', '硬拉', '飞鸟']):
        return 5.0

    # 自重力量
    if any(k in et for k in ['俯卧撑', '引体', '自重', '平板']):
        return 3.8

    # 有氧
    if '跑步机' in et:
        return 7.5
    if '户外跑' in et or '路跑' in et:
        return 8.0
    if '慢跑' in et or '快跑' in et or '冲刺' in et:
        return 9.0
    if '跑' in et and '跑步机' not in et:
        return 8.0  # 兜底"跑步"类
    if '骑行' in et or '自行车' in et or '小黄车' in et or '骑车' in et:
        return 6.0
    if '跳绳' in et:
        return 12.0
    if '椭圆机' in et:
        return 5.5
    if '游泳' in et:
        return 7.0
    if 'hiit' in et:
        return 8.5

    # 柔韧 / 平衡
    if any(k in et for k in ['八段锦', '太极', '瑜伽', '拉伸', '冥想']):
        return 2.5

    # 日常活动
    if any(k in et for k in ['家务', '做饭', '洗衣', '打扫', '清洁']):
        return 2.5
    if '走路' in et or '散步' in et:
        return 3.0
    if '通勤' in et:
        return 2.5
    if '爬楼' in et or '楼梯' in et:
        return 4.0

    return 3.0  # 兜底


def _infer_category(exercise_type):
    """根据动作名推断 category：有氧/力量/柔韧/日常"""
    if not exercise_type:
        return '有氧'
    et = exercise_type

    # 力量
    if any(k in et for k in ['哑铃', '杠铃', '史密斯', '弯举', '推举', '推肩',
                             '平举', '前平举', '侧平举', '深蹲', '卧推', '划船',
                             '硬拉', '飞鸟', '俯卧撑', '引体', '自重', '平板']):
        return '力量'

    # 柔韧
    if any(k in et for k in ['八段锦', '太极', '瑜伽', '拉伸', '冥想']):
        return '柔韧'

    # 日常
    if any(k in et for k in ['家务', '做饭', '洗衣', '打扫', '清洁', '通勤', '走路', '散步', '爬楼']):
        return '日常'

    # 兜底：有氧
    return '有氧'


def estimate_calories_met(exercise_type, body_weight, duration_minutes=None,
                          sets=0, reps=0):
    """基于 METs × 体重 × 时长 推算卡路里

    公式（NSCA / ACSM 国际标准）：
      有氧/柔韧/日常：卡路里 = MET × 体重 × 时长(h)
      力量训练        ：卡路里 = MET × 体重 × 组数 × 0.05h（每组约 3 分钟含间歇）

    Args:
        exercise_type:    动作名（哑铃弯举/户外跑/八段锦/做饭 等）
        body_weight:      体重 kg
        duration_minutes: 时长分钟（有氧/柔韧/日常场景必填）
        sets:             力量场景的组数
        reps:             力量场景的总次数（保留参数，目前未参与公式）

    Returns:
        tuple: (calories_estimated: float, met_used: float)
    """
    met = _lookup_met(exercise_type)
    category = _infer_category(exercise_type)

    if category in ('有氧', '柔韧', '日常'):
        if not duration_minutes or duration_minutes <= 0:
            return (0.0, met)
        hours = duration_minutes / 60.0
        cal = met * body_weight * hours
    elif category == '力量':
        if sets <= 0:
            # 力量没组数则兜底按 1 组估
            sets = 1
        cal = met * body_weight * sets * 0.05
    else:
        cal = 0.0

    return (round(cal, 1), met)


def estimate_intensity_met(met):
    """基于 METs 估 4 档强度（无需心率，兜底用）

    映射规则：
      MET < 3   → 低     （散步、家务）
      MET 3-6   → 中     （快走、骑行、力量训练）
      MET 6-9   → 高     （跑步、跳绳）
      MET > 9   → 极限   （冲刺、HIIT）

    Args:
        met: METs 值

    Returns:
        str | None: '低' / '中' / '高' / '极限'，无法判断返回 None
    """
    if met is None or met <= 0:
        return None
    if met < 3:
        return '低'
    if met < 6:
        return '中'
    if met < 9:
        return '高'
    return '极限'


def parse_user_intensity(user_text):
    """口语化强度 → 4 档（用户主观感受优先于 METs 推算）

    Args:
        user_text: 用户描述（如"挺累的"、"轻松"、"累死"）

    Returns:
        str | None: '低' / '中' / '高' / '极限'，拿不准返回 None
    """
    if not user_text:
        return None
    t = user_text.lower()

    # 极限
    if any(k in t for k in ['累死', '力竭', '极限', '干不动', '暴毙', '撑不住', '想死', '不行']):
        return '极限'

    # 高
    if any(k in t for k in ['很累', '挺累', '暴汗', '喘', '气喘吁吁', '出汗多',
                             '冲', '狠', 'hard', 'hiit']):
        return '高'

    # 低
    if any(k in t for k in ['轻松', '没什么', '没感觉', '微微', '散步', 'easy', '很轻']):
        return '低'

    # 中
    if any(k in t for k in ['一般', '还行', '中等', '普通', '正常', '适中', '中等强度']):
        return '中'

    return None  # 拿不准不返回，让 AI 兜底


def combined_calories(user_reported, estimated, deviation_threshold_warning=0.5):
    """卡路里综合考虑：你报的 vs AI 推算，按偏差给出最终入档值

    规则：
      偏差 < 20%       → 取 AI 推算值
      偏差 20-50%      → 取两者中位 + note 标"差异大"
      偏差 > 50%       → 不直接入档，返回 None 让 AI 反问

    Args:
        user_reported:        用户报的卡路里（None 表示用户没报）
        estimated:            AI 推算的卡路里
        deviation_threshold_warning: 偏差阈值（默认 50%）

    Returns:
        tuple: (final_calories: float | None, note_suffix: str | None, deviation_pct: float)
            final_calories: 最终入档值；None 表示偏差过大需反问
            note_suffix:    要附加到 note 的说明文字
            deviation_pct:  偏差百分比（绝对值）
    """
    if user_reported is None:
        return (round(estimated, 1), None, 0.0)

    if estimated <= 0:
        return (float(user_reported), None, 0.0)

    deviation = abs(user_reported - estimated) / estimated

    if deviation < 0.20:
        # < 20% 取推算
        return (round(estimated, 1),
                f"你报 {user_reported}/AI {round(estimated,1)}/偏差 {int(deviation*100)}%",
                deviation)
    elif deviation < deviation_threshold_warning:
        # 20-50% 取中位
        mid = (user_reported + estimated) / 2
        return (round(mid, 1),
                f"你报 {user_reported}/AI {round(estimated,1)}/偏差 {int(deviation*100)}%/取中位",
                deviation)
    else:
        # > 50% 返回 None，反问
        return (None,
                f"你报 {user_reported}/AI {round(estimated,1)}/偏差 {int(deviation*100)}%/需确认",
                deviation)