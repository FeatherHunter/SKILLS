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
    ('🧬', '身体细节',      'body_detail'),
    ('📸', '身材照片',      'body_photo'),
    ('🎯', '目标管理',      'goal'),
    ('🛠', '基础信息',      'profile'),
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
            'category': '饮食',     'wake_word': '记一餐',     'desc': '记一餐',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-diet-add <食物> <热量> <蛋白> [碳水] [脂肪] [克数] [备注] --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「记一餐」。\n\n我刚吃了一顿,帮我记录。如果我没说全克数或营养,问我补齐。记录后给我看:食物名/克数/热量/蛋白/碳水/脂肪 + 餐别 + 时间 + 今日累计 vs 目标。完成后给 1 句话总结,不需要过多文字解释。\n\n食物名称:____\n克数(选填,默认按食品库每 100g):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_add_meal', 'name': '记一餐', 'subfunction': '记饮食', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-diet-add <食物> <热量> <蛋白> [碳水] [脂肪] [克数] [备注] --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「记一餐」。\n\n我刚吃了一顿,帮我记录。如果我没说全克数或营养,问我补齐。记录后给我看:食物名/克数/热量/蛋白/碳水/脂肪 + 餐别 + 时间 + 今日累计 vs 目标。完成后给 1 句话总结,不需要过多文字解释。\n\n食物名称:____\n克数(选填,默认按食品库每 100g):____',
            'user_intent': '记录刚吃的一餐食物与营养', 'data_fields': ["food_name", "grams", "calories", "protein", "carbs", "fat", "meal", "time"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '饮食',     'wake_word': '记一餐（含备注）',     'desc': '记一餐（含备注）',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-diet-add <食物> <热量> <蛋白> [碳水] [脂肪] [克数] [备注] --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「记一餐（含备注）」。\n\n我刚吃了一顿,要连同备注一起记录(如「加了辣酱」「食堂打的」)。如果我没说全克数或营养,问我补齐。记录后给我看:食物名/克数/热量/蛋白/碳水/脂肪 + 餐别 + 时间 + 备注。完成后给 1 句话总结,不需要过多文字解释。\n\n食物名称:____\n克数(选填,默认按食品库每 100g):____\n备注:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_add_meal_note', 'name': '记一餐（含备注）', 'subfunction': '记饮食', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-diet-add <食物> <热量> <蛋白> [碳水] [脂肪] [克数] [备注] --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「记一餐（含备注）」。\n\n我刚吃了一顿,要连同备注一起记录(如「加了辣酱」「食堂打的」)。如果我没说全克数或营养,问我补齐。记录后给我看:食物名/克数/热量/蛋白/碳水/脂肪 + 餐别 + 时间 + 备注。完成后给 1 句话总结,不需要过多文字解释。\n\n食物名称:____\n克数(选填,默认按食品库每 100g):____\n备注:____',
            'user_intent': '记录一餐并附上备注', 'data_fields': ["food_name", "grams", "calories", "protein", "carbs", "fat", "meal", "time", "note"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '饮食',     'wake_word': '补记饮食',     'desc': '补记饮食',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-diet-add <食物> <热量> <蛋白> [碳水] [脂肪] [克数] [备注] --date <日期> --time <时间> --meal <餐别> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「补记饮食」。\n\n我要补录之前某天的饮食(不是现在吃的)。如果我没说全克数或营养,问我补齐。记录后给我看:食物/克数/营养 + 补录日期 + 补录标识,若当天已有相同食物请提示我冲突。完成后给 1 句话总结,不需要过多文字解释。\n\n食物名称:____\n日期(YYYY-MM-DD):____\n时间(选填):____\n克数(选填,默认按食品库每 100g):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_backfill', 'name': '补记饮食', 'subfunction': '记饮食', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-diet-add <食物> <热量> <蛋白> [碳水] [脂肪] [克数] [备注] --date <日期> --time <时间> --meal <餐别> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「补记饮食」。\n\n我要补录之前某天的饮食(不是现在吃的)。如果我没说全克数或营养,问我补齐。记录后给我看:食物/克数/营养 + 补录日期 + 补录标识,若当天已有相同食物请提示我冲突。完成后给 1 句话总结,不需要过多文字解释。\n\n食物名称:____\n日期(YYYY-MM-DD):____\n时间(选填):____\n克数(选填,默认按食品库每 100g):____',
            'user_intent': '补录之前某天的饮食', 'data_fields': ["food_name", "grams", "calories", "protein", "date", "time", "meal"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '饮食',     'wake_word': '批量补记饮食',     'desc': '批量补记饮食',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-diet-batch --input <meals.json> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「批量补记饮食」。\n\n我要一次补录多餐(不同日期/不同餐别),一行一餐地说。写之前先给我看整理好的清单,确认无误再写入。完成后给我看:写入条数/跳过条数/失败条数 + 失败明细。完成后给 1 句话总结,不需要过多文字解释。\n\n每行一餐(日期/时间/食物/克数/营养,换行分隔):\n____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_backfill_batch', 'name': '批量补记饮食', 'subfunction': '记饮食', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-diet-batch --input <meals.json> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「批量补记饮食」。\n\n我要一次补录多餐(不同日期/不同餐别),一行一餐地说。写之前先给我看整理好的清单,确认无误再写入。完成后给我看:写入条数/跳过条数/失败条数 + 失败明细。完成后给 1 句话总结,不需要过多文字解释。\n\n每行一餐(日期/时间/食物/克数/营养,换行分隔):\n____',
            'user_intent': '一次批量补录多餐饮食', 'data_fields': ["date", "time", "food_name", "grams", "calories", "protein", "carbs", "fat"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '饮食',     'wake_word': '扫描营养表',     'desc': '扫描营养表',
            'main_prompt': {
        'cli': 'mmx vision describe <图片> → python scripts/render_nutrition_label.py --ai-json <json> → 确认后 python scripts/calorie_tracker.py add', 'text': '请你加载技能 卡路里,执行唤醒词「扫描营养表」。\n\n我拍了食物包装的营养成分表图片,请你识别出热量/蛋白/碳水/脂肪等字段,给我看识别结果(照片 + 识别出的营养),我确认后写进饮食记录。识别不确定的地方标注一下。完成后给 1 句话总结,不需要过多文字解释。\n\n营养表图片路径:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_scan_label', 'name': '扫描营养表', 'subfunction': '记饮食', 'output_type': 'process',
            'html_template': 'templates/nutrition_label_wizard.html', 'data_source': 'mmx vision describe <图片> → python scripts/render_nutrition_label.py --ai-json <json> → 确认后 python scripts/calorie_tracker.py add', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「扫描营养表」。\n\n我拍了食物包装的营养成分表图片,请你识别出热量/蛋白/碳水/脂肪等字段,给我看识别结果(照片 + 识别出的营养),我确认后写进饮食记录。识别不确定的地方标注一下。完成后给 1 句话总结,不需要过多文字解释。\n\n营养表图片路径:____',
            'user_intent': '拍照识别营养成分表并记录', 'data_fields': ["calories", "protein", "carbs", "fat", "sugar", "sodium", "fiber"],
            'depends_on_external': False, 'order': 4},
    {
            'category': '饮食',     'wake_word': '扫描营养表（指定日期）',     'desc': '扫描营养表（指定日期）',
            'main_prompt': {
        'cli': 'mmx vision describe <图片> → python scripts/render_nutrition_label.py --ai-json <json> --date <日期> → 确认后 python scripts/calorie_tracker.py add --date <日期>', 'text': '请你加载技能 卡路里,执行唤醒词「扫描营养表（指定日期）」。\n\n我拍了食物包装的营养成分表图片,要补录到指定日期。请你识别出热量/蛋白/碳水/脂肪等字段,给我看识别结果(照片 + 识别出的营养 + 指定日期),我确认后按该日期写进饮食记录。完成后给 1 句话总结,不需要过多文字解释。\n\n营养表图片路径:____\n日期(YYYY-MM-DD):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_scan_label_date', 'name': '扫描营养表（指定日期）', 'subfunction': '记饮食', 'output_type': 'process',
            'html_template': 'templates/nutrition_label_wizard.html', 'data_source': 'mmx vision describe <图片> → python scripts/render_nutrition_label.py --ai-json <json> --date <日期> → 确认后 python scripts/calorie_tracker.py add --date <日期>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「扫描营养表（指定日期）」。\n\n我拍了食物包装的营养成分表图片,要补录到指定日期。请你识别出热量/蛋白/碳水/脂肪等字段,给我看识别结果(照片 + 识别出的营养 + 指定日期),我确认后按该日期写进饮食记录。完成后给 1 句话总结,不需要过多文字解释。\n\n营养表图片路径:____\n日期(YYYY-MM-DD):____',
            'user_intent': '拍照识别营养表并补录到指定日期', 'data_fields': ["calories", "protein", "carbs", "fat", "date"],
            'depends_on_external': False, 'order': 5},
    {
            'category': '饮食',     'wake_word': '记喝水',     'desc': '记喝水',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-water-add <ml> [--date <日期>] --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「记喝水」。\n\n我喝了水,帮我记录。如果我说「喝了几杯」,请按一杯约 250ml 折算成总量;如果我只说了杯子大小,先问我确认。记录后给我看:本次 ml + 今日累计/目标 + 距目标进度。完成后给 1 句话总结,不需要过多文字解释。\n\n喝水量(ml,或「几杯」):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_log_water', 'name': '记喝水', 'subfunction': '记饮食', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-water-add <ml> [--date <日期>] --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「记喝水」。\n\n我喝了水,帮我记录。如果我说「喝了几杯」,请按一杯约 250ml 折算成总量;如果我只说了杯子大小,先问我确认。记录后给我看:本次 ml + 今日累计/目标 + 距目标进度。完成后给 1 句话总结,不需要过多文字解释。\n\n喝水量(ml,或「几杯」):____',
            'user_intent': '记录一次饮水(含多杯解析)', 'data_fields': ["ml", "today_total_ml", "water_goal_ml", "remaining_ml"],
            'depends_on_external': False, 'order': 6},
    {
            'category': '饮食',     'wake_word': '复制昨日饮食',     'desc': '复制昨日饮食',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-diet-copy [--from <来源日期>] [--to <目标日期>] --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「复制昨日饮食」。\n\n我要把昨天(或指定某天)吃的东西原样复制到今天(或指定某天),省得重新记。复制完成后给我看:复制条数/跳过条数(同时间同食物已存在则跳过)。完成后给 1 句话总结,不需要过多文字解释。\n\n来源日期(选填,默认昨天):____\n目标日期(选填,默认今天):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_copy_yesterday', 'name': '复制昨日饮食', 'subfunction': '记饮食', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-diet-copy [--from <来源日期>] [--to <目标日期>] --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「复制昨日饮食」。\n\n我要把昨天(或指定某天)吃的东西原样复制到今天(或指定某天),省得重新记。复制完成后给我看:复制条数/跳过条数(同时间同食物已存在则跳过)。完成后给 1 句话总结,不需要过多文字解释。\n\n来源日期(选填,默认昨天):____\n目标日期(选填,默认今天):____',
            'user_intent': '一键把昨天的饮食复制到今天', 'data_fields': ["copied", "skipped", "from_date", "to_date"],
            'depends_on_external': False, 'order': 7},
    {
            'category': '饮食',     'wake_word': '改饮食记录',     'desc': '改饮食记录',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-diet-update <id> [--food <食物>] [--grams <克数>] [--calories <热量>] [--protein <蛋白>] [--carbs <碳水>] [--fat <脂肪>] [--date <日期>] [--time <时间>] [--note <备注>] --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「改饮食记录」。\n\n我要改某条饮食记录。如果我没说清是哪条,请先列出最近的记录让我选。改之前先给我看这条记录的当前内容,改完后给我看:改前/改后 + 改动字段。完成后给 1 句话总结,不需要过多文字解释。\n\n要改的记录(如「最近一条」或日期+食物):____\n要改的字段(食物/克数/热量/蛋白/碳水/脂肪/日期/时间/备注):____\n新值:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_update_record', 'name': '改饮食记录', 'subfunction': '改饮食', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-diet-update <id> [--food <食物>] [--grams <克数>] [--calories <热量>] [--protein <蛋白>] [--carbs <碳水>] [--fat <脂肪>] [--date <日期>] [--time <时间>] [--note <备注>] --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改饮食记录」。\n\n我要改某条饮食记录。如果我没说清是哪条,请先列出最近的记录让我选。改之前先给我看这条记录的当前内容,改完后给我看:改前/改后 + 改动字段。完成后给 1 句话总结,不需要过多文字解释。\n\n要改的记录(如「最近一条」或日期+食物):____\n要改的字段(食物/克数/热量/蛋白/碳水/脂肪/日期/时间/备注):____\n新值:____',
            'user_intent': '修改某条饮食记录的字段', 'data_fields': ["food_name", "grams", "calories", "protein", "carbs", "fat", "note"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '饮食',     'wake_word': '改某日饮食',     'desc': '改某日饮食',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-diet-update-date <日期> [--字段 新值 ...] --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「改某日饮食」。\n\n我要改某一天的全部饮食记录(如那天的时间/克数/备注都记错了)。改之前先告诉我那天有几条记录,改完后给我看:命中条数/改前/改后。完成后给 1 句话总结,不需要过多文字解释。\n\n日期(YYYY-MM-DD):____\n要改的字段与新值(如 备注=修正):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_update_by_date', 'name': '改某日饮食', 'subfunction': '改饮食', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-diet-update-date <日期> [--字段 新值 ...] --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改某日饮食」。\n\n我要改某一天的全部饮食记录(如那天的时间/克数/备注都记错了)。改之前先告诉我那天有几条记录,改完后给我看:命中条数/改前/改后。完成后给 1 句话总结,不需要过多文字解释。\n\n日期(YYYY-MM-DD):____\n要改的字段与新值(如 备注=修正):____',
            'user_intent': '按日期批量修改当天饮食记录', 'data_fields': ["date", "matched", "updated", "changed_fields"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '饮食',     'wake_word': '删饮食记录',     'desc': '删饮食记录',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-diet-delete <id> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「删饮食记录」。\n\n我要删一条饮食记录。如果我没说清是哪条,请先列出最近的几条让我选。删除前先给我看这条记录的内容,确认无误再删,最后给我确认回执。完成后给 1 句话总结,不需要过多文字解释。\n\n要删的记录(选填,如「最近一条」或日期):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_delete_record', 'name': '删饮食记录', 'subfunction': '改饮食', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-diet-delete <id> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「删饮食记录」。\n\n我要删一条饮食记录。如果我没说清是哪条,请先列出最近的几条让我选。删除前先给我看这条记录的内容,确认无误再删,最后给我确认回执。完成后给 1 句话总结,不需要过多文字解释。\n\n要删的记录(选填,如「最近一条」或日期):____',
            'user_intent': '删除一条饮食记录', 'data_fields': ["id", "food_name", "calories", "date", "snapshot"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '饮食',     'wake_word': '删一餐',     'desc': '删一餐',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-diet-delete-meal <日期> <餐别> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「删一餐」。\n\n我要删某天某一餐的全部记录(如删掉今天的早餐)。如果我没说日期默认今天。删除前告诉我这一餐有几条,确认后删除,给我看:餐别 + 删除条数。完成后给 1 句话总结,不需要过多文字解释。\n\n餐别(早餐/午餐/下午茶/晚餐/夜宵/加餐):____\n日期(选填,默认今天):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_delete_by_meal', 'name': '删一餐', 'subfunction': '改饮食', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-diet-delete-meal <日期> <餐别> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「删一餐」。\n\n我要删某天某一餐的全部记录(如删掉今天的早餐)。如果我没说日期默认今天。删除前告诉我这一餐有几条,确认后删除,给我看:餐别 + 删除条数。完成后给 1 句话总结,不需要过多文字解释。\n\n餐别(早餐/午餐/下午茶/晚餐/夜宵/加餐):____\n日期(选填,默认今天):____',
            'user_intent': '按餐别删除某天的一餐记录', 'data_fields': ["date", "meal", "deleted"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '饮食',     'wake_word': '删某日饮食',     'desc': '删某日饮食',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-diet-delete-date <日期> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「删某日饮食」。\n\n我要清空某一天的整日饮食记录。删除前告诉我那天有几条,确认后删除,给我看:日期 + 删除条数。完成后给 1 句话总结,不需要过多文字解释。\n\n日期(YYYY-MM-DD):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_delete_by_date', 'name': '删某日饮食', 'subfunction': '改饮食', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-diet-delete-date <日期> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「删某日饮食」。\n\n我要清空某一天的整日饮食记录。删除前告诉我那天有几条,确认后删除,给我看:日期 + 删除条数。完成后给 1 句话总结,不需要过多文字解释。\n\n日期(YYYY-MM-DD):____',
            'user_intent': '清空某一天的整日饮食记录', 'data_fields': ["date", "deleted"],
            'depends_on_external': False, 'order': 4},
    {
            'category': '饮食',     'wake_word': '批量删饮食',     'desc': '批量删饮食',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-diet-delete-range <开始> <结束> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「批量删饮食」。\n\n我要按日期范围批量删除饮食记录。删除前告诉我这个范围有几条,确认后删除,给我看:时间范围 + 删除条数 + 确认回执。完成后给 1 句话总结,不需要过多文字解释。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_delete_by_range', 'name': '批量删饮食', 'subfunction': '改饮食', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-diet-delete-range <开始> <结束> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「批量删饮食」。\n\n我要按日期范围批量删除饮食记录。删除前告诉我这个范围有几条,确认后删除,给我看:时间范围 + 删除条数 + 确认回执。完成后给 1 句话总结,不需要过多文字解释。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____',
            'user_intent': '按日期范围批量删除饮食记录', 'data_fields': ["start", "end", "deleted"],
            'depends_on_external': False, 'order': 5},
    {
            'category': '饮食',     'wake_word': '看今日饮食',     'desc': '看今日饮食',
            'main_prompt': {
        'cli': 'python scripts/render_today_diet.py --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看今日饮食」。\n\n我想看今天的饮食:按餐别分组列出每条食物(克数/热量/蛋白/碳水/脂肪)+ 今日累计 vs 目标。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_view_today', 'name': '看今日饮食', 'subfunction': '看饮食', 'output_type': 'result',
            'html_template': 'templates/today_diet.html', 'data_source': 'python scripts/render_today_diet.py --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看今日饮食」。\n\n我想看今天的饮食:按餐别分组列出每条食物(克数/热量/蛋白/碳水/脂肪)+ 今日累计 vs 目标。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看今天按餐别分组的饮食明细', 'data_fields': ["meal", "food_name", "grams", "calories", "protein", "carbs", "fat", "goal"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '饮食',     'wake_word': '看昨日饮食',     'desc': '看昨日饮食',
            'main_prompt': {
        'cli': 'python scripts/render_today_diet.py --date <昨天> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看昨日饮食」。\n\n我想看昨天的饮食:按餐别分组列出每条食物(克数/热量/蛋白/碳水/脂肪)+ 当日累计 vs 目标。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_view_yesterday', 'name': '看昨日饮食', 'subfunction': '看饮食', 'output_type': 'result',
            'html_template': 'templates/today_diet.html', 'data_source': 'python scripts/render_today_diet.py --date <昨天> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看昨日饮食」。\n\n我想看昨天的饮食:按餐别分组列出每条食物(克数/热量/蛋白/碳水/脂肪)+ 当日累计 vs 目标。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看昨天按餐别分组的饮食明细', 'data_fields': ["meal", "food_name", "grams", "calories", "protein", "carbs", "fat", "goal"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '饮食',     'wake_word': '看本周饮食',     'desc': '看本周饮食',
            'main_prompt': {
        'cli': 'python scripts/render_today_meals.py --week current --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看本周饮食」。\n\n我想看本周(周一到今天)的饮食明细:逐条列表 + 总热量/日均/总蛋白/日均。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_view_this_week', 'name': '看本周饮食', 'subfunction': '看饮食', 'output_type': 'result',
            'html_template': 'templates/today_meals.html', 'data_source': 'python scripts/render_today_meals.py --week current --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看本周饮食」。\n\n我想看本周(周一到今天)的饮食明细:逐条列表 + 总热量/日均/总蛋白/日均。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看本周自然周的饮食明细与汇总', 'data_fields': ["date", "food_name", "calories", "protein", "total_calorie", "avg_calorie"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '饮食',     'wake_word': '看上周饮食',     'desc': '看上周饮食',
            'main_prompt': {
        'cli': 'python scripts/render_today_meals.py --week last --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看上周饮食」。\n\n我想看上周(上一个自然周)的饮食明细:逐条列表 + 总热量/日均/总蛋白/日均。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_view_last_week', 'name': '看上周饮食', 'subfunction': '看饮食', 'output_type': 'result',
            'html_template': 'templates/today_meals.html', 'data_source': 'python scripts/render_today_meals.py --week last --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看上周饮食」。\n\n我想看上周(上一个自然周)的饮食明细:逐条列表 + 总热量/日均/总蛋白/日均。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看上周自然周的饮食明细与汇总', 'data_fields': ["date", "food_name", "calories", "protein", "total_calorie", "avg_calorie"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '饮食',     'wake_word': '看本月饮食',     'desc': '看本月饮食',
            'main_prompt': {
        'cli': 'python scripts/render_today_meals.py --month current --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看本月饮食」。\n\n我想看本月(自然月)的饮食明细:逐条列表 + 总热量/日均/总蛋白/日均(天数多时按日汇总)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_view_this_month', 'name': '看本月饮食', 'subfunction': '看饮食', 'output_type': 'result',
            'html_template': 'templates/today_meals.html', 'data_source': 'python scripts/render_today_meals.py --month current --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看本月饮食」。\n\n我想看本月(自然月)的饮食明细:逐条列表 + 总热量/日均/总蛋白/日均(天数多时按日汇总)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看本月自然月的饮食明细与汇总', 'data_fields': ["date", "food_name", "calories", "protein", "total_calorie", "avg_calorie"],
            'depends_on_external': False, 'order': 4},
    {
            'category': '饮食',     'wake_word': '看上月饮食',     'desc': '看上月饮食',
            'main_prompt': {
        'cli': 'python scripts/render_today_meals.py --month last --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看上月饮食」。\n\n我想看上月(上一个自然月)的饮食明细:逐条列表 + 总热量/日均/总蛋白/日均(天数多时按日汇总)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_view_last_month', 'name': '看上月饮食', 'subfunction': '看饮食', 'output_type': 'result',
            'html_template': 'templates/today_meals.html', 'data_source': 'python scripts/render_today_meals.py --month last --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看上月饮食」。\n\n我想看上月(上一个自然月)的饮食明细:逐条列表 + 总热量/日均/总蛋白/日均(天数多时按日汇总)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看上月自然月的饮食明细与汇总', 'data_fields': ["date", "food_name", "calories", "protein", "total_calorie", "avg_calorie"],
            'depends_on_external': False, 'order': 5},
    {
            'category': '饮食',     'wake_word': '看最近 7 天饮食',     'desc': '看最近 7 天饮食',
            'main_prompt': {
        'cli': 'python scripts/render_today_meals.py --days 7 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看最近 7 天饮食」。\n\n我想看最近 7 天(滚动窗口)的饮食明细:逐条列表 + 总热量/日均/总蛋白/日均。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_view_7d', 'name': '看最近 7 天饮食', 'subfunction': '看饮食', 'output_type': 'result',
            'html_template': 'templates/today_meals.html', 'data_source': 'python scripts/render_today_meals.py --days 7 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看最近 7 天饮食」。\n\n我想看最近 7 天(滚动窗口)的饮食明细:逐条列表 + 总热量/日均/总蛋白/日均。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看最近 7 天滚动窗口的饮食明细', 'data_fields': ["date", "food_name", "calories", "protein", "total_calorie", "avg_calorie"],
            'depends_on_external': False, 'order': 6},
    {
            'category': '饮食',     'wake_word': '看最近 30 天饮食',     'desc': '看最近 30 天饮食',
            'main_prompt': {
        'cli': 'python scripts/render_today_meals.py --days 30 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看最近 30 天饮食」。\n\n我想看最近 30 天(滚动窗口)的饮食:按日汇总 + 总热量/日均/总蛋白/日均(天数多时降采样)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_view_30d', 'name': '看最近 30 天饮食', 'subfunction': '看饮食', 'output_type': 'result',
            'html_template': 'templates/today_meals.html', 'data_source': 'python scripts/render_today_meals.py --days 30 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看最近 30 天饮食」。\n\n我想看最近 30 天(滚动窗口)的饮食:按日汇总 + 总热量/日均/总蛋白/日均(天数多时降采样)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看最近 30 天滚动窗口的饮食汇总', 'data_fields': ["date", "calories", "total_calorie", "avg_calorie"],
            'depends_on_external': False, 'order': 7},
    {
            'category': '饮食',     'wake_word': '看某段时间饮食',     'desc': '看某段时间饮食',
            'main_prompt': {
        'cli': 'python scripts/render_today_meals.py --start <开始> --end <结束> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看某段时间饮食」。\n\n我想看自定义日期区间的饮食明细:逐条列表 + 区间起止 + 总热量/日均/总蛋白/日均。完成后给 1 句话总结,不需要过多文字解释。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_view_range', 'name': '看某段时间饮食', 'subfunction': '看饮食', 'output_type': 'result',
            'html_template': 'templates/today_meals.html', 'data_source': 'python scripts/render_today_meals.py --start <开始> --end <结束> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看某段时间饮食」。\n\n我想看自定义日期区间的饮食明细:逐条列表 + 区间起止 + 总热量/日均/总蛋白/日均。完成后给 1 句话总结,不需要过多文字解释。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____',
            'user_intent': '看自定义日期区间的饮食明细', 'data_fields': ["start", "end", "date", "food_name", "calories", "total_calorie", "avg_calorie"],
            'depends_on_external': False, 'order': 8},
    {
            'category': '饮食',     'wake_word': '看今日喝水',     'desc': '看今日喝水',
            'main_prompt': {
        'cli': 'python scripts/render_today_water.py --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看今日喝水」。\n\n我想看今天的饮水:累计饮水量/距目标/每杯时间 + 进度条。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_view_water', 'name': '看今日喝水', 'subfunction': '看饮食', 'output_type': 'result',
            'html_template': 'templates/today_water.html', 'data_source': 'python scripts/render_today_water.py --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看今日喝水」。\n\n我想看今天的饮水:累计饮水量/距目标/每杯时间 + 进度条。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看今日饮水总量与目标进度', 'data_fields': ["total_ml", "goal_ml", "remaining_ml", "cups"],
            'depends_on_external': False, 'order': 9},
    {
            'category': '饮食',     'wake_word': '看「有备注」的饮食记录',     'desc': '看「有备注」的饮食记录',
            'main_prompt': {
        'cli': 'python scripts/render_today_meals.py --with-note --days <N> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看「有备注」的饮食记录」。\n\n我想看带备注的饮食记录(如「加了辣酱」「食堂打的」):表(日期/餐别/食物/克数/热量/蛋白/备注)。时间范围默认最近 7 天,也可指定。完成后给 1 句话总结,不需要过多文字解释。\n\n时间范围(选填,默认最近 7 天):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_view_with_note', 'name': '看「有备注」的饮食记录', 'subfunction': '看饮食', 'output_type': 'result',
            'html_template': 'templates/today_meals.html', 'data_source': 'python scripts/render_today_meals.py --with-note --days <N> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看「有备注」的饮食记录」。\n\n我想看带备注的饮食记录(如「加了辣酱」「食堂打的」):表(日期/餐别/食物/克数/热量/蛋白/备注)。时间范围默认最近 7 天,也可指定。完成后给 1 句话总结,不需要过多文字解释。\n\n时间范围(选填,默认最近 7 天):____',
            'user_intent': '查看带备注的饮食记录', 'data_fields': ["date", "meal", "food_name", "grams", "calories", "protein", "note"],
            'depends_on_external': False, 'order': 10},
    {
            'category': '饮食',     'wake_word': '查食品',     'desc': '查食品',
            'main_prompt': {
        'cli': 'python scripts/render_food_search.py --query <关键词>', 'text': '请你加载技能 卡路里,执行唤醒词「查食品」。\n\n我想查某食物的营养数据:名称/品牌/分类/热量/蛋白/碳水/脂肪/来源。如果没查到精确的,给我相近的几条。完成后给 1 句话总结,不需要过多文字解释。\n\n食物名称:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'food_search', 'name': '查食品', 'subfunction': '查食品', 'output_type': 'result',
            'html_template': 'templates/food_search.html', 'data_source': 'python scripts/render_food_search.py --query <关键词>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「查食品」。\n\n我想查某食物的营养数据:名称/品牌/分类/热量/蛋白/碳水/脂肪/来源。如果没查到精确的,给我相近的几条。完成后给 1 句话总结,不需要过多文字解释。\n\n食物名称:____',
            'user_intent': '查询食物的营养数据', 'data_fields': ["product_name", "brand", "calories", "protein", "carbs", "fat", "source"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '饮食',     'wake_word': '查食品（按分类）',     'desc': '查食品（按分类）',
            'main_prompt': {
        'cli': 'python scripts/render_food_search.py --category <分类>', 'text': '请你加载技能 卡路里,执行唤醒词「查食品（按分类）」。\n\n我想按分类查食品库(如 饮料/主食/蛋白类/水果/零食):列出该分类全部食品 + 营养数据,按分类分组展示。完成后给 1 句话总结,不需要过多文字解释。\n\n分类名称:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'food_search_category', 'name': '查食品（按分类）', 'subfunction': '查食品', 'output_type': 'result',
            'html_template': 'templates/food_search.html', 'data_source': 'python scripts/render_food_search.py --category <分类>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「查食品（按分类）」。\n\n我想按分类查食品库(如 饮料/主食/蛋白类/水果/零食):列出该分类全部食品 + 营养数据,按分类分组展示。完成后给 1 句话总结,不需要过多文字解释。\n\n分类名称:____',
            'user_intent': '按分类浏览食品库', 'data_fields': ["category", "product_name", "brand", "calories", "protein"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '饮食',     'wake_word': '存食品',     'desc': '存食品',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-product-add <名称> <品牌> <热量> <蛋白> <脂肪> <饱和脂肪> <碳水> <糖> <纤维> <钠> [备注] --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「存食品」。\n\n我要把新食品的营养数据存进食品库(每 100g 为基准)。告诉我必填字段:名称/品牌/热量/蛋白/脂肪/饱和脂肪/碳水/糖/纤维/钠/来源。存完后给我看:写入回执 + 名称 + 各营养值。完成后给 1 句话总结,不需要过多文字解释。\n\n食品名称:____\n品牌:____\n热量(每 100g):____\n蛋白:____\n脂肪:____\n饱和脂肪(选填):____\n碳水:____\n糖(选填):____\n纤维(选填):____\n钠:____\n来源(选填):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'food_add', 'name': '存食品', 'subfunction': '查食品', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-product-add <名称> <品牌> <热量> <蛋白> <脂肪> <饱和脂肪> <碳水> <糖> <纤维> <钠> [备注] --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「存食品」。\n\n我要把新食品的营养数据存进食品库(每 100g 为基准)。告诉我必填字段:名称/品牌/热量/蛋白/脂肪/饱和脂肪/碳水/糖/纤维/钠/来源。存完后给我看:写入回执 + 名称 + 各营养值。完成后给 1 句话总结,不需要过多文字解释。\n\n食品名称:____\n品牌:____\n热量(每 100g):____\n蛋白:____\n脂肪:____\n饱和脂肪(选填):____\n碳水:____\n糖(选填):____\n纤维(选填):____\n钠:____\n来源(选填):____',
            'user_intent': '把新食品的营养数据存入食品库', 'data_fields': ["product_name", "brand", "calories", "protein", "fat", "carbohydrates", "sodium", "source"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '饮食',     'wake_word': '改食品',     'desc': '改食品',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-product-update <id> [--字段 新值 ...] --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「改食品」。\n\n我要改食品库里某条食品的营养数据。如果我没说清是哪条,先列出相近的几条让我选。改前给我看原值,改后给我看:改前/改后。完成后给 1 句话总结,不需要过多文字解释。\n\n食品名称或编号:____\n要改的字段(热量/蛋白/脂肪/碳水/糖/钠/品牌等):____\n新值:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'food_update', 'name': '改食品', 'subfunction': '查食品', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-product-update <id> [--字段 新值 ...] --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改食品」。\n\n我要改食品库里某条食品的营养数据。如果我没说清是哪条,先列出相近的几条让我选。改前给我看原值,改后给我看:改前/改后。完成后给 1 句话总结,不需要过多文字解释。\n\n食品名称或编号:____\n要改的字段(热量/蛋白/脂肪/碳水/糖/钠/品牌等):____\n新值:____',
            'user_intent': '修改食品库中某条食品的数据', 'data_fields': ["product_name", "brand", "calories", "protein", "fat", "carbohydrates", "sodium"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '饮食',     'wake_word': '下架食品',     'desc': '下架食品',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-product-deprecate <id> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「下架食品」。\n\n我要把食品库里的某条食品下架(标废弃,以后查询/搜索/导入去重都不再出现)。先确认是哪条,下架后给我回执并提示「已下架」。完成后给 1 句话总结,不需要过多文字解释。\n\n食品名称或编号:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'food_deprecate', 'name': '下架食品', 'subfunction': '查食品', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-product-deprecate <id> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「下架食品」。\n\n我要把食品库里的某条食品下架(标废弃,以后查询/搜索/导入去重都不再出现)。先确认是哪条,下架后给我回执并提示「已下架」。完成后给 1 句话总结,不需要过多文字解释。\n\n食品名称或编号:____',
            'user_intent': '下架食品库中的某条食品', 'data_fields': ["id", "product_name", "is_deprecated"],
            'depends_on_external': False, 'order': 4},
    {
            'category': '饮食',     'wake_word': '看食品库（去重）',     'desc': '看食品库（去重）',
            'main_prompt': {
        'cli': 'python scripts/render_dedupe_report.py', 'text': '请你加载技能 卡路里,执行唤醒词「看食品库（去重）」。\n\n我想检查食品库有没有重复的食品(同名同品牌多条)。给我看:重复组列表/重复条数/处理建议。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'food_dedupe', 'name': '看食品库（去重）', 'subfunction': '查食品', 'output_type': 'result',
            'html_template': 'templates/dedupe_report.html', 'data_source': 'python scripts/render_dedupe_report.py', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看食品库（去重）」。\n\n我想检查食品库有没有重复的食品(同名同品牌多条)。给我看:重复组列表/重复条数/处理建议。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '检查食品库中的重复条目', 'data_fields': ["product_name", "brand", "count", "ids"],
            'depends_on_external': False, 'order': 5},
    {
            'category': '饮食',     'wake_word': '批量导入食品',     'desc': '批量导入食品',
            'main_prompt': {
        'cli': 'python scripts/render_batch_import.py --input <preview.json> → 确认后 python scripts/batch_import.py import <file.jsonl>', 'text': '请你加载技能 卡路里,执行唤醒词「批量导入食品」。\n\n我有一个食品数据文件(每行一条:名称/热量/蛋白/脂肪/碳水/钠/来源等)要批量导入食品库。先给我看导入预览(导入条数/跳过条数/失败明细),我确认后再真正写入。完成后给 1 句话总结,不需要过多文字解释。\n\n文件路径:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'food_batch_import', 'name': '批量导入食品', 'subfunction': '查食品', 'output_type': 'process',
            'html_template': 'templates/batch_import_preview.html', 'data_source': 'python scripts/render_batch_import.py --input <preview.json> → 确认后 python scripts/batch_import.py import <file.jsonl>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「批量导入食品」。\n\n我有一个食品数据文件(每行一条:名称/热量/蛋白/脂肪/碳水/钠/来源等)要批量导入食品库。先给我看导入预览(导入条数/跳过条数/失败明细),我确认后再真正写入。完成后给 1 句话总结,不需要过多文字解释。\n\n文件路径:____',
            'user_intent': '批量导入食品数据到食品库', 'data_fields': ["product_name", "calories", "protein", "fat", "carbohydrates", "sodium", "source"],
            'depends_on_external': False, 'order': 6},
    {
            'category': '饮食',     'wake_word': '校验批量导入',     'desc': '校验批量导入',
            'main_prompt': {
        'cli': 'python scripts/batch_import.py validate <file.jsonl> --json-output <out.json> → python scripts/render_batch_import.py --input <out.json>', 'text': '请你加载技能 卡路里,执行唤醒词「校验批量导入」。\n\n我有一个食品数据文件(每行一条),只想先校验能不能导入,不真正写入。给我看:通过条数/失败条数 + 每条失败原因。完成后给 1 句话总结,不需要过多文字解释。\n\n文件路径:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'food_batch_validate', 'name': '校验批量导入', 'subfunction': '查食品', 'output_type': 'result',
            'html_template': 'templates/batch_import_preview.html', 'data_source': 'python scripts/batch_import.py validate <file.jsonl> --json-output <out.json> → python scripts/render_batch_import.py --input <out.json>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「校验批量导入」。\n\n我有一个食品数据文件(每行一条),只想先校验能不能导入,不真正写入。给我看:通过条数/失败条数 + 每条失败原因。完成后给 1 句话总结,不需要过多文字解释。\n\n文件路径:____',
            'user_intent': '预校验批量导入文件能否通过', 'data_fields': ["line", "name", "status", "reason"],
            'depends_on_external': False, 'order': 7},
    {
            'category': '饮食',     'wake_word': '看食品来源统计',     'desc': '看食品来源统计',
            'main_prompt': {
        'cli': 'python scripts/render_source_stats.py', 'text': '请你加载技能 卡路里,执行唤醒词「看食品来源统计」。\n\n我想看食品库的食品来源分布(按来源分组计数):每个来源多少条 + 占比 + 总数。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'food_source_stats', 'name': '看食品来源统计', 'subfunction': '查食品', 'output_type': 'result',
            'html_template': 'templates/source_stats.html', 'data_source': 'python scripts/render_source_stats.py', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看食品来源统计」。\n\n我想看食品库的食品来源分布(按来源分组计数):每个来源多少条 + 占比 + 总数。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看食品库按来源分组的统计', 'data_fields': ["source", "count", "pct", "total"],
            'depends_on_external': False, 'order': 8},
    {
            'category': '饮食',     'wake_word': '看营养结构',     'desc': '看营养结构',
            'main_prompt': {
        'cli': 'python scripts/render_nutrition_ratio.py --days 7 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看营养结构」。\n\n我想看最近一段时间(默认 7 天)的蛋白/碳水/脂肪占比:饼图 + 实际 vs 目标。如果我要看别的窗口会告诉你。完成后给 1 句话总结,不需要过多文字解释。\n\n时间范围(选填,默认最近 7 天):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'nutrition_ratio', 'name': '看营养结构', 'subfunction': '看营养', 'output_type': 'result',
            'html_template': 'templates/nutrition_ratio.html', 'data_source': 'python scripts/render_nutrition_ratio.py --days 7 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看营养结构」。\n\n我想看最近一段时间(默认 7 天)的蛋白/碳水/脂肪占比:饼图 + 实际 vs 目标。如果我要看别的窗口会告诉你。完成后给 1 句话总结,不需要过多文字解释。\n\n时间范围(选填,默认最近 7 天):____',
            'user_intent': '看蛋白碳水脂肪的营养占比', 'data_fields': ["protein_pct", "carb_pct", "fat_pct", "goal"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '饮食',     'wake_word': '看今日营养',     'desc': '看今日营养',
            'main_prompt': {
        'cli': 'python scripts/render_today_diet.py --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看今日营养」。\n\n我想看今天 4 项营养(热量/蛋白/碳水/脂肪)的实际 vs 目标 + 完成度。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'nutrition_today', 'name': '看今日营养', 'subfunction': '看营养', 'output_type': 'result',
            'html_template': 'templates/today_diet.html', 'data_source': 'python scripts/render_today_diet.py --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看今日营养」。\n\n我想看今天 4 项营养(热量/蛋白/碳水/脂肪)的实际 vs 目标 + 完成度。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看今日 4 项营养完成度', 'data_fields': ["calories", "protein", "carbs", "fat", "goal", "pct"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '饮食',     'wake_word': '看饮食总览',     'desc': '看饮食总览',
            'main_prompt': {
        'cli': 'python scripts/render_diet_overview.py --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看饮食总览」。\n\n我想看周期累计的饮食总览:本周/本月累计(总热量/日均/总蛋白)+ 趋势小图(不含今日,今日看主页)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'nutrition_overview', 'name': '看饮食总览', 'subfunction': '看营养', 'output_type': 'result',
            'html_template': 'templates/diet_overview.html', 'data_source': 'python scripts/render_diet_overview.py --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看饮食总览」。\n\n我想看周期累计的饮食总览:本周/本月累计(总热量/日均/总蛋白)+ 趋势小图(不含今日,今日看主页)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看本周本月累计饮食总览', 'data_fields': ["week_total", "month_total", "avg_cal", "trend"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '饮食',     'wake_word': '看营养素深度',     'desc': '看营养素深度',
            'main_prompt': {
        'cli': 'python scripts/render_nutrition_detail.py --days 7 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看营养素深度」。\n\n我想看微量营养素摄入:纤维/钠/糖 vs 推荐值(时间范围默认最近 7 天)。食品库没有的按缺数据标注。完成后给 1 句话总结,不需要过多文字解释。\n\n时间范围(选填,默认最近 7 天):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'nutrition_detail', 'name': '看营养素深度', 'subfunction': '看营养', 'output_type': 'result',
            'html_template': 'templates/nutrition_detail.html', 'data_source': 'python scripts/render_nutrition_detail.py --days 7 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看营养素深度」。\n\n我想看微量营养素摄入:纤维/钠/糖 vs 推荐值(时间范围默认最近 7 天)。食品库没有的按缺数据标注。完成后给 1 句话总结,不需要过多文字解释。\n\n时间范围(选填,默认最近 7 天):____',
            'user_intent': '看纤维钠糖等微量营养素摄入', 'data_fields': ["fiber", "sodium", "sugar", "target", "missing_foods"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '饮食',     'wake_word': '看高热量榜',     'desc': '看高热量榜',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category high_calorie --top-n 10 --days 7 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看高热量榜」。\n\n我想看最近一段时间(默认 7 天)热量最高的食物 TOP 10:排名/食物/热量。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_high_calorie', 'name': '看高热量榜', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category high_calorie --top-n 10 --days 7 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看高热量榜」。\n\n我想看最近一段时间(默认 7 天)热量最高的食物 TOP 10:排名/食物/热量。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看高热量食物 TOP10', 'data_fields': ["rank", "food_name", "calories"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '饮食',     'wake_word': '看低热量榜',     'desc': '看低热量榜',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category low_calorie --top-n 10 --days 7 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看低热量榜」。\n\n我想看最近一段时间(默认 7 天)热量最低的食物 TOP 10:排名/食物/热量。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_low_calorie', 'name': '看低热量榜', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category low_calorie --top-n 10 --days 7 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看低热量榜」。\n\n我想看最近一段时间(默认 7 天)热量最低的食物 TOP 10:排名/食物/热量。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看低热量食物 TOP10', 'data_fields': ["rank", "food_name", "calories"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '饮食',     'wake_word': '看频繁吃榜',     'desc': '看频繁吃榜',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category frequent --top-n 10 --days 7 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看频繁吃榜」。\n\n我想看最近一段时间(默认 7 天)吃得最多的食物 TOP 10:排名/食物/频次/最近一次。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_frequent', 'name': '看频繁吃榜', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category frequent --top-n 10 --days 7 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看频繁吃榜」。\n\n我想看最近一段时间(默认 7 天)吃得最多的食物 TOP 10:排名/食物/频次/最近一次。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看最常吃的食物 TOP10', 'data_fields': ["rank", "food_name", "count", "last_date"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '饮食',     'wake_word': '看高碳水榜',     'desc': '看高碳水榜',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category high_carb --top-n 10 --days 7 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看高碳水榜」。\n\n我想看最近一段时间(默认 7 天)碳水最高的食物 TOP 10:排名/食物/碳水。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_high_carb', 'name': '看高碳水榜', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category high_carb --top-n 10 --days 7 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看高碳水榜」。\n\n我想看最近一段时间(默认 7 天)碳水最高的食物 TOP 10:排名/食物/碳水。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看高碳水食物 TOP10', 'data_fields': ["rank", "food_name", "carbs"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '饮食',     'wake_word': '看高蛋白榜',     'desc': '看高蛋白榜',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category high_protein --top-n 10 --days 7 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看高蛋白榜」。\n\n我想看最近一段时间(默认 7 天)蛋白最高的食物 TOP 10:排名/食物/蛋白。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_high_protein', 'name': '看高蛋白榜', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category high_protein --top-n 10 --days 7 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看高蛋白榜」。\n\n我想看最近一段时间(默认 7 天)蛋白最高的食物 TOP 10:排名/食物/蛋白。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看高蛋白食物 TOP10', 'data_fields': ["rank", "food_name", "protein"],
            'depends_on_external': False, 'order': 4},
    {
            'category': '饮食',     'wake_word': '看高热量榜（最近 30 天）',     'desc': '看高热量榜（最近 30 天）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category high_calorie --top-n 10 --days 30 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看高热量榜（最近 30 天）」。\n\n我想看最近 30 天热量最高的食物 TOP 10:排名/食物/热量。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_high_calorie_30d', 'name': '看高热量榜（最近 30 天）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category high_calorie --top-n 10 --days 30 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看高热量榜（最近 30 天）」。\n\n我想看最近 30 天热量最高的食物 TOP 10:排名/食物/热量。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看最近 30 天高热量食物 TOP10', 'data_fields': ["rank", "food_name", "calories"],
            'depends_on_external': False, 'order': 5},
    {
            'category': '饮食',     'wake_word': '看高热量榜（本月）',     'desc': '看高热量榜（本月）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category high_calorie --top-n 10 --start <月初> --end <月末> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看高热量榜（本月）」。\n\n我想看本月(自然月)热量最高的食物 TOP 10:排名/食物/热量。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_high_calorie_month', 'name': '看高热量榜（本月）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category high_calorie --top-n 10 --start <月初> --end <月末> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看高热量榜（本月）」。\n\n我想看本月(自然月)热量最高的食物 TOP 10:排名/食物/热量。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看本月高热量食物 TOP10', 'data_fields': ["rank", "food_name", "calories"],
            'depends_on_external': False, 'order': 6},
    {
            'category': '饮食',     'wake_word': '看高热量榜（自定义）',     'desc': '看高热量榜（自定义）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category high_calorie --top-n 10 --start <开始> --end <结束> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看高热量榜（自定义）」。\n\n我想看自定义日期区间热量最高的食物 TOP 10:排名/食物/热量 + 区间起止。完成后给 1 句话总结,不需要过多文字解释。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_high_calorie_custom', 'name': '看高热量榜（自定义）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category high_calorie --top-n 10 --start <开始> --end <结束> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看高热量榜（自定义）」。\n\n我想看自定义日期区间热量最高的食物 TOP 10:排名/食物/热量 + 区间起止。完成后给 1 句话总结,不需要过多文字解释。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____',
            'user_intent': '看自定义区间高热量食物 TOP10', 'data_fields': ["rank", "food_name", "calories", "start", "end"],
            'depends_on_external': False, 'order': 7},
    {
            'category': '饮食',     'wake_word': '看低热量榜（最近 30 天）',     'desc': '看低热量榜（最近 30 天）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category low_calorie --top-n 10 --days 30 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看低热量榜（最近 30 天）」。\n\n我想看最近 30 天热量最低的食物 TOP 10:排名/食物/热量。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_low_calorie_30d', 'name': '看低热量榜（最近 30 天）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category low_calorie --top-n 10 --days 30 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看低热量榜（最近 30 天）」。\n\n我想看最近 30 天热量最低的食物 TOP 10:排名/食物/热量。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看最近 30 天低热量食物 TOP10', 'data_fields': ["rank", "food_name", "calories"],
            'depends_on_external': False, 'order': 8},
    {
            'category': '饮食',     'wake_word': '看低热量榜（本月）',     'desc': '看低热量榜（本月）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category low_calorie --top-n 10 --start <月初> --end <月末> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看低热量榜（本月）」。\n\n我想看本月(自然月)热量最低的食物 TOP 10:排名/食物/热量。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_low_calorie_month', 'name': '看低热量榜（本月）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category low_calorie --top-n 10 --start <月初> --end <月末> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看低热量榜（本月）」。\n\n我想看本月(自然月)热量最低的食物 TOP 10:排名/食物/热量。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看本月低热量食物 TOP10', 'data_fields': ["rank", "food_name", "calories"],
            'depends_on_external': False, 'order': 9},
    {
            'category': '饮食',     'wake_word': '看低热量榜（自定义）',     'desc': '看低热量榜（自定义）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category low_calorie --top-n 10 --start <开始> --end <结束> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看低热量榜（自定义）」。\n\n我想看自定义日期区间热量最低的食物 TOP 10:排名/食物/热量 + 区间起止。完成后给 1 句话总结,不需要过多文字解释。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_low_calorie_custom', 'name': '看低热量榜（自定义）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category low_calorie --top-n 10 --start <开始> --end <结束> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看低热量榜（自定义）」。\n\n我想看自定义日期区间热量最低的食物 TOP 10:排名/食物/热量 + 区间起止。完成后给 1 句话总结,不需要过多文字解释。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____',
            'user_intent': '看自定义区间低热量食物 TOP10', 'data_fields': ["rank", "food_name", "calories", "start", "end"],
            'depends_on_external': False, 'order': 10},
    {
            'category': '饮食',     'wake_word': '看频繁吃榜（最近 30 天）',     'desc': '看频繁吃榜（最近 30 天）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category frequent --top-n 10 --days 30 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看频繁吃榜（最近 30 天）」。\n\n我想看最近 30 天吃得最多的食物 TOP 10:排名/食物/频次/最近一次。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_frequent_30d', 'name': '看频繁吃榜（最近 30 天）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category frequent --top-n 10 --days 30 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看频繁吃榜（最近 30 天）」。\n\n我想看最近 30 天吃得最多的食物 TOP 10:排名/食物/频次/最近一次。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看最近 30 天最常吃的食物 TOP10', 'data_fields': ["rank", "food_name", "count", "last_date"],
            'depends_on_external': False, 'order': 11},
    {
            'category': '饮食',     'wake_word': '看频繁吃榜（本月）',     'desc': '看频繁吃榜（本月）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category frequent --top-n 10 --start <月初> --end <月末> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看频繁吃榜（本月）」。\n\n我想看本月(自然月)吃得最多的食物 TOP 10:排名/食物/频次/最近一次。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_frequent_month', 'name': '看频繁吃榜（本月）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category frequent --top-n 10 --start <月初> --end <月末> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看频繁吃榜（本月）」。\n\n我想看本月(自然月)吃得最多的食物 TOP 10:排名/食物/频次/最近一次。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看本月最常吃的食物 TOP10', 'data_fields': ["rank", "food_name", "count", "last_date"],
            'depends_on_external': False, 'order': 12},
    {
            'category': '饮食',     'wake_word': '看频繁吃榜（自定义）',     'desc': '看频繁吃榜（自定义）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category frequent --top-n 10 --start <开始> --end <结束> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看频繁吃榜（自定义）」。\n\n我想看自定义日期区间吃得最多的食物 TOP 10:排名/食物/频次/最近一次 + 区间起止。完成后给 1 句话总结,不需要过多文字解释。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_frequent_custom', 'name': '看频繁吃榜（自定义）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category frequent --top-n 10 --start <开始> --end <结束> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看频繁吃榜（自定义）」。\n\n我想看自定义日期区间吃得最多的食物 TOP 10:排名/食物/频次/最近一次 + 区间起止。完成后给 1 句话总结,不需要过多文字解释。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____',
            'user_intent': '看自定义区间最常吃的食物 TOP10', 'data_fields': ["rank", "food_name", "count", "last_date", "start", "end"],
            'depends_on_external': False, 'order': 13},
    {
            'category': '饮食',     'wake_word': '看高碳水榜（最近 30 天）',     'desc': '看高碳水榜（最近 30 天）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category high_carb --top-n 10 --days 30 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看高碳水榜（最近 30 天）」。\n\n我想看最近 30 天碳水最高的食物 TOP 10:排名/食物/碳水。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_high_carb_30d', 'name': '看高碳水榜（最近 30 天）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category high_carb --top-n 10 --days 30 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看高碳水榜（最近 30 天）」。\n\n我想看最近 30 天碳水最高的食物 TOP 10:排名/食物/碳水。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看最近 30 天高碳水食物 TOP10', 'data_fields': ["rank", "food_name", "carbs"],
            'depends_on_external': False, 'order': 14},
    {
            'category': '饮食',     'wake_word': '看高碳水榜（本月）',     'desc': '看高碳水榜（本月）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category high_carb --top-n 10 --start <月初> --end <月末> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看高碳水榜（本月）」。\n\n我想看本月(自然月)碳水最高的食物 TOP 10:排名/食物/碳水。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_high_carb_month', 'name': '看高碳水榜（本月）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category high_carb --top-n 10 --start <月初> --end <月末> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看高碳水榜（本月）」。\n\n我想看本月(自然月)碳水最高的食物 TOP 10:排名/食物/碳水。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看本月高碳水食物 TOP10', 'data_fields': ["rank", "food_name", "carbs"],
            'depends_on_external': False, 'order': 15},
    {
            'category': '饮食',     'wake_word': '看高碳水榜（自定义）',     'desc': '看高碳水榜（自定义）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category high_carb --top-n 10 --start <开始> --end <结束> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看高碳水榜（自定义）」。\n\n我想看自定义日期区间碳水最高的食物 TOP 10:排名/食物/碳水 + 区间起止。完成后给 1 句话总结,不需要过多文字解释。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_high_carb_custom', 'name': '看高碳水榜（自定义）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category high_carb --top-n 10 --start <开始> --end <结束> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看高碳水榜（自定义）」。\n\n我想看自定义日期区间碳水最高的食物 TOP 10:排名/食物/碳水 + 区间起止。完成后给 1 句话总结,不需要过多文字解释。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____',
            'user_intent': '看自定义区间高碳水食物 TOP10', 'data_fields': ["rank", "food_name", "carbs", "start", "end"],
            'depends_on_external': False, 'order': 16},
    {
            'category': '饮食',     'wake_word': '看高蛋白榜（最近 30 天）',     'desc': '看高蛋白榜（最近 30 天）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category high_protein --top-n 10 --days 30 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看高蛋白榜（最近 30 天）」。\n\n我想看最近 30 天蛋白最高的食物 TOP 10:排名/食物/蛋白。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_high_protein_30d', 'name': '看高蛋白榜（最近 30 天）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category high_protein --top-n 10 --days 30 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看高蛋白榜（最近 30 天）」。\n\n我想看最近 30 天蛋白最高的食物 TOP 10:排名/食物/蛋白。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看最近 30 天高蛋白食物 TOP10', 'data_fields': ["rank", "food_name", "protein"],
            'depends_on_external': False, 'order': 17},
    {
            'category': '饮食',     'wake_word': '看高蛋白榜（本月）',     'desc': '看高蛋白榜（本月）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category high_protein --top-n 10 --start <月初> --end <月末> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看高蛋白榜（本月）」。\n\n我想看本月(自然月)蛋白最高的食物 TOP 10:排名/食物/蛋白。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_high_protein_month', 'name': '看高蛋白榜（本月）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category high_protein --top-n 10 --start <月初> --end <月末> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看高蛋白榜（本月）」。\n\n我想看本月(自然月)蛋白最高的食物 TOP 10:排名/食物/蛋白。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看本月高蛋白食物 TOP10', 'data_fields': ["rank", "food_name", "protein"],
            'depends_on_external': False, 'order': 18},
    {
            'category': '饮食',     'wake_word': '看高蛋白榜（自定义）',     'desc': '看高蛋白榜（自定义）',
            'main_prompt': {
        'cli': 'python scripts/render_food_ranking.py --category high_protein --top-n 10 --start <开始> --end <结束> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看高蛋白榜（自定义）」。\n\n我想看自定义日期区间蛋白最高的食物 TOP 10:排名/食物/蛋白 + 区间起止。完成后给 1 句话总结,不需要过多文字解释。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'ranking_high_protein_custom', 'name': '看高蛋白榜（自定义）', 'subfunction': '看排行', 'output_type': 'result',
            'html_template': 'templates/food_ranking.html', 'data_source': 'python scripts/render_food_ranking.py --category high_protein --top-n 10 --start <开始> --end <结束> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看高蛋白榜（自定义）」。\n\n我想看自定义日期区间蛋白最高的食物 TOP 10:排名/食物/蛋白 + 区间起止。完成后给 1 句话总结,不需要过多文字解释。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____',
            'user_intent': '看自定义区间高蛋白食物 TOP10', 'data_fields': ["rank", "food_name", "protein", "start", "end"],
            'depends_on_external': False, 'order': 19},
    {
            'category': '饮食',     'wake_word': '饮食复盘（本周）',     'desc': '饮食复盘（本周）',
            'main_prompt': {
        'cli': 'python scripts/render_diet_review.py --type week --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「饮食复盘（本周）」。\n\n我想看本周饮食复盘:总热量/日均/总蛋白/日均 + 趋势 + 高频 TOP5 + 一句话结论。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_review_week', 'name': '饮食复盘（本周）', 'subfunction': '饮食复盘', 'output_type': 'result',
            'html_template': 'templates/diet_review.html', 'data_source': 'python scripts/render_diet_review.py --type week --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「饮食复盘（本周）」。\n\n我想看本周饮食复盘:总热量/日均/总蛋白/日均 + 趋势 + 高频 TOP5 + 一句话结论。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看本周饮食复盘小结', 'data_fields': ["total_cal", "avg_cal", "total_protein", "avg_protein", "top5", "trend"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '饮食',     'wake_word': '饮食复盘（本月）',     'desc': '饮食复盘（本月）',
            'main_prompt': {
        'cli': 'python scripts/render_diet_review.py --type month --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「饮食复盘（本月）」。\n\n我想看本月饮食复盘:总热量/日均/总蛋白/日均 + 趋势 + 高频 TOP5 + 一句话结论。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_review_month', 'name': '饮食复盘（本月）', 'subfunction': '饮食复盘', 'output_type': 'result',
            'html_template': 'templates/diet_review.html', 'data_source': 'python scripts/render_diet_review.py --type month --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「饮食复盘（本月）」。\n\n我想看本月饮食复盘:总热量/日均/总蛋白/日均 + 趋势 + 高频 TOP5 + 一句话结论。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看本月饮食复盘小结', 'data_fields': ["total_cal", "avg_cal", "total_protein", "avg_protein", "top5", "trend"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '饮食',     'wake_word': '饮食复盘（最近 90 天）',     'desc': '饮食复盘（最近 90 天）',
            'main_prompt': {
        'cli': 'python scripts/render_diet_review.py --type quarter --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「饮食复盘（最近 90 天）」。\n\n我想看最近 90 天饮食复盘:总热量/日均/总蛋白/日均 + 趋势 + 高频 TOP5 + 一句话结论。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_review_90d', 'name': '饮食复盘（最近 90 天）', 'subfunction': '饮食复盘', 'output_type': 'result',
            'html_template': 'templates/diet_review.html', 'data_source': 'python scripts/render_diet_review.py --type quarter --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「饮食复盘（最近 90 天）」。\n\n我想看最近 90 天饮食复盘:总热量/日均/总蛋白/日均 + 趋势 + 高频 TOP5 + 一句话结论。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看最近 90 天饮食复盘小结', 'data_fields': ["total_cal", "avg_cal", "total_protein", "avg_protein", "top5", "trend"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '饮食',     'wake_word': '饮食复盘（今年）',     'desc': '饮食复盘（今年）',
            'main_prompt': {
        'cli': 'python scripts/render_diet_review.py --type year --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「饮食复盘（今年）」。\n\n我想看今年饮食复盘:总热量/日均/总蛋白/日均 + 趋势 + 高频 TOP5 + 一句话结论。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_review_year', 'name': '饮食复盘（今年）', 'subfunction': '饮食复盘', 'output_type': 'result',
            'html_template': 'templates/diet_review.html', 'data_source': 'python scripts/render_diet_review.py --type year --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「饮食复盘（今年）」。\n\n我想看今年饮食复盘:总热量/日均/总蛋白/日均 + 趋势 + 高频 TOP5 + 一句话结论。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看今年饮食复盘小结', 'data_fields': ["total_cal", "avg_cal", "total_protein", "avg_protein", "top5", "trend"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '饮食',     'wake_word': '饮食复盘（自定义时间）',     'desc': '饮食复盘（自定义时间）',
            'main_prompt': {
        'cli': 'python scripts/render_diet_review.py --type range --start <开始> --end <结束> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「饮食复盘（自定义时间）」。\n\n我想看自定义日期区间的饮食复盘:总热量/日均/总蛋白/日均 + 趋势 + 高频 TOP5 + 一句话结论 + 区间。完成后给 1 句话总结,不需要过多文字解释。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'diet_review_range', 'name': '饮食复盘（自定义时间）', 'subfunction': '饮食复盘', 'output_type': 'result',
            'html_template': 'templates/diet_review.html', 'data_source': 'python scripts/render_diet_review.py --type range --start <开始> --end <结束> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「饮食复盘（自定义时间）」。\n\n我想看自定义日期区间的饮食复盘:总热量/日均/总蛋白/日均 + 趋势 + 高频 TOP5 + 一句话结论 + 区间。完成后给 1 句话总结,不需要过多文字解释。\n\n开始日期(YYYY-MM-DD):____\n结束日期(YYYY-MM-DD):____',
            'user_intent': '看自定义区间的饮食复盘小结', 'data_fields': ["total_cal", "avg_cal", "total_protein", "avg_protein", "top5", "trend", "start", "end"],
            'depends_on_external': False, 'order': 4},
    {
            'category': '饮食',     'wake_word': '看早餐（最近 7 天）',     'desc': '看早餐（最近 7 天）',
            'main_prompt': {
        'cli': 'python scripts/render_meal_distribution.py --meal breakfast --days 7 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看早餐（最近 7 天）」。\n\n我想看最近 7 天早餐的饮食:明细表 + 早餐日均 + 一句话结论。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'meal_dist_breakfast', 'name': '看早餐（最近 7 天）', 'subfunction': '餐别分布', 'output_type': 'result',
            'html_template': 'templates/meal_distribution.html', 'data_source': 'python scripts/render_meal_distribution.py --meal breakfast --days 7 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看早餐（最近 7 天）」。\n\n我想看最近 7 天早餐的饮食:明细表 + 早餐日均 + 一句话结论。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看最近 7 天早餐饮食明细', 'data_fields': ["date", "food_name", "calories", "avg_cal", "meal"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '饮食',     'wake_word': '看午餐（最近 7 天）',     'desc': '看午餐（最近 7 天）',
            'main_prompt': {
        'cli': 'python scripts/render_meal_distribution.py --meal lunch --days 7 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看午餐（最近 7 天）」。\n\n我想看最近 7 天午餐的饮食:明细表 + 午餐日均 + 一句话结论。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'meal_dist_lunch', 'name': '看午餐（最近 7 天）', 'subfunction': '餐别分布', 'output_type': 'result',
            'html_template': 'templates/meal_distribution.html', 'data_source': 'python scripts/render_meal_distribution.py --meal lunch --days 7 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看午餐（最近 7 天）」。\n\n我想看最近 7 天午餐的饮食:明细表 + 午餐日均 + 一句话结论。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看最近 7 天午餐饮食明细', 'data_fields': ["date", "food_name", "calories", "avg_cal", "meal"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '饮食',     'wake_word': '看晚餐（最近 7 天）',     'desc': '看晚餐（最近 7 天）',
            'main_prompt': {
        'cli': 'python scripts/render_meal_distribution.py --meal dinner --days 7 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看晚餐（最近 7 天）」。\n\n我想看最近 7 天晚餐的饮食:明细表 + 晚餐日均 + 一句话结论。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'meal_dist_dinner', 'name': '看晚餐（最近 7 天）', 'subfunction': '餐别分布', 'output_type': 'result',
            'html_template': 'templates/meal_distribution.html', 'data_source': 'python scripts/render_meal_distribution.py --meal dinner --days 7 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看晚餐（最近 7 天）」。\n\n我想看最近 7 天晚餐的饮食:明细表 + 晚餐日均 + 一句话结论。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看最近 7 天晚餐饮食明细', 'data_fields': ["date", "food_name", "calories", "avg_cal", "meal"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '饮食',     'wake_word': '看加餐（最近 7 天）',     'desc': '看加餐（最近 7 天）',
            'main_prompt': {
        'cli': 'python scripts/render_meal_distribution.py --meal snack --days 7 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看加餐（最近 7 天）」。\n\n我想看最近 7 天加餐(下午茶+夜宵)的饮食:明细表 + 加餐日均 + 一句话结论。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'meal_dist_snack', 'name': '看加餐（最近 7 天）', 'subfunction': '餐别分布', 'output_type': 'result',
            'html_template': 'templates/meal_distribution.html', 'data_source': 'python scripts/render_meal_distribution.py --meal snack --days 7 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看加餐（最近 7 天）」。\n\n我想看最近 7 天加餐(下午茶+夜宵)的饮食:明细表 + 加餐日均 + 一句话结论。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看最近 7 天加餐饮食明细', 'data_fields': ["date", "food_name", "calories", "avg_cal", "meal"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '饮食',     'wake_word': '看全部餐别分布（最近 7 天）',     'desc': '看全部餐别分布（最近 7 天）',
            'main_prompt': {
        'cli': 'python scripts/render_meal_distribution.py --meal all --days 7 --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看全部餐别分布（最近 7 天）」。\n\n我想看最近 7 天各餐别(早餐/午餐/晚餐/加餐)的分布对比:明细表 + 各餐别热量占比 + 占比%。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'meal_dist_all', 'name': '看全部餐别分布（最近 7 天）', 'subfunction': '餐别分布', 'output_type': 'result',
            'html_template': 'templates/meal_distribution.html', 'data_source': 'python scripts/render_meal_distribution.py --meal all --days 7 --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看全部餐别分布（最近 7 天）」。\n\n我想看最近 7 天各餐别(早餐/午餐/晚餐/加餐)的分布对比:明细表 + 各餐别热量占比 + 占比%。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看最近 7 天全部餐别分布对比', 'data_fields': ["meal", "count", "calories", "pct"],
            'depends_on_external': False, 'order': 4},

    {
            'category': '体重',     'wake_word': '记体重',     'desc': '记录今天的体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_receipt.py --live --kg <kg> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「记体重」。\n\n我刚称了体重,帮我记录今天的体重。记录后请给我看:体重值、记录时间、BMI、与上次体重的差距、与目标体重的差距。完成后给 1 句话总结,不需要过多文字解释。\n\n体重(kg):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_log', 'name': '记体重', 'subfunction': '量体重', 'output_type': 'receipt',
            'html_template': 'templates/weight_log_receipt.html', 'data_source': 'python scripts/render_weight_receipt.py --live --kg <kg> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「记体重」。\n\n我刚称了体重,帮我记录今天的体重。记录后请给我看:体重值、记录时间、BMI、与上次体重的差距、与目标体重的差距。完成后给 1 句话总结,不需要过多文字解释。\n\n体重(kg):____',
            'user_intent': '记录今天的体重', 'data_fields': ['weight_kg', 'bmi', 'delta_last', 'goal_diff', 'date', 'time'],
            'depends_on_external': False, 'order': 0
    },
    {
            'category': '体重',     'wake_word': '记体重（含备注）',     'desc': '记录今天的体重并带备注',
            'main_prompt': {
        'cli': 'python scripts/render_weight_receipt.py --live --kg <kg> --note <备注> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「记体重（含备注）」。\n\n我刚称了体重,记录今天的体重并带上备注(如 晨起空腹/运动后/睡前)。记录后请给我看:体重值、记录时间、BMI、备注、备注分类标签、与目标体重的差距。完成后给 1 句话总结,不需要过多文字解释。\n\n体重(kg):____\n备注:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_log_note', 'name': '记体重（含备注）', 'subfunction': '量体重', 'output_type': 'receipt',
            'html_template': 'templates/weight_log_receipt.html', 'data_source': 'python scripts/render_weight_receipt.py --live --kg <kg> --note <备注> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「记体重（含备注）」。\n\n我刚称了体重,记录今天的体重并带上备注(如 晨起空腹/运动后/睡前)。记录后请给我看:体重值、记录时间、BMI、备注、备注分类标签、与目标体重的差距。完成后给 1 句话总结,不需要过多文字解释。\n\n体重(kg):____\n备注:____',
            'user_intent': '记录今天的体重并带备注', 'data_fields': ['weight_kg', 'bmi', 'note', 'note_tag', 'goal_diff', 'date', 'time'],
            'depends_on_external': False, 'order': 1
    },
    {
            'category': '体重',     'wake_word': '补录体重',     'desc': '补录过去某天的体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_receipt.py --live --kg <kg> --date <YYYY-MM-DD> --chain "1.解析→2.查冲突→3.写库→4.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「补录体重」。\n\n我要补录过去某天的体重(不是今天)。补录后请给我看:日期、体重值、BMI、补录标识、距今天数。完成后给 1 句话总结,不需要过多文字解释。\n\n体重(kg):____\n日期(YYYY-MM-DD):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_backfill', 'name': '补录体重', 'subfunction': '量体重', 'output_type': 'receipt',
            'html_template': 'templates/weight_log_receipt.html', 'data_source': 'python scripts/render_weight_receipt.py --live --kg <kg> --date <YYYY-MM-DD> --chain "1.解析→2.查冲突→3.写库→4.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「补录体重」。\n\n我要补录过去某天的体重(不是今天)。补录后请给我看:日期、体重值、BMI、补录标识、距今天数。完成后给 1 句话总结,不需要过多文字解释。\n\n体重(kg):____\n日期(YYYY-MM-DD):____',
            'user_intent': '补录过去某天的体重', 'data_fields': ['weight_kg', 'bmi', 'date', 'days_ago', 'backfill_flag', 'conflict'],
            'depends_on_external': False, 'order': 2
    },
    {
            'category': '体重',     'wake_word': '批量补录体重',     'desc': '一次补录多天体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_receipt.py --live-batch --input <jsonl> --chain "1.解析→2.查冲突→3.批量写库→4.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「批量补录体重」。\n\n我要一次补录多天的体重。我会给你 日期+体重 的列表(每行一条),也可能只说连续天数加起始体重让你帮我生成。记录完成后请给我看:写入条数、跳过条数、失败条数与失败明细。完成后给 1 句话总结,不需要过多文字解释。\n\n多天体重(每行一条: 日期 体重):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_backfill_batch', 'name': '批量补录体重', 'subfunction': '量体重', 'output_type': 'receipt',
            'html_template': 'templates/weight_batch_receipt.html', 'data_source': 'python scripts/render_weight_receipt.py --live-batch --input <jsonl> --chain "1.解析→2.查冲突→3.批量写库→4.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「批量补录体重」。\n\n我要一次补录多天的体重。我会给你 日期+体重 的列表(每行一条),也可能只说连续天数加起始体重让你帮我生成。记录完成后请给我看:写入条数、跳过条数、失败条数与失败明细。完成后给 1 句话总结,不需要过多文字解释。\n\n多天体重(每行一条: 日期 体重):____',
            'user_intent': '一次补录多天体重', 'data_fields': ['wrote', 'skipped', 'failed', 'fail_details', 'items'],
            'depends_on_external': False, 'order': 3
    },
    {
            'category': '体重',     'wake_word': '看今日体重',     'desc': '看今天的体重数据',
            'main_prompt': {
        'cli': 'python scripts/render_weight_dashboard.py --view today --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看今日体重」。\n\n我想看今天的体重数据:今天的体重值、与上次体重的差距、一句话点评。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_today', 'name': '看今日体重', 'subfunction': '量体重', 'output_type': 'result',
            'html_template': 'templates/weight_dashboard.html', 'data_source': 'python scripts/render_weight_dashboard.py --view today --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看今日体重」。\n\n我想看今天的体重数据:今天的体重值、与上次体重的差距、一句话点评。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看今天的体重数据', 'data_fields': ['weight_kg', 'delta_last', 'summary', 'date'],
            'depends_on_external': False, 'order': 4
    },
    {
            'category': '体重',     'wake_word': '改体重记录',     'desc': '修改某条体重记录',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-weight-update --id <ID> --weight <kg> --note <备注> --chain "1.定位→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「改体重记录」。\n\n我要改某条体重记录(体重值或备注)。改完后请给我看:改前/改后对比 + 影响字段(如 BMI 变化)。完成后给 1 句话总结,不需要过多文字解释。\n\n要改的记录(最近一条/日期/编号):____\n新体重(kg):____\n新备注:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_update', 'name': '改体重记录', 'subfunction': '改体重记录', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-weight-update --id <ID> --weight <kg> --note <备注> --chain "1.定位→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改体重记录」。\n\n我要改某条体重记录(体重值或备注)。改完后请给我看:改前/改后对比 + 影响字段(如 BMI 变化)。完成后给 1 句话总结,不需要过多文字解释。\n\n要改的记录(最近一条/日期/编号):____\n新体重(kg):____\n新备注:____',
            'user_intent': '修改某条体重记录', 'data_fields': ['id', 'weight_kg', 'note', 'old_record', 'new_record', 'bmi'],
            'depends_on_external': False, 'order': 0
    },
    {
            'category': '体重',     'wake_word': '改某日体重',     'desc': '按日期修改某天的体重记录',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-weight-update --date <YYYY-MM-DD> --weight <kg> --chain "1.定位→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「改某日体重」。\n\n我要按日期改某天的体重记录。改完后请给我看:命中条数、改前/改后对比。完成后给 1 句话总结,不需要过多文字解释。\n\n日期(YYYY-MM-DD):____\n新体重(kg):____\n新备注:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_update_by_date', 'name': '改某日体重', 'subfunction': '改体重记录', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-weight-update --date <YYYY-MM-DD> --weight <kg> --chain "1.定位→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改某日体重」。\n\n我要按日期改某天的体重记录。改完后请给我看:命中条数、改前/改后对比。完成后给 1 句话总结,不需要过多文字解释。\n\n日期(YYYY-MM-DD):____\n新体重(kg):____\n新备注:____',
            'user_intent': '按日期修改某天的体重记录', 'data_fields': ['date', 'hit_count', 'old_record', 'new_record', 'weight_kg', 'note'],
            'depends_on_external': False, 'order': 1
    },
    {
            'category': '体重',     'wake_word': '删体重记录',     'desc': '删除一条体重记录',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-weight-delete --id <ID> --chain "1.定位→2.快照→3.删除→4.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「删体重记录」。\n\n我要删一条体重记录。删除后请给我看:确认回执(含被删记录的内容)。完成后给 1 句话总结,不需要过多文字解释。\n\n要删的记录(最近一条/日期/编号):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_delete', 'name': '删体重记录', 'subfunction': '改体重记录', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-weight-delete --id <ID> --chain "1.定位→2.快照→3.删除→4.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「删体重记录」。\n\n我要删一条体重记录。删除后请给我看:确认回执(含被删记录的内容)。完成后给 1 句话总结,不需要过多文字解释。\n\n要删的记录(最近一条/日期/编号):____',
            'user_intent': '删除一条体重记录', 'data_fields': ['id', 'snapshot', 'date', 'weight_kg', 'confirm'],
            'depends_on_external': False, 'order': 2
    },
    {
            'category': '体重',     'wake_word': '删某日体重',     'desc': '删除某一天的体重记录',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-weight-delete --date <YYYY-MM-DD> --chain "1.定位→2.快照→3.删除→4.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「删某日体重」。\n\n我要删某一天的全部体重记录。删除后请给我看:删除条数、日期。完成后给 1 句话总结,不需要过多文字解释。\n\n日期(YYYY-MM-DD):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_delete_by_date', 'name': '删某日体重', 'subfunction': '改体重记录', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-weight-delete --date <YYYY-MM-DD> --chain "1.定位→2.快照→3.删除→4.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「删某日体重」。\n\n我要删某一天的全部体重记录。删除后请给我看:删除条数、日期。完成后给 1 句话总结,不需要过多文字解释。\n\n日期(YYYY-MM-DD):____',
            'user_intent': '删除某一天的体重记录', 'data_fields': ['date', 'deleted_count', 'snapshot', 'confirm'],
            'depends_on_external': False, 'order': 3
    },
    {
            'category': '体重',     'wake_word': '批量删体重',     'desc': '按日期范围批量删除体重记录',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-weight-delete --start <S> --end <E> --chain "1.定位→2.快照→3.删除→4.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「批量删体重」。\n\n我要按日期范围批量删除体重记录。删除后请给我看:时间范围、删除条数。完成后给 1 句话总结,不需要过多文字解释。\n\n起止日期(YYYY-MM-DD):____ ~ ____'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_delete_batch', 'name': '批量删体重', 'subfunction': '改体重记录', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-weight-delete --start <S> --end <E> --chain "1.定位→2.快照→3.删除→4.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「批量删体重」。\n\n我要按日期范围批量删除体重记录。删除后请给我看:时间范围、删除条数。完成后给 1 句话总结,不需要过多文字解释。\n\n起止日期(YYYY-MM-DD):____ ~ ____',
            'user_intent': '按日期范围批量删除体重记录', 'data_fields': ['start', 'end', 'deleted_count', 'snapshot', 'confirm'],
            'depends_on_external': False, 'order': 4
    },
    {
            'category': '体重',     'wake_word': '看本周体重',     'desc': '看本周自然周的体重明细',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode history --week current', 'text': '请你加载技能 卡路里,执行唤醒词「看本周体重」。\n\n我想看本周(自然周,周一开始)的体重明细:每日记录表格 + 周均值 + 周净变化 + 一句话。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_detail_week', 'name': '看本周体重', 'subfunction': '看体重明细', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode history --week current', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看本周体重」。\n\n我想看本周(自然周,周一开始)的体重明细:每日记录表格 + 周均值 + 周净变化 + 一句话。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看本周自然周的体重明细', 'data_fields': ['week', 'items', 'avg', 'net_change', 'summary'],
            'depends_on_external': False, 'order': 0
    },
    {
            'category': '体重',     'wake_word': '看上周体重',     'desc': '看上周体重明细并与本周对比',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode history --week last', 'text': '请你加载技能 卡路里,执行唤醒词「看上周体重」。\n\n我想看上周(自然周)的体重明细:每日记录表格 + 周均值 + 周净变化,并和本周对比一下。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_detail_last_week', 'name': '看上周体重', 'subfunction': '看体重明细', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode history --week last', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看上周体重」。\n\n我想看上周(自然周)的体重明细:每日记录表格 + 周均值 + 周净变化,并和本周对比一下。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看上周体重明细并与本周对比', 'data_fields': ['week', 'items', 'avg', 'net_change', 'vs_this_week'],
            'depends_on_external': False, 'order': 1
    },
    {
            'category': '体重',     'wake_word': '看本月体重',     'desc': '看本月自然月的体重明细',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode history --month current', 'text': '请你加载技能 卡路里,执行唤醒词「看本月体重」。\n\n我想看本月(自然月)的体重明细:每日记录表格 + 月均值 + 月净变化 + 一句话。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_detail_month', 'name': '看本月体重', 'subfunction': '看体重明细', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode history --month current', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看本月体重」。\n\n我想看本月(自然月)的体重明细:每日记录表格 + 月均值 + 月净变化 + 一句话。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看本月自然月的体重明细', 'data_fields': ['month', 'items', 'avg', 'net_change', 'summary'],
            'depends_on_external': False, 'order': 2
    },
    {
            'category': '体重',     'wake_word': '看上月体重',     'desc': '看上个月体重明细并与本月对比',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode history --month last', 'text': '请你加载技能 卡路里,执行唤醒词「看上月体重」。\n\n我想看上个月(自然月)的体重明细:每日记录表格 + 月均值 + 月净变化,并和本月对比一下。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_detail_last_month', 'name': '看上月体重', 'subfunction': '看体重明细', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode history --month last', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看上月体重」。\n\n我想看上个月(自然月)的体重明细:每日记录表格 + 月均值 + 月净变化,并和本月对比一下。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看上个月体重明细并与本月对比', 'data_fields': ['month', 'items', 'avg', 'net_change', 'vs_this_month'],
            'depends_on_external': False, 'order': 3
    },
    {
            'category': '体重',     'wake_word': '看最近 7 天体重',     'desc': '看最近 7 天的体重明细',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode history --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「看最近 7 天体重」。\n\n我想看最近 7 天(滚动)的体重明细:每日记录表格 + 均值 + 净变化 + 一句话。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_detail_7d', 'name': '看最近 7 天体重', 'subfunction': '看体重明细', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode history --days 7', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看最近 7 天体重」。\n\n我想看最近 7 天(滚动)的体重明细:每日记录表格 + 均值 + 净变化 + 一句话。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看最近 7 天的体重明细', 'data_fields': ['days', 'items', 'avg', 'net_change', 'summary'],
            'depends_on_external': False, 'order': 4
    },
    {
            'category': '体重',     'wake_word': '看最近 90 天体重',     'desc': '看最近 90 天的体重明细(每周一行)',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode history --days 90', 'text': '请你加载技能 卡路里,执行唤醒词「看最近 90 天体重」。\n\n我想看最近 90 天的体重明细:按每周一行降采样显示 + 均值/净变化 + 一句话。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_detail_90d', 'name': '看最近 90 天体重', 'subfunction': '看体重明细', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode history --days 90', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看最近 90 天体重」。\n\n我想看最近 90 天的体重明细:按每周一行降采样显示 + 均值/净变化 + 一句话。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看最近 90 天的体重明细(每周一行)', 'data_fields': ['days', 'items', 'avg', 'net_change', 'summary'],
            'depends_on_external': False, 'order': 5
    },
    {
            'category': '体重',     'wake_word': '看某段时间体重',     'desc': '看自定义时间段的体重明细',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode history --start <S> --end <E>', 'text': '请你加载技能 卡路里,执行唤醒词「看某段时间体重」。\n\n我想看某段时间(自定义起止日期)的体重明细:每日记录表格 + 区间统计(均值/净变化)+ 一句话。完成后给 1 句话总结,不需要过多文字解释。\n\n起止日期(YYYY-MM-DD):____ ~ ____'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_detail_range', 'name': '看某段时间体重', 'subfunction': '看体重明细', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode history --start <S> --end <E>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看某段时间体重」。\n\n我想看某段时间(自定义起止日期)的体重明细:每日记录表格 + 区间统计(均值/净变化)+ 一句话。完成后给 1 句话总结,不需要过多文字解释。\n\n起止日期(YYYY-MM-DD):____ ~ ____',
            'user_intent': '看自定义时间段的体重明细', 'data_fields': ['start', 'end', 'items', 'avg', 'net_change', 'summary'],
            'depends_on_external': False, 'order': 6
    },
    {
            'category': '体重',     'wake_word': '看体重曲线',     'desc': '看默认 30 天的体重曲线',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode trend --days 30', 'text': '请你加载技能 卡路里,执行唤醒词「看体重曲线」。\n\n我想看体重曲线(默认最近 30 天):折线图 + KPI(当前体重/区间起始/区间结束/区间变化/日均速率/趋势方向)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_curve', 'name': '看体重曲线', 'subfunction': '看体重曲线', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode trend --days 30', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重曲线」。\n\n我想看体重曲线(默认最近 30 天):折线图 + KPI(当前体重/区间起始/区间结束/区间变化/日均速率/趋势方向)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看默认 30 天的体重曲线', 'data_fields': ['days', 'items', 'current', 'delta', 'daily_rate', 'trend'],
            'depends_on_external': False, 'order': 0
    },
    {
            'category': '体重',     'wake_word': '看体重曲线（带目标）',     'desc': '看体重曲线并叠加目标线',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode trend --days 30 --show-target', 'text': '请你加载技能 卡路里,执行唤醒词「看体重曲线（带目标）」。\n\n我想看最近 30 天的体重曲线,并把我的目标体重画成目标线:折线图 + 目标线 + 当前距目标的差距 + KPI(当前/变化/速率/趋势)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_curve_target', 'name': '看体重曲线（带目标）', 'subfunction': '看体重曲线', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode trend --days 30 --show-target', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重曲线（带目标）」。\n\n我想看最近 30 天的体重曲线,并把我的目标体重画成目标线:折线图 + 目标线 + 当前距目标的差距 + KPI(当前/变化/速率/趋势)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看体重曲线并叠加目标线', 'data_fields': ['days', 'items', 'target', 'goal_diff', 'current', 'delta', 'daily_rate'],
            'depends_on_external': False, 'order': 1
    },
    {
            'category': '体重',     'wake_word': '看体重曲线（带里程碑）',     'desc': '看体重曲线并标注里程碑点',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode trend --days 30 --show-milestones', 'text': '请你加载技能 卡路里,执行唤醒词「看体重曲线（带里程碑）」。\n\n我想看最近 30 天的体重曲线,并在上面标出里程碑点(如减重 5kg/10kg 达成的那天):折线图 + 里程碑点 + 达成日期 + KPI。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_curve_milestone', 'name': '看体重曲线（带里程碑）', 'subfunction': '看体重曲线', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode trend --days 30 --show-milestones', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重曲线（带里程碑）」。\n\n我想看最近 30 天的体重曲线,并在上面标出里程碑点(如减重 5kg/10kg 达成的那天):折线图 + 里程碑点 + 达成日期 + KPI。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看体重曲线并标注里程碑点', 'data_fields': ['days', 'items', 'milestones', 'current', 'delta', 'daily_rate'],
            'depends_on_external': False, 'order': 2
    },
    {
            'category': '体重',     'wake_word': '看体重曲线（带异常点）',     'desc': '看体重曲线并标注异常点',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode trend --days 30 --show-anomalies', 'text': '请你加载技能 卡路里,执行唤醒词「看体重曲线（带异常点）」。\n\n我想看最近 30 天的体重曲线,并标出异常点(与正常波动偏差较大的记录):折线图 + 异常点红圈标注 + 异常点说明 + KPI。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_curve_anomaly', 'name': '看体重曲线（带异常点）', 'subfunction': '看体重曲线', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode trend --days 30 --show-anomalies', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重曲线（带异常点）」。\n\n我想看最近 30 天的体重曲线,并标出异常点(与正常波动偏差较大的记录):折线图 + 异常点红圈标注 + 异常点说明 + KPI。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看体重曲线并标注异常点', 'data_fields': ['days', 'items', 'anomalies', 'current', 'delta', 'daily_rate'],
            'depends_on_external': False, 'order': 3
    },
    {
            'category': '体重',     'wake_word': '看本月体重曲线',     'desc': '看本月自然月的体重曲线',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode trend --month current', 'text': '请你加载技能 卡路里,执行唤醒词「看本月体重曲线」。\n\n我想看本月(自然月)的体重曲线:折线图 + KPI(当前/起止/变化/速率/趋势)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_curve_month', 'name': '看本月体重曲线', 'subfunction': '看体重曲线', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode trend --month current', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看本月体重曲线」。\n\n我想看本月(自然月)的体重曲线:折线图 + KPI(当前/起止/变化/速率/趋势)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看本月自然月的体重曲线', 'data_fields': ['month', 'items', 'current', 'delta', 'daily_rate', 'trend'],
            'depends_on_external': False, 'order': 4
    },
    {
            'category': '体重',     'wake_word': '看上月体重曲线',     'desc': '看上个月自然月的体重曲线',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode trend --month last', 'text': '请你加载技能 卡路里,执行唤醒词「看上月体重曲线」。\n\n我想看上个月(自然月)的体重曲线:折线图 + KPI(当前/起止/变化/速率/趋势)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_curve_last_month', 'name': '看上月体重曲线', 'subfunction': '看体重曲线', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode trend --month last', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看上月体重曲线」。\n\n我想看上个月(自然月)的体重曲线:折线图 + KPI(当前/起止/变化/速率/趋势)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看上个月自然月的体重曲线', 'data_fields': ['month', 'items', 'current', 'delta', 'daily_rate', 'trend'],
            'depends_on_external': False, 'order': 5
    },
    {
            'category': '体重',     'wake_word': '看最近 90 天体重曲线',     'desc': '看最近 90 天的体重曲线',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode trend --days 90', 'text': '请你加载技能 卡路里,执行唤醒词「看最近 90 天体重曲线」。\n\n我想看最近 90 天的体重曲线(每 3 天降采样显示):折线图 + KPI(当前/起止/变化/速率/趋势)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_curve_90d', 'name': '看最近 90 天体重曲线', 'subfunction': '看体重曲线', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode trend --days 90', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看最近 90 天体重曲线」。\n\n我想看最近 90 天的体重曲线(每 3 天降采样显示):折线图 + KPI(当前/起止/变化/速率/趋势)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看最近 90 天的体重曲线', 'data_fields': ['days', 'items', 'current', 'delta', 'daily_rate', 'trend'],
            'depends_on_external': False, 'order': 6
    },
    {
            'category': '体重',     'wake_word': '看最近 180 天体重曲线',     'desc': '看最近 180 天的体重曲线',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode trend --days 180', 'text': '请你加载技能 卡路里,执行唤醒词「看最近 180 天体重曲线」。\n\n我想看最近 180 天的体重曲线(每周降采样显示):折线图 + KPI(当前/起止/变化/速率/趋势)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_curve_180d', 'name': '看最近 180 天体重曲线', 'subfunction': '看体重曲线', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode trend --days 180', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看最近 180 天体重曲线」。\n\n我想看最近 180 天的体重曲线(每周降采样显示):折线图 + KPI(当前/起止/变化/速率/趋势)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看最近 180 天的体重曲线', 'data_fields': ['days', 'items', 'current', 'delta', 'daily_rate', 'trend'],
            'depends_on_external': False, 'order': 7
    },
    {
            'category': '体重',     'wake_word': '看最近 365 天体重曲线',     'desc': '看最近 365 天的体重曲线',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode trend --days 365', 'text': '请你加载技能 卡路里,执行唤醒词「看最近 365 天体重曲线」。\n\n我想看最近 365 天的体重曲线(每月降采样显示):折线图 + KPI(当前/起止/变化/速率/趋势)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_curve_365d', 'name': '看最近 365 天体重曲线', 'subfunction': '看体重曲线', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode trend --days 365', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看最近 365 天体重曲线」。\n\n我想看最近 365 天的体重曲线(每月降采样显示):折线图 + KPI(当前/起止/变化/速率/趋势)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看最近 365 天的体重曲线', 'data_fields': ['days', 'items', 'current', 'delta', 'daily_rate', 'trend'],
            'depends_on_external': False, 'order': 8
    },
    {
            'category': '体重',     'wake_word': '看某段时间体重曲线',     'desc': '看自定义时间段的体重曲线',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode trend --start <S> --end <E>', 'text': '请你加载技能 卡路里,执行唤醒词「看某段时间体重曲线」。\n\n我想看某段时间(自定义起止日期)的体重曲线,跨度大时自动降采样:折线图 + KPI(当前/起止/变化/速率/趋势)。完成后给 1 句话总结,不需要过多文字解释。\n\n起止日期(YYYY-MM-DD):____ ~ ____'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_curve_range', 'name': '看某段时间体重曲线', 'subfunction': '看体重曲线', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode trend --start <S> --end <E>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看某段时间体重曲线」。\n\n我想看某段时间(自定义起止日期)的体重曲线,跨度大时自动降采样:折线图 + KPI(当前/起止/变化/速率/趋势)。完成后给 1 句话总结,不需要过多文字解释。\n\n起止日期(YYYY-MM-DD):____ ~ ____',
            'user_intent': '看自定义时间段的体重曲线', 'data_fields': ['start', 'end', 'items', 'current', 'delta', 'daily_rate', 'trend'],
            'depends_on_external': False, 'order': 9
    },
    {
            'category': '体重',     'wake_word': '看体重稳不稳（增强版）',     'desc': '看最近 30 天体重波动是否稳定',
            'main_prompt': {
        'cli': 'python scripts/render_weight_volatility_v2.py', 'text': '请你加载技能 卡路里,执行唤醒词「看体重稳不稳（增强版）」。\n\n我想看最近 30 天我的体重稳不稳:3 项指标(日均波动/标准差/异常次数)+ 波动主图(带正常波动范围带)+ 异常点列表 + 一句话判断。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_vol', 'name': '看体重稳不稳（增强版）', 'subfunction': '看体重稳不稳', 'output_type': 'result',
            'html_template': 'templates/weight_volatility_v2.html', 'data_source': 'python scripts/render_weight_volatility_v2.py', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重稳不稳（增强版）」。\n\n我想看最近 30 天我的体重稳不稳:3 项指标(日均波动/标准差/异常次数)+ 波动主图(带正常波动范围带)+ 异常点列表 + 一句话判断。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看最近 30 天体重波动是否稳定', 'data_fields': ['std', 'avg_daily_delta', 'anomaly_count', 'points', 'anomalies', 'baseline'],
            'depends_on_external': False, 'order': 0
    },
    {
            'category': '体重',     'wake_word': '看本月波动',     'desc': '看本月自然月的体重波动',
            'main_prompt': {
        'cli': 'python scripts/render_weight_volatility_v2.py --start <月初> --end <月末>', 'text': '请你加载技能 卡路里,执行唤醒词「看本月波动」。\n\n我想看本月(自然月)体重波动:3 项指标(日均波动/标准差/异常次数)+ 波动主图 + 异常点列表 + 一句话判断。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_vol_month', 'name': '看本月波动', 'subfunction': '看体重稳不稳', 'output_type': 'result',
            'html_template': 'templates/weight_volatility_v2.html', 'data_source': 'python scripts/render_weight_volatility_v2.py --start <月初> --end <月末>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看本月波动」。\n\n我想看本月(自然月)体重波动:3 项指标(日均波动/标准差/异常次数)+ 波动主图 + 异常点列表 + 一句话判断。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看本月自然月的体重波动', 'data_fields': ['month', 'std', 'avg_daily_delta', 'anomaly_count', 'points', 'anomalies'],
            'depends_on_external': False, 'order': 1
    },
    {
            'category': '体重',     'wake_word': '看最近 90 天波动',     'desc': '看最近 90 天的体重波动',
            'main_prompt': {
        'cli': 'python scripts/render_weight_volatility_v2.py --days 90', 'text': '请你加载技能 卡路里,执行唤醒词「看最近 90 天波动」。\n\n我想看最近 90 天的体重波动(降采样显示):3 项指标(日均波动/标准差/异常次数)+ 波动主图 + 异常点列表 + 一句话判断。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_vol_90d', 'name': '看最近 90 天波动', 'subfunction': '看体重稳不稳', 'output_type': 'result',
            'html_template': 'templates/weight_volatility_v2.html', 'data_source': 'python scripts/render_weight_volatility_v2.py --days 90', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看最近 90 天波动」。\n\n我想看最近 90 天的体重波动(降采样显示):3 项指标(日均波动/标准差/异常次数)+ 波动主图 + 异常点列表 + 一句话判断。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看最近 90 天的体重波动', 'data_fields': ['days', 'std', 'avg_daily_delta', 'anomaly_count', 'points', 'anomalies'],
            'depends_on_external': False, 'order': 2
    },
    {
            'category': '体重',     'wake_word': '看最近 180 天波动',     'desc': '看最近 180 天的体重波动',
            'main_prompt': {
        'cli': 'python scripts/render_weight_volatility_v2.py --days 180', 'text': '请你加载技能 卡路里,执行唤醒词「看最近 180 天波动」。\n\n我想看最近 180 天的体重波动(降采样显示):3 项指标(日均波动/标准差/异常次数)+ 波动主图 + 异常点列表 + 一句话判断。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_vol_180d', 'name': '看最近 180 天波动', 'subfunction': '看体重稳不稳', 'output_type': 'result',
            'html_template': 'templates/weight_volatility_v2.html', 'data_source': 'python scripts/render_weight_volatility_v2.py --days 180', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看最近 180 天波动」。\n\n我想看最近 180 天的体重波动(降采样显示):3 项指标(日均波动/标准差/异常次数)+ 波动主图 + 异常点列表 + 一句话判断。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看最近 180 天的体重波动', 'data_fields': ['days', 'std', 'avg_daily_delta', 'anomaly_count', 'points', 'anomalies'],
            'depends_on_external': False, 'order': 3
    },
    {
            'category': '体重',     'wake_word': '看波动异常点',     'desc': '只看体重波动中的异常点',
            'main_prompt': {
        'cli': 'python scripts/render_weight_volatility_v2.py --view anomalies-only', 'text': '请你加载技能 卡路里,执行唤醒词「看波动异常点」。\n\n我想只看体重波动中的异常点:异常点列表(日期/体重/偏差幅度/偏离方向)+ 可能原因 + 一句话。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_vol_anomalies', 'name': '看波动异常点', 'subfunction': '看体重稳不稳', 'output_type': 'result',
            'html_template': 'templates/weight_volatility_v2.html', 'data_source': 'python scripts/render_weight_volatility_v2.py --view anomalies-only', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看波动异常点」。\n\n我想只看体重波动中的异常点:异常点列表(日期/体重/偏差幅度/偏离方向)+ 可能原因 + 一句话。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '只看体重波动中的异常点', 'data_fields': ['anomalies', 'reasons', 'summary'],
            'depends_on_external': False, 'order': 4
    },
    {
            'category': '体重',     'wake_word': '看「有备注」的体重记录',     'desc': '看带备注的体重记录及备注分类',
            'main_prompt': {
        'cli': 'python scripts/render_weight_history.py --mode notes --days 30', 'text': '请你加载技能 卡路里,执行唤醒词「看「有备注」的体重记录」。\n\n我想看所有带备注的体重记录:表格(日期/体重/备注/与前后均值对比)+ 备注分类分布(如 晨起空腹/运动后/睡前 各有多少条)+ 一句话。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_notes', 'name': '看「有备注」的体重记录', 'subfunction': '看体重备注', 'output_type': 'result',
            'html_template': 'templates/weight_history.html', 'data_source': 'python scripts/render_weight_history.py --mode notes --days 30', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看「有备注」的体重记录」。\n\n我想看所有带备注的体重记录:表格(日期/体重/备注/与前后均值对比)+ 备注分类分布(如 晨起空腹/运动后/睡前 各有多少条)+ 一句话。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看带备注的体重记录及备注分类', 'data_fields': ['items', 'note_tags', 'tag_distribution', 'summary'],
            'depends_on_external': False, 'order': 0
    },
    {
            'category': '体重',     'wake_word': '对比体重：最近 30 天 vs 之前 30 天',     'desc': '对比最近 30 天与之前 30 天的体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario a1 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：最近 30 天 vs 之前 30 天」。\n\n我想对比最近 30 天和之前 30 天两段体重。请给我看:两段各自的均值/起始体重/终止体重/段内变化/段内波动 + 两段差值(Δkg)/变化方向/速率差(g/天)/速度判断(快了/慢了/持平)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_30d', 'name': '对比体重：最近 30 天 vs 之前 30 天', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario a1 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：最近 30 天 vs 之前 30 天」。\n\n我想对比最近 30 天和之前 30 天两段体重。请给我看:两段各自的均值/起始体重/终止体重/段内变化/段内波动 + 两段差值(Δkg)/变化方向/速率差(g/天)/速度判断(快了/慢了/持平)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '对比最近 30 天与之前 30 天的体重', 'data_fields': ['seg1', 'seg2', 'avg', 'delta_kg', 'rate_diff', 'speed_judge', 'volatility'],
            'depends_on_external': False, 'order': 0
    },
    {
            'category': '体重',     'wake_word': '对比体重：自定义两段时间',     'desc': '自定义两段时间对比体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario a2 --start-a <S1> --end-a <E1> --start-b <S2> --end-b <E2> --chain "1.识别→2.读DB→3.对比→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：自定义两段时间」。\n\n我想自定义两段日期对比体重。请给我看:两段各自的均值/起始体重/终止体重/段内变化/段内波动 + 两段差值(Δkg)/变化方向/速率差(g/天)/速度判断。完成后给 1 句话总结,不需要过多文字解释。\n\n第一段起止(YYYY-MM-DD):____ ~ ____\n第二段起止(YYYY-MM-DD):____ ~ ____'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_custom', 'name': '对比体重：自定义两段时间', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario a2 --start-a <S1> --end-a <E1> --start-b <S2> --end-b <E2> --chain "1.识别→2.读DB→3.对比→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：自定义两段时间」。\n\n我想自定义两段日期对比体重。请给我看:两段各自的均值/起始体重/终止体重/段内变化/段内波动 + 两段差值(Δkg)/变化方向/速率差(g/天)/速度判断。完成后给 1 句话总结,不需要过多文字解释。\n\n第一段起止(YYYY-MM-DD):____ ~ ____\n第二段起止(YYYY-MM-DD):____ ~ ____',
            'user_intent': '自定义两段时间对比体重', 'data_fields': ['seg1', 'seg2', 'avg', 'delta_kg', 'rate_diff', 'speed_judge', 'volatility'],
            'depends_on_external': False, 'order': 1
    },
    {
            'category': '体重',     'wake_word': '对比体重：本周 vs 上周',     'desc': '对比本周与上周的体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario a3 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：本周 vs 上周」。\n\n我想对比本周和上周的体重(自然周对齐)。请给我看:两段各自的均值/起始/终止/段内变化/段内波动 + 差值(Δkg)/方向/速率差/速度判断。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_week', 'name': '对比体重：本周 vs 上周', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario a3 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：本周 vs 上周」。\n\n我想对比本周和上周的体重(自然周对齐)。请给我看:两段各自的均值/起始/终止/段内变化/段内波动 + 差值(Δkg)/方向/速率差/速度判断。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '对比本周与上周的体重', 'data_fields': ['seg1', 'seg2', 'sample_ok', 'avg', 'delta_kg', 'rate_diff', 'speed_judge'],
            'depends_on_external': False, 'order': 2
    },
    {
            'category': '体重',     'wake_word': '对比体重：本月 vs 上月',     'desc': '对比本月与上月的体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario a4 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：本月 vs 上月」。\n\n我想对比本月和上月的体重(自然月对齐)。请给我看:两段各自的均值/起始/终止/段内变化/段内波动 + 差值(Δkg)/方向/速率差/速度判断。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_month', 'name': '对比体重：本月 vs 上月', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario a4 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：本月 vs 上月」。\n\n我想对比本月和上月的体重(自然月对齐)。请给我看:两段各自的均值/起始/终止/段内变化/段内波动 + 差值(Δkg)/方向/速率差/速度判断。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '对比本月与上月的体重', 'data_fields': ['seg1', 'seg2', 'avg', 'delta_kg', 'rate_diff', 'speed_judge', 'volatility'],
            'depends_on_external': False, 'order': 3
    },
    {
            'category': '体重',     'wake_word': '对比体重：近 N 天 vs 上一个 N 天',     'desc': '对比近 N 天与之前同样 N 天的体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario a5 --n <N> --chain "1.识别→2.读DB→3.对比→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：近 N 天 vs 上一个 N 天」。\n\n我想对比最近 N 天和之前同样 N 天(滚动窗口)的体重,N 由我指定。请给我看:两段各自的均值/起始/终止/段内变化/段内波动 + 差值(Δkg)/方向/速率差/速度判断。完成后给 1 句话总结,不需要过多文字解释。\n\nN(天数):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_ndays', 'name': '对比体重：近 N 天 vs 上一个 N 天', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario a5 --n <N> --chain "1.识别→2.读DB→3.对比→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：近 N 天 vs 上一个 N 天」。\n\n我想对比最近 N 天和之前同样 N 天(滚动窗口)的体重,N 由我指定。请给我看:两段各自的均值/起始/终止/段内变化/段内波动 + 差值(Δkg)/方向/速率差/速度判断。完成后给 1 句话总结,不需要过多文字解释。\n\nN(天数):____',
            'user_intent': '对比近 N 天与之前同样 N 天的体重', 'data_fields': ['n_days', 'seg1', 'seg2', 'avg', 'delta_kg', 'rate_diff', 'speed_judge'],
            'depends_on_external': False, 'order': 4
    },
    {
            'category': '体重',     'wake_word': '对比体重：今天 vs 一年前今天',     'desc': '对比今天与一年前同一天的体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario a6 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：今天 vs 一年前今天」。\n\n我想对比今天的体重和一年前同一天的体重。请给我看:当前体重/一年前同日体重/差值(Δkg)/方向/一年变化/容差命中说明/一年内区间段均值。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_1y', 'name': '对比体重：今天 vs 一年前今天', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario a6 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：今天 vs 一年前今天」。\n\n我想对比今天的体重和一年前同一天的体重。请给我看:当前体重/一年前同日体重/差值(Δkg)/方向/一年变化/容差命中说明/一年内区间段均值。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '对比今天与一年前同一天的体重', 'data_fields': ['current', 'year_ago', 'delta_kg', 'direction', 'tolerance_hit', 'period_avg'],
            'depends_on_external': False, 'order': 5
    },
    {
            'category': '体重',     'wake_word': '对比体重：今天 vs 半年前今天',     'desc': '对比今天与半年前同一天的体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario a7 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：今天 vs 半年前今天」。\n\n我想对比今天的体重和半年前同一天的体重。请给我看:当前体重/半年前同日体重/差值(Δkg)/方向/容差命中说明/半年内区间段均值。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_6m', 'name': '对比体重：今天 vs 半年前今天', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario a7 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：今天 vs 半年前今天」。\n\n我想对比今天的体重和半年前同一天的体重。请给我看:当前体重/半年前同日体重/差值(Δkg)/方向/容差命中说明/半年内区间段均值。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '对比今天与半年前同一天的体重', 'data_fields': ['current', 'past', 'delta_kg', 'direction', 'tolerance_hit', 'period_avg'],
            'depends_on_external': False, 'order': 6
    },
    {
            'category': '体重',     'wake_word': '对比体重：今天 vs 三月前今天',     'desc': '对比今天与三月前同一天的体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario a8 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：今天 vs 三月前今天」。\n\n我想对比今天的体重和三个月前同一天的体重。请给我看:当前体重/三月前同日体重/差值(Δkg)/方向/容差命中说明/三个月内区间段均值。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_3m', 'name': '对比体重：今天 vs 三月前今天', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario a8 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：今天 vs 三月前今天」。\n\n我想对比今天的体重和三个月前同一天的体重。请给我看:当前体重/三月前同日体重/差值(Δkg)/方向/容差命中说明/三个月内区间段均值。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '对比今天与三月前同一天的体重', 'data_fields': ['current', 'past', 'delta_kg', 'direction', 'tolerance_hit', 'period_avg'],
            'depends_on_external': False, 'order': 7
    },
    {
            'category': '体重',     'wake_word': '对比体重：当前 vs 目标体重',     'desc': '对比当前体重与目标体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario b1 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：当前 vs 目标体重」。\n\n我想对比当前体重和目标体重。请给我看:当前体重/目标体重/差值(Δkg)/已完成百分比/预计达成日期(按当前速率推算)/当前 BMI/目标 BMI/是否达标判断。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_target', 'name': '对比体重：当前 vs 目标体重', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario b1 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：当前 vs 目标体重」。\n\n我想对比当前体重和目标体重。请给我看:当前体重/目标体重/差值(Δkg)/已完成百分比/预计达成日期(按当前速率推算)/当前 BMI/目标 BMI/是否达标判断。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '对比当前体重与目标体重', 'data_fields': ['current', 'target', 'delta_kg', 'pct_done', 'eta', 'current_bmi', 'target_bmi', 'verdict'],
            'depends_on_external': False, 'order': 8
    },
    {
            'category': '体重',     'wake_word': '对比体重：当前 vs 平台期首日',     'desc': '对比当前体重与最近一次平台期首日',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario b8 --chain "1.识别→2.读DB→3.平台期识别→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：当前 vs 平台期首日」。\n\n请自动识别我最近一次平台期,并对比当前体重和平台期首日的体重。请给我看:当前体重/平台期首日体重/平台期持续天数/突破平台期后的变化(Δkg)/这是我第几次平台期/历史平台期平均突破耗时。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_plateau', 'name': '对比体重：当前 vs 平台期首日', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario b8 --chain "1.识别→2.读DB→3.平台期识别→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：当前 vs 平台期首日」。\n\n请自动识别我最近一次平台期,并对比当前体重和平台期首日的体重。请给我看:当前体重/平台期首日体重/平台期持续天数/突破平台期后的变化(Δkg)/这是我第几次平台期/历史平台期平均突破耗时。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '对比当前体重与最近一次平台期首日', 'data_fields': ['current', 'plateau_start', 'plateau_days', 'delta_after', 'plateau_count', 'avg_break_days'],
            'depends_on_external': False, 'order': 9
    },
    {
            'category': '体重',     'wake_word': '对比体重：当前 vs 历史最低',     'desc': '对比当前体重与历史最低',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario e1 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：当前 vs 历史最低」。\n\n请自动定位我历史最低的体重并和当前对比。请给我看:当前体重/历史最低体重 + 日期/差值(Δ)/距历史最低的天数/一句话。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_min', 'name': '对比体重：当前 vs 历史最低', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario e1 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：当前 vs 历史最低」。\n\n请自动定位我历史最低的体重并和当前对比。请给我看:当前体重/历史最低体重 + 日期/差值(Δ)/距历史最低的天数/一句话。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '对比当前体重与历史最低', 'data_fields': ['current', 'min_kg', 'min_date', 'delta_kg', 'days_since', 'summary'],
            'depends_on_external': False, 'order': 10
    },
    {
            'category': '体重',     'wake_word': '对比体重：当前 vs 历史最高',     'desc': '对比当前体重与历史最高',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario e2 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：当前 vs 历史最高」。\n\n请自动定位我历史最高的体重并和当前对比。请给我看:当前体重/历史最高体重 + 日期/已下降多少(Δ)/下降速率/一句话。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_max', 'name': '对比体重：当前 vs 历史最高', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario e2 --chain "1.识别→2.读DB→3.对比→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：当前 vs 历史最高」。\n\n请自动定位我历史最高的体重并和当前对比。请给我看:当前体重/历史最高体重 + 日期/已下降多少(Δ)/下降速率/一句话。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '对比当前体重与历史最高', 'data_fields': ['current', 'max_kg', 'max_date', 'delta_kg', 'rate', 'summary'],
            'depends_on_external': False, 'order': 11
    },
    {
            'category': '体重',     'wake_word': '对比体重：减重 5kg 那天 vs 今天',     'desc': '对比减重 5kg 达成日与今天的体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario e3 --delta 5 --chain "1.识别→2.读DB→3.反查里程碑→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：减重 5kg 那天 vs 今天」。\n\n请反查我减重 5kg 达成的那一天,和今天对比。请给我看:当前体重/减重 5kg 那天的体重与日期/从那天到今天的用时/期间速率/这段轨迹。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_5kg', 'name': '对比体重：减重 5kg 那天 vs 今天', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario e3 --delta 5 --chain "1.识别→2.读DB→3.反查里程碑→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：减重 5kg 那天 vs 今天」。\n\n请反查我减重 5kg 达成的那一天,和今天对比。请给我看:当前体重/减重 5kg 那天的体重与日期/从那天到今天的用时/期间速率/这段轨迹。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '对比减重 5kg 达成日与今天的体重', 'data_fields': ['current', 'milestone_kg', 'milestone_date', 'elapsed_days', 'rate', 'trajectory'],
            'depends_on_external': False, 'order': 12
    },
    {
            'category': '体重',     'wake_word': '对比体重：减重 10kg 那天 vs 今天',     'desc': '对比减重 10kg 达成日与今天的体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario e3 --delta 10 --chain "1.识别→2.读DB→3.反查里程碑→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：减重 10kg 那天 vs 今天」。\n\n请反查我减重 10kg 达成的那一天,和今天对比。请给我看:当前体重/减重 10kg 那天的体重与日期/从那天到今天的用时/期间速率/这段轨迹。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_10kg', 'name': '对比体重：减重 10kg 那天 vs 今天', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario e3 --delta 10 --chain "1.识别→2.读DB→3.反查里程碑→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：减重 10kg 那天 vs 今天」。\n\n请反查我减重 10kg 达成的那一天,和今天对比。请给我看:当前体重/减重 10kg 那天的体重与日期/从那天到今天的用时/期间速率/这段轨迹。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '对比减重 10kg 达成日与今天的体重', 'data_fields': ['current', 'milestone_kg', 'milestone_date', 'elapsed_days', 'rate', 'trajectory'],
            'depends_on_external': False, 'order': 13
    },
    {
            'category': '体重',     'wake_word': '对比体重：当前 vs 入夏最低',     'desc': '对比当前体重与入夏最低',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario e5 --chain "1.识别→2.读DB→3.季节定位→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：当前 vs 入夏最低」。\n\n请定位我今年夏天的体重最低点并和当前对比。请给我看:当前体重/入夏最低体重 + 日期/差值(Δ)/距那天多少天。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_summer', 'name': '对比体重：当前 vs 入夏最低', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario e5 --chain "1.识别→2.读DB→3.季节定位→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：当前 vs 入夏最低」。\n\n请定位我今年夏天的体重最低点并和当前对比。请给我看:当前体重/入夏最低体重 + 日期/差值(Δ)/距那天多少天。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '对比当前体重与入夏最低', 'data_fields': ['current', 'season_min_kg', 'season_min_date', 'delta_kg', 'days_since'],
            'depends_on_external': False, 'order': 14
    },
    {
            'category': '体重',     'wake_word': '对比体重：当前 vs 入冬最低',     'desc': '对比当前体重与入冬最低',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario e6 --chain "1.识别→2.读DB→3.季节定位→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：当前 vs 入冬最低」。\n\n请定位我最近一个冬天的体重最低点并和当前对比。请给我看:当前体重/入冬最低体重 + 日期/差值(Δ)/距那天多少天。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_winter', 'name': '对比体重：当前 vs 入冬最低', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario e6 --chain "1.识别→2.读DB→3.季节定位→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：当前 vs 入冬最低」。\n\n请定位我最近一个冬天的体重最低点并和当前对比。请给我看:当前体重/入冬最低体重 + 日期/差值(Δ)/距那天多少天。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '对比当前体重与入冬最低', 'data_fields': ['current', 'season_min_kg', 'season_min_date', 'delta_kg', 'days_since'],
            'depends_on_external': False, 'order': 15
    },
    {
            'category': '体重',     'wake_word': '对比体重：运动多 vs 运动少的两个月',     'desc': '对比运动最多与最少两个月的体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario c5 --chain "1.识别→2.读DB→3.选极端月→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：运动多 vs 运动少的两个月」。\n\n请自动选出我运动量最高和最低的两个月对比体重。请给我看:运动最高月 vs 最低月的各自体重均值/段内变化/运动总量/差值(Δkg)/速率差,并附上两个月的摄入热量与睡眠时长作对照。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_exercise', 'name': '对比体重：运动多 vs 运动少的两个月', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario c5 --chain "1.识别→2.读DB→3.选极端月→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：运动多 vs 运动少的两个月」。\n\n请自动选出我运动量最高和最低的两个月对比体重。请给我看:运动最高月 vs 最低月的各自体重均值/段内变化/运动总量/差值(Δkg)/速率差,并附上两个月的摄入热量与睡眠时长作对照。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '对比运动最多与最少两个月的体重', 'data_fields': ['high_month', 'low_month', 'avg', 'delta_kg', 'rate_diff', 'calories', 'sleep', 'exercise_total'],
            'depends_on_external': False, 'order': 16
    },
    {
            'category': '体重',     'wake_word': '对比体重：工作日 vs 周末',     'desc': '对比工作日与周末的体重',
            'main_prompt': {
        'cli': 'python scripts/render_weight_compare.py --scenario d4 --chain "1.识别→2.读DB→3.周内聚合→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比体重：工作日 vs 周末」。\n\n请把最近一周的体重按 工作日(周一至周五)和 周末(周六周日)分组对比。请给我看:工作日均值/周末均值/差值(Δkg)/工作日波动 vs 周末波动/一致率。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_cmp_weekend', 'name': '对比体重：工作日 vs 周末', 'subfunction': '对比体重', 'output_type': 'result',
            'html_template': 'templates/weight_compare.html', 'data_source': 'python scripts/render_weight_compare.py --scenario d4 --chain "1.识别→2.读DB→3.周内聚合→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体重：工作日 vs 周末」。\n\n请把最近一周的体重按 工作日(周一至周五)和 周末(周六周日)分组对比。请给我看:工作日均值/周末均值/差值(Δkg)/工作日波动 vs 周末波动/一致率。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '对比工作日与周末的体重', 'data_fields': ['weekday_avg', 'weekend_avg', 'delta_kg', 'weekday_vol', 'weekend_vol', 'agreement_rate'],
            'depends_on_external': False, 'order': 17
    },
    {
            'category': '体重',     'wake_word': '看体重总览',     'desc': '看体重综合总览',
            'main_prompt': {
        'cli': 'python scripts/render_weight_dashboard.py --view overview --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看体重总览」。\n\n我想看体重综合总览:5 项指标(当前体重/近 7 天变化/距历史最低/距目标/波动等级)+ 最近 7 天趋势小图 + 一句话。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_overview', 'name': '看体重总览', 'subfunction': '体重复盘', 'output_type': 'result',
            'html_template': 'templates/weight_dashboard.html', 'data_source': 'python scripts/render_weight_dashboard.py --view overview --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重总览」。\n\n我想看体重综合总览:5 项指标(当前体重/近 7 天变化/距历史最低/距目标/波动等级)+ 最近 7 天趋势小图 + 一句话。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看体重综合总览', 'data_fields': ['current', 'delta_7d', 'diff_min', 'diff_target', 'vol_level', 'trend_7d', 'summary'],
            'depends_on_external': False, 'order': 0
    },
    {
            'category': '体重',     'wake_word': '体重复盘（本周）',     'desc': '复盘本周的体重变化',
            'main_prompt': {
        'cli': 'python scripts/render_weight_review.py --type week --chain "1.识别→2.读DB→3.复盘→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「体重复盘（本周）」。\n\n我想看本周的体重复盘:本周变化(Δkg)/周均值/与上周对比 + 趋势图 + 一句话。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_review_week', 'name': '体重复盘（本周）', 'subfunction': '体重复盘', 'output_type': 'result',
            'html_template': 'templates/weight_review.html', 'data_source': 'python scripts/render_weight_review.py --type week --chain "1.识别→2.读DB→3.复盘→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「体重复盘（本周）」。\n\n我想看本周的体重复盘:本周变化(Δkg)/周均值/与上周对比 + 趋势图 + 一句话。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '复盘本周的体重变化', 'data_fields': ['delta_kg', 'avg', 'vs_last_period', 'trend', 'summary'],
            'depends_on_external': False, 'order': 1
    },
    {
            'category': '体重',     'wake_word': '体重复盘（本月）',     'desc': '复盘本月的体重变化',
            'main_prompt': {
        'cli': 'python scripts/render_weight_review.py --type month --chain "1.识别→2.读DB→3.复盘→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「体重复盘（本月）」。\n\n我想看本月的体重复盘:本月变化(Δkg)/月均值/与上月对比 + 趋势图 + 一句话。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_review_month', 'name': '体重复盘（本月）', 'subfunction': '体重复盘', 'output_type': 'result',
            'html_template': 'templates/weight_review.html', 'data_source': 'python scripts/render_weight_review.py --type month --chain "1.识别→2.读DB→3.复盘→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「体重复盘（本月）」。\n\n我想看本月的体重复盘:本月变化(Δkg)/月均值/与上月对比 + 趋势图 + 一句话。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '复盘本月的体重变化', 'data_fields': ['delta_kg', 'avg', 'vs_last_period', 'trend', 'summary'],
            'depends_on_external': False, 'order': 2
    },
    {
            'category': '体重',     'wake_word': '体重复盘（最近 90 天）',     'desc': '复盘最近 90 天的体重变化',
            'main_prompt': {
        'cli': 'python scripts/render_weight_review.py --type 90d --chain "1.识别→2.读DB→3.复盘→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「体重复盘（最近 90 天）」。\n\n我想看最近 90 天的体重复盘:期间变化(Δkg)/均值/与上一段 90 天对比 + 趋势图 + 一句话。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_review_90d', 'name': '体重复盘（最近 90 天）', 'subfunction': '体重复盘', 'output_type': 'result',
            'html_template': 'templates/weight_review.html', 'data_source': 'python scripts/render_weight_review.py --type 90d --chain "1.识别→2.读DB→3.复盘→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「体重复盘（最近 90 天）」。\n\n我想看最近 90 天的体重复盘:期间变化(Δkg)/均值/与上一段 90 天对比 + 趋势图 + 一句话。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '复盘最近 90 天的体重变化', 'data_fields': ['delta_kg', 'avg', 'vs_last_period', 'trend', 'summary'],
            'depends_on_external': False, 'order': 3
    },
    {
            'category': '体重',     'wake_word': '体重复盘（今年）',     'desc': '复盘今年的体重变化',
            'main_prompt': {
        'cli': 'python scripts/render_weight_review.py --type year --chain "1.识别→2.读DB→3.复盘→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「体重复盘（今年）」。\n\n我想看今年的体重复盘:全年变化(Δkg)/年度均值/月度趋势图 + 一句话。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_review_year', 'name': '体重复盘（今年）', 'subfunction': '体重复盘', 'output_type': 'result',
            'html_template': 'templates/weight_review.html', 'data_source': 'python scripts/render_weight_review.py --type year --chain "1.识别→2.读DB→3.复盘→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「体重复盘（今年）」。\n\n我想看今年的体重复盘:全年变化(Δkg)/年度均值/月度趋势图 + 一句话。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '复盘今年的体重变化', 'data_fields': ['delta_kg', 'avg', 'monthly_trend', 'summary'],
            'depends_on_external': False, 'order': 4
    },
    {
            'category': '体重',     'wake_word': '体重复盘（自定义时间）',     'desc': '复盘自定义时间段的体重变化',
            'main_prompt': {
        'cli': 'python scripts/render_weight_review.py --start <S> --end <E> --chain "1.识别→2.读DB→3.复盘→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「体重复盘（自定义时间）」。\n\n我想看某段时间的体重复盘(自定义起止日期):期间变化(Δkg)/均值/与上一段等长区间对比 + 趋势图 + 一句话。完成后给 1 句话总结,不需要过多文字解释。\n\n起止日期(YYYY-MM-DD):____ ~ ____'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_review_range', 'name': '体重复盘（自定义时间）', 'subfunction': '体重复盘', 'output_type': 'result',
            'html_template': 'templates/weight_review.html', 'data_source': 'python scripts/render_weight_review.py --start <S> --end <E> --chain "1.识别→2.读DB→3.复盘→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「体重复盘（自定义时间）」。\n\n我想看某段时间的体重复盘(自定义起止日期):期间变化(Δkg)/均值/与上一段等长区间对比 + 趋势图 + 一句话。完成后给 1 句话总结,不需要过多文字解释。\n\n起止日期(YYYY-MM-DD):____ ~ ____',
            'user_intent': '复盘自定义时间段的体重变化', 'data_fields': ['start', 'end', 'delta_kg', 'avg', 'vs_last_period', 'trend', 'summary'],
            'depends_on_external': False, 'order': 5
    },
    {
            'category': '体重',     'wake_word': '看里程碑回溯',     'desc': '看历史达成的体重里程碑',
            'main_prompt': {
        'cli': 'python scripts/render_weight_review.py --type milestones --chain "1.识别→2.读DB→3.回溯→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「看里程碑回溯」。\n\n我想看所有达成过的体重里程碑:表格(里程碑名/日期/体重/用时)+ 一句话。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'w_milestones', 'name': '看里程碑回溯', 'subfunction': '体重复盘', 'output_type': 'result',
            'html_template': 'templates/weight_review.html', 'data_source': 'python scripts/render_weight_review.py --type milestones --chain "1.识别→2.读DB→3.回溯→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看里程碑回溯」。\n\n我想看所有达成过的体重里程碑:表格(里程碑名/日期/体重/用时)+ 一句话。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看历史达成的体重里程碑', 'data_fields': ['milestones', 'summary'],
            'depends_on_external': False, 'order': 6
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
            'category': '健身计划',     'wake_word': '看本周计划',     'desc': '本周训练日历(7 天表 + 完成度)',
            'main_prompt': {
        'cli': 'python scripts/render_workout_plan.py --week <N>', 'text': '请你加载技能 卡路里,执行唤醒词「看本周计划」。\n\n我想看本周的训练日历:7 天表格(周一至周日,含休息日行)、每天的训练时段和动作,以及本周整体完成度。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_view_this_week', 'name': '看本周计划', 'subfunction': '看训练计划', 'output_type': 'result',
            'html_template': 'templates/workout_plan_view.html', 'data_source': 'python scripts/render_workout_plan.py --week <N>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看本周计划」。\n\n我想看本周的训练日历:7 天表格(周一至周日,含休息日行)、每天的训练时段和动作,以及本周整体完成度。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '我想看本周的训练日历和完成度', 'data_fields': ["week_number", "days", "sessions", "movements", "completion_rate"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '健身计划',     'wake_word': '看下周计划',     'desc': '下周训练日历预览(含待练状态)',
            'main_prompt': {
        'cli': 'python scripts/render_workout_plan.py --week <N+1>', 'text': '请你加载技能 卡路里,执行唤醒词「看下周计划」。\n\n我想看下周的训练日历:7 天表格(周一至周日,含休息日行)、每天的训练时段和动作,以及下周整体完成度(还没练的显示为待练)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_view_next_week', 'name': '看下周计划', 'subfunction': '看训练计划', 'output_type': 'result',
            'html_template': 'templates/workout_plan_view.html', 'data_source': 'python scripts/render_workout_plan.py --week <N+1>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看下周计划」。\n\n我想看下周的训练日历:7 天表格(周一至周日,含休息日行)、每天的训练时段和动作,以及下周整体完成度(还没练的显示为待练)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '我想预览下周的训练安排', 'data_fields': ["week_number", "days", "sessions", "movements", "completion_rate"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '健身计划',     'wake_word': '看上周计划',     'desc': '上周训练日历 + 完成率回顾',
            'main_prompt': {
        'cli': 'python scripts/render_workout_plan.py --week <N-1>', 'text': '请你加载技能 卡路里,执行唤醒词「看上周计划」。\n\n我想看上周的训练日历:7 天表格(周一至周日,含休息日行)、每天的训练时段和动作,以及上周完成率回顾(哪些练了、哪些漏了)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_view_last_week', 'name': '看上周计划', 'subfunction': '看训练计划', 'output_type': 'result',
            'html_template': 'templates/workout_plan_view.html', 'data_source': 'python scripts/render_workout_plan.py --week <N-1>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看上周计划」。\n\n我想看上周的训练日历:7 天表格(周一至周日,含休息日行)、每天的训练时段和动作,以及上周完成率回顾(哪些练了、哪些漏了)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '我想回顾上周的训练安排和完成率', 'data_fields': ["week_number", "days", "sessions", "movements", "completion_rate"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '健身计划',     'wake_word': '看指定周计划',     'desc': '指定周次训练日历',
            'main_prompt': {
        'cli': 'python scripts/render_workout_plan.py --week <N>', 'text': '请你加载技能 卡路里,执行唤醒词「看指定周计划」。\n\n我想看某一周的训练日历:7 天表格(周一至周日,含休息日行)、每天的训练时段和动作,以及该周完成度。完成后给 1 句话总结,不需要过多文字解释。\n\n周次(如第 3 周):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_view_week', 'name': '看指定周计划', 'subfunction': '看训练计划', 'output_type': 'result',
            'html_template': 'templates/workout_plan_view.html', 'data_source': 'python scripts/render_workout_plan.py --week <N>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看指定周计划」。\n\n我想看某一周的训练日历:7 天表格(周一至周日,含休息日行)、每天的训练时段和动作,以及该周完成度。完成后给 1 句话总结,不需要过多文字解释。\n\n周次(如第 3 周):____',
            'user_intent': '我想查看指定周次的训练安排', 'data_fields': ["week_number", "days", "sessions", "movements", "completion_rate"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '健身计划',     'wake_word': '看今天练什么',     'desc': '今日动作/组数/重量 + 实时完成进度',
            'main_prompt': {
        'cli': 'python scripts/render_workout_plan.py --today', 'text': '请你加载技能 卡路里,执行唤醒词「看今天练什么」。\n\n我想看今天要练的动作(动作/组数/重量),以及每个动作的实时完成情况:已完成、剩余组数、完成百分比。如果今天休息或计划还没开始,请明确告诉我。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_view_today', 'name': '看今天练什么', 'subfunction': '看训练计划', 'output_type': 'result',
            'html_template': 'templates/workout_plan_view.html', 'data_source': 'python scripts/render_workout_plan.py --today', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看今天练什么」。\n\n我想看今天要练的动作(动作/组数/重量),以及每个动作的实时完成情况:已完成、剩余组数、完成百分比。如果今天休息或计划还没开始,请明确告诉我。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '我想看今天练什么以及练到哪了', 'data_fields': ["sessions", "movements", "sets_done", "sets_remaining", "completion_rate"],
            'depends_on_external': False, 'order': 4},
    {
            'category': '健身计划',     'wake_word': '看计划概览',     'desc': '计划总览 KPI + 每周完成率列表',
            'main_prompt': {
        'cli': 'python scripts/render_workout_plan.py --overview', 'text': '请你加载技能 卡路里,执行唤醒词「看计划概览」。\n\n我想看整个健身计划的概览:总周数、整体完成率、训练日数、动作总数几个关键数字,以及每周完成率列表。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_overview', 'name': '看计划概览', 'subfunction': '看训练计划', 'output_type': 'result',
            'html_template': 'templates/workout_plan_view.html', 'data_source': 'python scripts/render_workout_plan.py --overview', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看计划概览」。\n\n我想看整个健身计划的概览:总周数、整体完成率、训练日数、动作总数几个关键数字,以及每周完成率列表。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '我想看训练计划的总体概览和每周完成情况', 'data_fields': ["total_weeks", "completion_rate", "training_days", "total_movements", "weekly_rates"],
            'depends_on_external': False, 'order': 5},
    {
            'category': '健身计划',     'wake_word': '看计划 vs 实际',     'desc': '计划 vs 实际对比(完成度/偏差/动作级表)',
            'main_prompt': {
        'cli': 'python scripts/render_workout_plan.py --vs-actual --start <D1> --end <D2>', 'text': '请你加载技能 卡路里,执行唤醒词「看计划 vs 实际」。\n\n我想对比一段时间里计划和实际完成:整体完成度、偏差,以及动作级对比表(动作/计划组数/实际组数/偏差百分比)。完成后给 1 句话总结,不需要过多文字解释。\n\n时间范围(默认本周,可给日期):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_vs_actual', 'name': '看计划 vs 实际', 'subfunction': '看训练计划', 'output_type': 'result',
            'html_template': 'templates/workout_plan_view.html', 'data_source': 'python scripts/render_workout_plan.py --vs-actual --start <D1> --end <D2>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看计划 vs 实际」。\n\n我想对比一段时间里计划和实际完成:整体完成度、偏差,以及动作级对比表(动作/计划组数/实际组数/偏差百分比)。完成后给 1 句话总结,不需要过多文字解释。\n\n时间范围(默认本周,可给日期):____',
            'user_intent': '我想对比计划训练量和实际完成量的差距', 'data_fields': ["completion_rate", "deviation", "movement_rows", "start_date", "end_date"],
            'depends_on_external': False, 'order': 6},
    {
            'category': '健身计划',     'wake_word': '定训练计划',     'desc': 'AI 采访式创建计划(预览确认 → 写入回执)',
            'main_prompt': {
        'cli': 'plan_generator.write_plan', 'text': '请你加载技能 卡路里,执行唤醒词「定训练计划」。\n\n我想制定一份新的健身计划,根据我的目标和训练情况来安排(标题/总周数/起始日)。如果我没说清楚我的目标和训练情况,请先问我。请先给我看完整计划预览,我确认后再保存,保存后给我回执。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_set', 'name': '定训练计划', 'subfunction': '定训练计划', 'output_type': 'receipt',
            'html_template': 'templates/plan_builder_wizard.html', 'data_source': 'plan_generator.write_plan', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「定训练计划」。\n\n我想制定一份新的健身计划,根据我的目标和训练情况来安排(标题/总周数/起始日)。如果我没说清楚我的目标和训练情况,请先问我。请先给我看完整计划预览,我确认后再保存,保存后给我回执。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '我想根据我的目标和情况定制一份训练计划', 'data_fields': ["goal", "experience", "frequency", "target_parts", "title", "total_weeks", "start_date"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '健身计划',     'wake_word': '复制训练计划',     'desc': '复制整计划或某周作为模板',
            'main_prompt': {
        'cli': 'plan_generator.copy_week', 'text': '请你加载技能 卡路里,执行唤醒词「复制训练计划」。\n\n我想把现有训练计划复制一份作为模板(可以复制整个计划或某一周)。请告诉我复制了哪些内容、新计划/新周的标题或周次。完成后给 1 句话总结,不需要过多文字解释。\n\n要复制的周次(选填,空=整个计划):____\n新标题(选填):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_copy', 'name': '复制训练计划', 'subfunction': '定训练计划', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'plan_generator.copy_week', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「复制训练计划」。\n\n我想把现有训练计划复制一份作为模板(可以复制整个计划或某一周)。请告诉我复制了哪些内容、新计划/新周的标题或周次。完成后给 1 句话总结,不需要过多文字解释。\n\n要复制的周次(选填,空=整个计划):____\n新标题(选填):____',
            'user_intent': '我想复制一份训练计划作为新模板', 'data_fields': ["copied_weeks", "new_title", "source_week"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '健身计划',     'wake_word': '定休息日',     'desc': '标记某天为休息日(或取消)',
            'main_prompt': {
        'cli': 'plan_generator.update_session', 'text': '请你加载技能 卡路里,执行唤醒词「定休息日」。\n\n我想把某一天的训练标记为休息日(或取消休息)。完成后给我设置回执,显示改动的是哪天、改前和改后的状态。完成后给 1 句话总结,不需要过多文字解释。\n\n日期或周次+星期:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_set_rest', 'name': '定休息日', 'subfunction': '定训练计划', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'plan_generator.update_session', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「定休息日」。\n\n我想把某一天的训练标记为休息日(或取消休息)。完成后给我设置回执,显示改动的是哪天、改前和改后的状态。完成后给 1 句话总结,不需要过多文字解释。\n\n日期或周次+星期:____',
            'user_intent': '我想把某天标记为休息日', 'data_fields': ["date", "is_rest_day", "before", "after"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '健身计划',     'wake_word': '加训练动作',     'desc': '给某天/时段加动作(组数/重量)',
            'main_prompt': {
        'cli': 'plan_generator.add_session', 'text': '请你加载技能 卡路里,执行唤醒词「加训练动作」。\n\n我想给计划里的某一天或某个训练时段加训练动作,包括动作名、组数和重量。如果计划是每周循环的,告诉我加在哪一周,不说就所有周都加。完成后给我回执,显示新增的动作/组数/重量。完成后给 1 句话总结,不需要过多文字解释。\n\n加到哪天(如 周三):____\n加到第几周(选填,空=所有周):____\n时段(选填):____\n动作名:____\n组数:____\n重量(kg,选填):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_add_movement', 'name': '加训练动作', 'subfunction': '定训练计划', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'plan_generator.add_session', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「加训练动作」。\n\n我想给计划里的某一天或某个训练时段加训练动作,包括动作名、组数和重量。如果计划是每周循环的,告诉我加在哪一周,不说就所有周都加。完成后给我回执,显示新增的动作/组数/重量。完成后给 1 句话总结,不需要过多文字解释。\n\n加到哪天(如 周三):____\n加到第几周(选填,空=所有周):____\n时段(选填):____\n动作名:____\n组数:____\n重量(kg,选填):____',
            'user_intent': '我想给训练计划加一个新动作', 'data_fields': ["week_number", "day_of_week", "session_label", "movement", "sets", "weight_kg"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '健身计划',     'wake_word': '定一周计划',     'desc': '快速设置一周 7 天安排',
            'main_prompt': {
        'cli': 'plan_generator.write_plan', 'text': '请你加载技能 卡路里,执行唤醒词「定一周计划」。\n\n我想快速设置某一周的训练安排,告诉我这周每天(周一至周日)练什么或休息,只想练其中几天也没关系,空着的天按休息处理。完成后给我设置回执,显示这 7 天的安排。完成后给 1 句话总结,不需要过多文字解释。\n\n第几周(默认本周):____\n一周安排(如:周一胸、周三腿,没说的天按休息):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_set_week', 'name': '定一周计划', 'subfunction': '定训练计划', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'plan_generator.write_plan', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「定一周计划」。\n\n我想快速设置某一周的训练安排,告诉我这周每天(周一至周日)练什么或休息,只想练其中几天也没关系,空着的天按休息处理。完成后给我设置回执,显示这 7 天的安排。完成后给 1 句话总结,不需要过多文字解释。\n\n第几周(默认本周):____\n一周安排(如:周一胸、周三腿,没说的天按休息):____',
            'user_intent': '我想快速设置一周七天的训练安排', 'data_fields': ["week_number", "day_schedule", "rest_days"],
            'depends_on_external': False, 'order': 4},
    {
            'category': '健身计划',     'wake_word': '改训练计划',     'desc': '改计划配置字段(改前/改后 + 影响)',
            'main_prompt': {
        'cli': 'plan_generator.update_config', 'text': '请你加载技能 卡路里,执行唤醒词「改训练计划」。\n\n我想改训练计划的某个字段(如标题、总周数、开始日期、描述)。改完给我看改前/改后对比,并提示影响(如改开始日期会影响周次计算)。完成后给 1 句话总结,不需要过多文字解释。\n\n要改的字段(标题/总周数/开始日期/描述,可改多个):____\n新值:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_update', 'name': '改训练计划', 'subfunction': '改训练计划', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'plan_generator.update_config', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改训练计划」。\n\n我想改训练计划的某个字段(如标题、总周数、开始日期、描述)。改完给我看改前/改后对比,并提示影响(如改开始日期会影响周次计算)。完成后给 1 句话总结,不需要过多文字解释。\n\n要改的字段(标题/总周数/开始日期/描述,可改多个):____\n新值:____',
            'user_intent': '我想修改训练计划的某个配置字段', 'data_fields': ["field", "before", "after"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '健身计划',     'wake_word': '改某天训练',     'desc': '改某天训练安排(改前/改后)',
            'main_prompt': {
        'cli': 'plan_generator.update_session', 'text': '请你加载技能 卡路里,执行唤醒词「改某天训练」。\n\n我想改某一天的训练安排(时段、动作、组数等)。改完给我看改了哪些、改前和改后。完成后给 1 句话总结,不需要过多文字解释。\n\n日期:____\n要改的内容:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_update_day', 'name': '改某天训练', 'subfunction': '改训练计划', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'plan_generator.update_session', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改某天训练」。\n\n我想改某一天的训练安排(时段、动作、组数等)。改完给我看改了哪些、改前和改后。完成后给 1 句话总结,不需要过多文字解释。\n\n日期:____\n要改的内容:____',
            'user_intent': '我想修改某一天的训练安排', 'data_fields': ["date", "field", "before", "after"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '健身计划',     'wake_word': '删某天训练',     'desc': '删某天训练(快照确认 → 回执)',
            'main_prompt': {
        'cli': 'plan_generator.delete_session', 'text': '请你加载技能 卡路里,执行唤醒词「删某天训练」。\n\n我想删掉某一天的训练安排(或某天的某个训练时段)。删除前先让我确认,确认后删除,给我确认回执。完成后给 1 句话总结,不需要过多文字解释。\n\n日期:____\n要删的时段(选填,空=删整天):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_delete_day', 'name': '删某天训练', 'subfunction': '改训练计划', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'plan_generator.delete_session', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「删某天训练」。\n\n我想删掉某一天的训练安排(或某天的某个训练时段)。删除前先让我确认,确认后删除,给我确认回执。完成后给 1 句话总结,不需要过多文字解释。\n\n日期:____\n要删的时段(选填,空=删整天):____',
            'user_intent': '我想删除某天的训练安排', 'data_fields': ["date", "snapshot", "deleted_sessions"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '健身计划',     'wake_word': '改动作',     'desc': '替换动作(改前/改后 + 组数变化)',
            'main_prompt': {
        'cli': 'plan_generator.update_session', 'text': '请你加载技能 卡路里,执行唤醒词「改动作」。\n\n我想把计划里的某个动作换成另一个动作(或改它的组数)。如果计划是每周循环的,告诉我要改哪一周,不说就所有周都改。改完给我看改前/改后动作和组数变化。完成后给 1 句话总结,不需要过多文字解释。\n\n要改的周(选填,空=所有周):____\n原动作:____\n新动作:____\n组数(选填):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_update_movement', 'name': '改动作', 'subfunction': '改训练计划', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'plan_generator.update_session', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改动作」。\n\n我想把计划里的某个动作换成另一个动作(或改它的组数)。如果计划是每周循环的,告诉我要改哪一周,不说就所有周都改。改完给我看改前/改后动作和组数变化。完成后给 1 句话总结,不需要过多文字解释。\n\n要改的周(选填,空=所有周):____\n原动作:____\n新动作:____\n组数(选填):____',
            'user_intent': '我想替换计划里的某个动作', 'data_fields': ["date", "old_movement", "new_movement", "sets_before", "sets_after"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '健身计划',     'wake_word': '撤销训练计划',     'desc': '删除整个计划(确认 → 回执 + 提示)',
            'main_prompt': {
        'cli': 'plan_generator.delete_plan', 'text': '请你加载技能 卡路里,执行唤醒词「撤销训练计划」。\n\n我想删除整个训练计划(所有周次和配置)。删除前先让我确认,确认后删除,给我删除回执和提示(删除后如何重新制定)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_delete', 'name': '撤销训练计划', 'subfunction': '改训练计划', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'plan_generator.delete_plan', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「撤销训练计划」。\n\n我想删除整个训练计划(所有周次和配置)。删除前先让我确认,确认后删除,给我删除回执和提示(删除后如何重新制定)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '我想删除整个训练计划', 'data_fields': ["plan_summary", "deleted_config", "deleted_rows"],
            'depends_on_external': False, 'order': 4},
    {
            'category': '健身计划',     'wake_word': '落地训练',     'desc': '4 步落地(补计划/记心愿/推送/回写)',
            'main_prompt': {
        'cli': 'python scripts/sync_plan.py --days 1', 'text': '请你加载技能 卡路里,执行唤醒词「落地训练」。\n\n我想把某天的训练计划真正落地执行:补计划到日历、记心愿、推送到训记、拉取训记实绩 4 步全流程,逐动作确认实际做的重量和组数。给我看 4 步进度和每步结果(已补计划/已记心愿/已推送/已回写),以及完成度。完成后给 1 句话总结,不需要过多文字解释。\n\n日期(默认今天):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_execute', 'name': '落地训练', 'subfunction': '落地训练', 'output_type': 'process',
            'html_template': 'templates/process_progress.html', 'data_source': 'python scripts/sync_plan.py --days 1', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「落地训练」。\n\n我想把某天的训练计划真正落地执行:补计划到日历、记心愿、推送到训记、拉取训记实绩 4 步全流程,逐动作确认实际做的重量和组数。给我看 4 步进度和每步结果(已补计划/已记心愿/已推送/已回写),以及完成度。完成后给 1 句话总结,不需要过多文字解释。\n\n日期(默认今天):____',
            'user_intent': '我想把某天的训练计划完整落地执行', 'data_fields': ["date", "step1_created", "step2_added", "step3_pushed", "step4_backfilled", "completion"],
            'depends_on_external': True, 'order': 0},
    {
            'category': '健身计划',     'wake_word': '落地到本周末',     'desc': '批量落地到本周末(跨天汇总)',
            'main_prompt': {
        'cli': 'python scripts/sync_plan.py --days <N>', 'text': '请你加载技能 卡路里,执行唤醒词「落地到本周末」。\n\n我想把从今天到周日所有训练日一次落地执行(补计划/记心愿/推训记/回写),如果今天已是周日就只落地今天。请给我看跨天列表、每一步的汇总(已补计划/已记心愿/已推送/已回写)和总完成度。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_execute_weekend', 'name': '落地到本周末', 'subfunction': '落地训练', 'output_type': 'process',
            'html_template': 'templates/process_progress.html', 'data_source': 'python scripts/sync_plan.py --days <N>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「落地到本周末」。\n\n我想把从今天到周日所有训练日一次落地执行(补计划/记心愿/推训记/回写),如果今天已是周日就只落地今天。请给我看跨天列表、每一步的汇总(已补计划/已记心愿/已推送/已回写)和总完成度。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '我想把本周剩余训练日批量落地', 'data_fields': ["days", "day_summaries", "step_totals", "completion"],
            'depends_on_external': True, 'order': 1},
    {
            'category': '健身计划',     'wake_word': '落地到本月底',     'desc': '批量落地到本月底(跨天汇总)',
            'main_prompt': {
        'cli': 'python scripts/sync_plan.py --days <N>', 'text': '请你加载技能 卡路里,执行唤醒词「落地到本月底」。\n\n我想把从今天到本月底所有训练日一次落地执行(补计划/记心愿/推训记/回写),如果今天已是月底就只落地今天。请给我看跨天列表、每一步的汇总(已补计划/已记心愿/已推送/已回写)和总完成度。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_execute_month', 'name': '落地到本月底', 'subfunction': '落地训练', 'output_type': 'process',
            'html_template': 'templates/process_progress.html', 'data_source': 'python scripts/sync_plan.py --days <N>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「落地到本月底」。\n\n我想把从今天到本月底所有训练日一次落地执行(补计划/记心愿/推训记/回写),如果今天已是月底就只落地今天。请给我看跨天列表、每一步的汇总(已补计划/已记心愿/已推送/已回写)和总完成度。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '我想把本月剩余训练日批量落地', 'data_fields': ["days", "day_summaries", "step_totals", "completion"],
            'depends_on_external': True, 'order': 2},
    {
            'category': '健身计划',     'wake_word': '同步到训记',     'desc': '推 plan 到训记(前置审计动作名)',
            'main_prompt': {
        'cli': 'python scripts/xunji_bridge.py push-plan --date <D>', 'text': '请你加载技能 卡路里,执行唤醒词「同步到训记」。\n\n我想把某天的训练计划推送到训记 App(落地流程里的训记推送这一步单独做)。推送前先检查计划里的动作名训记能否识别,有识别不了的先告诉我。完成后给我同步结果:推了几条、每条成功/失败、哪些动作名有问题。完成后给 1 句话总结,不需要过多文字解释。\n\n日期(默认今天):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_sync_xunji', 'name': '同步到训记', 'subfunction': '落地训练', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/xunji_bridge.py push-plan --date <D>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「同步到训记」。\n\n我想把某天的训练计划推送到训记 App(落地流程里的训记推送这一步单独做)。推送前先检查计划里的动作名训记能否识别,有识别不了的先告诉我。完成后给我同步结果:推了几条、每条成功/失败、哪些动作名有问题。完成后给 1 句话总结,不需要过多文字解释。\n\n日期(默认今天):____',
            'user_intent': '我想把训练计划推送到训记', 'data_fields': ["date", "pushed_count", "results", "unrecognized_movements"],
            'depends_on_external': True, 'order': 3},
    {
            'category': '健身计划',     'wake_word': '拉训记实绩',     'desc': '拉训记实绩回写 exercise_log',
            'main_prompt': {
        'cli': 'python scripts/xunji_bridge.py backfill --date <D>', 'text': '请你加载技能 卡路里,执行唤醒词「拉训记实绩」。\n\n我想把训记 App 里的实际训练数据拉回来,写进卡路里的运动记录(落地流程里的回写这一步单独做)。请给我看回写结果:新增几条、更新几条、跳过几条,以及有没有冲突需要处理。完成后给 1 句话总结,不需要过多文字解释。\n\n日期(默认今天):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_backfill_xunji', 'name': '拉训记实绩', 'subfunction': '落地训练', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/xunji_bridge.py backfill --date <D>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「拉训记实绩」。\n\n我想把训记 App 里的实际训练数据拉回来,写进卡路里的运动记录(落地流程里的回写这一步单独做)。请给我看回写结果:新增几条、更新几条、跳过几条,以及有没有冲突需要处理。完成后给 1 句话总结,不需要过多文字解释。\n\n日期(默认今天):____',
            'user_intent': '我想把训记里的实际训练拉回卡路里', 'data_fields': ["date", "inserted", "updated", "skipped", "conflicts"],
            'depends_on_external': True, 'order': 4},
    {
            'category': '健身计划',     'wake_word': '计划复盘（本周）',     'desc': '本周复盘(KPI + 趋势 + 上周对比)',
            'main_prompt': {
        'cli': 'python scripts/render_exercise_review_html.py --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「计划复盘（本周）」。\n\n我想复盘本周的训练:完成率、训练日数、消耗等关键数字,完成趋势,以及本周与上周的对比。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_review_week', 'name': '计划复盘（本周）', 'subfunction': '计划复盘', 'output_type': 'result',
            'html_template': 'templates/exercise_review.html', 'data_source': 'python scripts/render_exercise_review_html.py --days 7', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「计划复盘（本周）」。\n\n我想复盘本周的训练:完成率、训练日数、消耗等关键数字,完成趋势,以及本周与上周的对比。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '我想复盘本周训练完成情况', 'data_fields': ["completion_rate", "training_days", "calories_burned", "trend", "delta_vs_last_week"],
            'depends_on_external': False, 'order': 0},
    {
            'category': '健身计划',     'wake_word': '计划复盘（本月）',     'desc': '本月复盘(KPI + 趋势 + 上月对比)',
            'main_prompt': {
        'cli': 'python scripts/render_exercise_review_html.py --start <D1> --end <D2>', 'text': '请你加载技能 卡路里,执行唤醒词「计划复盘（本月）」。\n\n我想复盘本月的训练:完成率、训练日数、消耗等关键数字,完成趋势,以及本月与上月的对比。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_review_month', 'name': '计划复盘（本月）', 'subfunction': '计划复盘', 'output_type': 'result',
            'html_template': 'templates/exercise_review.html', 'data_source': 'python scripts/render_exercise_review_html.py --start <D1> --end <D2>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「计划复盘（本月）」。\n\n我想复盘本月的训练:完成率、训练日数、消耗等关键数字,完成趋势,以及本月与上月的对比。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '我想复盘本月训练完成情况', 'data_fields': ["completion_rate", "training_days", "calories_burned", "trend", "delta_vs_last_month"],
            'depends_on_external': False, 'order': 1},
    {
            'category': '健身计划',     'wake_word': '计划复盘（全部）',     'desc': '全部复盘(总完成率 + 高频动作)',
            'main_prompt': {
        'cli': 'python scripts/render_exercise_review_html.py --start <D1> --end <D2>', 'text': '请你加载技能 卡路里,执行唤醒词「计划复盘（全部）」。\n\n我想复盘整个训练计划:总完成率,以及做得最多的动作(高频动作)排名。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_review_all', 'name': '计划复盘（全部）', 'subfunction': '计划复盘', 'output_type': 'result',
            'html_template': 'templates/exercise_review.html', 'data_source': 'python scripts/render_exercise_review_html.py --start <D1> --end <D2>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「计划复盘（全部）」。\n\n我想复盘整个训练计划:总完成率,以及做得最多的动作(高频动作)排名。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '我想复盘整个训练计划的总完成率和高频动作', 'data_fields': ["total_completion_rate", "top_movements"],
            'depends_on_external': False, 'order': 2},
    {
            'category': '健身计划',     'wake_word': '看计划完成率',     'desc': '每周完成率折线趋势',
            'main_prompt': {
        'cli': 'python scripts/render_workout_plan.py --completion', 'text': '请你加载技能 卡路里,执行唤醒词「看计划完成率」。\n\n我想看训练计划的完成率趋势:每周完成率的折线图,能看出哪周完成得好、哪周掉下来了。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_completion_rate', 'name': '看计划完成率', 'subfunction': '计划复盘', 'output_type': 'result',
            'html_template': 'templates/workout_plan_view.html', 'data_source': 'python scripts/render_workout_plan.py --completion', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看计划完成率」。\n\n我想看训练计划的完成率趋势:每周完成率的折线图,能看出哪周完成得好、哪周掉下来了。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '我想看每周训练完成率的变化趋势', 'data_fields': ["weekly_completion", "trend"],
            'depends_on_external': False, 'order': 3},
    {
            'category': '健身计划',     'wake_word': '看未完成训练',     'desc': '漏练日期 + 应练动作列表',
            'main_prompt': {
        'cli': 'python scripts/render_workout_plan.py --missed --days <N>', 'text': '请你加载技能 卡路里,执行唤醒词「看未完成训练」。\n\n我想看哪些天的训练没完成(漏练):漏练的日期,以及那天本该练的动作列表。完成后给 1 句话总结,不需要过多文字解释。\n\n时间范围(默认最近 4 周):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_missed', 'name': '看未完成训练', 'subfunction': '计划复盘', 'output_type': 'result',
            'html_template': 'templates/workout_plan_view.html', 'data_source': 'python scripts/render_workout_plan.py --missed --days <N>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看未完成训练」。\n\n我想看哪些天的训练没完成(漏练):漏练的日期,以及那天本该练的动作列表。完成后给 1 句话总结,不需要过多文字解释。\n\n时间范围(默认最近 4 周):____',
            'user_intent': '我想看哪些训练日漏练了', 'data_fields': ["missed_dates", "planned_movements"],
            'depends_on_external': False, 'order': 4},
    {
            'category': '健身计划',     'wake_word': '看动作完成率',     'desc': '动作完成率 TOP 榜',
            'main_prompt': {
        'cli': 'python scripts/render_workout_plan.py --movement-rate --days <N>', 'text': '请你加载技能 卡路里,执行唤醒词「看动作完成率」。\n\n我想看每个动作的完成率排名:哪些动作完成得好、哪些经常没做。完成后给 1 句话总结,不需要过多文字解释。\n\n时间范围(默认最近 4 周):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_movement_rate', 'name': '看动作完成率', 'subfunction': '计划复盘', 'output_type': 'result',
            'html_template': 'templates/workout_plan_view.html', 'data_source': 'python scripts/render_workout_plan.py --movement-rate --days <N>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看动作完成率」。\n\n我想看每个动作的完成率排名:哪些动作完成得好、哪些经常没做。完成后给 1 句话总结,不需要过多文字解释。\n\n时间范围(默认最近 4 周):____',
            'user_intent': '我想看各动作的完成率排名', 'data_fields': ["movement_ranking", "completion_rate"],
            'depends_on_external': False, 'order': 5},
    {
            'category': '健身计划',     'wake_word': '扫禁忌',     'desc': '禁忌动作扫描(腰/膝/肩 + 替代建议)',
            'main_prompt': {
        'cli': 'python scripts/render_contraindication.py', 'text': '请你加载技能 卡路里,执行唤醒词「扫禁忌」。\n\n我想检查训练计划里有没有伤腰/膝/肩的禁忌动作(默认全身位,也可以指定部位)。请列出有风险的动作、原因,以及推荐的替代动作。完成后给 1 句话总结,不需要过多文字解释。\n\n部位(腰/膝/肩,选填,默认全部):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'plan_contraindication', 'name': '扫禁忌', 'subfunction': '安全检查', 'output_type': 'result',
            'html_template': 'templates/contraindication_report.html', 'data_source': 'python scripts/render_contraindication.py', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「扫禁忌」。\n\n我想检查训练计划里有没有伤腰/膝/肩的禁忌动作(默认全身位,也可以指定部位)。请列出有风险的动作、原因,以及推荐的替代动作。完成后给 1 句话总结,不需要过多文字解释。\n\n部位(腰/膝/肩,选填,默认全部):____',
            'user_intent': '我想检查训练计划里的禁忌动作', 'data_fields': ["part", "hits", "severity", "safe_variants"],
            'depends_on_external': False, 'order': 0},
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
        'cli': 'python scripts/render_goal_config.py --live --chain <思考链>', 'text': '请你加载技能 卡路里,执行唤醒词「定营养目标」。\n\n我想设每日 4 大宏量营养目标(热量/蛋白/碳水/脂肪)+ 饮水目标。若热量明显低于我的基础代谢(BMR),请提示我注意。完成后给 1 句话总结,不需要过多文字解释。\n\n我的目标数值(请按实际替换,不知道的可以空着):\n热量(卡):____\n蛋白(g):____\n碳水(g):____\n脂肪(g):____\n饮水(ml):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_set_nutrition', 'name': '定营养目标', 'subfunction': '定目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_config.html', 'data_source': 'python scripts/render_goal_config.py --live --chain <思考链>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「定营养目标」。\n\n我想设每日 4 大宏量营养目标(热量/蛋白/碳水/脂肪)+ 饮水目标。若热量明显低于我的基础代谢(BMR),请提示我注意。完成后给 1 句话总结,不需要过多文字解释。\n\n我的目标数值(请按实际替换,不知道的可以空着):\n热量(卡):____\n蛋白(g):____\n碳水(g):____\n脂肪(g):____\n饮水(ml):____',
            'user_intent': '设每日 4 项宏量营养目标', 'data_fields': ['calorie_goal', 'protein_goal', 'carbs_goal', 'fat_goal', 'water_goal'],
            'depends_on_external': False, 'order': 0},
    {
            'category': '目标管理',     'wake_word': '定营养目标(自动算)',     'desc': '按档案 + 策略自动算每日营养目标',
            'main_prompt': {
        'cli': 'python scripts/render_goal_recommend.py --profile <减脂/维持/增肌> --chain <思考链>', 'text': '请你加载技能 卡路里,执行唤醒词「定营养目标(自动算)」。\n\n想根据我的档案(身高/体重/年龄/活动量)+ 目标方向自动算出 4 项营养目标。若我未提供方向或档案信息缺失,请先询问补齐;若我已明确表达,直接计算,必要时做几句信息确认即可。完成后给 1 句话总结,不需要过多文字解释。\n\n我的目标方向(减脂 / 维持 / 增肌):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_set_nutrition_auto', 'name': '定营养目标(自动算)', 'subfunction': '定目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_recommend.html', 'data_source': 'python scripts/render_goal_recommend.py --profile <减脂/维持/增肌> --chain <思考链>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「定营养目标(自动算)」。\n\n想根据我的档案(身高/体重/年龄/活动量)+ 目标方向自动算出 4 项营养目标。若我未提供方向或档案信息缺失,请先询问补齐;若我已明确表达,直接计算,必要时做几句信息确认即可。完成后给 1 句话总结,不需要过多文字解释。\n\n我的目标方向(减脂 / 维持 / 增肌):____',
            'user_intent': '按档案 + 策略自动算每日营养目标', 'data_fields': ['tdee', 'recommend', 'weekly_rate', 'macros_4', 'basis', 'plan_reasons'],
            'depends_on_external': False, 'order': 1},
    {
            'category': '目标管理',     'wake_word': '定体重目标',     'desc': '设定体重目标值与可选截止日期',
            'main_prompt': {
        'cli': 'python scripts/render_goal_weight.py --mode basic --chain <思考链>', 'text': '请你加载技能 卡路里,执行唤醒词「定体重目标」。\n\n我想设定体重目标(目标 kg + 可选截止日期)。请显示我的当前体重、目标值、差值(Δkg)和建议速率。完成后给 1 句话总结,不需要过多文字解释。\n\n我的体重目标(kg):____\n截止日期(选填):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_set_weight', 'name': '定体重目标', 'subfunction': '定目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_weight.html', 'data_source': 'python scripts/render_goal_weight.py --mode basic --chain <思考链>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「定体重目标」。\n\n我想设定体重目标(目标 kg + 可选截止日期)。请显示我的当前体重、目标值、差值(Δkg)和建议速率。完成后给 1 句话总结,不需要过多文字解释。\n\n我的体重目标(kg):____\n截止日期(选填):____',
            'user_intent': '设定体重目标值与可选截止日期', 'data_fields': ['current_weight', 'target_weight', 'deadline', 'delta_kg', 'suggested_rate'],
            'depends_on_external': False, 'order': 2},
    {
            'category': '目标管理',     'wake_word': '定体重目标(自动算截止)',     'desc': '按速率推算截止日期的体重目标',
            'main_prompt': {
        'cli': 'python scripts/render_goal_weight.py --mode auto_deadline --chain <思考链>', 'text': '请你加载技能 卡路里,执行唤醒词「定体重目标(自动算截止)」。\n\n我想设定体重目标(目标 kg + 期望每周减重速率),由你自动推算合理截止日期,并校验速率是否合理(不超安全范围)。请显示我的当前体重、目标值、推算截止日期和速率校验结果。完成后给 1 句话总结,不需要过多文字解释。\n\n我的体重目标(kg):____\n期望每周减重速率(kg/周):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_set_weight_auto_deadline', 'name': '定体重目标(自动算截止)', 'subfunction': '定目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_weight.html', 'data_source': 'python scripts/render_goal_weight.py --mode auto_deadline --chain <思考链>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「定体重目标(自动算截止)」。\n\n我想设定体重目标(目标 kg + 期望每周减重速率),由你自动推算合理截止日期,并校验速率是否合理(不超安全范围)。请显示我的当前体重、目标值、推算截止日期和速率校验结果。完成后给 1 句话总结,不需要过多文字解释。\n\n我的体重目标(kg):____\n期望每周减重速率(kg/周):____',
            'user_intent': '按速率推算截止日期的体重目标', 'data_fields': ['current_weight', 'target_weight', 'est_deadline', 'rate_check'],
            'depends_on_external': False, 'order': 3},
    {
            'category': '目标管理',     'wake_word': '定体重目标(含起始日)',     'desc': '完整 setup 体重目标含起始日',
            'main_prompt': {
        'cli': 'python scripts/render_goal_weight.py --mode with_start --chain <思考链>', 'text': '请你加载技能 卡路里,执行唤醒词「定体重目标(含起始日)」。\n\n我想完整设定体重目标:目标 kg + 起始日 + 截止日 + 起点体重。请显示我的起始日、起点体重、当前体重、目标值、截止和差值。完成后给 1 句话总结,不需要过多文字解释。\n\n我的体重目标(kg):____\n起始日:____\n截止日期:____\n起点体重(kg):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_set_weight_with_start', 'name': '定体重目标(含起始日)', 'subfunction': '定目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_weight.html', 'data_source': 'python scripts/render_goal_weight.py --mode with_start --chain <思考链>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「定体重目标(含起始日)」。\n\n我想完整设定体重目标:目标 kg + 起始日 + 截止日 + 起点体重。请显示我的起始日、起点体重、当前体重、目标值、截止和差值。完成后给 1 句话总结,不需要过多文字解释。\n\n我的体重目标(kg):____\n起始日:____\n截止日期:____\n起点体重(kg):____',
            'user_intent': '完整 setup 体重目标含起始日', 'data_fields': ['weight_goal', 'goal_deadline', 'start_date', 'start_weight'],
            'depends_on_external': False, 'order': 4},
    {
            'category': '目标管理',     'wake_word': '定饮水目标',     'desc': '设每日饮水目标',
            'main_prompt': {
        'cli': 'python scripts/render_goal_config.py --live --water-only --chain <思考链>', 'text': '请你加载技能 卡路里,执行唤醒词「定饮水目标」。\n\n我想设定每天饮水目标(ml)。完成后给 1 句话总结,不需要过多文字解释。\n\n我的饮水目标(ml):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_set_water', 'name': '定饮水目标', 'subfunction': '定目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_config.html', 'data_source': 'python scripts/render_goal_config.py --live --water-only --chain <思考链>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「定饮水目标」。\n\n我想设定每天饮水目标(ml)。完成后给 1 句话总结,不需要过多文字解释。\n\n我的饮水目标(ml):____',
            'user_intent': '设每日饮水目标', 'data_fields': ['water_goal'],
            'depends_on_external': False, 'order': 5},
    {
            'category': '目标管理',     'wake_word': '定饮水目标(自动算)',     'desc': '按体重推算饮水目标推荐值',
            'main_prompt': {
        'cli': 'python scripts/render_goal_recommend.py --water-only --chain <思考链>', 'text': '请你加载技能 卡路里,执行唤醒词「定饮水目标(自动算)」。\n\n想按我的体重(ml/kg)自动推算饮水目标推荐值,并和旧目标对比。请显示计算依据、推荐值、旧值与新值对比。完成后给 1 句话总结,不需要过多文字解释。\n\n我的体重(kg,选填,默认取最新记录):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_set_water_auto', 'name': '定饮水目标(自动算)', 'subfunction': '定目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_recommend.html', 'data_source': 'python scripts/render_goal_recommend.py --water-only --chain <思考链>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「定饮水目标(自动算)」。\n\n想按我的体重(ml/kg)自动推算饮水目标推荐值,并和旧目标对比。请显示计算依据、推荐值、旧值与新值对比。完成后给 1 句话总结,不需要过多文字解释。\n\n我的体重(kg,选填,默认取最新记录):____',
            'user_intent': '按体重推算饮水目标推荐值', 'data_fields': ['weight_kg', 'season', 'recommended_water_ml'],
            'depends_on_external': False, 'order': 6},
    {
            'category': '目标管理',     'wake_word': '一键定全套目标',     'desc': '一键设定营养+体重+饮水全套目标',
            'main_prompt': {
        'cli': 'python scripts/render_goal_recommend.py --full-kit --profile <减脂/维持/增肌> --chain <思考链>', 'text': '请你加载技能 卡路里,执行唤醒词「一键定全套目标」。\n\n想一键设定 3 类目标(营养 + 体重 + 饮水),基于我的档案自动计算,先给我看每类目标值与依据说明,等我确认后再采纳。若我的档案(身高/年龄/活动量)未设置、无体重记录或信息缺失,请先询问补齐;若我已明确表达,直接计算,必要时做几句信息确认即可。完成后给 1 句话总结,不需要过多文字解释。\n\n我的目标方向(减脂 / 维持 / 增肌):____\n我的体重目标(kg,选填):____\n截止日期(选填):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_set_full_kit', 'name': '一键定全套目标', 'subfunction': '定目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_recommend.html', 'data_source': 'python scripts/render_goal_recommend.py --full-kit --profile <减脂/维持/增肌> --chain <思考链>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「一键定全套目标」。\n\n想一键设定 3 类目标(营养 + 体重 + 饮水),基于我的档案自动计算,先给我看每类目标值与依据说明,等我确认后再采纳。若我的档案(身高/年龄/活动量)未设置、无体重记录或信息缺失,请先询问补齐;若我已明确表达,直接计算,必要时做几句信息确认即可。完成后给 1 句话总结,不需要过多文字解释。\n\n我的目标方向(减脂 / 维持 / 增肌):____\n我的体重目标(kg,选填):____\n截止日期(选填):____',
            'user_intent': '一键设定营养+体重+饮水全套目标', 'data_fields': ['calorie_goal', 'protein_goal', 'carbs_goal', 'fat_goal', 'water_goal', 'weight_goal'],
            'depends_on_external': False, 'order': 7},
    {
            'category': '目标管理',     'wake_word': '看今日目标',     'desc': '看今日营养 4 项 + 饮水共 5 项目标完成度（体重为累计目标，引导到看体重目标进度）',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode today --chain <思考链>', 'text': '请你加载技能 卡路里,执行唤醒词「看今日目标」。\n\n我想看今日 5 项目标完成度:热量/蛋白/碳水/脂肪/饮水的目标值、实际值与完成度百分比。体重是累计目标,若我想看,请引导我到「看体重目标进度」。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_today', 'name': '看今日目标', 'subfunction': '看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode today --chain <思考链>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看今日目标」。\n\n我想看今日 5 项目标完成度:热量/蛋白/碳水/脂肪/饮水的目标值、实际值与完成度百分比。体重是累计目标,若我想看,请引导我到「看体重目标进度」。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看今日营养 4 项 + 饮水共 5 项目标完成度（体重为累计目标，引导到看体重目标进度）', 'data_fields': ['calorie_goal', 'protein_goal', 'carbs_goal', 'fat_goal', 'water_goal', 'actual', 'pct'],
            'depends_on_external': False, 'order': 8},
    {
            'category': '目标管理',     'wake_word': '看本周目标',     'desc': '看本周目标完成度汇总',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode week --chain <思考链>', 'text': '请你加载技能 卡路里,执行唤醒词「看本周目标」。\n\n我想看本周目标完成情况:日均实际 vs 日目标、周总量 vs 周目标(热量/蛋白/碳水/脂肪/饮水)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_week', 'name': '看本周目标', 'subfunction': '看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode week --chain <思考链>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看本周目标」。\n\n我想看本周目标完成情况:日均实际 vs 日目标、周总量 vs 周目标(热量/蛋白/碳水/脂肪/饮水)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看本周目标完成度汇总', 'data_fields': ['daily_avg', 'daily_target', 'week_total', 'week_target'],
            'depends_on_external': False, 'order': 9},
    {
            'category': '目标管理',     'wake_word': '看营养目标进度',     'desc': '看 4 项营养目标进度',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode nutrition --chain <思考链>', 'text': '请你加载技能 卡路里,执行唤醒词「看营养目标进度」。\n\n我想看 4 项营养目标(热量/蛋白/碳水/脂肪)的完成进度条、完成度百分比和缺口(目标 - 实际)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_nutrition_progress', 'name': '看营养目标进度', 'subfunction': '看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode nutrition --chain <思考链>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看营养目标进度」。\n\n我想看 4 项营养目标(热量/蛋白/碳水/脂肪)的完成进度条、完成度百分比和缺口(目标 - 实际)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看 4 项营养目标进度', 'data_fields': ['calorie_rate', 'protein_rate', 'carbs_rate', 'fat_rate', 'calorie_gap'],
            'depends_on_external': False, 'order': 10},
    {
            'category': '目标管理',     'wake_word': '看体重目标进度',     'desc': '看体重目标进度含预估达成',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode weight_progress --chain <思考链>', 'text': '请你加载技能 卡路里,执行唤醒词「看体重目标进度」。\n\n我想看体重目标进度:当前体重、目标值、差值(Δ)、完成百分比、预测达成日、剩余天数和建议速率。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_weight_progress', 'name': '看体重目标进度', 'subfunction': '看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode weight_progress --chain <思考链>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体重目标进度」。\n\n我想看体重目标进度:当前体重、目标值、差值(Δ)、完成百分比、预测达成日、剩余天数和建议速率。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看体重目标进度含预估达成', 'data_fields': ['current', 'target', 'delta', 'pct', 'predict_date', 'days_left', 'suggested_rate'],
            'depends_on_external': False, 'order': 11},
    {
            'category': '目标管理',     'wake_word': '看饮水目标进度',     'desc': '看饮水目标进度',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode water --chain <思考链>', 'text': '请你加载技能 卡路里,执行唤醒词「看饮水目标进度」。\n\n我想看今日饮水进度:累计饮水量、目标值、完成度百分比和剩余量(ml)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_water_progress', 'name': '看饮水目标进度', 'subfunction': '看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode water --chain <思考链>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看饮水目标进度」。\n\n我想看今日饮水进度:累计饮水量、目标值、完成度百分比和剩余量(ml)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看饮水目标进度', 'data_fields': ['cumulative', 'target', 'pct', 'remaining_ml'],
            'depends_on_external': False, 'order': 12},
    {
            'category': '目标管理',     'wake_word': '看目标对比实际',     'desc': '看目标线 vs 实际线折线对比',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode vs_actual --chain <思考链>', 'text': '请你加载技能 卡路里,执行唤醒词「看目标对比实际」。\n\n我想看热量目标线 vs 实际摄入线的对比折线图 + 偏差分析,默认最近 30 天(可自定义时间窗口)。完成后给 1 句话总结,不需要过多文字解释。\n\n时间窗口(天,选填,默认 30):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_vs_actual', 'name': '看目标对比实际', 'subfunction': '看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode vs_actual --chain <思考链>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看目标对比实际」。\n\n我想看热量目标线 vs 实际摄入线的对比折线图 + 偏差分析,默认最近 30 天(可自定义时间窗口)。完成后给 1 句话总结,不需要过多文字解释。\n\n时间窗口(天,选填,默认 30):____',
            'user_intent': '看目标线 vs 实际线折线对比', 'data_fields': ['daily_calorie_goal', 'daily_calorie_actual', 'deviation_pct'],
            'depends_on_external': False, 'order': 13},
    {
            'category': '目标管理',     'wake_word': '看目标完成度',     'desc': '查看全部目标完成度 + 缺口绝对值 + 总评分',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode completion --chain <思考链>', 'text': '请你加载技能 卡路里,执行唤醒词「看目标完成度」。\n\n我想看全部目标完成度汇总:5 项(热量/蛋白/碳水/脂肪/饮水)完成度百分比、各自缺口(目标 - 实际)和总评分。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_completion', 'name': '看目标完成度（含缺口）', 'subfunction': '看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode completion --chain <思考链>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看目标完成度」。\n\n我想看全部目标完成度汇总:5 项(热量/蛋白/碳水/脂肪/饮水)完成度百分比、各自缺口(目标 - 实际)和总评分。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '查看全部目标完成度 + 缺口绝对值 + 总评分', 'data_fields': ['pct', 'gap', 'total_score'],
            'depends_on_external': False, 'order': 14},
    {
            'category': '目标管理',     'wake_word': '看即将到期的目标',     'desc': '看即将到期的目标列表',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode weight --expiring 14 --chain <思考链>', 'text': '请你加载技能 卡路里,执行唤醒词「看即将到期的目标」。\n\n我想看即将到期的体重目标:目标值、截止日期、剩余天数、当前进度和紧迫度(默认 14 天内到期)。完成后给 1 句话总结,不需要过多文字解释。\n\n到期窗口(天,选填,默认 14):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_expiring', 'name': '看即将到期的目标', 'subfunction': '看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode weight --expiring 14 --chain <思考链>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看即将到期的目标」。\n\n我想看即将到期的体重目标:目标值、截止日期、剩余天数、当前进度和紧迫度(默认 14 天内到期)。完成后给 1 句话总结,不需要过多文字解释。\n\n到期窗口(天,选填,默认 14):____',
            'user_intent': '看即将到期的目标列表', 'data_fields': ['weight_goal', 'deadline', 'days_left', 'current_weight', 'completion_pct', 'urgency'],
            'depends_on_external': False, 'order': 15},
    {
            'category': '目标管理',     'wake_word': '看目标完成率(按周)',     'desc': '看本周营养目标每日完成率',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode nutrition --period week --chain <思考链>', 'text': '请你加载技能 卡路里,执行唤醒词「看目标完成率(按周)」。\n\n我想看本周(7 天)每日目标完成率柱状图 + 达标天数(达标带 80%-120%)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_completion_rate_week', 'name': '看目标完成率(按周)', 'subfunction': '看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode nutrition --period week --chain <思考链>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看目标完成率(按周)」。\n\n我想看本周(7 天)每日目标完成率柱状图 + 达标天数(达标带 80%-120%)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看本周营养目标每日完成率', 'data_fields': ['week_daily_rate', 'week_complete_days', 'week_avg_rate'],
            'depends_on_external': False, 'order': 16},
    {
            'category': '目标管理',     'wake_word': '看目标完成率(按月)',     'desc': '看本月营养目标每日完成率',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode nutrition --period month --chain <思考链>', 'text': '请你加载技能 卡路里,执行唤醒词「看目标完成率(按月)」。\n\n我想看本月(30 天)每日目标完成率柱状图 + 达标天数(达标带 80%-120%)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_completion_rate_month', 'name': '看目标完成率(按月)', 'subfunction': '看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode nutrition --period month --chain <思考链>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看目标完成率(按月)」。\n\n我想看本月(30 天)每日目标完成率柱状图 + 达标天数(达标带 80%-120%)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '看本月营养目标每日完成率', 'data_fields': ['month_daily_rate', 'month_complete_days', 'month_avg_rate'],
            'depends_on_external': False, 'order': 17},
    {
            'category': '目标管理',     'wake_word': '改营养目标',     'desc': '改某项或全部营养目标',
            'main_prompt': {
        'cli': 'python scripts/render_goal_config.py --modify-nutrition --chain <思考链>', 'text': '请你加载技能 卡路里,执行唤醒词「改营养目标」。\n\n我想修改营养目标(热量/蛋白/碳水/脂肪/饮水),可同时改多项。请显示每项改前值与改后值,并预估修改后的影响(热量缺口/预算变化)。完成后给 1 句话总结,不需要过多文字解释。\n\n我要改的项(每行一项,不改的留空):\n热量(卡)新目标值:____\n蛋白(g)新目标值:____\n碳水(g)新目标值:____\n脂肪(g)新目标值:____\n饮水(ml)新目标值:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_modify_nutrition', 'name': '改营养目标', 'subfunction': '改目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_config.html', 'data_source': 'python scripts/render_goal_config.py --modify-nutrition --chain <思考链>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改营养目标」。\n\n我想修改营养目标(热量/蛋白/碳水/脂肪/饮水),可同时改多项。请显示每项改前值与改后值,并预估修改后的影响(热量缺口/预算变化)。完成后给 1 句话总结,不需要过多文字解释。\n\n我要改的项(每行一项,不改的留空):\n热量(卡)新目标值:____\n蛋白(g)新目标值:____\n碳水(g)新目标值:____\n脂肪(g)新目标值:____\n饮水(ml)新目标值:____',
            'user_intent': '改某项或全部营养目标', 'data_fields': ['old_calorie_goal', 'new_calorie_goal', 'old_protein_goal', 'new_protein_goal', 'old_water_goal', 'new_water_goal'],
            'depends_on_external': False, 'order': 18},
    {
            'category': '目标管理',     'wake_word': '改体重目标',     'desc': '改体重目标含截止日',
            'main_prompt': {
        'cli': 'python scripts/render_goal_weight.py --mode modify --chain <思考链>', 'text': '请你加载技能 卡路里,执行唤醒词「改体重目标」。\n\n我想修改体重目标值或截止日期。请显示改前值与改后值,并给出新的建议减重速率。完成后给 1 句话总结,不需要过多文字解释。\n\n我要改的项(每行一项,不改的留空):\n体重目标(kg):____\n截止日期:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_modify_weight', 'name': '改体重目标', 'subfunction': '改目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_weight.html', 'data_source': 'python scripts/render_goal_weight.py --mode modify --chain <思考链>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改体重目标」。\n\n我想修改体重目标值或截止日期。请显示改前值与改后值,并给出新的建议减重速率。完成后给 1 句话总结,不需要过多文字解释。\n\n我要改的项(每行一项,不改的留空):\n体重目标(kg):____\n截止日期:____',
            'user_intent': '改体重目标含截止日', 'data_fields': ['old_weight_goal', 'new_weight_goal', 'old_deadline', 'new_deadline'],
            'depends_on_external': False, 'order': 19},
    {
            'category': '目标管理',     'wake_word': '改饮水目标',     'desc': '单独改饮水目标',
            'main_prompt': {
        'cli': 'python scripts/render_goal_config.py --modify-water --chain <思考链>', 'text': '请你加载技能 卡路里,执行唤醒词「改饮水目标」。\n\n我想单独修改饮水目标,其他营养目标保持不变。请显示改前值与改后值。完成后给 1 句话总结,不需要过多文字解释。\n\n饮水目标(ml):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_modify_water', 'name': '改饮水目标', 'subfunction': '改目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_config.html', 'data_source': 'python scripts/render_goal_config.py --modify-water --chain <思考链>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改饮水目标」。\n\n我想单独修改饮水目标,其他营养目标保持不变。请显示改前值与改后值。完成后给 1 句话总结,不需要过多文字解释。\n\n饮水目标(ml):____',
            'user_intent': '单独改饮水目标', 'data_fields': ['old_water_goal', 'new_water_goal'],
            'depends_on_external': False, 'order': 20},
    {
            'category': '目标管理',     'wake_word': '暂停所有目标',     'desc': '临时暂停全部目标',
            'main_prompt': {
        'cli': 'python scripts/render_goal_status.py --status paused --chain <思考链>', 'text': '请你加载技能 卡路里,执行唤醒词「暂停所有目标」。\n\n我想临时冻结全部目标(营养 + 体重 + 饮水),记录照常,仅目标暂停。请显示暂停状态、说明和恢复入口提示。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_pause_all', 'name': '暂停所有目标', 'subfunction': '改目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_status.html', 'data_source': 'python scripts/render_goal_status.py --status paused --chain <思考链>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「暂停所有目标」。\n\n我想临时冻结全部目标(营养 + 体重 + 饮水),记录照常,仅目标暂停。请显示暂停状态、说明和恢复入口提示。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '临时暂停全部目标', 'data_fields': ['paused', 'note', 'restore_hint'],
            'depends_on_external': False, 'order': 21},
    {
            'category': '目标管理',     'wake_word': '重启所有目标',     'desc': '从暂停恢复全部目标',
            'main_prompt': {
        'cli': 'python scripts/render_goal_status.py --status resumed --chain <思考链>', 'text': '请你加载技能 卡路里,执行唤醒词「重启所有目标」。\n\n我想从暂停恢复全部目标(营养 + 体重 + 饮水)。请显示重启状态。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_resume_all', 'name': '重启所有目标', 'subfunction': '改目标', 'output_type': 'receipt',
            'html_template': 'templates/goal_status.html', 'data_source': 'python scripts/render_goal_status.py --status resumed --chain <思考链>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「重启所有目标」。\n\n我想从暂停恢复全部目标(营养 + 体重 + 饮水)。请显示重启状态。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '从暂停恢复全部目标', 'data_fields': ['resume_state', 'resumed_at'],
            'depends_on_external': False, 'order': 22},
    {
            'category': '目标管理',     'wake_word': '看目标历史完成',     'desc': '看历史目标完成情况',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode history --chain <思考链>', 'text': '请你加载技能 卡路里,执行唤醒词「看目标历史完成」。\n\n我想看历史目标达成情况:每日达成列表(按时间排序)+ 完成/未完成天数统计(达标带 80%-120%)。完成后给 1 句话总结,不需要过多文字解释。\n\n回看天数(选填,默认 30):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_history_complete', 'name': '看目标历史完成', 'subfunction': '看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode history --chain <思考链>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看目标历史完成」。\n\n我想看历史目标达成情况:每日达成列表(按时间排序)+ 完成/未完成天数统计(达标带 80%-120%)。完成后给 1 句话总结,不需要过多文字解释。\n\n回看天数(选填,默认 30):____',
            'user_intent': '看历史目标完成情况', 'data_fields': ['goal_history', 'completed_count', 'incomplete_count'],
            'depends_on_external': False, 'order': 23},
    {
            'category': '目标管理',     'wake_word': '看目标预测达成',     'desc': '预测目标达成日 + 置信度（体重部分复用对比体重 B1 的预测）',
            'main_prompt': {
        'cli': 'python scripts/render_goal_progress.py --mode predict --chain <思考链>', 'text': '请你加载技能 卡路里,执行唤醒词「看目标预测达成」。\n\n我想看按当前趋势预测的目标达成日 + 置信度(体重部分复用对比体重的预测逻辑)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'goal_view_predict', 'name': '看目标预测达成', 'subfunction': '看目标', 'output_type': 'result',
            'html_template': 'templates/goal_progress.html', 'data_source': 'python scripts/render_goal_progress.py --mode predict --chain <思考链>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看目标预测达成」。\n\n我想看按当前趋势预测的目标达成日 + 置信度(体重部分复用对比体重的预测逻辑)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '预测目标达成日 + 置信度（体重部分复用对比体重 B1 的预测）', 'data_fields': ['predict_date', 'confidence'],
            'depends_on_external': False, 'order': 24},
    {
            'category': '分析',     'wake_word': '查健康报告',     'desc': '四维度综合健康仪表盘',
            'main_prompt': {
        'cli': 'python scripts/render_health_dashboard.py --days 7', 'text': '请你加载技能 卡路里,执行唤醒词「查健康报告」。\n\n我要看 4 维健康仪表盘(热量/营养/运动/体重综合,默认 7 天)。\n\n完成后给 1 句话总结,不需要过多文字解释。'},
            'fill_hints': [],
            'variants': [{
        'label': '查健康报告 本月', 'cli': 'python scripts/render_health_dashboard.py --start 2026-07-01 --end 2026-07-26', 'prompt': '请你加载技能 卡路里,执行唤醒词「查健康报告 本月」。\n\n我要看本月 1 号到今天的健康报告。\n\n完成后给 1 句话总结,不需要过多文字解释。'}]},
    {
            'category': '分析',     'wake_word': '查卡路里数据',     'desc': '数据健康检查(lint_health)',
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
            'category': '身体细节',     'wake_word': '记体脂（皮褶钳）',     'desc': '皮褶钳测 7 点(Jackson-Pollock 自动算体脂率)',
            'main_prompt': {
        'cli': 'python scripts/body_composition.py add ...', 'text': '请你加载技能 卡路里,执行唤醒词「记体脂（皮褶钳）」。\n\n我用皮褶钳测了 7 点(胸/腹/大腿/三头/肩胛下/髂上/腋中 mm),请按 Jackson-Pollock 7 点法帮我算体脂率并记录。如果我没说性别/年龄,请先问我。完成后给 1 句话总结,不需要过多文字解释。\n\n7 点皮褶厚度(mm):\n胸:____\n腹:____\n大腿:____\n三头:____\n肩胛下:____\n髂上:____\n腋中:____\n性别(男/女):____\n年龄:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_comp_add_caliper', 'name': '记体脂（皮褶钳）', 'subfunction': '记身体细节', 'output_type': 'receipt',
            'html_template': 'templates/body_composition_wizard.html', 'data_source': 'python scripts/render_body_composition_wizard.py --caliper-chest-mm <C> --caliper-abdominal-mm <A> --caliper-thigh-mm <T> --caliper-tricep-mm <T> --caliper-subscapular-mm <S> --caliper-suprailiac-mm <I> --caliper-midaxillary-mm <M> --age <A> --sex <男/女>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「记体脂（皮褶钳）」。\n\n我用皮褶钳测了 7 点(胸/腹/大腿/三头/肩胛下/髂上/腋中 mm),请按 Jackson-Pollock 7 点法帮我算体脂率并记录。如果我没说性别/年龄,请先问我。完成后给 1 句话总结,不需要过多文字解释。\n\n7 点皮褶厚度(mm):\n胸:____\n腹:____\n大腿:____\n三头:____\n肩胛下:____\n髂上:____\n腋中:____\n性别(男/女):____\n年龄:____',
            'user_intent': '我想用手持皮褶钳测 7 点并自动算体脂率存档', 'data_fields': ['caliper_chest_mm', 'caliper_abdominal_mm', 'caliper_thigh_mm', 'caliper_tricep_mm', 'caliper_subscapular_mm', 'caliper_suprailiac_mm', 'caliper_midaxillary_mm', 'body_fat_pct', 'age', 'sex', 'source'],
            'depends_on_external': False, 'order': 0},
    {
            'category': '身体细节',     'wake_word': '记体脂（外部测量）',     'desc': '外部设备(健身房/医院/其他)测体脂率',
            'main_prompt': {
        'cli': 'python scripts/body_composition.py add --source gym ...', 'text': '请你加载技能 卡路里,执行唤醒词「记体脂（外部测量）」。\n\n我用外部设备(健身房 InBody/医院/其他)测了体脂率,请帮我记录体脂率和来源、日期。完成后给 1 句话总结,不需要过多文字解释。\n\n体脂率(%):____\n来源(健身房/医院/其他):____\n日期:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_comp_add_external', 'name': '记体脂（外部测量）', 'subfunction': '记身体细节', 'output_type': 'receipt',
            'html_template': 'templates/body_composition_wizard.html', 'data_source': 'python scripts/render_body_composition_wizard.py --source <健身房/医院/其他> --body-fat-pct <P> --date <D>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「记体脂（外部测量）」。\n\n我用外部设备(健身房 InBody/医院/其他)测了体脂率,请帮我记录体脂率和来源、日期。完成后给 1 句话总结,不需要过多文字解释。\n\n体脂率(%):____\n来源(健身房/医院/其他):____\n日期:____',
            'user_intent': '我想记录外部设备(健身房/医院)测的体脂率', 'data_fields': ['body_fat_pct', 'source', 'date'],
            'depends_on_external': False, 'order': 1},
    {
            'category': '身体细节',     'wake_word': '记围度',     'desc': '13 部位围度入库:上身 5 + 下身 4 + 手臂 4,cm 单位',
            'main_prompt': {
        'cli': 'python scripts/body_measurements.py add ...', 'text': '请你加载技能 卡路里,执行唤醒词「记围度」。\n\n我量了身体围度,请帮我记录 13 项围度(胸/腰/腹/臀/肩/大腿/小腿/手臂/前臂,左+右),量了哪项填哪项,没量的留空。完成后给 1 句话总结,不需要过多文字解释。\n\n胸围(cm):____\n腰围(cm):____\n腹围(cm):____\n臀围(cm):____\n肩围(cm):____\n左大腿(cm):____\n右大腿(cm):____\n左小腿(cm):____\n右小腿(cm):____\n左上臂(cm):____\n右上臂(cm):____\n左前臂(cm):____\n右前臂(cm):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_meas_add', 'name': '记围度', 'subfunction': '记身体细节', 'output_type': 'receipt',
            'html_template': 'templates/body_measurements_wizard.html', 'data_source': 'python scripts/render_body_measurements_wizard.py --chest-cm <C> --waist-cm <W> --abdomen-cm <A> --hip-cm <H> --shoulder-cm <S> --left-thigh-cm <LT> --right-thigh-cm <RT> --left-calf-cm <LC> --right-calf-cm <RC> --left-arm-cm <LA> --right-arm-cm <RA> --left-forearm-cm <LF> --right-forearm-cm <RF>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「记围度」。\n\n我量了身体围度,请帮我记录 13 项围度(胸/腰/腹/臀/肩/大腿/小腿/手臂/前臂,左+右),量了哪项填哪项,没量的留空。完成后给 1 句话总结,不需要过多文字解释。\n\n胸围(cm):____\n腰围(cm):____\n腹围(cm):____\n臀围(cm):____\n肩围(cm):____\n左大腿(cm):____\n右大腿(cm):____\n左小腿(cm):____\n右小腿(cm):____\n左上臂(cm):____\n右上臂(cm):____\n左前臂(cm):____\n右前臂(cm):____',
            'user_intent': '我想记录身体围度(13 项,可部分填写)', 'data_fields': ['chest_cm', 'waist_cm', 'abdomen_cm', 'hip_cm', 'shoulder_cm', 'left_thigh_cm', 'right_thigh_cm', 'left_calf_cm', 'right_calf_cm', 'left_arm_cm', 'right_arm_cm', 'left_forearm_cm', 'right_forearm_cm', 'date'],
            'depends_on_external': False, 'order': 2},
    {
            'category': '身体细节',     'wake_word': '补记体脂',     'desc': '补录历史某天体脂(冲突提示 + 循环补其他日期)',
            'main_prompt': {
        'cli': 'python scripts/body_composition.py add --date <D> ...', 'text': '请你加载技能 卡路里,执行唤醒词「补记体脂」。\n\n我要补录之前某天的体脂测量(不是今天的)。如果那天已有记录,请先告诉我冲突再确认。补完后可以问我还要不要补其他日期。完成后给 1 句话总结,不需要过多文字解释。\n\n体脂率(%):____\n来源(皮褶钳/健身房/医院/其他):____\n日期:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_comp_backfill', 'name': '补记体脂', 'subfunction': '记身体细节', 'output_type': 'receipt',
            'html_template': 'templates/body_composition_wizard.html', 'data_source': 'python scripts/render_body_composition_wizard.py --date <D> --body-fat-pct <P> --source <皮褶钳/健身房/医院/其他>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「补记体脂」。\n\n我要补录之前某天的体脂测量(不是今天的)。如果那天已有记录,请先告诉我冲突再确认。补完后可以问我还要不要补其他日期。完成后给 1 句话总结,不需要过多文字解释。\n\n体脂率(%):____\n来源(皮褶钳/健身房/医院/其他):____\n日期:____',
            'user_intent': '我想补录过去某天的体脂测量', 'data_fields': ['date', 'body_fat_pct', 'source', 'conflict'],
            'depends_on_external': False, 'order': 3},
    {
            'category': '身体细节',     'wake_word': '补记围度',     'desc': '补录历史某天围度(冲突提示 + 循环补其他日期)',
            'main_prompt': {
        'cli': 'python scripts/body_measurements.py add --date <D> ...', 'text': '请你加载技能 卡路里,执行唤醒词「补记围度」。\n\n我要补录之前某天的围度测量(不是今天的)。如果那天已有记录,请先告诉我冲突再确认。补完后可以问我还要不要补其他日期。完成后给 1 句话总结,不需要过多文字解释。\n\n各围度(cm,量了哪项填哪项):\n胸围:____\n腰围:____\n腹围:____\n臀围:____\n肩围:____\n左大腿:____\n右大腿:____\n左小腿:____\n右小腿:____\n左上臂:____\n右上臂:____\n左前臂:____\n右前臂:____\n日期:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_meas_backfill', 'name': '补记围度', 'subfunction': '记身体细节', 'output_type': 'receipt',
            'html_template': 'templates/body_measurements_wizard.html', 'data_source': 'python scripts/render_body_measurements_wizard.py --date <D> --waist-cm <W> --hip-cm <H>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「补记围度」。\n\n我要补录之前某天的围度测量(不是今天的)。如果那天已有记录,请先告诉我冲突再确认。补完后可以问我还要不要补其他日期。完成后给 1 句话总结,不需要过多文字解释。\n\n各围度(cm,量了哪项填哪项):\n胸围:____\n腰围:____\n腹围:____\n臀围:____\n肩围:____\n左大腿:____\n右大腿:____\n左小腿:____\n右小腿:____\n左上臂:____\n右上臂:____\n左前臂:____\n右前臂:____\n日期:____',
            'user_intent': '我想补录过去某天的围度测量', 'data_fields': ['date', 'chest_cm', 'waist_cm', 'abdomen_cm', 'hip_cm', 'shoulder_cm', 'conflict'],
            'depends_on_external': False, 'order': 4},
    {
            'category': '身体细节',     'wake_word': '看体脂',     'desc': '历史体脂记录 + 来源筛选',
            'main_prompt': {
        'cli': 'python scripts/body_composition.py list [--source <s>]', 'text': '请你加载技能 卡路里,执行唤醒词「看体脂」。\n\n我想看历史体脂记录:日期/体脂率/来源 的表格 + 当前最新值,并按来源筛选(皮褶钳/健身房/医院/全部)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_comp_list', 'name': '看体脂', 'subfunction': '看身体细节', 'output_type': 'result',
            'html_template': 'templates/body_composition_view.html', 'data_source': 'python scripts/render_body_composition_view.py --mode list --source <皮褶钳/健身房/医院/全部>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体脂」。\n\n我想看历史体脂记录:日期/体脂率/来源 的表格 + 当前最新值,并按来源筛选(皮褶钳/健身房/医院/全部)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '我想看历史体脂记录并可按来源筛选', 'data_fields': ['date', 'body_fat_pct', 'source', 'source_filter', 'current'],
            'depends_on_external': False, 'order': 0},
    {
            'category': '身体细节',     'wake_word': '看体脂趋势',     'desc': '体脂率时间线(默认最近来源,可切换)',
            'main_prompt': {
        'cli': 'python scripts/body_composition.py trend [--source <s>]', 'text': '请你加载技能 卡路里,执行唤醒词「看体脂趋势」。\n\n我想看体脂率变化折线图,默认用我最近用的来源,也可以切换来源;同时给 KPI(变化/平均/最低)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_comp_trend', 'name': '看体脂趋势', 'subfunction': '看身体细节', 'output_type': 'result',
            'html_template': 'templates/body_composition_view.html', 'data_source': 'python scripts/render_body_composition_view.py --mode trend --source <默认最近来源> --days 90', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看体脂趋势」。\n\n我想看体脂率变化折线图,默认用我最近用的来源,也可以切换来源;同时给 KPI(变化/平均/最低)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '我想看体脂率趋势(默认最近来源,可切换)', 'data_fields': ['source', 'trend', 'delta', 'avg', 'min'],
            'depends_on_external': False, 'order': 1},
    {
            'category': '身体细节',     'wake_word': '看围度',     'desc': '历史围度记录 + 部位筛选',
            'main_prompt': {
        'cli': 'python scripts/body_measurements.py list [--metric <col>]', 'text': '请你加载技能 卡路里,执行唤醒词「看围度」。\n\n我想看历史围度记录:日期/各围度 的表格,并按部位筛选(只看某部位的历史)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_meas_list', 'name': '看围度', 'subfunction': '看身体细节', 'output_type': 'result',
            'html_template': 'templates/body_measurements_view.html', 'data_source': 'python scripts/render_body_measurements_view.py --mode list --metric <部位>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看围度」。\n\n我想看历史围度记录:日期/各围度 的表格,并按部位筛选(只看某部位的历史)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '我想看历史围度记录并可按部位筛选', 'data_fields': ['date', 'measurements', 'metric_filter'],
            'depends_on_external': False, 'order': 2},
    {
            'category': '身体细节',     'wake_word': '看围度趋势',     'desc': '单围度时间线(先选部位)',
            'main_prompt': {
        'cli': 'python scripts/body_measurements.py trend --metric <col>', 'text': '请你加载技能 卡路里,执行唤醒词「看围度趋势」。\n\n我想看某个部位的围度变化折线图。请先让我选部位,再画折线并给变化摘要。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_meas_trend', 'name': '看围度趋势', 'subfunction': '看身体细节', 'output_type': 'result',
            'html_template': 'templates/body_measurements_view.html', 'data_source': 'python scripts/render_body_measurements_view.py --mode trend --metric <部位> --days 90', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「看围度趋势」。\n\n我想看某个部位的围度变化折线图。请先让我选部位,再画折线并给变化摘要。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '我想看某部位围度的变化趋势', 'data_fields': ['metric', 'trend', 'delta_summary'],
            'depends_on_external': False, 'order': 3},
    {
            'category': '身体细节',     'wake_word': '对比体脂',     'desc': '两段时间体脂对比(注明同来源)',
            'main_prompt': {
        'cli': 'python scripts/body_composition.py compare --start1 <D1> --end1 <D2> --start2 <D3> --end2 <D4> [--source <s>]', 'text': '请你加载技能 卡路里,执行唤醒词「对比体脂」。\n\n我想对比两次体脂测量,第一次和第二次都可以给具体日期或一段时间。请显示两次各自的均值/最低/记录数 + 差值(Δ)和变化率,并注明必须同来源对比才有意义。完成后给 1 句话总结,不需要过多文字解释。\n\n第一次(日期或时间段):____\n第二次(日期或时间段):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_comp_compare', 'name': '对比体脂', 'subfunction': '比身体细节', 'output_type': 'result',
            'html_template': 'templates/body_composition_view.html', 'data_source': 'python scripts/render_body_composition_view.py --mode compare --start1 <D1> --end1 <D2> --start2 <D3> --end2 <D4> --source <来源>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比体脂」。\n\n我想对比两次体脂测量,第一次和第二次都可以给具体日期或一段时间。请显示两次各自的均值/最低/记录数 + 差值(Δ)和变化率,并注明必须同来源对比才有意义。完成后给 1 句话总结,不需要过多文字解释。\n\n第一次(日期或时间段):____\n第二次(日期或时间段):____',
            'user_intent': '我想对比两段时间的体脂变化', 'data_fields': ['period1', 'period2', 'delta', 'pct_change', 'source'],
            'depends_on_external': False, 'order': 0},
    {
            'category': '身体细节',     'wake_word': '对比围度',     'desc': '两个日期围度对比(13 项 Δ)',
            'main_prompt': {
        'cli': 'python scripts/body_measurements.py compare --date1 <D1> --date2 <D2>', 'text': '请你加载技能 卡路里,执行唤醒词「对比围度」。\n\n我想对比两次围度测量,显示 13 项各自的差值(Δ)。完成后给 1 句话总结,不需要过多文字解释。\n\n第一次日期:____\n第二次日期:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_meas_compare', 'name': '对比围度', 'subfunction': '比身体细节', 'output_type': 'result',
            'html_template': 'templates/body_measurements_view.html', 'data_source': 'python scripts/render_body_measurements_view.py --mode compare --date1 <D1> --date2 <D2>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比围度」。\n\n我想对比两次围度测量,显示 13 项各自的差值(Δ)。完成后给 1 句话总结,不需要过多文字解释。\n\n第一次日期:____\n第二次日期:____',
            'user_intent': '我想对比两个日期的围度变化', 'data_fields': ['date1', 'date2', 'deltas'],
            'depends_on_external': False, 'order': 1},
    {
            'category': '身体细节',     'wake_word': '删体脂',     'desc': '软删除体脂记录(先列候选 → 快照确认 → 回执)',
            'main_prompt': {
        'cli': 'python scripts/body_composition.py delete --id <ID>', 'text': '请你加载技能 卡路里,执行唤醒词「删体脂」。\n\n我要删一条体脂记录。如果我没说清是哪条,请先列出最近的几条记录(日期/体脂率/来源)让我选。确认后,删除前先给我看这条记录的内容,确认无误再删,最后给我确认回执。完成后给 1 句话总结,不需要过多文字解释。\n\n要删的记录(选填,如「最近一条」或日期):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_comp_delete', 'name': '删体脂', 'subfunction': '删身体细节', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_body_delete_receipt.py --entity composition --id <ID>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「删体脂」。\n\n我要删一条体脂记录。如果我没说清是哪条,请先列出最近的几条记录(日期/体脂率/来源)让我选。确认后,删除前先给我看这条记录的内容,确认无误再删,最后给我确认回执。完成后给 1 句话总结,不需要过多文字解释。\n\n要删的记录(选填,如「最近一条」或日期):____',
            'user_intent': '我想删除一条体脂记录', 'data_fields': ['id', 'date', 'body_fat_pct', 'source', 'snapshot'],
            'depends_on_external': False, 'order': 0},
    {
            'category': '身体细节',     'wake_word': '删围度',     'desc': '软删除围度记录(先列候选 → 快照确认 → 回执)',
            'main_prompt': {
        'cli': 'python scripts/body_measurements.py delete --id <ID>', 'text': '请你加载技能 卡路里,执行唤醒词「删围度」。\n\n我要删一条围度记录。如果我没说清是哪条,请先列出最近的几条记录(日期/各围度)让我选。确认后,删除前先给我看这条记录的内容,确认无误再删,最后给我确认回执。完成后给 1 句话总结,不需要过多文字解释。\n\n要删的记录(选填,如「最近一条」或日期):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_meas_delete', 'name': '删围度', 'subfunction': '删身体细节', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_body_delete_receipt.py --entity measurements --id <ID>', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「删围度」。\n\n我要删一条围度记录。如果我没说清是哪条,请先列出最近的几条记录(日期/各围度)让我选。确认后,删除前先给我看这条记录的内容,确认无误再删,最后给我确认回执。完成后给 1 句话总结,不需要过多文字解释。\n\n要删的记录(选填,如「最近一条」或日期):____',
            'user_intent': '我想删除一条围度记录', 'data_fields': ['id', 'date', 'measurements', 'snapshot'],
            'depends_on_external': False, 'order': 1},
    {
            'category': '身材照片',     'wake_word': '记身材照',     'desc': '存一张身材照(发图/路径双模式)',
            'main_prompt': {
        'cli': 'python scripts/render_body_photo_receipt.py --live-add <照片> --tag <标签> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「记身材照」。\n\n我要存一张身材照。你可以直接发照片给我(手机/飞书),也可以告诉我照片文件路径(电脑)。如果标签没说,请问我。存完后给我看:照片缩略图预览 + 拍摄日期 + 标签 + 距上次同标签拍照间隔了几天(规律拍照提醒)。完成后给 1 句话总结,不需要过多文字解释。\n\n标签(如 正面/侧面/背部):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_photo_add_single', 'name': '存一张照片', 'subfunction': '存身材照', 'output_type': 'receipt',
            'html_template': 'templates/body_photo_receipt.html', 'data_source': 'python scripts/render_body_photo_receipt.py --live-add <照片> --tag <标签> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「记身材照」。\n\n我要存一张身材照。你可以直接发照片给我(手机/飞书),也可以告诉我照片文件路径(电脑)。如果标签没说,请问我。存完后给我看:照片缩略图预览 + 拍摄日期 + 标签 + 距上次同标签拍照间隔了几天(规律拍照提醒)。完成后给 1 句话总结,不需要过多文字解释。\n\n标签(如 正面/侧面/背部):____',
            'user_intent': '存一张身材照并预览回执', 'data_fields': ['photo_path', 'tag_list', 'date', 'distance_days', 'note'],
            'depends_on_external': False, 'order': 0},
    {
            'category': '身材照片',     'wake_word': '记身材照',     'desc': '存一张带备注的身材照',
            'main_prompt': {
        'cli': 'python scripts/render_body_photo_receipt.py --live-add <照片> --tag <标签> --note <备注> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「记身材照」。\n\n我要存一张身材照并附备注(比如当时的状态/饮食阶段)。你可以直接发照片给我(手机/飞书),也可以告诉我照片文件路径(电脑)。如果标签没说,请问我。存完后给我看:照片缩略图预览 + 拍摄日期 + 标签 + 备注 + 距上次同标签拍照间隔。完成后给 1 句话总结,不需要过多文字解释。\n\n标签(如 正面/侧面/背部):____\n备注:____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_photo_add_note', 'name': '存照片（含备注）', 'subfunction': '存身材照', 'output_type': 'receipt',
            'html_template': 'templates/body_photo_receipt.html', 'data_source': 'python scripts/render_body_photo_receipt.py --live-add <照片> --tag <标签> --note <备注> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「记身材照」。\n\n我要存一张身材照并附备注(比如当时的状态/饮食阶段)。你可以直接发照片给我(手机/飞书),也可以告诉我照片文件路径(电脑)。如果标签没说,请问我。存完后给我看:照片缩略图预览 + 拍摄日期 + 标签 + 备注 + 距上次同标签拍照间隔。完成后给 1 句话总结,不需要过多文字解释。\n\n标签(如 正面/侧面/背部):____\n备注:____',
            'user_intent': '存一张带备注的身材照', 'data_fields': ['photo_path', 'tag_list', 'date', 'note', 'distance_days'],
            'depends_on_external': False, 'order': 1},
    {
            'category': '身材照片',     'wake_word': '记身材照',     'desc': '批量存多张身材照(逐张状态明细)',
            'main_prompt': {
        'cli': 'python scripts/render_body_photo_receipt.py --live-add <照片1> <照片2> ... --tag <标签> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「记身材照」。\n\n我要一次性存多张身材照(可连发多张照片,或给多个路径)。每张照片可以单独指定标签(如"这张是侧面"),没指定的用我给的默认标签。存完后给我看:每张照片的缩略图 + 标签 + 状态(成功/跳过/失败+原因)+ 汇总成功张数。完成后给 1 句话总结,不需要过多文字解释。\n\n默认标签(如 正面):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_photo_add_batch', 'name': '批量存照片', 'subfunction': '存身材照', 'output_type': 'receipt',
            'html_template': 'templates/body_photo_receipt.html', 'data_source': 'python scripts/render_body_photo_receipt.py --live-add <照片1> <照片2> ... --tag <标签> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「记身材照」。\n\n我要一次性存多张身材照(可连发多张照片,或给多个路径)。每张照片可以单独指定标签(如"这张是侧面"),没指定的用我给的默认标签。存完后给我看:每张照片的缩略图 + 标签 + 状态(成功/跳过/失败+原因)+ 汇总成功张数。完成后给 1 句话总结,不需要过多文字解释。\n\n默认标签(如 正面):____',
            'user_intent': '批量存多张身材照并看逐张结果', 'data_fields': ['photo_path', 'tag_list', 'status', 'reason', 'batch_count'],
            'depends_on_external': False, 'order': 2},
    {
            'category': '身材照片',     'wake_word': '查身材照',     'desc': '浏览身材照(网格 + 时间/标签筛选 + 计数)',
            'main_prompt': {
        'cli': 'python scripts/render_body_photo_gallery.py [--days <N> | --start <D> --end <D>] [--tag <标签>] --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「查身材照」。\n\n我想浏览身材照:照片网格 + 按时间/标签筛选 + 照片总数/各标签计数 + 距上次拍照多少天。时间可以用天数(如最近 30 天)、某个日期(如 7月1日)、或一段范围(如 6月1日~7月1日);没填默认最近 90 天。完成后给 1 句话总结,不需要过多文字解释。\n\n时间(最近 N 天 / 某日期 / 某范围,选填):____\n标签(选填,如 正面):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_photo_list', 'name': '看身材照', 'subfunction': '看身材照', 'output_type': 'result',
            'html_template': 'templates/body_photo_gallery.html', 'data_source': 'python scripts/render_body_photo_gallery.py [--days <N> | --start <D> --end <D>] [--tag <标签>] --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「查身材照」。\n\n我想浏览身材照:照片网格 + 按时间/标签筛选 + 照片总数/各标签计数 + 距上次拍照多少天。时间可以用天数(如最近 30 天)、某个日期(如 7月1日)、或一段范围(如 6月1日~7月1日);没填默认最近 90 天。完成后给 1 句话总结,不需要过多文字解释。\n\n时间(最近 N 天 / 某日期 / 某范围,选填):____\n标签(选填,如 正面):____',
            'user_intent': '浏览身材照并按时间/标签筛选', 'data_fields': ['photos', 'tag_counts', 'total_count', 'days_since_last', 'filters'],
            'depends_on_external': False, 'order': 0},
    {
            'category': '身材照片',     'wake_word': '对比两张照片',     'desc': '两张照片并排对比(间隔天数/标签/备注)',
            'main_prompt': {
        'cli': 'python scripts/render_body_photo_compare.py --id1 <ID> --id2 <ID> --chain "1.识别→2.读DB→3.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「对比两张照片」。\n\n我想把两张身材照并排对比。可以说日期(如"月初 vs 月底")、编号,或让我从最近的照片里选。并排显示:两张照片 + 各自拍摄日期 + 间隔天数 + 各自标签/备注。完成后给 1 句话总结,不需要过多文字解释。\n\n照片 1(日期/编号/留空):____\n照片 2(日期/编号/留空):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_photo_compare', 'name': '对比两张照片', 'subfunction': '比身材照', 'output_type': 'result',
            'html_template': 'templates/body_photo_compare.html', 'data_source': 'python scripts/render_body_photo_compare.py --id1 <ID> --id2 <ID> --chain "1.识别→2.读DB→3.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「对比两张照片」。\n\n我想把两张身材照并排对比。可以说日期(如"月初 vs 月底")、编号,或让我从最近的照片里选。并排显示:两张照片 + 各自拍摄日期 + 间隔天数 + 各自标签/备注。完成后给 1 句话总结,不需要过多文字解释。\n\n照片 1(日期/编号/留空):____\n照片 2(日期/编号/留空):____',
            'user_intent': '并排对比两张身材照看变化', 'data_fields': ['photo1', 'photo2', 'interval_days', 'tag_list', 'note'],
            'depends_on_external': False, 'order': 1},
    {
            'category': '身材照片',     'wake_word': '生成身材照GIF',     'desc': '时间段多张照片合成变化 GIF(帧数/首末日期)',
            'main_prompt': {
        'cli': 'python scripts/render_body_photo_gif_result.py --tag <标签> [--start <D> --end <D> | --days <N> | --photo-id <ID> ...] --chain "1.识别→2.选照片→3.合成→4.渲染"', 'text': '请你加载技能 卡路里,执行唤醒词「生成身材照GIF」。\n\n我要把一段时间的多张身材照合成变化 GIF。请先确认照片范围(标签/时间),生成后给我看:GIF 预览 + 文件位置 + 时间跨度 + 帧数 + 合成照片总数 + 首末日期。完成后给 1 句话总结,不需要过多文字解释。\n\n标签(如 正面):____\n时间范围(如 最近3个月 / 起始日期):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_photo_gif', 'name': '生成身材照 GIF', 'subfunction': '比身材照', 'output_type': 'result',
            'html_template': 'templates/body_photo_gif_result.html', 'data_source': 'python scripts/render_body_photo_gif_result.py --tag <标签> [--start <D> --end <D> | --days <N> | --photo-id <ID> ...] --chain "1.识别→2.选照片→3.合成→4.渲染"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「生成身材照GIF」。\n\n我要把一段时间的多张身材照合成变化 GIF。请先确认照片范围(标签/时间),生成后给我看:GIF 预览 + 文件位置 + 时间跨度 + 帧数 + 合成照片总数 + 首末日期。完成后给 1 句话总结,不需要过多文字解释。\n\n标签(如 正面):____\n时间范围(如 最近3个月 / 起始日期):____',
            'user_intent': '把一段时间的身材照合成变化 GIF', 'data_fields': ['gif_path', 'time_span', 'frames', 'photo_count', 'first_date', 'last_date'],
            'depends_on_external': False, 'order': 0},
    {
            'category': '身材照片',     'wake_word': '删身材照',     'desc': '删除照片(先列候选 → 快照确认 → 回执)',
            'main_prompt': {
        'cli': 'python scripts/render_body_photo_receipt.py --live-delete --id <ID> --chain "1.列候选→2.确认→3.删除→4.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「删身材照」。\n\n我要删一张身材照(删除后无法恢复)。如果我没说清是哪张,请先列出最近的几张照片(缩略图+日期+标签)让我选。确认后,删除前先给我看这张照片的内容(快照),确认无误再删,最后给我确认回执。完成后给 1 句话总结,不需要过多文字解释。\n\n要删的照片(选填,如「最近一张」或日期):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_photo_delete', 'name': '删身材照', 'subfunction': '管身材照', 'output_type': 'receipt',
            'html_template': 'templates/body_photo_receipt.html', 'data_source': 'python scripts/render_body_photo_receipt.py --live-delete --id <ID> --chain "1.列候选→2.确认→3.删除→4.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「删身材照」。\n\n我要删一张身材照(删除后无法恢复)。如果我没说清是哪张,请先列出最近的几张照片(缩略图+日期+标签)让我选。确认后,删除前先给我看这张照片的内容(快照),确认无误再删,最后给我确认回执。完成后给 1 句话总结,不需要过多文字解释。\n\n要删的照片(选填,如「最近一张」或日期):____',
            'user_intent': '删除一张身材照(带快照确认)', 'data_fields': ['id', 'date', 'tag_list', 'snapshot', 'photo_path'],
            'depends_on_external': False, 'order': 0},
    {
            'category': '身材照片',     'wake_word': '改照片标签',     'desc': '标签覆盖整套(可多个,改前/改后对比)',
            'main_prompt': {
        'cli': 'python scripts/render_body_photo_receipt.py --live-tag-set --id <ID> --tag-list <标签1,标签2> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「改照片标签」。\n\n我要把某张照片的标签换成整套新标签(覆盖旧的,可多个)。请先确认这张照片原来的完整标签列表,改完后给我看:改前/改后对比 + 新的完整标签列表。完成后给 1 句话总结,不需要过多文字解释。\n\n照片(日期或编号):____\n新标签(可多个,如 正面,侧面):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_photo_tag_set', 'name': '改照片标签', 'subfunction': '管身材照', 'output_type': 'receipt',
            'html_template': 'templates/body_photo_receipt.html', 'data_source': 'python scripts/render_body_photo_receipt.py --live-tag-set --id <ID> --tag-list <标签1,标签2> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改照片标签」。\n\n我要把某张照片的标签换成整套新标签(覆盖旧的,可多个)。请先确认这张照片原来的完整标签列表,改完后给我看:改前/改后对比 + 新的完整标签列表。完成后给 1 句话总结,不需要过多文字解释。\n\n照片(日期或编号):____\n新标签(可多个,如 正面,侧面):____',
            'user_intent': '把照片标签换成整套新标签', 'data_fields': ['tag_before', 'tag_after', 'tag_list'],
            'depends_on_external': False, 'order': 1},
    {
            'category': '身材照片',     'wake_word': '加照片标签',     'desc': '追加标签(可多个,判重提示)',
            'main_prompt': {
        'cli': 'python scripts/render_body_photo_receipt.py --live-tag-add --id <ID> --tag <标签> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「加照片标签」。\n\n我要给某张照片追加标签(不覆盖已有,可一次加多个)。如果某个标签已经存在,请提示我。加完后给我看:新增后完整标签列表。完成后给 1 句话总结,不需要过多文字解释。\n\n照片(日期或编号):____\n要加的标签(可多个,逗号分隔):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_photo_tag_add', 'name': '加照片标签', 'subfunction': '管身材照', 'output_type': 'receipt',
            'html_template': 'templates/body_photo_receipt.html', 'data_source': 'python scripts/render_body_photo_receipt.py --live-tag-add --id <ID> --tag <标签> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「加照片标签」。\n\n我要给某张照片追加标签(不覆盖已有,可一次加多个)。如果某个标签已经存在,请提示我。加完后给我看:新增后完整标签列表。完成后给 1 句话总结,不需要过多文字解释。\n\n照片(日期或编号):____\n要加的标签(可多个,逗号分隔):____',
            'user_intent': '给照片追加一个或多个标签', 'data_fields': ['tag_added', 'tag_list', 'duplicate'],
            'depends_on_external': False, 'order': 2},
    {
            'category': '身材照片',     'wake_word': '删照片标签',     'desc': '移除标签(可多个,至少保留 1 个)',
            'main_prompt': {
        'cli': 'python scripts/render_body_photo_receipt.py --live-tag-remove --id <ID> --tag <标签> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「删照片标签」。\n\n我要从某张照片上移除标签(其余保留,可一次删多个)。请先告诉我这张照片当前有哪些标签,删完后给我看:删除前/删除后列表。每张照片至少保留 1 个标签,删空会提示我;想清空全部标签请用「改照片标签」。完成后给 1 句话总结,不需要过多文字解释。\n\n照片(日期或编号):____\n要删的标签(可多个,逗号分隔):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'body_photo_tag_remove', 'name': '删照片标签', 'subfunction': '管身材照', 'output_type': 'receipt',
            'html_template': 'templates/body_photo_receipt.html', 'data_source': 'python scripts/render_body_photo_receipt.py --live-tag-remove --id <ID> --tag <标签> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「删照片标签」。\n\n我要从某张照片上移除标签(其余保留,可一次删多个)。请先告诉我这张照片当前有哪些标签,删完后给我看:删除前/删除后列表。每张照片至少保留 1 个标签,删空会提示我;想清空全部标签请用「改照片标签」。完成后给 1 句话总结,不需要过多文字解释。\n\n照片(日期或编号):____\n要删的标签(可多个,逗号分隔):____',
            'user_intent': '从照片上移除一个或多个标签', 'data_fields': ['tag_removed', 'tag_before', 'tag_after'],
            'depends_on_external': False, 'order': 3},
    {
            'category': '基础信息',     'wake_word': '设置档案',     'desc': '设置基础档案(身高/年龄/性别/活动量,含采访式引导)',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-profile-set --age <A> --gender <G> --height <H> --activity <L> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「设置档案」。\n\n我想设置基础档案(身高/年龄/性别/活动量)。如果我没说全,请一项一项问我,并根据我的日常情况推荐合适的活动量。设置完成后给我看:身高/年龄/性别/活动量 + 推荐活动量 + 设置时间。完成后给 1 句话总结,不需要过多文字解释。\n\n我的身高(cm):____\n年龄:____\n性别(男/女):____\n日常活动情况(选填,用于推荐活动量):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'profile_setup', 'name': '设置档案', 'subfunction': '设置资料', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-profile-set --age <A> --gender <G> --height <H> --activity <L> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「设置档案」。\n\n我想设置基础档案(身高/年龄/性别/活动量)。如果我没说全,请一项一项问我,并根据我的日常情况推荐合适的活动量。设置完成后给我看:身高/年龄/性别/活动量 + 推荐活动量 + 设置时间。完成后给 1 句话总结,不需要过多文字解释。\n\n我的身高(cm):____\n年龄:____\n性别(男/女):____\n日常活动情况(选填,用于推荐活动量):____',
            'user_intent': '设置基础档案(身高/年龄/性别/活动量)', 'data_fields': ['height_cm', 'age', 'gender', 'activity_level', 'activity_factor', 'created_at'],
            'depends_on_external': False, 'order': 0},
    {
            'category': '基础信息',     'wake_word': '设活动量',     'desc': '单独设置活动量(含 TDEE 系数影响)',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-profile-activity <level> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「设活动量」。\n\n我要单独设置活动量(久坐/轻度/中度/活跃/高度活跃)。设置后请告诉我:活动等级、对应的消耗系数(TDEE 系数)、以及对我每日消耗的影响。完成后给 1 句话总结,不需要过多文字解释。\n\n我的活动量(久坐/轻度/中度/活跃/高度活跃):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'profile_set_activity', 'name': '设活动量', 'subfunction': '设置资料', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-profile-activity <level> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「设活动量」。\n\n我要单独设置活动量(久坐/轻度/中度/活跃/高度活跃)。设置后请告诉我:活动等级、对应的消耗系数(TDEE 系数)、以及对我每日消耗的影响。完成后给 1 句话总结,不需要过多文字解释。\n\n我的活动量(久坐/轻度/中度/活跃/高度活跃):____',
            'user_intent': '单独设置活动量', 'data_fields': ['activity_level', 'activity_factor', 'tdee'],
            'depends_on_external': False, 'order': 1},
    {
            'category': '基础信息',     'wake_word': '改档案',     'desc': '单字段或多字段修改档案(含改前/改后对比 + 影响提示)',
            'main_prompt': {
        'cli': 'python scripts/render_crud_receipt.py --live-profile-update --field <X> --value <Y> --chain "1.解析→2.写库→3.回执"', 'text': '请你加载技能 卡路里,执行唤醒词「改档案」。\n\n我要改档案里的字段(身高/年龄/性别/活动量/备注)。改之前请先确认我原来的值,改完后给我看:改前/改后对比 + 影响提示(如改身高影响 BMI、改活动量影响每日消耗)。完成后给 1 句话总结,不需要过多文字解释。\n\n我要改的字段(允许一行一条,可改多个):\n身高(新值):____\n年龄(新值):____\n性别(新值):____\n活动量(新值):____\n备注(新值):____'},
        'fill_hints': [],
            'variants': [],
            'key': 'profile_update', 'name': '改档案', 'subfunction': '改资料', 'output_type': 'receipt',
            'html_template': 'templates/crud_receipt.html', 'data_source': 'python scripts/render_crud_receipt.py --live-profile-update --field <X> --value <Y> --chain "1.解析→2.写库→3.回执"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「改档案」。\n\n我要改档案里的字段(身高/年龄/性别/活动量/备注)。改之前请先确认我原来的值,改完后给我看:改前/改后对比 + 影响提示(如改身高影响 BMI、改活动量影响每日消耗)。完成后给 1 句话总结,不需要过多文字解释。\n\n我要改的字段(允许一行一条,可改多个):\n身高(新值):____\n年龄(新值):____\n性别(新值):____\n活动量(新值):____\n备注(新值):____',
            'user_intent': '修改档案中的字段', 'data_fields': ['height_cm', 'age', 'gender', 'activity_level', 'note', 'bmi', 'tdee'],
            'depends_on_external': False, 'order': 0},
    {
            'category': '基础信息',     'wake_word': '查档案',     'desc': '查看完整档案(含活动量/最新体重/BMI/BMR/TDEE)',
            'main_prompt': {
        'cli': 'python scripts/render_crud_view.py --entity profile --chain "1.识别→2.读DB→3.算TDEE"', 'text': '请你加载技能 卡路里,执行唤醒词「查档案」。\n\n我想看自己的完整档案:身高/年龄/性别/活动量 + 最新体重 + BMI/BMR/TDEE(含活动量对应的消耗系数说明)。完成后给 1 句话总结,不需要过多文字解释。'},
        'fill_hints': [],
            'variants': [],
            'key': 'profile_view', 'name': '查档案', 'subfunction': '看档案', 'output_type': 'result',
            'html_template': 'templates/crud_view.html', 'data_source': 'python scripts/render_crud_view.py --entity profile --chain "1.识别→2.读DB→3.算TDEE"', 'prompt_template': '请你加载技能 卡路里,执行唤醒词「查档案」。\n\n我想看自己的完整档案:身高/年龄/性别/活动量 + 最新体重 + BMI/BMR/TDEE(含活动量对应的消耗系数说明)。完成后给 1 句话总结,不需要过多文字解释。',
            'user_intent': '查看档案及最新体重与身体指标', 'data_fields': ['height_cm', 'age', 'gender', 'activity_level', 'activity_factor', 'weight_kg', 'bmi', 'bmr', 'tdee'],
            'depends_on_external': False, 'order': 0}
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
