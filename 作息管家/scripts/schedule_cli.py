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
import json as _json
from datetime import datetime, date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from schedule_db import (
    init_db, get_last_record_full,
    get_messages_for_sync, add_record_full,
    get_records_by_date, get_records_range,
    has_records_for_date, get_daily_summary,
    get_summaries_range, get_connection, DB_PATH,
    upsert_plan, get_plan, get_plans, add_summary,
    count_messages_from,
    # 2026-06-29 新增：事件型 plan
    list_plan_events, upsert_plan_events, update_plan_event,
    deactivate_plan_event, set_feishu_event_id, get_plan_event,
    validate_24h_coverage, normalize_time,
    _normalize_date,  # 日期容错：CLI 入口先归一，传给下游
    # 2026-07-12 新增：轻量查询 + 缺则建
    search_plan_event, ensure_plan_event,
)
from feishu_sync import (
    is_feishu_available, LarkAPIError,
    create_event as feishu_create_event,
    update_event as feishu_update_event,
    delete_event as feishu_delete_event,
    diff_and_sync as feishu_diff_and_sync,
    PlanEvent as FeishuPlanEvent,
    search_events as feishu_search_events,
)

# ============ CLI 命令 ============
def cmd_prepare_messages(args):
    """
    准备同步消息（始终分页）:查询游标前10条(上下文) + 游标后新消息(分页),输出JSON供AI分析
    用法:
      python schedule_cli.py prepare-messages                              # 默认: 从数据库游标到当前时间, 第1页, 每页200条
      python schedule_cli.py prepare-messages <开始时间>                       # 指定开始时间到当前时间
      python schedule_cli.py prepare-messages <开始时间> <结束时间>            # 指定时间范围
      python schedule_cli.py prepare-messages <开始时间> <结束时间> --page 2      # 第2页
      python schedule_cli.py prepare-messages <开始时间> <结束时间> --page-size 200  # 每页200条
    时间格式: YYYY-MM-DD HH:MM:SS  或  YYYY-MM-DD
    示例: python schedule_cli.py prepare-messages 2026-05-09 2026-05-22
          python schedule_cli.py prepare-messages 2026-05-09 2026-05-22 --page 2 --page-size 200
    """
    import json
    import math
    from datetime import datetime, timedelta

    # 解析分页参数
    page = 1
    page_size = 200
    clean_args = []
    i = 0
    while i < len(args):
        if args[i] == '--page' and i + 1 < len(args):
            page = int(args[i + 1])
            i += 2
        elif args[i] == '--page-size' and i + 1 < len(args):
            page_size = int(args[i + 1])
            i += 2
        else:
            clean_args.append(args[i])
            i += 1

    # 解析时间参数
    start_time_str = None
    end_time_str = None
    use_db_cursor = True

    if len(clean_args) >= 1:
        use_db_cursor = False
        start_time_str = clean_args[0]
        if len(clean_args) >= 2:
            end_time_str = clean_args[1]
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
            print("错误: 作息记录为空,请先初始化或手动添加一条记录")
            return
        cursor_datetime = f"{cursor_record['date']} {cursor_record['time_end']}:00"
        cursor_activity = cursor_record['activity']
        cursor_category = cursor_record['category']
    else:
        cursor_datetime = start_time_str
        cursor_activity = None
        cursor_category = None

    # 计算分页
    offset = (page - 1) * page_size
    total_messages = count_messages_from(cursor_datetime, end_time_str)
    total_pages = math.ceil(total_messages / page_size) if total_messages > 0 else 1
    has_next = page < total_pages

    # 获取同步所需的消息（分页）
    cursor_dt, prev_messages, new_messages = get_messages_for_sync(
        cursor_datetime, end_time_str, limit=page_size, offset=offset
    )

    print(f"开始时间: {cursor_datetime}")
    print(f"结束时间: {end_time_str}")
    if use_db_cursor:
        print(f"最后活动: {cursor_activity} [{cursor_category}]")
    print()
    print(f"上下文消息: {len(prev_messages)} 条（仅供参考，不处理）")
    print(f"待处理消息: {len(new_messages)} 条（第{page}页/{total_pages}页，每页{page_size}条，共{total_messages}条）")
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
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total_messages': total_messages,
            'total_pages': total_pages,
            'has_next': has_next
        },
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
    print("- new_messages: 当前页的新消息,需要分析并写入数据库")
    print("- 需要保证记录首尾相接(time_start = 上一条 time_end)")
    print("- 空白时间段请生成 category='未知' 的记录填充")
    print("- 按活动切换点生成细粒度记录,不要合并")
    print(f"- 调用 add_record_full() 逐条写入,记录数应 >= {len(new_messages)}")
    if has_next:
        print(f"- ⚠️ 还有下一页! 处理完本页后，请用 --page {page + 1} 获取下一页")

