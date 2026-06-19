#!/usr/bin/env python3
"""
为 2026-06-18 生成每日作息报告
1. 验证记录是否覆盖 00:00-23:59
2. 按分类汇总 total_minutes
3. 调用 add_summary() 写入 daily_summary
4. 保存 JSON 数据供 HTML 渲染
"""

import sys
import json
from datetime import datetime, date
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))
from schedule_db import (
    get_records_by_date, add_summary,
    get_daily_summary, get_plan
)

# ============ 配置 ============
TARGET_DATE = "2026-06-18"
SKILL_DIR = Path(__file__).parent.parent

# ============ 0. 验证记录覆盖 ============
records = get_records_by_date(TARGET_DATE)
print(f"获取 {len(records)} 条记录")
print(f"首条: {records[0]['time_start']}")
print(f"末条: {records[-1]['time_end']}")

first_start = records[0]['time_start']
last_end = records[-1]['time_end']

# 验证时间连续性
gaps = []
for i in range(1, len(records)):
    prev_end = records[i-1]['time_end']
    cur_start = records[i]['time_start']
    if prev_end != cur_start:
        gaps.append((i, prev_end, cur_start))

if gaps:
    print(f"\n⚠️ 发现 {len(gaps)} 处时间断点:")
    for idx, pe, cs in gaps:
        print(f"  [{idx}] prev_end={pe} → cur_start={cs}")
else:
    print("✓ 时间完全连续，无断点")

# ============ 1. 智能分类映射 ============
def refine_category(rec):
    """根据 activity 内容细化分类"""
    orig_cat = rec['category']
    activity = rec['activity']

    # 休息分类细化：长睡/午睡→睡眠；短休→休闲
    if orig_cat == '休息':
        if rec['duration_minutes'] >= 60:
            return '睡眠'
        if any(kw in activity for kw in ['睡眠', '睡觉', '午睡', '躺床休息']):
            return '睡眠'
        if rec['duration_minutes'] <= 2:
            return '休闲'
        return '休闲'

    return orig_cat

# 应用 refine
records_refined = [
    {**r, 'category': refine_category(r)} for r in records
]

# ============ 2. 按细化分类汇总 ============
cat_minutes = defaultdict(int)
cat_records = defaultdict(list)
for r in records_refined:
    cat_minutes[r['category']] += r['duration_minutes']
    cat_records[r['category']].append(r)

print()
print("细化后分类汇总:")
total_check = 0
for cat, mins in sorted(cat_minutes.items(), key=lambda x: -x[1]):
    print(f"  {cat}: {mins}min = {mins//60}h{mins%60}m")
    total_check += mins
print(f"  合计: {total_check}min = {total_check//60}h{total_check%60}m")

# ============ 3. 验证是否覆盖 24h ============
print()
if first_start == '00:00' and last_end == '23:59':
    print(f"✓ 首条 {first_start} ~ 末条 {last_end}，覆盖 00:00-23:59")
    if total_check >= 1439:
        print(f"✓ 总计 {total_check}min 满足 24h 覆盖")
    else:
        print(f"⚠️ 总计 {total_check}min < 1439min")
else:
    print(f"⚠️ 首条 {first_start} 或末条 {last_end} 不满足 00:00-23:59 覆盖")

# ============ 4. 调用 add_summary 写入 daily_summary ============
print()
print("写入 daily_summary...")
for cat, mins in cat_minutes.items():
    result = add_summary(TARGET_DATE, cat, mins)
    print(f"  ✓ {cat}: {mins}min")

# 验证
print()
print("验证写入结果:")
saved = get_daily_summary(TARGET_DATE)
for item in saved:
    print(f"  {item['category']}: {item['total_minutes']}min")
print(f"共 {len(saved)} 条")

