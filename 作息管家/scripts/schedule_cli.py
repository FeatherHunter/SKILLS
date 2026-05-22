#!/usr/bin/env python3
"""
作息管家 - 主CLI脚本
功能:分析语录数据库 → 生成作息记录 → 提供查询接口

三层架构:
  1. schedule_db.py     → 数据库底层
  2. schedule_cli.py   → 本文件,AI分析+CLI逻辑
  3. SKILL.md          → 上层技能定义

增量同步逻辑(核心):
  下次继续从最新的最后一条记录开始
"""

import sys
import os
from datetime import datetime, date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from schedule_db import (
    init_db, get_last_record_full,
    get_messages_for_sync, get_messages_before, get_messages_from,
    add_record_full, get_records_by_date, get_records_range,
    has_records_for_date, get_daily_summary,
    get_summaries_range, get_connection, DB_PATH,
    upsert_plan, get_plan, get_plans
)

def calculate_daily_summary(records):
    """根据记录计算每日摘要"""
    summary = {
        "sleep": 0, "work": 0, "exercise": 0,
        "commute": 0, "eating": 0, "learning": 0,
        "entertainment": 0, "unknown": 0
    }

    category_map = {
        "睡眠": "sleep", "工作": "work", "运动": "exercise",
        "通勤": "commute", "餐饮": "eating", "学习": "learning",
        "娱乐": "entertainment", "未知": "unknown"
    }

    for rec in records:
        _, time_start, time_end, duration, activity, category, _, _, _ = rec
        minutes = duration or 0
        key = category_map.get(category, "unknown")
        summary[key] += minutes

    return summary

# ============ CLI 命令 ============
def cmd_prepare_messages(args):
    """
    准备同步消息:查询游标前10条(上下文) + 游标后新消息,输出JSON供AI分析
    用法:
      python schedule_cli.py prepare-messages                              # 默认: 从数据库游标到当前时间
      python schedule_cli.py prepare-messages <开始时间>                       # 指定开始时间到当前时间
      python schedule_cli.py prepare-messages <开始时间> <结束时间>            # 指定时间范围
    时间格式: YYYY-MM-DD HH:MM:SS  或  YYYY-MM-DD
    示例: python schedule_cli.py prepare-messages 2026-05-09 2026-05-22
    """
    import json
    from datetime import datetime, timedelta

    # 解析参数
    start_time_str = None
    end_time_str = None
    use_db_cursor = True

    if len(args) >= 1:
        use_db_cursor = False
        start_time_str = args[0]
        if len(args) >= 2:
            end_time_str = args[1]
        else:
            end_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # 格式化时间
    if start_time_str:
        if len(start_time_str) == 10:
            start_time_str += ' 00:00:00'
        elif len(start_time_str) == 16:
            start_time_str += ':00'
    if end_time_str:
        if len(end_time_str) == 10:
            end_time_str += ' 23:59:59'
        elif len(end_time_str) == 16:
            end_time_str += ':00'
    # 获取游标位置
    if use_db_cursor:
        cursor_record = get_last_record_full()
        if not cursor_record:
            print("错误: 作息表为空,请先初始化或手动添加一条记录")
            return
        cursor_datetime = f"{cursor_record['date']} {cursor_record['time_end']}:00"
        cursor_activity = cursor_record['activity']
        cursor_category = cursor_record['category']
    else:
        cursor_datetime = start_time_str
        cursor_activity = None
        cursor_category = None

    # 获取同步所需的消息
    cursor_dt, prev_messages, new_messages = get_messages_for_sync(cursor_datetime, end_time_str)

    print(f"开始时间: {cursor_datetime}")
    print(f"结束时间: {end_time_str}")
    if use_db_cursor:
        print(f"最后活动: {cursor_activity} [{cursor_category}]")
    print()
    print(f"上下文消息: {len(prev_messages)} 条（仅供参考，不处理）")
    print(f"待处理消息: {len(new_messages)} 条（从开始时间到结束时间）")
    print()

    if not new_messages:
        print("没有新消息需要同步")
        return

    # 输出 JSON 格式供 AI 分析
    output = {
        'cursor_datetime': cursor_datetime,
        'cursor_activity': cursor_activity if use_db_cursor else None,
        'cursor_category': cursor_category if use_db_cursor else None,
        'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'prev_message_count': len(prev_messages),
        'new_message_count': len(new_messages),
        'prev_messages': [],
        'new_messages': []
    }

    # 上下文消息（按时间正序）
    for msg_id, time_str, channel, content in prev_messages:
        output['prev_messages'].append({
            'msg_id': msg_id,
            'time': time_str,
            'channel': channel,
            'content': content
        })

    # 新消息（从游标时间开始）
    for msg_id, time_hhmm, channel, content in new_messages:
        output['new_messages'].append({
            'msg_id': msg_id,
            'time': time_hhmm,
            'channel': channel,
            'content': content
        })

    # 输出 JSON
    print("【JSON输出开始】")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print("【JSON输出结束】")
    print()
    print("AI分析说明:")
    print("- prev_messages: 游标前10条消息,帮助你理解上下文,不写入数据库")
    print("- new_messages: 游标之后的新消息,需要分析并写入数据库")
    print("- 需要保证记录首尾相接(time_start = 上一条 time_end)")
    print("- 空白时间段请生成 category='未知' 的记录填充")
    print("- 按活动切换点生成细粒度记录,不要合并")
    print(f"- 调用 add_record_full() 逐条写入,记录数应 >= {len(new_messages)}")
    print("\"\"\"")
    print("作息管家 CLI 用法：")
    print("    python schedule_cli.py init              # 初始化数据库")
    print("    python schedule_cli.py prepare-messages # 查询游标到现在的所有消息（供AI分析）")
    print("    python schedule_cli.py list [日期]        # 查看指定日期作息（默认今天）")
    print("    python schedule_cli.py detail [日期]     # 详细展示（含分析推理）")
    print("    python schedule_cli.py summary [日期]     # 查看每日摘要")
    print("    python schedule_cli.py timeline [日期]    # 时间轴展示")
    print("    python schedule_cli.py report [日期]      # 完整报告")
    print("    python schedule_cli.py range <开始> <结束>  # 日期范围统计")
    print("    python schedule_cli.py status            # 数据库状态")
    print("\"\"\"")

