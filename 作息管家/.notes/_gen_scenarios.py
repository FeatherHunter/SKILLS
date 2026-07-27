#!/usr/bin/env python3
"""生成 scenarios.yaml — 一次性脚本,生成后废弃(产物在 references/scenarios.yaml)"""
from pathlib import Path
import yaml

# === 场景数据(按唤醒词组织)===
scenarios = []

# 通用辅助
def add(wake_word, scenario_id, title, dimensions, prompt, status="", result=""):
    scenarios.append({
        "wake_word": wake_word,
        "scenario_id": scenario_id,
        "scenario_title": title,
        "dimensions": dimensions,
        "prompt": prompt,
        "status": status,
        "result": result,
    })

# ============== #0 记作息 ==============
add("#0 记作息", "record_add_single", "添加单条作息记录",
    {"activity": "任意活动", "duration_minutes": "1-1440", "category": "白名单二级"},
    "请帮我记一条作息:今天 14:00-15:00 写了 AI 调优代码",
    result="会写入 1 条作息记录,生成回执 HTML 显示 id/时间/分类/原文")
add("#0 记作息", "record_add_json", "通过 JSON 文件批量添加",
    {"input": "JSON 文件路径"},
    "请帮我批量导入这些作息数据(从 JSON 文件)",
    result="逐条校验后写入,生成多条回执 HTML")
add("#0 记作息", "record_add_illegal_category", "category 不在白名单",
    {"category": "未在白名单的二级"},
    "记一笔:14:00 写了代码",
    status="【待开发】",
    result="校验会报错,提示'提议新增 X'等心法 #5 申请流程")
add("#0 记作息", "record_add_l1_only", "只传一级 category",
    {"category": "仅一级(如'创作')"},
    "请帮我记一条创作类作息",
    result="写入成功但附加 warning:建议细化到二级")
add("#0 记作息", "record_add_missing_field", "必填字段缺失",
    {"missing": "任一必填"},
    "请帮我记一条作息(用户漏说活动名)",
    result="校验报错,提示缺哪个字段 + 当前值 + 期望值")

# ============== #1 准备消息 ==============
add("#1 准备消息", "prep_default", "默认游标到当前时间拉取",
    {"range": "默认(游标到当前)"},
    "请帮我准备今天的消息",
    result="返回分页消息(默认 200 条/页)")
add("#1 准备消息", "prep_with_range", "指定时间区间拉取",
    {"range": "YYYY-MM-DD HH:MM ~ YYYY-MM-DD HH:MM"},
    "请帮我拉 2026-07-20 00:00 到 2026-07-24 23:59 的消息",
    result="返回该区间分页消息")
add("#1 准备消息", "prep_pagination", "翻页获取下一页",
    {"page": "N"},
    "请帮我翻第 3 页",
    result="返回第 3 页消息 + pagination.has_next 提示")
add("#1 准备消息", "prep_no_messages", "区间内无消息",
    {"range": "无消息区间"},
    "请帮我准备 2026-07-23 的消息",
    result="返回空列表,AI 应告知无消息")

# ============== #2 #3 同步 ==============
add("#2 同步作息", "sync_full", "完整同步流程(准备+分析+写入)",
    {"range": "默认"},
    "请帮我同步今天的消息成作息记录",
    result="AI 拉消息→分析→批量写入,每条生成回执 HTML")
add("#2 同步作息", "sync_partial_day", "同步指定日期",
    {"date": "YYYY-MM-DD"},
    "请帮我同步 2026-07-22 的消息",
    result="同步该日全量消息")
add("#3 增量同步", "sync_incremental", "从游标继续",
    {"cursor": "上次结束位置"},
    "请帮我增量同步(接着上次)",
    result="从 get_last_record_full 拿游标继续")
add("#3 增量同步", "sync_no_cursor", "首次同步无游标",
    {"first_time": True},
    "请帮我同步(从未同步过)",
    result="从最早消息开始同步")

# ============== #4 今天总结 ==============
add("#4 今天总结", "summary_full_24h", "当日满 24h 出综合报告",
    {"date": "今天", "complete": True},
    "请给我今天总结",
    result="生成 record_day.html 综合报告(分类/时长/24h 时间轴/睡眠/AI 钩子)")