# ============ 5. 计算时间轴（每小时主分类，按分钟覆盖）============
hours = [None] * 24
hour_minutes = [defaultdict(int) for _ in range(24)]
for r in records_refined:
    try:
        h_start = int(r['time_start'].split(':')[0])
        s_min = int(r['time_start'].split(':')[1])
        if r['time_end'] == '23:59':
            e_min_total = 23 * 60 + 59
        elif r['time_end'] == '24:00':
            e_min_total = 24 * 60
        else:
            eh, em = map(int, r['time_end'].split(':'))
            e_min_total = eh * 60 + em
        s_min_total = h_start * 60 + s_min
        cur = s_min_total
        while cur < e_min_total:
            h = cur // 60
            if h < 24:
                next_hour = (h + 1) * 60
                covered = min(next_hour, e_min_total) - cur
                hour_minutes[h][r['category']] += covered
                cur = next_hour
            else:
                break
    except Exception as e:
        pass

# 取每小时主导分类
for h in range(24):
    if hour_minutes[h]:
        hours[h] = max(hour_minutes[h].items(), key=lambda x: x[1])[0]
    else:
        hours[h] = '休息'

# 填充空白小时（向前找）
last_cat = None
for i, h in enumerate(hours):
    if h is None:
        hours[i] = last_cat if last_cat else '休息'
    else:
        last_cat = h

# ============ 6. 计算颜色 emoji 映射 ============
color_map = {
    "睡眠": "#5E5CE6", "工作": "#007AFF", "学习": "#34C759", "运动": "#FF9500",
    "通勤": "#64D2FF", "餐饮": "#FF9F0A", "娱乐": "#AF52DE", "社交": "#FF2D55",
    "休闲": "#30D158", "健康": "#FF3B30", "洗漱": "#5AC8FA", "兴趣爱好": "#BF8F5F",
    "居家": "#BF8F5F", "家政家务": "#A2845E", "居家管理": "#A2845E",
    "家务": "#A2845E", "生活": "#8E8E93", "未知": "#8E8E93", "休息": "#8E8E93",
}

emoji_map = {
    "睡眠": "😴", "工作": "💼", "学习": "📚", "运动": "🏋️",
    "通勤": "🚴", "餐饮": "🍽️", "娱乐": "🎮", "社交": "💕",
    "休闲": "🛋️", "健康": "🏥", "洗漱": "🚿", "兴趣爱好": "🎨",
    "居家": "🏠", "家政家务": "🧹", "居家管理": "🧹",
    "家务": "🧹", "生活": "🌱", "未知": "❓", "休息": "🛋️",
}

# ============ 7. 准备数据 ============
plan = get_plan(TARGET_DATE)
sleep_records = [r for r in records_refined if r['category'] == '睡眠']
sleep_records.sort(key=lambda x: -x['duration_minutes'])
main_sleep = sleep_records[0] if sleep_records else None
work_records = [r for r in records_refined if r['category'] == '工作']
commute_records = [r for r in records_refined if r['category'] == '通勤']
meal_records = [r for r in records_refined if r['category'] == '餐饮']
health_records = [r for r in records_refined if r['category'] == '健康']

# 输出 JSON 数据
data = {
    'date': TARGET_DATE,
    'total_records': len(records),
    'total_minutes': total_check,
    'total_hours': total_check / 60,
    'cat_minutes': dict(cat_minutes),
    'hours': hours,
    'main_sleep': main_sleep,
    'sleep_records': sleep_records,
    'work_records': work_records,
    'commute_records': commute_records,
    'meal_records': meal_records,
    'health_records': health_records,
    'plan': plan,
    'records': [
        {
            'time_start': r['time_start'],
            'time_end': r['time_end'],
            'duration_minutes': r['duration_minutes'],
            'category': r['category'],
            'activity': r['activity']
        }
        for r in records_refined
    ]
}

JSON_PATH = Path(f'/tmp/report_data_{TARGET_DATE}.json')
with open(JSON_PATH, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2, default=str)

print()
print(f"数据已保存到 {JSON_PATH}")
print()
print(f"📌 计划: {'有' if plan else '无'}")
print(f"📌 总记录: {len(records)}")
print(f"📌 睡眠段数: {len(sleep_records)}")
print(f"📌 健康段数: {len(health_records)}")
print(f"📌 工作段数: {len(work_records)}")
print(f"📌 通勤段数: {len(commute_records)}")
print(f"📌 餐饮段数: {len(meal_records)}")