def cmd_help():
    print("""
作息管家 CLI 用法：
    python schedule_cli.py init              # 初始化数据库
    python schedule_cli.py prepare-messages # 查询游标到现在的所有消息（供AI分析）
    python schedule_cli.py list [日期]        # 查看指定日期作息（默认今天）
    python schedule_cli.py detail [日期]     # 详细展示（含分析推理）
    python schedule_cli.py summary [日期]     # 查看指定日期摘要
    python schedule_cli.py timeline [日期]    # 时间轴展示
    python schedule_cli.py report [日期]      # 完整报告
    python schedule_cli.py range <开始> <结束>  # 日期范围统计
    python schedule_cli.py status            # 数据库状态
""")

def fmt_time(t):
    return t.split(":")[0] + ":" + t.split(":")[1] if ":" in t else t

def print_records(date_str, records):
    print(f"\n{'='*60}")
    print(f"📅 {date_str} 作息记录")
    print(f"{'='*60}")
    if not records:
        print("  (无记录)")
        return

    total_min = 0
    emoji_map = {
        "睡眠": "😴", "工作": "💼", "学习": "📚", "运动": "🏋️",
        "通勤": "🚴", "餐饮": "🍽️", "娱乐": "🎮", "社交": "💕",
        "休闲": "🛋️", "健康": "🏥", "洗漱": "🚿",
        "兴趣爱好": "🎨", "未知": "❓"
    }

    for rec in records:
        _, ts, te, dur, act, cat, src_cnt, src_ts, reasoning = rec
        total_min += dur or 0
        emoji = emoji_map.get(cat, "📌")
        conf_mark = "✓" if len(src_cnt.split("||")) == 1 else "○"
        print(f"  {emoji} {fmt_time(ts)}~{fmt_time(te)} [{cat}] {conf_mark}")
        print(f"     {act[:45]}")

    print(f"\n  共 {len(records)} 块, 约 {total_min//60}h{total_min%60}m")

def print_detail(date_str, records):
    """详细展示,包含分析推理过程"""
    print(f"\n{'='*60}")
    print(f"📋 {date_str} 详细分析")
    print(f"{'='*60}")
    if not records:
        print("  (无记录)")
        return

    for rec in records:
        _, ts, te, dur, act, cat, src_cnt, src_ts, reasoning = rec
        print(f"\n⏰ {fmt_time(ts)} ~ {fmt_time(te)} [{cat}] ({dur}min)")
        print(f"  活动: {act[:60]}")
        print(f"  消息来源: {src_cnt[:80]}...")
        print(f"  消息时间: {src_ts}")
        print(f"  推理: {reasoning[:100]}...")

def print_summary(date_str, summary):
    print(f"\n📊 {date_str} 作息摘要")
    print(f"{'='*50}")

    items = [
        ("😴 睡眠", summary.get("sleep", 0)),
        ("💼 工作", summary.get("work", 0)),
        ("📚 学习", summary.get("learning", 0)),
        ("🏋️ 运动", summary.get("exercise", 0)),
        ("🚴 通勤", summary.get("commute", 0)),
        ("🍽️ 餐饮", summary.get("eating", 0)),
        ("🎮 娱乐", summary.get("entertainment", 0)),
        ("❓ 未知", summary.get("unknown", 0)),
    ]

    total = 0
    for label, minutes in items:
        if minutes > 0:
            print(f"  {label}: {minutes//60}h{minutes%60}m")
            total += minutes

    print(f"\n  总计: {total//60}h{total%60}m")