def cmd_help():
    print("""
作息管家 CLI 用法：
    python schedule_cli.py init              # 初始化数据库
    python schedule_cli.py prepare-messages  # 查询游标到现在的所有消息（供AI分析）
    python schedule_cli.py list [日期]       # 查看指定日期作息（默认今天）
    python schedule_cli.py detail [日期]     # 详细展示（含分析推理）
    python schedule_cli.py summary [日期]    # 查看指定日期摘要
    python schedule_cli.py timeline [日期]   # 时间轴展示
    python schedule_cli.py report [日期]     # 完整报告
    python schedule_cli.py range <开始> <结束>  # 日期范围统计
    python schedule_cli.py status            # 数据库状态
    python schedule_cli.py query-plans <日期>   # 查询日程
    python schedule_cli.py upsert-plan <日期> --json '{...}'  # 新增/更新旧版日程
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
        ts = rec['time_start']
        te = rec['time_end']
        dur = rec['duration_minutes']
        act = rec['activity']
        cat = rec['category']
        src_cnt = rec.get('source_contents', '')
        total_min += dur or 0
        emoji = emoji_map.get(cat, "📌")
        msg_count = len(src_cnt.split("\n")) if src_cnt else 0
        conf_mark = "✓" if msg_count <= 3 else "○"
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
        ts = rec['time_start']
        te = rec['time_end']
        dur = rec['duration_minutes']
        act = rec['activity']
        cat = rec['category']
        src_cnt = rec.get('source_contents', '')
        src_ts = rec.get('source_timestamps', '')
        reasoning = rec.get('analysis_reasoning', '')
        print(f"\n⏰ {fmt_time(ts)} ~ {fmt_time(te)} [{cat}] ({dur}min)")
        print(f"  活动: {act[:60]}")
        print(f"  消息来源: {src_cnt[:80]}...")
        print(f"  消息时间: {src_ts}")
        print(f"  推理: {reasoning[:100]}...")

def print_summary(date_str, summary_list):
    """打印每日摘要，summary_list 为 list of {category, total_minutes}"""
    print(f"\n📊 {date_str} 作息摘要")
    print(f"{'='*50}")

    if not summary_list:
        print("  (无摘要数据)")
        return

    emoji_map = {
        "睡眠": "😴", "工作": "💼", "学习": "📚", "运动": "🏋️",
        "通勤": "🚴", "餐饮": "🍽️", "娱乐": "🎮", "社交": "💕",
        "休闲": "🛋️", "健康": "🏥", "洗漱": "🚿",
        "兴趣爱好": "🎨", "未知": "❓"
    }

    total = 0
    for item in summary_list:
        cat = item['category']
        minutes = item['total_minutes']
        emoji = emoji_map.get(cat, "📌")
        print(f"  {emoji} {cat}: {minutes//60}h{minutes%60}m")
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
    summary_list = get_daily_summary(date_str)
    if summary_list:
        print_summary(date_str, summary_list)
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
        ts = rec['time_start']
        te = rec['time_end']
        cat = rec['category']
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
    summary_list = get_daily_summary(date_str)
    print_records(date_str, records)
    if summary_list:
        print_summary(date_str, summary_list)

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
    查询日程聚合视图
    用法: python schedule_cli.py query-plans <日期1,日期2,...>
    示例: python schedule_cli.py query-plans 2026-05-22
          python schedule_cli.py query-plans 2026-05-20,2026-05-21,2026-05-22
    日期参数容错：20260703 / 2026-07-03 / 2026/07/03 都接受（2026-07-03 起）。
    """
    if not args:
        print("用法: python schedule_cli.py query-plans <日期1,日期2,...>")
        print("示例: python schedule_cli.py query-plans 2026-05-22")
        print("      python schedule_cli.py query-plans 2026-05-20,2026-05-21,2026-05-22")
        return

    raw = args[0]
    # 逗号分隔多日期，逐段归一（任一段非法则报错）
    try:
        normalized_dates = [_normalize_date(d) for d in raw.split(',')]
    except ValueError as e:
        print(f"❌ {e}")
        return
    dates_str = ','.join(normalized_dates)
    plans = get_plans(dates_str)

    if not plans:
        print(f"未找到以下日期的日程: {dates_str}")
        return

    for plan in plans:
        print(f"\n{'='*60}")
        print(f"📅 {plan['date']} 日程（24h 聚合视图）")
        print(f"{'='*60}")

        for h in range(24):
            content = plan.get(f'hour_{h}', '')
            if content:
                print(f"  {h:02d}:00 - {h+1:02d}:00  {content}")
            else:
                print(f"  {h:02d}:00 - {h+1:02d}:00  (未规划)")

        # 跨命令交叉提示（2026-07-01 新增：让 AI 和用户都知道 list-events 才是默认）
        print(f"\n💡 这是 24h 聚合视图,同小时内的多条事件用 + 合并,丢失 notes/飞书同步状态/ID。")
        print(f"   默认查询请用 list-events: schedule_cli.py list-events {plan['date']}")

def cmd_upsert_plan(args):
    """
    新增或更新旧版日程
    用法: python schedule_cli.py upsert-plan <日期> <hour_0_planned> <hour_1_planned> ...
    简化用法: python schedule_cli.py upsert-plan <日期> --json '{"hour_0": "睡觉", "hour_8": "工作"}'
    """
    if len(args) < 2:
        print("""用法:
  python schedule_cli.py upsert-plan <日期> hour_0_planned hour_1_planned ...
  python schedule_cli.py upsert-plan <日期> --json '{"hour_0": "睡觉", "hour_8": "30min工作"}'

示例:
  # 简单方式(必须填满24小时)
  python schedule_cli.py upsert-plan 2026-05-22 "睡觉" "睡觉" "睡觉" "睡觉" "睡觉" "睡觉" "睡觉" "睡觉" "通勤+工作" "工作" "工作" "工作" "午餐" "午休" "工作" "工作" "通勤回家" "晚餐" "休息" "娱乐" "休息" "睡觉" "睡觉" "睡觉"

  # JSON方式(必须填满24小时)
  python schedule_cli.py upsert-plan 2026-05-22 --json '{"hour_0": "睡觉", "hour_1": "睡觉", ..., "hour_23": "睡觉"}'
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
        # 简单方式: 从第2个参数开始，必须提供24个小时的安排
        if len(args[1:]) != 24:
            print(f"错误: 必须提供24个小时的时间段安排，当前只提供了 {len(args[1:])} 个")
            print("示例: python schedule_cli.py upsert-plan 2026-05-22 睡觉 睡觉 睡觉 睡觉 睡觉 睡觉 睡觉 睡觉 通勤+工作 工作 工作 工作 午餐 午休 工作 工作 通勤回家 晚餐 休息 娱乐 休息 睡觉 睡觉 睡觉")
            return
        hour_plans = {}
        for i, arg in enumerate(args[1:]):
            hour_plans[f'hour_{i}'] = arg

    # 校验是否填满了全部24小时
    valid_keys = {f'hour_{i}' for i in range(24)}
    missing = valid_keys - set(hour_plans.keys())
    if missing:
        missing_hours = sorted([int(k.split('_')[1]) for k in missing])
        print(f"错误: 以下时间段未填写: {missing_hours}")
        print("要求: 必须填满全部24个小时（hour_0 到 hour_23）")
        return

    try:
        result = upsert_plan(date, hour_plans)
        action = '新增' if result['action'] == 'insert' else '更新'
        print(f"✓ {date} 日程{action}成功")
        print(f"  已记录 24 个小时")
    except Exception as e:
        print(f"错误: {e}")

# ============ 主入口 ============
def main(argv=None):
    """CLI 主入口：分发命令。2026-06-29 重构为函数，让所有 cmd_X 在调用前完成定义。"""
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        cmd_help()
        sys.exit(1)

    cmd = argv[0]
    args = argv[1:]

    if cmd == "init":
        init_db()
        print("✓ 数据库初始化完成")

    elif cmd == "add":
        cmd_add_record(args)

    elif cmd == "prepare-messages":
        cmd_prepare_messages(args)

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
            summaries = get_summaries_range(start, end)
            print(f"\n📅 {start} ~ {end} 作息汇总\n{'='*60}")
            if not summaries:
                print("  (无摘要数据)")
            else:
                # 按日期分组
                from collections import defaultdict
                grouped = defaultdict(list)
                for item in summaries:
                    grouped[item['date']].append(item)
                for d in sorted(grouped.keys()):
                    parts = []
                    total = 0
                    for item in grouped[d]:
                        cat = item['category']
                        mins = item['total_minutes']
                        total += mins
                        parts.append(f"{cat}{mins//60}h")
                    print(f"  {d}: {' '.join(parts)} 总{total//60}h")
        else:
            print("用法: schedule_cli.py range <开始> <结束>")

    elif cmd == "status":
        cmd_status()

    elif cmd == "query-plans":
        cmd_query_plans(args)

    elif cmd == "upsert-plan":
        cmd_upsert_plan(args)

    elif cmd == "upsert-plan-events":
        cmd_upsert_plan_events(args)

    elif cmd == "update-event":
        cmd_update_event(args)

    elif cmd == "deactivate-event":
        cmd_deactivate_event(args)

    elif cmd == "list-events":
        cmd_list_events(args)

    elif cmd == "search-plan-event":
        cmd_search_plan_event(args)

    elif cmd == "ensure-plan-event":
        cmd_ensure_plan_event(args)

    elif cmd == "feishu-resync":
        cmd_feishu_resync(args)

    # === 2026-07-23 新增:HTML 渲染模式(日程可视化) ===
    elif cmd == "render-list-events":
        cmd_render_list_events(args)
    elif cmd == "render-query-plans":
        cmd_render_query_plans(args)
    # === end ===

    # === 2026-07-23 改造:作息记录查询 → HTML 报告(单文件,硬绑 SKILLS_DB_PATH/schedule_html/) ===
    elif cmd == "render-record-report":
        cmd_render_record_report(args)
    elif cmd == "render-record-day":
        cmd_render_record_day(args)
    elif cmd == "render-record-range":
        cmd_render_record_range(args)
    elif cmd == "render-record-compare":
        cmd_render_record_compare(args)
    elif cmd == "render-record-compare-months":
        cmd_render_record_compare_months(args)
    elif cmd == "render-record-category":
        cmd_render_record_category(args)
    elif cmd == "render-record-category-range":
        cmd_render_record_category_range(args)
    elif cmd == "render-record-anomaly":
        cmd_render_record_anomaly(args)
    elif cmd == "render-records-detail":
        cmd_render_records_detail(args)
    elif cmd == "get-record":
        cmd_get_record(args)    # === end ===

    # === 2026-07-22 新增：分类系统管理 ===
    elif cmd == "list-categories":
        cmd_list_categories(args)
    elif cmd == "propose-category":
        cmd_propose_category(args)
    elif cmd == "approve-category":
        cmd_approve_category(args)
    # === end ===

    elif cmd == "help":
        cmd_help()

    else:
        print(f"未知命令: {cmd}")
        cmd_help()
# ============================================================
# 2026-06-29 新增：事件型日程（schedule_plans 新版）+ 飞书日历同步
# ============================================================
#
# 五个新命令：
#   upsert-plan-events <date> --json '...'   # 整日覆盖式 upsert（必填满 24h）
#   update-event <id> --title ... --notes ...   # 单条精细修改
#   deactivate-event <id>                       # 单条软删（is_active=0）
#   list-events <date>                          # 当天事件 + 飞书同步状态
#   feishu-resync <date>                        # 重同步某天到飞书
#
# 决策 C：每次 CRUD 后 AI 通过本 CLI 询问飞书同步（CLI 不静默同步）
# ============================================================


def _ask_yes_no(question: str, default: bool = True) -> bool:
    """通用 Y/n 询问（CLI 直接执行模式）"""
    suffix = " [Y/n]: " if default else " [y/N]: "
    sys.stdout.write(question + suffix)
    sys.stdout.flush()
    try:
        ans = input().strip().lower()
    except EOFError:
        return default
    if not ans:
        return default
    return ans in ("y", "yes", "是")


def _print_feishu_intro() -> None:
    """首次飞书询问时打出能力探测结果（统一告知）"""
    status = is_feishu_available()
    tier_label = {
        "full":    "✅ 全可用",
        "partial": "⚠️ 部分可用（cli 已装但 auth/权限不全）",
        "missing": "ℹ️ 未安装 lark-cli",
        "unknown": "⚠️ 探测失败",
    }
    print(f"  飞书探测：{tier_label.get(status.tier, status.tier)}")
    if status.cli_path:
        print(f"    路径：{status.cli_path}")
    if status.cli_version:
        print(f"    版本：{status.cli_version}")
    if status.last_error:
        print(f"    错误：{status.last_error}")


def _maybe_sync_after_write(db_event_ids: list, date: str) -> None:
    """
    写库完成后调用：询问用户是否同步飞书。
    - 若飞书能力不可用 → 告知后跳过（不阻塞主流程）
    - 用户同意 → 走 diff_and_sync
    """
    status = is_feishu_available()
    if not status.fully_available:
        print()
        print("  ℹ️ 飞书能力不可用或未授权——本批事件仅写入本地数据库。")
        print("    装了飞书后会解锁：① 同步计划到飞书日历 ② 自动拆分分钟级事件 ③ 双向 CRUD 同步")
        print()
        return

    print()
    _print_feishu_intro()
    if not _ask_yes_no(f"  ? 是否把这 {len(db_event_ids)} 个新事件同步到飞书日历？", default=True):
        print("  → 已跳过飞书同步。后续可用 feishu-resync 重新同步。")
        return

    # 拉当天活跃事件 → 同步
    active_events = list_plan_events(date, include_inactive=False)
    plan_events = [
        FeishuPlanEvent(
            time_start=e["time_start"], time_end=e["time_end"],
            title=e["title"], notes=e.get("notes") or "",
            category=e.get("category") or "",
            feishu_event_id=e.get("feishu_event_id"),
        )
        for e in active_events
    ]
    try:
        result = feishu_diff_and_sync(date, plan_events, dry_run=False, ask_callback=lambda q: _ask_yes_no("  " + q, default=True))
    except LarkAPIError as e:
        print(f"  ❌ 飞书同步失败：{e}")
        return
    except Exception as e:
        print(f"  ❌ 飞书同步异常：{type(e).__name__}：{e}")
        return

    print(f"  ✅ 飞书同步完成：created={len(result['created'])} updated={len(result['updated'])} deleted={len(result['deleted'])} skipped={len(result['skipped'])} errors={len(result['errors'])}")

    # 提示:飞书时间变更已自动同步 DB
    time_synced = result.get("time_synced") or []
    if time_synced:
        print(f"  ℹ️  飞书时间变更已自动同步 DB({len(time_synced)} 条):")
        for db_id, old_s, old_e, new_s, new_e in time_synced[:5]:
            print(f"     #{db_id}: {old_s}-{old_e} → {new_s}-{new_e}")
        if len(time_synced) > 5:
            print(f"     ... 还有 {len(time_synced) - 5} 条")

    # 提示:过去日期默认跳过的 create(避免死灰复燃)
    past_skipped = result.get("past_skipped") or []
    if past_skipped:
        print(f"  ⚠️  过去日期 {date} 默认跳过 {len(past_skipped)} 条 create(避免死灰复燃):")
        for db_id, title in past_skipped[:5]:
            print(f"     #{db_id} {title!r}")
        if len(past_skipped) > 5:
            print(f"     ... 还有 {len(past_skipped) - 5} 条")
        print(f"     如需强制 create,请手动在飞书日历添加对应事件后重跑 resync。")

    # 保险丝:如果飞书侧某时间段存在多个 event(历史重复 create 留下),
    # 立即打印警告,提示用户清理。
    dupes = result.get("duplicate_groups") or []
    if dupes:
        total_extra = sum(g["count"] - 1 for g in dupes)
        print(f"  ⚠️  检测到飞书侧重复 event: {len(dupes)} 个时间段共有 {total_extra} 个冗余 event_id")
        print(f"     建议运行清理脚本(联系小婉)或手动在飞书删除。")

    # 回写 feishu_event_id 到 schedule_plans
    # diff_and_sync 内部已经按 (date,start,end) 匹配；我们用 list_plan_events 重新 match
    if result["created"] or result["updated"] or result["deleted"]:
        try:
            refreshed = list_plan_events(date, include_inactive=True)
            # 反查飞书 events（按 description 含"作息管家自动同步"过滤）
            from feishu_sync import search_events
            feishu_list = search_events(start=date, end=date, query="作息管家自动同步")
            feishu_by_hh = {(_iso_to_hhmm(e.start, date), _iso_to_hhmm(e.end, date)): e.event_id for e in feishu_list}
            for e in refreshed:
                key = (e["time_start"], e["time_end"])
                fid = feishu_by_hh.get(key)
                if fid and fid != e.get("feishu_event_id"):
                    set_feishu_event_id(e["id"], fid)
        except Exception:
            # 回写失败不影响主结果
            pass


def _iso_to_hhmm(iso: str, date_fallback: str) -> str:
    """ISO 8601 → HH:MM 工具（与 feishu_sync 同名函数的本地副本）"""
    import re
    m = re.search(r"T(\d{2}:\d{2})", iso)
    if m:
        return m.group(1)
    return "00:00"


def _cleanup_old_event_in_slot(date: str, hhmm_start: str, hhmm_end: str,
                                keep_event_id: str) -> int:
    """
    兜底清理:在飞书日历上,把同 (date, start, end) 时间槽里,
    除 keep_event_id 之外的所有 event 全部删除。

    触发场景:update-event 改时段时,delete_event 失败(网络/权限等)
    但新 event 已经 create 成功,如果不清理,飞书侧会同时存在旧 + 新。

    返回:实际删除的 event 数。
    """
    try:
        # 拉飞书当天所有 event(query="作息管家自动同步" 过滤我们管的)
        events = feishu_search_events(start=date, end=date, query="作息管家自动同步")
    except LarkAPIError as e:
        print(f"  ⚠️ 兜底清理失败(拉飞书 events):{e}")
        return 0

    target = (hhmm_start, hhmm_end)
    to_delete = []
    for ev in events:
        ev_start = _iso_to_hhmm(ev.start, date)
        ev_end = _iso_to_hhmm(ev.end, date)
        if (ev_start, ev_end) != target:
            continue
        if ev.event_id == keep_event_id:
            continue
        to_delete.append(ev.event_id)

    deleted = 0
    for eid in to_delete:
        try:
            feishu_delete_event(eid)
            deleted += 1
        except LarkAPIError as e:
            print(f"  ⚠️ 兜底清理:删除 {eid} 失败:{e}")
    if deleted:
        print(f"  ✅ 兜底清理完成:删除 {deleted} 个同时间槽 event")
    return deleted


# ============================================================
# 新命令：upsert-plan-events
# ============================================================

def cmd_upsert_plan_events(args):
    """
    新增/更新一日全部事件（24h 录满硬约束）
    用法:
      python schedule_cli.py upsert-plan-events <日期> --json '[{...},{...}]'

    events JSON 示例:
    [
      {"time_start":"00:00","time_end":"07:00","title":"睡觉","notes":"深度","category":"休息"},
      {"time_start":"07:00","time_end":"08:00","title":"起床","notes":"洗漱+早餐","category":"起居"},
      {"time_start":"08:00","time_end":"12:00","title":"上班","notes":"码代码","category":"工作"},
      ...
      {"time_start":"22:00","time_end":"24:00","title":"休息","notes":null,"category":"休息"}
    ]
    """
    if not args or "--json" not in args:
        print("""用法:
  python schedule_cli.py upsert-plan-events <日期> --json '[{...},{...}]'

要求:
  - events 联合区间必须覆盖 [00:00, 24:00]
  - 每条 event 必含: time_start / time_end / title
  - 可选: notes / category

示例:
  python schedule_cli.py upsert-plan-events 2026-06-30 --json '[
    {"time_start":"00:00","time_end":"07:00","title":"睡觉"},
    {"time_start":"07:00","time_end":"08:00","title":"起床","notes":"洗漱"},
    {"time_start":"08:00","time_end":"12:00","title":"上班"},
    {"time_start":"12:00","time_end":"13:00","title":"午餐"},
    ...
    {"time_start":"22:00","time_end":"24:00","title":"休息"}
  ]'
""")
        return

    date = args[0]
    json_idx = args.index("--json")
    if json_idx + 1 >= len(args):
        print("错误: --json 后需要跟 JSON 字符串")
        return

    import json
    json_src = args[json_idx + 1]
    # 支持 @file.json 语法（AI 推荐用法，绕开 shell quoting 难题）
    if json_src.startswith("@"):
        file_path = json_src[1:]
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                json_text = f.read()
        except OSError as e:
            print(f"错误: 读取 JSON 文件 {file_path} 失败：{e}")
            return
    elif json_src == "-":
        # 从 stdin 读取
        json_text = sys.stdin.read()
    else:
        json_text = json_src
    try:
        events = json.loads(json_text)
    except json.JSONDecodeError as e:
        print(f"JSON 解析错误: {e}")
        return

    if not isinstance(events, list):
        print("错误: 顶层必须是数组")
        return

    # 预校验（24h 覆盖 + 字段合法）
    err = validate_24h_coverage(events)
    if err:
        print(f"错误: {err}")
        return

    # 写入
    try:
        result = upsert_plan_events(date, events, validate_24h=False)
    except Exception as e:
        print(f"错误: {e}")
        return

    print(f"✅ {date} 写入成功")
    print(f"   新增: {result['added']}  更新: {result['updated']}  软删旧: {result['deactivated']}  活跃总数: {result['total_active']}")

    # 询问飞书同步
    if result["added"] > 0 or result["updated"] > 0:
        _maybe_sync_after_write([], date)


# ============================================================
# 新命令：update-event
# ============================================================

def cmd_update_event(args):
    """
    单条精细修改
    用法:
      python schedule_cli.py update-event <id> [--title X] [--notes Y] [--category Z]
                                       [--time-start HH:MM] [--time-end HH:MM]
                                       [--completion 已完成] [--completion-note "拖延了1h"]

    修改后如果该事件已同步飞书，会询问是否同步修改到飞书。
    """
    if not args:
        print("""用法:
  python schedule_cli.py update-event <id> [--title X] [--notes Y] [--category Z]
                                       [--time-start HH:MM] [--time-end HH:MM]
                                       [--completion 未完成] [--completion-note "下雨"]

示例:
  python schedule_cli.py update-event 123 --title "通勤+早餐" --notes "骑车+豆浆"
  python schedule_cli.py update-event 456 --completion "已完成" --completion-note "按时"
""")
        return

    try:
        event_id = int(args[0])
    except ValueError:
        print(f"错误: id 必须是整数，得到 {args[0]!r}")
        return

    updates = {}
    if "--title" in args:
        updates["title"] = args[args.index("--title") + 1]
    if "--notes" in args:
        updates["notes"] = args[args.index("--notes") + 1]
    if "--category" in args:
        updates["category"] = args[args.index("--category") + 1]
    if "--time-start" in args:
        updates["time_start"] = args[args.index("--time-start") + 1]
    if "--time-end" in args:
        updates["time_end"] = args[args.index("--time-end") + 1]
    if "--completion" in args:
        updates["completion"] = args[args.index("--completion") + 1]
    if "--completion-note" in args:
        updates["completion_note"] = args[args.index("--completion-note") + 1]

    if not updates:
        print("错误: 未指定任何修改字段")
        return

    # 检查记录存在 + 是否有飞书 event_id
    event = get_plan_event(event_id)
    if not event:
        print(f"错误: 找不到 id={event_id} 的事件")
        return
    feishu_event_id = event.get("feishu_event_id")

    if not update_plan_event(event_id, updates):
        print("错误: 更新失败（可能值未变）")
        return

    print(f"✅ 已更新 id={event_id}")
    print(f"   字段: {', '.join(f'{k}={v!r}' for k, v in updates.items())}")

    # 询问飞书同步
    if feishu_event_id:
        status = is_feishu_available()
        if status.fully_available:
            print()
            print(f"  该事件已同步到飞书 (event_id={feishu_event_id})")
            if _ask_yes_no("  ? 是否把这次改动也同步到飞书？", default=True):
                try:
                    feishu_args = {}
                    if "summary" in updates or "title" in updates:
                        feishu_args["summary"] = updates.get("title", event["title"])
                    if "notes" in updates:
                        feishu_args["description"] = updates.get("notes", "")
                    # 时段变化 = 删旧 + 建新（飞书日历没有"改时间"按钮）
                    # **设计原则**:任何路径都不需要用户手动处理。
                    # 即使 delete 失败(网络/权限等),也用 search_events 兜底清理,
                    # 保证飞书侧只剩新 event,不留下重复。
                    if "time_start" in updates or "time_end" in updates:
                        new_start = updates.get("time_start", event["time_start"])
                        new_end = updates.get("time_end", event["time_end"])
                        if (new_start, new_end) != (event["time_start"], event["time_end"]):
                            # Step 1: 先建新的(如果这一步失败,旧的不动)
                            try:
                                new_feishu_id = feishu_create_event(
                                    start=f"{event['date']}T{new_start}:00+08:00",
                                    end=f"{event['date']}T{new_end}:00+08:00",
                                    summary=feishu_args.get("summary", event["title"]),
                                    description=feishu_args.get("description", event.get("notes") or ""),
                                ).event_id
                            except LarkAPIError as e:
                                print(f"  ❌ 创建新飞书事件失败:{e}")
                                return

                            # Step 2: 删旧的(失败也无所谓,新 event 已建)
                            try:
                                feishu_delete_event(feishu_event_id)
                            except LarkAPIError as e:
                                msg = str(e).lower()
                                if "not found" in msg:
                                    # 旧 event 本来就没了,无需清理
                                    pass
                                else:
                                    # delete 真失败(网络/权限等)→ 兜底清理
                                    print(f"  ⚠️ 删除旧飞书事件失败:{e}")
                                    print(f"  ℹ️  自动清理同时间槽其他 event...")
                                    _cleanup_old_event_in_slot(
                                        event["date"], new_start, new_end,
                                        keep_event_id=new_feishu_id,
                                    )

                            # Step 3: 更新 DB 端 ID
                            set_feishu_event_id(event_id, new_feishu_id)
                            print(f"  ✅ 飞书事件已重建：{new_feishu_id}")
                            return
                        else:
                            # 仅 start/end 存在 args 但值未变，忽略
                            pass
                    if feishu_args:
                        feishu_update_event(feishu_event_id, **feishu_args)
                        print(f"  ✅ 飞书事件已更新")
                    else:
                        print("  （无飞书侧字段需要更新）")
                except LarkAPIError as e:
                    print(f"  ❌ 飞书同步失败：{e}")
        else:
            print(f"  ℹ️ 该事件已绑定飞书 event_id={feishu_event_id}，但飞书当前不可用，未同步。")


# ============================================================
# 新命令：deactivate-event
# ============================================================

def cmd_deactivate_event(args):
    """
    单条软删（is_active=0）
    用法:
      python schedule_cli.py deactivate-event <id>

    如果该事件已同步飞书，会询问是否同步删除飞书事件。
    """
    if not args:
        print("用法: python schedule_cli.py deactivate-event <id>")
        return

    try:
        event_id = int(args[0])
    except ValueError:
        print(f"错误: id 必须是整数，得到 {args[0]!r}")
        return

    event = get_plan_event(event_id)
    if not event:
        print(f"错误: 找不到 id={event_id}")
        return
    if event["is_active"] == 0:
        print(f"ℹ️ id={event_id} 已经是停用状态")
        return

    if not deactivate_plan_event(event_id):
        print("错误: 停用失败")
        return

    print(f"✅ id={event_id}（{event['time_start']}-{event['time_end']} {event['title'][:20]}）已软删")

    # 询问飞书同步
    feishu_event_id = event.get("feishu_event_id")
    if feishu_event_id:
        status = is_feishu_available()
        if status.fully_available:
            print()
            print(f"  该事件已同步到飞书 (event_id={feishu_event_id})")
            if _ask_yes_no("  ? 是否也删除飞书那边的日程？", default=True):
                try:
                    feishu_delete_event(feishu_event_id)
                    set_feishu_event_id(event_id, "")  # 清空关联
                    print(f"  ✅ 飞书事件已删除")
                except LarkAPIError as e:
                    print(f"  ❌ 删除飞书事件失败：{e}")
        else:
            print(f"  ℹ️ 已绑定飞书 event_id={feishu_event_id}，但飞书不可用，未同步。")


# ============================================================
# 新命令：list-events
# ============================================================

def cmd_list_events(args):
    """
    查询某日所有事件 + 飞书同步状态
    用法:
      python schedule_cli.py list-events <日期>

    输出: id | 时段 | title | notes | feishu_event_id | last_synced_at
    日期参数容错：20260703 / 2026-07-03 / 2026/07/03 都接受（2026-07-03 起）。
    """
    if not args:
        print("用法: python schedule_cli.py list-events <日期>")
        return

    try:
        date = _normalize_date(args[0])
    except ValueError as e:
        print(f"❌ {e}")
        return
    active = list_plan_events(date, include_inactive=False)
    inactive = list_plan_events(date, include_inactive=True)
    inactive_ids = {e["id"] for e in inactive if e["is_active"] == 0}

    if not inactive and not active:
        print(f"  {date} 无任何日程事件")
        return

    # 飞书能力
    status = is_feishu_available()
    feishu_tier = status.tier
    print(f"\n📅 {date} 日程列表")
    print(f"  飞书能力: {feishu_tier} （{'CLI 可用' if status.cli_installed else '未安装'} / {'已授权' if status.authenticated else '未授权'} / {'可写' if status.calendar_writable else '无写权限'}）")
    print("=" * 90)
    print(f"  {'ID':>5} {'时段':<11} {'title':<20} {'notes':<25} 飞书ID / 同步状态        完成")
    print("-" * 110)

    all_events = sorted(active + [e for e in inactive if e["id"] not in {x['id'] for x in active}], key=lambda e: e["time_start"])
    for e in all_events:
        marker = "✗ " if e["is_active"] == 0 else "  "
        notes_short = (e.get("notes") or "")[:25]
        title_short = (e["title"] or "")[:20]
        feishu_id = e.get("feishu_event_id") or "-"
        synced = e.get("last_synced_at") or "-"
        comp = e.get("completion") or "-"
        print(f"{marker}{e['id']:>4} {e['time_start']}-{e['time_end']:<5} {title_short:<20} {notes_short:<25} {feishu_id[:30]} / {synced}  {comp}")
    print()
    print(f"  共活跃 {len(active)} 条 / 停用 {len(inactive_ids)} 条")


def cmd_search_plan_event(args):
    """
    轻量查询：按日期+标题查找日程事件
    用法:
      python schedule_cli.py search-plan-event <日期> --title <标题>
    输出 JSON: {"found": true/false, "id": N, "time_start": "...", ...}
    """
    import json
    title = None
    clean_args = []
    i = 0
    while i < len(args):
        if args[i] == "--title" and i + 1 < len(args):
            title = args[i + 1]
            i += 2
        else:
            clean_args.append(args[i])
            i += 1
    if not clean_args or not title:
        print(json.dumps({"error": "用法: search-plan-event <日期> --title <标题>"}, ensure_ascii=False))
        return
    try:
        date = _normalize_date(clean_args[0])
    except ValueError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return
    result = search_plan_event(date, title)
    if result:
        result["found"] = True
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(json.dumps({"found": False, "date": date, "title": title}, ensure_ascii=False))


def cmd_ensure_plan_event(args):
    """
    缺则建：查日期+时段是否存在，不存在则 INSERT
    用法:
      python schedule_cli.py ensure-plan-event <日期> --time-start HH:MM --time-end HH:MM --title <标题> [--notes X] [--category Y]
    输出 JSON: {"action": "found"/"created", "id": N}
    """
    import json
    title = notes = category = time_start = time_end = None
    clean_args = []
    i = 0
    while i < len(args):
        if args[i] == "--title" and i + 1 < len(args):
            title = args[i + 1]; i += 2
        elif args[i] == "--time-start" and i + 1 < len(args):
            time_start = args[i + 1]; i += 2
        elif args[i] == "--time-end" and i + 1 < len(args):
            time_end = args[i + 1]; i += 2
        elif args[i] == "--notes" and i + 1 < len(args):
            notes = args[i + 1]; i += 2
        elif args[i] == "--category" and i + 1 < len(args):
            category = args[i + 1]; i += 2
        else:
            clean_args.append(args[i]); i += 1
    if not clean_args or not title or not time_start or not time_end:
        print(json.dumps({"error": "用法: ensure-plan-event <日期> --time-start HH:MM --time-end HH:MM --title <标题>"}, ensure_ascii=False))
        return
    try:
        date = _normalize_date(clean_args[0])
    except ValueError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return
    result = ensure_plan_event(date, time_start, time_end, title, notes, category)
    print(json.dumps(result, ensure_ascii=False, default=str))


# ============================================================
# 新命令：feishu-resync
# ============================================================

def _reconcile_feishu_ids(date: str) -> int:
    """
    Phase 0: 反向对账
    拉飞书当日 events,对 DB 中 feishu_event_id 为空的事件做严格匹配
    (time_start + time_end + title),找到唯一匹配则自动回填 ID。
    返回: 实际回填的条数。
    """
    from feishu_sync import search_events

    # 飞书侧:用 search_events 拉"作息管家自动同步"标记的 events
    try:
        feishu_list = search_events(start=date, end=date, query="作息管家自动同步")
    except LarkAPIError as e:
        print(f"  ⚠️ 拉飞书 events 失败,跳过对账：{e}")
        return 0

    # 索引飞书:(start, end, summary) -> [event_id]
    import re
    feishu_index = {}
    for ev in feishu_list:
        start_iso = ev.start if hasattr(ev, "start") else ev.get("start", "")
        end_iso = ev.end if hasattr(ev, "end") else ev.get("end", "")
        start_date = start_iso[:10] if start_iso else ""
        end_date = end_iso[:10] if end_iso else ""
        start = _iso_to_hhmm(start_iso, date)
        end = _iso_to_hhmm(end_iso, date)
        # 跨日边界规则:飞书 end_time="次日 00:00" 等价于 DB "23:59"
        if end == "00:00" and start_date and end_date and start_date != end_date:
            end = "23:59"
        summary = (ev.summary if hasattr(ev, "summary") else ev.get("summary", "")).strip()
        ev_id = ev.event_id if hasattr(ev, "event_id") else ev.get("event_id", "")
        if not ev_id:
            continue
        feishu_index.setdefault((start, end, summary), []).append(ev_id)

    # DB 侧:找缺 ID 的 event
    db_events = list_plan_events(date, include_inactive=False)
    matched = []
    for e in db_events:
        if e.get("feishu_event_id"):
            continue
        db_start = normalize_time(e["time_start"])
        db_end = normalize_time(e["time_end"])
        db_title = e["title"].strip()
        candidates = feishu_index.get((db_start, db_end, db_title), [])
        if len(candidates) == 1:
            matched.append((e["id"], db_title, candidates[0]))
        elif len(candidates) > 1:
            print(f"  ⚠️ DB #{e['id']} \"{db_title}\" 飞书侧有 {len(candidates)} 个撞 key 候选,跳过(需手工处理)")

    if not matched:
        print("  → 对账:DB 端无缺 ID 的事件")
        return 0

    print(f"  → 对账:发现 {len(matched)} 条可回填")
    for db_id, title, fid in matched:
        print(f"       DB #{db_id:3d} \"{title}\"  ←  飞书 {fid[:13]}...")

    if not _ask_yes_no("  ? 是否回填这些 feishu_event_id?", default=True):
        print("  → 已跳过对账回填")
        return 0

    for db_id, title, fid in matched:
        set_feishu_event_id(db_id, fid)
        print(f"     ✓ DB #{db_id} → {fid}")
    return len(matched)


def cmd_feishu_resync(args):
    """
    重同步某天事件到飞书(Phase 0 对账 + diff + apply)
    用法:
      python schedule_cli.py feishu-resync <日期>

    行为:
      - Phase 0: 反向对账(自动回填 DB 缺 ID 的事件)
      - 拉飞书当日事件
      - 对比 DB 活跃事件
      - 询问每个 create/update/delete 动作
    """
    if not args:
        print("用法: python schedule_cli.py feishu-resync <日期>")
        return

    try:
        date = _normalize_date(args[0])
    except ValueError as e:
        print(f"❌ {e}")
        return

    status = is_feishu_available()
    if not status.fully_available:
        print(f"❌ 飞书不可用:{status.tier}")
        print(f"   {status.last_error or ''}")
        return

    print(f"\n🔄 重同步 {date} 到飞书日历 ...")
    _print_feishu_intro()

    # Phase 0: 反向对账(回填 DB 缺 ID 的事件)
    print("\n  [Phase 0] 反向对账:把飞书侧存在但 DB 缺 ID 的事件关联起来")
    _reconcile_feishu_ids(date)

    # 拉 DB 活跃事件(对账后可能新增了 ID)
    active = list_plan_events(date, include_inactive=False)
    if not active:
        print(f"  {date} 无活跃事件,无需同步")
        return

    plan_events = [
        FeishuPlanEvent(
            time_start=e["time_start"], time_end=e["time_end"],
            title=e["title"], notes=e.get("notes") or "",
            category=e.get("category") or "",
            feishu_event_id=e.get("feishu_event_id"),
        )
        for e in active
    ]
    try:
        result = feishu_diff_and_sync(date, plan_events, dry_run=False, ask_callback=lambda q: _ask_yes_no("  " + q, default=True))
    except LarkAPIError as e:
        print(f"  ❌ 飞书 diff 失败:{e}")
        return

    print(f"\n  ✅ 完成")
    print(f"     created={len(result['created'])}  updated={len(result['updated'])}  deleted={len(result['deleted'])}  skipped={len(result['skipped'])}  errors={len(result['errors'])}")

    # 提示:飞书时间变更已自动同步到 DB
    time_synced = result.get("time_synced") or []
    if time_synced:
        print(f"  ℹ️  飞书时间变更已自动同步 DB({len(time_synced)} 条):")
        for db_id, old_s, old_e, new_s, new_e in time_synced[:5]:
            print(f"     #{db_id}: {old_s}-{old_e} → {new_s}-{new_e}")
        if len(time_synced) > 5:
            print(f"     ... 还有 {len(time_synced) - 5} 条")

    # 提示:过去日期默认跳过的 create(避免死灰复燃)
    past_skipped = result.get("past_skipped") or []
    if past_skipped:
        print(f"  ⚠️  过去日期 {date} 默认跳过 {len(past_skipped)} 条 create(避免死灰复燃):")
        for db_id, title in past_skipped[:5]:
            print(f"     #{db_id} {title!r}")
        if len(past_skipped) > 5:
            print(f"     ... 还有 {len(past_skipped) - 5} 条")
        print(f"     如需强制 create,请手动在飞书日历添加对应事件后重跑 resync。")

    # 保险丝:飞书侧重复 event 警告
    dupes = result.get("duplicate_groups") or []
    if dupes:
        total_extra = sum(g["count"] - 1 for g in dupes)
        print(f"  ⚠️  检测到飞书侧重复 event: {len(dupes)} 个时间段共有 {total_extra} 个冗余 event_id")
        print(f"     建议运行清理脚本(联系小婉)或手动在飞书删除。")

    if result["errors"]:
        print(f"     错误明细:")
        for eid, err in result["errors"][:5]:
            print(f"       {eid}: {err}")


# ============================================================
# 2026-07-23 新增：HTML 渲染模式（查日程/24h 概览 可视化）
# ============================================================
#
# 两个新命令:
#   render-list-events <日期> [--out PATH]   # 对应 list-events 的 HTML 版
#   render-query-plans <日期1,日期2,...>     # 对应 query-plans 多日聚合的 HTML 版
#
# 设计原则:
# - 旧 list-events / query-plans 输出文本(零变动,完全兼容)
# - HTML 模式只生成文件,不修改数据库
# - 模板在 templates/, 渲染器在 schedule_html_render.py
# - 默认输出到作息管家/reports/ 下
# - AI 拿到路径后用 <media src="..." type="file" /> 交付

def cmd_render_list_events(args):
    """
    render-list-events <日期> [--out PATH]

    把 list-events 的数据渲染成 HTML(首屏摘要卡 + 24h 时间轴 + 事件卡片 +
    完成度筛选 + 飞书同步状态 + 24h 缺口高亮)。

    用法:
      python scripts/schedule_cli.py render-list-events 2026-07-15
      python scripts/schedule_cli.py render-list-events 2026-07-15 --out reports/my.html
    """
    from pathlib import Path as _P

    if not args:
        print(_json.dumps({
            "status": "error",
            "message": "用法: render-list-events <日期> [--out PATH]",
            "example": "render-list-events 2026-07-15"
        }, ensure_ascii=False))
        return

    from schedule_db import _normalize_date
    try:
        date = _normalize_date(args[0])
    except ValueError as e:
        print(_json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))
        return

    out_path = None
    i = 1
    while i < len(args):
        if args[i] == "--out" and i + 1 < len(args):
            out_path = _P(args[i + 1]).resolve()
            i += 2
        else:
            i += 1

    try:
        from schedule_html_render import render_list_events, render_and_write
    except Exception as e:
        print(_json.dumps({
            "status": "error",
            "message": f"加载渲染器失败: {type(e).__name__}: {e}"
        }, ensure_ascii=False))
        return

    payload = render_list_events(date)
    result = render_and_write(payload, out_path)

    if result["status"] == "ok":
        result["data"]["json_payload"] = payload
    print(_json.dumps(result, ensure_ascii=False, indent=2))


def cmd_render_query_plans(args):
    """
    render-query-plans <日期1,日期2,...> [--out PATH]

    把 query-plans 的多日聚合数据渲染成 HTML(多日对比 + 完成度统计 +
    缺口检测)。

    用法:
      python scripts/schedule_cli.py render-query-plans 2026-07-13,2026-07-14,2026-07-15
      python scripts/schedule_cli.py render-query-plans 2026-07-13,2026-07-14 --out reports/wk.html
    """
    from pathlib import Path as _P

    if not args:
        print(_json.dumps({
            "status": "error",
            "message": "用法: render-query-plans <日期1,日期2,...> [--out PATH]",
            "example": "render-query-plans 2026-07-13,2026-07-14,2026-07-15"
        }, ensure_ascii=False))
        return

    dates_raw = args[0]
    out_path = None
    i = 1
    while i < len(args):
        if args[i] == "--out" and i + 1 < len(args):
            out_path = _P(args[i + 1]).resolve()
            i += 2
        else:
            i += 1

    try:
        from schedule_html_render import render_query_plans, render_and_write
    except Exception as e:
        print(_json.dumps({
            "status": "error",
            "message": f"加载渲染器失败: {type(e).__name__}: {e}"
        }, ensure_ascii=False))
        return

    payload = render_query_plans(dates_raw)
    result = render_and_write(payload, out_path)

    if result["status"] == "ok":
        result["data"]["json_payload"] = payload
    print(_json.dumps(result, ensure_ascii=False, indent=2))


# ============================================================
# 2026-07-23 新增:作息记录查询 → HTML 单日报告
# ============================================================
#
# 一个命令:render-record-report <日期>
# 行为:
#   1. 从 schedule_records 现读(无中间文件,无 /tmp JSON)
#   2. 派生 4 段数据(时间分配/24h 色带/AI 亮点占位/睡眠分析)
#   3. 注入 templates/schedule_record_report.html
#   4. 写到 SKILLS_DB_PATH/schedule_html/<date>_record_report.html(目录必须已存在)
#   5. stdout 一行 JSON:status/data.file_path/data.bytes/message
#
# 设计约束(来自 SKILL五层 + 预置 HTML 指导手册):
#   - 不查 schedule_db.py 之外的 DB(数据层 §1)
#   - 输出文件 = SKILLS_DB_PATH/schedule_html/<date>_record_report.html
#   - 不传 --out(目录硬绑,只有 SKILLS_DB_PATH 环境变量决定)
#   - 目录不存在 → 报错(不静默建)
#   - 同日期覆盖写(用户主动调就期望刷新)
#   - 第 ③ 段 AI 亮点默认空(本次不做 AI 叙事)
def cmd_render_record_report(args):
    """
    render-record-report <日期>

    把该日 schedule_records 表的全部记录 → 4 段 HTML 报告 →
    写到 SKILLS_DB_PATH/schedule_html/<date>_record_report.html → stdout JSON。

    用法:
      python scripts/schedule_cli.py render-record-report 2026-07-15
    """
    from schedule_html_render import _record_dir, render_record_report, render_and_write
    from pathlib import Path as _P

    if not args:
        print(_json.dumps({
            "status": "error",
            "message": "用法: render-record-report <日期>(YYYY-MM-DD)",
            "example": "render-record-report 2026-07-15"
        }, ensure_ascii=False))
        return

    date = args[0]

    # 校验日期(字段名 + 当前值 + 期望值 + 怎么修 — 接口层硬规则)
    from schedule_db import _normalize_date
    try:
        date = _normalize_date(date)
    except ValueError as e:
        print(_json.dumps({
            "status": "error",
            "message": f"date 字段格式非法: '{args[0]}'(期望 YYYY-MM-DD 或 YYYYMMDD,建议: 2026-07-15)"
        }, ensure_ascii=False))
        return

    # 校验输出目录(硬绑 SKILLS_DB_PATH,不存在 → 报错不静默建)
    record_dir = _record_dir()
    if not record_dir.exists():
        print(_json.dumps({
            "status": "error",
            "message": f"HTML 输出目录不存在: 字段 --out_dir,期望值 {record_dir},"
                       f"建议: mkdir -p {record_dir} 或设置环境变量 SKILLS_DB_PATH 指向含 schedule_html/ 子目录的位置"
        }, ensure_ascii=False))
        return

    # 派生数据
    try:
        payload = render_record_report(date)
    except Exception as e:
        print(_json.dumps({
            "status": "error",
            "message": f"派生渲染数据失败: {type(e).__name__}: {e}"
        }, ensure_ascii=False))
        return

    # 写文件(覆盖写,同日期刷新)
    result = render_and_write(payload, None)
    if result["status"] != "ok":
        print(_json.dumps(result, ensure_ascii=False, indent=2))
        return

    fp = _P(result["data"]["file_path"])
    size_bytes = fp.stat().st_size
    print(_json.dumps({
        "status": "ok",
        "data": {
            "file_path": str(fp),
            "bytes": size_bytes,
            "size_kb": result["data"]["size_kb"],
            "mode": "record-report",
            "date": date,
            "record_count": payload["data"]["meta"]["record_count"],
        },
        "message": f"✓ 作息记录报告已写入: {fp}"
    }, ensure_ascii=False, indent=2))


# ===== 7 个新 cmd(2026-07-23 升级:5 模板 8 命令)=====
# 共享 helper:校验日期 + 调用派生 + 写文件 + 输出 JSON
def _render_record_cmd(args, render_fn, mode_name, label_fields, output_path_override=None):
    """
    render_fn: 一个返回 payload 字典的函数
    label_fields: 用于 stdout JSON 的额外 meta 字段列表
    output_path_override: 可选的输出路径(Path 对象,None 用 default_output_path)
    """
    from schedule_html_render import render_and_write
    from pathlib import Path as _P
    if not args:
        return {"status": "error", "message": f"用法: 至少需要 1 个参数"}

    try:
        payload = render_fn(*args)
    except Exception as e:
        return {"status": "error", "message": f"派生失败: {type(e).__name__}: {e}"}

    if payload.get("status") != "ok":
        return payload

    result = render_and_write(payload, output_path_override)
    if result.get("status") != "ok":
        return result

    fp = _P(result["data"]["file_path"])
    data = {
        "file_path": str(fp),
        "bytes": fp.stat().st_size,
        "size_kb": result["data"]["size_kb"],
        "mode": mode_name,
    }
    data.update(label_fields or {})
    return {
        "status": "ok",
        "data": data,
        "message": f"✓ {mode_name} 已写入: {fp}",
    }


def cmd_render_record_day(args):
    """render-record-day <日期>"""
    from schedule_html_render import render_record_day
    if not args:
        print(_json.dumps({"status":"error","message":"用法: render-record-day <日期>"}, ensure_ascii=False))
        return
    r = _render_record_cmd(args, render_record_day, "record-day",
                            {"date": args[0], "record_count": None})
    print(_json.dumps(r, ensure_ascii=False, indent=2))


def cmd_render_record_range(args):
    """render-record-range <开始> <结束>"""
    from schedule_html_render import render_record_range
    if len(args) < 2:
        print(_json.dumps({"status":"error","message":"用法: render-record-range <开始> <结束>"}, ensure_ascii=False))
        return
    r = _render_record_cmd(args, render_record_range, "record-range",
                            {"start": args[0], "end": args[1]})
    print(_json.dumps(r, ensure_ascii=False, indent=2))


def cmd_render_record_compare(args):
    """render-record-compare <labelA> <startA> <endA> <labelB> <startB> <endB>"""
    from schedule_html_render import render_record_compare
    if len(args) < 6:
        print(_json.dumps({
            "status":"error",
            "message":"用法: render-record-compare <labelA> <startA> <endA> <labelB> <startB> <endB>",
            "example":"render-record-compare 6月 2026-06-01 2026-06-30 7月 2026-07-01 2026-07-31"
        }, ensure_ascii=False))
        return
    r = _render_record_cmd(args, render_record_compare, "record-compare",
                            {"label_a": args[0], "label_b": args[3]})
    print(_json.dumps(r, ensure_ascii=False, indent=2))


def cmd_render_record_compare_months(args):
    """render-record-compare-months <YYYY-MM> <YYYY-MM>"""
    from datetime import date as _d
    from schedule_html_render import render_record_compare

    if len(args) < 2:
        print(_json.dumps({
            "status":"error",
            "message":"用法: render-record-compare-months <YYYY-MM> <YYYY-MM>",
            "example":"render-record-compare-months 2026-06 2026-07"
        }, ensure_ascii=False))
        return

    a, b = args[0], args[1]
    # 解析 YYYY-MM
    try:
        ya, ma = map(int, a.split("-"))
        yb, mb = map(int, b.split("-"))
    except Exception:
        print(_json.dumps({"status":"error","message":f"date 格式非法: '{a}' 或 '{b}'(期望 YYYY-MM)"}, ensure_ascii=False))
        return

    da_start = _d(ya, ma, 1)
    db_start = _d(yb, mb, 1)
    # 计算下月第一天
    if ma == 12:
        da_end = _d(ya + 1, 1, 1)
    else:
        da_end = _d(ya, ma + 1, 1)
    if mb == 12:
        db_end = _d(yb + 1, 1, 1)
    else:
        db_end = _d(yb, mb + 1, 1)

    sa = da_start.isoformat()
    ea = da_end.isoformat()
    sb = db_start.isoformat()
    eb = db_end.isoformat()
    label_a = f"{ya}年{ma}月"
    label_b = f"{yb}年{mb}月"
    r = _render_record_cmd([label_a, sa, ea, label_b, sb, eb],
                            render_record_compare, "record-compare",
                            {"label_a": label_a, "label_b": label_b,
                             "a_range": f"{sa}~{ea}", "b_range": f"{sb}~{eb}"})
    # 替换路径:用中文 label 替代 a_vs_b
    if r.get("status") == "ok":
        from pathlib import Path as _P
        new_path = _P(r["data"]["file_path"]).parent / f"{label_a}_vs_{label_b}_record_compare.html"
        old_path = _P(r["data"]["file_path"])
        if old_path.exists():
            if new_path.exists():
                new_path.unlink()  # H9 修复:目标存在先删,避免 Windows 抛 FileExistsError
            old_path.rename(new_path)
        r["data"]["file_path"] = str(new_path)
        r["data"]["file_path"] = str(new_path)
    print(_json.dumps(r, ensure_ascii=False, indent=2))


def cmd_render_record_category(args):
    """render-record-category <日期> <category>"""
    from schedule_html_render import render_record_category
    if len(args) < 2:
        print(_json.dumps({
            "status":"error",
            "message":"用法: render-record-category <日期> <category>",
            "example":"render-record-category 2026-07-15 健身"
        }, ensure_ascii=False))
        return
    date, category = args[0], args[1]
    r = _render_record_cmd([category, date, date], render_record_category, "record-category",
                            {"date": date, "start": date, "end": date, "category": category})
    print(_json.dumps(r, ensure_ascii=False, indent=2))


def cmd_render_record_category_range(args):
    """render-record-category-range <开始> <结束> <category>"""
    from schedule_html_render import render_record_category
    if len(args) < 3:
        print(_json.dumps({
            "status":"error",
            "message":"用法: render-record-category-range <开始> <结束> <category>",
            "example":"render-record-category-range 2026-07-01 2026-07-31 健身"
        }, ensure_ascii=False))
        return
    start, end, category = args[0], args[1], args[2]
    r = _render_record_cmd([category, start, end], render_record_category, "record-category",
                            {"start": start, "end": end, "category": category})
    print(_json.dumps(r, ensure_ascii=False, indent=2))


def cmd_render_record_anomaly(args):
    """render-record-anomaly [--window 7]"""
    from schedule_html_render import render_record_anomaly

    window = 7  # 默认
    i = 0
    while i < len(args):
        if args[i] == "--window" and i + 1 < len(args):
            try:
                window = int(args[i + 1])
            except ValueError:
                print(_json.dumps({"status":"error","message":f"--window 值非法: '{args[i+1]}'(期望整数 1-90)"}, ensure_ascii=False))
                return
            i += 2
        else:
            i += 1
    if not (1 <= window <= 90):
        print(_json.dumps({"status":"error","message":f"--window 超出范围: {window}(期望 1-90)"}, ensure_ascii=False))
        return
    r = _render_record_cmd([window], render_record_anomaly, "record-anomaly",
                            {"window_days": window})
    print(_json.dumps(r, ensure_ascii=False, indent=2))






def cmd_render_records_detail(args):
    """render-records-detail <日期> [--record-id N]

    作息详情网页（人工智能推理溯源, 四步契约 §8 落地）。
    按 100% 字段暴露原则,每条作息记录全 11 字段都注入 payload,
      上层(HTML 模板) 自行决定消费哪些、是否折叠、什么样式。
    """
    from schedule_html_render import _record_dir, render_records_detail, render_and_write
    from pathlib import Path as _P

    if not args:
        print(_json.dumps({
            "status": "error",
            "message": "用法: render-records-detail <日期>(YYYY-MM-DD) [--record-id N]",
            "example": "render-records-detail 2026-07-15",
        }, ensure_ascii=False))
        return

    date = args[0]
    record_id = None
    i = 1
    while i < len(args):
        if args[i] == "--record-id" and i + 1 < len(args):
            try:
                record_id = int(args[i + 1])
            except ValueError:
                print(_json.dumps({"status": "error", "message": f"--record-id 值非法: '{args[i+1]}'(期望整数)"}, ensure_ascii=False))
                return
            i += 2
        else:
            i += 1

    from schedule_db import _normalize_date
    try:
        date = _normalize_date(date)
    except ValueError:
        print(_json.dumps({"status": "error", "message": f"date 字段格式非法: '{date}'(期望 YYYY-MM-DD 或 YYYYMMDD,建议: 2026-07-15)"}, ensure_ascii=False))
        return

    record_dir = _record_dir()
    if not record_dir.exists():
        print(_json.dumps({
            "status": "error",
            "message": f"HTML 输出目录不存在: 字段 record_dir(派生自环境变量 SKILLS_DB_PATH),当前值 {record_dir},建议: mkdir -p {record_dir}",
        }, ensure_ascii=False))
        return

    try:
        payload = render_records_detail(date, record_id=record_id)
    except Exception as e:
        print(_json.dumps({
            "status": "error",
            "message": f"派生失败: {type(e).__name__}: {e}",
        }, ensure_ascii=False))
        return

    if payload.get("status") != "ok":
        print(_json.dumps(payload, ensure_ascii=False, indent=2))
        return

    result = render_and_write(payload, None)
    if result.get("status") != "ok":
        print(_json.dumps(result, ensure_ascii=False, indent=2))
        return

    fp = _P(result["data"]["file_path"])
    size_bytes = fp.stat().st_size
    extra = {"record_id": record_id} if record_id else {}
    print(_json.dumps({
        "status": "ok",
        "data": {
            "file_path": str(fp),
            "bytes": size_bytes,
            "size_kb": result["data"]["size_kb"],
            "mode": "record-detail",
            "date": date,
            "record_count": len(payload["data"].get("records", [])),
            **extra,
        },
        "message": f"✓ 作息详情网页已写入: {fp}",
    }, ensure_ascii=False, indent=2))


# ============================================================
# 2026-07-22 新增：分类系统管理（基于 validators.py 白名单）
# ============================================================
#
# 三个命令:
#   list-categories [--level 1|2]              # 查白名单
#   propose-category --code X --hint Y         # 提议新分类(对话式)
#   approve-category --code X                  # 批准分类(写入 YAML)
#

def cmd_list_categories(args):
    """
    list-categories [--level 1|2] [--json]
    列出分类白名单。默认同时显示一级+二级。
    """
    from validators import list_level1, list_level2

    level = None
    as_json = False
    for a in args:
        if a.startswith("--level="):
            level = a.split("=", 1)[1]
        elif a == "--json":
            as_json = True

    result = {}
    if level in (None, "1"):
        result["level1"] = list_level1()
    if level in (None, "2"):
        result["level2"] = list_level2()

    if as_json:
        print(_json.dumps(result, ensure_ascii=False, indent=2))
        return

    # 人类可读
    if "level1" in result:
        print("一级白名单(8 个固定):")
        for c in result["level1"]:
            print(f"  - {c}")
        print()
    if "level2" in result:
        print("二级白名单(含 YAML 扩展):")
        for lv1, lv2_list in result["level2"].items():
            print(f"  {lv1}: {' / '.join(lv2_list)}")
    print(f"\n(YAML 路径: {Path(__file__).parent.parent / '.db' / 'category_whitelist.yaml'})")


def cmd_propose_category(args):
    """
    propose-category --code "一级.二级" --hint "场景说明"
    AI 发现新分类不在白名单时调用 → 输出"提议",等用户口头确认后
    再调 approve-category 真正写入。
    """
    code = None
    hint = ""
    i = 0
    while i < len(args):
        if args[i] == "--code" and i + 1 < len(args):
            code = args[i + 1]
            i += 2
        elif args[i] == "--hint" and i + 1 < len(args):
            hint = args[i + 1]
            i += 2
        else:
            i += 1

    if not code:
        print(_json.dumps({
            "status": "error",
            "message": "--code 必填,格式: '一级.二级' (例: 调整.散步)"
        }, ensure_ascii=False))
        return

    from validators import validate_category
    valid, err = validate_category(code)
    if valid:
        print(_json.dumps({
            "status": "info",
            "message": f"'{code}' 已在白名单中,无需提议。"
        }, ensure_ascii=False))
        return

    print(_json.dumps({
        "status": "ok",
        "data": {
            "proposed": code,
            "hint": hint,
            "current_error": err
        },
        "message": (
            f"📝 提议新增分类: '{code}'\n"
            f"   场景说明: {hint or '(无)'}\n\n"
            f"   请用户口头确认后,我再调用 approve-category --code '{code}' 写入 YAML。"
        )
    }, ensure_ascii=False, indent=2))


def cmd_approve_category(args):
    """
    approve-category --code "一级.二级"
    用户确认后,AI 调用此命令写入白名单 YAML。
    """
    code = None
    i = 0
    while i < len(args):
        if args[i] == "--code" and i + 1 < len(args):
            code = args[i + 1]
            i += 2
        else:
            i += 1

    if not code:
        print(_json.dumps({
            "status": "error",
            "message": "--code 必填"
        }, ensure_ascii=False))
        return

    from validators import parse_category, LEVEL1_WHITELIST
    level1, level2 = parse_category(code)

    if not level1 or not level2:
        print(_json.dumps({
            "status": "error",
            "message": f"格式错误,应为 '一级.二级': {code}"
        }, ensure_ascii=False))
        return

    if level1 not in LEVEL1_WHITELIST:
        print(_json.dumps({
            "status": "error",
            "message": f"一级 '{level1}' 不在白名单: {sorted(LEVEL1_WHITELIST)}"
        }, ensure_ascii=False))
        return

    yaml_path = Path(__file__).parent.parent / ".db" / "category_whitelist.yaml"
    data = {}
    if yaml_path.exists():
        try:
            import yaml
            with open(yaml_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            print(_json.dumps({
                "status": "warn",
                "message": f"YAML 加载失败,将以空文件开始: {e}"
            }, ensure_ascii=False))
            data = {}

    data.setdefault(level1, [])
    if level2 in data[level1]:
        result_msg = f"'{code}' 已在 YAML 白名单中,无需重复添加。"
    else:
        data[level1].append(level2)
        data[level1] = sorted(set(data[level1]))
        yaml_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            import yaml
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
            result_msg = f"✓ '{code}' 已加入 YAML 白名单。下一条 add_record 即可使用。"
        except Exception as e:
            print(_json.dumps({
                "status": "error",
                "message": f"YAML 写入失败: {e}"
            }, ensure_ascii=False))
            return

    print(_json.dumps({
        "status": "ok",
        "data": {
            "code": code,
            "yaml_path": str(yaml_path),
            "current_whitelist": data
        },
        "message": result_msg
    }, ensure_ascii=False, indent=2))


# ============================================================
# 2026-07-22 新增：add 入口(规范化写入路径)
# ============================================================
#
# 设计要点:
#   - 暴露 add_record_full 给 CLI,所有写入都走校验
#   - 支持命令行参数 + --json 两种方式
#   - category 仅一级时给"建议细化"警告(Q2=C 决策)
#   - schedule_records 无飞书事件,不需要询问同步(Q4)
#

def cmd_add_record(args):
    """
    add [--date D] [--time-start S] [--time-end E] [--duration N] [--activity A]
        --category C --source-contents SC --source-timestamps ST --analysis-reasoning AR
        [--json @file.json | --json '{...}']

    必填 9 字段:date / time_start / time_end / duration_minutes / activity /
                category / source_contents / source_timestamps / analysis_reasoning
    """

    # === 1. 解析参数 ===
    parsed = {}
    json_payload = None
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--json":
            # --json @file.json 或 --json '{...}'
            if i + 1 >= len(args):
                print(_json.dumps({"status": "error", "message": "--json 后需跟文件名(@file)或 JSON 字符串"}, ensure_ascii=False))
                return
            v = args[i + 1]
            if v.startswith("@"):
                file_path = v[1:]
                try:
                    with open(file_path, encoding="utf-8") as f:
                        json_payload = _json.load(f)
                except Exception as e:
                    print(_json.dumps({"status": "error", "message": f"读取 JSON 文件失败: {e}"}, ensure_ascii=False))
                    return
            else:
                try:
                    json_payload = _json.loads(v)
                except Exception as e:
                    print(_json.dumps({"status": "error", "message": f"JSON 解析失败: {e}"}, ensure_ascii=False))
                    return
            i += 2
            continue
        # --key value 形式
        if a.startswith("--") and i + 1 < len(args):
            key = a[2:].replace("-", "_")
            parsed[key] = args[i + 1]
            i += 2
        else:
            i += 1

    if json_payload:
        data = json_payload
    else:
        data = parsed

    # === 2. 字段映射 + 必填校验 ===
    field_map = {
        "date": "date",
        "time_start": "time_start",
        "time_end": "time_end",
        "duration_minutes": "duration_minutes",
        "activity": "activity",
        "category": "category",
        "source_contents": "source_contents",
        "source_timestamps": "source_timestamps",
        "analysis_reasoning": "analysis_reasoning",
    }
    kwargs = {}
    missing = []
    for k_in, k_out in field_map.items():
        v = data.get(k_in)
        if v is None or v == "":
            missing.append(k_in)
        else:
            # duration_minutes 转换
            if k_in == "duration_minutes":
                try:
                    v = int(v)
                except (TypeError, ValueError):
                    print(_json.dumps({"status": "error", "message": f"duration_minutes 必须是整数: {v!r}"}, ensure_ascii=False))
                    return
            kwargs[k_out] = v
    if missing:
        print(_json.dumps({
            "status": "error",
            "message": f"缺少必填字段: {', '.join(missing)}",
            "required": list(field_map.keys())
        }, ensure_ascii=False))
        return

    # === 3. category 校验(下沉到 add_record_full) ===
    # add_record_full 内部已调 validators.validate_category()
    # 一级放行但 Q2=C 决策:在 CLI 层加"建议细化"警告
    from validators import parse_category, list_level2
    level1, level2 = parse_category(kwargs["category"])
    warning = None
    if level1 and not level2:
        # 一级 category, 建议细化
        level2_options = list_level2(level1).get(level1, [])
        if level2_options:
            warning = (
                f"💡 category='{level1}' 是一级,建议细化到二级。"
                f"可选: {level2_options[:8]}{'...' if len(level2_options) > 8 else ''}"
            )

    # === 4. 写入 ===
    try:
        from schedule_db import add_record_full
        record_id = add_record_full(**kwargs)
        result = {
            "status": "ok",
            "data": {"id": record_id, "category": kwargs["category"], "date": kwargs["date"]},
            "message": f"✓ 记录 id={record_id} 已写入 ({kwargs['date']} {kwargs['time_start']}~{kwargs['time_end']} {kwargs['category']})"
        }
        if warning:
            result["warning"] = warning
            result["message"] += f"\n{warning}"
        print(_json.dumps(result, ensure_ascii=False, indent=2))
    except ValueError as e:
        # 校验失败
        print(_json.dumps({
            "status": "error",
            "message": f"写入失败: {e}"
        }, ensure_ascii=False))
    except Exception as e:
        print(_json.dumps({
            "status": "error",
            "message": f"未知错误: {type(e).__name__}: {e}"
        }, ensure_ascii=False))


# ============================================================
# help 更新
# ============================================================

def cmd_help():
    print("""
作息管家 CLI 帮助

基础:
  init                                    初始化数据库
  add <参数> 或 --json                    写入作息记录(规范化入口,2026-07-22 新增)
  prepare-messages [start] [end] [--page N] [--page-size N]   取待同步消息
  list [date]                             查看某日作息  add-summary --date D --category C --total-minutes M  写一条作息摘要,让 daily_summary 不再孤儿
  detail [date]                           含 AI 推理的详情
  summary [date]                          每日摘要
  timeline [date]                         时间轴
  report [date]                           综合报告
  range <start> <end>                     日期范围统计
  status                                  数据库状态

日程（新版事件型，2026-06-29）:
  upsert-plan-events <date> --json '[]'   整日 upsert（24h 录满硬约束）
  update-event <id> [--title X ...]       单条精细修改（含 --completion --completion-note）
  deactivate-event <id>                   单条软删
  list-events <date>                      当天日程 + 飞书同步状态 + 完成情况
  search-plan-event <date> --title X      按日期+标题查日程事件（轻量查询，JSON）
  ensure-plan-event <date> --time-start HH:MM --time-end HH:MM --title X [--notes Y] [--category Z]  补计划：单条追加，幂等
  feishu-resync <date>                    重同步某天到飞书

HTML 渲染(可视化查询结果):
  render-list-events <date> [--out PATH]   渲染日程 list-events 为 HTML(摘要+时间轴+事件卡片)
  render-query-plans <d1,d2,...> [--out PATH]  渲染日程多日 query-plans 为 HTML
  render-record-report <date>              [兼容] 单日报告 HTML(同 render-record-day)
  render-record-day <date>                  单日报告 HTML(4段+健康分+AI钩子)
  render-record-range <开始> <结束>           区间报告 HTML(7维趋势+健康分+AI钩子)
  render-record-compare <labelA> <startA> <endA> <labelB> <startB> <endB>   两段对比报告 HTML(7维差异+AI钩子)
  render-record-compare-months <YYYY-MM> <YYYY-MM>  整月对比报告 HTML(如 2026-06 vs 2026-07)
  render-record-category <日期> <category>    单日单类深挖 HTML(24h×1day热力图)
  render-record-category-range <开始> <结束> <category>  区间单类深挖 HTML(24h×Nday热力图)
  render-record-anomaly [--window 7]          异常检测 HTML(雷达+红框+AI钩子)
  render-records-detail <日期> [--record-id N]   作息详情 HTML(人工智能推理溯源,每条全 11 字段都注入 payload)

分类系统（2026-07-22 新增）:
  list-categories [--level 1|2] [--json]   列出分类白名单
  propose-category --code X --hint Y      提议新分类（对话式，AI 用）
  approve-category --code X               批准分类（写入 YAML）

日程（旧版 24-hour，保留兼容）:
  query-plans <date1,date2,...>            查询日程（24h 聚合视图）
  upsert-plan <date> ...                  旧版 upsert

说明:
  1. 第一次使用新版计划前，请先执行：
       python scripts/migrate_plan_to_events.py
  2. 每次 CRUD 后，本 CLI 会询问是否同步飞书日历（决策 C：每次询问）
  3. 飞书能力探测（lark-cli 安装/auth/权限）— 自动检测
  4. 删一条事件 = 软删（is_active=0），同步飞书时也会询问是否删飞书那边
""")

if __name__ == "__main__":
    main()