add("#4 今天总结", "summary_partial", "当日未满 24h 出摘要",
    {"date": "今天", "complete": False},
    "请给我今天总结(还没记完)",
    result="生成简短摘要 + 提示'补全后再看完整报告'")
add("#4 今天总结", "summary_specific_date", "指定日期总结",
    {"date": "YYYY-MM-DD"},
    "请给我 2026-07-22 的总结",
    result="生成该日 report")
add("#4 今天总结", "summary_no_records", "指定日期无记录",
    {"date": "YYYY-MM-DD", "records": 0},
    "请给我 2026-01-01 的总结",
    result="报告空态,提示该日无记录")

# ============== #5 汇总作息 ==============
add("#5 汇总作息", "summary_range_default", "日期范围汇总",
    {"range": "YYYY-MM-DD ~ YYYY-MM-DD"},
    "请给我 7/13~7/19 这一周的汇总",
    result="生成 record_range.html(分类聚合+7维趋势+睡眠统计)")
add("#5 汇总作息", "summary_range_full", "日期范围文本汇总",
    {"range": "任意范围", "format": "text"},
    "请给我 7/13~7/19 的文本汇总",
    result="生成纯文本分类聚合")

# ============== #6 查作息 ==============
add("#6 查作息", "record_list_today", "今日作息列表",
    {"date": "今天"},
    "请帮我看看今天我做了什么",
    result="生成 record_day.html(4 卡摘要+分类进度+时间轴+睡眠)")
add("#6 查作息", "record_list_yesterday", "昨日作息",
    {"date": "昨天"},
    "昨天我做了什么",
    result="生成昨日 report_day.html")
add("#6 查作息", "record_list_specific", "指定日期作息",
    {"date": "YYYY-MM-DD"},
    "请帮我看看 2026-07-15 我做了什么",
    result="生成该日 record_day.html")
add("#6 查作息", "record_list_empty", "指定日期无记录",
    {"date": "YYYY-MM-DD", "records": 0},
    "请帮我看看 2026-07-01 我做了什么",
    result="生成空态 HTML,提示该日无记录")

# ============== #7 查作息详情 ==============
add("#7 查作息详情", "detail_day", "查看某日所有详情",
    {"date": "YYYY-MM-DD"},
    "请帮我看 7/15 作息详情(含 AI 推理链)",
    result="生成 record_detail.html(每条记录 11 字段全展开)")
add("#7 查作息详情", "detail_record", "查看单条详情",
    {"record_id": "N"},
    "请帮我看 id=123 这条记录详情",
    result="生成 record_detail.html(单条)")
add("#7 查作息详情", "detail_with_reasoning", "查看 AI 推理链",
    {"date": "YYYY-MM-DD", "include_reasoning": True},
    "请帮我看 7/15 的 AI 是怎么分类的",
    result="详情页 analysis_reasoning 字段完整展示")

# ============== #8 查作息时间轴 ==============
add("#8 查作息时间轴", "timeline_today", "今日时间轴",
    {"date": "今天"},
    "今天时间轴看一下",
    result="生成 record_day.html(24h 时间轴高亮)")
add("#8 查作息时间轴", "timeline_specific", "指定日期时间轴",
    {"date": "YYYY-MM-DD"},
    "请帮我看 7/15 的 24h 时间轴",
    result="生成该日 report 含时间轴")

# ============== #9 查作息范围 ==============
add("#9 查作息范围", "range_default", "日期范围统计",
    {"range": "YYYY-MM-DD ~ YYYY-MM-DD"},
    "请帮我看 7/13~7/19 这一周",
    result="生成 record_range.html")
add("#9 查作息范围", "range_this_week", "本周范围",
    {"range": "本周(自动计算)"},
    "请帮我看本周",
    result="本周一~周日 record_range.html")
add("#9 查作息范围", "range_text", "范围文本降级",
    {"range": "任意", "format": "text"},
    "请帮我看本周(直接给文本)",
    result="纯文本分类聚合")