def cmd_list(args):
    date_str = args[0] if args else date.today().strftime("%Y-%m-%d")
    records = get_records_by_date(date_str)
    print_records(date_str, records)

def cmd_detail(args):
    date_str = args[0] if args else date.today().strftime("%Y-%m-%d")
    records = get_records_by_date(date_str)
    print_detail(date_str, records)

def cmd_summary(args):
    date_str = args[0] if args else date.today().strftime("%Y-%m-%d")
    summary = get_daily_summary(date_str)
    if summary:
        print_summary(date_str, summary)
    else:
        print(f"  暂无 {date_str} 的摘要数据")

def cmd_timeline(args):
    date_str = args[0] if args else date.today().strftime("%Y-%m-%d")
    records = get_records_by_date(date_str)

    print(f"\n⏰ {date_str} 时间轴")
    print(f"{'='*60}")

    if not records:
        print("  (无记录)")
        return

    emoji_map = {
        "睡眠": "😴", "工作": "💼", "学习": "📚", "运动": "🏋️",
        "通勤": "🚴", "餐饮": "🍽️", "娱乐": "🎮", "社交": "💕",
        "休闲": "🛋️", "健康": "🏥", "洗漱": "🚿",
        "兴趣爱好": "🎨", "未知": "❓"
    }

    timeline = ["  "] * 24
    for rec in records:
        _, ts, te, dur, act, cat, src_cnt, src_ts, reasoning = rec
        try:
            h_start = int(ts.split(":")[0])
            h_end = int(te.split(":")[0]) if te else h_start + 1
        except:
            continue
        emoji = emoji_map.get(cat, "📌")
        label = cat[:2]

        for h in range(h_start, min(h_end + 1, 24)):
            timeline[h] = f"{emoji}{label}"

    for h in range(24):
        bar = "▓▓▓" if timeline[h] != "  " else "░░░"
        print(f"  {h:02d}:00 {bar} {timeline[h]}")

def cmd_report(args):
    date_str = args[0] if args else date.today().strftime("%Y-%m-%d")
    records = get_records_by_date(date_str)
    summary = get_daily_summary(date_str)
    print_records(date_str, records)
    if summary:
        print_summary(date_str, summary)

def cmd_status():
    conn = get_connection()
    c = conn.cursor()

    c.execute('SELECT COUNT(*) FROM schedule_records')
    total = c.fetchone()[0]

    c.execute('SELECT COUNT(DISTINCT date) FROM schedule_records')
    days = c.fetchone()[0]

    c.execute('SELECT MIN(date), MAX(date) FROM schedule_records')
    min_d, max_d = c.fetchone()

    last = get_last_record_full()

    print(f"""
作息管家 数据库状态
{'='*50}
  数据库: {DB_PATH}
  总记录数: {total}
  已记录天数: {days}
  日期范围: {min_d or '无'} ~ {max_d or '无'}
  最后记录: {last['date'] + ' ' + last['time_end'] + ' ' + last['activity'] if last else '无'}
""")
    conn.close()

def cmd_query_plans(args):
    """
    查询计划作息
    用法: python schedule_cli.py query-plans <日期1,日期2,...>
    示例: python schedule_cli.py query-plans 2026-05-22
          python schedule_cli.py query-plans 2026-05-20,2026-05-21,2026-05-22
    """
    if not args:
        print("用法: python schedule_cli.py query-plans <日期1,日期2,...>")
        print("示例: python schedule_cli.py query-plans 2026-05-22")
        print("      python schedule_cli.py query-plans 2026-05-20,2026-05-21,2026-05-22")
        return

    dates_str = args[0]
    plans = get_plans(dates_str)

    if not plans:
        print(f"未找到以下日期的计划: {dates_str}")
        return

    for plan in plans:
        print(f"\n{'='*60}")
        print(f"📅 {plan['date']} 计划作息")
        print(f"{'='*60}")
        
        for h in range(24):
            content = plan.get(f'hour_{h}', '')
            if content:
                print(f"  {h:02d}:00 - {h+1:02d}:00  {content}")
            else:
                print(f"  {h:02d}:00 - {h+1:02d}:00  (未规划)")

