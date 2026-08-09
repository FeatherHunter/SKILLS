"""卡路里技能 · 唤醒词速查台 · 数据源

v2.4.10 起 · 给 templates/help_center.html 提供结构化数据。

每个 TRIGGER 含:
  - wake_word: 主唤醒词(显示给用户)
  - aliases:   同义变体(显示在 summary)
  - category:  12 分类之一(给 sticky 导航分组)
  - desc:      一句话说明
  - main_prompt: { cli, text }   默认/最常用场景
  - variants:    [ { label, cli, prompt }, ... ]   详细用法(原文照搬 SKILL.md §触发词速查表)

约束(必须满足,否则 check_trigger_consistency.py 报错):
  - wake_word ⊆ SKILL.md frontmatter 触发词
  - aliases 项 ⊆ SKILL.md frontmatter 触发词
  - cli 必须是可执行的相对路径(python scripts/<file>.py ...)

维护规则:
  - 新增 trigger:同步 SKILL.md frontmatter + 本文件 + render_help_center.py 一致
  - 修改 cli:必须更新 SKILL.md §触发词速查表 + 本文件 + render_*.py docstring

⚠️ **2026-08-01 场景体系重构中(Phase 2 数据填充)**
本文件旧版 80 个 wake_word(v2.x 时代)已部分替换:
- ✅ **目标管理 25 场景已同步**(2026-08-02 · ticket #7):25 条新 13 字段 scene 格式
  (category='目标管理', 含 output_type/html_template/data_fields 等,render_help_center 透传)
- ✅ **基础信息 4 场景已同步**(2026-08-02 · ticket #8):设置档案 / 设活动量 / 改档案 / 查档案
  (category='基础信息', 新 13 字段 scene 格式,替换旧综合分类 设置档案/查档案)
- ✅ **身体细节 13 场景已同步**(2026-08-02 · ticket #9):记体脂（皮褶钳）/记体脂（外部测量）/记围度/补记体脂/补记围度/看体脂/看体脂趋势/看围度/看围度趋势/对比体脂/对比围度/删体脂/删围度
  (category='身体细节', 新 13 字段 scene 格式,替换旧身体成分/围度 8 条)
- ✅ **身材照片 10 场景已同步**(2026-08-02 · ticket #10):8 条唯一触发词(记身材照×3 / 查身材照 / 对比两张照片 / 生成身材照GIF / 删身材照 / 改照片标签 / 加照片标签 / 删照片标签)
  (category='身材照片', 新 13 字段 scene 格式;记身材照 3 场景同唤醒词,merge 时按 (wake_word, key) 去重保 3 卡)
- ✅ **分析 154 场景已同步**(2026-08-02 · ticket #11):A1 组合分析 60 + A2 健康报告 19 + A3 整体趋势 15 + A4 自动分析 23 + A5 营养分析 16 + A6 预测模拟 20 + 单点 1
  (category='分析', 新 13 字段 scene 格式,替换旧综合分析 13 条)
- ⏳ 其余分类仍为旧版运行时数据,待各自分类 ticket 同步。
v1.0 重设计的**权威场景清单**在 `.scratch/scene-index-recovered.md`(每场景含描述 + 呈现数据 + 用户确认记录),
开发期数据在 `.scratch/scene_data/NN-分类.json`(schema 13 字段,check_scene_data.py 校验)。
已确认分类:主页 9(scene_data/01-主页.json) / 饮食 68 / 体重 58 / 运动 39 / 健身计划 29 / 基础信息 4 / 身体细节 13(2026-08-01)。
**Phase 2 同步时按 scene-data 替换本文件对应分类**,当前勿据此文件判断"最终场景设计"。

"""


# ============ Prompt 骨架(v2.4.11 · 2026-07-26 重构) ============
# 每条 prompt = head + body + tail
# - head/tail 由 _prompt_skeleton() 统一包裹(避免重复)
# - body 由每条 TRIGGER 各自手写(具体说明该场景做什么、产出什么)
# 约束(check_prompt_quality.py 强制):
#   - body 必须非空(避免"按流程执行"这类空话)
#   - 整条 prompt 由 _prompt_skeleton() 包裹(不允许手写)
#
# Q1 决策落地(ticket 16 · 2026-07-29):fill_hints 是独立字段,不合并进 body。
#   理由:body 是给用户看的场景说明(用户视角),fill_hints 是 AI 提示用户补字段的占位符(AI 视角)。
#   二者语义不同,合并会让 body 变成混合视角的杂烩。独立字段 + check_prompt_quality 守护
#   (触发 must_contain 关键词校验时仍校验 body,不校验 fill_hints)。

def _prompt_skeleton(wake: str, variant: str | None = None, body: str = '', fill_hints: list[str] | None = None) -> str:
    """prompt 模板骨架:head(用户对 AI 的请求)+ body(场景细节,不指导流程)

    Args:
        wake:       主唤醒词(中文,如 '查体重趋势')
        variant:    variant 标签(如 '上周'),None 表示主 prompt
        body:       用户场景的具体说明(用户能看到什么、什么时间窗口等),**不指导 AI 流程**
        fill_hints: 输入型 trigger 的填空提示(每项一行,追加到 body 末尾,供未来走 skeleton 时使用)

    Returns:
        完整 prompt 字符串,可直接粘给 AI

    设计原则:
    - prompt 是用户对 AI 说的话,不是流程手册
    - AI 自己读 SKILL.md 找流程 — 不在 prompt 里复述 SKILL.md §X.Y
    - body 只描述"用户能看到的成果"和"窗口/参数语境",不写步骤
    """
    if not body:
        raise ValueError(f'_prompt_skeleton body 必须非空(wake={wake}, variant={variant})')
    # variant label 已含 wake 前缀(约定),不再拼 wake
    name = variant if variant else wake
    head = (
        f"请你加载技能 卡路里,执行唤醒词「{name}」。\n\n"
        f"⚠️ §⚠️ 第 7 条 AI 验证协议:本 prompt 涉及'用户状态'断言时,"
        f"必须先 SELECT DB 验证(空值 ≠ '从未',损坏值 ≠ '原值',类型错 ≠ '视为 0')。"
    )
    if fill_hints:
        body += '\n\n' + '\n'.join(fill_hints)
    # 2026-08-05 用户拍板:旧「完成后给 1 句话总结」收尾作废,统一为 HTML 交付文字纪律
    tail = "交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。"
    return f"{head}\n\n{body}\n\n{tail}"


# 12 类别(顺序按 SKILL.md §触发词速查表)
CATEGORIES = [
    ('🏠', '主页',          'home'),
    ('🍚', '饮食记录',      'diet'),
    ('📦', '食品库',        'food_lib'),
    ('⚖️', '体重',          'weight'),
    ('🏃', '运动',          'exercise'),
    ('💪', '健身计划',      'workout'),
    ('📊', '分析',          'analysis'),
    ('📋', '综合',          'general'),
    ('🔄', '复盘',          'review'),
    ('🧬', '身体细节',      'body_detail'),
    ('📸', '身材照片',      'body_photo'),
    ('🎯', '目标管理',      'goal'),
    ('🛠', '基础信息',      'profile'),
]


# ===== 109 唤醒词(9 主页新场景 + 100)(80 旧 + 25 目标管理新场景) =====
TRIGGERS = [
    {
            'category': '主页',     'wake_word': '看今日主页', 'aliases': ['开卡路里', '卡路里面板', '今日卡路里'],     'desc': '看今天主页的整体数据,了解今天哪些做得好/差',
            'main_prompt': {
        'cli': 'python scripts/render_home.py --chain "1.识别→2.读DB聚合→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看今日主页」。\n\n我想看今天的主页 dashboard。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'home_today_overview', 'name': '看今日主页', 'subfunction': '看今日主页', 'output_type': 'result',
            'html_template': 'templates/home_dashboard.html', 'data_source': 'python scripts/render_home.py --chain "1.识别→2.读DB聚合→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看今日主页」。\n\n我想看今天的主页 dashboard。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看今天主页的整体数据,了解今天哪些做得好/差', 'data_fields': ["today_kpi", "goal_progress", "weekly_trend", "streak_days"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '主页',     'wake_word': '看今日饮食概览',     'desc': '只看今天饮食维度的完成情况',
            'main_prompt': {
        'cli': 'python scripts/render_home.py --section diet --chain "1.识别→2.读DB聚合→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看今日饮食概览」。\n\n我想看今天饮食 widget。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'home_today_diet_overview', 'name': '看今日饮食概览', 'subfunction': '看今日主页', 'output_type': 'result',
            'html_template': 'templates/home_dashboard.html', 'data_source': 'python scripts/render_home.py --section diet --chain "1.识别→2.读DB聚合→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看今日饮食概览」。\n\n我想看今天饮食 widget。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '只看今天饮食维度的完成情况', 'data_fields': ["diet_calories", "diet_protein", "diet_goal", "diet_vs_target"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '主页',     'wake_word': '看今日运动概览',     'desc': '只看今天运动维度的完成情况',
            'main_prompt': {
        'cli': 'python scripts/render_home.py --section exercise --chain "1.识别→2.读DB聚合→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看今日运动概览」。\n\n我想看今天运动 widget。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'home_today_exercise_overview', 'name': '看今日运动概览', 'subfunction': '看今日主页', 'output_type': 'result',
            'html_template': 'templates/home_dashboard.html', 'data_source': 'python scripts/render_home.py --section exercise --chain "1.识别→2.读DB聚合→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看今日运动概览」。\n\n我想看今天运动 widget。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '只看今天运动维度的完成情况', 'data_fields': ["exercise_burn", "exercise_duration", "exercise_goal", "exercise_vs_target"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '主页',     'wake_word': '看今日体重概览',     'desc': '只看今天体重维度的状态',
            'main_prompt': {
        'cli': 'python scripts/render_home.py --section weight --chain "1.识别→2.读DB聚合→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看今日体重概览」。\n\n我想看今天体重 widget。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'home_today_weight_overview', 'name': '看今日体重概览', 'subfunction': '看今日主页', 'output_type': 'result',
            'html_template': 'templates/home_dashboard.html', 'data_source': 'python scripts/render_home.py --section weight --chain "1.识别→2.读DB聚合→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看今日体重概览」。\n\n我想看今天体重 widget。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '只看今天体重维度的状态', 'data_fields': ["latest_weight", "weight_goal_gap", "weight_delta_7d"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '主页',     'wake_word': '看今日目标进度',     'desc': '看今天 4 项目标(热量/蛋白/饮水/运动)的完成度',
            'main_prompt': {
        'cli': 'python scripts/render_home.py --section goals --chain "1.识别→2.读DB聚合→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看今日目标进度」。\n\n我想看今天 4 项目标(热量/蛋白/饮水/运动)完成度。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'home_today_goal_progress', 'name': '看今日目标进度', 'subfunction': '看今日主页', 'output_type': 'result',
            'html_template': 'templates/home_dashboard.html', 'data_source': 'python scripts/render_home.py --section goals --chain "1.识别→2.读DB聚合→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看今日目标进度」。\n\n我想看今天 4 项目标(热量/蛋白/饮水/运动)完成度。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看今天 4 项目标(热量/蛋白/饮水/运动)的完成度', 'data_fields': ["goal_calorie_pct", "goal_protein_pct", "goal_water_pct", "goal_exercise_pct"],
            'depends_on_external': False, 'order': 4},
    {
            'category': '主页',     'wake_word': '看本周主页',     'desc': '看本周的整体数据总览',
            'main_prompt': {
        'cli': 'python scripts/render_home.py --period week --chain "1.识别→2.读DB聚合→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看本周主页」。\n\n我想看本周 dashboard。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'home_week_overview', 'name': '看本周主页', 'subfunction': '看周期主页', 'output_type': 'result',
            'html_template': 'templates/home_dashboard.html', 'data_source': 'python scripts/render_home.py --period week --chain "1.识别→2.读DB聚合→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看本周主页」。\n\n我想看本周 dashboard。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看本周的整体数据总览', 'data_fields': ["week_diet_total", "week_exercise_total", "week_weight_trend"],
            'depends_on_external': False, 'order': 5},
    {
            'category': '主页',     'wake_word': '看本月主页',     'desc': '看本月的整体数据总览',
            'main_prompt': {
        'cli': 'python scripts/render_home.py --period month --chain "1.识别→2.读DB聚合→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看本月主页」。\n\n我想看本月 dashboard。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'home_month_overview', 'name': '看本月主页', 'subfunction': '看周期主页', 'output_type': 'result',
            'html_template': 'templates/home_dashboard.html', 'data_source': 'python scripts/render_home.py --period month --chain "1.识别→2.读DB聚合→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看本月主页」。\n\n我想看本月 dashboard。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看本月的整体数据总览', 'data_fields': ["month_diet_total", "month_exercise_total", "month_weight_trend"],
            'depends_on_external': False, 'order': 6},
    {
            'category': '主页',     'wake_word': '看连续记录天数',     'desc': '看连续记录天数,获得激励',
            'main_prompt': {
        'cli': 'python scripts/render_home.py --section streak --chain "1.识别→2.读DB聚合→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看连续记录天数」。\n\n我想看我的连续记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'home_streak_days', 'name': '看连续记录天数', 'subfunction': '看今日成就', 'output_type': 'result',
            'html_template': 'templates/home_dashboard.html', 'data_source': 'python scripts/render_home.py --section streak --chain "1.识别→2.读DB聚合→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看连续记录天数」。\n\n我想看我的连续记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看连续记录天数,获得激励', 'data_fields': ["streak_current", "streak_longest"],
            'depends_on_external': False, 'order': 7},
    {
            'category': '主页',     'wake_word': '看今日热量预算',     'desc': '看今天还剩多少热量可吃',
            'main_prompt': {
        'cli': 'python scripts/render_home.py --section budget --chain "1.识别→2.读DB聚合→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看今日热量预算」。\n\n我想看今天还能吃多少。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'home_today_budget', 'name': '看今日热量预算', 'subfunction': '看今日主页', 'output_type': 'result',
            'html_template': 'templates/home_dashboard.html', 'data_source': 'python scripts/render_home.py --section budget --chain "1.识别→2.读DB聚合→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看今日热量预算」。\n\n我想看今天还能吃多少。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看今天还剩多少热量可吃', 'data_fields': ["tdee", "exercise_burn", "intake_today", "remaining_calories", "goal_gap"],
            'depends_on_external': False, 'order': 8},
    {
            'category': '饮食',     'wake_word': '记一餐',     'desc': '记一餐',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-diet-add <食物> <热量> <蛋白> [碳水] [脂肪] [克数] [备注] --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「记一餐」。\n\n我刚吃了一顿,帮我记录。如果我没说全克数或营养,问我补齐。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n食物名称:____\n克数(选填,默认按食品库每 100g):____\n\n⚠️ 同餐多食物(用「和/、/同时/一起」连接)必须合并为 1 个回执:全部食物确认后一次调用 --live-diet-batch-meal(issue #158),禁止逐个 --live-diet-add。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_add_meal', 'name': '记一餐', 'subfunction': '记饮食', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-diet-add <食物> <热量> <蛋白> [碳水] [脂肪] [克数] [备注] --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「记一餐」。\n\n我刚吃了一顿,帮我记录。如果我没说全克数或营养,问我补齐。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n食物名称:____\n克数(选填,默认按食品库每 100g):____\n\n⚠️ 同餐多食物(用「和/、/同时/一起」连接)必须合并为 1 个回执:全部食物确认后一次调用 --live-diet-batch-meal(issue #158),禁止逐个 --live-diet-add。',
            'user_intent': '记录刚吃的一餐食物与营养', 'data_fields': ["food_name", "grams", "calories", "protein", "carbs", "fat", "meal", "time"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '饮食',     'wake_word': '记一餐（含备注）',     'desc': '记一餐（含备注）',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-diet-add <食物> <热量> <蛋白> [碳水] [脂肪] [克数] [备注] --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「记一餐（含备注）」。\n\n我刚吃了一顿,要连同备注一起记录(如「加了辣酱」「食堂打的」)。如果我没说全克数或营养,问我补齐。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n食物名称:____\n克数(选填,默认按食品库每 100g):____\n备注:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_add_meal_note', 'name': '记一餐（含备注）', 'subfunction': '记饮食', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-diet-add <食物> <热量> <蛋白> [碳水] [脂肪] [克数] [备注] --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「记一餐（含备注）」。\n\n我刚吃了一顿,要连同备注一起记录(如「加了辣酱」「食堂打的」)。如果我没说全克数或营养,问我补齐。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n食物名称:____\n克数(选填,默认按食品库每 100g):____\n备注:____',
            'user_intent': '记录一餐并附上备注', 'data_fields': ["food_name", "grams", "calories", "protein", "carbs", "fat", "meal", "time", "note"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '饮食',     'wake_word': '补记饮食',     'desc': '补记饮食',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-diet-add <食物> <热量> <蛋白> [碳水] [脂肪] [克数] [备注] --date <日期> --time <时间> --meal <餐别> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「补记饮食」。\n\n我要补录之前某天的饮食(不是现在吃的)。如果我没说全克数或营养,问我补齐。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n食物名称:____\n日期(YYYY-MM-DD):____\n时间(选填):____\n克数(选填,默认按食品库每 100g):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_backfill', 'name': '补记饮食', 'subfunction': '记饮食', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-diet-add <食物> <热量> <蛋白> [碳水] [脂肪] [克数] [备注] --date <日期> --time <时间> --meal <餐别> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「补记饮食」。\n\n我要补录之前某天的饮食(不是现在吃的)。如果我没说全克数或营养,问我补齐。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n食物名称:____\n日期(YYYY-MM-DD):____\n时间(选填):____\n克数(选填,默认按食品库每 100g):____',
            'user_intent': '补录之前某天的饮食', 'data_fields': ["food_name", "grams", "calories", "protein", "date", "time", "meal"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '饮食',     'wake_word': '批量补记饮食',     'desc': '批量补记饮食',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-diet-batch --input <meals.json> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「批量补记饮食」。\n\n我要一次补录多餐(不同日期/不同餐别),一行一餐地说。写之前先给我看整理好的清单,确认无误再写入。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n每行一餐(日期/时间/食物/克数/营养,换行分隔):\n____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_backfill_batch', 'name': '批量补记饮食', 'subfunction': '记饮食', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-diet-batch --input <meals.json> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「批量补记饮食」。\n\n我要一次补录多餐(不同日期/不同餐别),一行一餐地说。写之前先给我看整理好的清单,确认无误再写入。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n每行一餐(日期/时间/食物/克数/营养,换行分隔):\n____',
            'user_intent': '一次批量补录多餐饮食', 'data_fields': ["date", "time", "food_name", "grams", "calories", "protein", "carbs", "fat"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '饮食',     'wake_word': '拍营养表记一餐',     'desc': '拍营养表记一餐',
            'main_prompt': {
        'cli': 'mmx vision describe <图片> → python scripts/render_nutrition_label.py --ai-json <json> → 确认后 python scripts/calorie_tracker.py add', 'text': '请你加载技能 卡路里,执行唤醒词「拍营养表记一餐」。\n\n我刚吃了这个食物,手边有包装。我拍下包装上的营养成分表给你,请你识别出热量/蛋白/碳水/脂肪等字段,给我看识别结果(照片 + 识别出的营养),我确认后记入今天的饮食。识别不确定的地方标注一下。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n营养表图片路径:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_scan_label', 'name': '拍营养表记一餐', 'subfunction': '记饮食', 'output_type': 'process',
            'html_template': 'templates/nutrition_label_wizard.html', 'data_source': 'mmx vision describe <图片> → python scripts/render_nutrition_label.py --ai-json <json> → 确认后 python scripts/calorie_tracker.py add', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「拍营养表记一餐」。\n\n我刚吃了这个食物,手边有包装。我拍下包装上的营养成分表给你,请你识别出热量/蛋白/碳水/脂肪等字段,给我看识别结果(照片 + 识别出的营养),我确认后记入今天的饮食。识别不确定的地方标注一下。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n营养表图片路径:____',
            'user_intent': '拍照识别营养成分表并记录', 'data_fields': ["calories", "protein", "carbs", "fat", "sugar", "sodium", "fiber"],
            'depends_on_external': False, 'order': 4},
    {
            'category': '饮食',     'wake_word': '拍营养表补记一餐',     'desc': '拍营养表补记一餐',
            'main_prompt': {
        'cli': 'mmx vision describe <图片> → python scripts/render_nutrition_label.py --ai-json <json> --date <日期> → 确认后 python scripts/calorie_tracker.py add --date <日期>', 'text': '请你加载技能 卡路里,执行唤醒词「拍营养表补记一餐」。\n\n我某天吃了这个食物但忘了记,现在手边有包装,拍给你识别。请你识别出热量/蛋白/碳水/脂肪等字段,给我看识别结果(照片 + 识别出的营养 + 补录日期),我确认后按那天记入饮食。识别不确定的地方标注一下。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n营养表图片路径:____\n日期(YYYY-MM-DD):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_scan_label_date', 'name': '拍营养表补记一餐', 'subfunction': '记饮食', 'output_type': 'process',
            'html_template': 'templates/nutrition_label_wizard.html', 'data_source': 'mmx vision describe <图片> → python scripts/render_nutrition_label.py --ai-json <json> --date <日期> → 确认后 python scripts/calorie_tracker.py add --date <日期>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「拍营养表补记一餐」。\n\n我某天吃了这个食物但忘了记,现在手边有包装,拍给你识别。请你识别出热量/蛋白/碳水/脂肪等字段,给我看识别结果(照片 + 识别出的营养 + 补录日期),我确认后按那天记入饮食。识别不确定的地方标注一下。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n营养表图片路径:____\n日期(YYYY-MM-DD):____',
            'user_intent': '拍照识别营养表并补录到指定日期', 'data_fields': ["calories", "protein", "carbs", "fat", "date"],
            'depends_on_external': False, 'order': 5},
    {
            'category': '饮食',     'wake_word': '记喝水',     'desc': '记喝水',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-water-add <ml> [--date <日期>] --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「记喝水」。\n\n我喝了水,帮我记录。如果我说「喝了几杯」,请按一杯约 250ml 折算成总量;如果我只说了杯子大小,先问我确认。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n喝水量(ml,或「几杯」):____'},
        'fill_hints': ['喝水量(ml,或「几杯」): '],
            'variants': [],
            'key': 'diet_log_water', 'name': '记喝水', 'subfunction': '记饮食', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-water-add <ml> [--date <日期>] --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「记喝水」。\n\n我喝了水,帮我记录。如果我说「喝了几杯」,请按一杯约 250ml 折算成总量;如果我只说了杯子大小,先问我确认。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n喝水量(ml,或「几杯」):____',
            'user_intent': '记录一次饮水(含多杯解析)', 'data_fields': ["ml", "today_total_ml", "water_goal_ml", "remaining_ml"],
            'depends_on_external': False, 'order': 6},
    {
            'category': '饮食',     'wake_word': '复制昨日饮食',     'desc': '复制昨日饮食',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-diet-copy [--from <来源日期>] [--to <目标日期>] --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「复制昨日饮食」。\n\n我要把昨天(或指定某天)吃的东西原样复制到今天(或指定某天),省得重新记。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n来源日期(选填,默认昨天):____\n目标日期(选填,默认今天):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_copy_yesterday', 'name': '复制昨日饮食', 'subfunction': '记饮食', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-diet-copy [--from <来源日期>] [--to <目标日期>] --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「复制昨日饮食」。\n\n我要把昨天(或指定某天)吃的东西原样复制到今天(或指定某天),省得重新记。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n来源日期(选填,默认昨天):____\n目标日期(选填,默认今天):____',
            'user_intent': '一键把昨天的饮食复制到今天', 'data_fields': ["copied", "skipped", "from_date", "to_date"],
            'depends_on_external': False, 'order': 7},
    {
            'category': '饮食',     'wake_word': '改饮食记录',     'desc': '改饮食记录',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-diet-update <id> [--food <食物>] [--grams <克数>] [--calories <热量>] [--protein <蛋白>] [--carbs <碳水>] [--fat <脂肪>] [--date <日期>] [--time <时间>] [--note <备注>] --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「改饮食记录」。\n\n我要改某条饮食记录。如果我没说清是哪条,请先列出最近的记录让我选。改之前先给我看这条记录的当前内容。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n要改的记录(如「最近一条」或日期+食物):____\n要改的字段(食物/克数/热量/蛋白/碳水/脂肪/日期/时间/备注):____\n新值:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_update_record', 'name': '改饮食记录', 'subfunction': '改饮食', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-diet-update <id> [--food <食物>] [--grams <克数>] [--calories <热量>] [--protein <蛋白>] [--carbs <碳水>] [--fat <脂肪>] [--date <日期>] [--time <时间>] [--note <备注>] --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改饮食记录」。\n\n我要改某条饮食记录。如果我没说清是哪条,请先列出最近的记录让我选。改之前先给我看这条记录的当前内容。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n要改的记录(如「最近一条」或日期+食物):____\n要改的字段(食物/克数/热量/蛋白/碳水/脂肪/日期/时间/备注):____\n新值:____',
            'user_intent': '修改某条饮食记录的字段', 'data_fields': ["food_name", "grams", "calories", "protein", "carbs", "fat", "note"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '饮食',     'wake_word': '改某日饮食',     'desc': '改某日饮食',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-diet-update-date <日期> [--字段 新值 ...] --chain "1.解析→2.写库→3.回执"', 'text': "请你加载技能 卡路里,执行唤醒词「改某日饮食」。\n\n我要改某一天的全部饮食记录(如那天的时间/克数/备注都记错了)。改之前先告诉我那天有几条记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n日期(YYYY-MM-DD):____\n要改的字段与新值(如 备注=修正):____"},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_update_by_date', 'name': '改某日饮食', 'subfunction': '改饮食', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-diet-update-date <日期> [--字段 新值 ...] --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改某日饮食」。\n\n我要改某一天的全部饮食记录(如那天的时间/克数/备注都记错了)。改之前先告诉我那天有几条记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n日期(YYYY-MM-DD):____\n要改的字段与新值(如 备注=修正):____',
            'user_intent': '按日期批量修改当天饮食记录', 'data_fields': ["date", "matched", "updated", "changed_fields"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '饮食',     'wake_word': '删饮食记录',     'desc': '删饮食记录',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-diet-delete <id> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「删饮食记录」。\n\n我要删一条饮食记录。如果我没说清是哪条,请先列出最近的几条让我选。删除前先给我看这条记录的内容,确认无误再删,最后给我确认回执。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n要删的记录(选填,如「最近一条」或日期):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_delete_record', 'name': '删饮食记录', 'subfunction': '改饮食', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-diet-delete <id> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「删饮食记录」。\n\n我要删一条饮食记录。如果我没说清是哪条,请先列出最近的几条让我选。删除前先给我看这条记录的内容,确认无误再删,最后给我确认回执。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n要删的记录(选填,如「最近一条」或日期):____',
            'user_intent': '删除一条饮食记录', 'data_fields': ["id", "food_name", "calories", "date", "snapshot"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '饮食',     'wake_word': '删一餐',     'desc': '删一餐',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-diet-delete-meal <日期> <餐别> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「删一餐」。\n\n我要删某天某一餐的全部记录(如删掉今天的早餐)。如果我没说日期默认今天。删除前告诉我这一餐有几条,确认后删除。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n餐别(早餐/午餐/下午茶/晚餐/夜宵/加餐):____\n日期(选填,默认今天):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_delete_by_meal', 'name': '删一餐', 'subfunction': '改饮食', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-diet-delete-meal <日期> <餐别> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「删一餐」。\n\n我要删某天某一餐的全部记录(如删掉今天的早餐)。如果我没说日期默认今天。删除前告诉我这一餐有几条,确认后删除。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n餐别(早餐/午餐/下午茶/晚餐/夜宵/加餐):____\n日期(选填,默认今天):____',
            'user_intent': '按餐别删除某天的一餐记录', 'data_fields': ["date", "meal", "deleted"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '饮食',     'wake_word': '删某日饮食',     'desc': '删某日饮食',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-diet-delete-date <日期> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「删某日饮食」。\n\n我要清空某一天的整日饮食记录。删除前告诉我那天有几条,确认后删除。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n日期(YYYY-MM-DD):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_delete_by_date', 'name': '删某日饮食', 'subfunction': '改饮食', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-diet-delete-date <日期> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「删某日饮食」。\n\n我要清空某一天的整日饮食记录。删除前告诉我那天有几条,确认后删除。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n日期(YYYY-MM-DD):____',
            'user_intent': '清空某一天的整日饮食记录', 'data_fields': ["date", "deleted"],
            'depends_on_external': False, 'order': 4},
    {
            'category': '饮食',     'wake_word': '批量删饮食',     'desc': '批量删饮食',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-diet-delete-range <开始> <结束> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「批量删饮食」。\n\n我要按日期范围批量删除饮食记录。删除前告诉我这个范围有几条,确认后删除。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_delete_by_range', 'name': '批量删饮食', 'subfunction': '改饮食', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-diet-delete-range <开始> <结束> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「批量删饮食」。\n\n我要按日期范围批量删除饮食记录。删除前告诉我这个范围有几条,确认后删除。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____',
            'user_intent': '按日期范围批量删除饮食记录', 'data_fields': ["start", "end", "deleted"],
            'depends_on_external': False, 'order': 5},
    {
            'category': '饮食',     'wake_word': '看今日饮食',     'desc': '看今日饮食',
            'main_prompt': {
        'cli': 'python scripts/render_today_diet.py --mode nutrition --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看今日饮食」。\n\n我想看今天的饮食。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_view_today', 'name': '看今日饮食', 'subfunction': '看饮食', 'output_type': 'result',
            'html_template': 'templates/today_diet.html', 'data_source': 'python scripts/render_today_diet.py --mode nutrition --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看今日饮食」。\n\n我想看今天的饮食。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看今天按餐别分组的饮食明细', 'data_fields': ["meal", "food_name", "grams", "calories", "protein", "carbs", "fat", "goal"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '饮食',     'wake_word': '看昨日饮食',     'desc': '看昨日饮食',
            'main_prompt': {
        'cli': 'python scripts/render_today_diet.py --date <昨天> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看昨日饮食」。\n\n我想看昨天的饮食。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_view_yesterday', 'name': '看昨日饮食', 'subfunction': '看饮食', 'output_type': 'result',
            'html_template': 'templates/today_diet.html', 'data_source': 'python scripts/render_today_diet.py --date <昨天> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看昨日饮食」。\n\n我想看昨天的饮食。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看昨天按餐别分组的饮食明细', 'data_fields': ["meal", "food_name", "grams", "calories", "protein", "carbs", "fat", "goal"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '饮食',     'wake_word': '看本周饮食',     'desc': '看本周饮食',
            'main_prompt': {
        'cli': 'python scripts/render_today_meals.py --week current --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看本周饮食」。\n\n我想看本周(周一到今天)的饮食明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_view_this_week', 'name': '看本周饮食', 'subfunction': '看饮食', 'output_type': 'result',
            'html_template': 'templates/today_meals.html', 'data_source': 'python scripts/render_today_meals.py --week current --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看本周饮食」。\n\n我想看本周(周一到今天)的饮食明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看本周自然周的饮食明细与汇总', 'data_fields': ["date", "food_name", "calories", "protein", "total_calorie", "avg_calorie"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '饮食',     'wake_word': '看上周饮食',     'desc': '看上周饮食',
            'main_prompt': {
        'cli': 'python scripts/render_today_meals.py --week last --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看上周饮食」。\n\n我想看上周(上一个自然周)的饮食明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_view_last_week', 'name': '看上周饮食', 'subfunction': '看饮食', 'output_type': 'result',
            'html_template': 'templates/today_meals.html', 'data_source': 'python scripts/render_today_meals.py --week last --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看上周饮食」。\n\n我想看上周(上一个自然周)的饮食明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看上周自然周的饮食明细与汇总', 'data_fields': ["date", "food_name", "calories", "protein", "total_calorie", "avg_calorie"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '饮食',     'wake_word': '看本月饮食',     'desc': '看本月饮食',
            'main_prompt': {
        'cli': 'python scripts/render_today_meals.py --month current --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看本月饮食」。\n\n我想看本月(自然月)的饮食明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_view_this_month', 'name': '看本月饮食', 'subfunction': '看饮食', 'output_type': 'result',
            'html_template': 'templates/today_meals.html', 'data_source': 'python scripts/render_today_meals.py --month current --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看本月饮食」。\n\n我想看本月(自然月)的饮食明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看本月自然月的饮食明细与汇总', 'data_fields': ["date", "food_name", "calories", "protein", "total_calorie", "avg_calorie"],
            'depends_on_external': False, 'order': 4},
    {
            'category': '饮食',     'wake_word': '看上月饮食',     'desc': '看上月饮食',
            'main_prompt': {
        'cli': 'python scripts/render_today_meals.py --month last --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看上月饮食」。\n\n我想看上月(上一个自然月)的饮食明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_view_last_month', 'name': '看上月饮食', 'subfunction': '看饮食', 'output_type': 'result',
            'html_template': 'templates/today_meals.html', 'data_source': 'python scripts/render_today_meals.py --month last --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看上月饮食」。\n\n我想看上月(上一个自然月)的饮食明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看上月自然月的饮食明细与汇总', 'data_fields': ["date", "food_name", "calories", "protein", "total_calorie", "avg_calorie"],
            'depends_on_external': False, 'order': 5},
    {
            'category': '饮食',     'wake_word': '看最近 7 天饮食',     'desc': '看最近 7 天饮食',
            'main_prompt': {
        'cli': 'python scripts/render_today_meals.py --days 7 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看最近 7 天饮食」。\n\n我想看最近 7 天(滚动窗口)的饮食明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_view_7d', 'name': '看最近 7 天饮食', 'subfunction': '看饮食', 'output_type': 'result',
            'html_template': 'templates/today_meals.html', 'data_source': 'python scripts/render_today_meals.py --days 7 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看最近 7 天饮食」。\n\n我想看最近 7 天(滚动窗口)的饮食明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 7 天滚动窗口的饮食明细', 'data_fields': ["date", "food_name", "calories", "protein", "total_calorie", "avg_calorie"],
            'depends_on_external': False, 'order': 6},
    {
            'category': '饮食',     'wake_word': '看最近 30 天饮食',     'desc': '看最近 30 天饮食',
            'main_prompt': {
        'cli': 'python scripts/render_today_meals.py --days 30 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看最近 30 天饮食」。\n\n我想看最近 30 天(滚动窗口)的饮食。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_view_30d', 'name': '看最近 30 天饮食', 'subfunction': '看饮食', 'output_type': 'result',
            'html_template': 'templates/today_meals.html', 'data_source': 'python scripts/render_today_meals.py --days 30 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看最近 30 天饮食」。\n\n我想看最近 30 天(滚动窗口)的饮食。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 30 天滚动窗口的饮食汇总', 'data_fields': ["date", "calories", "total_calorie", "avg_calorie"],
            'depends_on_external': False, 'order': 7},
    {
            'category': '饮食',     'wake_word': '看某段时间饮食',     'desc': '看某段时间饮食',
            'main_prompt': {
        'cli': 'python scripts/render_today_meals.py --start <开始> --end <结束> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看某段时间饮食」。\n\n我想看自定义日期区间的饮食明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_view_range', 'name': '看某段时间饮食', 'subfunction': '看饮食', 'output_type': 'result',
            'html_template': 'templates/today_meals.html', 'data_source': 'python scripts/render_today_meals.py --start <开始> --end <结束> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看某段时间饮食」。\n\n我想看自定义日期区间的饮食明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____',
            'user_intent': '看自定义日期区间的饮食明细', 'data_fields': ["start", "end", "date", "food_name", "calories", "total_calorie", "avg_calorie"],
            'depends_on_external': False, 'order': 8},
    {
            'category': '饮食',     'wake_word': '看今日喝水',     'desc': '看今日喝水',
            'main_prompt': {
        'cli': 'python scripts/render_today_water.py --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看今日喝水」。\n\n我想看今天的饮水。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_view_water', 'name': '看今日喝水', 'subfunction': '看饮食', 'output_type': 'result',
            'html_template': 'templates/today_water.html', 'data_source': 'python scripts/render_today_water.py --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看今日喝水」。\n\n我想看今天的饮水。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看今日饮水总量与目标进度', 'data_fields': ["total_ml", "goal_ml", "remaining_ml", "cups"],
            'depends_on_external': False, 'order': 9},
    {
            'category': '饮食',     'wake_word': '看有备注的饮食记录',     'desc': '看「有备注」的饮食记录',
            'main_prompt': {
        'cli': 'python scripts/render_today_meals.py --with-note --days <N> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看有备注的饮食记录」。\n\n我想看带备注的饮食记录(如「加了辣酱」「食堂打的」)。时间范围默认最近 7 天,也可指定。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n时间范围(选填,默认最近 7 天):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_view_with_note', 'name': '看「有备注」的饮食记录', 'subfunction': '看饮食', 'output_type': 'result',
            'html_template': 'templates/today_meals.html', 'data_source': 'python scripts/render_today_meals.py --with-note --days <N> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看有备注的饮食记录」。\n\n我想看带备注的饮食记录(如「加了辣酱」「食堂打的」)。时间范围默认最近 7 天,也可指定。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n时间范围(选填,默认最近 7 天):____',
            'user_intent': '查看带备注的饮食记录', 'data_fields': ["date", "meal", "food_name", "grams", "calories", "protein", "note"],
            'depends_on_external': False, 'order': 10},
    {
            'category': '饮食',     'wake_word': '查食品',     'desc': '查食品',
            'main_prompt': {
        'cli': 'python scripts/render_food_search.py --query <关键词>', 'text': '请你加载技能 卡路里,执行唤醒词「查食品」。\n\n我想查某食物的营养数据。如果没查到精确的,给我相近的几条。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n食物名称:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'food_search', 'name': '查食品', 'subfunction': '查食品', 'output_type': 'result',
            'html_template': 'templates/food_search.html', 'data_source': 'python scripts/render_food_search.py --query <关键词>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「查食品」。\n\n我想查某食物的营养数据。如果没查到精确的,给我相近的几条。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n食物名称:____',
            'user_intent': '查询食物的营养数据', 'data_fields': ["product_name", "brand", "calories", "protein", "carbs", "fat", "source"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '饮食',     'wake_word': '查食品（按分类）',     'desc': '查食品（按分类）',
            'main_prompt': {
        'cli': 'python scripts/render_food_search.py --category <分类>', 'text': '请你加载技能 卡路里,执行唤醒词「查食品（按分类）」。\n\n我想按分类查食品库(如 饮料/主食/蛋白类/水果/零食):列出该分类全部食品 + 营养数据,按分类分组。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n分类名称:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'food_search_category', 'name': '查食品（按分类）', 'subfunction': '查食品', 'output_type': 'result',
            'html_template': 'templates/food_search.html', 'data_source': 'python scripts/render_food_search.py --category <分类>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「查食品（按分类）」。\n\n我想按分类查食品库(如 饮料/主食/蛋白类/水果/零食):列出该分类全部食品 + 营养数据,按分类分组。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n分类名称:____',
            'user_intent': '按分类浏览食品库', 'data_fields': ["category", "product_name", "brand", "calories", "protein"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '饮食',     'wake_word': '存食品',     'desc': '存食品',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-product-add <名称> <品牌> <热量> <蛋白> <脂肪> <饱和脂肪> <碳水> <糖> <纤维> <钠> [备注] --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「存食品」。\n\n我要把新食品的营养数据存进食品库(每 100g 为基准)。告诉我必填字段:名称/品牌/热量/蛋白/脂肪/饱和脂肪/碳水/糖/纤维/钠/来源。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n食品名称:____\n品牌:____\n热量(每 100g):____\n蛋白:____\n脂肪:____\n饱和脂肪(选填):____\n碳水:____\n糖(选填):____\n纤维(选填):____\n钠:____\n来源(选填):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'food_add', 'name': '存食品', 'subfunction': '查食品', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-product-add <名称> <品牌> <热量> <蛋白> <脂肪> <饱和脂肪> <碳水> <糖> <纤维> <钠> [备注] --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「存食品」。\n\n我要把新食品的营养数据存进食品库(每 100g 为基准)。告诉我必填字段:名称/品牌/热量/蛋白/脂肪/饱和脂肪/碳水/糖/纤维/钠/来源。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n食品名称:____\n品牌:____\n热量(每 100g):____\n蛋白:____\n脂肪:____\n饱和脂肪(选填):____\n碳水:____\n糖(选填):____\n纤维(选填):____\n钠:____\n来源(选填):____',
            'user_intent': '把新食品的营养数据存入食品库', 'data_fields': ["product_name", "brand", "calories", "protein", "fat", "carbohydrates", "sodium", "source"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '饮食',     'wake_word': '改食品',     'desc': '改食品',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-product-update <id> [--字段 新值 ...] --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「改食品」。\n\n我要改食品库里某条食品的营养数据。如果我没说清是哪条,先列出相近的几条让我选。改前给我看原值。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n食品名称或编号:____\n要改的字段(热量/蛋白/脂肪/碳水/糖/钠/品牌等):____\n新值:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'food_update', 'name': '改食品', 'subfunction': '查食品', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-product-update <id> [--字段 新值 ...] --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改食品」。\n\n我要改食品库里某条食品的营养数据。如果我没说清是哪条,先列出相近的几条让我选。改前给我看原值。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n食品名称或编号:____\n要改的字段(热量/蛋白/脂肪/碳水/糖/钠/品牌等):____\n新值:____',
            'user_intent': '修改食品库中某条食品的数据', 'data_fields': ["product_name", "brand", "calories", "protein", "fat", "carbohydrates", "sodium"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '饮食',     'wake_word': '下架食品',     'desc': '下架食品',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-product-deprecate <id> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「下架食品」。\n\n我要把食品库里的某条食品下架(标废弃,以后查询/搜索/导入去重都不再出现)。先确认是哪条,下架后给我回执并提示「已下架」。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n食品名称或编号:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'food_deprecate', 'name': '下架食品', 'subfunction': '查食品', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-product-deprecate <id> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「下架食品」。\n\n我要把食品库里的某条食品下架(标废弃,以后查询/搜索/导入去重都不再出现)。先确认是哪条,下架后给我回执并提示「已下架」。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n食品名称或编号:____',
            'user_intent': '下架食品库中的某条食品', 'data_fields': ["id", "product_name", "is_deprecated"],
            'depends_on_external': False, 'order': 4},
    {
            'category': '饮食',     'wake_word': '看食品库（去重）',     'desc': '看食品库（去重）',
            'main_prompt': {
        'cli': 'python scripts/render_dedupe_report.py', 'text': '请你加载技能 卡路里,执行唤醒词「看食品库（去重）」。\n\n我想检查食品库有没有重复的食品(同名同品牌多条)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'food_dedupe', 'name': '看食品库（去重）', 'subfunction': '查食品', 'output_type': 'result',
            'html_template': 'templates/dedupe_report.html', 'data_source': 'python scripts/render_dedupe_report.py', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看食品库（去重）」。\n\n我想检查食品库有没有重复的食品(同名同品牌多条)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '检查食品库中的重复条目', 'data_fields': ["product_name", "brand", "count", "ids"],
            'depends_on_external': False, 'order': 5},
    {
            'category': '饮食',     'wake_word': '批量导入食品',     'desc': '批量导入食品',
            'main_prompt': {
        'cli': 'python scripts/render_batch_import.py --input <preview.json> → 确认后 python scripts/batch_import.py import <file.jsonl>', 'text': '请你加载技能 卡路里,执行唤醒词「批量导入食品」。\n\n我有一个食品数据文件(每行一条:名称/热量/蛋白/脂肪/碳水/钠/来源等)要批量导入食品库。先给我看导入预览(导入条数/跳过条数/失败明细),我确认后再真正写入。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n文件路径:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'food_batch_import', 'name': '批量导入食品', 'subfunction': '查食品', 'output_type': 'process',
            'html_template': 'templates/batch_import_preview.html', 'data_source': 'python scripts/render_batch_import.py --input <preview.json> → 确认后 python scripts/batch_import.py import <file.jsonl>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「批量导入食品」。\n\n我有一个食品数据文件(每行一条:名称/热量/蛋白/脂肪/碳水/钠/来源等)要批量导入食品库。先给我看导入预览(导入条数/跳过条数/失败明细),我确认后再真正写入。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n文件路径:____',
            'user_intent': '批量导入食品数据到食品库', 'data_fields': ["product_name", "calories", "protein", "fat", "carbohydrates", "sodium", "source"],
            'depends_on_external': False, 'order': 6},
    {
            'category': '饮食',     'wake_word': '校验批量导入',     'desc': '校验批量导入',
            'main_prompt': {
        'cli': 'python scripts/batch_import.py validate <file.jsonl> --json-output <out.json> → python scripts/render_batch_import.py --input <out.json>', 'text': '请你加载技能 卡路里,执行唤醒词「校验批量导入」。\n\n我有一个食品数据文件(每行一条),只想先校验能不能导入,不真正写入。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n文件路径:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'food_batch_validate', 'name': '校验批量导入', 'subfunction': '查食品', 'output_type': 'result',
            'html_template': 'templates/batch_import_preview.html', 'data_source': 'python scripts/batch_import.py validate <file.jsonl> --json-output <out.json> → python scripts/render_batch_import.py --input <out.json>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「校验批量导入」。\n\n我有一个食品数据文件(每行一条),只想先校验能不能导入,不真正写入。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n文件路径:____',
            'user_intent': '预校验批量导入文件能否通过', 'data_fields': ["line", "name", "status", "reason"],
            'depends_on_external': False, 'order': 7},
    {
            'category': '饮食',     'wake_word': '看食品来源统计',     'desc': '看食品来源统计',
            'main_prompt': {
        'cli': 'python scripts/render_source_stats.py', 'text': '请你加载技能 卡路里,执行唤醒词「看食品来源统计」。\n\n我想看食品库的食品来源分布(按来源分组计数)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'food_source_stats', 'name': '看食品来源统计', 'subfunction': '查食品', 'output_type': 'result',
            'html_template': 'templates/source_stats.html', 'data_source': 'python scripts/render_source_stats.py', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看食品来源统计」。\n\n我想看食品库的食品来源分布(按来源分组计数)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看食品库按来源分组的统计', 'data_fields': ["source", "count", "pct", "total"],
            'depends_on_external': False, 'order': 8},
    {
            'category': '饮食',     'wake_word': '看营养结构',     'desc': '看营养结构',
            'main_prompt': {
        'cli': 'python scripts/render_nutrition_ratio.py --days 7 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看营养结构」。\n\n我想看最近一段时间(默认 7 天)的蛋白/碳水/脂肪占比。如果我要看别的窗口会告诉你。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n时间范围(选填,默认最近 7 天):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'nutrition_ratio', 'name': '看营养结构', 'subfunction': '看营养', 'output_type': 'result',
            'html_template': 'templates/nutrition_ratio.html', 'data_source': 'python scripts/render_nutrition_ratio.py --days 7 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看营养结构」。\n\n我想看最近一段时间(默认 7 天)的蛋白/碳水/脂肪占比。如果我要看别的窗口会告诉你。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n时间范围(选填,默认最近 7 天):____',
            'user_intent': '看蛋白碳水脂肪的营养占比', 'data_fields': ["protein_pct", "carb_pct", "fat_pct", "goal"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '饮食',     'wake_word': '看今日营养',     'desc': '看今日营养',
            'main_prompt': {
        'cli': 'python scripts/render_today_diet.py --mode nutrition --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看今日营养」。\n\n我想看今天 4 项营养(热量/蛋白/碳水/脂肪)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'nutrition_today', 'name': '看今日营养', 'subfunction': '看营养', 'output_type': 'result',
            'html_template': 'templates/today_diet.html', 'data_source': 'python scripts/render_today_diet.py --mode nutrition --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看今日营养」。\n\n我想看今天 4 项营养(热量/蛋白/碳水/脂肪)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看今日 4 项营养完成度', 'data_fields': ["calories", "protein", "carbs", "fat", "goal", "pct"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '饮食',     'wake_word': '看饮食总览',     'desc': '看饮食总览',
            'main_prompt': {
        'cli': 'python scripts/render_diet_overview.py --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看饮食总览」。\n\n我想看周期累计的饮食总览。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'nutrition_overview', 'name': '看饮食总览', 'subfunction': '看营养', 'output_type': 'result',
            'html_template': 'templates/diet_overview.html', 'data_source': 'python scripts/render_diet_overview.py --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看饮食总览」。\n\n我想看周期累计的饮食总览。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看本周本月累计饮食总览', 'data_fields': ["week_total", "month_total", "avg_cal", "trend"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '饮食',     'wake_word': '看营养素深度',     'desc': '看营养素深度',
            'main_prompt': {
        'cli': 'python scripts/render_nutrition_detail.py --days 7 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看营养素深度」。\n\n我想看微量营养素摄入。食品库没有的按缺数据标注。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n时间范围(选填,默认最近 7 天):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'nutrition_detail', 'name': '看营养素深度', 'subfunction': '看营养', 'output_type': 'result',
            'html_template': 'templates/nutrition_detail.html', 'data_source': 'python scripts/render_nutrition_detail.py --days 7 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看营养素深度」。\n\n我想看微量营养素摄入。食品库没有的按缺数据标注。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n时间范围(选填,默认最近 7 天):____',
            'user_intent': '看纤维钠糖等微量营养素摄入', 'data_fields': ["fiber", "sodium", "sugar", "target", "missing_foods"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '饮食',     'wake_word': '看高热量榜',     'desc': '看高热量榜',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category high_calorie --top-n 10 --days 7 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看高热量榜」。\n\n我想看最近一段时间(默认 7 天)热量最高的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_high_calorie', 'name': '看高热量榜', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category high_calorie --top-n 10 --days 7 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看高热量榜」。\n\n我想看最近一段时间(默认 7 天)热量最高的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看高热量食物 TOP10', 'data_fields': ["rank", "food_name", "calories"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '饮食',     'wake_word': '看低热量榜',     'desc': '看低热量榜',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category low_calorie --top-n 10 --days 7 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看低热量榜」。\n\n我想看最近一段时间(默认 7 天)热量最低的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_low_calorie', 'name': '看低热量榜', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category low_calorie --top-n 10 --days 7 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看低热量榜」。\n\n我想看最近一段时间(默认 7 天)热量最低的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看低热量食物 TOP10', 'data_fields': ["rank", "food_name", "calories"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '饮食',     'wake_word': '看频繁吃榜',     'desc': '看频繁吃榜',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category frequent --top-n 10 --days 7 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看频繁吃榜」。\n\n我想看最近一段时间(默认 7 天)吃得最多的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_frequent', 'name': '看频繁吃榜', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category frequent --top-n 10 --days 7 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看频繁吃榜」。\n\n我想看最近一段时间(默认 7 天)吃得最多的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最常吃的食物 TOP10', 'data_fields': ["rank", "food_name", "count", "last_date"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '饮食',     'wake_word': '看高碳水榜',     'desc': '看高碳水榜',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category high_carb --top-n 10 --days 7 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看高碳水榜」。\n\n我想看最近一段时间(默认 7 天)碳水最高的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_high_carb', 'name': '看高碳水榜', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category high_carb --top-n 10 --days 7 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看高碳水榜」。\n\n我想看最近一段时间(默认 7 天)碳水最高的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看高碳水食物 TOP10', 'data_fields': ["rank", "food_name", "carbs"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '饮食',     'wake_word': '看高蛋白榜',     'desc': '看高蛋白榜',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category high_protein --top-n 10 --days 7 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看高蛋白榜」。\n\n我想看最近一段时间(默认 7 天)蛋白最高的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_high_protein', 'name': '看高蛋白榜', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category high_protein --top-n 10 --days 7 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看高蛋白榜」。\n\n我想看最近一段时间(默认 7 天)蛋白最高的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看高蛋白食物 TOP10', 'data_fields': ["rank", "food_name", "protein"],
            'depends_on_external': False, 'order': 4},
    {
            'category': '饮食',     'wake_word': '看全部排行榜',     'desc': '看全部排行榜',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --all --top-n 10 --days <N> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看全部排行榜」。\n\n我想同时看所有食物榜单。时间范围默认最近 7 天,也可指定。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n时间范围(选填,默认最近 7 天):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_all', 'name': '看全部排行榜', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --all --top-n 10 --days <N> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看全部排行榜」。\n\n我想同时看所有食物榜单。时间范围默认最近 7 天,也可指定。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n时间范围(选填,默认最近 7 天):____',
            'user_intent': '同时看 5 个食物榜单(高热量/低热量/频繁吃/高碳水/高蛋白)', 'data_fields': ["rank", "food_name", "calories", "cnt", "category"],
            'depends_on_external': False, 'order': 5},
    {
            'category': '饮食',     'wake_word': '看高热量榜（最近 30 天）',     'desc': '看高热量榜（最近 30 天）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category high_calorie --top-n 10 --days 30 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看高热量榜（最近 30 天）」。\n\n我想看最近 30 天热量最高的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_high_calorie_30d', 'name': '看高热量榜（最近 30 天）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category high_calorie --top-n 10 --days 30 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看高热量榜（最近 30 天）」。\n\n我想看最近 30 天热量最高的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 30 天高热量食物 TOP10', 'data_fields': ["rank", "food_name", "calories"],
            'depends_on_external': False, 'order': 5},
    {
            'category': '饮食',     'wake_word': '看高热量榜（本月）',     'desc': '看高热量榜（本月）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category high_calorie --top-n 10 --start <月初> --end <月末> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看高热量榜（本月）」。\n\n我想看本月(自然月)热量最高的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_high_calorie_month', 'name': '看高热量榜（本月）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category high_calorie --top-n 10 --start <月初> --end <月末> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看高热量榜（本月）」。\n\n我想看本月(自然月)热量最高的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看本月高热量食物 TOP10', 'data_fields': ["rank", "food_name", "calories"],
            'depends_on_external': False, 'order': 6},
    {
            'category': '饮食',     'wake_word': '看高热量榜（自定义）',     'desc': '看高热量榜（自定义）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category high_calorie --top-n 10 --start <开始> --end <结束> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看高热量榜（自定义）」。\n\n我想看自定义日期区间热量最高的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_high_calorie_custom', 'name': '看高热量榜（自定义）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category high_calorie --top-n 10 --start <开始> --end <结束> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看高热量榜（自定义）」。\n\n我想看自定义日期区间热量最高的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____',
            'user_intent': '看自定义区间高热量食物 TOP10', 'data_fields': ["rank", "food_name", "calories", "start", "end"],
            'depends_on_external': False, 'order': 7},
    {
            'category': '饮食',     'wake_word': '看低热量榜（最近 30 天）',     'desc': '看低热量榜（最近 30 天）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category low_calorie --top-n 10 --days 30 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看低热量榜（最近 30 天）」。\n\n我想看最近 30 天热量最低的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_low_calorie_30d', 'name': '看低热量榜（最近 30 天）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category low_calorie --top-n 10 --days 30 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看低热量榜（最近 30 天）」。\n\n我想看最近 30 天热量最低的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 30 天低热量食物 TOP10', 'data_fields': ["rank", "food_name", "calories"],
            'depends_on_external': False, 'order': 8},
    {
            'category': '饮食',     'wake_word': '看低热量榜（本月）',     'desc': '看低热量榜（本月）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category low_calorie --top-n 10 --start <月初> --end <月末> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看低热量榜（本月）」。\n\n我想看本月(自然月)热量最低的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_low_calorie_month', 'name': '看低热量榜（本月）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category low_calorie --top-n 10 --start <月初> --end <月末> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看低热量榜（本月）」。\n\n我想看本月(自然月)热量最低的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看本月低热量食物 TOP10', 'data_fields': ["rank", "food_name", "calories"],
            'depends_on_external': False, 'order': 9},
    {
            'category': '饮食',     'wake_word': '看低热量榜（自定义）',     'desc': '看低热量榜（自定义）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category low_calorie --top-n 10 --start <开始> --end <结束> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看低热量榜（自定义）」。\n\n我想看自定义日期区间热量最低的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_low_calorie_custom', 'name': '看低热量榜（自定义）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category low_calorie --top-n 10 --start <开始> --end <结束> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看低热量榜（自定义）」。\n\n我想看自定义日期区间热量最低的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____',
            'user_intent': '看自定义区间低热量食物 TOP10', 'data_fields': ["rank", "food_name", "calories", "start", "end"],
            'depends_on_external': False, 'order': 10},
    {
            'category': '饮食',     'wake_word': '看频繁吃榜（最近 30 天）',     'desc': '看频繁吃榜（最近 30 天）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category frequent --top-n 10 --days 30 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看频繁吃榜（最近 30 天）」。\n\n我想看最近 30 天吃得最多的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_frequent_30d', 'name': '看频繁吃榜（最近 30 天）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category frequent --top-n 10 --days 30 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看频繁吃榜（最近 30 天）」。\n\n我想看最近 30 天吃得最多的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 30 天最常吃的食物 TOP10', 'data_fields': ["rank", "food_name", "count", "last_date"],
            'depends_on_external': False, 'order': 11},
    {
            'category': '饮食',     'wake_word': '看频繁吃榜（本月）',     'desc': '看频繁吃榜（本月）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category frequent --top-n 10 --start <月初> --end <月末> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看频繁吃榜（本月）」。\n\n我想看本月(自然月)吃得最多的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_frequent_month', 'name': '看频繁吃榜（本月）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category frequent --top-n 10 --start <月初> --end <月末> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看频繁吃榜（本月）」。\n\n我想看本月(自然月)吃得最多的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看本月最常吃的食物 TOP10', 'data_fields': ["rank", "food_name", "count", "last_date"],
            'depends_on_external': False, 'order': 12},
    {
            'category': '饮食',     'wake_word': '看频繁吃榜（自定义）',     'desc': '看频繁吃榜（自定义）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category frequent --top-n 10 --start <开始> --end <结束> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看频繁吃榜（自定义）」。\n\n我想看自定义日期区间吃得最多的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_frequent_custom', 'name': '看频繁吃榜（自定义）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category frequent --top-n 10 --start <开始> --end <结束> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看频繁吃榜（自定义）」。\n\n我想看自定义日期区间吃得最多的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____',
            'user_intent': '看自定义区间最常吃的食物 TOP10', 'data_fields': ["rank", "food_name", "count", "last_date", "start", "end"],
            'depends_on_external': False, 'order': 13},
    {
            'category': '饮食',     'wake_word': '看高碳水榜（最近 30 天）',     'desc': '看高碳水榜（最近 30 天）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category high_carb --top-n 10 --days 30 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看高碳水榜（最近 30 天）」。\n\n我想看最近 30 天碳水最高的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_high_carb_30d', 'name': '看高碳水榜（最近 30 天）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category high_carb --top-n 10 --days 30 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看高碳水榜（最近 30 天）」。\n\n我想看最近 30 天碳水最高的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 30 天高碳水食物 TOP10', 'data_fields': ["rank", "food_name", "carbs"],
            'depends_on_external': False, 'order': 14},
    {
            'category': '饮食',     'wake_word': '看高碳水榜（本月）',     'desc': '看高碳水榜（本月）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category high_carb --top-n 10 --start <月初> --end <月末> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看高碳水榜（本月）」。\n\n我想看本月(自然月)碳水最高的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_high_carb_month', 'name': '看高碳水榜（本月）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category high_carb --top-n 10 --start <月初> --end <月末> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看高碳水榜（本月）」。\n\n我想看本月(自然月)碳水最高的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看本月高碳水食物 TOP10', 'data_fields': ["rank", "food_name", "carbs"],
            'depends_on_external': False, 'order': 15},
    {
            'category': '饮食',     'wake_word': '看高碳水榜（自定义）',     'desc': '看高碳水榜（自定义）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category high_carb --top-n 10 --start <开始> --end <结束> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看高碳水榜（自定义）」。\n\n我想看自定义日期区间碳水最高的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_high_carb_custom', 'name': '看高碳水榜（自定义）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category high_carb --top-n 10 --start <开始> --end <结束> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看高碳水榜（自定义）」。\n\n我想看自定义日期区间碳水最高的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____',
            'user_intent': '看自定义区间高碳水食物 TOP10', 'data_fields': ["rank", "food_name", "carbs", "start", "end"],
            'depends_on_external': False, 'order': 16},
    {
            'category': '饮食',     'wake_word': '看高蛋白榜（最近 30 天）',     'desc': '看高蛋白榜（最近 30 天）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category high_protein --top-n 10 --days 30 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看高蛋白榜（最近 30 天）」。\n\n我想看最近 30 天蛋白最高的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_high_protein_30d', 'name': '看高蛋白榜（最近 30 天）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category high_protein --top-n 10 --days 30 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看高蛋白榜（最近 30 天）」。\n\n我想看最近 30 天蛋白最高的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 30 天高蛋白食物 TOP10', 'data_fields': ["rank", "food_name", "protein"],
            'depends_on_external': False, 'order': 17},
    {
            'category': '饮食',     'wake_word': '看高蛋白榜（本月）',     'desc': '看高蛋白榜（本月）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category high_protein --top-n 10 --start <月初> --end <月末> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看高蛋白榜（本月）」。\n\n我想看本月(自然月)蛋白最高的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_high_protein_month', 'name': '看高蛋白榜（本月）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category high_protein --top-n 10 --start <月初> --end <月末> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看高蛋白榜（本月）」。\n\n我想看本月(自然月)蛋白最高的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看本月高蛋白食物 TOP10', 'data_fields': ["rank", "food_name", "protein"],
            'depends_on_external': False, 'order': 18},
    {
            'category': '饮食',     'wake_word': '看高蛋白榜（自定义）',     'desc': '看高蛋白榜（自定义）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category high_protein --top-n 10 --start <开始> --end <结束> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看高蛋白榜（自定义）」。\n\n我想看自定义日期区间蛋白最高的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_high_protein_custom', 'name': '看高蛋白榜（自定义）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category high_protein --top-n 10 --start <开始> --end <结束> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看高蛋白榜（自定义）」。\n\n我想看自定义日期区间蛋白最高的食物 TOP 10。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____',
            'user_intent': '看自定义区间高蛋白食物 TOP10', 'data_fields': ["rank", "food_name", "protein", "start", "end"],
            'depends_on_external': False, 'order': 19},
    {
            'category': '饮食',     'wake_word': '饮食复盘（本周）',     'desc': '饮食复盘（本周）',
            'main_prompt': {
        'cli': 'python scripts/render_diet_review.py --type week --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「饮食复盘（本周）」。\n\n我想看本周饮食复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_review_week', 'name': '饮食复盘（本周）', 'subfunction': '饮食复盘', 'output_type': 'result',
            'html_template': 'templates/diet_review.html', 'data_source': 'python scripts/render_diet_review.py --type week --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「饮食复盘（本周）」。\n\n我想看本周饮食复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看本周饮食复盘小结', 'data_fields': ["total_cal", "avg_cal", "total_protein", "avg_protein", "top5", "trend"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '饮食',     'wake_word': '饮食复盘（本月）',     'desc': '饮食复盘（本月）',
            'main_prompt': {
        'cli': 'python scripts/render_diet_review.py --type month --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「饮食复盘（本月）」。\n\n我想看本月饮食复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_review_month', 'name': '饮食复盘（本月）', 'subfunction': '饮食复盘', 'output_type': 'result',
            'html_template': 'templates/diet_review.html', 'data_source': 'python scripts/render_diet_review.py --type month --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「饮食复盘（本月）」。\n\n我想看本月饮食复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看本月饮食复盘小结', 'data_fields': ["total_cal", "avg_cal", "total_protein", "avg_protein", "top5", "trend"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '饮食',     'wake_word': '饮食复盘（最近 90 天）',     'desc': '饮食复盘（最近 90 天）',
            'main_prompt': {
        'cli': 'python scripts/render_diet_review.py --type quarter --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「饮食复盘（最近 90 天）」。\n\n我想看最近 90 天饮食复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_review_90d', 'name': '饮食复盘（最近 90 天）', 'subfunction': '饮食复盘', 'output_type': 'result',
            'html_template': 'templates/diet_review.html', 'data_source': 'python scripts/render_diet_review.py --type quarter --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「饮食复盘（最近 90 天）」。\n\n我想看最近 90 天饮食复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 90 天饮食复盘小结', 'data_fields': ["total_cal", "avg_cal", "total_protein", "avg_protein", "top5", "trend"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '饮食',     'wake_word': '饮食复盘（今年）',     'desc': '饮食复盘（今年）',
            'main_prompt': {
        'cli': 'python scripts/render_diet_review.py --type year --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「饮食复盘（今年）」。\n\n我想看今年饮食复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_review_year', 'name': '饮食复盘（今年）', 'subfunction': '饮食复盘', 'output_type': 'result',
            'html_template': 'templates/diet_review.html', 'data_source': 'python scripts/render_diet_review.py --type year --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「饮食复盘（今年）」。\n\n我想看今年饮食复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看今年饮食复盘小结', 'data_fields': ["total_cal", "avg_cal", "total_protein", "avg_protein", "top5", "trend"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '饮食',     'wake_word': '饮食复盘（自定义时间）',     'desc': '饮食复盘（自定义时间）',
            'main_prompt': {
        'cli': 'python scripts/render_diet_review.py --type range --start <开始> --end <结束> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「饮食复盘（自定义时间）」。\n\n我想看自定义日期区间的饮食复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_review_range', 'name': '饮食复盘（自定义时间）', 'subfunction': '饮食复盘', 'output_type': 'result',
            'html_template': 'templates/diet_review.html', 'data_source': 'python scripts/render_diet_review.py --type range --start <开始> --end <结束> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「饮食复盘（自定义时间）」。\n\n我想看自定义日期区间的饮食复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____',
            'user_intent': '看自定义区间的饮食复盘小结', 'data_fields': ["total_cal", "avg_cal", "total_protein", "avg_protein", "top5", "trend", "start", "end"],
            'depends_on_external': False, 'order': 4},
    {
            'category': '饮食',     'wake_word': '看早餐（最近 7 天）',     'desc': '看早餐（最近 7 天）',
            'main_prompt': {
        'cli': 'python scripts/render_meal_distribution.py --meal breakfast --days 7 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看早餐（最近 7 天）」。\n\n我想看最近 7 天早餐的饮食。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'meal_dist_breakfast', 'name': '看早餐（最近 7 天）', 'subfunction': '餐别分布', 'output_type': 'result',
            'html_template': 'templates/meal_distribution.html', 'data_source': 'python scripts/render_meal_distribution.py --meal breakfast --days 7 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看早餐（最近 7 天）」。\n\n我想看最近 7 天早餐的饮食。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 7 天早餐饮食明细', 'data_fields': ["date", "food_name", "calories", "avg_cal", "meal"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '饮食',     'wake_word': '看午餐（最近 7 天）',     'desc': '看午餐（最近 7 天）',
            'main_prompt': {
        'cli': 'python scripts/render_meal_distribution.py --meal breakfast --days 7 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看午餐（最近 7 天）」。\n\n我想看最近 7 天午餐的饮食。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'meal_dist_lunch', 'name': '看午餐（最近 7 天）', 'subfunction': '餐别分布', 'output_type': 'result',
            'html_template': 'templates/meal_distribution.html', 'data_source': 'python scripts/render_meal_distribution.py --meal lunch --days 7 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看午餐（最近 7 天）」。\n\n我想看最近 7 天午餐的饮食。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 7 天午餐饮食明细', 'data_fields': ["date", "food_name", "calories", "avg_cal", "meal"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '饮食',     'wake_word': '看晚餐（最近 7 天）',     'desc': '看晚餐（最近 7 天）',
            'main_prompt': {
        'cli': 'python scripts/render_meal_distribution.py --meal lunch --days 7 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看晚餐（最近 7 天）」。\n\n我想看最近 7 天晚餐的饮食。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'meal_dist_dinner', 'name': '看晚餐（最近 7 天）', 'subfunction': '餐别分布', 'output_type': 'result',
            'html_template': 'templates/meal_distribution.html', 'data_source': 'python scripts/render_meal_distribution.py --meal dinner --days 7 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看晚餐（最近 7 天）」。\n\n我想看最近 7 天晚餐的饮食。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 7 天晚餐饮食明细', 'data_fields': ["date", "food_name", "calories", "avg_cal", "meal"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '饮食',     'wake_word': '看加餐（最近 7 天）',     'desc': '看加餐（最近 7 天）',
            'main_prompt': {
        'cli': 'python scripts/render_meal_distribution.py --meal dinner --days 7 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看加餐（最近 7 天）」。\n\n我想看最近 7 天加餐(下午茶+夜宵)的饮食。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'meal_dist_snack', 'name': '看加餐（最近 7 天）', 'subfunction': '餐别分布', 'output_type': 'result',
            'html_template': 'templates/meal_distribution.html', 'data_source': 'python scripts/render_meal_distribution.py --meal snack --days 7 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看加餐（最近 7 天）」。\n\n我想看最近 7 天加餐(下午茶+夜宵)的饮食。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 7 天加餐饮食明细', 'data_fields': ["date", "food_name", "calories", "avg_cal", "meal"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '饮食',     'wake_word': '看全部餐别分布（最近 7 天）',     'desc': '看全部餐别分布（最近 7 天）',
            'main_prompt': {
        'cli': 'python scripts/render_meal_distribution.py --meal snack --days 7 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看全部餐别分布（最近 7 天）」。\n\n我想看最近 7 天各餐别(早餐/午餐/晚餐/加餐)的分布对比。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'meal_dist_all', 'name': '看全部餐别分布（最近 7 天）', 'subfunction': '餐别分布', 'output_type': 'result',
            'html_template': 'templates/meal_distribution.html', 'data_source': 'python scripts/render_meal_distribution.py --meal all --days 7 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看全部餐别分布（最近 7 天）」。\n\n我想看最近 7 天各餐别(早餐/午餐/晚餐/加餐)的分布对比。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 7 天全部餐别分布对比', 'data_fields': ["meal", "count", "calories", "pct"],
            'depends_on_external': False, 'order': 4},

    {
            'category': '体重',     'wake_word': '记体重',     'desc': '记录今天的体重',
            'main_prompt': {
        'cli': 'python scripts/render_meal_distribution.py --meal all --days 7 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「记体重」。\n\n我刚称了体重,帮我记录今天的体重。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n体重(kg):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_log', 'name': '记体重', 'subfunction': '量体重', 'output_type': 'receipt',
            'html_template': 'templates/weight_log_receipt.html', 'data_source': 'python scripts/render_weight_receipt.py --live --kg <kg> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「记体重」。\n\n我刚称了体重,帮我记录今天的体重。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n体重(kg):____',
            'user_intent': '记录今天的体重', 'data_fields': ['weight_kg', 'bmi', 'delta_last', 'goal_diff', 'date', 'time'],
            'depends_on_external': False, 'order': 0
    },
    {
            'category': '体重',     'wake_word': '记体重（含备注）',     'desc': '记录今天的体重并带备注',
            'main_prompt': {
        'cli': 'python scripts/render_weight_receipt.py --live --kg <kg> --note <备注> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「记体重（含备注）」。\n\n我刚称了体重,记录今天的体重并带上备注(如 晨起空腹/运动后/睡前)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n体重(kg):____\n备注:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_log_note', 'name': '记体重（含备注）', 'subfunction': '量体重', 'output_type': 'receipt',
            'html_template': 'templates/weight_log_receipt.html', 'data_source': 'python scripts/render_weight_receipt.py --live --kg <kg> --note <备注> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「记体重（含备注）」。\n\n我刚称了体重,记录今天的体重并带上备注(如 晨起空腹/运动后/睡前)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n体重(kg):____\n备注:____',
            'user_intent': '记录今天的体重并带备注', 'data_fields': ['weight_kg', 'bmi', 'note', 'note_tag', 'goal_diff', 'date', 'time'],
            'depends_on_external': False, 'order': 1
    },
    {
            'category': '体重',     'wake_word': '补录体重',     'desc': '补录过去某天的体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_receipt.py --live --kg <kg> --date <YYYY-MM-DD> --chain "1.解析→2.查冲突→3.写库→4.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「补录体重」。\n\n我要补录过去某天的体重(不是今天)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n体重(kg):____\n日期(YYYY-MM-DD):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_backfill', 'name': '补录体重', 'subfunction': '量体重', 'output_type': 'receipt',
            'html_template': 'templates/weight_log_receipt.html', 'data_source': 'python scripts/render_weight_receipt.py --live --kg <kg> --date <YYYY-MM-DD> --chain "1.解析→2.查冲突→3.写库→4.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「补录体重」。\n\n我要补录过去某天的体重(不是今天)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n体重(kg):____\n日期(YYYY-MM-DD):____',
            'user_intent': '补录过去某天的体重', 'data_fields': ['weight_kg', 'bmi', 'date', 'days_ago', 'backfill_flag', 'conflict'],
            'depends_on_external': False, 'order': 2
    },
    {
            'category': '体重',     'wake_word': '批量补录体重',     'desc': '一次补录多天体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_receipt.py --live-batch --input <jsonl> --chain "1.解析→2.查冲突→3.批量写库→4.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「批量补录体重」。\n\n我要一次补录多天的体重。我会给你 日期+体重 的列表(每行一条),也可能只说连续天数加起始体重让你帮我生成。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n多天体重(每行一条: 日期 体重):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_backfill_batch', 'name': '批量补录体重', 'subfunction': '量体重', 'output_type': 'receipt',
            'html_template': 'templates/weight_batch_receipt.html', 'data_source': 'python scripts/render_weight_receipt.py --live-batch --input <jsonl> --chain "1.解析→2.查冲突→3.批量写库→4.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「批量补录体重」。\n\n我要一次补录多天的体重。我会给你 日期+体重 的列表(每行一条),也可能只说连续天数加起始体重让你帮我生成。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n多天体重(每行一条: 日期 体重):____',
            'user_intent': '一次补录多天体重', 'data_fields': ['wrote', 'skipped', 'failed', 'fail_details', 'items'],
            'depends_on_external': False, 'order': 3
    },
    {
            'category': '体重',     'wake_word': '看今日体重',     'desc': '看今天的体重数据',
            'main_prompt': {
        'cli': 'python scripts/render_weight_dashboard.py --view today --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看今日体重」。\n\n我想看今天的体重数据。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_today', 'name': '看今日体重', 'subfunction': '量体重', 'output_type': 'result',
            'html_template': 'templates/weight_dashboard.html', 'data_source': 'python scripts/render_weight_dashboard.py --view today --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看今日体重」。\n\n我想看今天的体重数据。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看今天的体重数据', 'data_fields': ['weight_kg', 'delta_last', 'summary', 'date'],
            'depends_on_external': False, 'order': 4
    },
    {
            'category': '体重',     'wake_word': '改体重记录',     'desc': '修改某条体重记录',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-weight-update --id <ID> --weight <kg> --note <备注> --chain "1.定位→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「改体重记录」。\n\n我要改某条体重记录(体重值或备注)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n要改的记录(最近一条/日期/编号):____\n新体重(kg):____\n新备注:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_update', 'name': '改体重记录', 'subfunction': '改体重记录', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-weight-update --id <ID> --weight <kg> --note <备注> --chain "1.定位→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改体重记录」。\n\n我要改某条体重记录(体重值或备注)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n要改的记录(最近一条/日期/编号):____\n新体重(kg):____\n新备注:____',
            'user_intent': '修改某条体重记录', 'data_fields': ['id', 'weight_kg', 'note', 'old_record', 'new_record', 'bmi'],
            'depends_on_external': False, 'order': 0
    },
    {
            'category': '体重',     'wake_word': '改某日体重',     'desc': '按日期修改某天的体重记录',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-weight-update --date <YYYY-MM-DD> --weight <kg> [--note <备注>] --chain "1.定位→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「改某日体重」。\n\n我要按日期改某天的体重记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n日期(YYYY-MM-DD):____\n新体重(kg):____\n新备注:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_update_by_date', 'name': '改某日体重', 'subfunction': '改体重记录', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-weight-update --date <YYYY-MM-DD> --weight <kg> [--note <备注>] --chain "1.定位→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改某日体重」。\n\n我要按日期改某天的体重记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n日期(YYYY-MM-DD):____\n新体重(kg):____\n新备注:____',
            'user_intent': '按日期修改某天的体重记录', 'data_fields': ['date', 'hit_count', 'old_record', 'new_record', 'weight_kg', 'note'],
            'depends_on_external': False, 'order': 1
    },
    {
            'category': '体重',     'wake_word': '删体重记录',     'desc': '删除一条体重记录',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-weight-delete --id <ID> --chain "1.定位→2.快照→3.删除→4.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「删体重记录」。\n\n我要删一条体重记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n要删的记录(最近一条/日期/编号):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_delete', 'name': '删体重记录', 'subfunction': '改体重记录', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-weight-delete --id <ID> --chain "1.定位→2.快照→3.删除→4.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「删体重记录」。\n\n我要删一条体重记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n要删的记录(最近一条/日期/编号):____',
            'user_intent': '删除一条体重记录', 'data_fields': ['id', 'snapshot', 'date', 'weight_kg', 'confirm'],
            'depends_on_external': False, 'order': 2
    },
    {
            'category': '体重',     'wake_word': '删某日体重',     'desc': '删除某一天的体重记录',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-weight-delete --date <YYYY-MM-DD> --chain "1.定位→2.快照→3.删除→4.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「删某日体重」。\n\n我要删某一天的全部体重记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n日期(YYYY-MM-DD):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_delete_by_date', 'name': '删某日体重', 'subfunction': '改体重记录', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-weight-delete --date <YYYY-MM-DD> --chain "1.定位→2.快照→3.删除→4.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「删某日体重」。\n\n我要删某一天的全部体重记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n日期(YYYY-MM-DD):____',
            'user_intent': '删除某一天的体重记录', 'data_fields': ['date', 'deleted_count', 'snapshot', 'confirm'],
            'depends_on_external': False, 'order': 3
    },
    {
            'category': '体重',     'wake_word': '批量删体重',     'desc': '按日期范围批量删除体重记录',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-weight-delete --start <S> --end <E> --chain "1.定位→2.快照→3.删除→4.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「批量删体重」。\n\n我要按日期范围批量删除体重记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n起止日期(YYYY-MM-DD):____ ~ ____'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_delete_batch', 'name': '批量删体重', 'subfunction': '改体重记录', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-weight-delete --start <S> --end <E> --chain "1.定位→2.快照→3.删除→4.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「批量删体重」。\n\n我要按日期范围批量删除体重记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n起止日期(YYYY-MM-DD):____ ~ ____',
            'user_intent': '按日期范围批量删除体重记录', 'data_fields': ['start', 'end', 'deleted_count', 'snapshot', 'confirm'],
            'depends_on_external': False, 'order': 4
    },
    {
            'category': '体重',     'wake_word': '看本周体重',     'desc': '看本周自然周的体重明细',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode history --week current', 'text': '请你加载技能 卡路里,执行唤醒词「看本周体重」。\n\n我想看本周(自然周,周一开始)的体重明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_detail_week', 'name': '看本周体重', 'subfunction': '看体重明细', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode history --week current', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看本周体重」。\n\n我想看本周(自然周,周一开始)的体重明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看本周自然周的体重明细', 'data_fields': ['week', 'items', 'avg', 'net_change', 'summary'],
            'depends_on_external': False, 'order': 0
    },
    {
            'category': '体重',     'wake_word': '看上周体重',     'desc': '看上周体重明细并与本周对比',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode history --week last', 'text': '请你加载技能 卡路里,执行唤醒词「看上周体重」。\n\n我想看上周(自然周)的体重明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_detail_last_week', 'name': '看上周体重', 'subfunction': '看体重明细', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode history --week last', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看上周体重」。\n\n我想看上周(自然周)的体重明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看上周体重明细并与本周对比', 'data_fields': ['week', 'items', 'avg', 'net_change', 'vs_this_week'],
            'depends_on_external': False, 'order': 1
    },
    {
            'category': '体重',     'wake_word': '看本月体重',     'desc': '看本月自然月的体重明细',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode history --month current', 'text': '请你加载技能 卡路里,执行唤醒词「看本月体重」。\n\n我想看本月(自然月)的体重明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_detail_month', 'name': '看本月体重', 'subfunction': '看体重明细', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode history --month current', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看本月体重」。\n\n我想看本月(自然月)的体重明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看本月自然月的体重明细', 'data_fields': ['month', 'items', 'avg', 'net_change', 'summary'],
            'depends_on_external': False, 'order': 2
    },
    {
            'category': '体重',     'wake_word': '看上月体重',     'desc': '看上个月体重明细并与本月对比',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode history --month last', 'text': '请你加载技能 卡路里,执行唤醒词「看上月体重」。\n\n我想看上个月(自然月)的体重明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_detail_last_month', 'name': '看上月体重', 'subfunction': '看体重明细', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode history --month last', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看上月体重」。\n\n我想看上个月(自然月)的体重明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看上个月体重明细并与本月对比', 'data_fields': ['month', 'items', 'avg', 'net_change', 'vs_this_month'],
            'depends_on_external': False, 'order': 3
    },
    {
            'category': '体重',     'wake_word': '看最近 7 天体重',     'desc': '看最近 7 天的体重明细',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode history --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「看最近 7 天体重」。\n\n我想看最近 7 天(滚动)的体重明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_detail_7d', 'name': '看最近 7 天体重', 'subfunction': '看体重明细', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode history --days 7', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看最近 7 天体重」。\n\n我想看最近 7 天(滚动)的体重明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 7 天的体重明细', 'data_fields': ['days', 'items', 'avg', 'net_change', 'summary'],
            'depends_on_external': False, 'order': 4
    },
    {
            'category': '体重',     'wake_word': '看最近 90 天体重',     'desc': '看最近 90 天的体重明细(每周一行)',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode history --days 90', 'text': '请你加载技能 卡路里,执行唤醒词「看最近 90 天体重」。\n\n我想看最近 90 天的体重明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_detail_90d', 'name': '看最近 90 天体重', 'subfunction': '看体重明细', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode history --days 90', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看最近 90 天体重」。\n\n我想看最近 90 天的体重明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 90 天的体重明细(每周一行)', 'data_fields': ['days', 'items', 'avg', 'net_change', 'summary'],
            'depends_on_external': False, 'order': 5
    },
    {
            'category': '体重',     'wake_word': '看某段时间体重',     'desc': '看自定义时间段的体重明细',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode history --start <S> --end <E>', 'text': '请你加载技能 卡路里,执行唤醒词「看某段时间体重」。\n\n我想看某段时间(自定义起止日期)的体重明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n起止日期(YYYY-MM-DD):____ ~ ____'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_detail_range', 'name': '看某段时间体重', 'subfunction': '看体重明细', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode history --start <S> --end <E>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看某段时间体重」。\n\n我想看某段时间(自定义起止日期)的体重明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n起止日期(YYYY-MM-DD):____ ~ ____',
            'user_intent': '看自定义时间段的体重明细', 'data_fields': ['start', 'end', 'items', 'avg', 'net_change', 'summary'],
            'depends_on_external': False, 'order': 6
    },
    {
            'category': '体重',     'wake_word': '看体重曲线',     'desc': '看默认 30 天的体重曲线',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode trend --days 30', 'text': '请你加载技能 卡路里,执行唤醒词「看体重曲线」。\n\n我想看体重曲线(默认最近 30 天)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_curve', 'name': '看体重曲线', 'subfunction': '看体重曲线', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode trend --days 30', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重曲线」。\n\n我想看体重曲线(默认最近 30 天)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看默认 30 天的体重曲线', 'data_fields': ['days', 'items', 'current', 'delta', 'daily_rate', 'trend'],
            'depends_on_external': False, 'order': 0
    },
    {
            'category': '体重',     'wake_word': '看体重曲线（带目标）',     'desc': '看体重曲线并叠加目标线',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode trend --days 30 --show-target', 'text': '请你加载技能 卡路里,执行唤醒词「看体重曲线（带目标）」。\n\n我想看最近 30 天的体重曲线,并把我的目标体重画成目标线。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_curve_target', 'name': '看体重曲线（带目标）', 'subfunction': '看体重曲线', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode trend --days 30 --show-target', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重曲线（带目标）」。\n\n我想看最近 30 天的体重曲线,并把我的目标体重画成目标线。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重曲线并叠加目标线', 'data_fields': ['days', 'items', 'target', 'goal_diff', 'current', 'delta', 'daily_rate'],
            'depends_on_external': False, 'order': 1
    },
    {
            'category': '体重',     'wake_word': '看体重曲线（带里程碑）',     'desc': '看体重曲线并标注里程碑点',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode trend --days 30 --show-milestones', 'text': '请你加载技能 卡路里,执行唤醒词「看体重曲线（带里程碑）」。\n\n我想看最近 30 天的体重曲线,并在上面标出里程碑点(如减重 5kg/10kg 达成的那天)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_curve_milestone', 'name': '看体重曲线（带里程碑）', 'subfunction': '看体重曲线', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode trend --days 30 --show-milestones', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重曲线（带里程碑）」。\n\n我想看最近 30 天的体重曲线,并在上面标出里程碑点(如减重 5kg/10kg 达成的那天)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重曲线并标注里程碑点', 'data_fields': ['days', 'items', 'milestones', 'current', 'delta', 'daily_rate'],
            'depends_on_external': False, 'order': 2
    },
    {
            'category': '体重',     'wake_word': '看体重曲线（带异常点）',     'desc': '看体重曲线并标注异常点',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode trend --days 30 --show-anomalies', 'text': '请你加载技能 卡路里,执行唤醒词「看体重曲线（带异常点）」。\n\n我想看最近 30 天的体重曲线,并标出异常点(与正常波动偏差较大的记录)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_curve_anomaly', 'name': '看体重曲线（带异常点）', 'subfunction': '看体重曲线', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode trend --days 30 --show-anomalies', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重曲线（带异常点）」。\n\n我想看最近 30 天的体重曲线,并标出异常点(与正常波动偏差较大的记录)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重曲线并标注异常点', 'data_fields': ['days', 'items', 'anomalies', 'current', 'delta', 'daily_rate'],
            'depends_on_external': False, 'order': 3
    },
    {
            'category': '体重',     'wake_word': '看本月体重曲线',     'desc': '看本月自然月的体重曲线',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode trend --month current', 'text': '请你加载技能 卡路里,执行唤醒词「看本月体重曲线」。\n\n我想看本月(自然月)的体重曲线。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_curve_month', 'name': '看本月体重曲线', 'subfunction': '看体重曲线', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode trend --month current', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看本月体重曲线」。\n\n我想看本月(自然月)的体重曲线。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看本月自然月的体重曲线', 'data_fields': ['month', 'items', 'current', 'delta', 'daily_rate', 'trend'],
            'depends_on_external': False, 'order': 4
    },
    {
            'category': '体重',     'wake_word': '看上月体重曲线',     'desc': '看上个月自然月的体重曲线',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode trend --month last', 'text': '请你加载技能 卡路里,执行唤醒词「看上月体重曲线」。\n\n我想看上个月(自然月)的体重曲线。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_curve_last_month', 'name': '看上月体重曲线', 'subfunction': '看体重曲线', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode trend --month last', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看上月体重曲线」。\n\n我想看上个月(自然月)的体重曲线。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看上个月自然月的体重曲线', 'data_fields': ['month', 'items', 'current', 'delta', 'daily_rate', 'trend'],
            'depends_on_external': False, 'order': 5
    },
    {
            'category': '体重',     'wake_word': '看最近 90 天体重曲线',     'desc': '看最近 90 天的体重曲线',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode trend --days 90', 'text': '请你加载技能 卡路里,执行唤醒词「看最近 90 天体重曲线」。\n\n我想看最近 90 天的体重曲线(每 3 天降采样显示)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_curve_90d', 'name': '看最近 90 天体重曲线', 'subfunction': '看体重曲线', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode trend --days 90', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看最近 90 天体重曲线」。\n\n我想看最近 90 天的体重曲线(每 3 天降采样显示)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 90 天的体重曲线', 'data_fields': ['days', 'items', 'current', 'delta', 'daily_rate', 'trend'],
            'depends_on_external': False, 'order': 6
    },
    {
            'category': '体重',     'wake_word': '看最近 180 天体重曲线',     'desc': '看最近 180 天的体重曲线',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode trend --days 180', 'text': '请你加载技能 卡路里,执行唤醒词「看最近 180 天体重曲线」。\n\n我想看最近 180 天的体重曲线(每周降采样显示)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_curve_180d', 'name': '看最近 180 天体重曲线', 'subfunction': '看体重曲线', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode trend --days 180', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看最近 180 天体重曲线」。\n\n我想看最近 180 天的体重曲线(每周降采样显示)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 180 天的体重曲线', 'data_fields': ['days', 'items', 'current', 'delta', 'daily_rate', 'trend'],
            'depends_on_external': False, 'order': 7
    },
    {
            'category': '体重',     'wake_word': '看最近 365 天体重曲线',     'desc': '看最近 365 天的体重曲线',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode trend --days 365', 'text': '请你加载技能 卡路里,执行唤醒词「看最近 365 天体重曲线」。\n\n我想看最近 365 天的体重曲线(每月降采样显示)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_curve_365d', 'name': '看最近 365 天体重曲线', 'subfunction': '看体重曲线', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode trend --days 365', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看最近 365 天体重曲线」。\n\n我想看最近 365 天的体重曲线(每月降采样显示)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 365 天的体重曲线', 'data_fields': ['days', 'items', 'current', 'delta', 'daily_rate', 'trend'],
            'depends_on_external': False, 'order': 8
    },
    {
            'category': '体重',     'wake_word': '看某段时间体重曲线',     'desc': '看自定义时间段的体重曲线',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode trend --start <S> --end <E>', 'text': '请你加载技能 卡路里,执行唤醒词「看某段时间体重曲线」。\n\n我想看某段时间(自定义起止日期)的体重曲线,跨度大时自动降采样。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n起止日期(YYYY-MM-DD):____ ~ ____'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_curve_range', 'name': '看某段时间体重曲线', 'subfunction': '看体重曲线', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode trend --start <S> --end <E>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看某段时间体重曲线」。\n\n我想看某段时间(自定义起止日期)的体重曲线,跨度大时自动降采样。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n起止日期(YYYY-MM-DD):____ ~ ____',
            'user_intent': '看自定义时间段的体重曲线', 'data_fields': ['start', 'end', 'items', 'current', 'delta', 'daily_rate', 'trend'],
            'depends_on_external': False, 'order': 9
    },
    {
            'category': '体重',     'wake_word': '看体重稳不稳（增强版）',     'desc': '看最近 30 天体重波动是否稳定',
            'main_prompt': {
        'cli': 'python scripts/render_weight_volatility_v2.py', 'text': '请你加载技能 卡路里,执行唤醒词「看体重稳不稳（增强版）」。\n\n我想看最近 30 天我的体重稳不稳。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_vol', 'name': '看体重稳不稳（增强版）', 'subfunction': '看体重稳不稳', 'output_type': 'result',
            'html_template': 'templates/weight_volatility_v2.html', 'data_source': 'python scripts/render_weight_volatility_v2.py', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重稳不稳（增强版）」。\n\n我想看最近 30 天我的体重稳不稳。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 30 天体重波动是否稳定', 'data_fields': ['std', 'avg_daily_delta', 'anomaly_count', 'points', 'anomalies', 'baseline'],
            'depends_on_external': False, 'order': 0
    },
    {
            'category': '体重',     'wake_word': '看本月波动',     'desc': '看本月自然月的体重波动',
            'main_prompt': {
        'cli': 'python scripts/render_weight_volatility_v2.py --start <月初> --end <月末>', 'text': '请你加载技能 卡路里,执行唤醒词「看本月波动」。\n\n我想看本月(自然月)体重波动。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_vol_month', 'name': '看本月波动', 'subfunction': '看体重稳不稳', 'output_type': 'result',
            'html_template': 'templates/weight_volatility_v2.html', 'data_source': 'python scripts/render_weight_volatility_v2.py --start <月初> --end <月末>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看本月波动」。\n\n我想看本月(自然月)体重波动。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看本月自然月的体重波动', 'data_fields': ['month', 'std', 'avg_daily_delta', 'anomaly_count', 'points', 'anomalies'],
            'depends_on_external': False, 'order': 1
    },
    {
            'category': '体重',     'wake_word': '看最近 90 天波动',     'desc': '看最近 90 天的体重波动',
            'main_prompt': {
        'cli': 'python scripts/render_weight_volatility_v2.py --days 90', 'text': '请你加载技能 卡路里,执行唤醒词「看最近 90 天波动」。\n\n我想看最近 90 天的体重波动(降采样显示)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_vol_90d', 'name': '看最近 90 天波动', 'subfunction': '看体重稳不稳', 'output_type': 'result',
            'html_template': 'templates/weight_volatility_v2.html', 'data_source': 'python scripts/render_weight_volatility_v2.py --days 90', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看最近 90 天波动」。\n\n我想看最近 90 天的体重波动(降采样显示)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 90 天的体重波动', 'data_fields': ['days', 'std', 'avg_daily_delta', 'anomaly_count', 'points', 'anomalies'],
            'depends_on_external': False, 'order': 2
    },
    {
            'category': '体重',     'wake_word': '看最近 180 天波动',     'desc': '看最近 180 天的体重波动',
            'main_prompt': {
        'cli': 'python scripts/render_weight_volatility_v2.py --days 180', 'text': '请你加载技能 卡路里,执行唤醒词「看最近 180 天波动」。\n\n我想看最近 180 天的体重波动(降采样显示)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_vol_180d', 'name': '看最近 180 天波动', 'subfunction': '看体重稳不稳', 'output_type': 'result',
            'html_template': 'templates/weight_volatility_v2.html', 'data_source': 'python scripts/render_weight_volatility_v2.py --days 180', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看最近 180 天波动」。\n\n我想看最近 180 天的体重波动(降采样显示)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 180 天的体重波动', 'data_fields': ['days', 'std', 'avg_daily_delta', 'anomaly_count', 'points', 'anomalies'],
            'depends_on_external': False, 'order': 3
    },
    {
            'category': '体重',     'wake_word': '看波动异常点',     'desc': '只看体重波动中的异常点',
            'main_prompt': {
        'cli': 'python scripts/render_weight_volatility_v2.py --view anomalies-only', 'text': '请你加载技能 卡路里,执行唤醒词「看波动异常点」。\n\n我想只看体重波动中的异常点。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_vol_anomalies', 'name': '看波动异常点', 'subfunction': '看体重稳不稳', 'output_type': 'result',
            'html_template': 'templates/weight_volatility_v2.html', 'data_source': 'python scripts/render_weight_volatility_v2.py --view anomalies-only', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看波动异常点」。\n\n我想只看体重波动中的异常点。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '只看体重波动中的异常点', 'data_fields': ['anomalies', 'reasons', 'summary'],
            'depends_on_external': False, 'order': 4
    },
    {
            'category': '体重',     'wake_word': '看「有备注」的体重记录',     'desc': '看带备注的体重记录及备注分类',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode notes --days 30', 'text': '请你加载技能 卡路里,执行唤醒词「看「有备注」的体重记录」。\n\n我想看所有带备注的体重记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_notes', 'name': '看「有备注」的体重记录', 'subfunction': '看体重备注', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode notes --days 30', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看「有备注」的体重记录」。\n\n我想看所有带备注的体重记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看带备注的体重记录及备注分类', 'data_fields': ['items', 'note_tags', 'tag_distribution', 'summary'],
            'depends_on_external': False, 'order': 0
    },
    {
            'category': '体重',     'wake_word': '对比体重：最近 30 天 vs 之前 30 天',     'desc': '对比最近 30 天与之前 30 天的体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario a1 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：最近 30 天 vs 之前 30 天」。\n\n我想对比最近 30 天和之前 30 天两段体重。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_30d', 'name': '对比体重：最近 30 天 vs 之前 30 天', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario a1 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：最近 30 天 vs 之前 30 天」。\n\n我想对比最近 30 天和之前 30 天两段体重。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '对比最近 30 天与之前 30 天的体重', 'data_fields': ['seg1', 'seg2', 'avg', 'delta_kg', 'rate_diff', 'speed_judge', 'volatility'],
            'depends_on_external': False, 'order': 0
    },
    {
            'category': '体重',     'wake_word': '对比体重：自定义两段时间',     'desc': '自定义两段时间对比体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario a2 --start-a <S1> --end-a <E1> --start-b <S2> --end-b <E2> --chain "1.识别→2.读DB→3.对比→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：自定义两段时间」。\n\n我想自定义两段日期对比体重。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n第一段起止(YYYY-MM-DD):____ ~ ____\n第二段起止(YYYY-MM-DD):____ ~ ____'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_custom', 'name': '对比体重：自定义两段时间', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario a2 --start-a <S1> --end-a <E1> --start-b <S2> --end-b <E2> --chain "1.识别→2.读DB→3.对比→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：自定义两段时间」。\n\n我想自定义两段日期对比体重。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n第一段起止(YYYY-MM-DD):____ ~ ____\n第二段起止(YYYY-MM-DD):____ ~ ____',
            'user_intent': '自定义两段时间对比体重', 'data_fields': ['seg1', 'seg2', 'avg', 'delta_kg', 'rate_diff', 'speed_judge', 'volatility'],
            'depends_on_external': False, 'order': 1
    },
    {
            'category': '体重',     'wake_word': '对比体重：本周 vs 上周',     'desc': '对比本周与上周的体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario a3 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：本周 vs 上周」。\n\n我想对比本周和上周的体重(自然周对齐)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_week', 'name': '对比体重：本周 vs 上周', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario a3 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：本周 vs 上周」。\n\n我想对比本周和上周的体重(自然周对齐)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '对比本周与上周的体重', 'data_fields': ['seg1', 'seg2', 'sample_ok', 'avg', 'delta_kg', 'rate_diff', 'speed_judge'],
            'depends_on_external': False, 'order': 2
    },
    {
            'category': '体重',     'wake_word': '对比体重：本月 vs 上月',     'desc': '对比本月与上月的体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario a4 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：本月 vs 上月」。\n\n我想对比本月和上月的体重(自然月对齐)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_month', 'name': '对比体重：本月 vs 上月', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario a4 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：本月 vs 上月」。\n\n我想对比本月和上月的体重(自然月对齐)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '对比本月与上月的体重', 'data_fields': ['seg1', 'seg2', 'avg', 'delta_kg', 'rate_diff', 'speed_judge', 'volatility'],
            'depends_on_external': False, 'order': 3
    },
    {
            'category': '体重',     'wake_word': '对比体重：近 N 天 vs 上一个 N 天',     'desc': '对比近 N 天与之前同样 N 天的体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario a5 --n <N> --chain "1.识别→2.读DB→3.对比→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：近 N 天 vs 上一个 N 天」。\n\n我想对比最近 N 天和之前同样 N 天(滚动窗口)的体重,N 由我指定。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\nN(天数):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_ndays', 'name': '对比体重：近 N 天 vs 上一个 N 天', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario a5 --n <N> --chain "1.识别→2.读DB→3.对比→4.渲染"', 'prompt_template': "请你加载技能 卡路里,执行唤醒词「对比体重：近 N 天 vs 上一个 N 天」。\n\n我想对比最近 N 天和之前同样 N 天(滚动窗口)的体重,N 由我指定。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\nN(天数):____",
            'user_intent': '对比近 N 天与之前同样 N 天的体重', 'data_fields': ['n_days', 'seg1', 'seg2', 'avg', 'delta_kg', 'rate_diff', 'speed_judge'],
            'depends_on_external': False, 'order': 4
    },
    {
            'category': '体重',     'wake_word': '对比体重：今天 vs 一年前今天',     'desc': '对比今天与一年前同一天的体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario a6 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：今天 vs 一年前今天」。\n\n我想对比今天的体重和一年前同一天的体重。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_1y', 'name': '对比体重：今天 vs 一年前今天', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario a6 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：今天 vs 一年前今天」。\n\n我想对比今天的体重和一年前同一天的体重。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '对比今天与一年前同一天的体重', 'data_fields': ['current', 'year_ago', 'delta_kg', 'direction', 'tolerance_hit', 'period_avg'],
            'depends_on_external': False, 'order': 5
    },
    {
            'category': '体重',     'wake_word': '对比体重：今天 vs 半年前今天',     'desc': '对比今天与半年前同一天的体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario a7 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：今天 vs 半年前今天」。\n\n我想对比今天的体重和半年前同一天的体重。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_6m', 'name': '对比体重：今天 vs 半年前今天', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario a7 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'prompt_template': "请你加载技能 卡路里,执行唤醒词「对比体重：今天 vs 半年前今天」。\n\n我想对比今天的体重和半年前同一天的体重。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。",
            'user_intent': '对比今天与半年前同一天的体重', 'data_fields': ['current', 'past', 'delta_kg', 'direction', 'tolerance_hit', 'period_avg'],
            'depends_on_external': False, 'order': 6
    },
    {
            'category': '体重',     'wake_word': '对比体重：今天 vs 三月前今天',     'desc': '对比今天与三月前同一天的体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario a8 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：今天 vs 三月前今天」。\n\n我想对比今天的体重和三个月前同一天的体重。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_3m', 'name': '对比体重：今天 vs 三月前今天', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario a8 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：今天 vs 三月前今天」。\n\n我想对比今天的体重和三个月前同一天的体重。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '对比今天与三月前同一天的体重', 'data_fields': ['current', 'past', 'delta_kg', 'direction', 'tolerance_hit', 'period_avg'],
            'depends_on_external': False, 'order': 7
    },
    {
            'category': '体重',     'wake_word': '对比体重：当前 vs 目标体重',     'desc': '对比当前体重与目标体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario b1 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：当前 vs 目标体重」。\n\n我想对比当前体重和目标体重。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_target', 'name': '对比体重：当前 vs 目标体重', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario b1 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：当前 vs 目标体重」。\n\n我想对比当前体重和目标体重。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '对比当前体重与目标体重', 'data_fields': ['current', 'target', 'delta_kg', 'pct_done', 'eta', 'current_bmi', 'target_bmi', 'verdict'],
            'depends_on_external': False, 'order': 8
    },
    {
            'category': '体重',     'wake_word': '对比体重：当前 vs 平台期首日',     'desc': '对比当前体重与最近一次平台期首日',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario b8 --chain "1.识别→2.读DB→3.平台期识别→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：当前 vs 平台期首日」。\n\n请自动识别我最近一次平台期,并对比当前体重和平台期首日的体重。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_plateau', 'name': '对比体重：当前 vs 平台期首日', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario b8 --chain "1.识别→2.读DB→3.平台期识别→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：当前 vs 平台期首日」。\n\n请自动识别我最近一次平台期,并对比当前体重和平台期首日的体重。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '对比当前体重与最近一次平台期首日', 'data_fields': ['current', 'plateau_start', 'plateau_days', 'delta_after', 'plateau_count', 'avg_break_days'],
            'depends_on_external': False, 'order': 9
    },
    {
            'category': '体重',     'wake_word': '对比体重：当前 vs 历史最低',     'desc': '对比当前体重与历史最低',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario e1 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：当前 vs 历史最低」。\n\n请自动定位我历史最低的体重并和当前对比。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_min', 'name': '对比体重：当前 vs 历史最低', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario e1 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：当前 vs 历史最低」。\n\n请自动定位我历史最低的体重并和当前对比。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '对比当前体重与历史最低', 'data_fields': ['current', 'min_kg', 'min_date', 'delta_kg', 'days_since', 'summary'],
            'depends_on_external': False, 'order': 10
    },
    {
            'category': '体重',     'wake_word': '对比体重：当前 vs 历史最高',     'desc': '对比当前体重与历史最高',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario e2 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：当前 vs 历史最高」。\n\n请自动定位我历史最高的体重并和当前对比。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_max', 'name': '对比体重：当前 vs 历史最高', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario e2 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：当前 vs 历史最高」。\n\n请自动定位我历史最高的体重并和当前对比。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '对比当前体重与历史最高', 'data_fields': ['current', 'max_kg', 'max_date', 'delta_kg', 'rate', 'summary'],
            'depends_on_external': False, 'order': 11
    },
    {
            'category': '体重',     'wake_word': '对比体重：减重 5kg 那天 vs 今天',     'desc': '对比减重 5kg 达成日与今天的体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario e3 --delta 5 --chain "1.识别→2.读DB→3.反查里程碑→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：减重 5kg 那天 vs 今天」。\n\n请反查我减重 5kg 达成的那一天,和今天对比。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_5kg', 'name': '对比体重：减重 5kg 那天 vs 今天', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario e3 --delta 5 --chain "1.识别→2.读DB→3.反查里程碑→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：减重 5kg 那天 vs 今天」。\n\n请反查我减重 5kg 达成的那一天,和今天对比。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '对比减重 5kg 达成日与今天的体重', 'data_fields': ['current', 'milestone_kg', 'milestone_date', 'elapsed_days', 'rate', 'trajectory'],
            'depends_on_external': False, 'order': 12
    },
    {
            'category': '体重',     'wake_word': '对比体重：减重 10kg 那天 vs 今天',     'desc': '对比减重 10kg 达成日与今天的体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario e3 --delta 10 --chain "1.识别→2.读DB→3.反查里程碑→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：减重 10kg 那天 vs 今天」。\n\n请反查我减重 10kg 达成的那一天,和今天对比。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_10kg', 'name': '对比体重：减重 10kg 那天 vs 今天', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario e3 --delta 10 --chain "1.识别→2.读DB→3.反查里程碑→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：减重 10kg 那天 vs 今天」。\n\n请反查我减重 10kg 达成的那一天,和今天对比。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '对比减重 10kg 达成日与今天的体重', 'data_fields': ['current', 'milestone_kg', 'milestone_date', 'elapsed_days', 'rate', 'trajectory'],
            'depends_on_external': False, 'order': 13
    },
    {
            'category': '体重',     'wake_word': '对比体重：当前 vs 入夏最低',     'desc': '对比当前体重与入夏最低',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario e5 --chain "1.识别→2.读DB→3.季节定位→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：当前 vs 入夏最低」。\n\n请定位我今年夏天的体重最低点并和当前对比。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_summer', 'name': '对比体重：当前 vs 入夏最低', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario e5 --chain "1.识别→2.读DB→3.季节定位→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：当前 vs 入夏最低」。\n\n请定位我今年夏天的体重最低点并和当前对比。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '对比当前体重与入夏最低', 'data_fields': ['current', 'season_min_kg', 'season_min_date', 'delta_kg', 'days_since'],
            'depends_on_external': False, 'order': 14
    },
    {
            'category': '体重',     'wake_word': '对比体重：当前 vs 入冬最低',     'desc': '对比当前体重与入冬最低',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario e6 --chain "1.识别→2.读DB→3.季节定位→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：当前 vs 入冬最低」。\n\n请定位我最近一个冬天的体重最低点并和当前对比。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_winter', 'name': '对比体重：当前 vs 入冬最低', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario e6 --chain "1.识别→2.读DB→3.季节定位→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：当前 vs 入冬最低」。\n\n请定位我最近一个冬天的体重最低点并和当前对比。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '对比当前体重与入冬最低', 'data_fields': ['current', 'season_min_kg', 'season_min_date', 'delta_kg', 'days_since'],
            'depends_on_external': False, 'order': 15
    },
    {
            'category': '体重',     'wake_word': '对比体重：运动多 vs 运动少的两个月',     'desc': '对比运动最多与最少两个月的体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario c5 --chain "1.识别→2.读DB→3.选极端月→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：运动多 vs 运动少的两个月」。\n\n请自动选出我运动量最高和最低的两个月对比体重。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_exercise', 'name': '对比体重：运动多 vs 运动少的两个月', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario c5 --chain "1.识别→2.读DB→3.选极端月→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：运动多 vs 运动少的两个月」。\n\n请自动选出我运动量最高和最低的两个月对比体重。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '对比运动最多与最少两个月的体重', 'data_fields': ['high_month', 'low_month', 'avg', 'delta_kg', 'rate_diff', 'calories', 'sleep', 'exercise_total'],
            'depends_on_external': False, 'order': 16
    },
    {
            'category': '体重',     'wake_word': '对比体重：工作日 vs 周末',     'desc': '对比工作日与周末的体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario d4 --chain "1.识别→2.读DB→3.周内聚合→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：工作日 vs 周末」。\n\n请把最近一周的体重按 工作日(周一至周五)和 周末(周六周日)分组对比。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_weekend', 'name': '对比体重：工作日 vs 周末', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario d4 --chain "1.识别→2.读DB→3.周内聚合→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：工作日 vs 周末」。\n\n请把最近一周的体重按 工作日(周一至周五)和 周末(周六周日)分组对比。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '对比工作日与周末的体重', 'data_fields': ['weekday_avg', 'weekend_avg', 'delta_kg', 'weekday_vol', 'weekend_vol', 'agreement_rate'],
            'depends_on_external': False, 'order': 17
    },
    {
            'category': '体重',     'wake_word': '看体重总览',     'desc': '看体重综合总览',
            'main_prompt': {
        'cli': 'python scripts/render_weight_dashboard.py --view overview --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看体重总览」。\n\n我想看体重综合总览。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_overview', 'name': '看体重总览', 'subfunction': '体重复盘', 'output_type': 'result',
            'html_template': 'templates/weight_dashboard.html', 'data_source': 'python scripts/render_weight_dashboard.py --view overview --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重总览」。\n\n我想看体重综合总览。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重综合总览', 'data_fields': ['current', 'delta_7d', 'diff_min', 'diff_target', 'vol_level', 'trend_7d', 'summary'],
            'depends_on_external': False, 'order': 0
    },
    {
            'category': '体重',     'wake_word': '体重复盘（本周）',     'desc': '复盘本周的体重变化',
            'main_prompt': {
        'cli': 'python scripts/render_weight_review.py --type week --chain "1.识别→2.读DB→3.复盘→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「体重复盘（本周）」。\n\n我想看本周的体重复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_review_week', 'name': '体重复盘（本周）', 'subfunction': '体重复盘', 'output_type': 'result',
            'html_template': 'templates/weight_review.html', 'data_source': 'python scripts/render_weight_review.py --type week --chain "1.识别→2.读DB→3.复盘→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「体重复盘（本周）」。\n\n我想看本周的体重复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '复盘本周的体重变化', 'data_fields': ['delta_kg', 'avg', 'vs_last_period', 'trend', 'summary'],
            'depends_on_external': False, 'order': 1
    },
    {
            'category': '体重',     'wake_word': '体重复盘（本月）',     'desc': '复盘本月的体重变化',
            'main_prompt': {
        'cli': 'python scripts/render_weight_review.py --type month --chain "1.识别→2.读DB→3.复盘→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「体重复盘（本月）」。\n\n我想看本月的体重复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_review_month', 'name': '体重复盘（本月）', 'subfunction': '体重复盘', 'output_type': 'result',
            'html_template': 'templates/weight_review.html', 'data_source': 'python scripts/render_weight_review.py --type month --chain "1.识别→2.读DB→3.复盘→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「体重复盘（本月）」。\n\n我想看本月的体重复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '复盘本月的体重变化', 'data_fields': ['delta_kg', 'avg', 'vs_last_period', 'trend', 'summary'],
            'depends_on_external': False, 'order': 2
    },
    {
            'category': '体重',     'wake_word': '体重复盘（最近 90 天）',     'desc': '复盘最近 90 天的体重变化',
            'main_prompt': {
        'cli': 'python scripts/render_weight_review.py --type 90d --chain "1.识别→2.读DB→3.复盘→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「体重复盘（最近 90 天）」。\n\n我想看最近 90 天的体重复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_review_90d', 'name': '体重复盘（最近 90 天）', 'subfunction': '体重复盘', 'output_type': 'result',
            'html_template': 'templates/weight_review.html', 'data_source': 'python scripts/render_weight_review.py --type 90d --chain "1.识别→2.读DB→3.复盘→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「体重复盘（最近 90 天）」。\n\n我想看最近 90 天的体重复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '复盘最近 90 天的体重变化', 'data_fields': ['delta_kg', 'avg', 'vs_last_period', 'trend', 'summary'],
            'depends_on_external': False, 'order': 3
    },
    {
            'category': '体重',     'wake_word': '体重复盘（今年）',     'desc': '复盘今年的体重变化',
            'main_prompt': {
        'cli': 'python scripts/render_weight_review.py --type year --chain "1.识别→2.读DB→3.复盘→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「体重复盘（今年）」。\n\n我想看今年的体重复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_review_year', 'name': '体重复盘（今年）', 'subfunction': '体重复盘', 'output_type': 'result',
            'html_template': 'templates/weight_review.html', 'data_source': 'python scripts/render_weight_review.py --type year --chain "1.识别→2.读DB→3.复盘→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「体重复盘（今年）」。\n\n我想看今年的体重复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '复盘今年的体重变化', 'data_fields': ['delta_kg', 'avg', 'monthly_trend', 'summary'],
            'depends_on_external': False, 'order': 4
    },
    {
            'category': '体重',     'wake_word': '体重复盘（自定义时间）',     'desc': '复盘自定义时间段的体重变化',
            'main_prompt': {
        'cli': 'python scripts/render_weight_review.py --start <S> --end <E> --chain "1.识别→2.读DB→3.复盘→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「体重复盘（自定义时间）」。\n\n我想看某段时间的体重复盘(自定义起止日期)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n起止日期(YYYY-MM-DD):____ ~ ____'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_review_range', 'name': '体重复盘（自定义时间）', 'subfunction': '体重复盘', 'output_type': 'result',
            'html_template': 'templates/weight_review.html', 'data_source': 'python scripts/render_weight_review.py --start <S> --end <E> --chain "1.识别→2.读DB→3.复盘→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「体重复盘（自定义时间）」。\n\n我想看某段时间的体重复盘(自定义起止日期)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n起止日期(YYYY-MM-DD):____ ~ ____',
            'user_intent': '复盘自定义时间段的体重变化', 'data_fields': ['start', 'end', 'delta_kg', 'avg', 'vs_last_period', 'trend', 'summary'],
            'depends_on_external': False, 'order': 5
    },
    {
            'category': '体重',     'wake_word': '看里程碑回溯',     'desc': '看历史达成的体重里程碑',
            'main_prompt': {
        'cli': 'python scripts/render_weight_review.py --type milestones --chain "1.识别→2.读DB→3.回溯→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看里程碑回溯」。\n\n我想看所有达成过的体重里程碑。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_milestones', 'name': '看里程碑回溯', 'subfunction': '体重复盘', 'output_type': 'result',
            'html_template': 'templates/weight_review.html', 'data_source': 'python scripts/render_weight_review.py --type milestones --chain "1.识别→2.读DB→3.回溯→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看里程碑回溯」。\n\n我想看所有达成过的体重里程碑。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看历史达成的体重里程碑', 'data_fields': ['milestones', 'summary'],
            'depends_on_external': False, 'order': 6
    },

    {
            'category': '运动',     'wake_word': '记运动',     'desc': '记录一次运动(类型/时长/消耗/时间)',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_receipt.py --live-add --type <T> --calories <C> [--minutes <M>] --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「记运动」。\n\n我做了运动,请记下来。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n运动类型:____\n时长(分钟):____\n热量(卡,选填):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_add', 'name': '记运动', 'subfunction': '记运动', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_exercise_receipt.py --live-add --type <T> --calories <C> [--minutes <M>] --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「记运动」。\n\n我做了运动,请记下来。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n运动类型:____\n时长(分钟):____\n热量(卡,选填):____',
            'user_intent': '记录一次运动(类型/时长/消耗/时间)', 'data_fields': ["exercise_type", "duration_minutes", "calories_burned", "time", "is_estimated"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '运动',     'wake_word': '记运动（含备注）',     'desc': '记录一次运动并附带备注',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_receipt.py --live-add --type <T> --calories <C> [--minutes <M>] --note <N> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「记运动（含备注）」。\n\n我做了运动,请连同备注一起记下来。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n运动类型:____\n时长(分钟):____\n热量(卡,选填):____\n备注:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_add_note', 'name': '记运动（含备注）', 'subfunction': '记运动', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_exercise_receipt.py --live-add --type <T> --calories <C> [--minutes <M>] --note <N> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「记运动（含备注）」。\n\n我做了运动,请连同备注一起记下来。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n运动类型:____\n时长(分钟):____\n热量(卡,选填):____\n备注:____',
            'user_intent': '记录一次运动并附带备注', 'data_fields': ["exercise_type", "duration_minutes", "calories_burned", "note", "time"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '运动',     'wake_word': '记力量训练',     'desc': '记录力量训练(每组一行)',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_receipt.py --live-add-strength --type <T> --sets <N> --load <KG> --reps <R> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「记力量训练」。\n\n我练了力量训练,请记下来。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n动作名:____\n组数:____\n单组重量(kg):____\n每组次数:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_add_strength', 'name': '记力量训练', 'subfunction': '记运动', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_exercise_receipt.py --live-add-strength --type <T> --sets <N> --load <KG> --reps <R> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「记力量训练」。\n\n我练了力量训练,请记下来。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n动作名:____\n组数:____\n单组重量(kg):____\n每组次数:____',
            'user_intent': '记录力量训练(每组一行)', 'data_fields': ["exercise_type", "set_index", "load_kg", "reps", "calories_burned"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '运动',     'wake_word': '记有氧运动',     'desc': '记录有氧运动(时长/距离/配速/心率)',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_receipt.py --live-add --type <T> --category 有氧 --minutes <M> --distance <KM> [--avg-hr <BPM>] [--max-hr <BPM>] --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「记有氧运动」。\n\n我做了有氧运动,请记下来。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n运动类型:____\n时长(分钟):____\n距离(km,选填):____\n平均心率(选填):____\n最高心率(选填):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_add_cardio', 'name': '记有氧运动', 'subfunction': '记运动', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_exercise_receipt.py --live-add --type <T> --category 有氧 --minutes <M> --distance <KM> [--avg-hr <BPM>] [--max-hr <BPM>] --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「记有氧运动」。\n\n我做了有氧运动,请记下来。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n运动类型:____\n时长(分钟):____\n距离(km,选填):____\n平均心率(选填):____\n最高心率(选填):____',
            'user_intent': '记录有氧运动(时长/距离/配速/心率)', 'data_fields': ["exercise_type", "duration_minutes", "distance_km", "avg_heart_rate", "max_heart_rate", "pace"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '运动',     'wake_word': '记日常活动',     'desc': '记录日常活动(步数/消耗/时段)',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_receipt.py --live-add-daily --type <T> [--steps <N>] [--period <时段>] --minutes <M> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「记日常活动」。\n\n我做了日常活动(家务/通勤/走路等),请记下来。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n活动类型:____\n步数(选填):____\n时段(上午/下午/晚上,选填):____\n时长(分钟):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_add_daily', 'name': '记日常活动', 'subfunction': '记运动', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_exercise_receipt.py --live-add-daily --type <T> [--steps <N>] [--period <时段>] --minutes <M> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「记日常活动」。\n\n我做了日常活动(家务/通勤/走路等),请记下来。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n活动类型:____\n步数(选填):____\n时段(上午/下午/晚上,选填):____\n时长(分钟):____',
            'user_intent': '记录日常活动(步数/消耗/时段)', 'data_fields': ["exercise_type", "steps", "period", "duration_minutes", "calories_burned"],
            'depends_on_external': False, 'order': 4},
    {
            'category': '运动',     'wake_word': '补记运动',     'desc': '补录历史某天的运动',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_receipt.py --live-backfill --date <D> --type <T> --calories <C> [--minutes <M>] --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「补记运动」。\n\n我忘了记某天的运动,请补录到指定日期。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n运动类型:____\n日期:____\n时长(分钟):____\n热量(卡,选填):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_backfill', 'name': '补记运动', 'subfunction': '记运动', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_exercise_receipt.py --live-backfill --date <D> --type <T> --calories <C> [--minutes <M>] --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「补记运动」。\n\n我忘了记某天的运动,请补录到指定日期。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n运动类型:____\n日期:____\n时长(分钟):____\n热量(卡,选填):____',
            'user_intent': '补录历史某天的运动', 'data_fields': ["date", "exercise_type", "duration_minutes", "calories_burned", "is_backfill"],
            'depends_on_external': False, 'order': 5},
    {
            'category': '运动',     'wake_word': '批量补记运动',     'desc': '一次补录多天的运动',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_receipt.py --live-batch-add --items "<日期 类型 时长 热量;...>" --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「批量补记运动」。\n\n我要一次性补录多天的运动,每条含日期/类型/时长/热量。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n批量数据(每行一条:日期 类型 时长(分钟) 热量(卡)):\n____'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_batch_add', 'name': '批量补记运动', 'subfunction': '记运动', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_exercise_receipt.py --live-batch-add --items "<日期 类型 时长 热量;...>" --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「批量补记运动」。\n\n我要一次性补录多天的运动,每条含日期/类型/时长/热量。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n批量数据(每行一条:日期 类型 时长(分钟) 热量(卡)):\n____',
            'user_intent': '一次补录多天的运动', 'data_fields': ["written_count", "skipped_count", "failed_count", "failures"],
            'depends_on_external': False, 'order': 6},
    {
            'category': '运动',     'wake_word': '复制昨日运动',     'desc': '把昨天的运动复制到今天(或指定日期)',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_receipt.py --live-copy --target <D> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「复制昨日运动」。\n\n我想把昨天的运动记录复制到今天(或指定日期)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n复制到哪一天(选填,默认今天):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_copy', 'name': '复制昨日运动', 'subfunction': '记运动', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_exercise_receipt.py --live-copy --target <D> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「复制昨日运动」。\n\n我想把昨天的运动记录复制到今天(或指定日期)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n复制到哪一天(选填,默认今天):____',
            'user_intent': '把昨天的运动复制到今天(或指定日期)', 'data_fields': ["copied_count", "skipped_count", "target_date"],
            'depends_on_external': False, 'order': 7},
    {
            'category': '运动',     'wake_word': '改运动记录',     'desc': '修改一条运动记录',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_receipt.py --live-update --id <ID> [--field <X> --value <Y>] --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「改运动记录」。\n\n我要改一条运动记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n要改的记录(选填,如「最近一条」或日期):____\n要改的字段(类型/时长/热量/日期/备注):____\n新值:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_update', 'name': '改运动记录', 'subfunction': '改运动', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_exercise_receipt.py --live-update --id <ID> [--field <X> --value <Y>] --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改运动记录」。\n\n我要改一条运动记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n要改的记录(选填,如「最近一条」或日期):____\n要改的字段(类型/时长/热量/日期/备注):____\n新值:____',
            'user_intent': '修改一条运动记录', 'data_fields': ["id", "old_record", "new_record"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '运动',     'wake_word': '改某日运动',     'desc': '按日期修改运动记录',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_receipt.py --live-update-day --date <D> [--field <X> --value <Y>] --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「改某日运动」。\n\n我要改某一天的运动记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n日期:____\n要改的字段:____\n新值:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_update_day', 'name': '改某日运动', 'subfunction': '改运动', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_exercise_receipt.py --live-update-day --date <D> [--field <X> --value <Y>] --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改某日运动」。\n\n我要改某一天的运动记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n日期:____\n要改的字段:____\n新值:____',
            'user_intent': '按日期修改运动记录', 'data_fields': ["date", "matched_count", "old_record", "new_record"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '运动',     'wake_word': '删运动记录',     'desc': '删除一条运动记录',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_receipt.py --live-delete --id <ID> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「删运动记录」。\n\n我要删一条运动记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n要删的记录(选填,如「最近一条」或日期):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_delete', 'name': '删运动记录', 'subfunction': '改运动', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_exercise_receipt.py --live-delete --id <ID> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「删运动记录」。\n\n我要删一条运动记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n要删的记录(选填,如「最近一条」或日期):____',
            'user_intent': '删除一条运动记录', 'data_fields': ["id", "snapshot"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '运动',     'wake_word': '删某日运动',     'desc': '删除某天全部运动记录',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_receipt.py --live-delete-day --date <D> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「删某日运动」。\n\n我要删某一天的全部运动记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n日期:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_delete_day', 'name': '删某日运动', 'subfunction': '改运动', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_exercise_receipt.py --live-delete-day --date <D> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「删某日运动」。\n\n我要删某一天的全部运动记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n日期:____',
            'user_intent': '删除某天全部运动记录', 'data_fields': ["date", "deleted_count"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '运动',     'wake_word': '批量删运动',     'desc': '删除一个时间范围内的运动记录',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_receipt.py --live-delete-range --from <F> --to <T> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「批量删运动」。\n\n我要删除一个时间范围内的运动记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期:____\n结束日期:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_delete_range', 'name': '批量删运动', 'subfunction': '改运动', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_exercise_receipt.py --live-delete-range --from <F> --to <T> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「批量删运动」。\n\n我要删除一个时间范围内的运动记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期:____\n结束日期:____',
            'user_intent': '删除一个时间范围内的运动记录', 'data_fields': ["start_date", "end_date", "deleted_count"],
            'depends_on_external': False, 'order': 4},
    {
            'category': '运动',     'wake_word': '看今日运动',     'desc': '看今天运动明细和累计',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_summary.py --mode records --today', 'text': '请你加载技能 卡路里,执行唤醒词「看今日运动」。\n\n我想看今天运动明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_view_today', 'name': '看今日运动', 'subfunction': '看运动', 'output_type': 'result',
            'html_template': 'templates/exercise_summary.html', 'data_source': 'python scripts/render_exercise_summary.py --mode records --today', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看今日运动」。\n\n我想看今天运动明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看今天运动明细和累计', 'data_fields': ["date", "records", "total_calories", "total_minutes", "exercise_goal"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '运动',     'wake_word': '看昨日运动',     'desc': '看昨天运动明细和累计',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_summary.py --mode records --yesterday', 'text': '请你加载技能 卡路里,执行唤醒词「看昨日运动」。\n\n我想看昨天运动明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_view_yesterday', 'name': '看昨日运动', 'subfunction': '看运动', 'output_type': 'result',
            'html_template': 'templates/exercise_summary.html', 'data_source': 'python scripts/render_exercise_summary.py --mode records --yesterday', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看昨日运动」。\n\n我想看昨天运动明细。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看昨天运动明细和累计', 'data_fields': ["date", "records", "total_calories", "total_minutes", "exercise_goal"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '运动',     'wake_word': '看本周运动',     'desc': '看本周运动汇总',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_summary.py --mode summary --week', 'text': '请你加载技能 卡路里,执行唤醒词「看本周运动」。\n\n我想看本周运动(周一到今天)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_view_week', 'name': '看本周运动', 'subfunction': '看运动', 'output_type': 'result',
            'html_template': 'templates/exercise_summary.html', 'data_source': 'python scripts/render_exercise_summary.py --mode summary --week', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看本周运动」。\n\n我想看本周运动(周一到今天)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看本周运动汇总', 'data_fields': ["start_date", "end_date", "records", "total_calories", "total_minutes", "daily_avg", "active_days"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '运动',     'wake_word': '看上周运动',     'desc': '看上周运动汇总',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_summary.py --mode summary --last-week', 'text': '请你加载技能 卡路里,执行唤醒词「看上周运动」。\n\n我想看上周运动(周一至周日)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_view_last_week', 'name': '看上周运动', 'subfunction': '看运动', 'output_type': 'result',
            'html_template': 'templates/exercise_summary.html', 'data_source': 'python scripts/render_exercise_summary.py --mode summary --last-week', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看上周运动」。\n\n我想看上周运动(周一至周日)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看上周运动汇总', 'data_fields': ["start_date", "end_date", "records", "total_calories", "total_minutes", "daily_avg", "active_days"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '运动',     'wake_word': '看本月运动',     'desc': '看本月运动汇总',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_summary.py --mode summary --month', 'text': '请你加载技能 卡路里,执行唤醒词「看本月运动」。\n\n我想看本月运动(1 号到今天)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_view_month', 'name': '看本月运动', 'subfunction': '看运动', 'output_type': 'result',
            'html_template': 'templates/exercise_summary.html', 'data_source': 'python scripts/render_exercise_summary.py --mode summary --month', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看本月运动」。\n\n我想看本月运动(1 号到今天)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看本月运动汇总', 'data_fields': ["start_date", "end_date", "records", "total_calories", "total_minutes", "daily_avg", "active_days"],
            'depends_on_external': False, 'order': 4},
    {
            'category': '运动',     'wake_word': '看上月运动',     'desc': '看上月运动汇总',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_summary.py --mode summary --last-month', 'text': '请你加载技能 卡路里,执行唤醒词「看上月运动」。\n\n我想看上月运动。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_view_last_month', 'name': '看上月运动', 'subfunction': '看运动', 'output_type': 'result',
            'html_template': 'templates/exercise_summary.html', 'data_source': 'python scripts/render_exercise_summary.py --mode summary --last-month', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看上月运动」。\n\n我想看上月运动。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看上月运动汇总', 'data_fields': ["start_date", "end_date", "records", "total_calories", "total_minutes", "daily_avg", "active_days"],
            'depends_on_external': False, 'order': 5},
    {
            'category': '运动',     'wake_word': '看最近 7 天运动',     'desc': '看最近 7 天运动汇总',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_summary.py --mode summary --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「看最近 7 天运动」。\n\n我想看最近 7 天运动。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_view_7d', 'name': '看最近 7 天运动', 'subfunction': '看运动', 'output_type': 'result',
            'html_template': 'templates/exercise_summary.html', 'data_source': 'python scripts/render_exercise_summary.py --mode summary --days 7', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看最近 7 天运动」。\n\n我想看最近 7 天运动。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 7 天运动汇总', 'data_fields': ["start_date", "end_date", "records", "total_calories", "total_minutes", "daily_avg", "active_days"],
            'depends_on_external': False, 'order': 6},
    {
            'category': '运动',     'wake_word': '看最近 30 天运动',     'desc': '看最近 30 天运动汇总',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_summary.py --mode summary --days 30', 'text': '请你加载技能 卡路里,执行唤醒词「看最近 30 天运动」。\n\n我想看最近 30 天运动。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_view_30d', 'name': '看最近 30 天运动', 'subfunction': '看运动', 'output_type': 'result',
            'html_template': 'templates/exercise_summary.html', 'data_source': 'python scripts/render_exercise_summary.py --mode summary --days 30', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看最近 30 天运动」。\n\n我想看最近 30 天运动。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 30 天运动汇总', 'data_fields': ["start_date", "end_date", "records", "total_calories", "total_minutes", "daily_avg", "active_days"],
            'depends_on_external': False, 'order': 7},
    {
            'category': '运动',     'wake_word': '看某段时间运动',     'desc': '看一段自定义时间的运动汇总',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_summary.py --mode summary --from <F> --to <T>', 'text': '请你加载技能 卡路里,执行唤醒词「看某段时间运动」。\n\n我想看一段自定义时间的运动。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期:____\n结束日期:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_view_range', 'name': '看某段时间运动', 'subfunction': '看运动', 'output_type': 'result',
            'html_template': 'templates/exercise_summary.html', 'data_source': 'python scripts/render_exercise_summary.py --mode summary --from <F> --to <T>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看某段时间运动」。\n\n我想看一段自定义时间的运动。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期:____\n结束日期:____',
            'user_intent': '看一段自定义时间的运动汇总', 'data_fields': ["start_date", "end_date", "records", "total_calories", "total_minutes", "daily_avg", "active_days"],
            'depends_on_external': False, 'order': 8},
    {
            'category': '运动',     'wake_word': '看今日运动（vs 目标）',     'desc': '看今天运动目标达成情况(完成度/差额/判断)',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_goal_view.py --period today', 'text': '请你加载技能 卡路里,执行唤醒词「看今日运动（vs 目标）」。\n\n我想看今天的运动目标达成情况。如果还没设过每日运动消耗目标,先问我目标值。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_view_today_vs_goal', 'name': '看今日运动（vs 目标）', 'subfunction': '看运动', 'output_type': 'result',
            'html_template': 'templates/exercise_goal_view.html', 'data_source': 'python scripts/render_exercise_goal_view.py --period today', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看今日运动（vs 目标）」。\n\n我想看今天的运动目标达成情况。如果还没设过每日运动消耗目标,先问我目标值。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看今天运动目标达成情况(完成度/差额/判断)', 'data_fields': ["exercise_goal", "actual", "completion_pct", "gap", "achieved", "summary"],
            'depends_on_external': False, 'order': 9},
    {
            'category': '运动',     'wake_word': '看本周运动（vs 目标）',     'desc': '看本周运动目标达成情况(完成度/差额/判断)',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_goal_view.py --period week', 'text': '请你加载技能 卡路里,执行唤醒词「看本周运动（vs 目标）」。\n\n我想看本周的运动目标达成情况。如果还没设过每日运动消耗目标,先问我目标值。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_view_week_vs_goal', 'name': '看本周运动（vs 目标）', 'subfunction': '看运动', 'output_type': 'result',
            'html_template': 'templates/exercise_goal_view.html', 'data_source': 'python scripts/render_exercise_goal_view.py --period week', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看本周运动（vs 目标）」。\n\n我想看本周的运动目标达成情况。如果还没设过每日运动消耗目标,先问我目标值。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看本周运动目标达成情况(完成度/差额/判断)', 'data_fields': ["exercise_goal", "week_goal", "actual", "completion_pct", "gap", "achieved", "summary"],
            'depends_on_external': False, 'order': 10},
    {
            'category': '运动',     'wake_word': '看运动记录（有备注）',     'desc': '看带备注的运动记录',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_summary.py --mode records --has-note', 'text': '请你加载技能 卡路里,执行唤醒词「看运动记录（有备注）」。\n\n我想看带备注的运动记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_view_notes', 'name': '看运动记录（有备注）', 'subfunction': '看运动', 'output_type': 'result',
            'html_template': 'templates/exercise_summary.html', 'data_source': 'python scripts/render_exercise_summary.py --mode records --has-note', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看运动记录（有备注）」。\n\n我想看带备注的运动记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看带备注的运动记录', 'data_fields': ["records", "note"],
            'depends_on_external': False, 'order': 11},
    {
            'category': '运动',     'wake_word': '看运动记录（按力量筛选）',     'desc': '看力量训练记录',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_summary.py --mode records --category 力量', 'text': '请你加载技能 卡路里,执行唤醒词「看运动记录（按力量筛选）」。\n\n我想看力量训练记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_view_strength', 'name': '看运动记录（按力量筛选）', 'subfunction': '看运动', 'output_type': 'result',
            'html_template': 'templates/exercise_summary.html', 'data_source': 'python scripts/render_exercise_summary.py --mode records --category 力量', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看运动记录（按力量筛选）」。\n\n我想看力量训练记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看力量训练记录', 'data_fields': ["records", "set_index", "load_kg", "reps"],
            'depends_on_external': False, 'order': 12},
    {
            'category': '运动',     'wake_word': '看运动记录（按有氧筛选）',     'desc': '看有氧运动记录',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_summary.py --mode records --category 有氧', 'text': '请你加载技能 卡路里,执行唤醒词「看运动记录（按有氧筛选）」。\n\n我想看有氧运动记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_view_cardio', 'name': '看运动记录（按有氧筛选）', 'subfunction': '看运动', 'output_type': 'result',
            'html_template': 'templates/exercise_summary.html', 'data_source': 'python scripts/render_exercise_summary.py --mode records --category 有氧', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看运动记录（按有氧筛选）」。\n\n我想看有氧运动记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看有氧运动记录', 'data_fields': ["records", "distance_km", "pace"],
            'depends_on_external': False, 'order': 13},
    {
            'category': '运动',     'wake_word': '看最近 60 天运动',     'desc': '看最近 60 天运动(每天一行)',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_summary.py --mode summary --days 60', 'text': '请你加载技能 卡路里,执行唤醒词「看最近 60 天运动」。\n\n我想看最近 60 天运动(每天一行)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_view_60d', 'name': '看最近 60 天运动', 'subfunction': '看运动', 'output_type': 'result',
            'html_template': 'templates/exercise_summary.html', 'data_source': 'python scripts/render_exercise_summary.py --mode summary --days 60', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看最近 60 天运动」。\n\n我想看最近 60 天运动(每天一行)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 60 天运动(每天一行)', 'data_fields': ["start_date", "end_date", "daily_rows", "total_calories", "total_minutes", "daily_avg", "active_days"],
            'depends_on_external': False, 'order': 14},
    {
            'category': '运动',     'wake_word': '看最近 180 天运动',     'desc': '看最近 180 天运动(每 3 天降采样)',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_summary.py --mode summary --days 180 --downsample 3', 'text': '请你加载技能 卡路里,执行唤醒词「看最近 180 天运动」。\n\n我想看最近 180 天运动(每 3 天降采样一行)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_view_180d', 'name': '看最近 180 天运动', 'subfunction': '看运动', 'output_type': 'result',
            'html_template': 'templates/exercise_summary.html', 'data_source': 'python scripts/render_exercise_summary.py --mode summary --days 180 --downsample 3', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看最近 180 天运动」。\n\n我想看最近 180 天运动(每 3 天降采样一行)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 180 天运动(每 3 天降采样)', 'data_fields': ["start_date", "end_date", "downsample_rows", "total_calories", "total_minutes", "daily_avg", "active_days"],
            'depends_on_external': False, 'order': 15},
    {
            'category': '运动',     'wake_word': '看最近 365 天运动',     'desc': '看最近 365 天运动(每周降采样)',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_summary.py --mode summary --days 365 --downsample week', 'text': '请你加载技能 卡路里,执行唤醒词「看最近 365 天运动」。\n\n我想看最近 365 天运动(每周降采样一行)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_view_365d', 'name': '看最近 365 天运动', 'subfunction': '看运动', 'output_type': 'result',
            'html_template': 'templates/exercise_summary.html', 'data_source': 'python scripts/render_exercise_summary.py --mode summary --days 365 --downsample week', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看最近 365 天运动」。\n\n我想看最近 365 天运动(每周降采样一行)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 365 天运动(每周降采样)', 'data_fields': ["start_date", "end_date", "downsample_rows", "total_calories", "total_minutes", "daily_avg", "active_days"],
            'depends_on_external': False, 'order': 16},
    {
            'category': '运动',     'wake_word': '看运动类型分布',     'desc': '看运动类型分布(饼图+占比)',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_distribution.py --mode distribution', 'text': '请你加载技能 卡路里,执行唤醒词「看运动类型分布」。\n\n我想看运动类型分布。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_distribution', 'name': '看运动类型分布', 'subfunction': '运动分析', 'output_type': 'result',
            'html_template': 'templates/exercise_distribution.html', 'data_source': 'python scripts/render_exercise_distribution.py --mode distribution', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看运动类型分布」。\n\n我想看运动类型分布。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看运动类型分布(饼图+占比)', 'data_fields': ["distribution", "counts", "calories", "percentages"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '运动',     'wake_word': '看力量训练总览',     'desc': '看力量训练按动作聚合的总览',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_strength.py', 'text': '请你加载技能 卡路里,执行唤醒词「看力量训练总览」。\n\n我想看力量训练总览。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_strength_overview', 'name': '看力量训练总览', 'subfunction': '运动分析', 'output_type': 'result',
            'html_template': 'templates/exercise_strength.html', 'data_source': 'python scripts/render_exercise_strength.py', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看力量训练总览」。\n\n我想看力量训练总览。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看力量训练按动作聚合的总览', 'data_fields': ["action", "total_sets", "total_weight", "total_reps", "weight_trend"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '运动',     'wake_word': '看有氧训练总览',     'desc': '看有氧训练按类型聚合的总览',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_cardio.py', 'text': '请你加载技能 卡路里,执行唤醒词「看有氧训练总览」。\n\n我想看有氧训练总览。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_cardio_overview', 'name': '看有氧训练总览', 'subfunction': '运动分析', 'output_type': 'result',
            'html_template': 'templates/exercise_cardio.html', 'data_source': 'python scripts/render_exercise_cardio.py', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看有氧训练总览」。\n\n我想看有氧训练总览。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看有氧训练按类型聚合的总览', 'data_fields': ["exercise_type", "count", "total_minutes", "total_distance", "avg_pace"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '运动',     'wake_word': '看运动趋势',     'desc': '看运动趋势(每日时长/消耗/每周频次)',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_trend.py [--days 30]', 'text': '请你加载技能 卡路里,执行唤醒词「看运动趋势」。\n\n我想看运动趋势。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n时间窗口(天,选填,默认 30):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_trend', 'name': '看运动趋势', 'subfunction': '运动分析', 'output_type': 'result',
            'html_template': 'templates/exercise_trend.html', 'data_source': 'python scripts/render_exercise_trend.py [--days 30]', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看运动趋势」。\n\n我想看运动趋势。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n时间窗口(天,选填,默认 30):____',
            'user_intent': '看运动趋势(每日时长/消耗/每周频次)', 'data_fields': ["daily_minutes", "daily_calories", "weekly_frequency", "summary"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '运动',     'wake_word': '运动复盘（本周）',     'desc': '看本周运动复盘',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_recap.py --period week', 'text': '请你加载技能 卡路里,执行唤醒词「运动复盘（本周）」。\n\n我想看本周运动复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_recap_week', 'name': '运动复盘（本周）', 'subfunction': '运动复盘', 'output_type': 'result',
            'html_template': 'templates/exercise_recap.html', 'data_source': 'python scripts/render_exercise_recap.py --period week', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「运动复盘（本周）」。\n\n我想看本周运动复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看本周运动复盘', 'data_fields': ["total_minutes", "total_calories", "frequency", "type_distribution", "trend", "top_movements"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '运动',     'wake_word': '运动复盘（本月）',     'desc': '看本月运动复盘',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_recap.py --period month', 'text': '请你加载技能 卡路里,执行唤醒词「运动复盘（本月）」。\n\n我想看本月运动复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_recap_month', 'name': '运动复盘（本月）', 'subfunction': '运动复盘', 'output_type': 'result',
            'html_template': 'templates/exercise_recap.html', 'data_source': 'python scripts/render_exercise_recap.py --period month', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「运动复盘（本月）」。\n\n我想看本月运动复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看本月运动复盘', 'data_fields': ["total_minutes", "total_calories", "frequency", "type_distribution", "trend", "top_movements"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '运动',     'wake_word': '运动复盘（最近 90 天）',     'desc': '看最近 90 天运动复盘',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_recap.py --period 90d', 'text': '请你加载技能 卡路里,执行唤醒词「运动复盘（最近 90 天）」。\n\n我想看最近 90 天运动复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_recap_90d', 'name': '运动复盘（最近 90 天）', 'subfunction': '运动复盘', 'output_type': 'result',
            'html_template': 'templates/exercise_recap.html', 'data_source': 'python scripts/render_exercise_recap.py --period 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「运动复盘（最近 90 天）」。\n\n我想看最近 90 天运动复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 90 天运动复盘', 'data_fields': ["total_minutes", "total_calories", "frequency", "type_distribution", "trend", "top_movements"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '运动',     'wake_word': '运动复盘（今年）',     'desc': '看今年运动复盘',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_recap.py --period year', 'text': '请你加载技能 卡路里,执行唤醒词「运动复盘（今年）」。\n\n我想看今年运动复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_recap_year', 'name': '运动复盘（今年）', 'subfunction': '运动复盘', 'output_type': 'result',
            'html_template': 'templates/exercise_recap.html', 'data_source': 'python scripts/render_exercise_recap.py --period year', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「运动复盘（今年）」。\n\n我想看今年运动复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看今年运动复盘', 'data_fields': ["total_minutes", "total_calories", "frequency", "type_distribution", "trend", "top_movements"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '运动',     'wake_word': '运动复盘（自定义时间）',     'desc': '看自定义时间的运动复盘',
        'main_prompt': {
        'cli': 'python scripts/render_exercise_recap.py --period range --from <F> --to <T>', 'text': '请你加载技能 卡路里,执行唤醒词「运动复盘（自定义时间）」。\n\n我想看一段自定义时间的运动复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期:____\n结束日期:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'exercise_recap_range', 'name': '运动复盘（自定义时间）', 'subfunction': '运动复盘', 'output_type': 'result',
            'html_template': 'templates/exercise_recap.html', 'data_source': 'python scripts/render_exercise_recap.py --period range --from <F> --to <T>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「运动复盘（自定义时间）」。\n\n我想看一段自定义时间的运动复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期:____\n结束日期:____',
            'user_intent': '看自定义时间的运动复盘', 'data_fields': ["start_date", "end_date", "total_minutes", "total_calories", "frequency", "type_distribution", "trend", "top_movements"],
            'depends_on_external': False, 'order': 4},
    {
            'category': '健身计划',     'wake_word': '看本周计划',     'desc': '本周训练日历(7 天表 + 完成度)',
            'main_prompt': {
        'cli': 'python scripts/render_workout_plan.py --week <N>', 'text': '请你加载技能 卡路里,执行唤醒词「看本周计划」。\n\n我想看本周的训练日历。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_view_this_week', 'name': '看本周计划', 'subfunction': '看训练计划', 'output_type': 'result',
            'html_template': 'templates/workout_plan_view.html', 'data_source': 'python scripts/render_workout_plan.py --week <N>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看本周计划」。\n\n我想看本周的训练日历。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '我想看本周的训练日历和完成度', 'data_fields': ["week_number", "days", "sessions", "movements", "completion_rate"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '健身计划',     'wake_word': '看下周计划',     'desc': '下周训练日历预览(含待练状态)',
            'main_prompt': {
        'cli': 'python scripts/render_workout_plan.py --week <N+1>', 'text': '请你加载技能 卡路里,执行唤醒词「看下周计划」。\n\n我想看下周的训练日历。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_view_next_week', 'name': '看下周计划', 'subfunction': '看训练计划', 'output_type': 'result',
            'html_template': 'templates/workout_plan_view.html', 'data_source': 'python scripts/render_workout_plan.py --week <N+1>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看下周计划」。\n\n我想看下周的训练日历。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '我想预览下周的训练安排', 'data_fields': ["week_number", "days", "sessions", "movements", "completion_rate"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '健身计划',     'wake_word': '看上周计划',     'desc': '上周训练日历 + 完成率回顾',
            'main_prompt': {
        'cli': 'python scripts/render_workout_plan.py --week <N-1>', 'text': '请你加载技能 卡路里,执行唤醒词「看上周计划」。\n\n我想看上周的训练日历。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_view_last_week', 'name': '看上周计划', 'subfunction': '看训练计划', 'output_type': 'result',
            'html_template': 'templates/workout_plan_view.html', 'data_source': 'python scripts/render_workout_plan.py --week <N-1>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看上周计划」。\n\n我想看上周的训练日历。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '我想回顾上周的训练安排和完成率', 'data_fields': ["week_number", "days", "sessions", "movements", "completion_rate"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '健身计划',     'wake_word': '看指定周计划',     'desc': '指定周次训练日历',
            'main_prompt': {
        'cli': 'python scripts/render_workout_plan.py --week <N>', 'text': '请你加载技能 卡路里,执行唤醒词「看指定周计划」。\n\n我想看某一周的训练日历。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n周次(如第 3 周):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_view_week', 'name': '看指定周计划', 'subfunction': '看训练计划', 'output_type': 'result',
            'html_template': 'templates/workout_plan_view.html', 'data_source': 'python scripts/render_workout_plan.py --week <N>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看指定周计划」。\n\n我想看某一周的训练日历。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n周次(如第 3 周):____',
            'user_intent': '我想查看指定周次的训练安排', 'data_fields': ["week_number", "days", "sessions", "movements", "completion_rate"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '健身计划',     'wake_word': '看今天练什么',     'desc': '今日动作/组数/重量 + 实时完成进度',
            'main_prompt': {
        'cli': 'python scripts/render_workout_plan.py --today', 'text': '请你加载技能 卡路里,执行唤醒词「看今天练什么」。\n\n我想看今天要练的动作。如果今天休息或计划还没开始,请明确告诉我。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_view_today', 'name': '看今天练什么', 'subfunction': '看训练计划', 'output_type': 'result',
            'html_template': 'templates/workout_plan_view.html', 'data_source': 'python scripts/render_workout_plan.py --today', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看今天练什么」。\n\n我想看今天要练的动作。如果今天休息或计划还没开始,请明确告诉我。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '我想看今天练什么以及练到哪了', 'data_fields': ["sessions", "movements", "sets_done", "sets_remaining", "completion_rate"],
            'depends_on_external': False, 'order': 4},
    {
            'category': '健身计划',     'wake_word': '看计划概览',     'desc': '计划总览 KPI + 每周完成率列表',
            'main_prompt': {
        'cli': 'python scripts/render_workout_plan.py --overview', 'text': '请你加载技能 卡路里,执行唤醒词「看计划概览」。\n\n我想看整个健身计划的概览。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_overview', 'name': '看计划概览', 'subfunction': '看训练计划', 'output_type': 'result',
            'html_template': 'templates/workout_plan_view.html', 'data_source': 'python scripts/render_workout_plan.py --overview', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看计划概览」。\n\n我想看整个健身计划的概览。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '我想看训练计划的总体概览和每周完成情况', 'data_fields': ["total_weeks", "completion_rate", "training_days", "total_movements", "weekly_rates"],
            'depends_on_external': False, 'order': 5},
    {
            'category': '健身计划',     'wake_word': '看计划 vs 实际',     'desc': '计划 vs 实际对比(完成度/偏差/动作级表)',
            'main_prompt': {
        'cli': 'python scripts/render_workout_plan.py --vs-actual --start <D1> --end <D2>', 'text': '请你加载技能 卡路里,执行唤醒词「看计划 vs 实际」。\n\n我想对比一段时间里计划和实际完成。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n时间范围(默认本周,可给日期):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_vs_actual', 'name': '看计划 vs 实际', 'subfunction': '看训练计划', 'output_type': 'result',
            'html_template': 'templates/workout_plan_view.html', 'data_source': 'python scripts/render_workout_plan.py --vs-actual --start <D1> --end <D2>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看计划 vs 实际」。\n\n我想对比一段时间里计划和实际完成。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n时间范围(默认本周,可给日期):____',
            'user_intent': '我想对比计划训练量和实际完成量的差距', 'data_fields': ["completion_rate", "deviation", "movement_rows", "start_date", "end_date"],
            'depends_on_external': False, 'order': 6},
    {
            'category': '健身计划',     'wake_word': '定训练计划',     'desc': 'AI 采访式创建计划(预览确认 → 写入回执)',
            'main_prompt': {
        'cli': 'python scripts/render_plan_receipt.py --live-plan-set --plan-json <JSON> --chain "1.采访→2.预览确认→3.写库→4.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「定训练计划」。\n\n我想制定一份新的健身计划,根据我的目标和训练情况来安排(标题/总周数/起始日)。如果我没说清楚我的目标和训练情况,请先问我。请先给我看完整计划预览,我确认后再保存,保存后给我回执。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_set', 'name': '定训练计划', 'subfunction': '定训练计划', 'output_type': 'receipt',
            'html_template': 'templates/plan_builder_wizard.html', 'data_source': 'python scripts/render_plan_receipt.py --live-plan-set --plan-json <JSON> --chain "1.采访→2.预览确认→3.写库→4.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「定训练计划」。\n\n我想制定一份新的健身计划,根据我的目标和训练情况来安排(标题/总周数/起始日)。如果我没说清楚我的目标和训练情况,请先问我。请先给我看完整计划预览,我确认后再保存,保存后给我回执。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '我想根据我的目标和情况定制一份训练计划', 'data_fields': ["goal", "experience", "frequency", "target_parts", "title", "total_weeks", "start_date"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '健身计划',     'wake_word': '复制训练计划',     'desc': '复制整计划或某周作为模板',
            'main_prompt': {
        'cli': 'python scripts/render_plan_receipt.py --live-plan-copy [--new-title <T>] --chain "1.读当前计划→2.复制→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「复制训练计划」。\n\n我想把现有训练计划复制一份作为模板(可以复制整个计划或某一周)。请告诉我复制了哪些内容、新计划/新周的标题或周次。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n要复制的周次(选填,空=整个计划):____\n新标题(选填):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_copy', 'name': '复制训练计划', 'subfunction': '定训练计划', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_plan_receipt.py --live-plan-copy [--new-title <T>] --chain "1.读当前计划→2.复制→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「复制训练计划」。\n\n我想把现有训练计划复制一份作为模板(可以复制整个计划或某一周)。请告诉我复制了哪些内容、新计划/新周的标题或周次。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n要复制的周次(选填,空=整个计划):____\n新标题(选填):____',
            'user_intent': '我想复制一份训练计划作为新模板', 'data_fields': ["copied_weeks", "new_title", "source_week"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '健身计划',     'wake_word': '定休息日',     'desc': '标记某天为休息日(或取消)',
            'main_prompt': {
        'cli': 'python scripts/render_plan_receipt.py --live-plan-rest --week <W> --day <D> --rest <1|0> --chain "1.定位天→2.标记→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「定休息日」。\n\n我想把某一天的训练标记为休息日(或取消休息)。完成后给我设置回执。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n日期或周次+星期:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_set_rest', 'name': '定休息日', 'subfunction': '定训练计划', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_plan_receipt.py --live-plan-rest --week <W> --day <D> --rest <1|0> --chain "1.定位天→2.标记→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「定休息日」。\n\n我想把某一天的训练标记为休息日(或取消休息)。完成后给我设置回执。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n日期或周次+星期:____',
            'user_intent': '我想把某天标记为休息日', 'data_fields': ["date", "is_rest_day", "before", "after"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '健身计划',     'wake_word': '加训练动作',     'desc': '给某天/时段加动作(组数/重量)',
            'main_prompt': {
        'cli': 'python scripts/render_plan_receipt.py --live-plan-add --week <W> --day <D> --name <动作> --sets <N> [--weight <kg>] --chain "1.定位时段→2.加动作→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「加训练动作」。\n\n我想给计划里的某一天或某个训练时段加训练动作,包括动作名、组数和重量。如果计划是每周循环的,告诉我加在哪一周,不说就所有周都加。完成后给我回执。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n加到哪天(如 周三):____\n加到第几周(选填,空=所有周):____\n时段(选填):____\n动作名:____\n组数:____\n重量(kg,选填):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_add_movement', 'name': '加训练动作', 'subfunction': '定训练计划', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_plan_receipt.py --live-plan-add --week <W> --day <D> --name <动作> --sets <N> [--weight <kg>] --chain "1.定位时段→2.加动作→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「加训练动作」。\n\n我想给计划里的某一天或某个训练时段加训练动作,包括动作名、组数和重量。如果计划是每周循环的,告诉我加在哪一周,不说就所有周都加。完成后给我回执。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n加到哪天(如 周三):____\n加到第几周(选填,空=所有周):____\n时段(选填):____\n动作名:____\n组数:____\n重量(kg,选填):____',
            'user_intent': '我想给训练计划加一个新动作', 'data_fields': ["week_number", "day_of_week", "session_label", "movement", "sets", "weight_kg"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '健身计划',     'wake_word': '定一周计划',     'desc': '快速设置一周 7 天安排',
            'main_prompt': {
        'cli': 'python scripts/render_plan_receipt.py --live-plan-set-week --week <W> --days-json <JSON> --chain "1.解析7天→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「定一周计划」。\n\n我想快速设置某一周的训练安排,告诉我这周每天(周一至周日)练什么或休息,只想练其中几天也没关系,空着的天按休息处理。完成后给我设置回执。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n第几周(默认本周):____\n一周安排(如:周一胸、周三腿,没说的天按休息):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_set_week', 'name': '定一周计划', 'subfunction': '定训练计划', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_plan_receipt.py --live-plan-set-week --week <W> --days-json <JSON> --chain "1.解析7天→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「定一周计划」。\n\n我想快速设置某一周的训练安排,告诉我这周每天(周一至周日)练什么或休息,只想练其中几天也没关系,空着的天按休息处理。完成后给我设置回执。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n第几周(默认本周):____\n一周安排(如:周一胸、周三腿,没说的天按休息):____',
            'user_intent': '我想快速设置一周七天的训练安排', 'data_fields': ["week_number", "day_schedule", "rest_days"],
            'depends_on_external': False, 'order': 4},
    {
            'category': '健身计划',     'wake_word': '改训练计划',     'desc': '改计划配置字段(改前/改后 + 影响)',
            'main_prompt': {
        'cli': 'python scripts/render_plan_receipt.py --live-plan-update --field <X> --value <Y> --chain "1.读旧值→2.更新→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「改训练计划」。\n\n我想改训练计划的某个字段(如标题、总周数、开始日期、描述)。改完并提示影响(如改开始日期会影响周次计算)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n要改的字段(标题/总周数/开始日期/描述,可改多个):____\n新值:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_update', 'name': '改训练计划', 'subfunction': '改训练计划', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_plan_receipt.py --live-plan-update --field <X> --value <Y> --chain "1.读旧值→2.更新→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改训练计划」。\n\n我想改训练计划的某个字段(如标题、总周数、开始日期、描述)。改完并提示影响(如改开始日期会影响周次计算)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n要改的字段(标题/总周数/开始日期/描述,可改多个):____\n新值:____',
            'user_intent': '我想修改训练计划的某个配置字段', 'data_fields': ["field", "before", "after"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '健身计划',     'wake_word': '改某天训练',     'desc': '改某天训练安排(改前/改后)',
            'main_prompt': {
        'cli': 'python scripts/render_plan_receipt.py --live-plan-update-day --week <W> --day <D> --session <S> [--label <L>] --chain "1.读现状→2.更新→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「改某天训练」。\n\n我想改某一天的训练安排(时段、动作、组数等)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n日期:____\n要改的内容:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_update_day', 'name': '改某天训练', 'subfunction': '改训练计划', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_plan_receipt.py --live-plan-update-day --week <W> --day <D> --session <S> [--label <L>] --chain "1.读现状→2.更新→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改某天训练」。\n\n我想改某一天的训练安排(时段、动作、组数等)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n日期:____\n要改的内容:____',
            'user_intent': '我想修改某一天的训练安排', 'data_fields': ["date", "field", "before", "after"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '健身计划',     'wake_word': '删某天训练',     'desc': '删某天训练(快照确认 → 回执)',
            'main_prompt': {
        'cli': 'python scripts/render_plan_receipt.py --live-plan-delete-day --week <W> --day <D> --chain "1.快照→2.确认→3.删除→4.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「删某天训练」。\n\n我想删掉某一天的训练安排(或某天的某个训练时段)。删除前先让我确认,确认后删除,给我确认回执。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n日期:____\n要删的时段(选填,空=删整天):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_delete_day', 'name': '删某天训练', 'subfunction': '改训练计划', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_plan_receipt.py --live-plan-delete-day --week <W> --day <D> --chain "1.快照→2.确认→3.删除→4.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「删某天训练」。\n\n我想删掉某一天的训练安排(或某天的某个训练时段)。删除前先让我确认,确认后删除,给我确认回执。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n日期:____\n要删的时段(选填,空=删整天):____',
            'user_intent': '我想删除某天的训练安排', 'data_fields': ["date", "snapshot", "deleted_sessions"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '健身计划',     'wake_word': '改动作',     'desc': '替换动作(改前/改后 + 组数变化)',
            'main_prompt': {
        'cli': 'python scripts/render_plan_receipt.py --live-plan-update-movement --week <W> --day <D> --session <S> --old-name <A> --new-name <B> --chain "1.定位动作→2.替换→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「改动作」。\n\n我想把计划里的某个动作换成另一个动作(或改它的组数)。如果计划是每周循环的,告诉我要改哪一周,不说就所有周都改。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n要改的周(选填,空=所有周):____\n原动作:____\n新动作:____\n组数(选填):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_update_movement', 'name': '改动作', 'subfunction': '改训练计划', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_plan_receipt.py --live-plan-update-movement --week <W> --day <D> --session <S> --old-name <A> --new-name <B> --chain "1.定位动作→2.替换→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改动作」。\n\n我想把计划里的某个动作换成另一个动作(或改它的组数)。如果计划是每周循环的,告诉我要改哪一周,不说就所有周都改。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n要改的周(选填,空=所有周):____\n原动作:____\n新动作:____\n组数(选填):____',
            'user_intent': '我想替换计划里的某个动作', 'data_fields': ["date", "old_movement", "new_movement", "sets_before", "sets_after"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '健身计划',     'wake_word': '撤销训练计划',     'desc': '删除整个计划(确认 → 回执 + 提示)',
            'main_prompt': {
        'cli': 'python scripts/render_plan_receipt.py --live-plan-delete --chain "1.概要→2.确认→3.删除→4.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「撤销训练计划」。\n\n我想删除整个训练计划(所有周次和配置)。删除前先让我确认,确认后删除,给我删除回执和提示(删除后如何重新制定)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_delete', 'name': '撤销训练计划', 'subfunction': '改训练计划', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_plan_receipt.py --live-plan-delete --chain "1.概要→2.确认→3.删除→4.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「撤销训练计划」。\n\n我想删除整个训练计划(所有周次和配置)。删除前先让我确认,确认后删除,给我删除回执和提示(删除后如何重新制定)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '我想删除整个训练计划', 'data_fields': ["plan_summary", "deleted_config", "deleted_rows"],
            'depends_on_external': False, 'order': 4},
    {
            'category': '健身计划',     'wake_word': '落地训练',     'desc': '4 步落地(补计划/记心愿/推送/回写)',
            'main_prompt': {
        'cli': 'python scripts/sync_plan.py --days 1', 'text': '请你加载技能 卡路里,执行唤醒词「落地训练」。\n\n我想把某天的训练计划真正落地执行:补计划到日历、记心愿、推送到训记、拉取训记实绩 4 步全流程,逐动作确认实际做的重量和组数。给我看 4 步进度和每步结果(已补计划/已记心愿/已推送/已回写),以及完成度。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n日期(默认今天):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_execute', 'name': '落地训练', 'subfunction': '落地训练', 'output_type': 'process',
            'html_template': 'templates/process_progress.html', 'data_source': 'python scripts/sync_plan.py --days 1', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「落地训练」。\n\n我想把某天的训练计划真正落地执行:补计划到日历、记心愿、推送到训记、拉取训记实绩 4 步全流程,逐动作确认实际做的重量和组数。给我看 4 步进度和每步结果(已补计划/已记心愿/已推送/已回写),以及完成度。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n日期(默认今天):____',
            'user_intent': '我想把某天的训练计划完整落地执行', 'data_fields': ["date", "step1_created", "step2_added", "step3_pushed", "step4_backfilled", "completion"],
            'depends_on_external': True, 'order': 0},
    {
            'category': '健身计划',     'wake_word': '落地到本周末',     'desc': '批量落地到本周末(跨天汇总)',
            'main_prompt': {
        'cli': 'python scripts/sync_plan.py --days <N>', 'text': '请你加载技能 卡路里,执行唤醒词「落地到本周末」。\n\n我想把从今天到周日所有训练日一次落地执行(补计划/记心愿/推训记/回写),如果今天已是周日就只落地今天。请给我看跨天列表、每一步的汇总(已补计划/已记心愿/已推送/已回写)和总完成度。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_execute_weekend', 'name': '落地到本周末', 'subfunction': '落地训练', 'output_type': 'process',
            'html_template': 'templates/process_progress.html', 'data_source': 'python scripts/sync_plan.py --days <N>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「落地到本周末」。\n\n我想把从今天到周日所有训练日一次落地执行(补计划/记心愿/推训记/回写),如果今天已是周日就只落地今天。请给我看跨天列表、每一步的汇总(已补计划/已记心愿/已推送/已回写)和总完成度。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '我想把本周剩余训练日批量落地', 'data_fields': ["days", "day_summaries", "step_totals", "completion"],
            'depends_on_external': True, 'order': 1},
    {
            'category': '健身计划',     'wake_word': '落地到本月底',     'desc': '批量落地到本月底(跨天汇总)',
            'main_prompt': {
        'cli': 'python scripts/sync_plan.py --days <N>', 'text': '请你加载技能 卡路里,执行唤醒词「落地到本月底」。\n\n我想把从今天到本月底所有训练日一次落地执行(补计划/记心愿/推训记/回写),如果今天已是月底就只落地今天。请给我看跨天列表、每一步的汇总(已补计划/已记心愿/已推送/已回写)和总完成度。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_execute_month', 'name': '落地到本月底', 'subfunction': '落地训练', 'output_type': 'process',
            'html_template': 'templates/process_progress.html', 'data_source': 'python scripts/sync_plan.py --days <N>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「落地到本月底」。\n\n我想把从今天到本月底所有训练日一次落地执行(补计划/记心愿/推训记/回写),如果今天已是月底就只落地今天。请给我看跨天列表、每一步的汇总(已补计划/已记心愿/已推送/已回写)和总完成度。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '我想把本月剩余训练日批量落地', 'data_fields': ["days", "day_summaries", "step_totals", "completion"],
            'depends_on_external': True, 'order': 2},
    {
            'category': '健身计划',     'wake_word': '同步到训记',     'desc': '推 plan 到训记(前置审计动作名)',
            'main_prompt': {
        'cli': 'python scripts/render_plan_receipt.py --live-plan-sync --date <D> --chain "1.审计动作名→2.推送→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「同步到训记」。\n\n我想把某天的训练计划推送到训记 App(落地流程里的训记推送这一步单独做)。推送前先检查计划里的动作名训记能否识别,有识别不了的先告诉我。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n日期(默认今天):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_sync_xunji', 'name': '同步到训记', 'subfunction': '落地训练', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_plan_receipt.py --live-plan-sync --date <D> --chain "1.审计动作名→2.推送→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「同步到训记」。\n\n我想把某天的训练计划推送到训记 App(落地流程里的训记推送这一步单独做)。推送前先检查计划里的动作名训记能否识别,有识别不了的先告诉我。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n日期(默认今天):____',
            'user_intent': '我想把训练计划推送到训记', 'data_fields': ["date", "pushed_count", "results", "unrecognized_movements"],
            'depends_on_external': True, 'order': 3},
    {
            'category': '健身计划',     'wake_word': '拉训记实绩',     'desc': '拉训记实绩回写 exercise_log',
            'main_prompt': {
        'cli': 'python scripts/render_plan_receipt.py --live-plan-backfill --date <D> --chain "1.拉取→2.回写→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「拉训记实绩」。\n\n我想把训记 App 里的实际训练数据拉回来,写进卡路里的运动记录(落地流程里的回写这一步单独做)。如有冲突请提示我处理。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n日期(默认今天):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_backfill_xunji', 'name': '拉训记实绩', 'subfunction': '落地训练', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_plan_receipt.py --live-plan-backfill --date <D> --chain "1.拉取→2.回写→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「拉训记实绩」。\n\n我想把训记 App 里的实际训练数据拉回来,写进卡路里的运动记录(落地流程里的回写这一步单独做)。如有冲突请提示我处理。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n日期(默认今天):____',
            'user_intent': '我想把训记里的实际训练拉回卡路里', 'data_fields': ["date", "inserted", "updated", "skipped", "conflicts"],
            'depends_on_external': True, 'order': 4},
    {
            'category': '健身计划',     'wake_word': '计划复盘（本周）',     'desc': '本周复盘(KPI + 趋势 + 上周对比)',
            'main_prompt': {
        'cli': 'python scripts/render_exercise_review_html.py --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「计划复盘（本周）」。\n\n我想复盘本周的训练:完成率、训练日数、消耗等关键数字,完成趋势,以及本周与上周的对比。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_review_week', 'name': '计划复盘（本周）', 'subfunction': '计划复盘', 'output_type': 'result',
            'html_template': 'templates/exercise_review.html', 'data_source': 'python scripts/render_exercise_review_html.py --days 7', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「计划复盘（本周）」。\n\n我想复盘本周的训练:完成率、训练日数、消耗等关键数字,完成趋势,以及本周与上周的对比。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '我想复盘本周训练完成情况', 'data_fields': ["completion_rate", "training_days", "calories_burned", "trend", "delta_vs_last_week"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '健身计划',     'wake_word': '计划复盘（本月）',     'desc': '本月复盘(KPI + 趋势 + 上月对比)',
            'main_prompt': {
        'cli': 'python scripts/render_exercise_review_html.py --start <D1> --end <D2>', 'text': '请你加载技能 卡路里,执行唤醒词「计划复盘（本月）」。\n\n我想复盘本月的训练:完成率、训练日数、消耗等关键数字,完成趋势,以及本月与上月的对比。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_review_month', 'name': '计划复盘（本月）', 'subfunction': '计划复盘', 'output_type': 'result',
            'html_template': 'templates/exercise_review.html', 'data_source': 'python scripts/render_exercise_review_html.py --start <D1> --end <D2>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「计划复盘（本月）」。\n\n我想复盘本月的训练:完成率、训练日数、消耗等关键数字,完成趋势,以及本月与上月的对比。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '我想复盘本月训练完成情况', 'data_fields': ["completion_rate", "training_days", "calories_burned", "trend", "delta_vs_last_month"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '健身计划',     'wake_word': '计划复盘（全部）',     'desc': '全部复盘(总完成率 + 高频动作)',
            'main_prompt': {
        'cli': 'python scripts/render_exercise_review_html.py --start <D1> --end <D2>', 'text': '请你加载技能 卡路里,执行唤醒词「计划复盘（全部）」。\n\n我想复盘整个训练计划:总完成率,以及做得最多的动作(高频动作)排名。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_review_all', 'name': '计划复盘（全部）', 'subfunction': '计划复盘', 'output_type': 'result',
            'html_template': 'templates/exercise_review.html', 'data_source': 'python scripts/render_exercise_review_html.py --start <D1> --end <D2>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「计划复盘（全部）」。\n\n我想复盘整个训练计划:总完成率,以及做得最多的动作(高频动作)排名。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '我想复盘整个训练计划的总完成率和高频动作', 'data_fields': ["total_completion_rate", "top_movements"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '健身计划',     'wake_word': '看计划完成率',     'desc': '每周完成率折线趋势',
            'main_prompt': {
        'cli': 'python scripts/render_workout_plan.py --completion', 'text': '请你加载技能 卡路里,执行唤醒词「看计划完成率」。\n\n我想看训练计划的完成率趋势。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_completion_rate', 'name': '看计划完成率', 'subfunction': '计划复盘', 'output_type': 'result',
            'html_template': 'templates/workout_plan_view.html', 'data_source': 'python scripts/render_workout_plan.py --completion', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看计划完成率」。\n\n我想看训练计划的完成率趋势。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '我想看每周训练完成率的变化趋势', 'data_fields': ["weekly_completion", "trend"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '健身计划',     'wake_word': '看未完成训练',     'desc': '漏练日期 + 应练动作列表',
            'main_prompt': {
        'cli': 'python scripts/render_workout_plan.py --missed --days <N>', 'text': '请你加载技能 卡路里,执行唤醒词「看未完成训练」。\n\n我想看哪些天的训练没完成(漏练)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n时间范围(默认最近 4 周):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_missed', 'name': '看未完成训练', 'subfunction': '计划复盘', 'output_type': 'result',
            'html_template': 'templates/workout_plan_view.html', 'data_source': 'python scripts/render_workout_plan.py --missed --days <N>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看未完成训练」。\n\n我想看哪些天的训练没完成(漏练)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n时间范围(默认最近 4 周):____',
            'user_intent': '我想看哪些训练日漏练了', 'data_fields': ["missed_dates", "planned_movements"],
            'depends_on_external': False, 'order': 4},
    {
            'category': '健身计划',     'wake_word': '看动作完成率',     'desc': '动作完成率 TOP 榜',
            'main_prompt': {
        'cli': 'python scripts/render_workout_plan.py --movement-rate --days <N>', 'text': '请你加载技能 卡路里,执行唤醒词「看动作完成率」。\n\n我想看每个动作的完成率排名。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n时间范围(默认最近 4 周):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_movement_rate', 'name': '看动作完成率', 'subfunction': '计划复盘', 'output_type': 'result',
            'html_template': 'templates/workout_plan_view.html', 'data_source': 'python scripts/render_workout_plan.py --movement-rate --days <N>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看动作完成率」。\n\n我想看每个动作的完成率排名。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n时间范围(默认最近 4 周):____',
            'user_intent': '我想看各动作的完成率排名', 'data_fields': ["movement_ranking", "completion_rate"],
            'depends_on_external': False, 'order': 5},
    {
            'category': '健身计划',     'wake_word': '扫禁忌',     'desc': '禁忌动作扫描(腰/膝/肩 + 替代建议)',
            'main_prompt': {
        'cli': 'python scripts/render_contraindication.py', 'text': '请你加载技能 卡路里,执行唤醒词「扫禁忌」。\n\n我想检查训练计划里有没有伤腰/膝/肩的禁忌动作(默认全身位,也可以指定部位)。请列出有风险的动作、原因,以及推荐的替代动作。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n部位(腰/膝/肩,选填,默认全部):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_contraindication', 'name': '扫禁忌', 'subfunction': '安全检查', 'output_type': 'result',
            'html_template': 'templates/contraindication_report.html', 'data_source': 'python scripts/render_contraindication.py', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「扫禁忌」。\n\n我想检查训练计划里有没有伤腰/膝/肩的禁忌动作(默认全身位,也可以指定部位)。请列出有风险的动作、原因,以及推荐的替代动作。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n部位(腰/膝/肩,选填,默认全部):____',
            'user_intent': '我想检查训练计划里的禁忌动作', 'data_fields': ["part", "hits", "severity", "safe_variants"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '目标管理',     'wake_word': '定营养目标',     'desc': '设每日 4 项宏量营养目标',
            'main_prompt': {
        'cli': 'python scripts/render_goal_config.py --live', 'text': '请你加载技能 卡路里,执行唤醒词「定营养目标」。\n\n我想设每日 4 大宏量营养目标(热量/蛋白/碳水/脂肪)+ 饮水目标。若热量明显低于我的基础代谢(BMR),请提示我注意。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n我的目标数值(请按实际替换,不知道的可以空着):\n热量(卡):____\n蛋白(g):____\n碳水(g):____\n脂肪(g):____\n饮水(ml):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_set_nutrition', 'name': '定营养目标', 'subfunction': '定目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_config.html', 'data_source': 'python scripts/render_goal_config.py --live', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「定营养目标」。\n\n我想设每日 4 大宏量营养目标(热量/蛋白/碳水/脂肪)+ 饮水目标。若热量明显低于我的基础代谢(BMR),请提示我注意。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n我的目标数值(请按实际替换,不知道的可以空着):\n热量(卡):____\n蛋白(g):____\n碳水(g):____\n脂肪(g):____\n饮水(ml):____',
            'user_intent': '设每日 4 项宏量营养目标', 'data_fields': ["calorie_goal", "protein_goal", "carbs_goal", "fat_goal", "water_goal"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '目标管理',     'wake_word': '定营养目标(自动算)',     'desc': '按档案 + 策略自动算每日营养目标',
            'main_prompt': {
        'cli': 'python scripts/render_goal_recommend.py --profile <减脂/维持/增肌>', 'text': '请你加载技能 卡路里,执行唤醒词「定营养目标(自动算)」。\n\n想根据我的档案(身高/体重/年龄/活动量)+ 目标方向自动算出 4 项营养目标。若我未提供方向或档案信息缺失,请先询问补齐;若我已明确表达,直接计算,必要时做几句信息确认即可。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n我的目标方向(减脂 / 维持 / 增肌):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_set_nutrition_auto', 'name': '定营养目标(自动算)', 'subfunction': '定目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_recommend.html', 'data_source': 'python scripts/render_goal_recommend.py --profile <减脂/维持/增肌>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「定营养目标(自动算)」。\n\n想根据我的档案(身高/体重/年龄/活动量)+ 目标方向自动算出 4 项营养目标。若我未提供方向或档案信息缺失,请先询问补齐;若我已明确表达,直接计算,必要时做几句信息确认即可。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n我的目标方向(减脂 / 维持 / 增肌):____',
            'user_intent': '按档案 + 策略自动算每日营养目标', 'data_fields': ["tdee", "recommend", "weekly_rate", "macros_4", "basis", "plan_reasons"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '目标管理',     'wake_word': '定体重目标',     'desc': '设定体重目标值与可选截止日期',
            'main_prompt': {
        'cli': 'python scripts/render_goal_weight.py --mode basic --chain <思考链> → 写库后: python scripts/render_goal_weight.py --live --kg <目标> [--deadline <日期>] --scene basic --chain <思考链>(结果回执)', 'text': '请你加载技能 卡路里,执行唤醒词「定体重目标」。\n\n我想设定体重目标(目标 kg + 可选截止日期)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n我的体重目标(kg):____\n截止日期(选填):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_set_weight', 'name': '定体重目标', 'subfunction': '定目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_weight.html', 'data_source': 'python scripts/render_goal_weight.py --mode basic --chain <思考链> → 写库后: python scripts/render_goal_weight.py --live --kg <目标> [--deadline <日期>] --scene basic --chain <思考链>(结果回执)', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「定体重目标」。\n\n我想设定体重目标(目标 kg + 可选截止日期)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n我的体重目标(kg):____\n截止日期(选填):____',
            'user_intent': '设定体重目标值与可选截止日期', 'data_fields': ["current_weight", "target_weight", "deadline", "delta_kg", "suggested_rate"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '目标管理',     'wake_word': '定体重目标(自动算截止)',     'desc': '按速率推算截止日期的体重目标',
            'main_prompt': {
        'cli': 'python scripts/render_goal_weight.py --mode auto_deadline --chain <思考链> → 写库后: python scripts/render_goal_weight.py --live --kg <目标> --deadline <日期> --scene auto_deadline --chain <思考链>(结果回执)', 'text': '请你加载技能 卡路里,执行唤醒词「定体重目标(自动算截止)」。\n\n我想设定体重目标(目标 kg + 期望每周减重速率),由你自动推算合理截止日期,并校验速率是否合理(不超安全范围)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n我的体重目标(kg):____\n期望每周减重速率(kg/周):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_set_weight_auto_deadline', 'name': '定体重目标(自动算截止)', 'subfunction': '定目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_weight.html', 'data_source': 'python scripts/render_goal_weight.py --mode auto_deadline --chain <思考链> → 写库后: python scripts/render_goal_weight.py --live --kg <目标> --deadline <日期> --scene auto_deadline --chain <思考链>(结果回执)', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「定体重目标(自动算截止)」。\n\n我想设定体重目标(目标 kg + 期望每周减重速率),由你自动推算合理截止日期,并校验速率是否合理(不超安全范围)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n我的体重目标(kg):____\n期望每周减重速率(kg/周):____',
            'user_intent': '按速率推算截止日期的体重目标', 'data_fields': ["current_weight", "target_weight", "est_deadline", "rate_check"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '目标管理',     'wake_word': '定体重目标(含起始日)',     'desc': '完整 setup 体重目标含起始日',
            'main_prompt': {
        'cli': 'python scripts/render_goal_weight.py --mode with_start --chain <思考链> → 写库后: python scripts/render_goal_weight.py --live --kg <目标> --deadline <日期> [--start-kg <起点>] [--start-date <起始日>] --scene with_start --chain <思考链>(结果回执)', 'text': '请你加载技能 卡路里,执行唤醒词「定体重目标(含起始日)」。\n\n我想完整设定体重目标:目标 kg + 起始日 + 截止日 + 起点体重。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n我的体重目标(kg):____\n起始日:____\n截止日期:____\n起点体重(kg):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_set_weight_with_start', 'name': '定体重目标(含起始日)', 'subfunction': '定目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_weight.html', 'data_source': 'python scripts/render_goal_weight.py --mode with_start --chain <思考链> → 写库后: python scripts/render_goal_weight.py --live --kg <目标> --deadline <日期> [--start-kg <起点>] [--start-date <起始日>] --scene with_start --chain <思考链>(结果回执)', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「定体重目标(含起始日)」。\n\n我想完整设定体重目标:目标 kg + 起始日 + 截止日 + 起点体重。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n我的体重目标(kg):____\n起始日:____\n截止日期:____\n起点体重(kg):____',
            'user_intent': '完整 setup 体重目标含起始日', 'data_fields': ["weight_goal", "goal_deadline", "start_date", "start_weight"],
            'depends_on_external': False, 'order': 4},
    {
            'category': '目标管理',     'wake_word': '定饮水目标',     'desc': '设每日饮水目标',
            'main_prompt': {
        'cli': 'python scripts/render_goal_config.py --live --water-only', 'text': '请你加载技能 卡路里,执行唤醒词「定饮水目标」。\n\n我想设定每天饮水目标(ml)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n我的饮水目标(ml):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_set_water', 'name': '定饮水目标', 'subfunction': '定目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_config.html', 'data_source': 'python scripts/render_goal_config.py --live --water-only', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「定饮水目标」。\n\n我想设定每天饮水目标(ml)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n我的饮水目标(ml):____',
            'user_intent': '设每日饮水目标', 'data_fields': ["water_goal"],
            'depends_on_external': False, 'order': 5},
    {
            'category': '目标管理',     'wake_word': '定饮水目标(自动算)',     'desc': '按体重推算饮水目标推荐值',
            'main_prompt': {
        'cli': 'python scripts/render_goal_recommend.py --water-only', 'text': '请你加载技能 卡路里,执行唤醒词「定饮水目标(自动算)」。\n\n想按我的体重(ml/kg)自动推算饮水目标推荐值,并和旧目标对比。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n我的体重(kg,选填,默认取最新记录):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_set_water_auto', 'name': '定饮水目标(自动算)', 'subfunction': '定目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_recommend.html', 'data_source': 'python scripts/render_goal_recommend.py --water-only', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「定饮水目标(自动算)」。\n\n想按我的体重(ml/kg)自动推算饮水目标推荐值,并和旧目标对比。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n我的体重(kg,选填,默认取最新记录):____',
            'user_intent': '按体重推算饮水目标推荐值', 'data_fields': ["weight_kg", "season", "recommended_water_ml"],
            'depends_on_external': False, 'order': 6},
    {
            'category': '目标管理',     'wake_word': '一键定全套目标',     'desc': '一键设定营养+体重+饮水全套目标',
            'main_prompt': {
        'cli': 'python scripts/render_goal_recommend.py --full-kit --profile <减脂/维持/增肌>', 'text': '请你加载技能 卡路里,执行唤醒词「一键定全套目标」。\n\n想一键设定 3 类目标(营养 + 体重 + 饮水),基于我的档案自动计算,先给我看结果,等我确认后再采纳。若我的档案(身高/年龄/活动量)未设置、无体重记录或信息缺失,请先询问补齐;若我已明确表达,直接计算,必要时做几句信息确认即可。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n我的目标方向(减脂 / 维持 / 增肌):____\n我的体重目标(kg,选填):____\n截止日期(选填):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_set_full_kit', 'name': '一键定全套目标', 'subfunction': '定目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_recommend.html', 'data_source': 'python scripts/render_goal_recommend.py --full-kit --profile <减脂/维持/增肌>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「一键定全套目标」。\n\n想一键设定 3 类目标(营养 + 体重 + 饮水),基于我的档案自动计算,先给我看结果,等我确认后再采纳。若我的档案(身高/年龄/活动量)未设置、无体重记录或信息缺失,请先询问补齐;若我已明确表达,直接计算,必要时做几句信息确认即可。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n我的目标方向(减脂 / 维持 / 增肌):____\n我的体重目标(kg,选填):____\n截止日期(选填):____',
            'user_intent': '一键设定营养+体重+饮水全套目标', 'data_fields': ["calorie_goal", "protein_goal", "carbs_goal", "fat_goal", "water_goal", "weight_goal"],
            'depends_on_external': False, 'order': 7},
    {
            'category': '目标管理',     'wake_word': '看今日目标',     'desc': '看今日营养 4 项 + 饮水共 5 项目标完成度（体重为累计目标，引导到看体重目标进度）',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode today', 'text': '请你加载技能 卡路里,执行唤醒词「看今日目标」。\n\n我想看今日 5 项目标完成度(热量/蛋白/碳水/脂肪/饮水)。体重是累计目标,若我想看,请引导我到「看体重目标进度」。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_today', 'name': '看今日目标', 'subfunction': '看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode today', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看今日目标」。\n\n我想看今日 5 项目标完成度(热量/蛋白/碳水/脂肪/饮水)。体重是累计目标,若我想看,请引导我到「看体重目标进度」。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看今日营养 4 项 + 饮水共 5 项目标完成度（体重为累计目标，引导到看体重目标进度）', 'data_fields': ["calorie_goal", "protein_goal", "carbs_goal", "fat_goal", "water_goal", "actual", "pct"],
            'depends_on_external': False, 'order': 8},
    {
            'category': '目标管理',     'wake_word': '看本周目标',     'desc': '看本周目标完成度汇总',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode week', 'text': '请你加载技能 卡路里,执行唤醒词「看本周目标」。\n\n我想看本周目标完成情况(热量/蛋白/碳水/脂肪/饮水)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_week', 'name': '看本周目标', 'subfunction': '看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode week', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看本周目标」。\n\n我想看本周目标完成情况(热量/蛋白/碳水/脂肪/饮水)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看本周目标完成度汇总', 'data_fields': ["daily_avg", "daily_target", "week_total", "week_target"],
            'depends_on_external': False, 'order': 9},
    {
            'category': '目标管理',     'wake_word': '看营养目标进度',     'desc': '看 4 项营养目标进度',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode nutrition', 'text': '请你加载技能 卡路里,执行唤醒词「看营养目标进度」。\n\n我想看 4 项营养目标(热量/蛋白/碳水/脂肪)的完成进度。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_nutrition_progress', 'name': '看营养目标进度', 'subfunction': '看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode nutrition', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看营养目标进度」。\n\n我想看 4 项营养目标(热量/蛋白/碳水/脂肪)的完成进度。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看 4 项营养目标进度', 'data_fields': ["calorie_rate", "protein_rate", "carbs_rate", "fat_rate", "calorie_gap"],
            'depends_on_external': False, 'order': 10},
    {
            'category': '目标管理',     'wake_word': '看体重目标进度',     'desc': '看体重目标进度含预估达成',
            'main_prompt': {
        'cli': 'python scripts/calorie_tracker.py weight-goal-progress', 'text': '请你加载技能 卡路里,执行唤醒词「看体重目标进度」。\n\n我想看体重目标进度。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_weight_progress', 'name': '看体重目标进度', 'subfunction': '看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/calorie_tracker.py weight-goal-progress', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重目标进度」。\n\n我想看体重目标进度。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重目标进度含预估达成', 'data_fields': ["current", "target", "delta", "pct", "predict_date", "days_left", "suggested_rate"],
            'depends_on_external': False, 'order': 11},
    {
            'category': '目标管理',     'wake_word': '看饮水目标进度',     'desc': '看饮水目标进度',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode water', 'text': '请你加载技能 卡路里,执行唤醒词「看饮水目标进度」。\n\n我想看今日饮水进度。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_water_progress', 'name': '看饮水目标进度', 'subfunction': '看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode water', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看饮水目标进度」。\n\n我想看今日饮水进度。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看饮水目标进度', 'data_fields': ["cumulative", "target", "pct", "remaining_ml"],
            'depends_on_external': False, 'order': 12},
    {
            'category': '目标管理',     'wake_word': '看目标对比实际',     'desc': '看目标线 vs 实际线折线对比',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode vs_actual', 'text': '请你加载技能 卡路里,执行唤醒词「看目标对比实际」。\n\n我想看热量目标线 vs 实际摄入线的对比与偏差分析,默认最近 30 天(可自定义时间窗口)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n时间窗口(天,选填,默认 30):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_vs_actual', 'name': '看目标对比实际', 'subfunction': '看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode vs_actual', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看目标对比实际」。\n\n我想看热量目标线 vs 实际摄入线的对比与偏差分析,默认最近 30 天(可自定义时间窗口)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n时间窗口(天,选填,默认 30):____',
            'user_intent': '看目标线 vs 实际线折线对比', 'data_fields': ["daily_calorie_goal", "daily_calorie_actual", "deviation_pct"],
            'depends_on_external': False, 'order': 13},
    {
            'category': '目标管理',     'wake_word': '看目标完成度',     'desc': '查看全部目标完成度 + 缺口绝对值 + 总评分',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode completion', 'text': '请你加载技能 卡路里,执行唤醒词「看目标完成度」。\n\n我想看全部目标完成度汇总(热量/蛋白/碳水/脂肪/饮水)和总评分。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_completion', 'name': '看目标完成度（含缺口）', 'subfunction': '看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode completion', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看目标完成度」。\n\n我想看全部目标完成度汇总(热量/蛋白/碳水/脂肪/饮水)和总评分。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '查看全部目标完成度 + 缺口绝对值 + 总评分', 'data_fields': ["pct", "gap", "total_score"],
            'depends_on_external': False, 'order': 14},
    {
            'category': '目标管理',     'wake_word': '看即将到期的目标',     'desc': '看即将到期的目标列表',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode weight --expiring 14', 'text': '请你加载技能 卡路里,执行唤醒词「看即将到期的目标」。\n\n我想看即将到期的体重目标(默认 14 天内到期)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n到期窗口(天,选填,默认 14):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_expiring', 'name': '看即将到期的目标', 'subfunction': '看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode weight --expiring 14', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看即将到期的目标」。\n\n我想看即将到期的体重目标(默认 14 天内到期)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n到期窗口(天,选填,默认 14):____',
            'user_intent': '看即将到期的目标列表', 'data_fields': ["weight_goal", "deadline", "days_left", "current_weight", "completion_pct", "urgency"],
            'depends_on_external': False, 'order': 15},
    {
            'category': '目标管理',     'wake_word': '看目标完成率(按周)',     'desc': '看本周营养目标每日完成率',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode nutrition --period week', 'text': '请你加载技能 卡路里,执行唤醒词「看目标完成率(按周)」。\n\n我想看本周(7 天)每日目标完成率 + 达标天数(达标带 80%-120%)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_completion_rate_week', 'name': '看目标完成率(按周)', 'subfunction': '看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode nutrition --period week', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看目标完成率(按周)」。\n\n我想看本周(7 天)每日目标完成率 + 达标天数(达标带 80%-120%)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看本周营养目标每日完成率', 'data_fields': ["week_daily_rate", "week_complete_days", "week_avg_rate"],
            'depends_on_external': False, 'order': 16},
    {
            'category': '目标管理',     'wake_word': '看目标完成率(按月)',     'desc': '看本月营养目标每日完成率',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode nutrition --period month', 'text': '请你加载技能 卡路里,执行唤醒词「看目标完成率(按月)」。\n\n我想看本月(30 天)每日目标完成率 + 达标天数(达标带 80%-120%)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_completion_rate_month', 'name': '看目标完成率(按月)', 'subfunction': '看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode nutrition --period month', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看目标完成率(按月)」。\n\n我想看本月(30 天)每日目标完成率 + 达标天数(达标带 80%-120%)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看本月营养目标每日完成率', 'data_fields': ["month_daily_rate", "month_complete_days", "month_avg_rate"],
            'depends_on_external': False, 'order': 17},
    {
            'category': '目标管理',     'wake_word': '改营养目标',     'desc': '改某项或全部营养目标',
            'main_prompt': {
        'cli': 'python scripts/render_goal_config.py --modify-nutrition', 'text': '请你加载技能 卡路里,执行唤醒词「改营养目标」。\n\n我想修改营养目标(热量/蛋白/碳水/脂肪/饮水),可同时改多项,并预估修改后的影响(热量缺口/预算变化)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n我要改的项(每行一项,不改的留空):\n热量(卡)新目标值:____\n蛋白(g)新目标值:____\n碳水(g)新目标值:____\n脂肪(g)新目标值:____\n饮水(ml)新目标值:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_modify_nutrition', 'name': '改营养目标', 'subfunction': '改目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_config.html', 'data_source': 'python scripts/render_goal_config.py --modify-nutrition', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改营养目标」。\n\n我想修改营养目标(热量/蛋白/碳水/脂肪/饮水),可同时改多项,并预估修改后的影响(热量缺口/预算变化)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n我要改的项(每行一项,不改的留空):\n热量(卡)新目标值:____\n蛋白(g)新目标值:____\n碳水(g)新目标值:____\n脂肪(g)新目标值:____\n饮水(ml)新目标值:____',
            'user_intent': '改某项或全部营养目标', 'data_fields': ["old_calorie_goal", "new_calorie_goal", "old_protein_goal", "new_protein_goal", "old_water_goal", "new_water_goal"],
            'depends_on_external': False, 'order': 18},
    {
            'category': '目标管理',     'wake_word': '改体重目标',     'desc': '改体重目标含截止日',
            'main_prompt': {
        'cli': 'python scripts/render_goal_weight.py --mode modify --chain <思考链> → 写库后: python scripts/render_goal_weight.py --live --kg <新目标> [--deadline <新截止>] --scene modify --chain <思考链>(结果回执)', 'text': '请你加载技能 卡路里,执行唤醒词「改体重目标」。\n\n我想修改体重目标值或截止日期,并给出新的建议减重速率。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n我要改的项(每行一项,不改的留空):\n体重目标(kg):____\n截止日期:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_modify_weight', 'name': '改体重目标', 'subfunction': '改目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_weight.html', 'data_source': 'python scripts/render_goal_weight.py --mode modify --chain <思考链> → 写库后: python scripts/render_goal_weight.py --live --kg <新目标> [--deadline <新截止>] --scene modify --chain <思考链>(结果回执)', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改体重目标」。\n\n我想修改体重目标值或截止日期,并给出新的建议减重速率。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n我要改的项(每行一项,不改的留空):\n体重目标(kg):____\n截止日期:____',
            'user_intent': '改体重目标含截止日', 'data_fields': ["old_weight_goal", "new_weight_goal", "old_deadline", "new_deadline"],
            'depends_on_external': False, 'order': 19},
    {
            'category': '目标管理',     'wake_word': '改饮水目标',     'desc': '单独改饮水目标',
            'main_prompt': {
        'cli': 'python scripts/render_goal_config.py --modify-water', 'text': '请你加载技能 卡路里,执行唤醒词「改饮水目标」。\n\n我想单独修改饮水目标,其他营养目标保持不变。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n饮水目标(ml):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_modify_water', 'name': '改饮水目标', 'subfunction': '改目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_config.html', 'data_source': 'python scripts/render_goal_config.py --modify-water', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改饮水目标」。\n\n我想单独修改饮水目标,其他营养目标保持不变。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n饮水目标(ml):____',
            'user_intent': '单独改饮水目标', 'data_fields': ["old_water_goal", "new_water_goal"],
            'depends_on_external': False, 'order': 20},
    {
            'category': '目标管理',     'wake_word': '暂停所有目标',     'desc': '临时暂停全部目标',
            'main_prompt': {
        'cli': 'python scripts/render_goal_status.py --status paused', 'text': '请你加载技能 卡路里,执行唤醒词「暂停所有目标」。\n\n我想临时冻结全部目标(营养 + 体重 + 饮水),记录照常,仅目标暂停,并提示恢复入口。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_pause_all', 'name': '暂停所有目标', 'subfunction': '改目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_status.html', 'data_source': 'python scripts/render_goal_status.py --status paused', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「暂停所有目标」。\n\n我想临时冻结全部目标(营养 + 体重 + 饮水),记录照常,仅目标暂停,并提示恢复入口。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '临时暂停全部目标', 'data_fields': ["paused", "note", "restore_hint"],
            'depends_on_external': False, 'order': 21},
    {
            'category': '目标管理',     'wake_word': '重启所有目标',     'desc': '从暂停恢复全部目标',
            'main_prompt': {
        'cli': 'python scripts/render_goal_status.py --status resumed', 'text': '请你加载技能 卡路里,执行唤醒词「重启所有目标」。\n\n我想从暂停恢复全部目标(营养 + 体重 + 饮水)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_resume_all', 'name': '重启所有目标', 'subfunction': '改目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_status.html', 'data_source': 'python scripts/render_goal_status.py --status resumed', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「重启所有目标」。\n\n我想从暂停恢复全部目标(营养 + 体重 + 饮水)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '从暂停恢复全部目标', 'data_fields': ["resume_state", "resumed_at"],
            'depends_on_external': False, 'order': 22},
    {
            'category': '目标管理',     'wake_word': '看目标历史完成',     'desc': '看历史目标完成情况',
            'main_prompt': {
        'cli': 'goal_history.list_completed_goals', 'text': '请你加载技能 卡路里,执行唤醒词「看目标历史完成」。\n\n我想看历史目标达成情况,含每日达成列表与完成/未完成天数统计(达标带 80%-120%)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n回看天数(选填,默认 30):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_history_complete', 'name': '看目标历史完成', 'subfunction': '看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'goal_history.list_completed_goals', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看目标历史完成」。\n\n我想看历史目标达成情况,含每日达成列表与完成/未完成天数统计(达标带 80%-120%)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n回看天数(选填,默认 30):____',
            'user_intent': '看历史目标完成情况', 'data_fields': ["goal_history", "completed_count", "incomplete_count"],
            'depends_on_external': False, 'order': 23},
    {
            'category': '目标管理',     'wake_word': '看目标预测达成',     'desc': '预测目标达成日 + 置信度（体重部分复用对比体重 B1 的预测）',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode predict', 'text': '请你加载技能 卡路里,执行唤醒词「看目标预测达成」。\n\n我想看按当前趋势预测的目标达成日与置信度(体重部分复用对比体重的预测逻辑)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_predict', 'name': '看目标预测达成', 'subfunction': '看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode predict', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看目标预测达成」。\n\n我想看按当前趋势预测的目标达成日与置信度(体重部分复用对比体重的预测逻辑)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '预测目标达成日 + 置信度（体重部分复用对比体重 B1 的预测）', 'data_fields': ["predict_date", "confidence"],
            'depends_on_external': False, 'order': 24},

    {
            'category': '基础信息',     'wake_word': '设置档案',     'desc': '设置基础档案(身高/年龄/性别/活动量)',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-profile-set --age <A> --gender <G> --height <H> --activity <L> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「设置档案」。\n\n我想设置基础档案(身高/年龄/性别/活动量)。如果我没说全,请一项一项问我,并根据我的日常情况推荐合适的活动量。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n我的身高(cm):____\n年龄:____\n性别(男/女):____\n日常活动情况(选填,用于推荐活动量):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'profile_setup', 'name': '设置档案', 'subfunction': '设置资料', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-profile-set --age <A> --gender <G> --height <H> --activity <L> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「设置档案」。\n\n我想设置基础档案(身高/年龄/性别/活动量)。如果我没说全,请一项一项问我,并根据我的日常情况推荐合适的活动量。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n我的身高(cm):____\n年龄:____\n性别(男/女):____\n日常活动情况(选填,用于推荐活动量):____',
            'user_intent': '设置基础档案(身高/年龄/性别/活动量)', 'data_fields': ["height_cm", "age", "gender", "activity_level", "activity_factor", "created_at"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '基础信息',     'wake_word': '设活动量',     'desc': '单独设置活动量',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-profile-activity <level> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「设活动量」。\n\n我要单独设置活动量(久坐/轻度/中度/活跃/高度活跃)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n我的活动量(久坐/轻度/中度/活跃/高度活跃):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'profile_set_activity', 'name': '设活动量', 'subfunction': '设置资料', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-profile-activity <level> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「设活动量」。\n\n我要单独设置活动量(久坐/轻度/中度/活跃/高度活跃)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n我的活动量(久坐/轻度/中度/活跃/高度活跃):____',
            'user_intent': '单独设置活动量', 'data_fields': ["activity_level", "activity_factor", "tdee"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '基础信息',     'wake_word': '改档案',     'desc': '修改档案中的某个字段',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-profile-update --field <X> --value <Y> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「改档案」。\n\n我要改档案里的字段(身高/年龄/性别/活动量/备注)。改之前请先确认我原来的值。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n我要改的字段(允许一行一条,可改多个):\n身高(新值):____\n年龄(新值):____\n性别(新值):____\n活动量(新值):____\n备注(新值):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'profile_update', 'name': '改档案', 'subfunction': '改资料', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-profile-update --field <X> --value <Y> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改档案」。\n\n我要改档案里的字段(身高/年龄/性别/活动量/备注)。改之前请先确认我原来的值。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n我要改的字段(允许一行一条,可改多个):\n身高(新值):____\n年龄(新值):____\n性别(新值):____\n活动量(新值):____\n备注(新值):____',
            'user_intent': '修改档案中的某个字段', 'data_fields': ["height_cm", "age", "gender", "activity_level", "note", "bmi", "tdee"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '基础信息',     'wake_word': '查档案',     'desc': '查看档案及最新体重与身体指标',
            'main_prompt': {
        'cli': 'python scripts/render_crud_view.py --entity profile --chain "1.识别→2.读DB→3.算TDEE"', 'text': '请你加载技能 卡路里,执行唤醒词「查档案」。\n\n我想看自己的完整档案。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'profile_view', 'name': '查档案', 'subfunction': '看档案', 'output_type': 'result',
            'html_template': 'templates/crud_view.html', 'data_source': 'python scripts/render_crud_view.py --entity profile --chain "1.识别→2.读DB→3.算TDEE"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「查档案」。\n\n我想看自己的完整档案。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '查看档案及最新体重与身体指标', 'data_fields': ["height_cm", "age", "gender", "activity_level", "activity_factor", "weight_kg", "bmi", "bmr", "tdee"],
            'depends_on_external': False, 'order': 0},

    {
            'category': '身体细节',     'wake_word': '记体脂（皮褶钳）',     'desc': '我想用手持皮褶钳测 7 点并自动算体脂率存档',
            'main_prompt': {
        'cli': 'python scripts/render_body_composition_wizard.py --caliper-chest-mm <C> --caliper-abdominal-mm <A> --caliper-thigh-mm <T> --caliper-tricep-mm <T> --caliper-subscapular-mm <S> --caliper-suprailiac-mm <I> --caliper-midaxillary-mm <M> --age <A> --sex <男/女>', 'text': '请你加载技能 卡路里,执行唤醒词「记体脂（皮褶钳）」。\n\n我用皮褶钳测了 7 点(胸/腹/大腿/三头/肩胛下/髂上/腋中 mm),请按 Jackson-Pollock 7 点法帮我算体脂率并记录。如果我没说性别/年龄,请先问我。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n7 点皮褶厚度(mm):\n胸:____\n腹:____\n大腿:____\n三头:____\n肩胛下:____\n髂上:____\n腋中:____\n性别(男/女):____\n年龄:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_comp_add_caliper', 'name': '记体脂（皮褶钳）', 'subfunction': '记身体细节', 'output_type': 'receipt',
            'html_template': 'templates/body_composition_wizard.html', 'data_source': 'python scripts/render_body_composition_wizard.py --caliper-chest-mm <C> --caliper-abdominal-mm <A> --caliper-thigh-mm <T> --caliper-tricep-mm <T> --caliper-subscapular-mm <S> --caliper-suprailiac-mm <I> --caliper-midaxillary-mm <M> --age <A> --sex <男/女>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「记体脂（皮褶钳）」。\n\n我用皮褶钳测了 7 点(胸/腹/大腿/三头/肩胛下/髂上/腋中 mm),请按 Jackson-Pollock 7 点法帮我算体脂率并记录。如果我没说性别/年龄,请先问我。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n7 点皮褶厚度(mm):\n胸:____\n腹:____\n大腿:____\n三头:____\n肩胛下:____\n髂上:____\n腋中:____\n性别(男/女):____\n年龄:____',
            'user_intent': '我想用手持皮褶钳测 7 点并自动算体脂率存档', 'data_fields': ["caliper_chest_mm", "caliper_abdominal_mm", "caliper_thigh_mm", "caliper_tricep_mm", "caliper_subscapular_mm", "caliper_suprailiac_mm", "caliper_midaxillary_mm", "body_fat_pct", "age", "sex", "source"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '身体细节',     'wake_word': '记体脂（外部测量）',     'desc': '我想记录外部设备(健身房/医院)测的体脂率',
            'main_prompt': {
        'cli': 'python scripts/render_body_composition_wizard.py --source <健身房/医院/其他> --body-fat-pct <P> --date <D>', 'text': '请你加载技能 卡路里,执行唤醒词「记体脂（外部测量）」。\n\n我用外部设备(健身房 InBody/医院/其他)测了体脂率,请帮我记录体脂率和来源、日期。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n体脂率(%):____\n来源(健身房/医院/其他):____\n日期:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_comp_add_external', 'name': '记体脂（外部测量）', 'subfunction': '记身体细节', 'output_type': 'receipt',
            'html_template': 'templates/body_composition_wizard.html', 'data_source': 'python scripts/render_body_composition_wizard.py --source <健身房/医院/其他> --body-fat-pct <P> --date <D>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「记体脂（外部测量）」。\n\n我用外部设备(健身房 InBody/医院/其他)测了体脂率,请帮我记录体脂率和来源、日期。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n体脂率(%):____\n来源(健身房/医院/其他):____\n日期:____',
            'user_intent': '我想记录外部设备(健身房/医院)测的体脂率', 'data_fields': ["body_fat_pct", "source", "date"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '身体细节',     'wake_word': '记围度',     'desc': '我想记录身体围度(13 项,可部分填写)',
            'main_prompt': {
        'cli': 'python scripts/render_body_measurements_wizard.py --chest-cm <C> --waist-cm <W> --abdomen-cm <A> --hip-cm <H> --shoulder-cm <S> --left-thigh-cm <LT> --right-thigh-cm <RT> --left-calf-cm <LC> --right-calf-cm <RC> --left-arm-cm <LA> --right-arm-cm <RA> --left-forearm-cm <LF> --right-forearm-cm <RF>', 'text': '请你加载技能 卡路里,执行唤醒词「记围度」。\n\n我量了身体围度,请帮我记录 13 项围度(胸/腰/腹/臀/肩/大腿/小腿/手臂/前臂,左+右),量了哪项填哪项,没量的留空。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n胸围(cm):____\n腰围(cm):____\n腹围(cm):____\n臀围(cm):____\n肩围(cm):____\n左大腿(cm):____\n右大腿(cm):____\n左小腿(cm):____\n右小腿(cm):____\n左上臂(cm):____\n右上臂(cm):____\n左前臂(cm):____\n右前臂(cm):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_meas_add', 'name': '记围度', 'subfunction': '记身体细节', 'output_type': 'receipt',
            'html_template': 'templates/body_measurements_wizard.html', 'data_source': 'python scripts/render_body_measurements_wizard.py --chest-cm <C> --waist-cm <W> --abdomen-cm <A> --hip-cm <H> --shoulder-cm <S> --left-thigh-cm <LT> --right-thigh-cm <RT> --left-calf-cm <LC> --right-calf-cm <RC> --left-arm-cm <LA> --right-arm-cm <RA> --left-forearm-cm <LF> --right-forearm-cm <RF>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「记围度」。\n\n我量了身体围度,请帮我记录 13 项围度(胸/腰/腹/臀/肩/大腿/小腿/手臂/前臂,左+右),量了哪项填哪项,没量的留空。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n胸围(cm):____\n腰围(cm):____\n腹围(cm):____\n臀围(cm):____\n肩围(cm):____\n左大腿(cm):____\n右大腿(cm):____\n左小腿(cm):____\n右小腿(cm):____\n左上臂(cm):____\n右上臂(cm):____\n左前臂(cm):____\n右前臂(cm):____',
            'user_intent': '我想记录身体围度(13 项,可部分填写)', 'data_fields': ["chest_cm", "waist_cm", "abdomen_cm", "hip_cm", "shoulder_cm", "left_thigh_cm", "right_thigh_cm", "left_calf_cm", "right_calf_cm", "left_arm_cm", "right_arm_cm", "left_forearm_cm", "right_forearm_cm", "date"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '身体细节',     'wake_word': '补记体脂',     'desc': '我想补录过去某天的体脂测量',
            'main_prompt': {
        'cli': 'python scripts/render_body_composition_wizard.py --date <D> --body-fat-pct <P> --source <皮褶钳/健身房/医院/其他>', 'text': '请你加载技能 卡路里,执行唤醒词「补记体脂」。\n\n我要补录之前某天的体脂测量(不是今天的)。如果那天已有记录,请先告诉我冲突再确认。补完后可以问我还要不要补其他日期。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n体脂率(%):____\n来源(皮褶钳/健身房/医院/其他):____\n日期:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_comp_backfill', 'name': '补记体脂', 'subfunction': '记身体细节', 'output_type': 'receipt',
            'html_template': 'templates/body_composition_wizard.html', 'data_source': 'python scripts/render_body_composition_wizard.py --date <D> --body-fat-pct <P> --source <皮褶钳/健身房/医院/其他>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「补记体脂」。\n\n我要补录之前某天的体脂测量(不是今天的)。如果那天已有记录,请先告诉我冲突再确认。补完后可以问我还要不要补其他日期。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n体脂率(%):____\n来源(皮褶钳/健身房/医院/其他):____\n日期:____',
            'user_intent': '我想补录过去某天的体脂测量', 'data_fields': ["date", "body_fat_pct", "source", "conflict"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '身体细节',     'wake_word': '补记围度',     'desc': '我想补录过去某天的围度测量',
            'main_prompt': {
        'cli': 'python scripts/render_body_measurements_wizard.py --date <D> --waist-cm <W> --hip-cm <H>', 'text': '请你加载技能 卡路里,执行唤醒词「补记围度」。\n\n我要补录之前某天的围度测量(不是今天的)。如果那天已有记录,请先告诉我冲突再确认。补完后可以问我还要不要补其他日期。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n各围度(cm,量了哪项填哪项):\n胸围:____\n腰围:____\n腹围:____\n臀围:____\n肩围:____\n左大腿:____\n右大腿:____\n左小腿:____\n右小腿:____\n左上臂:____\n右上臂:____\n左前臂:____\n右前臂:____\n日期:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_meas_backfill', 'name': '补记围度', 'subfunction': '记身体细节', 'output_type': 'receipt',
            'html_template': 'templates/body_measurements_wizard.html', 'data_source': 'python scripts/render_body_measurements_wizard.py --date <D> --waist-cm <W> --hip-cm <H>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「补记围度」。\n\n我要补录之前某天的围度测量(不是今天的)。如果那天已有记录,请先告诉我冲突再确认。补完后可以问我还要不要补其他日期。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n各围度(cm,量了哪项填哪项):\n胸围:____\n腰围:____\n腹围:____\n臀围:____\n肩围:____\n左大腿:____\n右大腿:____\n左小腿:____\n右小腿:____\n左上臂:____\n右上臂:____\n左前臂:____\n右前臂:____\n日期:____',
            'user_intent': '我想补录过去某天的围度测量', 'data_fields': ["date", "chest_cm", "waist_cm", "abdomen_cm", "hip_cm", "shoulder_cm", "conflict"],
            'depends_on_external': False, 'order': 4},
    {
            'category': '身体细节',     'wake_word': '看体脂',     'desc': '我想看历史体脂记录并可按来源筛选',
            'main_prompt': {
        'cli': 'python scripts/render_body_composition_view.py --mode list --source <皮褶钳/健身房/医院/全部> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看体脂」。\n\n我想看历史体脂记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_comp_list', 'name': '看体脂', 'subfunction': '看身体细节', 'output_type': 'result',
            'html_template': 'templates/body_composition_view.html', 'data_source': 'python scripts/render_body_composition_view.py --mode list --source <皮褶钳/健身房/医院/全部> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体脂」。\n\n我想看历史体脂记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '我想看历史体脂记录并可按来源筛选', 'data_fields': ["date", "body_fat_pct", "source", "source_filter", "current"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '身体细节',     'wake_word': '看体脂趋势',     'desc': '我想看体脂率趋势(默认最近来源,可切换)',
            'main_prompt': {
        'cli': 'python scripts/render_body_composition_view.py --mode trend --source <默认最近来源> --days 90 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看体脂趋势」。\n\n我想看体脂率趋势,默认用我最近用的来源,也可以切换来源。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_comp_trend', 'name': '看体脂趋势', 'subfunction': '看身体细节', 'output_type': 'result',
            'html_template': 'templates/body_composition_view.html', 'data_source': 'python scripts/render_body_composition_view.py --mode trend --source <默认最近来源> --days 90 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体脂趋势」。\n\n我想看体脂率趋势,默认用我最近用的来源,也可以切换来源。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '我想看体脂率趋势(默认最近来源,可切换)', 'data_fields': ["source", "trend", "delta", "avg", "min"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '身体细节',     'wake_word': '看围度',     'desc': '我想看历史围度记录并可按部位筛选',
            'main_prompt': {
        'cli': 'python scripts/render_body_measurements_view.py --mode list --metric <部位> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看围度」。\n\n我想看历史围度记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_meas_list', 'name': '看围度', 'subfunction': '看身体细节', 'output_type': 'result',
            'html_template': 'templates/body_measurements_view.html', 'data_source': 'python scripts/render_body_measurements_view.py --mode list --metric <部位> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看围度」。\n\n我想看历史围度记录。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '我想看历史围度记录并可按部位筛选', 'data_fields': ["date", "measurements", "metric_filter"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '身体细节',     'wake_word': '看围度趋势',     'desc': '我想看某部位围度的变化趋势',
            'main_prompt': {
        'cli': 'python scripts/render_body_measurements_view.py --mode trend --metric <部位> --days 90 --chain "1.识别→2.选部位→3.读DB→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看围度趋势」。\n\n我想看某个部位的围度变化。请先让我选部位。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_meas_trend', 'name': '看围度趋势', 'subfunction': '看身体细节', 'output_type': 'result',
            'html_template': 'templates/body_measurements_view.html', 'data_source': 'python scripts/render_body_measurements_view.py --mode trend --metric <部位> --days 90 --chain "1.识别→2.选部位→3.读DB→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看围度趋势」。\n\n我想看某个部位的围度变化。请先让我选部位。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '我想看某部位围度的变化趋势', 'data_fields': ["metric", "trend", "delta_summary"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '身体细节',     'wake_word': '对比体脂',     'desc': '我想对比两段时间的体脂变化',
            'main_prompt': {
        'cli': 'python scripts/render_body_composition_view.py --mode compare --start1 <D1> --end1 <D2> --start2 <D3> --end2 <D4> --source <来源> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体脂」。\n\n我想对比两次体脂测量,第一次和第二次都可以给具体日期或一段时间。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n第一次(日期或时间段):____\n第二次(日期或时间段):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_comp_compare', 'name': '对比体脂', 'subfunction': '比身体细节', 'output_type': 'result',
            'html_template': 'templates/body_composition_view.html', 'data_source': 'python scripts/render_body_composition_view.py --mode compare --start1 <D1> --end1 <D2> --start2 <D3> --end2 <D4> --source <来源> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体脂」。\n\n我想对比两次体脂测量,第一次和第二次都可以给具体日期或一段时间。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n第一次(日期或时间段):____\n第二次(日期或时间段):____',
            'user_intent': '我想对比两段时间的体脂变化', 'data_fields': ["period1", "period2", "delta", "pct_change", "source"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '身体细节',     'wake_word': '对比围度',     'desc': '我想对比两个日期的围度变化',
            'main_prompt': {
        'cli': 'python scripts/render_body_measurements_view.py --mode compare --date1 <D1> --date2 <D2> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比围度」。\n\n我想对比两次围度测量。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n第一次日期:____\n第二次日期:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_meas_compare', 'name': '对比围度', 'subfunction': '比身体细节', 'output_type': 'result',
            'html_template': 'templates/body_measurements_view.html', 'data_source': 'python scripts/render_body_measurements_view.py --mode compare --date1 <D1> --date2 <D2> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比围度」。\n\n我想对比两次围度测量。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n第一次日期:____\n第二次日期:____',
            'user_intent': '我想对比两个日期的围度变化', 'data_fields': ["date1", "date2", "deltas"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '身体细节',     'wake_word': '删体脂',     'desc': '我想删除一条体脂记录',
            'main_prompt': {
        'cli': 'python scripts/render_body_delete_receipt.py --entity composition --id <ID> --chain "1.列候选→2.确认→3.删除→4.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「删体脂」。\n\n我要删一条体脂记录。如果我没说清是哪条,请先列出最近的几条记录(日期/体脂率/来源)让我选。确认后,删除前先给我看这条记录的内容,确认无误再删,最后给我确认回执。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n要删的记录(选填,如「最近一条」或日期):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_comp_delete', 'name': '删体脂', 'subfunction': '删身体细节', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_body_delete_receipt.py --entity composition --id <ID> --chain "1.列候选→2.确认→3.删除→4.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「删体脂」。\n\n我要删一条体脂记录。如果我没说清是哪条,请先列出最近的几条记录(日期/体脂率/来源)让我选。确认后,删除前先给我看这条记录的内容,确认无误再删,最后给我确认回执。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n要删的记录(选填,如「最近一条」或日期):____',
            'user_intent': '我想删除一条体脂记录', 'data_fields': ["id", "date", "body_fat_pct", "source", "snapshot"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '身体细节',     'wake_word': '删围度',     'desc': '我想删除一条围度记录',
            'main_prompt': {
        'cli': 'python scripts/render_body_delete_receipt.py --entity measurements --id <ID> --chain "1.列候选→2.确认→3.删除→4.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「删围度」。\n\n我要删一条围度记录。如果我没说清是哪条,请先列出最近的几条记录(日期/各围度)让我选。确认后,删除前先给我看这条记录的内容,确认无误再删,最后给我确认回执。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n要删的记录(选填,如「最近一条」或日期):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_meas_delete', 'name': '删围度', 'subfunction': '删身体细节', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_body_delete_receipt.py --entity measurements --id <ID> --chain "1.列候选→2.确认→3.删除→4.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「删围度」。\n\n我要删一条围度记录。如果我没说清是哪条,请先列出最近的几条记录(日期/各围度)让我选。确认后,删除前先给我看这条记录的内容,确认无误再删,最后给我确认回执。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n要删的记录(选填,如「最近一条」或日期):____',
            'user_intent': '我想删除一条围度记录', 'data_fields': ["id", "date", "measurements", "snapshot"],
            'depends_on_external': False, 'order': 1},

    {
            'category': '身材照片',     'wake_word': '记身材照',     'desc': '存一张身材照(发图/路径双模式)',
            'main_prompt': {
        'cli': 'python scripts/render_body_photo_receipt.py --live-add <照片路径> --tag <标签> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「记身材照」。\n\n我要存一张身材照。你可以直接发照片给我(手机/飞书),也可以告诉我照片文件路径(电脑)。如果标签没说,请问我。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n标签(如 正面/侧面/背部):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_photo_add_single', 'name': '存一张照片', 'subfunction': '存身材照', 'output_type': 'receipt',
            'html_template': 'templates/body_photo_receipt.html', 'data_source': 'python scripts/render_body_photo_receipt.py --live-add <照片路径> --tag <标签> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「记身材照」。\n\n我要存一张身材照。你可以直接发照片给我(手机/飞书),也可以告诉我照片文件路径(电脑)。如果标签没说,请问我。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n标签(如 正面/侧面/背部):____',
            'user_intent': '存一张身材照并预览回执', 'data_fields': ["photo_path", "tag_list", "date", "distance_days", "note"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '身材照片',     'wake_word': '记身材照',     'desc': '存一张带备注的身材照',
            'main_prompt': {
        'cli': 'python scripts/render_body_photo_receipt.py --live-add <照片路径> --tag <标签> --note <备注> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「记身材照」。\n\n我要存一张身材照并附备注(比如当时的状态/饮食阶段)。你可以直接发照片给我(手机/飞书),也可以告诉我照片文件路径(电脑)。如果标签没说,请问我。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n标签(如 正面/侧面/背部):____\n备注:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_photo_add_note', 'name': '存照片（含备注）', 'subfunction': '存身材照', 'output_type': 'receipt',
            'html_template': 'templates/body_photo_receipt.html', 'data_source': 'python scripts/render_body_photo_receipt.py --live-add <照片路径> --tag <标签> --note <备注> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「记身材照」。\n\n我要存一张身材照并附备注(比如当时的状态/饮食阶段)。你可以直接发照片给我(手机/飞书),也可以告诉我照片文件路径(电脑)。如果标签没说,请问我。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n标签(如 正面/侧面/背部):____\n备注:____',
            'user_intent': '存一张带备注的身材照', 'data_fields': ["photo_path", "tag_list", "date", "note", "distance_days"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '身材照片',     'wake_word': '记身材照',     'desc': '批量存多张身材照(逐张状态明细)',
            'main_prompt': {
        'cli': 'python scripts/render_body_photo_receipt.py --live-add <照片1> <照片2> ... --tag <标签> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「记身材照」。\n\n我要一次性存多张身材照(可连发多张照片,或给多个路径)。每张照片可以单独指定标签(如"这张是侧面"),没指定的用我给的默认标签。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n默认标签(如 正面):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_photo_add_batch', 'name': '批量存照片', 'subfunction': '存身材照', 'output_type': 'receipt',
            'html_template': 'templates/body_photo_receipt.html', 'data_source': 'python scripts/render_body_photo_receipt.py --live-add <照片1> <照片2> ... --tag <标签> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「记身材照」。\n\n我要一次性存多张身材照(可连发多张照片,或给多个路径)。每张照片可以单独指定标签(如"这张是侧面"),没指定的用我给的默认标签。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n默认标签(如 正面):____',
            'user_intent': '批量存多张身材照并看逐张结果', 'data_fields': ["photo_path", "tag_list", "status", "reason", "batch_count"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '身材照片',     'wake_word': '查身材照',     'desc': '浏览身材照(网格 + 时间/标签筛选 + 计数)',
            'main_prompt': {
        'cli': 'python scripts/render_body_photo_gallery.py [--days <N> | --start <D> --end <D>] [--tag <标签>] --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「查身材照」。\n\n我想浏览身材照。时间可以用天数(如最近 30 天)、某个日期(如 7月1日)、或一段范围(如 6月1日~7月1日);没填默认最近 90 天。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n时间(最近 N 天 / 某日期 / 某范围,选填):____\n标签(选填,如 正面):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_photo_list', 'name': '看身材照', 'subfunction': '看身材照', 'output_type': 'result',
            'html_template': 'templates/body_photo_gallery.html', 'data_source': 'python scripts/render_body_photo_gallery.py [--days <N> | --start <D> --end <D>] [--tag <标签>] --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「查身材照」。\n\n我想浏览身材照。时间可以用天数(如最近 30 天)、某个日期(如 7月1日)、或一段范围(如 6月1日~7月1日);没填默认最近 90 天。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n时间(最近 N 天 / 某日期 / 某范围,选填):____\n标签(选填,如 正面):____',
            'user_intent': '浏览身材照并按时间/标签筛选', 'data_fields': ["photos", "tag_counts", "total_count", "days_since_last", "filters"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '身材照片',     'wake_word': '对比两张照片',     'desc': '两张照片并排对比(间隔天数/标签/备注)',
            'main_prompt': {
        'cli': 'python scripts/render_body_photo_compare.py --id1 <ID> --id2 <ID> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比两张照片」。\n\n我想把两张身材照并排对比。可以说日期(如"月初 vs 月底")、编号,或让我从最近的照片里选。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n照片 1(日期/编号/留空):____\n照片 2(日期/编号/留空):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_photo_compare', 'name': '对比两张照片', 'subfunction': '比身材照', 'output_type': 'result',
            'html_template': 'templates/body_photo_compare.html', 'data_source': 'python scripts/render_body_photo_compare.py --id1 <ID> --id2 <ID> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比两张照片」。\n\n我想把两张身材照并排对比。可以说日期(如"月初 vs 月底")、编号,或让我从最近的照片里选。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n照片 1(日期/编号/留空):____\n照片 2(日期/编号/留空):____',
            'user_intent': '并排对比两张身材照看变化', 'data_fields': ["photo1", "photo2", "interval_days", "tag_list", "note"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '身材照片',     'wake_word': '生成身材照GIF',     'desc': '时间段多张照片合成变化 GIF(帧数/首末日期)',
            'main_prompt': {
        'cli': 'python scripts/render_body_photo_gif_result.py --tag <标签> [--start <D> --end <D> | --days <N> | --photo-id <ID> ...] --chain "1.识别→2.选照片→3.合成→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「生成身材照GIF」。\n\n我要把一段时间的多张身材照合成变化 GIF。请先确认照片范围(标签/时间)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n标签(如 正面):____\n时间范围(如 最近3个月 / 起始日期):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_photo_gif', 'name': '生成身材照 GIF', 'subfunction': '比身材照', 'output_type': 'result',
            'html_template': 'templates/body_photo_gif_result.html', 'data_source': 'python scripts/render_body_photo_gif_result.py --tag <标签> [--start <D> --end <D> | --days <N> | --photo-id <ID> ...] --chain "1.识别→2.选照片→3.合成→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「生成身材照GIF」。\n\n我要把一段时间的多张身材照合成变化 GIF。请先确认照片范围(标签/时间)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n标签(如 正面):____\n时间范围(如 最近3个月 / 起始日期):____',
            'user_intent': '把一段时间的身材照合成变化 GIF', 'data_fields': ["gif_path", "time_span", "frames", "photo_count", "first_date", "last_date"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '身材照片',     'wake_word': '删身材照',     'desc': '删除照片(先列候选 → 快照确认 → 回执)',
            'main_prompt': {
        'cli': 'python scripts/render_body_photo_receipt.py --live-delete --id <ID> --chain "1.列候选→2.确认→3.删除→4.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「删身材照」。\n\n我要删一张身材照(删除后无法恢复)。如果我没说清是哪张,请先列出最近的几张照片(缩略图+日期+标签)让我选。确认后,删除前先给我看这张照片的内容(快照),确认无误再删,最后给我确认回执。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n要删的照片(选填,如「最近一张」或日期):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_photo_delete', 'name': '删身材照', 'subfunction': '管身材照', 'output_type': 'receipt',
            'html_template': 'templates/body_photo_receipt.html', 'data_source': 'python scripts/render_body_photo_receipt.py --live-delete --id <ID> --chain "1.列候选→2.确认→3.删除→4.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「删身材照」。\n\n我要删一张身材照(删除后无法恢复)。如果我没说清是哪张,请先列出最近的几张照片(缩略图+日期+标签)让我选。确认后,删除前先给我看这张照片的内容(快照),确认无误再删,最后给我确认回执。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n要删的照片(选填,如「最近一张」或日期):____',
            'user_intent': '删除一张身材照(带快照确认)', 'data_fields': ["id", "date", "tag_list", "snapshot", "photo_path"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '身材照片',     'wake_word': '改照片标签',     'desc': '标签覆盖整套(可多个,改前/改后对比)',
            'main_prompt': {
        'cli': 'python scripts/render_body_photo_receipt.py --live-tag-set --id <ID> --tag-list <标签1,标签2> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「改照片标签」。\n\n我要把某张照片的标签换成整套新标签(覆盖旧的,可多个)。请先确认这张照片原来的完整标签列表。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n照片(日期或编号):____\n新标签(可多个,如 正面,侧面):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_photo_tag_set', 'name': '改照片标签', 'subfunction': '管身材照', 'output_type': 'receipt',
            'html_template': 'templates/body_photo_receipt.html', 'data_source': 'python scripts/render_body_photo_receipt.py --live-tag-set --id <ID> --tag-list <标签1,标签2> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改照片标签」。\n\n我要把某张照片的标签换成整套新标签(覆盖旧的,可多个)。请先确认这张照片原来的完整标签列表。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n照片(日期或编号):____\n新标签(可多个,如 正面,侧面):____',
            'user_intent': '把照片标签换成整套新标签', 'data_fields': ["tag_before", "tag_after", "tag_list"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '身材照片',     'wake_word': '加照片标签',     'desc': '追加标签(可多个,判重提示)',
            'main_prompt': {
        'cli': 'python scripts/render_body_photo_receipt.py --live-tag-add --id <ID> --tag <标签> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「加照片标签」。\n\n我要给某张照片追加标签(不覆盖已有,可一次加多个)。如果某个标签已经存在,请提示我。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n照片(日期或编号):____\n要加的标签(可多个,逗号分隔):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_photo_tag_add', 'name': '加照片标签', 'subfunction': '管身材照', 'output_type': 'receipt',
            'html_template': 'templates/body_photo_receipt.html', 'data_source': 'python scripts/render_body_photo_receipt.py --live-tag-add --id <ID> --tag <标签> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「加照片标签」。\n\n我要给某张照片追加标签(不覆盖已有,可一次加多个)。如果某个标签已经存在,请提示我。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n照片(日期或编号):____\n要加的标签(可多个,逗号分隔):____',
            'user_intent': '给照片追加一个标签', 'data_fields': ["tag_added", "tag_list", "duplicate"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '身材照片',     'wake_word': '删照片标签',     'desc': '移除标签(可多个,至少保留 1 个)',
            'main_prompt': {
        'cli': 'python scripts/render_body_photo_receipt.py --live-tag-remove --id <ID> --tag <标签> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「删照片标签」。\n\n我要从某张照片上移除标签(其余保留,可一次删多个)。请先告诉我这张照片当前有哪些标签,每张照片至少保留 1 个标签,删空会提示我;想清空全部标签请用「改照片标签」。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n照片(日期或编号):____\n要删的标签(可多个,逗号分隔):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_photo_tag_remove', 'name': '删照片标签', 'subfunction': '管身材照', 'output_type': 'receipt',
            'html_template': 'templates/body_photo_receipt.html', 'data_source': 'python scripts/render_body_photo_receipt.py --live-tag-remove --id <ID> --tag <标签> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「删照片标签」。\n\n我要从某张照片上移除标签(其余保留,可一次删多个)。请先告诉我这张照片当前有哪些标签,每张照片至少保留 1 个标签,删空会提示我;想清空全部标签请用「改照片标签」。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n照片(日期或编号):____\n要删的标签(可多个,逗号分隔):____',
            'user_intent': '从照片上移除一个标签', 'data_fields': ["tag_removed", "tag_before", "tag_after"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '分析',     'wake_word': '看体重 vs 摄入(最近 7 天)',     'desc': '看体重 vs 摄入(最近 7 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_calorie --window 7d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 摄入(最近 7 天)」。\n\n我想看最近 7 天的体重走势 vs 每日摄入热量的关系(吃多少影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_calorie_7d', 'name': '看体重 vs 摄入(最近 7 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_calorie --window 7d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 摄入(最近 7 天)」。\n\n我想看最近 7 天的体重走势 vs 每日摄入热量的关系(吃多少影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 摄入(最近 7 天)', 'data_fields': ['weight_kg', 'calories', 'correlation', 'regression', 'lag', 'strat'],
            'depends_on_external': False, 'order': 0},
    {
            'category': '分析',     'wake_word': '看体重 vs 摄入(最近 15 天)',     'desc': '看体重 vs 摄入(最近 15 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_calorie --window 15d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 摄入(最近 15 天)」。\n\n我想看最近 15 天的体重走势 vs 每日摄入热量的关系(吃多少影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_calorie_15d', 'name': '看体重 vs 摄入(最近 15 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_calorie --window 15d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 摄入(最近 15 天)」。\n\n我想看最近 15 天的体重走势 vs 每日摄入热量的关系(吃多少影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 摄入(最近 15 天)', 'data_fields': ['weight_kg', 'calories', 'correlation', 'regression', 'lag', 'strat'],
            'depends_on_external': False, 'order': 1},
    {
            'category': '分析',     'wake_word': '看体重 vs 摄入(最近 30 天)',     'desc': '看体重 vs 摄入(最近 30 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_calorie --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 摄入(最近 30 天)」。\n\n我想看最近 30 天的体重走势 vs 每日摄入热量的关系(吃多少影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_calorie_30d', 'name': '看体重 vs 摄入(最近 30 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_calorie --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 摄入(最近 30 天)」。\n\n我想看最近 30 天的体重走势 vs 每日摄入热量的关系(吃多少影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 摄入(最近 30 天)', 'data_fields': ['weight_kg', 'calories', 'correlation', 'regression', 'lag', 'strat'],
            'depends_on_external': False, 'order': 2},
    {
            'category': '分析',     'wake_word': '看体重 vs 摄入(最近 60 天)',     'desc': '看体重 vs 摄入(最近 60 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_calorie --window 60d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 摄入(最近 60 天)」。\n\n我想看最近 60 天的体重走势 vs 每日摄入热量的关系(吃多少影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_calorie_60d', 'name': '看体重 vs 摄入(最近 60 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_calorie --window 60d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 摄入(最近 60 天)」。\n\n我想看最近 60 天的体重走势 vs 每日摄入热量的关系(吃多少影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 摄入(最近 60 天)', 'data_fields': ['weight_kg', 'calories', 'correlation', 'regression', 'lag', 'strat'],
            'depends_on_external': False, 'order': 3},
    {
            'category': '分析',     'wake_word': '看体重 vs 摄入(最近 90 天)',     'desc': '看体重 vs 摄入(最近 90 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_calorie --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 摄入(最近 90 天)」。\n\n我想看最近 90 天的体重走势 vs 每日摄入热量的关系(吃多少影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_calorie_90d', 'name': '看体重 vs 摄入(最近 90 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_calorie --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 摄入(最近 90 天)」。\n\n我想看最近 90 天的体重走势 vs 每日摄入热量的关系(吃多少影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 摄入(最近 90 天)', 'data_fields': ['weight_kg', 'calories', 'correlation', 'regression', 'lag', 'strat'],
            'depends_on_external': False, 'order': 4},
    {
            'category': '分析',     'wake_word': '看体重 vs 摄入(最近 180 天)',     'desc': '看体重 vs 摄入(最近 180 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_calorie --window 180d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 摄入(最近 180 天)」。\n\n我想看最近 180 天的体重走势 vs 每日摄入热量的关系(吃多少影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_calorie_180d', 'name': '看体重 vs 摄入(最近 180 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_calorie --window 180d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 摄入(最近 180 天)」。\n\n我想看最近 180 天的体重走势 vs 每日摄入热量的关系(吃多少影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 摄入(最近 180 天)', 'data_fields': ['weight_kg', 'calories', 'correlation', 'regression', 'lag', 'strat'],
            'depends_on_external': False, 'order': 5},
    {
            'category': '分析',     'wake_word': '看体重 vs 摄入(最近 365 天)',     'desc': '看体重 vs 摄入(最近 365 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_calorie --window 365d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 摄入(最近 365 天)」。\n\n我想看最近 365 天的体重走势 vs 每日摄入热量的关系(吃多少影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_calorie_365d', 'name': '看体重 vs 摄入(最近 365 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_calorie --window 365d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 摄入(最近 365 天)」。\n\n我想看最近 365 天的体重走势 vs 每日摄入热量的关系(吃多少影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 摄入(最近 365 天)', 'data_fields': ['weight_kg', 'calories', 'correlation', 'regression', 'lag', 'strat'],
            'depends_on_external': False, 'order': 6},
    {
            'category': '分析',     'wake_word': '看体重 vs 摄入(本周)',     'desc': '看体重 vs 摄入(本周)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_calorie --window week_cur', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 摄入(本周)」。\n\n我想看本周的体重走势 vs 每日摄入热量的关系(吃多少影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_calorie_week_cur', 'name': '看体重 vs 摄入(本周)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_calorie --window week_cur', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 摄入(本周)」。\n\n我想看本周的体重走势 vs 每日摄入热量的关系(吃多少影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 摄入(本周)', 'data_fields': ['weight_kg', 'calories', 'correlation', 'regression', 'lag', 'strat'],
            'depends_on_external': False, 'order': 7},
    {
            'category': '分析',     'wake_word': '看体重 vs 摄入(本月)',     'desc': '看体重 vs 摄入(本月)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_calorie --window month_cur', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 摄入(本月)」。\n\n我想看本月的体重走势 vs 每日摄入热量的关系(吃多少影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_calorie_month_cur', 'name': '看体重 vs 摄入(本月)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_calorie --window month_cur', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 摄入(本月)」。\n\n我想看本月的体重走势 vs 每日摄入热量的关系(吃多少影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 摄入(本月)', 'data_fields': ['weight_kg', 'calories', 'correlation', 'regression', 'lag', 'strat'],
            'depends_on_external': False, 'order': 8},
    {
            'category': '分析',     'wake_word': '看体重 vs 摄入(自定义)',     'desc': '看体重 vs 摄入(自定义)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_calorie --window custom --start <开始日期> --end <结束日期>', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 摄入(自定义)」。\n\n我想看体重走势 vs 每日摄入热量的关系(吃多少影响体重吗)。请帮我分析自定义时间段(开始日期到结束日期)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_calorie_custom', 'name': '看体重 vs 摄入(自定义)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_calorie --window custom --start <开始日期> --end <结束日期>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 摄入(自定义)」。\n\n我想看体重走势 vs 每日摄入热量的关系(吃多少影响体重吗)。请帮我分析自定义时间段(开始日期到结束日期)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 摄入(自定义时间段)', 'data_fields': ['weight_kg', 'calories', 'correlation', 'regression', 'lag', 'strat'],
            'depends_on_external': False, 'order': 9},
    {
            'category': '分析',     'wake_word': '看体重 vs 运动(最近 7 天)',     'desc': '看体重 vs 运动(最近 7 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_exercise --window 7d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 运动(最近 7 天)」。\n\n我想看最近 7 天的体重走势 vs 每日运动消耗的关系(运动影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_exercise_7d', 'name': '看体重 vs 运动(最近 7 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_exercise --window 7d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 运动(最近 7 天)」。\n\n我想看最近 7 天的体重走势 vs 每日运动消耗的关系(运动影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 运动(最近 7 天)', 'data_fields': ['weight_kg', 'exercise_kcal', 'correlation', 'regression', 'lag', 'strat'],
            'depends_on_external': False, 'order': 10},
    {
            'category': '分析',     'wake_word': '看体重 vs 运动(最近 15 天)',     'desc': '看体重 vs 运动(最近 15 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_exercise --window 15d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 运动(最近 15 天)」。\n\n我想看最近 15 天的体重走势 vs 每日运动消耗的关系(运动影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_exercise_15d', 'name': '看体重 vs 运动(最近 15 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_exercise --window 15d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 运动(最近 15 天)」。\n\n我想看最近 15 天的体重走势 vs 每日运动消耗的关系(运动影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 运动(最近 15 天)', 'data_fields': ['weight_kg', 'exercise_kcal', 'correlation', 'regression', 'lag', 'strat'],
            'depends_on_external': False, 'order': 11},
    {
            'category': '分析',     'wake_word': '看体重 vs 运动(最近 30 天)',     'desc': '看体重 vs 运动(最近 30 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_exercise --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 运动(最近 30 天)」。\n\n我想看最近 30 天的体重走势 vs 每日运动消耗的关系(运动影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_exercise_30d', 'name': '看体重 vs 运动(最近 30 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_exercise --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 运动(最近 30 天)」。\n\n我想看最近 30 天的体重走势 vs 每日运动消耗的关系(运动影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 运动(最近 30 天)', 'data_fields': ['weight_kg', 'exercise_kcal', 'correlation', 'regression', 'lag', 'strat'],
            'depends_on_external': False, 'order': 12},
    {
            'category': '分析',     'wake_word': '看体重 vs 运动(最近 60 天)',     'desc': '看体重 vs 运动(最近 60 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_exercise --window 60d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 运动(最近 60 天)」。\n\n我想看最近 60 天的体重走势 vs 每日运动消耗的关系(运动影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_exercise_60d', 'name': '看体重 vs 运动(最近 60 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_exercise --window 60d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 运动(最近 60 天)」。\n\n我想看最近 60 天的体重走势 vs 每日运动消耗的关系(运动影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 运动(最近 60 天)', 'data_fields': ['weight_kg', 'exercise_kcal', 'correlation', 'regression', 'lag', 'strat'],
            'depends_on_external': False, 'order': 13},
    {
            'category': '分析',     'wake_word': '看体重 vs 运动(最近 90 天)',     'desc': '看体重 vs 运动(最近 90 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_exercise --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 运动(最近 90 天)」。\n\n我想看最近 90 天的体重走势 vs 每日运动消耗的关系(运动影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_exercise_90d', 'name': '看体重 vs 运动(最近 90 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_exercise --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 运动(最近 90 天)」。\n\n我想看最近 90 天的体重走势 vs 每日运动消耗的关系(运动影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 运动(最近 90 天)', 'data_fields': ['weight_kg', 'exercise_kcal', 'correlation', 'regression', 'lag', 'strat'],
            'depends_on_external': False, 'order': 14},
    {
            'category': '分析',     'wake_word': '看体重 vs 运动(最近 180 天)',     'desc': '看体重 vs 运动(最近 180 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_exercise --window 180d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 运动(最近 180 天)」。\n\n我想看最近 180 天的体重走势 vs 每日运动消耗的关系(运动影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_exercise_180d', 'name': '看体重 vs 运动(最近 180 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_exercise --window 180d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 运动(最近 180 天)」。\n\n我想看最近 180 天的体重走势 vs 每日运动消耗的关系(运动影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 运动(最近 180 天)', 'data_fields': ['weight_kg', 'exercise_kcal', 'correlation', 'regression', 'lag', 'strat'],
            'depends_on_external': False, 'order': 15},
    {
            'category': '分析',     'wake_word': '看体重 vs 运动(最近 365 天)',     'desc': '看体重 vs 运动(最近 365 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_exercise --window 365d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 运动(最近 365 天)」。\n\n我想看最近 365 天的体重走势 vs 每日运动消耗的关系(运动影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_exercise_365d', 'name': '看体重 vs 运动(最近 365 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_exercise --window 365d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 运动(最近 365 天)」。\n\n我想看最近 365 天的体重走势 vs 每日运动消耗的关系(运动影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 运动(最近 365 天)', 'data_fields': ['weight_kg', 'exercise_kcal', 'correlation', 'regression', 'lag', 'strat'],
            'depends_on_external': False, 'order': 16},
    {
            'category': '分析',     'wake_word': '看体重 vs 运动(本周)',     'desc': '看体重 vs 运动(本周)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_exercise --window week_cur', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 运动(本周)」。\n\n我想看本周的体重走势 vs 每日运动消耗的关系(运动影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_exercise_week_cur', 'name': '看体重 vs 运动(本周)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_exercise --window week_cur', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 运动(本周)」。\n\n我想看本周的体重走势 vs 每日运动消耗的关系(运动影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 运动(本周)', 'data_fields': ['weight_kg', 'exercise_kcal', 'correlation', 'regression', 'lag', 'strat'],
            'depends_on_external': False, 'order': 17},
    {
            'category': '分析',     'wake_word': '看体重 vs 运动(本月)',     'desc': '看体重 vs 运动(本月)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_exercise --window month_cur', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 运动(本月)」。\n\n我想看本月的体重走势 vs 每日运动消耗的关系(运动影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_exercise_month_cur', 'name': '看体重 vs 运动(本月)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_exercise --window month_cur', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 运动(本月)」。\n\n我想看本月的体重走势 vs 每日运动消耗的关系(运动影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 运动(本月)', 'data_fields': ['weight_kg', 'exercise_kcal', 'correlation', 'regression', 'lag', 'strat'],
            'depends_on_external': False, 'order': 18},
    {
            'category': '分析',     'wake_word': '看体重 vs 运动(自定义)',     'desc': '看体重 vs 运动(自定义)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_exercise --window custom --start <开始日期> --end <结束日期>', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 运动(自定义)」。\n\n我想看体重走势 vs 每日运动消耗的关系(运动影响体重吗)。请帮我分析自定义时间段(开始日期到结束日期)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_exercise_custom', 'name': '看体重 vs 运动(自定义)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_exercise --window custom --start <开始日期> --end <结束日期>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 运动(自定义)」。\n\n我想看体重走势 vs 每日运动消耗的关系(运动影响体重吗)。请帮我分析自定义时间段(开始日期到结束日期)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 运动(自定义时间段)', 'data_fields': ['weight_kg', 'exercise_kcal', 'correlation', 'regression', 'lag', 'strat'],
            'depends_on_external': False, 'order': 19},
    {
            'category': '分析',     'wake_word': '看体重 vs 蛋白(最近 7 天)',     'desc': '看体重 vs 蛋白(最近 7 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_protein --window 7d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 蛋白(最近 7 天)」。\n\n我想看最近 7 天的体重走势 vs 每日蛋白摄入的关系(蛋白够不够影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_protein_7d', 'name': '看体重 vs 蛋白(最近 7 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_protein --window 7d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 蛋白(最近 7 天)」。\n\n我想看最近 7 天的体重走势 vs 每日蛋白摄入的关系(蛋白够不够影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 蛋白(最近 7 天)', 'data_fields': ['weight_kg', 'protein', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 20},
    {
            'category': '分析',     'wake_word': '看体重 vs 蛋白(最近 15 天)',     'desc': '看体重 vs 蛋白(最近 15 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_protein --window 15d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 蛋白(最近 15 天)」。\n\n我想看最近 15 天的体重走势 vs 每日蛋白摄入的关系(蛋白够不够影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_protein_15d', 'name': '看体重 vs 蛋白(最近 15 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_protein --window 15d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 蛋白(最近 15 天)」。\n\n我想看最近 15 天的体重走势 vs 每日蛋白摄入的关系(蛋白够不够影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 蛋白(最近 15 天)', 'data_fields': ['weight_kg', 'protein', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 21},
    {
            'category': '分析',     'wake_word': '看体重 vs 蛋白(最近 30 天)',     'desc': '看体重 vs 蛋白(最近 30 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_protein --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 蛋白(最近 30 天)」。\n\n我想看最近 30 天的体重走势 vs 每日蛋白摄入的关系(蛋白够不够影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_protein_30d', 'name': '看体重 vs 蛋白(最近 30 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_protein --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 蛋白(最近 30 天)」。\n\n我想看最近 30 天的体重走势 vs 每日蛋白摄入的关系(蛋白够不够影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 蛋白(最近 30 天)', 'data_fields': ['weight_kg', 'protein', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 22},
    {
            'category': '分析',     'wake_word': '看体重 vs 蛋白(最近 60 天)',     'desc': '看体重 vs 蛋白(最近 60 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_protein --window 60d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 蛋白(最近 60 天)」。\n\n我想看最近 60 天的体重走势 vs 每日蛋白摄入的关系(蛋白够不够影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_protein_60d', 'name': '看体重 vs 蛋白(最近 60 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_protein --window 60d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 蛋白(最近 60 天)」。\n\n我想看最近 60 天的体重走势 vs 每日蛋白摄入的关系(蛋白够不够影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 蛋白(最近 60 天)', 'data_fields': ['weight_kg', 'protein', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 23},
    {
            'category': '分析',     'wake_word': '看体重 vs 蛋白(最近 90 天)',     'desc': '看体重 vs 蛋白(最近 90 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_protein --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 蛋白(最近 90 天)」。\n\n我想看最近 90 天的体重走势 vs 每日蛋白摄入的关系(蛋白够不够影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_protein_90d', 'name': '看体重 vs 蛋白(最近 90 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_protein --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 蛋白(最近 90 天)」。\n\n我想看最近 90 天的体重走势 vs 每日蛋白摄入的关系(蛋白够不够影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 蛋白(最近 90 天)', 'data_fields': ['weight_kg', 'protein', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 24},
    {
            'category': '分析',     'wake_word': '看体重 vs 蛋白(最近 180 天)',     'desc': '看体重 vs 蛋白(最近 180 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_protein --window 180d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 蛋白(最近 180 天)」。\n\n我想看最近 180 天的体重走势 vs 每日蛋白摄入的关系(蛋白够不够影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_protein_180d', 'name': '看体重 vs 蛋白(最近 180 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_protein --window 180d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 蛋白(最近 180 天)」。\n\n我想看最近 180 天的体重走势 vs 每日蛋白摄入的关系(蛋白够不够影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 蛋白(最近 180 天)', 'data_fields': ['weight_kg', 'protein', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 25},
    {
            'category': '分析',     'wake_word': '看体重 vs 蛋白(最近 365 天)',     'desc': '看体重 vs 蛋白(最近 365 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_protein --window 365d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 蛋白(最近 365 天)」。\n\n我想看最近 365 天的体重走势 vs 每日蛋白摄入的关系(蛋白够不够影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_protein_365d', 'name': '看体重 vs 蛋白(最近 365 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_protein --window 365d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 蛋白(最近 365 天)」。\n\n我想看最近 365 天的体重走势 vs 每日蛋白摄入的关系(蛋白够不够影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 蛋白(最近 365 天)', 'data_fields': ['weight_kg', 'protein', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 26},
    {
            'category': '分析',     'wake_word': '看体重 vs 蛋白(本周)',     'desc': '看体重 vs 蛋白(本周)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_protein --window week_cur', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 蛋白(本周)」。\n\n我想看本周的体重走势 vs 每日蛋白摄入的关系(蛋白够不够影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_protein_week_cur', 'name': '看体重 vs 蛋白(本周)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_protein --window week_cur', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 蛋白(本周)」。\n\n我想看本周的体重走势 vs 每日蛋白摄入的关系(蛋白够不够影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 蛋白(本周)', 'data_fields': ['weight_kg', 'protein', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 27},
    {
            'category': '分析',     'wake_word': '看体重 vs 蛋白(本月)',     'desc': '看体重 vs 蛋白(本月)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_protein --window month_cur', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 蛋白(本月)」。\n\n我想看本月的体重走势 vs 每日蛋白摄入的关系(蛋白够不够影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_protein_month_cur', 'name': '看体重 vs 蛋白(本月)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_protein --window month_cur', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 蛋白(本月)」。\n\n我想看本月的体重走势 vs 每日蛋白摄入的关系(蛋白够不够影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 蛋白(本月)', 'data_fields': ['weight_kg', 'protein', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 28},
    {
            'category': '分析',     'wake_word': '看体重 vs 蛋白(自定义)',     'desc': '看体重 vs 蛋白(自定义)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_protein --window custom --start <开始日期> --end <结束日期>', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 蛋白(自定义)」。\n\n我想看体重走势 vs 每日蛋白摄入的关系(蛋白够不够影响体重吗)。请帮我分析自定义时间段(开始日期到结束日期)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_protein_custom', 'name': '看体重 vs 蛋白(自定义)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_protein --window custom --start <开始日期> --end <结束日期>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 蛋白(自定义)」。\n\n我想看体重走势 vs 每日蛋白摄入的关系(蛋白够不够影响体重吗)。请帮我分析自定义时间段(开始日期到结束日期)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 蛋白(自定义时间段)', 'data_fields': ['weight_kg', 'protein', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 29},
    {
            'category': '分析',     'wake_word': '看体重 vs 缺口(最近 7 天)',     'desc': '看体重 vs 缺口(最近 7 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_deficit --window 7d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 缺口(最近 7 天)」。\n\n我想看最近 7 天的体重走势 vs 每日热量缺口的关系(缺口大小影响减重速度吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_deficit_7d', 'name': '看体重 vs 缺口(最近 7 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_deficit --window 7d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 缺口(最近 7 天)」。\n\n我想看最近 7 天的体重走势 vs 每日热量缺口的关系(缺口大小影响减重速度吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 缺口(最近 7 天)', 'data_fields': ['weight_kg', 'deficit', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 30},
    {
            'category': '分析',     'wake_word': '看体重 vs 缺口(最近 15 天)',     'desc': '看体重 vs 缺口(最近 15 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_deficit --window 15d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 缺口(最近 15 天)」。\n\n我想看最近 15 天的体重走势 vs 每日热量缺口的关系(缺口大小影响减重速度吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_deficit_15d', 'name': '看体重 vs 缺口(最近 15 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_deficit --window 15d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 缺口(最近 15 天)」。\n\n我想看最近 15 天的体重走势 vs 每日热量缺口的关系(缺口大小影响减重速度吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 缺口(最近 15 天)', 'data_fields': ['weight_kg', 'deficit', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 31},
    {
            'category': '分析',     'wake_word': '看体重 vs 缺口(最近 30 天)',     'desc': '看体重 vs 缺口(最近 30 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_deficit --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 缺口(最近 30 天)」。\n\n我想看最近 30 天的体重走势 vs 每日热量缺口的关系(缺口大小影响减重速度吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_deficit_30d', 'name': '看体重 vs 缺口(最近 30 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_deficit --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 缺口(最近 30 天)」。\n\n我想看最近 30 天的体重走势 vs 每日热量缺口的关系(缺口大小影响减重速度吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 缺口(最近 30 天)', 'data_fields': ['weight_kg', 'deficit', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 32},
    {
            'category': '分析',     'wake_word': '看体重 vs 缺口(最近 60 天)',     'desc': '看体重 vs 缺口(最近 60 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_deficit --window 60d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 缺口(最近 60 天)」。\n\n我想看最近 60 天的体重走势 vs 每日热量缺口的关系(缺口大小影响减重速度吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_deficit_60d', 'name': '看体重 vs 缺口(最近 60 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_deficit --window 60d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 缺口(最近 60 天)」。\n\n我想看最近 60 天的体重走势 vs 每日热量缺口的关系(缺口大小影响减重速度吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 缺口(最近 60 天)', 'data_fields': ['weight_kg', 'deficit', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 33},
    {
            'category': '分析',     'wake_word': '看体重 vs 缺口(最近 90 天)',     'desc': '看体重 vs 缺口(最近 90 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_deficit --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 缺口(最近 90 天)」。\n\n我想看最近 90 天的体重走势 vs 每日热量缺口的关系(缺口大小影响减重速度吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_deficit_90d', 'name': '看体重 vs 缺口(最近 90 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_deficit --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 缺口(最近 90 天)」。\n\n我想看最近 90 天的体重走势 vs 每日热量缺口的关系(缺口大小影响减重速度吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 缺口(最近 90 天)', 'data_fields': ['weight_kg', 'deficit', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 34},
    {
            'category': '分析',     'wake_word': '看体重 vs 缺口(最近 180 天)',     'desc': '看体重 vs 缺口(最近 180 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_deficit --window 180d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 缺口(最近 180 天)」。\n\n我想看最近 180 天的体重走势 vs 每日热量缺口的关系(缺口大小影响减重速度吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_deficit_180d', 'name': '看体重 vs 缺口(最近 180 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_deficit --window 180d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 缺口(最近 180 天)」。\n\n我想看最近 180 天的体重走势 vs 每日热量缺口的关系(缺口大小影响减重速度吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 缺口(最近 180 天)', 'data_fields': ['weight_kg', 'deficit', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 35},
    {
            'category': '分析',     'wake_word': '看体重 vs 缺口(最近 365 天)',     'desc': '看体重 vs 缺口(最近 365 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_deficit --window 365d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 缺口(最近 365 天)」。\n\n我想看最近 365 天的体重走势 vs 每日热量缺口的关系(缺口大小影响减重速度吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_deficit_365d', 'name': '看体重 vs 缺口(最近 365 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_deficit --window 365d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 缺口(最近 365 天)」。\n\n我想看最近 365 天的体重走势 vs 每日热量缺口的关系(缺口大小影响减重速度吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 缺口(最近 365 天)', 'data_fields': ['weight_kg', 'deficit', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 36},
    {
            'category': '分析',     'wake_word': '看体重 vs 缺口(本周)',     'desc': '看体重 vs 缺口(本周)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_deficit --window week_cur', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 缺口(本周)」。\n\n我想看本周的体重走势 vs 每日热量缺口的关系(缺口大小影响减重速度吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_deficit_week_cur', 'name': '看体重 vs 缺口(本周)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_deficit --window week_cur', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 缺口(本周)」。\n\n我想看本周的体重走势 vs 每日热量缺口的关系(缺口大小影响减重速度吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 缺口(本周)', 'data_fields': ['weight_kg', 'deficit', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 37},
    {
            'category': '分析',     'wake_word': '看体重 vs 缺口(本月)',     'desc': '看体重 vs 缺口(本月)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_deficit --window month_cur', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 缺口(本月)」。\n\n我想看本月的体重走势 vs 每日热量缺口的关系(缺口大小影响减重速度吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_deficit_month_cur', 'name': '看体重 vs 缺口(本月)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_deficit --window month_cur', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 缺口(本月)」。\n\n我想看本月的体重走势 vs 每日热量缺口的关系(缺口大小影响减重速度吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 缺口(本月)', 'data_fields': ['weight_kg', 'deficit', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 38},
    {
            'category': '分析',     'wake_word': '看体重 vs 缺口(自定义)',     'desc': '看体重 vs 缺口(自定义)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_deficit --window custom --start <开始日期> --end <结束日期>', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 缺口(自定义)」。\n\n我想看体重走势 vs 每日热量缺口的关系(缺口大小影响减重速度吗)。请帮我分析自定义时间段(开始日期到结束日期)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_deficit_custom', 'name': '看体重 vs 缺口(自定义)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_deficit --window custom --start <开始日期> --end <结束日期>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 缺口(自定义)」。\n\n我想看体重走势 vs 每日热量缺口的关系(缺口大小影响减重速度吗)。请帮我分析自定义时间段(开始日期到结束日期)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 缺口(自定义时间段)', 'data_fields': ['weight_kg', 'deficit', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 39},
    {
            'category': '分析',     'wake_word': '看摄入 vs 运动(最近 7 天)',     'desc': '看摄入 vs 运动(最近 7 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair calorie_exercise --window 7d', 'text': '请你加载技能 卡路里,执行唤醒词「看摄入 vs 运动(最近 7 天)」。\n\n我想看最近 7 天的每日摄入 vs 每日运动消耗的关系(吃得和动得匹配吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_calorie_exercise_7d', 'name': '看摄入 vs 运动(最近 7 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair calorie_exercise --window 7d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看摄入 vs 运动(最近 7 天)」。\n\n我想看最近 7 天的每日摄入 vs 每日运动消耗的关系(吃得和动得匹配吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看摄入 vs 运动(最近 7 天)', 'data_fields': ['calories', 'exercise_kcal', 'deficit', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 40},
    {
            'category': '分析',     'wake_word': '看摄入 vs 运动(最近 30 天)',     'desc': '看摄入 vs 运动(最近 30 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair calorie_exercise --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「看摄入 vs 运动(最近 30 天)」。\n\n我想看最近 30 天的每日摄入 vs 每日运动消耗的关系(吃得和动得匹配吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_calorie_exercise_30d', 'name': '看摄入 vs 运动(最近 30 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair calorie_exercise --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看摄入 vs 运动(最近 30 天)」。\n\n我想看最近 30 天的每日摄入 vs 每日运动消耗的关系(吃得和动得匹配吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看摄入 vs 运动(最近 30 天)', 'data_fields': ['calories', 'exercise_kcal', 'deficit', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 41},
    {
            'category': '分析',     'wake_word': '看摄入 vs 运动(最近 90 天)',     'desc': '看摄入 vs 运动(最近 90 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair calorie_exercise --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「看摄入 vs 运动(最近 90 天)」。\n\n我想看最近 90 天的每日摄入 vs 每日运动消耗的关系(吃得和动得匹配吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_calorie_exercise_90d', 'name': '看摄入 vs 运动(最近 90 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair calorie_exercise --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看摄入 vs 运动(最近 90 天)」。\n\n我想看最近 90 天的每日摄入 vs 每日运动消耗的关系(吃得和动得匹配吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看摄入 vs 运动(最近 90 天)', 'data_fields': ['calories', 'exercise_kcal', 'deficit', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 42},
    {
            'category': '分析',     'wake_word': '看摄入 vs 运动(最近 180 天)',     'desc': '看摄入 vs 运动(最近 180 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair calorie_exercise --window 180d', 'text': '请你加载技能 卡路里,执行唤醒词「看摄入 vs 运动(最近 180 天)」。\n\n我想看最近 180 天的每日摄入 vs 每日运动消耗的关系(吃得和动得匹配吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_calorie_exercise_180d', 'name': '看摄入 vs 运动(最近 180 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair calorie_exercise --window 180d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看摄入 vs 运动(最近 180 天)」。\n\n我想看最近 180 天的每日摄入 vs 每日运动消耗的关系(吃得和动得匹配吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看摄入 vs 运动(最近 180 天)', 'data_fields': ['calories', 'exercise_kcal', 'deficit', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 43},
    {
            'category': '分析',     'wake_word': '看摄入 vs 运动(最近 365 天)',     'desc': '看摄入 vs 运动(最近 365 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair calorie_exercise --window 365d', 'text': '请你加载技能 卡路里,执行唤醒词「看摄入 vs 运动(最近 365 天)」。\n\n我想看最近 365 天的每日摄入 vs 每日运动消耗的关系(吃得和动得匹配吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_calorie_exercise_365d', 'name': '看摄入 vs 运动(最近 365 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair calorie_exercise --window 365d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看摄入 vs 运动(最近 365 天)」。\n\n我想看最近 365 天的每日摄入 vs 每日运动消耗的关系(吃得和动得匹配吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看摄入 vs 运动(最近 365 天)', 'data_fields': ['calories', 'exercise_kcal', 'deficit', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 44},
    {
            'category': '分析',     'wake_word': '看摄入 vs 运动(自定义)',     'desc': '看摄入 vs 运动(自定义)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair calorie_exercise --window custom --start <开始日期> --end <结束日期>', 'text': '请你加载技能 卡路里,执行唤醒词「看摄入 vs 运动(自定义)」。\n\n我想看每日摄入 vs 每日运动消耗的关系(吃得和动得匹配吗)。请帮我分析自定义时间段(开始日期到结束日期)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_calorie_exercise_custom', 'name': '看摄入 vs 运动(自定义)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair calorie_exercise --window custom --start <开始日期> --end <结束日期>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看摄入 vs 运动(自定义)」。\n\n我想看每日摄入 vs 每日运动消耗的关系(吃得和动得匹配吗)。请帮我分析自定义时间段(开始日期到结束日期)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看摄入 vs 运动(自定义时间段)', 'data_fields': ['calories', 'exercise_kcal', 'deficit', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 45},
    {
            'category': '分析',     'wake_word': '看体重 vs 体脂(最近 7 天)',     'desc': '看体重 vs 体脂(最近 7 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_bodyfat --window 7d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 体脂(最近 7 天)」。\n\n我想看最近 7 天的体重走势 vs 体脂率走势的关系(减的是脂肪还是水分)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_bodyfat_7d', 'name': '看体重 vs 体脂(最近 7 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_bodyfat --window 7d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 体脂(最近 7 天)」。\n\n我想看最近 7 天的体重走势 vs 体脂率走势的关系(减的是脂肪还是水分)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 体脂(最近 7 天)', 'data_fields': ['weight_kg', 'body_fat_pct', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 46},
    {
            'category': '分析',     'wake_word': '看体重 vs 体脂(最近 30 天)',     'desc': '看体重 vs 体脂(最近 30 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_bodyfat --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 体脂(最近 30 天)」。\n\n我想看最近 30 天的体重走势 vs 体脂率走势的关系(减的是脂肪还是水分)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_bodyfat_30d', 'name': '看体重 vs 体脂(最近 30 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_bodyfat --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 体脂(最近 30 天)」。\n\n我想看最近 30 天的体重走势 vs 体脂率走势的关系(减的是脂肪还是水分)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 体脂(最近 30 天)', 'data_fields': ['weight_kg', 'body_fat_pct', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 47},
    {
            'category': '分析',     'wake_word': '看体重 vs 体脂(最近 90 天)',     'desc': '看体重 vs 体脂(最近 90 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_bodyfat --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 体脂(最近 90 天)」。\n\n我想看最近 90 天的体重走势 vs 体脂率走势的关系(减的是脂肪还是水分)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_bodyfat_90d', 'name': '看体重 vs 体脂(最近 90 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_bodyfat --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 体脂(最近 90 天)」。\n\n我想看最近 90 天的体重走势 vs 体脂率走势的关系(减的是脂肪还是水分)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 体脂(最近 90 天)', 'data_fields': ['weight_kg', 'body_fat_pct', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 48},
    {
            'category': '分析',     'wake_word': '看体重 vs 体脂(最近 180 天)',     'desc': '看体重 vs 体脂(最近 180 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_bodyfat --window 180d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 体脂(最近 180 天)」。\n\n我想看最近 180 天的体重走势 vs 体脂率走势的关系(减的是脂肪还是水分)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_bodyfat_180d', 'name': '看体重 vs 体脂(最近 180 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_bodyfat --window 180d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 体脂(最近 180 天)」。\n\n我想看最近 180 天的体重走势 vs 体脂率走势的关系(减的是脂肪还是水分)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 体脂(最近 180 天)', 'data_fields': ['weight_kg', 'body_fat_pct', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 49},
    {
            'category': '分析',     'wake_word': '看体重 vs 体脂(最近 365 天)',     'desc': '看体重 vs 体脂(最近 365 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_bodyfat --window 365d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 体脂(最近 365 天)」。\n\n我想看最近 365 天的体重走势 vs 体脂率走势的关系(减的是脂肪还是水分)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_bodyfat_365d', 'name': '看体重 vs 体脂(最近 365 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_bodyfat --window 365d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 体脂(最近 365 天)」。\n\n我想看最近 365 天的体重走势 vs 体脂率走势的关系(减的是脂肪还是水分)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 体脂(最近 365 天)', 'data_fields': ['weight_kg', 'body_fat_pct', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 50},
    {
            'category': '分析',     'wake_word': '看体重 vs 体脂(自定义)',     'desc': '看体重 vs 体脂(自定义)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_bodyfat --window custom --start <开始日期> --end <结束日期>', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 体脂(自定义)」。\n\n我想看体重走势 vs 体脂率走势的关系(减的是脂肪还是水分)。请帮我分析自定义时间段(开始日期到结束日期)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_bodyfat_custom', 'name': '看体重 vs 体脂(自定义)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_bodyfat --window custom --start <开始日期> --end <结束日期>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 体脂(自定义)」。\n\n我想看体重走势 vs 体脂率走势的关系(减的是脂肪还是水分)。请帮我分析自定义时间段(开始日期到结束日期)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 体脂(自定义时间段)', 'data_fields': ['weight_kg', 'body_fat_pct', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 51},
    {
            'category': '分析',     'wake_word': '看体重 vs 围度(最近 7 天)',     'desc': '看体重 vs 围度(最近 7 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_waist --window 7d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 围度(最近 7 天)」。\n\n我想看最近 7 天的体重走势 vs 各部位围度走势的关系(腰围真的在变小吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_waist_7d', 'name': '看体重 vs 围度(最近 7 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_waist --window 7d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 围度(最近 7 天)」。\n\n我想看最近 7 天的体重走势 vs 各部位围度走势的关系(腰围真的在变小吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 围度(最近 7 天)', 'data_fields': ['weight_kg', 'waist_cm', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 52},
    {
            'category': '分析',     'wake_word': '看体重 vs 围度(最近 30 天)',     'desc': '看体重 vs 围度(最近 30 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_waist --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 围度(最近 30 天)」。\n\n我想看最近 30 天的体重走势 vs 各部位围度走势的关系(腰围真的在变小吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_waist_30d', 'name': '看体重 vs 围度(最近 30 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_waist --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 围度(最近 30 天)」。\n\n我想看最近 30 天的体重走势 vs 各部位围度走势的关系(腰围真的在变小吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 围度(最近 30 天)', 'data_fields': ['weight_kg', 'waist_cm', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 53},
    {
            'category': '分析',     'wake_word': '看体重 vs 围度(最近 90 天)',     'desc': '看体重 vs 围度(最近 90 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_waist --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 围度(最近 90 天)」。\n\n我想看最近 90 天的体重走势 vs 各部位围度走势的关系(腰围真的在变小吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_waist_90d', 'name': '看体重 vs 围度(最近 90 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_waist --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 围度(最近 90 天)」。\n\n我想看最近 90 天的体重走势 vs 各部位围度走势的关系(腰围真的在变小吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 围度(最近 90 天)', 'data_fields': ['weight_kg', 'waist_cm', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 54},
    {
            'category': '分析',     'wake_word': '看体重 vs 围度(最近 180 天)',     'desc': '看体重 vs 围度(最近 180 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_waist --window 180d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 围度(最近 180 天)」。\n\n我想看最近 180 天的体重走势 vs 各部位围度走势的关系(腰围真的在变小吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_waist_180d', 'name': '看体重 vs 围度(最近 180 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_waist --window 180d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 围度(最近 180 天)」。\n\n我想看最近 180 天的体重走势 vs 各部位围度走势的关系(腰围真的在变小吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 围度(最近 180 天)', 'data_fields': ['weight_kg', 'waist_cm', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 55},
    {
            'category': '分析',     'wake_word': '看体重 vs 围度(最近 365 天)',     'desc': '看体重 vs 围度(最近 365 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_waist --window 365d', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 围度(最近 365 天)」。\n\n我想看最近 365 天的体重走势 vs 各部位围度走势的关系(腰围真的在变小吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_waist_365d', 'name': '看体重 vs 围度(最近 365 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_waist --window 365d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 围度(最近 365 天)」。\n\n我想看最近 365 天的体重走势 vs 各部位围度走势的关系(腰围真的在变小吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 围度(最近 365 天)', 'data_fields': ['weight_kg', 'waist_cm', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 56},
    {
            'category': '分析',     'wake_word': '看体重 vs 围度(自定义)',     'desc': '看体重 vs 围度(自定义)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair weight_waist --window custom --start <开始日期> --end <结束日期>', 'text': '请你加载技能 卡路里,执行唤醒词「看体重 vs 围度(自定义)」。\n\n我想看体重走势 vs 各部位围度走势的关系(腰围真的在变小吗)。请帮我分析自定义时间段(开始日期到结束日期)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_weight_waist_custom', 'name': '看体重 vs 围度(自定义)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair weight_waist --window custom --start <开始日期> --end <结束日期>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重 vs 围度(自定义)」。\n\n我想看体重走势 vs 各部位围度走势的关系(腰围真的在变小吗)。请帮我分析自定义时间段(开始日期到结束日期)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看体重 vs 围度(自定义时间段)', 'data_fields': ['weight_kg', 'waist_cm', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 57},
    {
            'category': '分析',     'wake_word': '看饮水 vs 体重(最近 30 天)',     'desc': '看饮水 vs 体重(最近 30 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair water_weight --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「看饮水 vs 体重(最近 30 天)」。\n\n我想看最近 30 天的饮水量 vs 体重的关系(喝水多少影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_water_weight_30d', 'name': '看饮水 vs 体重(最近 30 天)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair water_weight --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看饮水 vs 体重(最近 30 天)」。\n\n我想看最近 30 天的饮水量 vs 体重的关系(喝水多少影响体重吗)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看饮水 vs 体重(最近 30 天)', 'data_fields': ['water_ml', 'weight_kg', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 58},
    {
            'category': '分析',     'wake_word': '看饮水 vs 体重(自定义)',     'desc': '看饮水 vs 体重(自定义)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair water_weight --window custom --start <开始日期> --end <结束日期>', 'text': '请你加载技能 卡路里,执行唤醒词「看饮水 vs 体重(自定义)」。\n\n我想看饮水量 vs 体重的关系(喝水多少影响体重吗)。请帮我分析自定义时间段(开始日期到结束日期)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'cross_water_weight_custom', 'name': '看饮水 vs 体重(自定义)', 'subfunction': '组合分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair water_weight --window custom --start <开始日期> --end <结束日期>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看饮水 vs 体重(自定义)」。\n\n我想看饮水量 vs 体重的关系(喝水多少影响体重吗)。请帮我分析自定义时间段(开始日期到结束日期)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看饮水 vs 体重(自定义时间段)', 'data_fields': ['water_ml', 'weight_kg', 'correlation', 'regression', 'strat'],
            'depends_on_external': False, 'order': 59},
    {
            'category': '分析',     'wake_word': '看健康报告(本周)',     'desc': '看健康报告(本周)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view report --kind full --window week_cur', 'text': '请你加载技能 卡路里,执行唤醒词「看健康报告(本周)」。\n\n我想看本周的跨 8 维综合健康报告(饮食/运动/体重/饮水/体脂/围度/缺口/目标)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'report_full_week_cur', 'name': '看健康报告(本周)', 'subfunction': '健康报告', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view report --kind full --window week_cur', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看健康报告(本周)」。\n\n我想看本周的跨 8 维综合健康报告(饮食/运动/体重/饮水/体脂/围度/缺口/目标)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看本周的综合健康报告', 'data_fields': ['calories', 'exercise_kcal', 'weight_kg', 'water_ml', 'deficit', 'body_fat_pct', 'waist_cm', 'anomaly'],
            'depends_on_external': False, 'order': 60},
    {
            'category': '分析',     'wake_word': '看健康报告(上周)',     'desc': '看健康报告(上周)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view report --kind full --window week_prev', 'text': '请你加载技能 卡路里,执行唤醒词「看健康报告(上周)」。\n\n我想看上周的跨 8 维综合健康报告(饮食/运动/体重/饮水/体脂/围度/缺口/目标)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'report_full_week_prev', 'name': '看健康报告(上周)', 'subfunction': '健康报告', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view report --kind full --window week_prev', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看健康报告(上周)」。\n\n我想看上周的跨 8 维综合健康报告(饮食/运动/体重/饮水/体脂/围度/缺口/目标)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看上周的综合健康报告', 'data_fields': ['calories', 'exercise_kcal', 'weight_kg', 'water_ml', 'deficit', 'body_fat_pct', 'waist_cm', 'anomaly'],
            'depends_on_external': False, 'order': 61},
    {
            'category': '分析',     'wake_word': '看健康报告(最近 7 天)',     'desc': '看健康报告(最近 7 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view report --kind full --window 7d', 'text': '请你加载技能 卡路里,执行唤醒词「看健康报告(最近 7 天)」。\n\n我想看最近 7 天的跨 8 维综合健康报告(饮食/运动/体重/饮水/体脂/围度/缺口/目标)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'report_full_7d', 'name': '看健康报告(最近 7 天)', 'subfunction': '健康报告', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view report --kind full --window 7d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看健康报告(最近 7 天)」。\n\n我想看最近 7 天的跨 8 维综合健康报告(饮食/运动/体重/饮水/体脂/围度/缺口/目标)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 7 天的综合健康报告', 'data_fields': ['calories', 'exercise_kcal', 'weight_kg', 'water_ml', 'deficit', 'body_fat_pct', 'waist_cm', 'anomaly'],
            'depends_on_external': False, 'order': 62},
    {
            'category': '分析',     'wake_word': '看健康报告(最近 30 天)',     'desc': '看健康报告(最近 30 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view report --kind full --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「看健康报告(最近 30 天)」。\n\n我想看最近 30 天的跨 8 维综合健康报告(饮食/运动/体重/饮水/体脂/围度/缺口/目标)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'report_full_30d', 'name': '看健康报告(最近 30 天)', 'subfunction': '健康报告', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view report --kind full --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看健康报告(最近 30 天)」。\n\n我想看最近 30 天的跨 8 维综合健康报告(饮食/运动/体重/饮水/体脂/围度/缺口/目标)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 30 天的综合健康报告', 'data_fields': ['calories', 'exercise_kcal', 'weight_kg', 'water_ml', 'deficit', 'body_fat_pct', 'waist_cm', 'anomaly'],
            'depends_on_external': False, 'order': 63},
    {
            'category': '分析',     'wake_word': '看健康报告(最近 90 天)',     'desc': '看健康报告(最近 90 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view report --kind full --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「看健康报告(最近 90 天)」。\n\n我想看最近 90 天的跨 8 维综合健康报告(饮食/运动/体重/饮水/体脂/围度/缺口/目标)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'report_full_90d', 'name': '看健康报告(最近 90 天)', 'subfunction': '健康报告', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view report --kind full --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看健康报告(最近 90 天)」。\n\n我想看最近 90 天的跨 8 维综合健康报告(饮食/运动/体重/饮水/体脂/围度/缺口/目标)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 90 天的综合健康报告', 'data_fields': ['calories', 'exercise_kcal', 'weight_kg', 'water_ml', 'deficit', 'body_fat_pct', 'waist_cm', 'anomaly'],
            'depends_on_external': False, 'order': 64},
    {
            'category': '分析',     'wake_word': '看健康报告(最近 180 天)',     'desc': '看健康报告(最近 180 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view report --kind full --window 180d', 'text': '请你加载技能 卡路里,执行唤醒词「看健康报告(最近 180 天)」。\n\n我想看最近 180 天的跨 8 维综合健康报告(饮食/运动/体重/饮水/体脂/围度/缺口/目标)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'report_full_180d', 'name': '看健康报告(最近 180 天)', 'subfunction': '健康报告', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view report --kind full --window 180d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看健康报告(最近 180 天)」。\n\n我想看最近 180 天的跨 8 维综合健康报告(饮食/运动/体重/饮水/体脂/围度/缺口/目标)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 180 天的综合健康报告', 'data_fields': ['calories', 'exercise_kcal', 'weight_kg', 'water_ml', 'deficit', 'body_fat_pct', 'waist_cm', 'anomaly'],
            'depends_on_external': False, 'order': 65},
    {
            'category': '分析',     'wake_word': '看健康报告(最近 365 天)',     'desc': '看健康报告(最近 365 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view report --kind full --window 365d', 'text': '请你加载技能 卡路里,执行唤醒词「看健康报告(最近 365 天)」。\n\n我想看最近 365 天的跨 8 维综合健康报告(饮食/运动/体重/饮水/体脂/围度/缺口/目标)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'report_full_365d', 'name': '看健康报告(最近 365 天)', 'subfunction': '健康报告', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view report --kind full --window 365d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看健康报告(最近 365 天)」。\n\n我想看最近 365 天的跨 8 维综合健康报告(饮食/运动/体重/饮水/体脂/围度/缺口/目标)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看最近 365 天的综合健康报告', 'data_fields': ['calories', 'exercise_kcal', 'weight_kg', 'water_ml', 'deficit', 'body_fat_pct', 'waist_cm', 'anomaly'],
            'depends_on_external': False, 'order': 66},
    {
            'category': '分析',     'wake_word': '看健康报告(本月)',     'desc': '看健康报告(本月)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view report --kind full --window month_cur', 'text': '请你加载技能 卡路里,执行唤醒词「看健康报告(本月)」。\n\n我想看本月的跨 8 维综合健康报告(饮食/运动/体重/饮水/体脂/围度/缺口/目标)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'report_full_month_cur', 'name': '看健康报告(本月)', 'subfunction': '健康报告', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view report --kind full --window month_cur', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看健康报告(本月)」。\n\n我想看本月的跨 8 维综合健康报告(饮食/运动/体重/饮水/体脂/围度/缺口/目标)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看本月的综合健康报告', 'data_fields': ['calories', 'exercise_kcal', 'weight_kg', 'water_ml', 'deficit', 'body_fat_pct', 'waist_cm', 'anomaly'],
            'depends_on_external': False, 'order': 67},
    {
            'category': '分析',     'wake_word': '看健康报告(上月)',     'desc': '看健康报告(上月)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view report --kind full --window month_prev', 'text': '请你加载技能 卡路里,执行唤醒词「看健康报告(上月)」。\n\n我想看上月的跨 8 维综合健康报告(饮食/运动/体重/饮水/体脂/围度/缺口/目标)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'report_full_month_prev', 'name': '看健康报告(上月)', 'subfunction': '健康报告', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view report --kind full --window month_prev', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看健康报告(上月)」。\n\n我想看上月的跨 8 维综合健康报告(饮食/运动/体重/饮水/体脂/围度/缺口/目标)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看上月的综合健康报告', 'data_fields': ['calories', 'exercise_kcal', 'weight_kg', 'water_ml', 'deficit', 'body_fat_pct', 'waist_cm', 'anomaly'],
            'depends_on_external': False, 'order': 68},
    {
            'category': '分析',     'wake_word': '看健康报告(今年)',     'desc': '看健康报告(今年)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view report --kind full --window year_cur', 'text': '请你加载技能 卡路里,执行唤醒词「看健康报告(今年)」。\n\n我想看今年的跨 8 维综合健康报告(饮食/运动/体重/饮水/体脂/围度/缺口/目标)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'report_full_year_cur', 'name': '看健康报告(今年)', 'subfunction': '健康报告', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view report --kind full --window year_cur', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看健康报告(今年)」。\n\n我想看今年的跨 8 维综合健康报告(饮食/运动/体重/饮水/体脂/围度/缺口/目标)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看今年的综合健康报告', 'data_fields': ['calories', 'exercise_kcal', 'weight_kg', 'water_ml', 'deficit', 'body_fat_pct', 'waist_cm', 'anomaly'],
            'depends_on_external': False, 'order': 69},
    {
            'category': '分析',     'wake_word': '看健康报告(自定义)',     'desc': '看健康报告(自定义)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view report --kind full --window custom --start <开始日期> --end <结束日期>', 'text': '请你加载技能 卡路里,执行唤醒词「看健康报告(自定义)」。\n\n我想看自定义时间段(开始日期到结束日期)的跨 8 维综合健康报告(饮食/运动/体重/饮水/体脂/围度/缺口/目标)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期:____\n结束日期:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'report_full_custom', 'name': '看健康报告(自定义)', 'subfunction': '健康报告', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view report --kind full --window custom --start <开始日期> --end <结束日期>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看健康报告(自定义)」。\n\n我想看自定义时间段(开始日期到结束日期)的跨 8 维综合健康报告(饮食/运动/体重/饮水/体脂/围度/缺口/目标)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期:____\n结束日期:____',
            'user_intent': '看自定义时间段的综合健康报告', 'data_fields': ['calories', 'exercise_kcal', 'weight_kg', 'water_ml', 'deficit', 'body_fat_pct', 'waist_cm', 'anomaly'],
            'depends_on_external': False, 'order': 70},
    {
            'category': '分析',     'wake_word': '看BMI报告',     'desc': '看BMI报告',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view report --kind bmi --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「看BMI报告」。\n\n我想看BMI报告。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'report_bmi', 'name': '看BMI报告', 'subfunction': '健康报告', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view report --kind bmi --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看BMI报告」。\n\n我想看BMI报告。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看BMI报告', 'data_fields': ['bmi', 'height_cm', 'milestones'],
            'depends_on_external': False, 'order': 71},
    {
            'category': '分析',     'wake_word': '看TDEE报告',     'desc': '看TDEE报告',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view report --kind tdee --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「看TDEE报告」。\n\n我想看TDEE报告。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'report_tdee', 'name': '看TDEE报告', 'subfunction': '健康报告', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view report --kind tdee --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看TDEE报告」。\n\n我想看TDEE报告。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看TDEE报告', 'data_fields': ['tdee', 'activity_factor', 'calories', 'deficit'],
            'depends_on_external': False, 'order': 72},
    {
            'category': '分析',     'wake_word': '看BMR报告',     'desc': '看BMR报告',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view report --kind bmr --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「看BMR报告」。\n\n我想看BMR报告。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'report_bmr', 'name': '看BMR报告', 'subfunction': '健康报告', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view report --kind bmr --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看BMR报告」。\n\n我想看BMR报告。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看BMR报告', 'data_fields': ['bmr', 'tdee', 'calories', 'under_bmr_days'],
            'depends_on_external': False, 'order': 73},
    {
            'category': '分析',     'wake_word': '看蛋白质摄入报告',     'desc': '看蛋白质摄入报告',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view report --kind protein --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「看蛋白质摄入报告」。\n\n我想看蛋白质摄入报告。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'report_protein', 'name': '看蛋白质摄入报告', 'subfunction': '健康报告', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view report --kind protein --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看蛋白质摄入报告」。\n\n我想看蛋白质摄入报告。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看蛋白质摄入报告', 'data_fields': ['protein', 'weight_kg', 'rate', 'trend'],
            'depends_on_external': False, 'order': 74},
    {
            'category': '分析',     'wake_word': '看水分摄入报告',     'desc': '看水分摄入报告',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view report --kind water --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「看水分摄入报告」。\n\n我想看水分摄入报告。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'report_water', 'name': '看水分摄入报告', 'subfunction': '健康报告', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view report --kind water --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看水分摄入报告」。\n\n我想看水分摄入报告。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看水分摄入报告', 'data_fields': ['water_ml', 'water_goal', 'rate'],
            'depends_on_external': False, 'order': 75},
    {
            'category': '分析',     'wake_word': '看综合评分',     'desc': '看综合评分',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view report --kind score --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「看综合评分」。\n\n我想看综合评分。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'report_score', 'name': '看综合评分', 'subfunction': '健康报告', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view report --kind score --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看综合评分」。\n\n我想看综合评分。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看综合评分', 'data_fields': ['score', 'items', 'history'],
            'depends_on_external': False, 'order': 76},
    {
            'category': '分析',     'wake_word': '看健康趋势',     'desc': '看健康趋势',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view report --kind trend --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「看健康趋势」。\n\n我想看健康趋势。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'report_trend', 'name': '看健康趋势', 'subfunction': '健康报告', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view report --kind trend --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看健康趋势」。\n\n我想看健康趋势。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看健康趋势', 'data_fields': ['score', 'history', 'direction'],
            'depends_on_external': False, 'order': 77},
    {
            'category': '分析',     'wake_word': '看健康报告(含对比)',     'desc': '看健康报告(含对比)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view report --kind compare --window 本周', 'text': '请你加载技能 卡路里,执行唤醒词「看健康报告(含对比)」。\n\n我想看健康报告(含对比)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'report_compare', 'name': '看健康报告(含对比)', 'subfunction': '健康报告', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view report --kind compare --window 本周', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看健康报告(含对比)」。\n\n我想看健康报告(含对比)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看健康报告(含对比)', 'data_fields': ['deltas', 'top3'],
            'depends_on_external': False, 'order': 78},
    {
            'category': '分析',     'wake_word': '看整体趋势(体重+摄入+运动)',     'desc': '看整体趋势(体重+摄入+运动)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view trend --group g1 --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「看整体趋势(体重+摄入+运动)」。\n\n我想看多指标整体趋势(「体重+摄入+运动」3 个以上指标同图)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'trend_g1', 'name': '看整体趋势(体重+摄入+运动)', 'subfunction': '整体趋势', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view trend --group g1 --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看整体趋势(体重+摄入+运动)」。\n\n我想看多指标整体趋势(「体重+摄入+运动」3 个以上指标同图)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看「体重+摄入+运动」多指标整体趋势', 'data_fields': ['weight_kg', 'calories', 'exercise_kcal', 'protein', 'body_fat_pct', 'waist_cm', 'deficit', 'water_ml'],
            'depends_on_external': False, 'order': 79},
    {
            'category': '分析',     'wake_word': '看整体趋势(体重+体脂+围度)',     'desc': '看整体趋势(体重+体脂+围度)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view trend --group g2 --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「看整体趋势(体重+体脂+围度)」。\n\n我想看多指标整体趋势(「体重+体脂+围度」3 个以上指标同图)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'trend_g2', 'name': '看整体趋势(体重+体脂+围度)', 'subfunction': '整体趋势', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view trend --group g2 --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看整体趋势(体重+体脂+围度)」。\n\n我想看多指标整体趋势(「体重+体脂+围度」3 个以上指标同图)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看「体重+体脂+围度」多指标整体趋势', 'data_fields': ['weight_kg', 'calories', 'exercise_kcal', 'protein', 'body_fat_pct', 'waist_cm', 'deficit', 'water_ml'],
            'depends_on_external': False, 'order': 80},
    {
            'category': '分析',     'wake_word': '看整体趋势(饮食+蛋白+纤维)',     'desc': '看整体趋势(饮食+蛋白+纤维)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view trend --group g3 --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「看整体趋势(饮食+蛋白+纤维)」。\n\n我想看多指标整体趋势(「饮食+蛋白+纤维」3 个以上指标同图)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'trend_g3', 'name': '看整体趋势(饮食+蛋白+纤维)', 'subfunction': '整体趋势', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view trend --group g3 --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看整体趋势(饮食+蛋白+纤维)」。\n\n我想看多指标整体趋势(「饮食+蛋白+纤维」3 个以上指标同图)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看「饮食+蛋白+纤维」多指标整体趋势', 'data_fields': ['weight_kg', 'calories', 'exercise_kcal', 'protein', 'body_fat_pct', 'waist_cm', 'deficit', 'water_ml'],
            'depends_on_external': False, 'order': 81},
    {
            'category': '分析',     'wake_word': '看整体趋势(运动+力量+有氧)',     'desc': '看整体趋势(运动+力量+有氧)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view trend --group g4 --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「看整体趋势(运动+力量+有氧)」。\n\n我想看多指标整体趋势(「运动+力量+有氧」3 个以上指标同图)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'trend_g4', 'name': '看整体趋势(运动+力量+有氧)', 'subfunction': '整体趋势', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view trend --group g4 --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看整体趋势(运动+力量+有氧)」。\n\n我想看多指标整体趋势(「运动+力量+有氧」3 个以上指标同图)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看「运动+力量+有氧」多指标整体趋势', 'data_fields': ['weight_kg', 'calories', 'exercise_kcal', 'protein', 'body_fat_pct', 'waist_cm', 'deficit', 'water_ml'],
            'depends_on_external': False, 'order': 82},
    {
            'category': '分析',     'wake_word': '看整体趋势(BMI+体脂+肌肉量)',     'desc': '看整体趋势(BMI+体脂+肌肉量)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view trend --group g5 --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「看整体趋势(BMI+体脂+肌肉量)」。\n\n我想看多指标整体趋势(「BMI+体脂+肌肉量」3 个以上指标同图)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'trend_g5', 'name': '看整体趋势(BMI+体脂+肌肉量)', 'subfunction': '整体趋势', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view trend --group g5 --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看整体趋势(BMI+体脂+肌肉量)」。\n\n我想看多指标整体趋势(「BMI+体脂+肌肉量」3 个以上指标同图)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看「BMI+体脂+肌肉量」多指标整体趋势', 'data_fields': ['weight_kg', 'calories', 'exercise_kcal', 'protein', 'body_fat_pct', 'waist_cm', 'deficit', 'water_ml'],
            'depends_on_external': False, 'order': 83},
    {
            'category': '分析',     'wake_word': '看整体趋势(摄入+蛋白+运动)',     'desc': '看整体趋势(摄入+蛋白+运动)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view trend --group g6 --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「看整体趋势(摄入+蛋白+运动)」。\n\n我想看多指标整体趋势(「摄入+蛋白+运动」3 个以上指标同图)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'trend_g6', 'name': '看整体趋势(摄入+蛋白+运动)', 'subfunction': '整体趋势', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view trend --group g6 --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看整体趋势(摄入+蛋白+运动)」。\n\n我想看多指标整体趋势(「摄入+蛋白+运动」3 个以上指标同图)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看「摄入+蛋白+运动」多指标整体趋势', 'data_fields': ['weight_kg', 'calories', 'exercise_kcal', 'protein', 'body_fat_pct', 'waist_cm', 'deficit', 'water_ml'],
            'depends_on_external': False, 'order': 84},
    {
            'category': '分析',     'wake_word': '看整体趋势(体重+蛋白+缺口)',     'desc': '看整体趋势(体重+蛋白+缺口)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view trend --group g7 --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「看整体趋势(体重+蛋白+缺口)」。\n\n我想看多指标整体趋势(「体重+蛋白+缺口」3 个以上指标同图)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'trend_g7', 'name': '看整体趋势(体重+蛋白+缺口)', 'subfunction': '整体趋势', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view trend --group g7 --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看整体趋势(体重+蛋白+缺口)」。\n\n我想看多指标整体趋势(「体重+蛋白+缺口」3 个以上指标同图)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看「体重+蛋白+缺口」多指标整体趋势', 'data_fields': ['weight_kg', 'calories', 'exercise_kcal', 'protein', 'body_fat_pct', 'waist_cm', 'deficit', 'water_ml'],
            'depends_on_external': False, 'order': 85},
    {
            'category': '分析',     'wake_word': '看整体趋势(体重+摄入+缺口)',     'desc': '看整体趋势(体重+摄入+缺口)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view trend --group g8 --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「看整体趋势(体重+摄入+缺口)」。\n\n我想看多指标整体趋势(「体重+摄入+缺口」3 个以上指标同图)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'trend_g8', 'name': '看整体趋势(体重+摄入+缺口)', 'subfunction': '整体趋势', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view trend --group g8 --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看整体趋势(体重+摄入+缺口)」。\n\n我想看多指标整体趋势(「体重+摄入+缺口」3 个以上指标同图)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看「体重+摄入+缺口」多指标整体趋势', 'data_fields': ['weight_kg', 'calories', 'exercise_kcal', 'protein', 'body_fat_pct', 'waist_cm', 'deficit', 'water_ml'],
            'depends_on_external': False, 'order': 86},
    {
            'category': '分析',     'wake_word': '看整体趋势(体重+摄入+运动+缺口)',     'desc': '看整体趋势(体重+摄入+运动+缺口)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view trend --group g9 --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「看整体趋势(体重+摄入+运动+缺口)」。\n\n我想看多指标整体趋势(「体重+摄入+运动+缺口」3 个以上指标同图)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'trend_g9', 'name': '看整体趋势(体重+摄入+运动+缺口)', 'subfunction': '整体趋势', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view trend --group g9 --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看整体趋势(体重+摄入+运动+缺口)」。\n\n我想看多指标整体趋势(「体重+摄入+运动+缺口」3 个以上指标同图)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看「体重+摄入+运动+缺口」多指标整体趋势', 'data_fields': ['weight_kg', 'calories', 'exercise_kcal', 'protein', 'body_fat_pct', 'waist_cm', 'deficit', 'water_ml'],
            'depends_on_external': False, 'order': 87},
    {
            'category': '分析',     'wake_word': '看整体趋势(蛋白+运动)',     'desc': '看整体趋势(蛋白+运动)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view trend --group g10 --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「看整体趋势(蛋白+运动)」。\n\n我想看多指标整体趋势(「蛋白+运动」3 个以上指标同图)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'trend_g10', 'name': '看整体趋势(蛋白+运动)', 'subfunction': '整体趋势', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view trend --group g10 --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看整体趋势(蛋白+运动)」。\n\n我想看多指标整体趋势(「蛋白+运动」3 个以上指标同图)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看「蛋白+运动」多指标整体趋势', 'data_fields': ['weight_kg', 'calories', 'exercise_kcal', 'protein', 'body_fat_pct', 'waist_cm', 'deficit', 'water_ml'],
            'depends_on_external': False, 'order': 88},
    {
            'category': '分析',     'wake_word': '看整体趋势(综合多指标)',     'desc': '看整体趋势(综合多指标)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view trend --group g11 --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「看整体趋势(综合多指标)」。\n\n我想看多指标整体趋势(「综合多指标」3 个以上指标同图)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'trend_g11', 'name': '看整体趋势(综合多指标)', 'subfunction': '整体趋势', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view trend --group g11 --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看整体趋势(综合多指标)」。\n\n我想看多指标整体趋势(「综合多指标」3 个以上指标同图)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看「综合多指标」多指标整体趋势', 'data_fields': ['weight_kg', 'calories', 'exercise_kcal', 'protein', 'body_fat_pct', 'waist_cm', 'deficit', 'water_ml'],
            'depends_on_external': False, 'order': 89},
    {
            'category': '分析',     'wake_word': '看整体趋势(含月度对比)',     'desc': '看整体趋势(含月度对比)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view trend --group g11 --window 60d --period monthly', 'text': '请你加载技能 卡路里,执行唤醒词「看整体趋势(含月度对比)」。\n\n我想看全维度综合趋势图并含周期对比(含月度对比)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'trend_period_monthly', 'name': '看整体趋势(含月度对比)', 'subfunction': '整体趋势', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view trend --group g11 --window 60d --period monthly', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看整体趋势(含月度对比)」。\n\n我想看全维度综合趋势图并含周期对比(含月度对比)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看整体趋势并含含月度对比', 'data_fields': ['weight_kg', 'calories', 'exercise_kcal', 'protein', 'deficit', 'water_ml', 'period_compare'],
            'depends_on_external': False, 'order': 90},
    {
            'category': '分析',     'wake_word': '看整体趋势(含季度对比)',     'desc': '看整体趋势(含季度对比)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view trend --group g11 --window 180d --period quarterly', 'text': '请你加载技能 卡路里,执行唤醒词「看整体趋势(含季度对比)」。\n\n我想看全维度综合趋势图并含周期对比(含季度对比)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'trend_period_quarterly', 'name': '看整体趋势(含季度对比)', 'subfunction': '整体趋势', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view trend --group g11 --window 180d --period quarterly', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看整体趋势(含季度对比)」。\n\n我想看全维度综合趋势图并含周期对比(含季度对比)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看整体趋势并含含季度对比', 'data_fields': ['weight_kg', 'calories', 'exercise_kcal', 'protein', 'deficit', 'water_ml', 'period_compare'],
            'depends_on_external': False, 'order': 91},
    {
            'category': '分析',     'wake_word': '看整体趋势(含年度对比)',     'desc': '看整体趋势(含年度对比)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view trend --group g11 --window 730d --period yearly', 'text': '请你加载技能 卡路里,执行唤醒词「看整体趋势(含年度对比)」。\n\n我想看全维度综合趋势图并含周期对比(含年度对比)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'trend_period_yearly', 'name': '看整体趋势(含年度对比)', 'subfunction': '整体趋势', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view trend --group g11 --window 730d --period yearly', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看整体趋势(含年度对比)」。\n\n我想看全维度综合趋势图并含周期对比(含年度对比)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看整体趋势并含含年度对比', 'data_fields': ['weight_kg', 'calories', 'exercise_kcal', 'protein', 'deficit', 'water_ml', 'period_compare'],
            'depends_on_external': False, 'order': 92},
    {
            'category': '分析',     'wake_word': '看整体趋势(含目标对比)',     'desc': '看整体趋势(含目标对比)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view trend --group g11 --window 90d --period target', 'text': '请你加载技能 卡路里,执行唤醒词「看整体趋势(含目标对比)」。\n\n我想看全维度综合趋势图并含周期对比(含目标对比)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'trend_period_target', 'name': '看整体趋势(含目标对比)', 'subfunction': '整体趋势', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view trend --group g11 --window 90d --period target', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看整体趋势(含目标对比)」。\n\n我想看全维度综合趋势图并含周期对比(含目标对比)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看整体趋势并含含目标对比', 'data_fields': ['weight_kg', 'calories', 'exercise_kcal', 'protein', 'deficit', 'water_ml', 'period_compare'],
            'depends_on_external': False, 'order': 93},
    {
            'category': '分析',     'wake_word': '诊断体重波动原因',     'desc': '诊断体重波动原因',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view anomaly --diagnose weight_volatility --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「诊断体重波动原因」。\n\n我想诊断体重波动的来源(为什么忽上忽下)。并分解波动来源(水分/盐分/摄入)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diag_weight_volatility', 'name': '诊断体重波动原因', 'subfunction': '自动分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view anomaly --diagnose weight_volatility --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「诊断体重波动原因」。\n\n我想诊断体重波动的来源(为什么忽上忽下)。并分解波动来源(水分/盐分/摄入)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '诊断: 诊断体重波动原因', 'data_fields': ['findings', 'confidence', 'degraded', 'insight'],
            'depends_on_external': False, 'order': 94},
    {
            'category': '分析',     'wake_word': '诊断体重停滞(含平台期判断)',     'desc': '诊断体重停滞(含平台期判断)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view anomaly --diagnose weight_plateau --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「诊断体重停滞(含平台期判断)」。\n\n我想诊断体重停滞:帮我判断是否进入平台期(≥14 天体重变化 ≤±0.5kg)。数据不足时降级提示。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diag_weight_plateau', 'name': '诊断体重停滞(含平台期判断)', 'subfunction': '自动分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view anomaly --diagnose weight_plateau --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「诊断体重停滞(含平台期判断)」。\n\n我想诊断体重停滞:帮我判断是否进入平台期(≥14 天体重变化 ≤±0.5kg)。数据不足时降级提示。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '诊断: 诊断体重停滞(含平台期判断)', 'data_fields': ['findings', 'confidence', 'degraded', 'insight'],
            'depends_on_external': False, 'order': 95},
    {
            'category': '分析',     'wake_word': '诊断体重反弹',     'desc': '诊断体重反弹',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view anomaly --diagnose weight_rebound --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「诊断体重反弹」。\n\n我想诊断体重反弹:追溯反弹起点与可能原因(摄入回升/水分滞留/盐分)。数据不足时降级提示。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diag_weight_rebound', 'name': '诊断体重反弹', 'subfunction': '自动分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view anomaly --diagnose weight_rebound --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「诊断体重反弹」。\n\n我想诊断体重反弹:追溯反弹起点与可能原因(摄入回升/水分滞留/盐分)。数据不足时降级提示。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '诊断: 诊断体重反弹', 'data_fields': ['findings', 'confidence', 'degraded', 'insight'],
            'depends_on_external': False, 'order': 96},
    {
            'category': '分析',     'wake_word': '诊断体重下降原因',     'desc': '诊断体重下降原因',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view anomaly --diagnose weight_loss_cause --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「诊断体重下降原因」。\n\n我想诊断近期体重下降的原因:评估速度是否健康(0.5-1kg/周),区分来自饮食缺口还是运动。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diag_weight_loss_cause', 'name': '诊断体重下降原因', 'subfunction': '自动分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view anomaly --diagnose weight_loss_cause --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「诊断体重下降原因」。\n\n我想诊断近期体重下降的原因:评估速度是否健康(0.5-1kg/周),区分来自饮食缺口还是运动。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '诊断: 诊断体重下降原因', 'data_fields': ['findings', 'confidence', 'degraded', 'insight'],
            'depends_on_external': False, 'order': 97},
    {
            'category': '分析',     'wake_word': '诊断体重异常点',     'desc': '诊断体重异常点',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view anomaly --diagnose weight_anomaly --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「诊断体重异常点」。\n\n我想找出体重记录里的异常点(偏离均值过大的日期)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diag_weight_anomaly', 'name': '诊断体重异常点', 'subfunction': '自动分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view anomaly --diagnose weight_anomaly --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「诊断体重异常点」。\n\n我想找出体重记录里的异常点(偏离均值过大的日期)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '诊断: 诊断体重异常点', 'data_fields': ['findings', 'confidence', 'degraded', 'insight'],
            'depends_on_external': False, 'order': 98},
    {
            'category': '分析',     'wake_word': '诊断体重vs体脂围度背离',     'desc': '诊断体重vs体脂围度背离',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view anomaly --diagnose weight_divergence --window 180d', 'text': '请你加载技能 卡路里,执行唤醒词「诊断体重vs体脂围度背离」。\n\n我想诊断体重与体脂/围度是否背离(体重没变但腰细了?体重降但体脂没降?):背离检测。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diag_weight_divergence', 'name': '诊断体重vs体脂围度背离', 'subfunction': '自动分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view anomaly --diagnose weight_divergence --window 180d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「诊断体重vs体脂围度背离」。\n\n我想诊断体重与体脂/围度是否背离(体重没变但腰细了?体重降但体脂没降?):背离检测。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '诊断: 诊断体重vs体脂围度背离', 'data_fields': ['findings', 'confidence', 'degraded', 'insight'],
            'depends_on_external': False, 'order': 99},
    {
            'category': '分析',     'wake_word': '诊断饮食超标',     'desc': '诊断饮食超标',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view anomaly --diagnose diet_over --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「诊断饮食超标」。\n\n我想诊断我的饮食是否超标:超标日统计 + 超标来源食物 TOP。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diag_diet_over', 'name': '诊断饮食超标', 'subfunction': '自动分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view anomaly --diagnose diet_over --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「诊断饮食超标」。\n\n我想诊断我的饮食是否超标:超标日统计 + 超标来源食物 TOP。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '诊断: 诊断饮食超标', 'data_fields': ['findings', 'confidence', 'degraded', 'insight'],
            'depends_on_external': False, 'order': 100},
    {
            'category': '分析',     'wake_word': '诊断饮食不足',     'desc': '诊断饮食不足',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view anomaly --diagnose diet_under --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「诊断饮食不足」。\n\n我想诊断我的饮食是否不足:低于 BMR 天数。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diag_diet_under', 'name': '诊断饮食不足', 'subfunction': '自动分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view anomaly --diagnose diet_under --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「诊断饮食不足」。\n\n我想诊断我的饮食是否不足:低于 BMR 天数。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '诊断: 诊断饮食不足', 'data_fields': ['findings', 'confidence', 'degraded', 'insight'],
            'depends_on_external': False, 'order': 101},
    {
            'category': '分析',     'wake_word': '诊断营养不均衡(含均衡判断)',     'desc': '诊断营养不均衡(含均衡判断)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view anomaly --diagnose diet_unbalanced --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「诊断营养不均衡(含均衡判断)」。\n\n我想诊断我的营养是否均衡:三大营养占比 + 失衡维度 + 钠摄入。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diag_diet_unbalanced', 'name': '诊断营养不均衡(含均衡判断)', 'subfunction': '自动分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view anomaly --diagnose diet_unbalanced --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「诊断营养不均衡(含均衡判断)」。\n\n我想诊断我的营养是否均衡:三大营养占比 + 失衡维度 + 钠摄入。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '诊断: 诊断营养不均衡(含均衡判断)', 'data_fields': ['findings', 'confidence', 'degraded', 'insight'],
            'depends_on_external': False, 'order': 102},
    {
            'category': '分析',     'wake_word': '诊断饮食结构问题',     'desc': '诊断饮食结构问题',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view anomaly --diagnose diet_structure --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「诊断饮食结构问题」。\n\n我想诊断我的饮食结构:餐次分布(早/午/晚/夜宵)+ 单日进食频率 + 结构定位。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diag_diet_structure', 'name': '诊断饮食结构问题', 'subfunction': '自动分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view anomaly --diagnose diet_structure --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「诊断饮食结构问题」。\n\n我想诊断我的饮食结构:餐次分布(早/午/晚/夜宵)+ 单日进食频率 + 结构定位。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '诊断: 诊断饮食结构问题', 'data_fields': ['findings', 'confidence', 'degraded', 'insight'],
            'depends_on_external': False, 'order': 103},
    {
            'category': '分析',     'wake_word': '诊断运动不足',     'desc': '诊断运动不足',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view anomaly --diagnose exercise_insufficient --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「诊断运动不足」。\n\n我想诊断我的运动是否不足:运动频率(次/周)+ 日均消耗 + 与建议对比。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diag_exercise_insufficient', 'name': '诊断运动不足', 'subfunction': '自动分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view anomaly --diagnose exercise_insufficient --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「诊断运动不足」。\n\n我想诊断我的运动是否不足:运动频率(次/周)+ 日均消耗 + 与建议对比。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '诊断: 诊断运动不足', 'data_fields': ['findings', 'confidence', 'degraded', 'insight'],
            'depends_on_external': False, 'order': 104},
    {
            'category': '分析',     'wake_word': '诊断运动过量',     'desc': '诊断运动过量',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view anomaly --diagnose exercise_overload --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「诊断运动过量」。\n\n我想诊断我是否运动过量:连续训练天数检测。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diag_exercise_overload', 'name': '诊断运动过量', 'subfunction': '自动分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view anomaly --diagnose exercise_overload --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「诊断运动过量」。\n\n我想诊断我是否运动过量:连续训练天数检测。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '诊断: 诊断运动过量', 'data_fields': ['findings', 'confidence', 'degraded', 'insight'],
            'depends_on_external': False, 'order': 105},
    {
            'category': '分析',     'wake_word': '诊断运动类型失衡',     'desc': '诊断运动类型失衡',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view anomaly --diagnose exercise_type_imbalance --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「诊断运动类型失衡」。\n\n我想诊断我的运动类型是否均衡:力量/有氧/柔韧占比 + 建议搭配。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diag_exercise_type_imbalance', 'name': '诊断运动类型失衡', 'subfunction': '自动分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view anomaly --diagnose exercise_type_imbalance --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「诊断运动类型失衡」。\n\n我想诊断我的运动类型是否均衡:力量/有氧/柔韧占比 + 建议搭配。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '诊断: 诊断运动类型失衡', 'data_fields': ['findings', 'confidence', 'degraded', 'insight'],
            'depends_on_external': False, 'order': 106},
    {
            'category': '分析',     'wake_word': '诊断运动效率(含有效判断)',     'desc': '诊断运动效率(含有效判断)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view anomaly --diagnose exercise_efficiency --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「诊断运动效率(含有效判断)」。\n\n我想诊断我的运动效率:单位时长消耗(卡/分钟)+ 分类效率 + 有效性判断。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diag_exercise_efficiency', 'name': '诊断运动效率(含有效判断)', 'subfunction': '自动分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view anomaly --diagnose exercise_efficiency --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「诊断运动效率(含有效判断)」。\n\n我想诊断我的运动效率:单位时长消耗(卡/分钟)+ 分类效率 + 有效性判断。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '诊断: 诊断运动效率(含有效判断)', 'data_fields': ['findings', 'confidence', 'degraded', 'insight'],
            'depends_on_external': False, 'order': 107},
    {
            'category': '分析',     'wake_word': '诊断运动建议(含类型推荐)',     'desc': '诊断运动建议(含类型推荐)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view anomaly --diagnose exercise_advice --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「诊断运动建议(含类型推荐)」。\n\n我想知道我应该加哪种运动:基于当前运动结构的类型推荐 + 频率建议。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diag_exercise_advice', 'name': '诊断运动建议(含类型推荐)', 'subfunction': '自动分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view anomaly --diagnose exercise_advice --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「诊断运动建议(含类型推荐)」。\n\n我想知道我应该加哪种运动:基于当前运动结构的类型推荐 + 频率建议。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '诊断: 诊断运动建议(含类型推荐)', 'data_fields': ['findings', 'confidence', 'degraded', 'insight'],
            'depends_on_external': False, 'order': 108},
    {
            'category': '分析',     'wake_word': '为什么我没瘦',     'desc': '为什么我没瘦',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view anomaly --diagnose why_not_losing --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「为什么我没瘦」。\n\n为什么我没瘦?请全维度归因(缺口是否真的为负/平台期/水分/漏记)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diag_why_not_losing', 'name': '为什么我没瘦', 'subfunction': '自动分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view anomaly --diagnose why_not_losing --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「为什么我没瘦」。\n\n为什么我没瘦?请全维度归因(缺口是否真的为负/平台期/水分/漏记)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '诊断: 为什么我没瘦', 'data_fields': ['findings', 'confidence', 'degraded', 'insight'],
            'depends_on_external': False, 'order': 109},
    {
            'category': '分析',     'wake_word': '为什么我瘦太快',     'desc': '为什么我瘦太快',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view anomaly --diagnose why_losing_fast --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「为什么我瘦太快」。\n\n为什么我瘦太快?请评估速度是否危险(>1.5kg/周 为过快)+ 摄入是否过低。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diag_why_losing_fast', 'name': '为什么我瘦太快', 'subfunction': '自动分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view anomaly --diagnose why_losing_fast --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「为什么我瘦太快」。\n\n为什么我瘦太快?请评估速度是否危险(>1.5kg/周 为过快)+ 摄入是否过低。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '诊断: 为什么我瘦太快', 'data_fields': ['findings', 'confidence', 'degraded', 'insight'],
            'depends_on_external': False, 'order': 110},
    {
            'category': '分析',     'wake_word': '我的减重速度合理吗',     'desc': '我的减重速度合理吗',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view anomaly --diagnose rate_reasonable --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「我的减重速度合理吗」。\n\n我的减重速度合理吗?请与健康范围(0.5-1.0kg/周)对比,给出判定。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diag_rate_reasonable', 'name': '我的减重速度合理吗', 'subfunction': '自动分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view anomaly --diagnose rate_reasonable --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「我的减重速度合理吗」。\n\n我的减重速度合理吗?请与健康范围(0.5-1.0kg/周)对比,给出判定。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '诊断: 我的减重速度合理吗', 'data_fields': ['findings', 'confidence', 'degraded', 'insight'],
            'depends_on_external': False, 'order': 111},
    {
            'category': '分析',     'wake_word': '我的减肥策略对吗',     'desc': '我的减肥策略对吗',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view anomaly --diagnose strategy_check --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「我的减肥策略对吗」。\n\n我的减肥策略对吗?请做元评估:缺口是否合理 + 蛋白是否足够 + 运动是否有贡献。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diag_strategy_check', 'name': '我的减肥策略对吗', 'subfunction': '自动分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view anomaly --diagnose strategy_check --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「我的减肥策略对吗」。\n\n我的减肥策略对吗?请做元评估:缺口是否合理 + 蛋白是否足够 + 运动是否有贡献。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '诊断: 我的减肥策略对吗', 'data_fields': ['findings', 'confidence', 'degraded', 'insight'],
            'depends_on_external': False, 'order': 112},
    {
            'category': '分析',     'wake_word': '我距离目标还差什么',     'desc': '我距离目标还差什么',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view anomaly --diagnose gap_to_goal --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「我距离目标还差什么」。\n\n我距离目标还差什么?当前体重 vs 目标体重差距 + 按当前速度的预计达成时间。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diag_gap_to_goal', 'name': '我距离目标还差什么', 'subfunction': '自动分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view anomaly --diagnose gap_to_goal --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「我距离目标还差什么」。\n\n我距离目标还差什么?当前体重 vs 目标体重差距 + 按当前速度的预计达成时间。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '诊断: 我距离目标还差什么', 'data_fields': ['findings', 'confidence', 'degraded', 'insight'],
            'depends_on_external': False, 'order': 113},
    {
            'category': '分析',     'wake_word': '我这个月做得好的',     'desc': '我这个月做得好的',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view anomaly --diagnose month_highlights --window 本月', 'text': '请你加载技能 卡路里,执行唤醒词「我这个月做得好的」。\n\n我这个月做得好的有哪些?请做正向复盘:体重/运动/摄入各维度的亮点。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diag_month_highlights', 'name': '我这个月做得好的', 'subfunction': '自动分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view anomaly --diagnose month_highlights --window 本月', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「我这个月做得好的」。\n\n我这个月做得好的有哪些?请做正向复盘:体重/运动/摄入各维度的亮点。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '诊断: 我这个月做得好的', 'data_fields': ['findings', 'confidence', 'degraded', 'insight'],
            'depends_on_external': False, 'order': 114},
    {
            'category': '分析',     'wake_word': '我这个月需要改的',     'desc': '我这个月需要改的',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view anomaly --diagnose month_improve --window 本月', 'text': '请你加载技能 卡路里,执行唤醒词「我这个月需要改的」。\n\n我这个月需要改什么?请做负向复盘:超标日/运动不足/饮水不足等短板。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diag_month_improve', 'name': '我这个月需要改的', 'subfunction': '自动分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view anomaly --diagnose month_improve --window 本月', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「我这个月需要改的」。\n\n我这个月需要改什么?请做负向复盘:超标日/运动不足/饮水不足等短板。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '诊断: 我这个月需要改的', 'data_fields': ['findings', 'confidence', 'degraded', 'insight'],
            'depends_on_external': False, 'order': 115},
    {
            'category': '分析',     'wake_word': '综合健康评估',     'desc': '综合健康评估',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view anomaly --diagnose overall --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「综合健康评估」。\n\n请给我做一次综合健康评估。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diag_overall', 'name': '综合健康评估', 'subfunction': '自动分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view anomaly --diagnose overall --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「综合健康评估」。\n\n请给我做一次综合健康评估。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '诊断: 综合健康评估', 'data_fields': ['findings', 'confidence', 'degraded', 'insight'],
            'depends_on_external': False, 'order': 116},
    {
            'category': '分析',     'wake_word': '看蛋白 vs 碳水(最近 7 天)',     'desc': '看蛋白 vs 碳水(最近 7 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair protein_carbs --window 7d', 'text': '请你加载技能 卡路里,执行唤醒词「看蛋白 vs 碳水(最近 7 天)」。\n\n我想看最近 7 天的蛋白与碳水摄入量的关系。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'nut_protein_carbs_7d', 'name': '看蛋白 vs 碳水(最近 7 天)', 'subfunction': '营养分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair protein_carbs --window 7d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看蛋白 vs 碳水(最近 7 天)」。\n\n我想看最近 7 天的蛋白与碳水摄入量的关系。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看蛋白 vs 碳水(最近 7 天)', 'data_fields': ['protein', 'carbs', 'correlation'],
            'depends_on_external': False, 'order': 117},
    {
            'category': '分析',     'wake_word': '看蛋白 vs 碳水(最近 30 天)',     'desc': '看蛋白 vs 碳水(最近 30 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair protein_carbs --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「看蛋白 vs 碳水(最近 30 天)」。\n\n我想看最近 30 天的蛋白与碳水摄入量的关系。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'nut_protein_carbs_30d', 'name': '看蛋白 vs 碳水(最近 30 天)', 'subfunction': '营养分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair protein_carbs --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看蛋白 vs 碳水(最近 30 天)」。\n\n我想看最近 30 天的蛋白与碳水摄入量的关系。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看蛋白 vs 碳水(最近 30 天)', 'data_fields': ['protein', 'carbs', 'correlation'],
            'depends_on_external': False, 'order': 118},
    {
            'category': '分析',     'wake_word': '看蛋白 vs 碳水(最近 90 天)',     'desc': '看蛋白 vs 碳水(最近 90 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair protein_carbs --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「看蛋白 vs 碳水(最近 90 天)」。\n\n我想看最近 90 天的蛋白与碳水摄入量的关系。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'nut_protein_carbs_90d', 'name': '看蛋白 vs 碳水(最近 90 天)', 'subfunction': '营养分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair protein_carbs --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看蛋白 vs 碳水(最近 90 天)」。\n\n我想看最近 90 天的蛋白与碳水摄入量的关系。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看蛋白 vs 碳水(最近 90 天)', 'data_fields': ['protein', 'carbs', 'correlation'],
            'depends_on_external': False, 'order': 119},
    {
            'category': '分析',     'wake_word': '看蛋白 vs 碳水(自定义)',     'desc': '看蛋白 vs 碳水(自定义)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair protein_carbs --window custom --start <开始日期> --end <结束日期>', 'text': '请你加载技能 卡路里,执行唤醒词「看蛋白 vs 碳水(自定义)」。\n\n我想看自定义时间段(开始日期到结束日期)的蛋白与碳水摄入量的关系。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期:____\n结束日期:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'nut_protein_carbs_custom', 'name': '看蛋白 vs 碳水(自定义)', 'subfunction': '营养分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair protein_carbs --window custom --start <开始日期> --end <结束日期>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看蛋白 vs 碳水(自定义)」。\n\n我想看自定义时间段(开始日期到结束日期)的蛋白与碳水摄入量的关系。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期:____\n结束日期:____',
            'user_intent': '看蛋白 vs 碳水(自定义时间段)', 'data_fields': ['protein', 'carbs', 'correlation'],
            'depends_on_external': False, 'order': 120},
    {
            'category': '分析',     'wake_word': '看蛋白 vs 脂肪(最近 30 天)',     'desc': '看蛋白 vs 脂肪(最近 30 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair protein_fat --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「看蛋白 vs 脂肪(最近 30 天)」。\n\n我想看最近 30 天的蛋白与脂肪摄入量的关系。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'nut_protein_fat_30d', 'name': '看蛋白 vs 脂肪(最近 30 天)', 'subfunction': '营养分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair protein_fat --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看蛋白 vs 脂肪(最近 30 天)」。\n\n我想看最近 30 天的蛋白与脂肪摄入量的关系。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看蛋白 vs 脂肪(最近 30 天)', 'data_fields': ['protein', 'fat', 'correlation'],
            'depends_on_external': False, 'order': 121},
    {
            'category': '分析',     'wake_word': '看蛋白 vs 脂肪(最近 90 天)',     'desc': '看蛋白 vs 脂肪(最近 90 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair protein_fat --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「看蛋白 vs 脂肪(最近 90 天)」。\n\n我想看最近 90 天的蛋白与脂肪摄入量的关系。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'nut_protein_fat_90d', 'name': '看蛋白 vs 脂肪(最近 90 天)', 'subfunction': '营养分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair protein_fat --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看蛋白 vs 脂肪(最近 90 天)」。\n\n我想看最近 90 天的蛋白与脂肪摄入量的关系。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看蛋白 vs 脂肪(最近 90 天)', 'data_fields': ['protein', 'fat', 'correlation'],
            'depends_on_external': False, 'order': 122},
    {
            'category': '分析',     'wake_word': '看蛋白 vs 脂肪(自定义)',     'desc': '看蛋白 vs 脂肪(自定义)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair protein_fat --window custom --start <开始日期> --end <结束日期>', 'text': '请你加载技能 卡路里,执行唤醒词「看蛋白 vs 脂肪(自定义)」。\n\n我想看自定义时间段(开始日期到结束日期)的蛋白与脂肪摄入量的关系。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期:____\n结束日期:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'nut_protein_fat_custom', 'name': '看蛋白 vs 脂肪(自定义)', 'subfunction': '营养分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair protein_fat --window custom --start <开始日期> --end <结束日期>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看蛋白 vs 脂肪(自定义)」。\n\n我想看自定义时间段(开始日期到结束日期)的蛋白与脂肪摄入量的关系。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期:____\n结束日期:____',
            'user_intent': '看蛋白 vs 脂肪(自定义时间段)', 'data_fields': ['protein', 'fat', 'correlation'],
            'depends_on_external': False, 'order': 123},
    {
            'category': '分析',     'wake_word': '看碳水 vs 脂肪(最近 30 天)',     'desc': '看碳水 vs 脂肪(最近 30 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair carbs_fat --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「看碳水 vs 脂肪(最近 30 天)」。\n\n我想看最近 30 天的碳水与脂肪摄入量的关系。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'nut_carbs_fat_30d', 'name': '看碳水 vs 脂肪(最近 30 天)', 'subfunction': '营养分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair carbs_fat --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看碳水 vs 脂肪(最近 30 天)」。\n\n我想看最近 30 天的碳水与脂肪摄入量的关系。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看碳水 vs 脂肪(最近 30 天)', 'data_fields': ['carbs', 'fat', 'correlation'],
            'depends_on_external': False, 'order': 124},
    {
            'category': '分析',     'wake_word': '看碳水 vs 脂肪(最近 90 天)',     'desc': '看碳水 vs 脂肪(最近 90 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair carbs_fat --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「看碳水 vs 脂肪(最近 90 天)」。\n\n我想看最近 90 天的碳水与脂肪摄入量的关系。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'nut_carbs_fat_90d', 'name': '看碳水 vs 脂肪(最近 90 天)', 'subfunction': '营养分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair carbs_fat --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看碳水 vs 脂肪(最近 90 天)」。\n\n我想看最近 90 天的碳水与脂肪摄入量的关系。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看碳水 vs 脂肪(最近 90 天)', 'data_fields': ['carbs', 'fat', 'correlation'],
            'depends_on_external': False, 'order': 125},
    {
            'category': '分析',     'wake_word': '看碳水 vs 脂肪(自定义)',     'desc': '看碳水 vs 脂肪(自定义)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view combined --pair carbs_fat --window custom --start <开始日期> --end <结束日期>', 'text': '请你加载技能 卡路里,执行唤醒词「看碳水 vs 脂肪(自定义)」。\n\n我想看自定义时间段(开始日期到结束日期)的碳水与脂肪摄入量的关系。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期:____\n结束日期:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'nut_carbs_fat_custom', 'name': '看碳水 vs 脂肪(自定义)', 'subfunction': '营养分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view combined --pair carbs_fat --window custom --start <开始日期> --end <结束日期>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看碳水 vs 脂肪(自定义)」。\n\n我想看自定义时间段(开始日期到结束日期)的碳水与脂肪摄入量的关系。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期:____\n结束日期:____',
            'user_intent': '看碳水 vs 脂肪(自定义时间段)', 'data_fields': ['carbs', 'fat', 'correlation'],
            'depends_on_external': False, 'order': 126},
    {
            'category': '分析',     'wake_word': '看钠糖纤维趋势',     'desc': '看钠糖纤维趋势',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view nutrition --group sodium_fiber --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「看钠糖纤维趋势」。\n\n我想看钠/糖/纤维三种营养素的趋势(可让我选时间窗口,默认最近 90 天)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'nut_sodium_fiber', 'name': '看钠糖纤维趋势', 'subfunction': '营养分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view nutrition --group sodium_fiber --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看钠糖纤维趋势」。\n\n我想看钠/糖/纤维三种营养素的趋势(可让我选时间窗口,默认最近 90 天)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看钠糖纤维趋势', 'data_fields': ['sodium_mg', 'sugar_g', 'fiber_g', 'rate'],
            'depends_on_external': False, 'order': 127},
    {
            'category': '分析',     'wake_word': '看钠糖纤维综合',     'desc': '看钠糖纤维综合',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view nutrition --group sodium_combined --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「看钠糖纤维综合」。\n\n我想看钠/糖/纤维综合报告。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'nut_sodium_combined', 'name': '看钠糖纤维综合', 'subfunction': '营养分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view nutrition --group sodium_combined --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看钠糖纤维综合」。\n\n我想看钠/糖/纤维综合报告。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看钠糖纤维综合', 'data_fields': ['sodium_mg', 'sugar_g', 'fiber_g', 'worst'],
            'depends_on_external': False, 'order': 128},
    {
            'category': '分析',     'wake_word': '看营养建议',     'desc': '看营养建议',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view nutrition --group advice --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「看营养建议」。\n\n我想看营养改进建议。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'nut_advice', 'name': '看营养建议', 'subfunction': '营养分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view nutrition --group advice --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看营养建议」。\n\n我想看营养改进建议。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看营养建议', 'data_fields': ['items', 'gap', 'priority'],
            'depends_on_external': False, 'order': 129},
    {
            'category': '分析',     'wake_word': '看三大营养交叉(最近 30 天)',     'desc': '看三大营养交叉(最近 30 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view nutrition --group macro3 --window 30d', 'text': '请你加载技能 卡路里,执行唤醒词「看三大营养交叉(最近 30 天)」。\n\n我想看最近 30 天的蛋白/碳水/脂肪三者交叉。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'nut_macro3_30d', 'name': '看三大营养交叉(最近 30 天)', 'subfunction': '营养分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view nutrition --group macro3 --window 30d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看三大营养交叉(最近 30 天)」。\n\n我想看最近 30 天的蛋白/碳水/脂肪三者交叉。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看三大营养交叉(最近 30 天)', 'data_fields': ['protein', 'carbs', 'fat', 'shares', 'balanced'],
            'depends_on_external': False, 'order': 130},
    {
            'category': '分析',     'wake_word': '看三大营养交叉(最近 90 天)',     'desc': '看三大营养交叉(最近 90 天)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view nutrition --group macro3 --window 90d', 'text': '请你加载技能 卡路里,执行唤醒词「看三大营养交叉(最近 90 天)」。\n\n我想看最近 90 天的蛋白/碳水/脂肪三者交叉。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'nut_macro3_90d', 'name': '看三大营养交叉(最近 90 天)', 'subfunction': '营养分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view nutrition --group macro3 --window 90d', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看三大营养交叉(最近 90 天)」。\n\n我想看最近 90 天的蛋白/碳水/脂肪三者交叉。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '看三大营养交叉(最近 90 天)', 'data_fields': ['protein', 'carbs', 'fat', 'shares', 'balanced'],
            'depends_on_external': False, 'order': 131},
    {
            'category': '分析',     'wake_word': '看三大营养交叉(自定义)',     'desc': '看三大营养交叉(自定义)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view nutrition --group macro3 --window custom --start <开始日期> --end <结束日期>', 'text': '请你加载技能 卡路里,执行唤醒词「看三大营养交叉(自定义)」。\n\n我想看自定义时间段(开始日期到结束日期)的蛋白/碳水/脂肪三者交叉。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期:____\n结束日期:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'nut_macro3_custom', 'name': '看三大营养交叉(自定义)', 'subfunction': '营养分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view nutrition --group macro3 --window custom --start <开始日期> --end <结束日期>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看三大营养交叉(自定义)」。\n\n我想看自定义时间段(开始日期到结束日期)的蛋白/碳水/脂肪三者交叉。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n开始日期:____\n结束日期:____',
            'user_intent': '看三大营养交叉(自定义时间段)', 'data_fields': ['protein', 'carbs', 'fat', 'shares', 'balanced'],
            'depends_on_external': False, 'order': 132},
    {
            'category': '分析',     'wake_word': '预测体重(1 周后)',     'desc': '预测体重(1 周后)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view predict --kind weight_week', 'text': '请你加载技能 卡路里,执行唤醒词「预测体重(1 周后)」。\n\n我想预测 1 周后的体重。若数据不足 14 天请明确提示不预测。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'pred_weight_week', 'name': '预测体重(1 周后)', 'subfunction': '预测模拟', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view predict --kind weight_week', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「预测体重(1 周后)」。\n\n我想预测 1 周后的体重。若数据不足 14 天请明确提示不预测。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '预测体重(1 周后) 模拟/预测', 'data_fields': ['weight_kg', 'forecast', 'confidence', 'degraded'],
            'depends_on_external': False, 'order': 133},
    {
            'category': '分析',     'wake_word': '预测体重(1 月后)',     'desc': '预测体重(1 月后)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view predict --kind weight_month', 'text': '请你加载技能 卡路里,执行唤醒词「预测体重(1 月后)」。\n\n我想预测 1 月后的体重。若数据不足 14 天请明确提示不预测。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'pred_weight_month', 'name': '预测体重(1 月后)', 'subfunction': '预测模拟', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view predict --kind weight_month', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「预测体重(1 月后)」。\n\n我想预测 1 月后的体重。若数据不足 14 天请明确提示不预测。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '预测体重(1 月后) 模拟/预测', 'data_fields': ['weight_kg', 'forecast', 'confidence', 'degraded'],
            'depends_on_external': False, 'order': 134},
    {
            'category': '分析',     'wake_word': '预测体重(3 月后)',     'desc': '预测体重(3 月后)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view predict --kind weight_3m', 'text': '请你加载技能 卡路里,执行唤醒词「预测体重(3 月后)」。\n\n我想预测 3 月后的体重。若数据不足 14 天请明确提示不预测。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'pred_weight_3m', 'name': '预测体重(3 月后)', 'subfunction': '预测模拟', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view predict --kind weight_3m', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「预测体重(3 月后)」。\n\n我想预测 3 月后的体重。若数据不足 14 天请明确提示不预测。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '预测体重(3 月后) 模拟/预测', 'data_fields': ['weight_kg', 'forecast', 'confidence', 'degraded'],
            'depends_on_external': False, 'order': 135},
    {
            'category': '分析',     'wake_word': '预测体重(6 月后)',     'desc': '预测体重(6 月后)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view predict --kind weight_6m', 'text': '请你加载技能 卡路里,执行唤醒词「预测体重(6 月后)」。\n\n我想预测 6 月后的体重。若数据不足 14 天请明确提示不预测。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'pred_weight_6m', 'name': '预测体重(6 月后)', 'subfunction': '预测模拟', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view predict --kind weight_6m', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「预测体重(6 月后)」。\n\n我想预测 6 月后的体重。若数据不足 14 天请明确提示不预测。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '预测体重(6 月后) 模拟/预测', 'data_fields': ['weight_kg', 'forecast', 'confidence', 'degraded'],
            'depends_on_external': False, 'order': 136},
    {
            'category': '分析',     'wake_word': '预测体重(自定义时间)',     'desc': '预测体重(自定义时间)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view predict --kind weight_custom_t --days <天数>', 'text': '请你加载技能 卡路里,执行唤醒词「预测体重(自定义时间)」。\n\n我想预测自定义时间后的体重。若数据不足 14 天请明确提示不预测。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n预测多少天后:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'pred_weight_custom_t', 'name': '预测体重(自定义时间)', 'subfunction': '预测模拟', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view predict --kind weight_custom_t --days <天数>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「预测体重(自定义时间)」。\n\n我想预测自定义时间后的体重。若数据不足 14 天请明确提示不预测。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n预测多少天后:____',
            'user_intent': '预测体重(自定义时间) 模拟/预测', 'data_fields': ['weight_kg', 'forecast', 'confidence', 'degraded'],
            'depends_on_external': False, 'order': 137},
    {
            'category': '分析',     'wake_word': '预测体重(自定义目标)',     'desc': '预测体重(自定义目标)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view predict --kind weight_target --target <目标kg>', 'text': '请你加载技能 卡路里,执行唤醒词「预测体重(自定义目标)」。\n\n我想按当前趋势预测达成目标体重的日期:预计达成日 + 所需天数 + 假设说明 + 可行性提示;若数据不足 14 天请明确提示不预测。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n目标体重(kg):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'pred_weight_target', 'name': '预测体重(自定义目标)', 'subfunction': '预测模拟', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view predict --kind weight_target --target <目标kg>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「预测体重(自定义目标)」。\n\n我想按当前趋势预测达成目标体重的日期:预计达成日 + 所需天数 + 假设说明 + 可行性提示;若数据不足 14 天请明确提示不预测。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n目标体重(kg):____',
            'user_intent': '预测体重(自定义目标) 模拟/预测', 'data_fields': ['target', 'eta', 'days_left', 'feasible'],
            'depends_on_external': False, 'order': 138},
    {
            'category': '分析',     'wake_word': '模拟减重(每天-300卡)',     'desc': '模拟减重(每天-300卡)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view predict --kind sim_cut_300', 'text': '请你加载技能 卡路里,执行唤醒词「模拟减重(每天-300卡)」。\n\n我想模拟每天多减 300 卡的减重效果。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'pred_sim_cut_300', 'name': '模拟减重(每天-300卡)', 'subfunction': '预测模拟', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view predict --kind sim_cut_300', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「模拟减重(每天-300卡)」。\n\n我想模拟每天多减 300 卡的减重效果。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '模拟减重(每天-300卡) 模拟/预测', 'data_fields': ['cut_kcal', 'weekly_loss', 'forecast', 'feasible'],
            'depends_on_external': False, 'order': 139},
    {
            'category': '分析',     'wake_word': '模拟减重(每天-500卡)',     'desc': '模拟减重(每天-500卡)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view predict --kind sim_cut_500', 'text': '请你加载技能 卡路里,执行唤醒词「模拟减重(每天-500卡)」。\n\n我想模拟每天多减 500 卡的减重效果。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'pred_sim_cut_500', 'name': '模拟减重(每天-500卡)', 'subfunction': '预测模拟', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view predict --kind sim_cut_500', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「模拟减重(每天-500卡)」。\n\n我想模拟每天多减 500 卡的减重效果。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '模拟减重(每天-500卡) 模拟/预测', 'data_fields': ['cut_kcal', 'weekly_loss', 'forecast', 'feasible'],
            'depends_on_external': False, 'order': 140},
    {
            'category': '分析',     'wake_word': '模拟减重(每天-700卡)',     'desc': '模拟减重(每天-700卡)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view predict --kind sim_cut_700', 'text': '请你加载技能 卡路里,执行唤醒词「模拟减重(每天-700卡)」。\n\n我想模拟每天多减 700 卡的减重效果。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'pred_sim_cut_700', 'name': '模拟减重(每天-700卡)', 'subfunction': '预测模拟', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view predict --kind sim_cut_700', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「模拟减重(每天-700卡)」。\n\n我想模拟每天多减 700 卡的减重效果。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '模拟减重(每天-700卡) 模拟/预测', 'data_fields': ['cut_kcal', 'weekly_loss', 'forecast', 'feasible'],
            'depends_on_external': False, 'order': 141},
    {
            'category': '分析',     'wake_word': '模拟减重(30天减Xkg)',     'desc': '模拟减重(30天减Xkg)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view predict --kind sim_target_30 --target <Xkg>', 'text': '请你加载技能 卡路里,执行唤醒词「模拟减重(30天减Xkg)」。\n\n我想模拟 30 天减 X 公斤。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n30 天想减多少 kg:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'pred_sim_target_30', 'name': '模拟减重(30天减Xkg)', 'subfunction': '预测模拟', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view predict --kind sim_target_30 --target <Xkg>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「模拟减重(30天减Xkg)」。\n\n我想模拟 30 天减 X 公斤。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n30 天想减多少 kg:____',
            'user_intent': '模拟减重(30天减Xkg) 模拟/预测', 'data_fields': ['target_loss', 'needed_deficit', 'forecast', 'feasible'],
            'depends_on_external': False, 'order': 142},
    {
            'category': '分析',     'wake_word': '模拟减重(60天减Xkg)',     'desc': '模拟减重(60天减Xkg)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view predict --kind sim_target_60 --target <Xkg>', 'text': '请你加载技能 卡路里,执行唤醒词「模拟减重(60天减Xkg)」。\n\n我想模拟 60 天减 X 公斤。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n60 天想减多少 kg:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'pred_sim_target_60', 'name': '模拟减重(60天减Xkg)', 'subfunction': '预测模拟', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view predict --kind sim_target_60 --target <Xkg>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「模拟减重(60天减Xkg)」。\n\n我想模拟 60 天减 X 公斤。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n60 天想减多少 kg:____',
            'user_intent': '模拟减重(60天减Xkg) 模拟/预测', 'data_fields': ['target_loss', 'needed_deficit', 'forecast', 'feasible'],
            'depends_on_external': False, 'order': 143},
    {
            'category': '分析',     'wake_word': '模拟减重(90天减Xkg)',     'desc': '模拟减重(90天减Xkg)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view predict --kind sim_target_90 --target <Xkg>', 'text': '请你加载技能 卡路里,执行唤醒词「模拟减重(90天减Xkg)」。\n\n我想模拟 90 天减 X 公斤。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n90 天想减多少 kg:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'pred_sim_target_90', 'name': '模拟减重(90天减Xkg)', 'subfunction': '预测模拟', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view predict --kind sim_target_90 --target <Xkg>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「模拟减重(90天减Xkg)」。\n\n我想模拟 90 天减 X 公斤。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n90 天想减多少 kg:____',
            'user_intent': '模拟减重(90天减Xkg) 模拟/预测', 'data_fields': ['target_loss', 'needed_deficit', 'forecast', 'feasible'],
            'depends_on_external': False, 'order': 144},
    {
            'category': '分析',     'wake_word': '模拟减重(自定义天数减Xkg)',     'desc': '模拟减重(自定义天数减Xkg)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view predict --kind sim_target_custom --target <Xkg> --days <天数>', 'text': '请你加载技能 卡路里,执行唤醒词「模拟减重(自定义天数减Xkg)」。\n\n我想模拟自定义天数内减 X 公斤。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n天数:____\n想减多少 kg:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'pred_sim_target_custom', 'name': '模拟减重(自定义天数减Xkg)', 'subfunction': '预测模拟', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view predict --kind sim_target_custom --target <Xkg> --days <天数>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「模拟减重(自定义天数减Xkg)」。\n\n我想模拟自定义天数内减 X 公斤。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n天数:____\n想减多少 kg:____',
            'user_intent': '模拟减重(自定义天数减Xkg) 模拟/预测', 'data_fields': ['target_loss', 'days_target', 'needed_deficit', 'forecast', 'feasible'],
            'depends_on_external': False, 'order': 145},
    {
            'category': '分析',     'wake_word': '摄入预测(按当前速率 1 周)',     'desc': '摄入预测(按当前速率 1 周)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view predict --kind cal_week', 'text': '请你加载技能 卡路里,执行唤醒词「摄入预测(按当前速率 1 周)」。\n\n我想按当前速率预测 1 周后的日均摄入。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'pred_cal_week', 'name': '摄入预测(按当前速率 1 周)', 'subfunction': '预测模拟', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view predict --kind cal_week', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「摄入预测(按当前速率 1 周)」。\n\n我想按当前速率预测 1 周后的日均摄入。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '摄入预测(按当前速率 1 周) 模拟/预测', 'data_fields': ['calories', 'forecast', 'goal'],
            'depends_on_external': False, 'order': 146},
    {
            'category': '分析',     'wake_word': '摄入预测(按当前速率 1 月)',     'desc': '摄入预测(按当前速率 1 月)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view predict --kind cal_month', 'text': '请你加载技能 卡路里,执行唤醒词「摄入预测(按当前速率 1 月)」。\n\n我想按当前速率预测 1 月后的日均摄入。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'pred_cal_month', 'name': '摄入预测(按当前速率 1 月)', 'subfunction': '预测模拟', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view predict --kind cal_month', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「摄入预测(按当前速率 1 月)」。\n\n我想按当前速率预测 1 月后的日均摄入。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '摄入预测(按当前速率 1 月) 模拟/预测', 'data_fields': ['calories', 'forecast', 'goal'],
            'depends_on_external': False, 'order': 147},
    {
            'category': '分析',     'wake_word': '摄入预测(按当前速率 3 月)',     'desc': '摄入预测(按当前速率 3 月)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view predict --kind cal_3m', 'text': '请你加载技能 卡路里,执行唤醒词「摄入预测(按当前速率 3 月)」。\n\n我想按当前速率预测 3 月后的日均摄入。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'pred_cal_3m', 'name': '摄入预测(按当前速率 3 月)', 'subfunction': '预测模拟', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view predict --kind cal_3m', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「摄入预测(按当前速率 3 月)」。\n\n我想按当前速率预测 3 月后的日均摄入。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '摄入预测(按当前速率 3 月) 模拟/预测', 'data_fields': ['calories', 'forecast', 'goal'],
            'depends_on_external': False, 'order': 148},
    {
            'category': '分析',     'wake_word': '摄入预测(自定义)',     'desc': '摄入预测(自定义)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view predict --kind cal_custom --days <天数>', 'text': '请你加载技能 卡路里,执行唤醒词「摄入预测(自定义)」。\n\n我想预测自定义时间后的日均摄入。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n预测多少天后:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'pred_cal_custom', 'name': '摄入预测(自定义)', 'subfunction': '预测模拟', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view predict --kind cal_custom --days <天数>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「摄入预测(自定义)」。\n\n我想预测自定义时间后的日均摄入。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n预测多少天后:____',
            'user_intent': '摄入预测(自定义) 模拟/预测', 'data_fields': ['calories', 'forecast', 'goal'],
            'depends_on_external': False, 'order': 149},
    {
            'category': '分析',     'wake_word': '摄入预测(营养目标达成预测)',     'desc': '摄入预测(营养目标达成预测)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view predict --kind cal_goal', 'text': '请你加载技能 卡路里,执行唤醒词「摄入预测(营养目标达成预测)」。\n\n我想预测营养目标能否达成。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'pred_cal_goal', 'name': '摄入预测(营养目标达成预测)', 'subfunction': '预测模拟', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view predict --kind cal_goal', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「摄入预测(营养目标达成预测)」。\n\n我想预测营养目标能否达成。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '摄入预测(营养目标达成预测) 模拟/预测', 'data_fields': ['avg', 'goal', 'gap', 'on_target'],
            'depends_on_external': False, 'order': 150},
    {
            'category': '分析',     'wake_word': '摄入预测(卡路里缺口预测)',     'desc': '摄入预测(卡路里缺口预测)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view predict --kind cal_deficit', 'text': '请你加载技能 卡路里,执行唤醒词「摄入预测(卡路里缺口预测)」。\n\n我想预测卡路里缺口。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'pred_cal_deficit', 'name': '摄入预测(卡路里缺口预测)', 'subfunction': '预测模拟', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view predict --kind cal_deficit', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「摄入预测(卡路里缺口预测)」。\n\n我想预测卡路里缺口。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '摄入预测(卡路里缺口预测) 模拟/预测', 'data_fields': ['avg_deficit', 'weekly_loss'],
            'depends_on_external': False, 'order': 151},
    {
            'category': '分析',     'wake_word': '摄入预测(摄入稳定性预测)',     'desc': '摄入预测(摄入稳定性预测)',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view predict --kind cal_stability', 'text': '请你加载技能 卡路里,执行唤醒词「摄入预测(摄入稳定性预测)」。\n\n我想预测摄入的稳定性。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。'},
        'fill_hints': [],
            'variants': [],
            'key': 'pred_cal_stability', 'name': '摄入预测(摄入稳定性预测)', 'subfunction': '预测模拟', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view predict --kind cal_stability', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「摄入预测(摄入稳定性预测)」。\n\n我想预测摄入的稳定性。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。',
            'user_intent': '摄入预测(摄入稳定性预测) 模拟/预测', 'data_fields': ['avg', 'sigma', 'stable'],
            'depends_on_external': False, 'order': 152},
    {
            'category': '分析',     'wake_word': '看每日 6 因素综合',     'desc': '看每日 6 因素综合',
            'main_prompt': {
        'cli': 'python scripts/render_analysis.py --view six --date <YYYY-MM-DD>', 'text': '请你加载技能 卡路里,执行唤醒词「看每日 6 因素综合」。\n\n我想看某一天的全维度健康快照(体重/饮食/运动/饮水/体脂/围度)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n日期(YYYY-MM-DD):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'six_factors_daily', 'name': '看每日 6 因素综合', 'subfunction': '单点分析', 'output_type': 'result',
            'html_template': 'templates/combined_analysis.html', 'data_source': 'python scripts/render_analysis.py --view six --date <YYYY-MM-DD>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看每日 6 因素综合」。\n\n我想看某一天的全维度健康快照(体重/饮食/运动/饮水/体脂/围度)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n日期(YYYY-MM-DD):____',
            'user_intent': '看单日全维度健康快照', 'data_fields': ['weight_kg', 'calories', 'exercise_kcal', 'water_ml', 'body_fat_pct', 'waist_cm'],
            'depends_on_external': False, 'order': 153},
    {
            'category': "复盘",     'wake_word': "今日复盘",     'desc': "当日复盘",
            'main_prompt': {
        'cli': "python scripts/render_review.py --type day", 'text': "请你加载技能 卡路里,执行唤醒词「今日复盘」。\n\n我要看当日复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。"},
        'fill_hints': [],
            'variants': []},
    {
            'category': "复盘",     'wake_word': "关闭定时复盘",     'desc': "删除 cron",
            'main_prompt': {
        'cli': "mavis cron delete ...", 'text': "请你加载技能 卡路里,执行唤醒词「关闭定时复盘」。\n\n我要关掉每天自动复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。"},
        'fill_hints': [],
            'variants': []},
    {
            'category': "复盘",     'wake_word': "复盘",     'desc': "生成 8 维度复盘报告 HTML + 可选飞书发送",
            'main_prompt': {
        'cli': "python scripts/render_review.py", 'text': "请你加载技能 卡路里,执行唤醒词「复盘」。\n\n我要看一份复盘报告,默认最近 7 天。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。"},
        'fill_hints': [],
            'variants': []},
    {
            'category': "复盘",     'wake_word': "复盘日期范围",     'desc': "自定义日期范围复盘",
            'main_prompt': {
        'cli': "python scripts/render_review.py --range 2026-07-01:2026-07-14", 'text': "请你加载技能 卡路里,执行唤醒词「复盘日期范围」。\n\n我要看任意起止日期的复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。"},
        'fill_hints': [],
            'variants': []},
    {
            'category': "复盘",     'wake_word': "开启定时复盘",     'desc': "启动 cron(默认 23:00 / 过去 7 天)",
            'main_prompt': {
        'cli': "mavis cron create ...", 'text': "请你加载技能 卡路里,执行唤醒词「开启定时复盘」。\n\n我要设每天自动跑复盘(默认 23:00 跑过去 7 天)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。"},
        'fill_hints': [],
            'variants': []},
    {
            'category': "复盘",     'wake_word': "本周复盘",     'desc': "本周复盘(本周一-今天)",
            'main_prompt': {
        'cli': "python scripts/render_review.py --type week", 'text': "请你加载技能 卡路里,执行唤醒词「本周复盘」。\n\n我要看本周一-今天的复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。"},
        'fill_hints': [],
            'variants': []},
    {
            'category': "复盘",     'wake_word': "本年复盘",     'desc': "本年复盘(今年 1/1-今天)",
            'main_prompt': {
        'cli': "python scripts/render_review.py --type year", 'text': "请你加载技能 卡路里,执行唤醒词「本年复盘」。\n\n我要看今年 1/1 - 今天的复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。"},
        'fill_hints': [],
            'variants': []},
    {
            'category': "复盘",     'wake_word': "本月复盘",     'desc': "本月复盘(本月 1 号-今天)",
            'main_prompt': {
        'cli': "python scripts/render_review.py --type month", 'text': "请你加载技能 卡路里,执行唤醒词「本月复盘」。\n\n我要看本月 1 号-今天的复盘。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。"},
        'fill_hints': [],
            'variants': []},
    {
            'category': "分析",     'wake_word': "查低热量榜",     'desc': "低热量健康 TOP5",
            'main_prompt': {
        'cli': "python scripts/render_food_ranking.py --days 7 --category low_calorie", 'text': "请你加载技能 卡路里,执行唤醒词「查低热量榜」。\n\n我想看热量最低的 5 个健康食物(默认 7 天)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。"},
        'fill_hints': [],
            'variants': []},
    {
            'category': "分析",     'wake_word': "查健康报告",     'desc': "四维度综合健康仪表盘",
            'main_prompt': {
        'cli': "python scripts/render_health_dashboard.py --days 7", 'text': "请你加载技能 卡路里,执行唤醒词「查健康报告」。\n\n我要看 4 维健康仪表盘(热量/营养/运动/体重综合,默认 7 天)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。"},
        'fill_hints': [],
            'variants': [{"label": "查健康报告 本月", "cli": "python scripts/render_health_dashboard.py --start 2026-07-01 --end 2026-07-26", "prompt": "请你加载技能 卡路里,执行唤醒词「查健康报告 本月」。\n\n我要看本月 1 号到今天的健康报告。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。"}]},
    {
            'category': "分析",     'wake_word': "查卡路里数据",     'desc': "数据健康检查(lint_health)",
            'main_prompt': {
        'cli': "python scripts/render_lint_health.py", 'text': "请你加载技能 卡路里,执行唤醒词「查卡路里数据」。\n\n我要检查数据库的健康性。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。"},
        'fill_hints': [],
            'variants': []},
    {
            'category': "复盘",     'wake_word': "查定时复盘",     'desc': "查看当前定时复盘配置",
            'main_prompt': {
        'cli': "mavis cron list", 'text': "请你加载技能 卡路里,执行唤醒词「查定时复盘」。\n\n我想看当前定时复盘配置。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。"},
        'fill_hints': [],
            'variants': []},
    {
            'category': "分析",     'wake_word': "查热量缺口",     'desc': "热量缺口分析(摄入 vs 运动 vs TDEE)",
            'main_prompt': {
        'cli': "python scripts/render_calorie_deficit.py --days 7", 'text': "请你加载技能 卡路里,执行唤醒词「查热量缺口」。\n\n我想看摄入 vs 运动消耗的缺口(默认 7 天)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。"},
        'fill_hints': [],
            'variants': []},
    {
            'category': "分析",     'wake_word': "查热量趋势",     'desc': "热量摄入趋势",
            'main_prompt': {
        'cli': "python scripts/render_calorie_trend.py --days 7", 'text': "请你加载技能 卡路里,执行唤醒词「查热量趋势」。\n\n我想看每日热量摄入趋势(默认 7 天)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。"},
        'fill_hints': [],
            'variants': [{"label": "查热量趋势 上周", "cli": "python scripts/render_calorie_trend.py --days 7", "prompt": "请你加载技能 卡路里,执行唤醒词「查热量趋势 上周」。\n\n时间窗口/参数语境:查热量趋势 上周。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。"}, {"label": "查热量趋势 7 月", "cli": "python scripts/render_calorie_trend.py --start 2026-07-01 --end 2026-07-31", "prompt": "请你加载技能 卡路里,执行唤醒词「查热量趋势 7 月」。\n\n时间窗口/参数语境:查热量趋势 7 月。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。"}, {"label": "查热量趋势 最近 30 天", "cli": "python scripts/render_calorie_trend.py --days 30", "prompt": "请你加载技能 卡路里,执行唤醒词「查热量趋势 最近 30 天」。\n\n时间窗口/参数语境:查热量趋势 最近 30 天。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。"}]},
    {
            'category': "分析",     'wake_word': "查营养结构",     'desc': "营养素占比分析",
            'main_prompt': {
        'cli': "python scripts/render_nutrition_ratio.py --days 7", 'text': "请你加载技能 卡路里,执行唤醒词「查营养结构」。\n\n我想看蛋白/碳水/脂肪占比(默认 7 天)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。"},
        'fill_hints': [],
            'variants': [{"label": "查营养结构 7 月", "cli": "python scripts/render_nutrition_ratio.py --start 2026-07-01 --end 2026-07-31", "prompt": "请你加载技能 卡路里,执行唤醒词「查营养结构 7 月」。\n\n时间窗口/参数语境:查营养结构 7 月。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。"}]},
    {
            'category': "分析",     'wake_word': "查运动分布",     'desc': "运动类型分布",
            'main_prompt': {
        'cli': "python scripts/render_exercise_distribution.py --days 7", 'text': "请你加载技能 卡路里,执行唤醒词「查运动分布」。\n\n我想看 4 类运动(力量/有氧/柔韧/日常)的时间/消耗分布(默认 7 天)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。"},
        'fill_hints': [],
            'variants': []},
    {
            'category': "分析",     'wake_word': "查运动贡献",     'desc': "运动对热量缺口的贡献占比",
            'main_prompt': {
        'cli': "python scripts/render_exercise_distribution.py --days 7 --mode contribution", 'text': "请你加载技能 卡路里,执行唤醒词「查运动贡献」。\n\n我想看运动在热量缺口里的占比(默认 7 天)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。"},
        'fill_hints': [],
            'variants': []},
    {
            'category': "分析",     'wake_word': "查频繁吃榜",     'desc': "最常吃的食物 TOP5",
            'main_prompt': {
        'cli': "python scripts/render_food_ranking.py --days 7 --category frequent", 'text': "请你加载技能 卡路里,执行唤醒词「查频繁吃榜」。\n\n我想看吃最多次的食物(默认 7 天)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。"},
        'fill_hints': [],
            'variants': []},
    {
            'category': "分析",     'wake_word': "查食物排行",     'desc': "食物排行榜(默认高热量榜)",
            'main_prompt': {
        'cli': "python scripts/render_food_ranking.py --days 7", 'text': "请你加载技能 卡路里,执行唤醒词「查食物排行」。\n\n我想看 TOP 食物热量榜(默认高热量,默认 7 天)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。"},
        'fill_hints': [],
            'variants': []},
    {
            'category': "分析",     'wake_word': "查高热量榜",     'desc': "热量炸弹 TOP5",
            'main_prompt': {
        'cli': "python scripts/render_food_ranking.py --days 7 --category high_calorie", 'text': "请你加载技能 卡路里,执行唤醒词「查高热量榜」。\n\n我想看热量最高的 5 个食物(默认 7 天)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。"},
        'fill_hints': [],
            'variants': []},
    {
            'category': "分析",     'wake_word': "查高碳水榜",     'desc': "高碳水食物 TOP5",
            'main_prompt': {
        'cli': "python scripts/render_food_ranking.py --days 7 --category high_carb", 'text': "请你加载技能 卡路里,执行唤醒词「查高碳水榜」。\n\n我想看碳水最高的 5 个食物(默认 7 天)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。"},
        'fill_hints': [],
            'variants': []},
    {
            'category': "分析",     'wake_word': "查高蛋白榜",     'desc': "高蛋白食物 TOP5",
            'main_prompt': {
        'cli': "python scripts/render_food_ranking.py --days 7 --category high_protein", 'text': "请你加载技能 卡路里,执行唤醒词「查高蛋白榜」。\n\n我想看蛋白最高的 5 个食物(默认 7 天)。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。"},
        'fill_hints': [],
            'variants': []},
    {
            'category': "饮食",     'wake_word': "看「有备注」的饮食记录",     'desc': "看「有备注」的饮食记录",
            'main_prompt': {
        'cli': "python scripts/render_today_meals.py --with-note --days <N> --chain \"1.识别→2.读DB→3.渲染\"", 'text': "请你加载技能 卡路里,执行唤醒词「看「有备注」的饮食记录」。\n\n我想看带备注的饮食记录(如「加了辣酱」「食堂打的」)。时间范围默认最近 7 天,也可指定。交付 HTML 时,文字只回复精简而全面概括的信息,文字不允许超过三句话。\n\n时间范围(选填,默认最近 7 天):____"},
        'fill_hints': [],
            'variants': []},
]


def get_summary():
    """返回统计摘要,供 hero section 显示"""
    total = len(TRIGGERS)
    total_variants = sum(len(t.get('variants', [])) for t in TRIGGERS)
    by_cat = {}
    for t in TRIGGERS:
        cat = t['category']
        by_cat[cat] = by_cat.get(cat, 0) + 1 + len(t.get('variants', []))
    return {
        'total_wake_words': total,
        'total_prompts':    total + total_variants,
        'total_categories': len(CATEGORIES),
        'by_category':      by_cat,
    }


if __name__ == '__main__':
    import json
    print(json.dumps(get_summary(), ensure_ascii=False, indent=2))