# ============== #11 查作息状态 ==============
add("#11 查作息状态", "status_default", "查整体状态",
    {"scope": "all"},
    "作息状态怎么样",
    result="5 行文本(记录数/天数/最早/最近/同步状态)")

# ============== #12 查日程 ==============
add("#12 查日程", "list_events_today", "今日日程",
    {"date": "今天"},
    "请帮我看今天的日程",
    result="生成 plan_list_events.html(24h 时间轴+事件卡+筛选)")
add("#12 查日程", "list_events_specific", "指定日期日程",
    {"date": "YYYY-MM-DD"},
    "请帮我看 7/15 的日程",
    result="生成该日 plan_list_events.html")
add("#12 查日程", "search_event_title", "按标题搜索日程",
    {"date": "今天", "title": "健身"},
    "今天有健身吗",
    result="返回 search 结果(命中/未命中 JSON)")
add("#12 查日程", "search_event_triplet", "按时间三元组查重",
    {"date": "今天", "time_start": "HH:MM", "time_end": "HH:MM"},
    "今天 17:00-18:00 有什么安排",
    result="返回该时间槽事件(JSON)")
add("#12 查日程", "list_events_inactive", "查已软删事件",
    {"date": "今天", "include_inactive": True},
    "今天被删的日程有哪些",
    result="返回含 ✗ 前缀的事件")

# ============== #13 补计划 ==============
add("#13 补计划", "ensure_event_basic", "补一条计划(基础)",
    {"date": "后天", "time_start": "HH:MM", "time_end": "HH:MM", "title": "X"},
    "帮我补一条计划到后天 17:00-18:00 健身",
    result="ensure-plan-event → 生成 plan_receipt_add.html")
add("#13 补计划", "ensure_event_idempotent", "同时间重复(幂等)",
    {"date": "今天", "time_start": "HH:MM", "time_end": "HH:MM"},
    "再补一条 17:00-18:00 的健身(已有)",
    result="幂等命中,返回原 event_id,不重复创建")
add("#13 补计划", "ensure_event_with_notes", "补计划含备注",
    {"date": "明天", "notes": "细节", "category": "健康.健身"},
    "帮我补明天 17:00-18:00 健身(练背+有氧)",
    result="ensure-plan-event with notes → receipt HTML")

# ============== #14 复盘 ==============
add("#14 复盘", "review_today_normal", "今日复盘(标准流程)",
    {"date": "今天"},
    "请帮我复盘今天",
    result="list-events → 逐条 update-event --completion → render-plans-review.html")
add("#14 复盘", "review_today_all_done", "今日已全部复盘",
    {"date": "今天", "completion_all": True},
    "再帮我复盘一下今天",
    result="跳过 Step 0-5,直接进 Step 6 讨论模式")
add("#14 复盘", "review_no_events", "该日无活跃事件",
    {"date": "YYYY-MM-DD", "events_count": 0},
    "请帮我复盘 2026-07-01",
    result="提示'该日没有计划,无法复盘',退出")
add("#14 复盘", "review_with_memo_sync", "复盘前先同步备忘录",
    {"date": "今天", "memo_cli": True},
    "复盘前先对一下今天的打卡数据",
    result="询问用户是否已执行 /备忘录 备忘录同步")

# ============== #15 #16 24h 概览/多日 ==============
add("#15 24h 概览", "query_plans_today", "今日 24h 概览",
    {"date": "今天"},
    "今天 24h 安排概览",
    result="生成 plan_list_events.html(query-plans 模式,同小时 + 合并)")
add("#16 查多日计划", "query_plans_multi", "多日简版",
    {"dates": "YYYY-MM-DD,YYYY-MM-DD,..."},
    "请帮我看 7/13、7/14、7/15 三天计划",
    result="生成多日聚合 plan_list_events.html(不含 notes/completion/飞书状态)")

# ============== #17 商量计划 ==============
add("#17 商量计划", "plan_discuss_tomorrow", "商量明天计划",
    {"date": "明天"},
    "商量一下明天的计划",
    result="多轮对话 → render-plans-preview.html → 用户确认 → upsert-plan-events → plan_receipt_write.html")
