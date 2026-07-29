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
"""


# ============ Prompt 骨架(v2.4.11 · 2026-07-26 重构) ============
# 每条 prompt = head + body + tail
# - head/tail 由 _prompt_skeleton() 统一包裹(避免重复)
# - body 由每条 TRIGGER 各自手写(具体说明该场景做什么、产出什么)
# 约束(check_prompt_quality.py 强制):
#   - body 必须非空(避免"按流程执行"这类空话)
#   - 整条 prompt 由 _prompt_skeleton() 包裹(不允许手写)

def _prompt_skeleton(wake: str, variant: str | None = None, body: str = '') -> str:
    """prompt 模板骨架:head(用户对 AI 的请求)+ body(场景细节,不指导流程)

    Args:
        wake:       主唤醒词(中文,如 '查体重趋势')
        variant:    variant 标签(如 '上周'),None 表示主 prompt
        body:       用户场景的具体说明(用户能看到什么、什么时间窗口等),**不指导 AI 流程**

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
    head = f"请你加载技能 卡路里,执行唤醒词「{name}」。"
    tail = "完成后给 1 句话总结,不需要过多文字解释。"
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
    ('🧬', '身体成分',      'body_comp'),
    ('📏', '围度',          'body_measure'),
    ('📸', '身材照片',      'body_photo'),
]


