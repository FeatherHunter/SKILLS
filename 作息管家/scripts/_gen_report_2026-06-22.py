#!/usr/bin/env python3
"""
为 2026-06-22 生成每日作息报告
1. 验证记录是否覆盖 00:00-23:59
2. 验证时间连续性（首尾相接）
3. 按真实时间差计算每个分类的 total_minutes
4. 调用 add_summary() 写入 daily_summary
5. 保存 JSON 数据供 HTML 渲染
"""

import sys
import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))
from schedule_db import (
    get_records_by_date, add_summary,
    get_daily_summary, get_plan
)

# ============ 配置 ============
TARGET_DATE = "2026-06-22"
SKILL_DIR = Path(__file__).parent.parent

# ============ 0. 验证记录覆盖 ============
records = get_records_by_date(TARGET_DATE)
print(f"获取 {len(records)} 条记录")
print(f"首条: {records[0]['time_start']} ~ {records[0]['time_end']}")
print(f"末条: {records[-1]['time_start']} ~ {records[-1]['time_end']}")

# 计算真实时长（time_end - time_start，按分钟）
def calc_duration(ts, te):
    sh, sm = map(int, ts.split(':'))
    eh, em = map(int, te.split(':'))
    return (eh * 60 + em) - (sh * 60 + sm)

# ============ 1. 时间连续性验证 ============
print("\n========== 时间连续性验证 ==========")
prev_end = None
gaps = []
total_real = 0
for i, r in enumerate(records):
    real_dur = calc_duration(r['time_start'], r['time_end'])
    total_real += real_dur
    if prev_end is not None and r['time_start'] != prev_end:
        gaps.append((i, prev_end, r['time_start']))
    prev_end = r['time_end']

if gaps:
    print(f"⚠️ 发现 {len(gaps)} 处时间断点:")
    for idx, pe, cs in gaps:
        print(f"  [idx={idx}] prev_end={pe} → cur_start={cs}")
else:
    print("✓ 时间完全连续，无断点")

# ============ 2. 检查 stored duration_minutes 与真实时间差 ============
print("\n========== duration_minutes 字段一致性检查 ==========")
mismatches = []
for r in records:
    real_dur = calc_duration(r['time_start'], r['time_end'])
    if real_dur != r['duration_minutes']:
        mismatches.append({
            'id': r['id'],
            'ts': r['time_start'],
            'te': r['time_end'],
            'stored': r['duration_minutes'],
            'real': real_dur,
            'activity': r['activity']
        })

if mismatches:
    print(f"⚠️ 发现 {len(mismatches)} 条记录 duration_minutes 与实际不符:")
    for m in mismatches:
        print(f"  id={m['id']} {m['ts']}~{m['te']} stored={m['stored']} real={m['real']} diff={m['real']-m['stored']}")
        print(f"    activity: {m['activity'][:60]}")
else:
    print("✓ 所有记录 duration_minutes 字段一致")

# ============ 3. 验证 24h 覆盖 ============
print("\n========== 24h 覆盖验证 ==========")
first_start = records[0]['time_start']
last_end = records[-1]['time_end']
total_stored = sum(r['duration_minutes'] for r in records)

if first_start == '00:00':
    print(f"✓ 首条 {first_start} 从 00:00 开始")
else:
    print(f"⚠️ 首条 {first_start} 不是 00:00")

if last_end == '23:59':
    print(f"✓ 末条 {last_end} 覆盖到 23:59")
else:
    print(f"⚠️ 末条 {last_end} 不是 23:59")

print(f"\n真实总时长: {total_real} min = {total_real//60}h{total_real%60}m")
print(f"存储总时长: {total_stored} min = {total_stored//60}h{total_stored%60}m")
print(f"差值: {total_real - total_stored} min (应为0)")

if first_start == '00:00' and last_end == '23:59' and not gaps:
    print("\n✅ 满足满24小时条件（首尾相接、覆盖00:00~23:59）")
    coverage_ok = True
else:
    print("\n❌ 不满足满24小时条件")
    coverage_ok = False

if not coverage_ok:
    print("\n不满足条件，跳过 add_summary 写入和报告生成")
    sys.exit(1)

# ============ 4. 按真实时间差计算分类汇总 ============
print("\n========== 按分类汇总（真实时间差） ==========")

records_refined = []
for r in records:
    new_rec = {**r}
    new_rec['real_duration'] = calc_duration(r['time_start'], r['time_end'])
    records_refined.append(new_rec)