add("#17 商量计划", "plan_with_locked", "商量时已有部分事件",
    {"date": "明天", "existing_events": 4},
    "帮我重新商量明天的计划(已有 4 条)",
    result="Step 2 列出已有事件,询问保留策略,锁定后填空隙")
add("#17 商量计划", "plan_with_wish", "商量时拉心愿清单",
    {"date": "明天", "memo_cli": True},
    "商量明天(把心愿 X 安排进去)",
    result="Step 3 拉备忘·心愿,询问已完成的 + 本次推进的")
add("#17 商量计划", "plan_24h_coverage_fail", "覆盖校验失败",
    {"date": "明天", "gap_or_overlap": True},
    "商量明天计划(生成的事件有空隙)",
    result="24h 联合校验失败,提示具体哪条不连续/越界,重新生成")
add("#17 商量计划", "plan_feishu_sync", "商量后飞书同步",
    {"date": "明天", "feishu": "full"},
    "商量后顺便同步到飞书",
    result="CLI 探测后询问[Y/n],yes 则 diff_and_sync 批量 create + 回写 event_id")

# ============== #18 改计划 ==============
add("#18 改计划", "update_event_basic", "改单个事件字段",
    {"event_id": "N", "fields": ["title", "notes"]},
    "改 id=544 这条的 title 为健身(上午)",
    result="update-event → render-plan-receipt.html")
add("#18 改计划", "update_event_time", "改时段(飞书删旧建新)",
    {"event_id": "N", "time_start": "HH:MM", "time_end": "HH:MM"},
    "把 id=544 改成 17:30-18:30",
    result="飞书删旧 event_id + 建新 event_id + 回写新 feishu_event_id")
add("#18 改计划", "update_event_completion", "改 completion",
    {"event_id": "N", "completion": "已完成"},
    "把 id=544 标已完成",
    result="update-event --completion,生成 receipt HTML")
add("#18 改计划", "update_event_feishu_ask", "改后飞书询问",
    {"event_id": "N", "feishu_synced": True},
    "改 id=544 的 title(已同步飞书)",
    result="询问'飞书那边也要改吗?',yes 则飞书 +update")

# ============== #19 删计划 ==============
add("#19 删计划", "deactivate_event", "软删事件",
    {"event_id": "N"},
    "删 id=544 这条计划",
    result="deactivate-event → is_active=0 → render-plan-receipt.html")
add("#19 删计划", "deactivate_with_feishu", "软删 + 飞书删",
    {"event_id": "N", "feishu_synced": True},
    "删 id=544(已同步飞书)",
    result="软删 + 询问飞书删,yes 则 feishu_delete_event + 清空 feishu_event_id")

# ============== #20 日程管家同步 ==============
add("#20 日程管家同步", "feishu_resync_basic", "反向对账+diff 询问",
    {"date": "YYYY-MM-DD"},
    "请帮我同步今天的日程到飞书",
    result="Phase 0 反向对账 → diff create/update/delete → 逐条询问 [Y/n] → 执行")

# ============== #21 飞书探测 ==============
add("#21 飞书探测", "feishu_probe", "三档探测",
    {"scope": "cli/auth/calendar"},
    "飞书能力怎么样",
    result="返回 FeishuStatus( cli_installed/authenticated/calendar_writable/tier=full/partial/missing )")

# ============== #22 初始化数据库 ==============
add("#22 初始化数据库", "init_default", "建三表",
    {"scope": "all"},
    "帮我初始化数据库",
    result="创建 schedule_records / daily_summary / schedule_plans 三表")

# ============== #23 按 ID 查记录 ==============
add("#23 按 ID 查记录", "get_record_basic", "按 ID 查单条",
    {"record_id": "N"},
    "帮我查 id=123 这条记录",
    result="render-records-detail --record-id 123 → record_detail.html")

# ============== #24 写作息摘要 ==============
add("#24 写作息摘要", "add_summary_basic", "写摘要",
    {"date": "YYYY-MM-DD", "category": "X", "total_minutes": "N"},
    "帮我写摘要:2026-07-22 工作.AI调优 60 分钟",
    result="add-summary 写入 daily_summary(解决孤儿表问题)")
