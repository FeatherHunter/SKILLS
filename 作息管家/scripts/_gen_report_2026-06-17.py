#!/usr/bin/env python3
"""
为 2026-06-17 生成每日作息报告
1. 补全 00:00-06:15 睡眠记录（默认填充，接续前一天 22:56 入睡）
2. 按分类汇总 total_minutes
3. 调用 add_summary() 写入 daily_summary
4. 生成 HTML 报告
"""

import sys
import json
from datetime import datetime, date
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))
from schedule_db import (
    get_records_by_date, add_record_full, add_summary,
    get_daily_summary, get_plan
)

# ============ 配置 ============
TARGET_DATE = "2026-06-17"
SKILL_DIR = Path(__file__).parent.parent
REPORT_PATH = SKILL_DIR / "reports" / f"{TARGET_DATE}.html"

# ============ 0. 验证是否需要补全 ============
records = get_records_by_date(TARGET_DATE)
print(f"补全前 {len(records)} 条记录")
print(f"首条: {records[0]['time_start']}")
print(f"末条: {records[-1]['time_end']}")

first_start = records[0]['time_start']
if first_start != '00:00':
    print(f"\n⚠️ 首条记录开始时间为 {first_start}，不是 00:00")
    print(f"补全 00:00 ~ {first_start} 睡眠记录（默认填充）")
    
    # 计算 duration
    h, m = map(int, first_start.split(':'))
    duration = h * 60 + m
    
    # 添加默认填充记录
    add_record_full(
        date=TARGET_DATE,
        time_start='00:00',
        time_end=first_start,
        duration_minutes=duration,
        activity=f'凌晨睡眠（接续6月16日22:56入睡）',
        category='睡眠',
        source_contents=f'前一天末条记录 2026-06-16 22:56~06:15 [睡眠] 覆盖此时间段；00:00~{first_start} 期间无新消息（默认填充）',
        source_timestamps='2026-06-16 22:56',
        analysis_reasoning=f'默认填充：今日首条记录 {first_start}（用户醒来），前一天 2026-06-16 22:56~06:15 [睡眠] 跨午夜延伸到 2026-06-17 06:15。补充 00:00~{first_start} 睡眠记录以确保当日记录覆盖 00:00-23:59'
    )
    print(f"  ✓ 添加 00:00~{first_start} 睡眠记录")
    
    # 重新读取
    records = get_records_by_date(TARGET_DATE)
    print(f"补全后 {len(records)} 条记录")
else:
    print("首条已为 00:00，无需补全")

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

# ============ 2. 按细化分类汇总 ============
cat_minutes = defaultdict(int)
cat_records = defaultdict(list)
for r in records:
    final_cat = refine_category(r)
    cat_minutes[final_cat] += r['duration_minutes']
    cat_records[final_cat].append(r)

print()
print("细化后分类汇总:")
total_check = 0
for cat, mins in sorted(cat_minutes.items(), key=lambda x: -x[1]):
    print(f"  {cat}: {mins}min = {mins//60}h{mins%60}m")
    total_check += mins
print(f"  合计: {total_check}min = {total_check//60}h{total_check%60}m")

# ============ 3. 验证是否覆盖 24h ============
if total_check >= 1440:
    print(f"  ✓ 总计 {total_check}min >= 1440min (24h)，满足摘要生成条件")
else:
    print(f"  ⚠️ 总计 {total_check}min < 1440min (24h)，不满足摘要生成条件")
    print("  仍继续生成报告（基于现有数据）")

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

# ============ 5. 计算时间轴（每小时主分类）============
hours = [None] * 24  # 每小时主分类
for r in records:
    final_cat = refine_category(r)
    try:
        h_start = int(r['time_start'].split(':')[0])
        if r['time_end'] == '23:59':
            h_end = 23
        else:
            h_end = int(r['time_end'].split(':')[0])
        for h in range(h_start, h_end + 1):
            if h < 24 and hours[h] is None:
                hours[h] = final_cat
    except:
        pass

# 填充空白小时（向前找）
last_cat = None
for i, h in enumerate(hours):
    if h is None:
        hours[i] = last_cat if last_cat else '休息'
    else:
        last_cat = h

# ============ 6. 计算分类颜色映射 ============
color_map = {
    "睡眠": "#5E5CE6",
    "工作": "#007AFF",
    "学习": "#34C759",
    "运动": "#FF9500",
    "通勤": "#64D2FF",
    "餐饮": "#FF9F0A",
    "娱乐": "#AF52DE",
    "社交": "#FF2D55",
    "休闲": "#30D158",
    "健康": "#FF3B30",
    "洗漱": "#5AC8FA",
    "兴趣爱好": "#BF8F5F",
    "居家": "#BF8F5F",
    "家务": "#A2845E",
    "生活": "#8E8E93",
    "未知": "#8E8E93",
    "休息": "#8E8E93",
}

emoji_map = {
    "睡眠": "😴",
    "工作": "💼",
    "学习": "📚",
    "运动": "🏋️",
    "通勤": "🚴",
    "餐饮": "🍽️",
    "娱乐": "🎮",
    "社交": "💕",
    "休闲": "🛋️",
    "健康": "🏥",
    "洗漱": "🚿",
    "兴趣爱好": "🎨",
    "居家": "🏠",
    "家务": "🧹",
    "生活": "🌱",
    "未知": "❓",
    "休息": "🛋️",
}

# ============ 7. 准备数据供 HTML 生成 ============
plan = get_plan(TARGET_DATE)
sleep_records = [r for r in records if refine_category(r) == '睡眠']
sleep_records.sort(key=lambda x: -x['duration_minutes'])
main_sleep = sleep_records[0] if sleep_records else None
work_records = [r for r in records if refine_category(r) == '工作']
commute_records = [r for r in records if refine_category(r) == '通勤']
meal_records = [r for r in records if refine_category(r) == '餐饮']

# 输出 JSON 数据供 HTML 生成
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
    'plan': plan,
    'records': [
        {
            'time_start': r['time_start'],
            'time_end': r['time_end'],
            'duration_minutes': r['duration_minutes'],
            'category': refine_category(r),
            'activity': r['activity']
        }
        for r in records
    ]
}

with open('/tmp/report_data_2026-06-17.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2, default=str)

print()
print(f"数据已保存到 /tmp/report_data_2026-06-17.json")
print()
print(f"📌 计划: {'有' if plan else '无'}")
print(f"📌 总记录: {len(records)}")
print(f"📌 睡眠段数: {len(sleep_records)}")
print(f"📌 工作段数: {len(work_records)}")
print(f"📌 通勤段数: {len(commute_records)}")
print(f"📌 餐饮段数: {len(meal_records)}")