# 按分类汇总
cat_minutes = defaultdict(int)
cat_records = defaultdict(list)
for r in records_refined:
    cat_minutes[r['category']] += r['real_duration']
    cat_records[r['category']].append(r)

total_check = sum(cat_minutes.values())
print(f"总计: {total_check} min = {total_check//60}h{total_check%60}m")
print("\n各分类汇总:")
for cat, mins in sorted(cat_minutes.items(), key=lambda x: -x[1]):
    pct = mins / total_check * 100
    print(f"  {cat}: {mins}min = {mins//60}h{mins%60}m ({pct:.1f}%)")

# ============ 5. 验证总计 = 1439 分钟（24h - 1min） ============
print()
if total_check == 1439:
    print("✓ 总计 1439 min 正好覆盖 24h")
else:
    print(f"⚠️ 总计 {total_check} min != 1439 min")

# ============ 6. 写入 daily_summary ============
print("\n========== 写入 daily_summary ==========")
for cat, mins in cat_minutes.items():
    result = add_summary(TARGET_DATE, cat, mins)
    print(f"  ✓ {cat}: {mins}min")

# 验证写入
print("\n验证写入结果:")
saved = get_daily_summary(TARGET_DATE)
for item in saved:
    print(f"  {item['category']}: {item['total_minutes']}min")
print(f"共 {len(saved)} 条")

# ============ 7. 计算时间轴（每小时主导分类） ============
print("\n========== 计算时间轴 ==========")
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

hours = []
for h in range(24):
    if hour_minutes[h]:
        hours.append(max(hour_minutes[h].items(), key=lambda x: x[1])[0])
    else:
        hours.append('休息')

# ============ 8. 准备数据 ============
plan = get_plan(TARGET_DATE)
sleep_records = [r for r in records_refined if r['category'] == '睡眠']
sleep_records.sort(key=lambda x: -x['real_duration'])
main_sleep = sleep_records[0] if sleep_records else None
work_records = [r for r in records_refined if r['category'] == '工作']
commute_records = [r for r in records_refined if r['category'] == '通勤']
meal_records = [r for r in records_refined if r['category'] == '餐饮']
health_records = [r for r in records_refined if r['category'] == '健康']
study_records = [r for r in records_refined if r['category'] == '学习']
leisure_records = [r for r in records_refined if r['category'] == '休闲']
entertainment_records = [r for r in records_refined if r['category'] == '娱乐']

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
    'study_records': study_records,
    'leisure_records': leisure_records,
    'entertainment_records': entertainment_records,
    'plan': plan,
    'mismatches': mismatches,
    'records': [
        {
            'id': r['id'],
            'time_start': r['time_start'],
            'time_end': r['time_end'],
            'duration_minutes': r['real_duration'],
            'category': r['category'],
            'activity': r['activity']
        }
        for r in records_refined
    ]
}

JSON_PATH = Path(f'/tmp/report_data_{TARGET_DATE}.json')
with open(JSON_PATH, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2, default=str)

print(f"\n数据已保存到 {JSON_PATH}")

print(f"\n========== 摘要统计 ==========")
print(f"📌 计划: {'有' if plan else '无'}")
print(f"📌 总记录块: {len(records)}")
print(f"📌 真实总时长: {total_check} min ({total_check/60:.1f}h)")
print(f"📌 分类数: {len(cat_minutes)}")
print(f"📌 睡眠段数: {len(sleep_records)}")
if main_sleep:
    print(f"📌 主睡眠: {main_sleep['time_start']}~{main_sleep['time_end']} ({main_sleep['real_duration']}min)")
print(f"📌 工作段数: {len(work_records)}")
print(f"📌 通勤段数: {len(commute_records)}")
print(f"📌 餐饮段数: {len(meal_records)}")
print(f"📌 健康段数: {len(health_records)}")
print(f"📌 学习段数: {len(study_records)}")
print(f"📌 娱乐段数: {len(entertainment_records)}")
print(f"📌 休闲段数: {len(leisure_records)}")
print(f"📌 洗漱段数: {len([r for r in records_refined if r['category'] == '洗漱'])}")
print(f"📌 兴趣爱好段数: {len([r for r in records_refined if r['category'] == '兴趣爱好'])}")
print(f"📌 社交段数: {len([r for r in records_refined if r['category'] == '社交'])}")