add("#24 写作息摘要", "add_summary_idempotent", "同 date+category upsert",
    {"date": "YYYY-MM-DD", "category": "X"},
    "再写一次(已有)",
    result="upsert,total_minutes 覆盖")

# ============== #25 对比两个月 ==============
add("#25 对比两个月", "compare_months", "整月对比",
    {"month_a": "YYYY-MM", "month_b": "YYYY-MM"},
    "6 月和 7 月对比",
    result="render-record-compare-months → record_compare.html(4 卡+7维差异柱+AI 钩子)")
add("#25 对比两个月", "compare_range", "任意范围对比",
    {"label_a": "X", "range_a": "YYYY-MM-DD ~ YYYY-MM-DD",
     "label_b": "Y", "range_b": "YYYY-MM-DD ~ YYYY-MM-DD"},
    "上周和这周对比",
    result="render-record-compare → record_compare.html")
add("#25 对比两个月", "compare_week_vs_week", "周对比",
    {"label_a": "上周", "range_a": "周一~周日",
     "label_b": "本周", "range_b": "周一~周日"},
    "上周和这周差多少",
    result="render-record-compare 自动计算 + record_compare.html")

# ============== #26 修正作息 ==============
add("#26 修正作息", "amend_basic", "改 1 条记录多字段",
    {"record_id": "N", "fields": ["category", "activity"]},
    "这条记错了,改成工作.AI调优,活动是写代码",
    result="amend-record → render-record-receipt-edit.html(蓝调 diff)")
add("#26 修正作息", "amend_json_inline", "JSON 内联修改",
    {"record_id": "N", "json": "..."},
    "用 JSON 改 id=123 的多字段",
    result="amend-record --json '{...}' → 蓝调 diff")
add("#26 修正作息", "amend_24h_warn", "超过 24h 修改警告",
    {"record_id": "N", "record_date": "24h 前"},
    "改 3 天前那条记录(超 24h)",
    result="写入成功但附加 warning:操作规范建议 24h 内")

# ============== T4 类别深挖 ==============
add("T4 类别深挖", "category_range", "区间内某分类深挖",
    {"range": "YYYY-MM-DD ~ YYYY-MM-DD", "category": "X"},
    "这周健身什么时候做的",
    result="render-record-category-range → record_category.html(24h × N 天热力图)")
add("T4 类别深挖", "category_day", "单日某分类",
    {"date": "YYYY-MM-DD", "category": "X"},
    "7/15 健身什么时候做的",
    result="render-record-category → record_category.html")

# ============== T5 异常检测 ==============
add("T5 异常检测", "anomaly_default", "默认 7 天窗口检测",
    {"window": 7},
    "最近状态怎么样/有没有异常",
    result="render-record-anomaly → record_anomaly.html(7 维雷达 + 红/黄框异常)")
add("T5 异常检测", "anomaly_window_30", "30 天窗口",
    {"window": 30},
    "最近 30 天有没有异常",
    result="render-record-anomaly --window 30 → record_anomaly.html")

# === 写入文件 ===
output_path = Path(__file__).parent.parent / "references" / "scenarios.yaml"
output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, "w", encoding="utf-8") as f:
    f.write("# 作息管家 · 场景资产(§07 契约)\n")
    f.write("# 唯一事实源 — 所有 HELP HTML / 人类视图 / 机读视图都从这里派生\n")
    f.write("# 字段契约(§07 §2.2): wake_word / scenario_id / scenario_title / dimensions / prompt / status / result\n")
    f.write("# status 二态: '' (可用) / 【待开发】(不可执行但仍展示)\n\n")
    f.write("# Generated by .notes/_gen_scenarios.py — 一次性脚本\n")
    f.write("# 26 唤醒词 × 3-5 场景 = ~120 场景\n")
    f.write(f"# 场景总数: {len(scenarios)}\n\n")
    f.write(yaml.safe_dump(scenarios, allow_unicode=True, sort_keys=False, default_flow_style=False))

print(f"✅ 生成 scenarios.yaml: {len(scenarios)} 场景 → {output_path}")