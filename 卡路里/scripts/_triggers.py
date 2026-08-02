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
    ('🎯', '目标管理',      'goal'),
]


# ===== 101 唤醒词(80 旧 + 25 目标管理新场景) =====
TRIGGERS = [
    {
            'category': '主页',     'wake_word': '看今日主页', 'aliases': ['开卡路里', '卡路里面板', '今日卡路里'],     'desc': '把今日主页仪表盘渲染成 HTML:今日 4 维 KPI + 待办 + 最近 7 天小图',
            'main_prompt': {
        'cli': 'python scripts/render_home.py', 'text': '请你加载技能 卡路里,执行唤醒词「看今日主页」。\n\n我想看今天主页 dashboard:今日 4 维 KPI(热量/蛋白/饮水/运动)+ 今日目标完成度 + 最近 7 天趋势小图 + 待办事项。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '饮食记录',     'wake_word': '记吃了',     'desc': '把一条饮食写入 food_log,并回执 HTML',
            'main_prompt': {
        'cli': 'python scripts/calorie_tracker.py add <食物> <热量> <蛋白> [碳水] [脂肪] [克数] [备注]',
        'text': '请你加载技能 卡路里,执行唤醒词「记吃了」。\n\n我刚吃了一顿,需要写进 food_log。\n\nAI 流程:\n1. 在食品库查询食物名(如 "元气森林 冰红茶汽水")。\n2. 若命中:展示营养数据(每 100g 的热量/蛋白/碳水/脂肪),等我确认后写库。\n3. 若无命中:区分单位(ml vs g),如必要请我提供克数或包装营养数据,标注估算来源。\n4. 完成后给 1 句话总结,不需要过多文字解释。'},
        'must_contain': ['食品库', '确认', '单位'],
        'fill_hints': ['食物名称(必填): ', '克数(选填,默认按食品库每 100g): '],
        'variants': [{
        'label': '记吃了 [补录历史]', 'cli': 'python scripts/calorie_tracker.py add ... --date 2026-07-20 --time 12:30', 'prompt': '请你加载技能 卡路里,执行唤醒词「记吃了 [补录历史]」。\n\n刚想起来要补录之前的某次饮食(不是现在刚吃的)。同样走"查食品库 → 展示营养 → 用户确认 → 写库"4 步流程,单位 ml 与 g 区分。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '饮食记录',     'wake_word': '拍营养表',     'desc': '图片识别营养成分表并记录',
            'main_prompt': {
        'cli': 'mmx vision describe <图片> → python scripts/calorie_tracker.py add', 'text': '请你加载技能 卡路里,执行唤醒词「拍营养表」。\n\n我拍了食物包装的营养表图片,你识别后写入 food_log。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '饮食记录',     'wake_word': '删吃的',     'desc': '删除饮食记录(生成 crud_receipt 回执)',
            'main_prompt': {
        'cli': 'python scripts/calorie_tracker.py delete <id>', 'text': '请你加载技能 卡路里,执行唤醒词「删吃的」。\n\n我想删某条饮食记录,告诉我是哪条。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '饮食记录',     'wake_word': '改吃的',     'desc': '修改已记录饮食(8 字段)',
            'main_prompt': {
        'cli': 'python scripts/calorie_tracker.py update-meal <id> [--grams] [--food] [--calories] [--protein] [--carbs] [--fat] [--date] [--time] [--note]', 'text': '请你加载技能 卡路里,执行唤醒词「改吃的」。\n\n我想改某条饮食记录的一个字段(食物/克数/热量/蛋白/碳水/脂肪/日期/时间/备注)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '饮食记录',     'wake_word': '查今天吃',     'desc': '今日饮食摘要(4 餐)',
            'main_prompt': {
        'cli': 'python scripts/render_today_diet.py', 'text': '请你加载技能 卡路里,执行唤醒词「查今天吃」。\n\n我想看今天按餐次组织的吃了什么清单。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': [{
        'label': '查今天吃 昨天', 'cli': 'python scripts/render_today_diet.py --date 2026-07-25', 'prompt': '请你加载技能 卡路里,执行唤醒词「查今天吃 昨天」。\n\n我要看昨天的饮食摘要。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '饮食记录',     'wake_word': '查吃的记录',     'desc': '今日逐条饮食记录(list)',
            'alias_of': '查今天吃',  # ADR-0002 · ticket 03+04: 查吃的记录 = 查今天吃 的 alias,主 prompt 同源
            'main_prompt': {
        'cli': 'python scripts/render_today_diet.py', 'text': '请你加载技能 卡路里,执行唤醒词「查吃的记录」。\n\n我想看今天吃的明细(逐条/不是摘要)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': [{
        'label': '查吃的记录 昨天', 'cli': 'python scripts/render_today_diet.py --date 2026-07-25', 'prompt': '请你加载技能 卡路里,执行唤醒词「查吃的记录 昨天」。\n\n我要看昨天的逐条饮食记录。\n\n完成后给 1 句话总结,不需要过多文字解释。'}, {
        'label': '查吃的记录 7/1 到 7/14', 'cli': 'python scripts/render_today_meals.py --start 2026-07-01 --end 2026-07-14', 'prompt': '请你加载技能 卡路里,执行唤醒词「查吃的记录 7/1 到 7/14」。\n\n我给出明确日期区间,你看区间生成列表(跨多日时切到 today_meals 模板)。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '饮食记录',     'wake_word': '查热量历史',     'desc': '最近 N 天热量摄入历史',
            'main_prompt': {
        'cli': 'python scripts/render_calorie_trend.py --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「查热量历史」。\n\n我想看最近 N 天每日热量摄入趋势(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': [{
        'label': '查热量历史 30 天', 'cli': 'python scripts/render_calorie_trend.py --days 30', 'prompt': '请你加载技能 卡路里,执行唤醒词「查热量历史 30 天」。\n\n时间窗口固定最近 30 天。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '饮食记录',     'wake_word': '记喝水',     'desc': '记录饮水量',
            'main_prompt': {
        'cli': 'python scripts/calorie_tracker.py water <ml>', 'text': '请你加载技能 卡路里,执行唤醒词「记喝水」。\n\n我喝了一杯水,记录饮水量。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': ['饮水量 ml: '],
            'variants': []},
    {
            'category': '饮食记录',     'wake_word': '查今天喝水',     'desc': '今日饮水量(进度环 + 7 天 mini-chart)',
            'main_prompt': {
        'cli': 'python scripts/render_today_water.py', 'text': '请你加载技能 卡路里,执行唤醒词「查今天喝水」。\n\n我想看今天的饮水量。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '食品库',     'wake_word': '查热量',     'desc': '搜索食品营养成分',
            'main_prompt': {
        'cli': 'python scripts/render_food_search.py --query "<关键词>"', 'text': '请你加载技能 卡路里,执行唤醒词「查热量」。\n\n我想查某食物的热量/蛋白/碳水/脂肪(ticket 06 · ADR-0005)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': ['食物名(如 元气森林 冰红茶汽水 600ml): '],
            'variants': []},
    {
            'category': '食品库',     'wake_word': '存食品',     'desc': '添加食品营养成分到库',
            'main_prompt': {
        'cli': 'python scripts/calorie_tracker.py add-product <名称> <品牌> <热量> <蛋白质> <脂肪> <饱和脂肪> <碳水> <糖> <膳食纤维> <钠>', 'text': '请你加载技能 卡路里,执行唤醒词「存食品」。\n\n我要把新食品的营养数据存入食品库,告诉你必填字段(名称/品牌/热量/蛋白/脂肪/饱和脂肪/碳水/糖/膳食纤维/钠)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': ['食品名: ', '品牌: ', '热量(每 100g/ml): ', '蛋白质: ', '脂肪: ', '饱和脂肪: ', '碳水: ', '糖: ', '膳食纤维: ', '钠: '],
            'variants': []},
    {
            'category': '食品库',     'wake_word': '改食品',     'desc': '更新食品营养数据',
            'main_prompt': {
        'cli': 'python scripts/calorie_tracker.py update-product <id> [--calories] [--protein] ...', 'text': '请你加载技能 卡路里,执行唤醒词「改食品」。\n\n我想改某条食品库的某个字段。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': ['食品 id: ', '要改的字段(如 热量/蛋白质/...): ', '新值: '],
            'variants': []},
    {
            'category': '食品库',     'wake_word': '查食品库',     'desc': '列出全部食品营养成分',
            'main_prompt': {
        'cli': 'python scripts/render_food_library.py [--limit 200 | --all]', 'text': '请你加载技能 卡路里,执行唤醒词「查食品库」。\n\n我想列出全部食品库(ticket 07 · ADR-0005 · 默认 200 行)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '食品库',     'wake_word': '批量导入',     'desc': '批量录入/更新食品库',
            'main_prompt': {
        'cli': 'python scripts/batch_import.py import <file.jsonl>', 'text': '请你加载技能 卡路里,执行唤醒词「批量导入」。\n\n我有一个 JSONL 文件要批量录入食品库。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '食品库',     'wake_word': '校验批量',     'desc': '只校验 JSONL 不写入',
            'main_prompt': {
        'cli': 'python scripts/batch_import.py validate <file.jsonl>', 'text': '请你加载技能 卡路里,执行唤醒词「校验批量」。\n\n我要先校验我的 JSONL 文件能不能导入(不真正写入)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '体重',     'wake_word': '记体重',     'desc': '记录体重(身高自动从 user_profile 读)',
            'main_prompt': {
        'cli': 'python scripts/calorie_tracker.py weight <kg> [--note "<备注>"]', 'text': '请你加载技能 卡路里,执行唤醒词「记体重」。\n\n我刚称了体重,记录一下。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': ['体重 kg: '],
            'variants': []},
    {
            'category': '体重',     'wake_word': '改体重记录',     'desc': '修改历史体重记录',
            'main_prompt': {
        'cli': 'python scripts/calorie_tracker.py weight-update <id> [--weight <kg>] [--note <备注>]', 'text': '请你加载技能 卡路里,执行唤醒词「改体重记录」。\n\n我要改某条历史体重记录。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '体重',     'wake_word': '查体重历史',     'desc': '体重历史记录(mode=history)',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode history --days 30', 'text': '请你加载技能 卡路里,执行唤醒词「查体重历史」。\n\n我想看最近 N 天每天的体重列表(默认 30 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': [{
        'label': '查体重历史 上周', 'cli': 'python scripts/render_weight_history.py --mode history --days 7', 'prompt': '请你加载技能 卡路里,执行唤醒词「查体重历史 上周」。\n\n时间窗口固定最近 7 天。\n\n完成后给 1 句话总结,不需要过多文字解释。'}, {
        'label': '查体重历史 7/1 到 7/31', 'cli': 'python scripts/render_weight_history.py --mode history --start 2026-07-01 --end 2026-07-31', 'prompt': '请你加载技能 卡路里,执行唤醒词「查体重历史 7/1 到 7/31」。\n\n我要看整月体重列表。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '体重',     'wake_word': '查体重趋势',     'desc': '把体重画成折线图,看涨跌 + 起止差 + 异常点',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode trend --days 30', 'text': '请你加载技能 卡路里,执行唤醒词「查体重趋势」。\n\n我想看体重折线图,带起止对比和异常点高亮。默认最近 30 天,如果我说"上周"就是 7 天,"最近 90 天"就是 90 天,"7 月"就是当月整月。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
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
            'fill_hints': [],
            'variants': [{
        'label': '对比体重 7/1 到 7/31', 'cli': 'python scripts/render_weight_history.py --mode compare --start 2026-07-01 --end 2026-07-31', 'prompt': '请你加载技能 卡路里,执行唤醒词「对比体重 7/1 到 7/31」。\n\n我要对比 7 月整月内前后两段体重。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '体重',     'wake_word': '查体重波动',     'desc': '体重波动分析(标准差 + 异常点,mode=volatility)',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode volatility --days 30', 'text': '请你加载技能 卡路里,执行唤醒词「查体重波动」。\n\n我想看体重波动大小 + 异常点(默认 30 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '体重',
            'wake_word': '查体重波动 v2',
            'desc': '体重波动 dashboard v2(诊断 / 趋势 / 早警告 + Canvas + baseline toggle)',
            'main_prompt': {
                'cli': 'python scripts/render_weight_volatility_v2.py [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--baseline rolling|goal]',
                'text': '请你加载技能 卡路里,执行唤醒词「查体重波动 v2」。\n\n我想看体重波动 dashboard v2:3 张 KPI 卡(诊断 / 趋势 / 早警告)+ Canvas 主图(±σ 带 + 目标线)+ 异常列表。基线可在「近期常态」与「目标」之间切换。\n\n完成后给 1 句话总结,不需要过多文字解释。'
            },
            'fill_hints': [],
            'variants': [
                {'label': '查体重稳定性', 'prompt': '请你加载技能 卡路里,执行唤醒词「查体重稳定性」。\n\n体重波动 v2 的别名,含义相同。'},
                {'label': '查体重波动 v2 --text', 'cli': 'python scripts/render_weight_volatility_v2.py --text', 'prompt': '请你加载技能 卡路里,执行唤醒词「查体重波动 v2 --text」。\n\n纯文本模式输出(给 pipeline 用,无 HTML)。'},
            ]
    },
    {
            'category': '运动',     'wake_word': '记运动',     'desc': '记录运动消耗',
            'main_prompt': {
        'cli': 'python scripts/exercise_tracker.py add --date YYYY-MM-DD --type <类型> --calories <卡> [--minutes N] [--reps N]', 'text': '请你加载技能 卡路里,执行唤醒词「记运动」。\n\n我做了一项运动,记录运动类型 + 消耗热量 + 可选时长/次数。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': ['运动类型(如 跑步/力量/瑜伽): ', '消耗热量 卡(选填,可由 AI 估): '],
            'variants': []},
    {
            'category': '运动',     'wake_word': '改运动记录',     'desc': '更新运动记录',
            'main_prompt': {
        'cli': 'python scripts/exercise_tracker.py update --id <id> [--type] [--calories] [--minutes] ...', 'text': '请你加载技能 卡路里,执行唤醒词「改运动记录」。\n\n我要改某条运动记录。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '运动',     'wake_word': '查运动记录',     'desc': '查询运动记录(mode=records)',
            'main_prompt': {
        'cli': 'python scripts/render_exercise_summary.py --mode records --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「查运动记录」。\n\n我想看最近 N 天的运动明细(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': [{
        'label': '查运动记录 30 天', 'cli': 'python scripts/render_exercise_summary.py --mode records --days 30', 'prompt': '请你加载技能 卡路里,执行唤醒词「查运动记录 30 天」。\n\n时间窗口固定最近 30 天。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '运动',     'wake_word': '查运动汇总',     'desc': '运动汇总统计(mode=summary)',
            'main_prompt': {
        'cli': 'python scripts/render_exercise_summary.py --mode summary --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「查运动汇总」。\n\n我想看最近 N 天运动总消耗 + 总时长 + 活跃天数(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': [{
        'label': '查运动汇总 7 月', 'cli': 'python scripts/render_exercise_summary.py --mode summary --start 2026-07-01 --end 2026-07-31', 'prompt': '请你加载技能 卡路里,执行唤醒词「查运动汇总 7 月」。\n\n整月查询,7 月 1 号到 7 月底。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '运动',     'wake_word': '查运动类型',     'desc': '运动类型统计(力量/有氧/柔韧/日常)',
            'main_prompt': {
        'cli': 'python scripts/render_exercise_summary.py --mode stats --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「查运动类型」。\n\n我想看 4 类运动(力量/有氧/柔韧/日常)的占比(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '运动',     'wake_word': '查运动趋势',     'desc': '运动热量趋势(mode=trend,面积图)',
            'main_prompt': {
        'cli': 'python scripts/render_exercise_summary.py --mode trend --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「查运动趋势」。\n\n我想看每日运动消耗的面积图(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '健身计划',     'wake_word': '查健身计划', 'aliases': ['查询健身计划'],     'desc': '查看训练计划 HTML 页面(DB 数据驱动)',
            'main_prompt': {
        'cli': 'python scripts/render_workout_plan.py', 'text': '请你加载技能 卡路里,执行唤醒词「查健身计划」。\n\n我想看完整健身计划 + 今日复盘 section。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': [{
        'label': '查健身计划 --review', 'cli': 'python scripts/render_workout_plan.py --review', 'prompt': '请你加载技能 卡路里,执行唤醒词「查健身计划 --review」。\n\n我要看健身计划 + 今日复盘 section。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '健身计划',     'wake_word': '制定健身计划',     'desc': 'AI 采访式对话 → 校验 → 写入',
            'main_prompt': {
        'cli': 'AI 路由 → python scripts/plan_generator.py', 'text': '请你加载技能 卡路里,执行唤醒词「制定健身计划」。\n\n我要新设一份完整健身计划,从目标/经验/频率/部位几个维度跟我聊。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '健身计划',     'wake_word': '改健身计划',     'desc': 'AI 对话定位意图 → 改/增/删时段、调整周次',
            'main_prompt': {
        'cli': 'AI 路由 → python scripts/plan_generator.py', 'text': '请你加载技能 卡路里,执行唤醒词「改健身计划」。\n\n我要改既有计划(增删动作/调整周次/改时段等),先问你确认意图。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '健身计划',     'wake_word': '落地健身计划',     'desc': '把某天的健身计划执行一次:补计划 + 写心愿 + 推训记',
            'main_prompt': {
        'cli': 'python scripts/render_process_progress.py --input <json>', 'text': '请你加载技能 卡路里,执行唤醒词「落地健身计划」。\n\n我要把今天(某天)的计划真正执行一次,过程走完后给我看进度页。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '健身计划',     'wake_word': '卡路里同步',     'desc': '批量回填最近 3 天:每条 plan 都推训记 + 拉训记实际数据回写',
            'main_prompt': {
        'cli': 'python scripts/render_process_progress.py --input <json>', 'text': '请你加载技能 卡路里,执行唤醒词「卡路里同步」。\n\n最近 3 天的计划都还没真正落地,我要批量执行一次(推训记 + 拉训记回写),给我看总体进度页。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '健身计划',     'wake_word': '回写训记',     'desc': '拉训记数据回写 exercise_log(幂等)',
            'main_prompt': {
        'cli': 'python scripts/xunji_bridge.py backfill [--date <DATE>] [--days <N>]', 'text': '请你加载技能 卡路里,执行唤醒词「回写训记」。\n\n我要从训记拉取已完成的训练,写入运动记录。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': [{
        'label': '回写训记 最近 7 天', 'cli': 'python scripts/xunji_bridge.py backfill --days 7', 'prompt': '请你加载技能 卡路里,执行唤醒词「回写训记 最近 7 天」。\n\n时间窗口固定最近 7 天的训记实绩。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '健身计划',     'wake_word': '训记-覆盖X日的训练计划',     'desc': '用卡路里 plan 覆盖训记某天训练',
            'main_prompt': {
        'cli': 'python scripts/xunji_bridge.py overlay-plan --date <DATE>', 'text': '请你加载技能 卡路里,执行唤醒词「训记-覆盖X日的训练计划」。\n\n我要把卡路里的计划推到训记覆盖同一天的安排。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '健身计划',     'wake_word': '复盘训练',     'desc': '对指定时间段做 plan vs 实绩对比',
            'main_prompt': {
        'cli': 'python scripts/render_exercise_review_html.py --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「复盘训练」。\n\n我要对比健身计划 vs 实际完成情况(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': [{
        'label': '复盘训练 今天', 'cli': 'python scripts/render_exercise_review_html.py --start 2026-07-26 --end 2026-07-26', 'prompt': '请你加载技能 卡路里,执行唤醒词「复盘训练 今天」。\n\n我要看今天 vs 计划的对比。\n\n完成后给 1 句话总结,不需要过多文字解释。'}, {
        'label': '复盘训练 这周', 'cli': 'python scripts/render_exercise_review_html.py --days 7', 'prompt': '请你加载技能 卡路里,执行唤醒词「复盘训练 这周」。\n\n我要看本周 vs 计划的对比(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '健身计划',     'wake_word': '扫禁忌',     'desc': '检测 plan/DB 中禁忌动作(腰/膝/肩)',
            'main_prompt': {
        'cli': 'python scripts/render_contraindication.py', 'text': '请你加载技能 卡路里,执行唤醒词「扫禁忌」。\n\n我要扫出健身计划/数据库里可能伤腰/膝/肩的动作(默认全身位)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': [{
        'label': '扫禁忌 腰', 'cli': 'python scripts/render_contraindication.py --part 腰', 'prompt': '请你加载技能 卡路里,执行唤醒词「扫禁忌 腰」。\n\n只要扫腰部相关禁忌动作。\n\n完成后给 1 句话总结,不需要过多文字解释。'}, {
        'label': '扫禁忌 膝', 'cli': 'python scripts/render_contraindication.py --part 膝', 'prompt': '请你加载技能 卡路里,执行唤醒词「扫禁忌 膝」。\n\n只要扫膝部相关禁忌动作。\n\n完成后给 1 句话总结,不需要过多文字解释。'}, {
        'label': '扫禁忌 肩', 'cli': 'python scripts/render_contraindication.py --part 肩', 'prompt': '请你加载技能 卡路里,执行唤醒词「扫禁忌 肩」。\n\n只要扫肩部相关禁忌动作。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '健身计划',     'wake_word': '审计动作名',     'desc': '扫描 plan 里非训记官方动作名(push-plan 前必跑)',
            'main_prompt': {
        'cli': 'python scripts/audit_plan_names.py [--strict] [--fix-suggestions]', 'text': '请你加载技能 卡路里,执行唤醒词「审计动作名」。\n\n推送训记前我先确认 plan 里的动作名都能映射。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '分析',     'wake_word': '查热量趋势',     'desc': '热量摄入趋势',
            'main_prompt': {
        'cli': 'python scripts/render_calorie_trend.py --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「查热量趋势」。\n\n我想看每日热量摄入趋势(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': [{
        'label': '查热量趋势 上周', 'cli': 'python scripts/render_calorie_trend.py --days 7', 'prompt': '请你加载技能 卡路里,执行唤醒词「查热量趋势 上周」。\n\n时间窗口/参数语境:查热量趋势 上周。\n\n完成后给 1 句话总结,不需要过多文字解释。'}, {
        'label': '查热量趋势 7 月', 'cli': 'python scripts/render_calorie_trend.py --start 2026-07-01 --end 2026-07-31', 'prompt': '请你加载技能 卡路里,执行唤醒词「查热量趋势 7 月」。\n\n时间窗口/参数语境:查热量趋势 7 月。\n\n完成后给 1 句话总结,不需要过多文字解释。'}, {
        'label': '查热量趋势 最近 30 天', 'cli': 'python scripts/render_calorie_trend.py --days 30', 'prompt': '请你加载技能 卡路里,执行唤醒词「查热量趋势 最近 30 天」。\n\n时间窗口/参数语境:查热量趋势 最近 30 天。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '分析',     'wake_word': '查营养结构',     'desc': '营养素占比分析',
            'main_prompt': {
        'cli': 'python scripts/render_nutrition_ratio.py --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「查营养结构」。\n\n我想看蛋白/碳水/脂肪占比(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': [{
        'label': '查营养结构 7 月', 'cli': 'python scripts/render_nutrition_ratio.py --start 2026-07-01 --end 2026-07-31', 'prompt': '请你加载技能 卡路里,执行唤醒词「查营养结构 7 月」。\n\n时间窗口/参数语境:查营养结构 7 月。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '分析',     'wake_word': '查热量缺口',     'desc': '热量缺口分析(摄入 vs 运动 vs TDEE)',
            'main_prompt': {
        'cli': 'python scripts/render_calorie_deficit.py --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「查热量缺口」。\n\n我想看摄入 vs 运动消耗的缺口(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '分析',     'wake_word': '查食物排行',     'desc': '食物排行榜(默认高热量榜)',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「查食物排行」。\n\n我想看 TOP 食物热量榜(默认高热量,默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '分析',     'wake_word': '查高热量榜',     'desc': '热量炸弹 TOP5',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --days 7 --category high_calorie', 'text': '请你加载技能 卡路里,执行唤醒词「查高热量榜」。\n\n我想看热量最高的 5 个食物(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '分析',     'wake_word': '查低热量榜',     'desc': '低热量健康 TOP5',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --days 7 --category low_calorie', 'text': '请你加载技能 卡路里,执行唤醒词「查低热量榜」。\n\n我想看热量最低的 5 个健康食物(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '分析',     'wake_word': '查频繁吃榜',     'desc': '最常吃的食物 TOP5',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --days 7 --category frequent', 'text': '请你加载技能 卡路里,执行唤醒词「查频繁吃榜」。\n\n我想看吃最多次的食物(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '分析',     'wake_word': '查高碳水榜',     'desc': '高碳水食物 TOP5',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --days 7 --category high_carb', 'text': '请你加载技能 卡路里,执行唤醒词「查高碳水榜」。\n\n我想看碳水最高的 5 个食物(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '分析',     'wake_word': '查高蛋白榜',     'desc': '高蛋白食物 TOP5',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --days 7 --category high_protein', 'text': '请你加载技能 卡路里,执行唤醒词「查高蛋白榜」。\n\n我想看蛋白最高的 5 个食物(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '分析',     'wake_word': '查运动分布',     'desc': '运动类型分布',
            'main_prompt': {
        'cli': 'python scripts/render_exercise_distribution.py --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「查运动分布」。\n\n我想看 4 类运动(力量/有氧/柔韧/日常)的时间/消耗分布(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '分析',     'wake_word': '查运动贡献',     'desc': '运动对热量缺口的贡献占比',
            'main_prompt': {
        'cli': 'python scripts/render_exercise_distribution.py --days 7 --mode contribution', 'text': '请你加载技能 卡路里,执行唤醒词「查运动贡献」。\n\n我想看运动在热量缺口里的占比(默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '目标管理',     'wake_word': '定营养目标',     'desc': '设每日 4 项宏量营养目标',
            'main_prompt': {
        'cli': 'python scripts/render_goal_config.py --live', 'text': '请你加载技能 卡路里,执行唤醒词「定营养目标」。\n\n我想设每日 4 大宏量营养目标(热量/蛋白/碳水/脂肪)+ 饮水目标。若热量明显低于我的基础代谢(BMR),请提示我注意。完成后给 1 句话总结,不需要过多文字解释。\n\n我的目标数值(请按实际替换,不知道的可以空着):\n热量(卡):____\n蛋白(g):____\n碳水(g):____\n脂肪(g):____\n饮水(ml):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_set_nutrition', 'name': '定营养目标', 'subfunction': 'G1 定目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_config.html', 'data_source': 'python scripts/calorie_tracker.py goal', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「定营养目标」。\n\n我想设每日 4 大宏量营养目标(热量/蛋白/碳水/脂肪)+ 饮水目标。若热量明显低于我的基础代谢(BMR),请提示我注意。完成后给 1 句话总结,不需要过多文字解释。\n\n我的目标数值(请按实际替换,不知道的可以空着):\n热量(卡):____\n蛋白(g):____\n碳水(g):____\n脂肪(g):____\n饮水(ml):____',
            'user_intent': '设每日 4 项宏量营养目标', 'data_fields': ['calorie_goal', 'protein_goal', 'carbs_goal', 'fat_goal', 'water_goal'],
            'depends_on_external': False, 'order': 0},
    {
            'category': '目标管理',     'wake_word': '定营养目标(自动算)',     'desc': '按档案 + 策略自动算每日营养目标',
            'main_prompt': {
        'cli': 'python scripts/render_goal_config.py --recommend <减脂/维持/增肌>', 'text': '请你加载技能 卡路里,执行唤醒词「定营养目标(自动算)」。\n\n想根据我的档案(身高/体重/年龄/活动量)+ 目标方向自动算出 4 项营养目标。若我未提供方向或档案信息缺失,请先询问补齐;若我已明确表达,直接计算,必要时做几句信息确认即可。完成后给 1 句话总结,不需要过多文字解释。\n\n我的目标方向(减脂 / 维持 / 增肌):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_set_nutrition_auto', 'name': '定营养目标(自动算)', 'subfunction': 'G1 定目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_config.html', 'data_source': 'nutrition_goal.recommend_nutrition_goal', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「定营养目标(自动算)」。\n\n想根据我的档案(身高/体重/年龄/活动量)+ 目标方向自动算出 4 项营养目标。若我未提供方向或档案信息缺失,请先询问补齐;若我已明确表达,直接计算,必要时做几句信息确认即可。完成后给 1 句话总结,不需要过多文字解释。\n\n我的目标方向(减脂 / 维持 / 增肌):____',
            'user_intent': '按档案 + 策略自动算每日营养目标', 'data_fields': ['tdee', 'recommend', 'weekly_rate', 'macros_4', 'basis', 'plan_reasons'],
            'depends_on_external': False, 'order': 1},
    {
            'category': '目标管理',     'wake_word': '定体重目标',     'desc': '设定体重目标值与可选截止日期',
            'main_prompt': {
        'cli': 'python scripts/render_goal_config.py --live', 'text': '请你加载技能 卡路里,执行唤醒词「定体重目标」。\n\n我想设定体重目标(目标 kg + 可选截止日期)。请显示我的当前体重、目标值、差值(Δkg)和建议速率。完成后给 1 句话总结,不需要过多文字解释。\n\n我的体重目标(kg):____\n截止日期(选填):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_set_weight', 'name': '定体重目标', 'subfunction': 'G1 定目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_config.html', 'data_source': 'python scripts/calorie_tracker.py weight-goal', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「定体重目标」。\n\n我想设定体重目标(目标 kg + 可选截止日期)。请显示我的当前体重、目标值、差值(Δkg)和建议速率。完成后给 1 句话总结,不需要过多文字解释。\n\n我的体重目标(kg):____\n截止日期(选填):____',
            'user_intent': '设定体重目标值与可选截止日期', 'data_fields': ['current_weight', 'target_weight', 'deadline', 'delta_kg', 'suggested_rate'],
            'depends_on_external': False, 'order': 2},
    {
            'category': '目标管理',     'wake_word': '定体重目标(自动算截止)',     'desc': '按速率推算截止日期的体重目标',
            'main_prompt': {
        'cli': 'python scripts/render_goal_config.py --live', 'text': '请你加载技能 卡路里,执行唤醒词「定体重目标(自动算截止)」。\n\n我想设定体重目标(目标 kg + 期望每周减重速率),由你自动推算合理截止日期,并校验速率是否合理(不超安全范围)。请显示我的当前体重、目标值、推算截止日期和速率校验结果。完成后给 1 句话总结,不需要过多文字解释。\n\n我的体重目标(kg):____\n期望每周减重速率(kg/周):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_set_weight_auto_deadline', 'name': '定体重目标(自动算截止)', 'subfunction': 'G1 定目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_config.html', 'data_source': 'weight_goal.set_weight_goal', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「定体重目标(自动算截止)」。\n\n我想设定体重目标(目标 kg + 期望每周减重速率),由你自动推算合理截止日期,并校验速率是否合理(不超安全范围)。请显示我的当前体重、目标值、推算截止日期和速率校验结果。完成后给 1 句话总结,不需要过多文字解释。\n\n我的体重目标(kg):____\n期望每周减重速率(kg/周):____',
            'user_intent': '按速率推算截止日期的体重目标', 'data_fields': ['current_weight', 'target_weight', 'est_deadline', 'rate_check'],
            'depends_on_external': False, 'order': 3},
    {
            'category': '目标管理',     'wake_word': '定体重目标(含起始日)',     'desc': '完整 setup 体重目标含起始日',
            'main_prompt': {
        'cli': 'python scripts/render_goal_config.py --live', 'text': '请你加载技能 卡路里,执行唤醒词「定体重目标(含起始日)」。\n\n我想完整设定体重目标:目标 kg + 起始日 + 截止日 + 起点体重。请显示我的起始日、起点体重、当前体重、目标值、截止和差值。完成后给 1 句话总结,不需要过多文字解释。\n\n我的体重目标(kg):____\n起始日:____\n截止日期:____\n起点体重(kg):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_set_weight_with_start', 'name': '定体重目标(含起始日)', 'subfunction': 'G1 定目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_config.html', 'data_source': 'weight_goal.set_weight_goal', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「定体重目标(含起始日)」。\n\n我想完整设定体重目标:目标 kg + 起始日 + 截止日 + 起点体重。请显示我的起始日、起点体重、当前体重、目标值、截止和差值。完成后给 1 句话总结,不需要过多文字解释。\n\n我的体重目标(kg):____\n起始日:____\n截止日期:____\n起点体重(kg):____',
            'user_intent': '完整 setup 体重目标含起始日', 'data_fields': ['weight_goal', 'goal_deadline', 'start_date', 'start_weight'],
            'depends_on_external': False, 'order': 4},
    {
            'category': '目标管理',     'wake_word': '定饮水目标',     'desc': '设每日饮水目标',
            'main_prompt': {
        'cli': 'python scripts/render_goal_config.py --live', 'text': '请你加载技能 卡路里,执行唤醒词「定饮水目标」。\n\n我想设定每天饮水目标(ml)。完成后给 1 句话总结,不需要过多文字解释。\n\n我的饮水目标(ml):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_set_water', 'name': '定饮水目标', 'subfunction': 'G1 定目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_config.html', 'data_source': 'nutrition_goal.set_nutrition_goal', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「定饮水目标」。\n\n我想设定每天饮水目标(ml)。完成后给 1 句话总结,不需要过多文字解释。\n\n我的饮水目标(ml):____',
            'user_intent': '设每日饮水目标', 'data_fields': ['water_goal'],
            'depends_on_external': False, 'order': 5},
    {
            'category': '目标管理',     'wake_word': '定饮水目标(自动算)',     'desc': '按体重推算饮水目标推荐值',
            'main_prompt': {
        'cli': 'python scripts/render_goal_config.py --recommend <减脂/维持/增肌>', 'text': '请你加载技能 卡路里,执行唤醒词「定饮水目标(自动算)」。\n\n想按我的体重(ml/kg)自动推算饮水目标推荐值,并和旧目标对比。请显示计算依据、推荐值、旧值与新值对比。完成后给 1 句话总结,不需要过多文字解释。\n\n我的体重(kg,选填,默认取最新记录):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_set_water_auto', 'name': '定饮水目标(自动算)', 'subfunction': 'G1 定目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_config.html', 'data_source': 'nutrition_goal.recommend_water_goal', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「定饮水目标(自动算)」。\n\n想按我的体重(ml/kg)自动推算饮水目标推荐值,并和旧目标对比。请显示计算依据、推荐值、旧值与新值对比。完成后给 1 句话总结,不需要过多文字解释。\n\n我的体重(kg,选填,默认取最新记录):____',
            'user_intent': '按体重推算饮水目标推荐值', 'data_fields': ['weight_kg', 'season', 'recommended_water_ml'],
            'depends_on_external': False, 'order': 6},
    {
            'category': '目标管理',     'wake_word': '一键定全套目标',     'desc': '一键设定营养+体重+饮水全套目标',
            'main_prompt': {
        'cli': 'python scripts/render_goal_config.py --recommend <减脂/维持/增肌>', 'text': '请你加载技能 卡路里,执行唤醒词「一键定全套目标」。\n\n想一键设定 3 类目标(营养 + 体重 + 饮水),基于我的档案自动计算,先给我看每类目标值与依据说明,等我确认后再采纳。若我的档案(身高/年龄/活动量)未设置、无体重记录或信息缺失,请先询问补齐;若我已明确表达,直接计算,必要时做几句信息确认即可。完成后给 1 句话总结,不需要过多文字解释。\n\n我的目标方向(减脂 / 维持 / 增肌):____\n我的体重目标(kg,选填):____\n截止日期(选填):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_set_full_kit', 'name': '一键定全套目标', 'subfunction': 'G1 定目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_config.html', 'data_source': 'nutrition_goal.recommend_nutrition_goal', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「一键定全套目标」。\n\n想一键设定 3 类目标(营养 + 体重 + 饮水),基于我的档案自动计算,先给我看每类目标值与依据说明,等我确认后再采纳。若我的档案(身高/年龄/活动量)未设置、无体重记录或信息缺失,请先询问补齐;若我已明确表达,直接计算,必要时做几句信息确认即可。完成后给 1 句话总结,不需要过多文字解释。\n\n我的目标方向(减脂 / 维持 / 增肌):____\n我的体重目标(kg,选填):____\n截止日期(选填):____',
            'user_intent': '一键设定营养+体重+饮水全套目标', 'data_fields': ['calorie_goal', 'protein_goal', 'carbs_goal', 'fat_goal', 'water_goal', 'weight_goal'],
            'depends_on_external': False, 'order': 7},
    {
            'category': '目标管理',     'wake_word': '看今日目标',     'desc': '看今日营养 4 项 + 饮水共 5 项目标完成度（体重为累计目标，引导到看体重目标进度）',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode today', 'text': '请你加载技能 卡路里,执行唤醒词「看今日目标」。\n\n我想看今日 5 项目标完成度:热量/蛋白/碳水/脂肪/饮水的目标值、实际值与完成度百分比。体重是累计目标,若我想看,请引导我到「看体重目标进度」。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_today', 'name': '看今日目标', 'subfunction': 'G2 看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode today', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看今日目标」。\n\n我想看今日 5 项目标完成度:热量/蛋白/碳水/脂肪/饮水的目标值、实际值与完成度百分比。体重是累计目标,若我想看,请引导我到「看体重目标进度」。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看今日营养 4 项 + 饮水共 5 项目标完成度（体重为累计目标，引导到看体重目标进度）', 'data_fields': ['calorie_goal', 'protein_goal', 'carbs_goal', 'fat_goal', 'water_goal', 'actual', 'pct'],
            'depends_on_external': False, 'order': 8},
    {
            'category': '目标管理',     'wake_word': '看本周目标',     'desc': '看本周目标完成度汇总',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode week', 'text': '请你加载技能 卡路里,执行唤醒词「看本周目标」。\n\n我想看本周目标完成情况:日均实际 vs 日目标、周总量 vs 周目标(热量/蛋白/碳水/脂肪/饮水)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_week', 'name': '看本周目标', 'subfunction': 'G2 看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode week', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看本周目标」。\n\n我想看本周目标完成情况:日均实际 vs 日目标、周总量 vs 周目标(热量/蛋白/碳水/脂肪/饮水)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看本周目标完成度汇总', 'data_fields': ['daily_avg', 'daily_target', 'week_total', 'week_target'],
            'depends_on_external': False, 'order': 9},
    {
            'category': '目标管理',     'wake_word': '看营养目标进度',     'desc': '看 4 项营养目标进度',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode nutrition', 'text': '请你加载技能 卡路里,执行唤醒词「看营养目标进度」。\n\n我想看 4 项营养目标(热量/蛋白/碳水/脂肪)的完成进度条、完成度百分比和缺口(目标 - 实际)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_nutrition_progress', 'name': '看营养目标进度', 'subfunction': 'G2 看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode nutrition', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看营养目标进度」。\n\n我想看 4 项营养目标(热量/蛋白/碳水/脂肪)的完成进度条、完成度百分比和缺口(目标 - 实际)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看 4 项营养目标进度', 'data_fields': ['calorie_rate', 'protein_rate', 'carbs_rate', 'fat_rate', 'calorie_gap'],
            'depends_on_external': False, 'order': 10},
    {
            'category': '目标管理',     'wake_word': '看体重目标进度',     'desc': '看体重目标进度含预估达成',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode weight_progress', 'text': '请你加载技能 卡路里,执行唤醒词「看体重目标进度」。\n\n我想看体重目标进度:当前体重、目标值、差值(Δ)、完成百分比、预测达成日、剩余天数和建议速率。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_weight_progress', 'name': '看体重目标进度', 'subfunction': 'G2 看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/calorie_tracker.py weight-goal-progress', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重目标进度」。\n\n我想看体重目标进度:当前体重、目标值、差值(Δ)、完成百分比、预测达成日、剩余天数和建议速率。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看体重目标进度含预估达成', 'data_fields': ['current', 'target', 'delta', 'pct', 'predict_date', 'days_left', 'suggested_rate'],
            'depends_on_external': False, 'order': 11},
    {
            'category': '目标管理',     'wake_word': '看饮水目标进度',     'desc': '看饮水目标进度',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode water', 'text': '请你加载技能 卡路里,执行唤醒词「看饮水目标进度」。\n\n我想看今日饮水进度:累计饮水量、目标值、完成度百分比和剩余量(ml)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_water_progress', 'name': '看饮水目标进度', 'subfunction': 'G2 看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode water', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看饮水目标进度」。\n\n我想看今日饮水进度:累计饮水量、目标值、完成度百分比和剩余量(ml)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看饮水目标进度', 'data_fields': ['cumulative', 'target', 'pct', 'remaining_ml'],
            'depends_on_external': False, 'order': 12},
    {
            'category': '目标管理',     'wake_word': '看目标对比实际',     'desc': '看目标线 vs 实际线折线对比',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode vs_actual', 'text': '请你加载技能 卡路里,执行唤醒词「看目标对比实际」。\n\n我想看热量目标线 vs 实际摄入线的对比折线图 + 偏差分析,默认最近 30 天(可自定义时间窗口)。完成后给 1 句话总结,不需要过多文字解释。\n\n时间窗口(天,选填,默认 30):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_vs_actual', 'name': '看目标对比实际', 'subfunction': 'G2 看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode vs_actual', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看目标对比实际」。\n\n我想看热量目标线 vs 实际摄入线的对比折线图 + 偏差分析,默认最近 30 天(可自定义时间窗口)。完成后给 1 句话总结,不需要过多文字解释。\n\n时间窗口(天,选填,默认 30):____',
            'user_intent': '看目标线 vs 实际线折线对比', 'data_fields': ['daily_calorie_goal', 'daily_calorie_actual', 'deviation_pct'],
            'depends_on_external': False, 'order': 13},
    {
            'category': '目标管理',     'wake_word': '看目标完成度',     'desc': '查看全部目标完成度 + 缺口绝对值 + 总评分',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode completion', 'text': '请你加载技能 卡路里,执行唤醒词「看目标完成度」。\n\n我想看全部目标完成度汇总:5 项(热量/蛋白/碳水/脂肪/饮水)完成度百分比、各自缺口(目标 - 实际)和总评分。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_completion', 'name': '看目标完成度（含缺口）', 'subfunction': 'G2 看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode completion', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看目标完成度」。\n\n我想看全部目标完成度汇总:5 项(热量/蛋白/碳水/脂肪/饮水)完成度百分比、各自缺口(目标 - 实际)和总评分。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '查看全部目标完成度 + 缺口绝对值 + 总评分', 'data_fields': ['pct', 'gap', 'total_score'],
            'depends_on_external': False, 'order': 14},
    {
            'category': '目标管理',     'wake_word': '看即将到期的目标',     'desc': '看即将到期的目标列表',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode weight --expiring 14', 'text': '请你加载技能 卡路里,执行唤醒词「看即将到期的目标」。\n\n我想看即将到期的体重目标:目标值、截止日期、剩余天数、当前进度和紧迫度(默认 14 天内到期)。完成后给 1 句话总结,不需要过多文字解释。\n\n到期窗口(天,选填,默认 14):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_expiring', 'name': '看即将到期的目标', 'subfunction': 'G2 看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode weight --expiring 14', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看即将到期的目标」。\n\n我想看即将到期的体重目标:目标值、截止日期、剩余天数、当前进度和紧迫度(默认 14 天内到期)。完成后给 1 句话总结,不需要过多文字解释。\n\n到期窗口(天,选填,默认 14):____',
            'user_intent': '看即将到期的目标列表', 'data_fields': ['weight_goal', 'deadline', 'days_left', 'current_weight', 'completion_pct', 'urgency'],
            'depends_on_external': False, 'order': 15},
    {
            'category': '目标管理',     'wake_word': '看目标完成率(按周)',     'desc': '看本周营养目标每日完成率',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode nutrition --period week', 'text': '请你加载技能 卡路里,执行唤醒词「看目标完成率(按周)」。\n\n我想看本周(7 天)每日目标完成率柱状图 + 达标天数(达标带 80%-120%)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_completion_rate_week', 'name': '看目标完成率(按周)', 'subfunction': 'G2 看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode nutrition --period week', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看目标完成率(按周)」。\n\n我想看本周(7 天)每日目标完成率柱状图 + 达标天数(达标带 80%-120%)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看本周营养目标每日完成率', 'data_fields': ['week_daily_rate', 'week_complete_days', 'week_avg_rate'],
            'depends_on_external': False, 'order': 16},
    {
            'category': '目标管理',     'wake_word': '看目标完成率(按月)',     'desc': '看本月营养目标每日完成率',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode nutrition --period month', 'text': '请你加载技能 卡路里,执行唤醒词「看目标完成率(按月)」。\n\n我想看本月(30 天)每日目标完成率柱状图 + 达标天数(达标带 80%-120%)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_completion_rate_month', 'name': '看目标完成率(按月)', 'subfunction': 'G2 看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode nutrition --period month', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看目标完成率(按月)」。\n\n我想看本月(30 天)每日目标完成率柱状图 + 达标天数(达标带 80%-120%)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看本月营养目标每日完成率', 'data_fields': ['month_daily_rate', 'month_complete_days', 'month_avg_rate'],
            'depends_on_external': False, 'order': 17},
    {
            'category': '目标管理',     'wake_word': '改营养目标',     'desc': '改某项或全部营养目标',
            'main_prompt': {
        'cli': 'python scripts/render_goal_config.py --live', 'text': '请你加载技能 卡路里,执行唤醒词「改营养目标」。\n\n我想修改营养目标(热量/蛋白/碳水/脂肪/饮水),可同时改多项。请显示每项改前值与改后值,并预估修改后的影响(热量缺口/预算变化)。完成后给 1 句话总结,不需要过多文字解释。\n\n我要改的项(每行一项,不改的留空):\n热量(卡)新目标值:____\n蛋白(g)新目标值:____\n碳水(g)新目标值:____\n脂肪(g)新目标值:____\n饮水(ml)新目标值:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_modify_nutrition', 'name': '改营养目标', 'subfunction': 'G3 改目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_config.html', 'data_source': 'python scripts/calorie_tracker.py goal', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改营养目标」。\n\n我想修改营养目标(热量/蛋白/碳水/脂肪/饮水),可同时改多项。请显示每项改前值与改后值,并预估修改后的影响(热量缺口/预算变化)。完成后给 1 句话总结,不需要过多文字解释。\n\n我要改的项(每行一项,不改的留空):\n热量(卡)新目标值:____\n蛋白(g)新目标值:____\n碳水(g)新目标值:____\n脂肪(g)新目标值:____\n饮水(ml)新目标值:____',
            'user_intent': '改某项或全部营养目标', 'data_fields': ['old_calorie_goal', 'new_calorie_goal', 'old_protein_goal', 'new_protein_goal', 'old_water_goal', 'new_water_goal'],
            'depends_on_external': False, 'order': 18},
    {
            'category': '目标管理',     'wake_word': '改体重目标',     'desc': '改体重目标含截止日',
            'main_prompt': {
        'cli': 'python scripts/render_goal_config.py --live', 'text': '请你加载技能 卡路里,执行唤醒词「改体重目标」。\n\n我想修改体重目标值或截止日期。请显示改前值与改后值,并给出新的建议减重速率。完成后给 1 句话总结,不需要过多文字解释。\n\n我要改的项(每行一项,不改的留空):\n体重目标(kg):____\n截止日期:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_modify_weight', 'name': '改体重目标', 'subfunction': 'G3 改目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_config.html', 'data_source': 'python scripts/calorie_tracker.py weight-goal', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改体重目标」。\n\n我想修改体重目标值或截止日期。请显示改前值与改后值,并给出新的建议减重速率。完成后给 1 句话总结,不需要过多文字解释。\n\n我要改的项(每行一项,不改的留空):\n体重目标(kg):____\n截止日期:____',
            'user_intent': '改体重目标含截止日', 'data_fields': ['old_weight_goal', 'new_weight_goal', 'old_deadline', 'new_deadline'],
            'depends_on_external': False, 'order': 19},
    {
            'category': '目标管理',     'wake_word': '改饮水目标',     'desc': '单独改饮水目标',
            'main_prompt': {
        'cli': 'python scripts/render_goal_config.py --live', 'text': '请你加载技能 卡路里,执行唤醒词「改饮水目标」。\n\n我想单独修改饮水目标,其他营养目标保持不变。请显示改前值与改后值。完成后给 1 句话总结,不需要过多文字解释。\n\n饮水目标(ml):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_modify_water', 'name': '改饮水目标', 'subfunction': 'G3 改目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_config.html', 'data_source': 'nutrition_goal.update_water_goal', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改饮水目标」。\n\n我想单独修改饮水目标,其他营养目标保持不变。请显示改前值与改后值。完成后给 1 句话总结,不需要过多文字解释。\n\n饮水目标(ml):____',
            'user_intent': '单独改饮水目标', 'data_fields': ['old_water_goal', 'new_water_goal'],
            'depends_on_external': False, 'order': 20},
    {
            'category': '目标管理',     'wake_word': '暂停所有目标',     'desc': '临时暂停全部目标',
            'main_prompt': {
        'cli': 'python scripts/goal_manager.py pause', 'text': '请你加载技能 卡路里,执行唤醒词「暂停所有目标」。\n\n我想临时冻结全部目标(营养 + 体重 + 饮水),记录照常,仅目标暂停。请显示暂停状态、说明和恢复入口提示。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_pause_all', 'name': '暂停所有目标', 'subfunction': 'G3 改目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_config.html', 'data_source': 'goal_manager.pause_all_goals', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「暂停所有目标」。\n\n我想临时冻结全部目标(营养 + 体重 + 饮水),记录照常,仅目标暂停。请显示暂停状态、说明和恢复入口提示。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '临时暂停全部目标', 'data_fields': ['paused', 'note', 'restore_hint'],
            'depends_on_external': False, 'order': 21},
    {
            'category': '目标管理',     'wake_word': '重启所有目标',     'desc': '从暂停恢复全部目标',
            'main_prompt': {
        'cli': 'python scripts/goal_manager.py resume', 'text': '请你加载技能 卡路里,执行唤醒词「重启所有目标」。\n\n我想从暂停恢复全部目标(营养 + 体重 + 饮水)。请显示重启状态。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_resume_all', 'name': '重启所有目标', 'subfunction': 'G3 改目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_config.html', 'data_source': 'goal_manager.resume_all_goals', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「重启所有目标」。\n\n我想从暂停恢复全部目标(营养 + 体重 + 饮水)。请显示重启状态。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '从暂停恢复全部目标', 'data_fields': ['resume_state', 'resumed_at'],
            'depends_on_external': False, 'order': 22},
    {
            'category': '目标管理',     'wake_word': '看目标历史完成',     'desc': '看历史目标完成情况',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode history', 'text': '请你加载技能 卡路里,执行唤醒词「看目标历史完成」。\n\n我想看历史目标达成情况:每日达成列表(按时间排序)+ 完成/未完成天数统计(达标带 80%-120%)。完成后给 1 句话总结,不需要过多文字解释。\n\n回看天数(选填,默认 30):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_history_complete', 'name': '看目标历史完成', 'subfunction': '新增', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'goal_history.list_completed_goals', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看目标历史完成」。\n\n我想看历史目标达成情况:每日达成列表(按时间排序)+ 完成/未完成天数统计(达标带 80%-120%)。完成后给 1 句话总结,不需要过多文字解释。\n\n回看天数(选填,默认 30):____',
            'user_intent': '看历史目标完成情况', 'data_fields': ['goal_history', 'completed_count', 'incomplete_count'],
            'depends_on_external': False, 'order': 23},
    {
            'category': '目标管理',     'wake_word': '看目标预测达成',     'desc': '预测目标达成日 + 置信度（体重部分复用对比体重 B1 的预测）',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode predict', 'text': '请你加载技能 卡路里,执行唤醒词「看目标预测达成」。\n\n我想看按当前趋势预测的目标达成日 + 置信度(体重部分复用对比体重的预测逻辑)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_predict', 'name': '看目标预测达成', 'subfunction': '新增', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode predict', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看目标预测达成」。\n\n我想看按当前趋势预测的目标达成日 + 置信度(体重部分复用对比体重的预测逻辑)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '预测目标达成日 + 置信度（体重部分复用对比体重 B1 的预测）', 'data_fields': ['predict_date', 'confidence'],
            'depends_on_external': False, 'order': 24},
    {
            'category': '综合',     'wake_word': '查健康报告',     'desc': '四维度综合健康仪表盘',
            'main_prompt': {
        'cli': 'python scripts/render_health_dashboard.py --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「查健康报告」。\n\n我要看 4 维健康仪表盘(热量/营养/运动/体重综合,默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': [{
        'label': '查健康报告 本月', 'cli': 'python scripts/render_health_dashboard.py --start 2026-07-01 --end 2026-07-26', 'prompt': '请你加载技能 卡路里,执行唤醒词「查健康报告 本月」。\n\n我要看本月 1 号到今天的健康报告。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '综合',     'wake_word': '查卡路里数据',     'desc': '数据健康检查(lint_health)',
            'main_prompt': {
        'cli': 'python scripts/render_lint_health.py', 'text': '请你加载技能 卡路里,执行唤醒词「查卡路里数据」。\n\n我要检查数据库的健康性。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '复盘',     'wake_word': '复盘',     'desc': '生成 8 维度复盘报告 HTML + 可选飞书发送',
            'main_prompt': {
        'cli': 'python scripts/render_review.py', 'text': '请你加载技能 卡路里,执行唤醒词「复盘」。\n\n我要看一份复盘报告,默认最近 7 天,带 8 个维度(热量/营养/运动/体重/饮水/缺口/目标/周对比)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '复盘',     'wake_word': '今日复盘', 'aliases': ['复盘今日', '日复盘'],     'desc': '当日复盘',
            'main_prompt': {
        'cli': 'python scripts/render_review.py --type day', 'text': '请你加载技能 卡路里,执行唤醒词「今日复盘」。\n\n我要看当日复盘。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '复盘',     'wake_word': '本周复盘', 'aliases': ['复盘本周', '周复盘'],     'desc': '本周复盘(本周一-今天)',
            'main_prompt': {
        'cli': 'python scripts/render_review.py --type week', 'text': '请你加载技能 卡路里,执行唤醒词「本周复盘」。\n\n我要看本周一-今天的复盘。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '复盘',     'wake_word': '本月复盘', 'aliases': ['复盘本月', '月复盘'],     'desc': '本月复盘(本月 1 号-今天)',
            'main_prompt': {
        'cli': 'python scripts/render_review.py --type month', 'text': '请你加载技能 卡路里,执行唤醒词「本月复盘」。\n\n我要看本月 1 号-今天的复盘。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '复盘',     'wake_word': '本年复盘', 'aliases': ['复盘本年', '年复盘'],     'desc': '本年复盘(今年 1/1-今天)',
            'main_prompt': {
        'cli': 'python scripts/render_review.py --type year', 'text': '请你加载技能 卡路里,执行唤醒词「本年复盘」。\n\n我要看今年 1/1 - 今天的复盘。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '复盘',     'wake_word': '复盘日期范围',     'desc': '自定义日期范围复盘',
            'main_prompt': {
        'cli': 'python scripts/render_review.py --range 2026-07-01:2026-07-14', 'text': '请你加载技能 卡路里,执行唤醒词「复盘日期范围」。\n\n我要看任意起止日期的复盘。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '复盘',     'wake_word': '开启定时复盘',     'desc': '启动 cron(默认 23:00 / 过去 7 天)',
            'main_prompt': {
        'cli': 'mavis cron create ...', 'text': '请你加载技能 卡路里,执行唤醒词「开启定时复盘」。\n\n我要设每天自动跑复盘(默认 23:00 跑过去 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '复盘',     'wake_word': '关闭定时复盘',     'desc': '删除 cron',
            'main_prompt': {
        'cli': 'mavis cron delete ...', 'text': '请你加载技能 卡路里,执行唤醒词「关闭定时复盘」。\n\n我要关掉每天自动复盘。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '复盘',     'wake_word': '查定时复盘',     'desc': '查看当前定时复盘配置',
            'main_prompt': {
        'cli': 'mavis cron list', 'text': '请你加载技能 卡路里,执行唤醒词「查定时复盘」。\n\n我想看当前定时复盘配置。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '身体成分',     'wake_word': '记体脂',     'desc': '皮褶钳测 7 点(Jackson-Pollock 自动算体脂率)',
            'main_prompt': {
        'cli': 'python scripts/body_composition.py add ... → HTML:body_composition_wizard.html', 'text': '请你加载技能 卡路里,执行唤醒词「记体脂」。\n\n我用皮褶钳测了 7 点(胸/腹/大腿/三头/肩胛下/髂上/腋中 mm),给我算体脂率。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': ['胸 mm: ', '腹 mm: ', '大腿 mm: ', '三头 mm: ', '肩胛下 mm: ', '髂上 mm: ', '腋中 mm: '],
            'variants': []},
    {
            'category': '身体成分',     'wake_word': '查体脂',     'desc': '历史体脂记录',
            'main_prompt': {
        'cli': 'python scripts/render_body_composition_wizard.py → list 视图', 'text': '请你加载技能 卡路里,执行唤醒词「查体脂」。\n\n我想看历史体脂测量记录。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '身体成分',     'wake_word': '查体脂趋势',     'desc': '体脂率时间线',
            'main_prompt': {
        'cli': 'python scripts/body_composition.py trend', 'text': '请你加载技能 卡路里,执行唤醒词「查体脂趋势」。\n\n我想看体脂率走势时间线。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '身体成分',     'wake_word': '删体脂',     'desc': '软删除体脂记录',
            'main_prompt': {
        'cli': 'python scripts/body_composition.py delete <id> → HTML:crud_receipt.html', 'text': '请你加载技能 卡路里,执行唤醒词「删体脂」。\n\n我要删某条体脂记录。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '围度',     'wake_word': '记围度',     'desc': '13 部位围度入库:上身 5 + 下身 4 + 手臂 4,cm 单位',
            'main_prompt': {
        'cli': 'python scripts/render_body_measurements_wizard.py [--chest-cm ...]', 'text': '请你加载技能 卡路里,执行唤醒词「记围度」。\n\n我想录入 13 部位围度(胸/腰/臀/大腿/小腿/手臂/前臂/颈/肩,左+右)。如果我已经给了具体数字就用它们,如果没给就让我看到空 form。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': ['胸围 cm: ', '腰围 cm: ', '臀围 cm: ', '其他部位选填(大腿/小腿/手臂/前臂/颈/肩,左+右) cm: '],
            'variants': []},
    {
            'category': '围度',     'wake_word': '查围度',     'desc': '历史围度记录',
            'main_prompt': {
        'cli': 'python scripts/render_body_measurements_wizard.py → list 视图', 'text': '请你加载技能 卡路里,执行唤醒词「查围度」。\n\n我想看历史围度测量记录。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '围度',     'wake_word': '查围度趋势',     'desc': '单围度时间线',
            'main_prompt': {
        'cli': 'python scripts/body_measurements.py trend --metric <col>', 'text': '请你加载技能 卡路里,执行唤醒词「查围度趋势」。\n\n我想看某一部位围度走势时间线。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '围度',     'wake_word': '删围度',     'desc': '软删除围度记录',
            'main_prompt': {
        'cli': 'python scripts/body_measurements.py delete <id> → HTML:crud_receipt.html', 'text': '请你加载技能 卡路里,执行唤醒词「删围度」。\n\n我要删某条围度记录。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '身材照片',     'wake_word': '记身材照',     'desc': '记录身材照片',
            'main_prompt': {
        'cli': 'python scripts/body_photo_log_wizard.py → 用户填路径 → add', 'text': '请你加载技能 卡路里,执行唤醒词「记身材照」。\n\n我要给身材照加一条入库记录(日期/时间/路径/标签/备注)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': ['照片路径: ', '标签(如 正面/侧面/背部): '],
            'variants': []},
    {
            'category': '身材照片',     'wake_word': '查身材照',     'desc': '查看照片历史(浏览 + 选 + 裁剪 + 调细节)',
            'main_prompt': {
        'cli': 'python scripts/render_body_photo_gif_planner.py --tag 正面', 'text': '请你加载技能 卡路里,执行唤醒词「查身材照」。\n\n我要浏览身材照(可筛选 + 裁剪 + 生成 GIF)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '身材照片',     'wake_word': '生成身材照GIF',     'desc': '生成身材变化 GIF',
            'main_prompt': {
        'cli': 'python scripts/render_body_photo_gif_planner.py --tag X --photo-id ...', 'text': '请你加载技能 卡路里,执行唤醒词「生成身材照GIF」。\n\n我要把多张身材照生成变化 GIF。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '身材照片',     'wake_word': '删身材照',     'desc': '删除身材照片',
            'main_prompt': {
        'cli': 'python scripts/body_photo_tracker.py delete <id>', 'text': '请你加载技能 卡路里,执行唤醒词「删身材照」。\n\n我要删某张照片。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '身材照片',     'wake_word': '改照片标签',     'desc': '修改照片标签',
            'main_prompt': {
        'cli': 'python scripts/body_photo_tracker.py tag <id> <new_tag>', 'text': '请你加载技能 卡路里,执行唤醒词「改照片标签」。\n\n我要改某张照片的 tag。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': []},
    {
            'category': '综合',     'wake_word': '设置档案',     'desc': '设置 user_profile(年龄/性别/身高/备注)',
            'main_prompt': {
        'cli': 'python scripts/render_profile_setup.py → 用户填 → 复制 prompt → set', 'text': '请你加载技能 卡路里,执行唤醒词「设置档案」。\n\n我要设身高/年龄/性别(影响 BMI/TDEE/营养目标)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': [{
        'label': '设置档案 (直接传参)', 'cli': 'python scripts/calorie_tracker.py profile set <age> <gender> --height <cm>', 'prompt': '请你加载技能 卡路里,执行唤醒词「设置档案 (直接传参)」。\n\n我已经给了完整参数,你直接调 set。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '综合',     'wake_word': '查档案',     'desc': '查看 user_profile + 最新体重',
            'main_prompt': {
        'cli': 'python scripts/render_crud_view.py --entity profile', 'text': '请你加载技能 卡路里,执行唤醒词「查档案」。\n\n我要看自己的档案 + 最新体重。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
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