def cmd_upsert_plan(args):
    """
    新增或更新计划作息
    用法: python schedule_cli.py upsert-plan <日期> <hour_0_planned> <hour_1_planned> ...
    简化用法: python schedule_cli.py upsert-plan <日期> --json '{"hour_0": "睡觉", "hour_8": "工作"}'
    """
    if len(args) < 2:
        print("""用法:
  python schedule_cli.py upsert-plan <日期> hour_0_planned hour_1_planned ...
  python schedule_cli.py upsert-plan <日期> --json '{"hour_0": "睡觉", "hour_8": "30min工作"}'

示例:
  # 简单方式(只填部分小时)
  python schedule_cli.py upsert-plan 2026-05-22 "睡觉" "" "" "" "" "" "通勤+工作" "工作"

  # JSON方式
  python schedule_cli.py upsert-plan 2026-05-22 --json '{"hour_0": "睡觉", "hour_8": "30min通勤+30min工作"}'
""")
        return

    date = args[0]

    # 检查是否带 --json
    if '--json' in args:
        import json
        json_idx = args.index('--json')
        if json_idx + 1 < len(args):
            try:
                hour_plans = json.loads(args[json_idx + 1])
            except json.JSONDecodeError as e:
                print(f"JSON 解析错误: {e}")
                return
        else:
            print("错误: --json 后需要跟JSON字符串")
            return
    else:
        # 简单方式: 从第2个参数开始，每两个一组 (hour_N, content)
        # 但更简单: 允许只传部分小时，其他留空
        hour_plans = {}
        for i, arg in enumerate(args[1:]):
            if arg.strip():  # 非空才记录
                hour_plans[f'hour_{i}'] = arg

    try:
        result = upsert_plan(date, hour_plans)
        action = '新增' if result['action'] == 'insert' else '更新'
        print(f"✓ {date} 计划作息{action}成功")
        print(f"  已记录 {len(hour_plans)} 个小时")
    except Exception as e:
        print(f"错误: {e}")

def cmd_plan_help():
    print("""作息管家 计划作息 CLI 用法:
    python schedule_cli.py query-plans <日期1,日期2,...>  # 查询计划作息（支持逗号分隔多日期）
    python schedule_cli.py upsert-plan <日期> [hours...]   # 新增或更新计划作息（存在则更新）
    python schedule_cli.py upsert-plan <日期> --json '{"hour_0": "..."}'  # JSON方式

示例:
  # 查询单天
  python schedule_cli.py query-plans 2026-05-22
  
  # 查询多天
  python schedule_cli.py query-plans 2026-05-20,2026-05-21,2026-05-22
  
  # 新增/更新计划（简单方式，只填非空小时）
  python schedule_cli.py upsert-plan 2026-05-22 "睡觉" "" "" "" "" "" "通勤+工作" "工作"
  
  # 新增/更新计划（JSON方式）
  python schedule_cli.py upsert-plan 2026-05-22 --json '{"hour_0": "睡觉", "hour_8": "30min通勤+30min工作"}'
""")

# ============ 主入口 ============
if __name__ == "__main__":
    if len(sys.argv) < 2:
        cmd_help()
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd == "init":
        init_db()
        print("✓ 数据库初始化完成")

    elif cmd == "prepare-messages":
        cmd_prepare_messages(args)

    elif cmd == "sync":
        print("sync 命令已废弃，请使用 prepare-messages + AI分析")
        if args:
            target = datetime.strptime(args[0], "%Y-%m-%d").date()
            sync_date(target)
        else:
            sync_incremental()

    elif cmd == "sync-days":
        days = int(args[0]) if args else 3
        auto_sync_days(days)

    elif cmd == "list":
        cmd_list(args)

    elif cmd == "detail":
        cmd_detail(args)

    elif cmd == "summary":
        cmd_summary(args)

    elif cmd == "timeline":
        cmd_timeline(args)

    elif cmd == "report":
        cmd_report(args)

    elif cmd == "range":
        if len(args) >= 2:
            start, end = args[0], args[1]
            rows = get_summaries_range(start, end)
            print(f"\n📅 {start} ~ {end} 作息汇总\n{'='*60}")
            for row in rows:
                d, sl, wk, ex, cm, ea, ln, en, unk = row
                total = sl + wk + ex + cm + ea + ln + en + unk
                print(f"  {d}: 睡{sl//60}h 工{wk//60}h 学{ln//60}h 运{ex//60}h 娱{en//60}h 总{total//60}h")
        else:
            print("用法: schedule_cli.py range <开始> <结束>")

    elif cmd == "status":
        cmd_status()

    elif cmd == "query-plans":
        cmd_query_plans(args)

    elif cmd == "upsert-plan":
        cmd_upsert_plan(args)

    elif cmd == "help":
        cmd_help()

    else:
        print(f"未知命令: {cmd}")
        cmd_help()