# ===== 80 唤醒词 × ~2 用法 = ~150 prompt =====
TRIGGERS = [
    {
            'category': '主页',     'wake_word': '开卡路里', 'aliases': ['卡路里面板'],     'desc': '把今日主页仪表盘渲染成 HTML:今日 KPI + 待办 + 最近 7 天小图',
            'main_prompt': {
        'cli': 'python scripts/render_home.py', 'text': '请你加载技能 卡路里,执行唤醒词「开卡路里」。\n\n我想看今日主页 dashboard(KPI 卡片 + 今日目标完成度 + 最近 7 天趋势小图 + 待办事项)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': [{
        'label': '开卡路里 [指定日期]', 'cli': 'python scripts/render_home.py --date 2026-07-20', 'prompt': '请你加载技能 卡路里,执行唤醒词「开卡路里 [指定日期]」。\n\n我要看过去某一天(不是今天)的主页 dashboard。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '主页',     'wake_word': '今日卡路里',     'desc': '打开今日 dashboard(默认今日)',
            'main_prompt': {
        'cli': 'python scripts/render_home.py', 'text': '请你加载技能 卡路里,执行唤醒词「今日卡路里」。\n\n跟"开卡路里"一样,看今日总览。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '饮食记录',     'wake_word': '记吃了',     'desc': '把一条饮食写入 food_log,并回执 HTML',
            'main_prompt': {
        'cli': 'python scripts/calorie_tracker.py add <食物> <热量> <蛋白> [碳水] [脂肪] [克数] [备注]',
        'text': '请你加载技能 卡路里,执行唤醒词「记吃了」。\n\n我刚吃了一顿,需要写进 food_log。\n\nAI 流程:\n1. 在食品库查询食物名(如 "元气森林 冰红茶汽水")。\n2. 若命中:展示营养数据(每 100g 的热量/蛋白/碳水/脂肪),等我确认后写库。\n3. 若无命中:区分单位(ml vs g),如必要请我提供克数或包装营养数据,标注估算来源。\n4. 完成后给 1 句话总结,不需要过多文字解释。'},
        'must_contain': ['食品库', '确认', '单位'],
        'variants': [{
        'label': '记吃了 [补录历史]', 'cli': 'python scripts/calorie_tracker.py add ... --date 2026-07-20 --time 12:30', 'prompt': '请你加载技能 卡路里,执行唤醒词「记吃了 [补录历史]」。\n\n刚想起来要补录之前的某次饮食(不是现在刚吃的)。同样走"查食品库 → 展示营养 → 用户确认 → 写库"4 步流程,单位 ml 与 g 区分。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '饮食记录',     'wake_word': '拍营养表',     'desc': '图片识别营养成分表并记录',
            'main_prompt': {
        'cli': 'mmx vision describe <图片> → python scripts/calorie_tracker.py add', 'text': '请你加载技能 卡路里,执行唤醒词「拍营养表」。\n\n我拍了食物包装的营养表图片,你识别后写入 food_log。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '饮食记录',     'wake_word': '删吃的',     'desc': '删除饮食记录(生成 crud_receipt 回执)',
            'main_prompt': {
        'cli': 'python scripts/calorie_tracker.py delete <id>', 'text': '请你加载技能 卡路里,执行唤醒词「删吃的」。\n\n我想删某条饮食记录,告诉我是哪条。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '饮食记录',     'wake_word': '改吃的',     'desc': '修改已记录饮食(8 字段)',
            'main_prompt': {
        'cli': 'python scripts/calorie_tracker.py update-meal <id> [--grams] [--food] [--calories] [--protein] [--carbs] [--fat] [--date] [--time] [--note]', 'text': '请你加载技能 卡路里,执行唤醒词「改吃的」。\n\n我想改某条饮食记录的一个字段(食物/克数/热量/蛋白/碳水/脂肪/日期/时间/备注)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '饮食记录',     'wake_word': '查今天吃',     'desc': '今日饮食摘要(4 餐)',
            'main_prompt': {
        'cli': 'python scripts/render_today_diet.py', 'text': '请你加载技能 卡路里,执行唤醒词「查今天吃」。\n\n我想看今天按餐次组织的吃了什么清单。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': [{
        'label': '查今天吃 昨天', 'cli': 'python scripts/render_today_diet.py --date 2026-07-25', 'prompt': '请你加载技能 卡路里,执行唤醒词「查今天吃 昨天」。\n\n我要看昨天的饮食摘要。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '饮食记录',     'wake_word': '查吃的记录',     'desc': '今日逐条饮食记录(list)',
            'alias_of': '查今天吃',  # ADR-0002 · ticket 03+04: 查吃的记录 = 查今天吃 的 alias,主 prompt 同源
            'main_prompt': {
        'cli': 'python scripts/render_today_diet.py', 'text': '请你加载技能 卡路里,执行唤醒词「查吃的记录」。\n\n我想看今天吃的明细(逐条/不是摘要)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': [{
        'label': '查吃的记录 昨天', 'cli': 'python scripts/render_today_diet.py --date 2026-07-25', 'prompt': '请你加载技能 卡路里,执行唤醒词「查吃的记录 昨天」。\n\n我要看昨天的逐条饮食记录。\n\n完成后给 1 句话总结,不需要过多文字解释。'}, {
        'label': '查吃的记录 7/1 到 7/14', 'cli': 'python scripts/render_today_meals.py --start 2026-07-01 --end 2026-07-14', 'prompt': '请你加载技能 卡路里,执行唤醒词「查吃的记录 7/1 到 7/14」。\n\n我给出明确日期区间,你看区间生成列表(跨多日时切到 today_meals 模板)。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '饮食记录',     'wake_word': '查热量历史',     'desc': '最近 N 天热量摄入历史',
            'main_prompt': {
        'cli': 'python scripts/render_calorie_trend.py --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「查热量历史」。\n\n我想看最近 N 天每日热量摄入趋势(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': [{
        'label': '查热量历史 30 天', 'cli': 'python scripts/render_calorie_trend.py --days 30', 'prompt': '请你加载技能 卡路里,执行唤醒词「查热量历史 30 天」。\n\n时间窗口固定最近 30 天。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '饮食记录',     'wake_word': '记喝水',     'desc': '记录饮水量',
            'main_prompt': {
        'cli': 'python scripts/calorie_tracker.py water <ml>', 'text': '请你加载技能 卡路里,执行唤醒词「记喝水」。\n\n我喝了一杯水,记录饮水量。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '饮食记录',     'wake_word': '查今天喝水',     'desc': '今日饮水量(进度环 + 7 天 mini-chart)',
            'main_prompt': {
        'cli': 'python scripts/render_today_water.py', 'text': '请你加载技能 卡路里,执行唤醒词「查今天喝水」。\n\n我想看今天的饮水量。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '食品库',     'wake_word': '查热量',     'desc': '搜索食品营养成分',
            'main_prompt': {
        'cli': 'python scripts/calorie_tracker.py search-product <关键词>', 'text': '请你加载技能 卡路里,执行唤醒词「查热量」。\n\n我想查某食物的热量/蛋白/碳水/脂肪。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '食品库',     'wake_word': '存食品',     'desc': '添加食品营养成分到库',
            'main_prompt': {
        'cli': 'python scripts/calorie_tracker.py add-product <名称> <品牌> <热量> <蛋白质> <脂肪> <饱和脂肪> <碳水> <糖> <膳食纤维> <钠>', 'text': '请你加载技能 卡路里,执行唤醒词「存食品」。\n\n我要把新食品的营养数据存入食品库,告诉你必填字段(名称/品牌/热量/蛋白/脂肪/饱和脂肪/碳水/糖/膳食纤维/钠)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '食品库',     'wake_word': '改食品',     'desc': '更新食品营养数据',
            'main_prompt': {
        'cli': 'python scripts/calorie_tracker.py update-product <id> [--calories] [--protein] ...', 'text': '请你加载技能 卡路里,执行唤醒词「改食品」。\n\n我想改某条食品库的某个字段。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '食品库',     'wake_word': '查食品库',     'desc': '列出全部食品营养成分',
            'main_prompt': {
        'cli': 'python scripts/calorie_tracker.py list-products', 'text': '请你加载技能 卡路里,执行唤醒词「查食品库」。\n\n我想列出全部食品库。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '食品库',     'wake_word': '批量导入',     'desc': '批量录入/更新食品库',
            'main_prompt': {
        'cli': 'python scripts/batch_import.py import <file.jsonl>', 'text': '请你加载技能 卡路里,执行唤醒词「批量导入」。\n\n我有一个 JSONL 文件要批量录入食品库。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '食品库',     'wake_word': '校验批量',     'desc': '只校验 JSONL 不写入',
            'main_prompt': {
        'cli': 'python scripts/batch_import.py validate <file.jsonl>', 'text': '请你加载技能 卡路里,执行唤醒词「校验批量」。\n\n我要先校验我的 JSONL 文件能不能导入(不真正写入)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '体重',     'wake_word': '记体重',     'desc': '记录体重(身高自动从 user_profile 读)',
            'main_prompt': {
        'cli': 'python scripts/calorie_tracker.py weight <kg> [--note "<备注>"]', 'text': '请你加载技能 卡路里,执行唤醒词「记体重」。\n\n我刚称了体重,记录一下。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '体重',     'wake_word': '改体重记录',     'desc': '修改历史体重记录',
            'main_prompt': {
        'cli': 'python scripts/calorie_tracker.py weight-update <id> [--weight <kg>] [--note <备注>]', 'text': '请你加载技能 卡路里,执行唤醒词「改体重记录」。\n\n我要改某条历史体重记录。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '体重',     'wake_word': '查体重历史',     'desc': '体重历史记录(mode=history)',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode history --days 30', 'text': '请你加载技能 卡路里,执行唤醒词「查体重历史」。\n\n我想看最近 N 天每天的体重列表(默认 30 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': [{
        'label': '查体重历史 上周', 'cli': 'python scripts/render_weight_history.py --mode history --days 7', 'prompt': '请你加载技能 卡路里,执行唤醒词「查体重历史 上周」。\n\n时间窗口固定最近 7 天。\n\n完成后给 1 句话总结,不需要过多文字解释。'}, {
        'label': '查体重历史 7/1 到 7/31', 'cli': 'python scripts/render_weight_history.py --mode history --start 2026-07-01 --end 2026-07-31', 'prompt': '请你加载技能 卡路里,执行唤醒词「查体重历史 7/1 到 7/31」。\n\n我要看整月体重列表。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '体重',     'wake_word': '查体重趋势',     'desc': '把体重画成折线图,看涨跌 + 起止差 + 异常点',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode trend --days 30', 'text': '请你加载技能 卡路里,执行唤醒词「查体重趋势」。\n\n我想看体重折线图,带起止对比和异常点高亮。默认最近 30 天,如果我说"上周"就是 7 天,"最近 90 天"就是 90 天,"7 月"就是当月整月。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': [{
        'label': '查体重趋势 上周', 'cli': 'python scripts/render_weight_history.py --mode trend --days 7', 'prompt': '请你加载技能 卡路里,执行唤醒词「查体重趋势 上周」。\n\n时间窗口固定最近 7 天。\n\n完成后给 1 句话总结,不需要过多文字解释。'}, {
        'label': '查体重趋势 昨天', 'cli': 'python scripts/render_weight_history.py --mode trend --start 2026-07-25 --end 2026-07-25', 'prompt': '请你加载技能 卡路里,执行唤醒词「查体重趋势 昨天」。\n\n单日查询,要看那一天的体重数据卡片。\n\n完成后给 1 句话总结,不需要过多文字解释。'}, {
        'label': '查体重趋势 7/1 到 7/14', 'cli': 'python scripts/render_weight_history.py --mode trend --start 2026-07-01 --end 2026-07-14', 'prompt': '请你加载技能 卡路里,执行唤醒词「查体重趋势 7/1 到 7/14」。\n\n我给出明确日期区间,你按区间生成折线图。\n\n完成后给 1 句话总结,不需要过多文字解释。'}, {
        'label': '查体重趋势 7 月', 'cli': 'python scripts/render_weight_history.py --mode trend --start 2026-07-01 --end 2026-07-31', 'prompt': '请你加载技能 卡路里,执行唤醒词「查体重趋势 7 月」。\n\n整月查询,7 月 1 号到 7 月底。\n\n完成后给 1 句话总结,不需要过多文字解释。'}, {
        'label': '查体重趋势 最近 90 天', 'cli': 'python scripts/render_weight_history.py --mode trend --days 90', 'prompt': '请你加载技能 卡路里,执行唤醒词「查体重趋势 最近 90 天」。\n\n时间窗口固定最近 90 天。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '体重',     'wake_word': '对比体重',     'desc': '两时间段体重对比(mode=compare)',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode compare --days 30', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重」。\n\n我想对比两段时间的体重差异(默认 30 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': [{
        'label': '对比体重 7/1 到 7/31', 'cli': 'python scripts/render_weight_history.py --mode compare --start 2026-07-01 --end 2026-07-31', 'prompt': '请你加载技能 卡路里,执行唤醒词「对比体重 7/1 到 7/31」。\n\n我要对比 7 月整月内前后两段体重。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '体重',     'wake_word': '查体重波动',     'desc': '体重波动分析(标准差 + 异常点,mode=volatility)',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode volatility --days 30', 'text': '请你加载技能 卡路里,执行唤醒词「查体重波动」。\n\n我想看体重波动大小 + 异常点(默认 30 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '体重',     'wake_word': '设体重目标',     'desc': '设置体重目标 + 截止日期',
            'main_prompt': {
        'cli': 'python scripts/calorie_tracker.py weight-goal <kg> [deadline YYYY-MM-DD]', 'text': '请你加载技能 卡路里,执行唤醒词「设体重目标」。\n\n我要设减重/增重目标(kg + 可选截止日期)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '体重',     'wake_word': '查体重目标',     'desc': '体重目标达成进度',
            'main_prompt': {
        'cli': 'python scripts/calorie_tracker.py weight-goal-progress', 'text': '请你加载技能 卡路里,执行唤醒词「查体重目标」。\n\n我想看体重目标的完成进度。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '运动',     'wake_word': '记运动',     'desc': '记录运动消耗',
            'main_prompt': {
        'cli': 'python scripts/exercise_tracker.py add --date YYYY-MM-DD --type <类型> --calories <卡> [--minutes N] [--reps N]', 'text': '请你加载技能 卡路里,执行唤醒词「记运动」。\n\n我做了一项运动,记录运动类型 + 消耗热量 + 可选时长/次数。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '运动',     'wake_word': '改运动记录',     'desc': '更新运动记录',
            'main_prompt': {
        'cli': 'python scripts/exercise_tracker.py update --id <id> [--type] [--calories] [--minutes] ...', 'text': '请你加载技能 卡路里,执行唤醒词「改运动记录」。\n\n我要改某条运动记录。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '运动',     'wake_word': '查运动记录',     'desc': '查询运动记录(mode=records)',
            'main_prompt': {
        'cli': 'python scripts/render_exercise_summary.py --mode records --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「查运动记录」。\n\n我想看最近 N 天的运动明细(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': [{
        'label': '查运动记录 30 天', 'cli': 'python scripts/render_exercise_summary.py --mode records --days 30', 'prompt': '请你加载技能 卡路里,执行唤醒词「查运动记录 30 天」。\n\n时间窗口固定最近 30 天。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '运动',     'wake_word': '查运动汇总',     'desc': '运动汇总统计(mode=summary)',
            'main_prompt': {
        'cli': 'python scripts/render_exercise_summary.py --mode summary --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「查运动汇总」。\n\n我想看最近 N 天运动总消耗 + 总时长 + 活跃天数(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': [{
        'label': '查运动汇总 7 月', 'cli': 'python scripts/render_exercise_summary.py --mode summary --start 2026-07-01 --end 2026-07-31', 'prompt': '请你加载技能 卡路里,执行唤醒词「查运动汇总 7 月」。\n\n整月查询,7 月 1 号到 7 月底。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '运动',     'wake_word': '查运动类型',     'desc': '运动类型统计(力量/有氧/柔韧/日常)',
            'main_prompt': {
        'cli': 'python scripts/render_exercise_summary.py --mode stats --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「查运动类型」。\n\n我想看 4 类运动(力量/有氧/柔韧/日常)的占比(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '运动',     'wake_word': '查运动趋势',     'desc': '运动热量趋势(mode=trend,面积图)',
            'main_prompt': {
        'cli': 'python scripts/render_exercise_summary.py --mode trend --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「查运动趋势」。\n\n我想看每日运动消耗的面积图(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '健身计划',     'wake_word': '查健身计划', 'aliases': ['查询健身计划'],     'desc': '查看训练计划 HTML 页面(DB 数据驱动)',
            'main_prompt': {
        'cli': 'python scripts/render_workout_plan.py', 'text': '请你加载技能 卡路里,执行唤醒词「查健身计划」。\n\n我想看完整健身计划 + 今日复盘 section。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': [{
        'label': '查健身计划 --review', 'cli': 'python scripts/render_workout_plan.py --review', 'prompt': '请你加载技能 卡路里,执行唤醒词「查健身计划 --review」。\n\n我要看健身计划 + 今日复盘 section。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '健身计划',     'wake_word': '制定健身计划',     'desc': 'AI 采访式对话 → 校验 → 写入',
            'main_prompt': {
        'cli': 'AI 路由 → python scripts/plan_generator.py', 'text': '请你加载技能 卡路里,执行唤醒词「制定健身计划」。\n\n我要新设一份完整健身计划,从目标/经验/频率/部位几个维度跟我聊。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '健身计划',     'wake_word': '改健身计划',     'desc': 'AI 对话定位意图 → 改/增/删时段、调整周次',
            'main_prompt': {
        'cli': 'AI 路由 → python scripts/plan_generator.py', 'text': '请你加载技能 卡路里,执行唤醒词「改健身计划」。\n\n我要改既有计划(增删动作/调整周次/改时段等),先问你确认意图。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '健身计划',     'wake_word': '落地健身计划',     'desc': '把某天的健身计划执行一次:补计划 + 写心愿 + 推训记',
            'main_prompt': {
        'cli': 'python scripts/render_process_progress.py --input <json>', 'text': '请你加载技能 卡路里,执行唤醒词「落地健身计划」。\n\n我要把今天(某天)的计划真正执行一次,过程走完后给我看进度页。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '健身计划',     'wake_word': '卡路里同步',     'desc': '批量回填最近 3 天:每条 plan 都推训记 + 拉训记实际数据回写',
            'main_prompt': {
        'cli': 'python scripts/render_process_progress.py --input <json>', 'text': '请你加载技能 卡路里,执行唤醒词「卡路里同步」。\n\n最近 3 天的计划都还没真正落地,我要批量执行一次(推训记 + 拉训记回写),给我看总体进度页。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '健身计划',     'wake_word': '回写训记',     'desc': '拉训记数据回写 exercise_log(幂等)',
            'main_prompt': {
        'cli': 'python scripts/xunji_bridge.py backfill [--date <DATE>] [--days <N>]', 'text': '请你加载技能 卡路里,执行唤醒词「回写训记」。\n\n我要从训记拉取已完成的训练,写入运动记录。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': [{
        'label': '回写训记 最近 7 天', 'cli': 'python scripts/xunji_bridge.py backfill --days 7', 'prompt': '请你加载技能 卡路里,执行唤醒词「回写训记 最近 7 天」。\n\n时间窗口固定最近 7 天的训记实绩。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '健身计划',     'wake_word': '训记-覆盖X日的训练计划',     'desc': '用卡路里 plan 覆盖训记某天训练',
            'main_prompt': {
        'cli': 'python scripts/xunji_bridge.py overlay-plan --date <DATE>', 'text': '请你加载技能 卡路里,执行唤醒词「训记-覆盖X日的训练计划」。\n\n我要把卡路里的计划推到训记覆盖同一天的安排。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '健身计划',     'wake_word': '复盘训练',     'desc': '对指定时间段做 plan vs 实绩对比',
            'main_prompt': {
        'cli': 'python scripts/render_exercise_review_html.py --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「复盘训练」。\n\n我要对比健身计划 vs 实际完成情况(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': [{
        'label': '复盘训练 今天', 'cli': 'python scripts/render_exercise_review_html.py --start 2026-07-26 --end 2026-07-26', 'prompt': '请你加载技能 卡路里,执行唤醒词「复盘训练 今天」。\n\n我要看今天 vs 计划的对比。\n\n完成后给 1 句话总结,不需要过多文字解释。'}, {
        'label': '复盘训练 这周', 'cli': 'python scripts/render_exercise_review_html.py --days 7', 'prompt': '请你加载技能 卡路里,执行唤醒词「复盘训练 这周」。\n\n我要看本周 vs 计划的对比(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '健身计划',     'wake_word': '扫禁忌',     'desc': '检测 plan/DB 中禁忌动作(腰/膝/肩)',
            'main_prompt': {
        'cli': 'python scripts/render_contraindication.py', 'text': '请你加载技能 卡路里,执行唤醒词「扫禁忌」。\n\n我要扫出健身计划/数据库里可能伤腰/膝/肩的动作(默认全身位)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': [{
        'label': '扫禁忌 腰', 'cli': 'python scripts/render_contraindication.py --part 腰', 'prompt': '请你加载技能 卡路里,执行唤醒词「扫禁忌 腰」。\n\n只要扫腰部相关禁忌动作。\n\n完成后给 1 句话总结,不需要过多文字解释。'}, {
        'label': '扫禁忌 膝', 'cli': 'python scripts/render_contraindication.py --part 膝', 'prompt': '请你加载技能 卡路里,执行唤醒词「扫禁忌 膝」。\n\n只要扫膝部相关禁忌动作。\n\n完成后给 1 句话总结,不需要过多文字解释。'}, {
        'label': '扫禁忌 肩', 'cli': 'python scripts/render_contraindication.py --part 肩', 'prompt': '请你加载技能 卡路里,执行唤醒词「扫禁忌 肩」。\n\n只要扫肩部相关禁忌动作。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '健身计划',     'wake_word': '审计动作名',     'desc': '扫描 plan 里非训记官方动作名(push-plan 前必跑)',
            'main_prompt': {
        'cli': 'python scripts/audit_plan_names.py [--strict] [--fix-suggestions]', 'text': '请你加载技能 卡路里,执行唤醒词「审计动作名」。\n\n推送训记前我先确认 plan 里的动作名都能映射。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '分析',     'wake_word': '查热量趋势',     'desc': '热量摄入趋势',
            'main_prompt': {
        'cli': 'python scripts/render_calorie_trend.py --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「查热量趋势」。\n\n我想看每日热量摄入趋势(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': [{
        'label': '查热量趋势 上周', 'cli': 'python scripts/render_calorie_trend.py --days 7', 'prompt': '请你加载技能 卡路里,执行唤醒词「查热量趋势 上周」。\n\n时间窗口/参数语境:查热量趋势 上周。\n\n完成后给 1 句话总结,不需要过多文字解释。'}, {
        'label': '查热量趋势 7 月', 'cli': 'python scripts/render_calorie_trend.py --start 2026-07-01 --end 2026-07-31', 'prompt': '请你加载技能 卡路里,执行唤醒词「查热量趋势 7 月」。\n\n时间窗口/参数语境:查热量趋势 7 月。\n\n完成后给 1 句话总结,不需要过多文字解释。'}, {
        'label': '查热量趋势 最近 30 天', 'cli': 'python scripts/render_calorie_trend.py --days 30', 'prompt': '请你加载技能 卡路里,执行唤醒词「查热量趋势 最近 30 天」。\n\n时间窗口/参数语境:查热量趋势 最近 30 天。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '分析',     'wake_word': '查营养结构',     'desc': '营养素占比分析',
            'main_prompt': {
        'cli': 'python scripts/render_nutrition_ratio.py --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「查营养结构」。\n\n我想看蛋白/碳水/脂肪占比(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': [{
        'label': '查营养结构 7 月', 'cli': 'python scripts/render_nutrition_ratio.py --start 2026-07-01 --end 2026-07-31', 'prompt': '请你加载技能 卡路里,执行唤醒词「查营养结构 7 月」。\n\n时间窗口/参数语境:查营养结构 7 月。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '分析',     'wake_word': '查热量缺口',     'desc': '热量缺口分析(摄入 vs 运动 vs TDEE)',
            'main_prompt': {
        'cli': 'python scripts/render_calorie_deficit.py --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「查热量缺口」。\n\n我想看摄入 vs 运动消耗的缺口(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '分析',     'wake_word': '查食物排行',     'desc': '食物排行榜(默认高热量榜)',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「查食物排行」。\n\n我想看 TOP 食物热量榜(默认高热量,默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '分析',     'wake_word': '查高热量榜',     'desc': '热量炸弹 TOP5',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --days 7 --category high_calorie', 'text': '请你加载技能 卡路里,执行唤醒词「查高热量榜」。\n\n我想看热量最高的 5 个食物(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '分析',     'wake_word': '查低热量榜',     'desc': '低热量健康 TOP5',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --days 7 --category low_calorie', 'text': '请你加载技能 卡路里,执行唤醒词「查低热量榜」。\n\n我想看热量最低的 5 个健康食物(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '分析',     'wake_word': '查频繁吃榜',     'desc': '最常吃的食物 TOP5',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --days 7 --category frequent', 'text': '请你加载技能 卡路里,执行唤醒词「查频繁吃榜」。\n\n我想看吃最多次的食物(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '分析',     'wake_word': '查高碳水榜',     'desc': '高碳水食物 TOP5',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --days 7 --category high_carb', 'text': '请你加载技能 卡路里,执行唤醒词「查高碳水榜」。\n\n我想看碳水最高的 5 个食物(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '分析',     'wake_word': '查高蛋白榜',     'desc': '高蛋白食物 TOP5',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --days 7 --category high_protein', 'text': '请你加载技能 卡路里,执行唤醒词「查高蛋白榜」。\n\n我想看蛋白最高的 5 个食物(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '分析',     'wake_word': '查运动分布',     'desc': '运动类型分布',
            'main_prompt': {
        'cli': 'python scripts/render_exercise_distribution.py --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「查运动分布」。\n\n我想看 4 类运动(力量/有氧/柔韧/日常)的时间/消耗分布(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '分析',     'wake_word': '查运动贡献',     'desc': '运动对热量缺口的贡献占比',
            'main_prompt': {
        'cli': 'python scripts/render_exercise_distribution.py --days 7 --mode contribution', 'text': '请你加载技能 卡路里,执行唤醒词「查运动贡献」。\n\n我想看运动在热量缺口里的占比(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '综合',     'wake_word': '设营养目标',     'desc': '设置每日营养目标',
            'main_prompt': {
        'cli': 'python scripts/calorie_tracker.py goal <热量> <蛋白> <碳水> <脂肪> [饮水ml]', 'text': '请你加载技能 卡路里,执行唤醒词「设营养目标」。\n\n我要改每日 4 大宏量(热量/蛋白/碳水/脂肪)+ 饮水目标。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '综合',     'wake_word': '查营养目标',     'desc': '查看当前每日营养目标',
            'main_prompt': {
        'cli': 'python scripts/calorie_tracker.py get-goal', 'text': '请你加载技能 卡路里,执行唤醒词「查营养目标」。\n\n我想看当前的营养目标。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '综合',     'wake_word': '查健康报告',     'desc': '四维度综合健康仪表盘',
            'main_prompt': {
        'cli': 'python scripts/render_health_dashboard.py --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「查健康报告」。\n\n我要看 4 维健康仪表盘(热量/营养/运动/体重综合,默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': [{
        'label': '查健康报告 本月', 'cli': 'python scripts/render_health_dashboard.py --start 2026-07-01 --end 2026-07-26', 'prompt': '请你加载技能 卡路里,执行唤醒词「查健康报告 本月」。\n\n我要看本月 1 号到今天的健康报告。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '综合',     'wake_word': '查卡路里数据',     'desc': '数据健康检查(lint_health)',
            'main_prompt': {
        'cli': 'python scripts/render_lint_health.py', 'text': '请你加载技能 卡路里,执行唤醒词「查卡路里数据」。\n\n我要检查数据库的健康性。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '复盘',     'wake_word': '复盘',     'desc': '生成 8 维度复盘报告 HTML + 可选飞书发送',
            'main_prompt': {
        'cli': 'python scripts/render_review.py', 'text': '请你加载技能 卡路里,执行唤醒词「复盘」。\n\n我要看一份复盘报告,默认最近 7 天,带 8 个维度(热量/营养/运动/体重/饮水/缺口/目标/周对比)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '复盘',     'wake_word': '今日复盘', 'aliases': ['复盘今日', '日复盘'],     'desc': '当日复盘',
            'main_prompt': {
        'cli': 'python scripts/render_review.py --type day', 'text': '请你加载技能 卡路里,执行唤醒词「今日复盘」。\n\n我要看当日复盘。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '复盘',     'wake_word': '本周复盘', 'aliases': ['复盘本周', '周复盘'],     'desc': '本周复盘(本周一-今天)',
            'main_prompt': {
        'cli': 'python scripts/render_review.py --type week', 'text': '请你加载技能 卡路里,执行唤醒词「本周复盘」。\n\n我要看本周一-今天的复盘。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '复盘',     'wake_word': '本月复盘', 'aliases': ['复盘本月', '月复盘'],     'desc': '本月复盘(本月 1 号-今天)',
            'main_prompt': {
        'cli': 'python scripts/render_review.py --type month', 'text': '请你加载技能 卡路里,执行唤醒词「本月复盘」。\n\n我要看本月 1 号-今天的复盘。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '复盘',     'wake_word': '本年复盘', 'aliases': ['复盘本年', '年复盘'],     'desc': '本年复盘(今年 1/1-今天)',
            'main_prompt': {
        'cli': 'python scripts/render_review.py --type year', 'text': '请你加载技能 卡路里,执行唤醒词「本年复盘」。\n\n我要看今年 1/1 - 今天的复盘。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '复盘',     'wake_word': '复盘日期范围',     'desc': '自定义日期范围复盘',
            'main_prompt': {
        'cli': 'python scripts/render_review.py --range 2026-07-01:2026-07-14', 'text': '请你加载技能 卡路里,执行唤醒词「复盘日期范围」。\n\n我要看任意起止日期的复盘。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '复盘',     'wake_word': '开启定时复盘',     'desc': '启动 cron(默认 23:00 / 过去 7 天)',
            'main_prompt': {
        'cli': 'mavis cron create ...', 'text': '请你加载技能 卡路里,执行唤醒词「开启定时复盘」。\n\n我要设每天自动跑复盘(默认 23:00 跑过去 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '复盘',     'wake_word': '关闭定时复盘',     'desc': '删除 cron',
            'main_prompt': {
        'cli': 'mavis cron delete ...', 'text': '请你加载技能 卡路里,执行唤醒词「关闭定时复盘」。\n\n我要关掉每天自动复盘。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '复盘',     'wake_word': '查定时复盘',     'desc': '查看当前定时复盘配置',
            'main_prompt': {
        'cli': 'mavis cron list', 'text': '请你加载技能 卡路里,执行唤醒词「查定时复盘」。\n\n我想看当前定时复盘配置。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '身体成分',     'wake_word': '记体脂',     'desc': '皮褶钳测 7 点(Jackson-Pollock 自动算体脂率)',
            'main_prompt': {
        'cli': 'python scripts/body_composition.py add ... → HTML:body_composition_wizard.html', 'text': '请你加载技能 卡路里,执行唤醒词「记体脂」。\n\n我用皮褶钳测了 7 点(胸/腹/大腿/三头/肩胛下/髂上/腋中 mm),给我算体脂率。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '身体成分',     'wake_word': '查体脂',     'desc': '历史体脂记录',
            'main_prompt': {
        'cli': 'python scripts/render_body_composition_wizard.py → list 视图', 'text': '请你加载技能 卡路里,执行唤醒词「查体脂」。\n\n我想看历史体脂测量记录。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '身体成分',     'wake_word': '查体脂趋势',     'desc': '体脂率时间线',
            'main_prompt': {
        'cli': 'python scripts/body_composition.py trend', 'text': '请你加载技能 卡路里,执行唤醒词「查体脂趋势」。\n\n我想看体脂率走势时间线。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '身体成分',     'wake_word': '删体脂',     'desc': '软删除体脂记录',
            'main_prompt': {
        'cli': 'python scripts/body_composition.py delete <id> → HTML:crud_receipt.html', 'text': '请你加载技能 卡路里,执行唤醒词「删体脂」。\n\n我要删某条体脂记录。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '围度',     'wake_word': '记围度',     'desc': '13 部位围度入库:上身 5 + 下身 4 + 手臂 4,cm 单位',
            'main_prompt': {
        'cli': 'python scripts/render_body_measurements_wizard.py [--chest-cm ...]', 'text': '请你加载技能 卡路里,执行唤醒词「记围度」。\n\n我想录入 13 部位围度(胸/腰/臀/大腿/小腿/手臂/前臂/颈/肩,左+右)。如果我已经给了具体数字就用它们,如果没给就让我看到空 form。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '围度',     'wake_word': '查围度',     'desc': '历史围度记录',
            'main_prompt': {
        'cli': 'python scripts/render_body_measurements_wizard.py → list 视图', 'text': '请你加载技能 卡路里,执行唤醒词「查围度」。\n\n我想看历史围度测量记录。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '围度',     'wake_word': '查围度趋势',     'desc': '单围度时间线',
            'main_prompt': {
        'cli': 'python scripts/body_measurements.py trend --metric <col>', 'text': '请你加载技能 卡路里,执行唤醒词「查围度趋势」。\n\n我想看某一部位围度走势时间线。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '围度',     'wake_word': '删围度',     'desc': '软删除围度记录',
            'main_prompt': {
        'cli': 'python scripts/body_measurements.py delete <id> → HTML:crud_receipt.html', 'text': '请你加载技能 卡路里,执行唤醒词「删围度」。\n\n我要删某条围度记录。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '身材照片',     'wake_word': '记身材照',     'desc': '记录身材照片',
            'main_prompt': {
        'cli': 'python scripts/body_photo_log_wizard.py → 用户填路径 → add', 'text': '请你加载技能 卡路里,执行唤醒词「记身材照」。\n\n我要给身材照加一条入库记录(日期/时间/路径/标签/备注)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '身材照片',     'wake_word': '查身材照',     'desc': '查看照片历史(浏览 + 选 + 裁剪 + 调细节)',
            'main_prompt': {
        'cli': 'python scripts/render_body_photo_gif_planner.py --tag 正面', 'text': '请你加载技能 卡路里,执行唤醒词「查身材照」。\n\n我要浏览身材照(可筛选 + 裁剪 + 生成 GIF)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '身材照片',     'wake_word': '生成身材照GIF',     'desc': '生成身材变化 GIF',
            'main_prompt': {
        'cli': 'python scripts/render_body_photo_gif_planner.py --tag X --photo-id ...', 'text': '请你加载技能 卡路里,执行唤醒词「生成身材照GIF」。\n\n我要把多张身材照生成变化 GIF。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '身材照片',     'wake_word': '删身材照',     'desc': '删除身材照片',
            'main_prompt': {
        'cli': 'python scripts/body_photo_tracker.py delete <id>', 'text': '请你加载技能 卡路里,执行唤醒词「删身材照」。\n\n我要删某张照片。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '身材照片',     'wake_word': '改照片标签',     'desc': '修改照片标签',
            'main_prompt': {
        'cli': 'python scripts/body_photo_tracker.py tag <id> <new_tag>', 'text': '请你加载技能 卡路里,执行唤醒词「改照片标签」。\n\n我要改某张照片的 tag。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []},
    {
            'category': '综合',     'wake_word': '设置档案',     'desc': '设置 user_profile(年龄/性别/身高/备注)',
            'main_prompt': {
        'cli': 'python scripts/render_profile_setup.py → 用户填 → 复制 prompt → set', 'text': '请你加载技能 卡路里,执行唤醒词「设置档案」。\n\n我要设身高/年龄/性别(影响 BMI/TDEE/营养目标)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': [{
        'label': '设置档案 (直接传参)', 'cli': 'python scripts/calorie_tracker.py profile set <age> <gender> --height <cm>', 'prompt': '请你加载技能 卡路里,执行唤醒词「设置档案 (直接传参)」。\n\n我已经给了完整参数,你直接调 set。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '综合',     'wake_word': '查档案',     'desc': '查看 user_profile + 最新体重',
            'main_prompt': {
        'cli': 'python scripts/render_crud_view.py --entity profile', 'text': '请你加载技能 卡路里,执行唤醒词「查档案」。\n\n我要看自己的档案 + 最新体重。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'variants': []}
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
