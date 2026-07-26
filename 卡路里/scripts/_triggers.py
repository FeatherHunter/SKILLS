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

# ========== 🏠 主页 (3) ==========
{
    'category': '主页',
    'wake_word': '开卡路里',
    'aliases':   ['卡路里面板'],
    'desc':     '打开主页 dashboard(今日 KPI + 待办 + 最近日志)',
    'main_prompt': {
        'cli':  'python scripts/render_home.py',
        'text': """卡路里技能 · 主页 dashboard

场景:用户需要打开今日总览(热量 + 待办 + KPI 卡片)
数据:今日 date 维度的全部健康指标 + 最近 7 天日志
期望:AI 调 {cli} 生成 HTML 页面给用户(V1.3 原则 11 强制 HTML)
来源:用户唤醒词 "开卡路里"
        """.strip(),
    },
    'variants': [
        {
            'label':  '开卡路里 [指定日期]',
            'cli':    'python scripts/render_home.py --date 2026-07-20',
            'prompt': """卡路里技能 · 主页 dashboard(指定日期)

场景:用户要查过去某一天的总览
数据:指定 date 的 dashboard 数据
期望:AI 解析日期 → 调 {cli}(--date YYYY-MM-DD)
来源:用户唤醒词含具体日期
            """.strip(),
        },
    ],
},
{
    'category': '主页',
    'wake_word': '今日卡路里',
    'desc':     '打开今日 dashboard(默认今日)',
    'main_prompt': {
        'cli':  'python scripts/render_home.py',
        'text': """卡路里技能 · 今日 dashboard

场景:用户打开今日默认 dashboard
数据:今日 date 全部健康指标
期望:AI 调 {cli} 生成 HTML
来源:用户唤醒词 "今日卡路里"(同义:开卡路里)
        """.strip(),
    },
    'variants': [],
},

# ========== 🍚 饮食记录 (9) ==========
{
    'category': '饮食记录',
    'wake_word': '记吃了',
    'desc':     '记录饮食(库匹配/图片识别/外部搜索统一入口)',
    'main_prompt': {
        'cli':  'python scripts/calorie_tracker.py add <食物> <热量> <蛋白> [碳水] [脂肪] [克数] [备注]',
        'text': """卡路里技能 · 记录饮食

场景:用户吃了东西,要把这条记录写进 food_log
数据:食物名 + 克数 + 4 大宏量(热量/蛋白/碳水/脂肪)
期望:AI 调 calorie_tracker.py add,字段不全时用库匹配 / 图片识别 / 搜索兜底
来源:用户自然语言描述(如 "吃了 1 个鸡蛋 50g")
        """.strip(),
    },
    'variants': [
        {
            'label':  '记吃了 [补录历史]',
            'cli':    'python scripts/calorie_tracker.py add ... --date 2026-07-20 --time 12:30',
            'prompt': """卡路里技能 · 补录历史饮食

场景:用户现在才想起要补录之前的饮食
数据:food_log(date/time/food_name/grams/calories/protein/carbs/fat)
期望:AI 解析日期时间 → 调 {cli} 加 --date --time --meal 参数
来源:用户说 "刚才 / 昨天 / 上周X" 等补录语境
            """.strip(),
        },
    ],
},
{
    'category': '饮食记录',
    'wake_word': '拍营养表',
    'desc':     '图片识别营养成分表并记录',
    'main_prompt': {
        'cli':  'mmx vision describe <图片> → python scripts/calorie_tracker.py add',
        'text': """卡路里技能 · 拍营养表

场景:用户拍了食物包装/营养表的图片
数据:mmx vision 输出结构化营养字段(food_name/calories/protein/carbs/fat)
期望:AI 调 mmx vision describe 提取 → 解析 → 调 calorie_tracker.py add 存库
来源:用户上传图片 + 说 "拍营养表"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '饮食记录',
    'wake_word': '删吃的',
    'desc':     '删除饮食记录(生成 crud_receipt 回执)',
    'main_prompt': {
        'cli':  'python scripts/calorie_tracker.py delete <id>',
        'text': """卡路里技能 · 删除饮食记录

场景:用户要删某条饮食记录
数据:food_log 指定 id
期望:AI 解析要删的 id → 调 {cli} → 生成 crud_receipt.html 回执
来源:用户说 "删 N" 或描述具体记录
        """.strip(),
    },
    'variants': [],
},
{
    'category': '饮食记录',
    'wake_word': '改吃的',
    'desc':     '修改已记录饮食(8 字段)',
    'main_prompt': {
        'cli':  'python scripts/calorie_tracker.py update-meal <id> [--grams] [--food] [--calories] [--protein] [--carbs] [--fat] [--date] [--time] [--note]',
        'text': """卡路里技能 · 改饮食记录

场景:用户发现某条饮食记录有误需要修改
数据:food_log 指定 id,8 字段(food/grams/calories/protein/carbs/fat/date/time/note)
期望:AI 定位 id → 调 update-meal ... --field value → 生成 crud_receipt.html 回执
来源:用户说 "改 N,K 改成 V"(如 "改 5 克数改成 180")
        """.strip(),
    },
    'variants': [],
},
{
    'category': '饮食记录',
    'wake_word': '查今天吃',
    'desc':     '今日饮食摘要(4 餐)',
    'main_prompt': {
        'cli':  'python scripts/render_today_diet.py',
        'text': """卡路里技能 · 今日饮食摘要

场景:用户要查今日吃了什么、热量摄入、营养结构
数据:food_log WHERE date=今日 + daily_goal
期望:AI 调 {cli} 生成 HTML(V1.3 强制)
来源:用户唤醒词 "查今天吃"
        """.strip(),
    },
    'variants': [
        {
            'label':  '查今天吃 昨天',
            'cli':    'python scripts/render_today_diet.py --date 2026-07-25',
            'prompt': """卡路里技能 · 昨日饮食摘要

场景:用户要查昨天饮食
数据:food_log WHERE date=指定
期望:AI 解析日期 → 调 {cli} 加 --date
来源:"查今天吃 昨天"
            """.strip(),
        },
    ],
},
{
    'category': '饮食记录',
    'wake_word': '查吃的记录',
    'desc':     '今日逐条饮食记录(list)',
    'main_prompt': {
        'cli':  'python scripts/render_today_meals.py',
        'text': """卡路里技能 · 今日逐条饮食

场景:用户要逐条看今天吃了什么
数据:food_log WHERE date=今日 所有条目
期望:AI 调 {cli} 生成 HTML(列表视图,非摘要)
来源:"查吃的记录"
        """.strip(),
    },
    'variants': [
        {
            'label':  '查吃的记录 昨天',
            'cli':    'python scripts/render_today_meals.py --date 2026-07-25',
            'prompt': '数据:food_log WHERE date=指定\n期望:AI 解析日期 → 调 {cli} 加 --date\n来源:"查吃的记录 昨天"\n',
        },
        {
            'label':  '查吃的记录 7/1 到 7/14',
            'cli':    'python scripts/render_today_meals.py --start 2026-07-01 --end 2026-07-14',
            'prompt': '数据:food_log 区间\n期望:AI 解析区间 → 调 {cli} --start --end\n来源:"查吃的记录 7/1 到 7/14"\n',
        },
    ],
},
{
    'category': '饮食记录',
    'wake_word': '查热量历史',
    'desc':     '最近 N 天热量摄入历史',
    'main_prompt': {
        'cli':  'python scripts/render_calorie_trend.py --days 7',
        'text': """卡路里技能 · 热量历史

场景:用户查最近 7 天每日热量趋势
数据:food_log SUM(calories) GROUP BY date
期望:AI 调 {cli} 默认 7 天
来源:"查热量历史"
        """.strip(),
    },
    'variants': [
        {
            'label':  '查热量历史 30 天',
            'cli':    'python scripts/render_calorie_trend.py --days 30',
            'prompt': '数据:最近 30 天\n期望:AI 解析 → --days 30\n来源:"查热量历史 30 天"\n',
        },
    ],
},
{
    'category': '饮食记录',
    'wake_word': '记喝水',
    'desc':     '记录饮水量',
    'main_prompt': {
        'cli':  'python scripts/calorie_tracker.py water <ml>',
        'text': """卡路里技能 · 记录饮水

场景:用户喝了一杯水,要记录
数据:water_ml(food_log food_name='💧水')
期望:AI 解析 ml 数 → 调 {cli}
来源:"记喝水 500ml" / "喝了一杯水约 250ml"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '饮食记录',
    'wake_word': '查今天喝水',
    'desc':     '今日饮水量',
    'main_prompt': {
        'cli':  'python scripts/calorie_tracker.py summary',
        'text': """卡路里技能 · 查今天饮水

场景:用户查今日喝水量
数据:food_log WHERE date=今日 AND food_name='💧水'
期望:AI 调 calorie_tracker.py summary(返回含 water 字段)
来源:"查今天喝水"
        """.strip(),
    },
    'variants': [],
},

# ========== 📦 食品库 (6) ==========
{
    'category': '食品库',
    'wake_word': '查热量',
    'desc':     '搜索食品营养成分',
    'main_prompt': {
        'cli':  'python scripts/calorie_tracker.py search-product <关键词>',
        'text': """卡路里技能 · 搜食品营养成分

场景:用户想查某食物的热量/蛋白/碳水/脂肪
数据:nutrition_products 表 LIKE 搜索
期望:AI 解析关键词 → 调 {cli}
来源:"查热量 可乐"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '食品库',
    'wake_word': '存食品',
    'desc':     '添加食品营养成分到库',
    'main_prompt': {
        'cli':  'python scripts/calorie_tracker.py add-product <名称> <品牌> <热量> <蛋白质> <脂肪> <饱和脂肪> <碳水> <糖> <膳食纤维> <钠>',
        'text': """卡路里技能 · 存食品到库

场景:用户要把新食品的营养数据写入 nutrition_products
数据:10 个营养字段(必填 7)
期望:AI 解析后调 {cli} → 生成 crud_receipt 回执
来源:"存食品 <name> <brand> ..." 或图片识别结果
        """.strip(),
    },
    'variants': [],
},
{
    'category': '食品库',
    'wake_word': '改食品',
    'desc':     '更新食品营养数据',
    'main_prompt': {
        'cli':  'python scripts/calorie_tracker.py update-product <id> [--calories] [--protein] ...',
        'text': """卡路里技能 · 改食品

场景:用户发现库里的某食品数据要更新
数据:nutrition_products 指定 id
期望:AI 解析字段 → 调 {cli} → 回执
来源:"改食品 <id> <字段> = <值>"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '食品库',
    'wake_word': '查食品库',
    'desc':     '列出全部食品营养成分',
    'main_prompt': {
        'cli':  'python scripts/calorie_tracker.py list-products',
        'text': """卡路里技能 · 列出全部食品

场景:用户要遍历整个食品库
数据:nutrition_products 全表
期望:AI 调 {cli}
来源:"查食品库"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '食品库',
    'wake_word': '批量导入',
    'desc':     '批量录入/更新食品库',
    'main_prompt': {
        'cli':  'python scripts/batch_import.py import <file.jsonl>',
        'text': """卡路里技能 · 批量导入食品

场景:用户有一个 JSONL 文件要批量入库
数据:JSONL 每行 1 条食品(必填 7 字段)
期望:AI 调 batch_import.py validate 先校验 → 通过后 import
来源:"批量导入 /path/to/file.jsonl"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '食品库',
    'wake_word': '校验批量',
    'desc':     '只校验 JSONL 不写入',
    'main_prompt': {
        'cli':  'python scripts/batch_import.py validate <file.jsonl>',
        'text': """卡路里技能 · 校验 JSONL

场景:用户要确认文件能导入但先不写库
数据:JSONL 文件
期望:AI 调 {cli} 返回 status ok/warn/fail
来源:"校验批量 /path/to/file.jsonl"
        """.strip(),
    },
    'variants': [],
},

# ========== ⚖️ 体重 (8) ==========
{
    'category': '体重',
    'wake_word': '记体重',
    'desc':     '记录体重(身高自动从 user_profile 读)',
    'main_prompt': {
        'cli':  'python scripts/calorie_tracker.py weight <kg> [--note "<备注>"]',
        'text': """卡路里技能 · 记录体重

场景:用户刚称了体重
数据:weight_log(身高自动从 user_profile 读,BMI 自动算)
期望:AI 解析 kg → 调 {cli};有备注则加 --note
来源:"记体重 70.5" / "刚称了 71kg 我今天吃饱了"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '体重',
    'wake_word': '改体重记录',
    'desc':     '修改历史体重记录',
    'main_prompt': {
        'cli':  'python scripts/calorie_tracker.py weight-update <id> [--weight <kg>] [--note <备注>]',
        'text': """卡路里技能 · 改体重记录

场景:用户发现历史体重数据错了
数据:weight_log 指定 id
期望:AI 解析 id + 新字段 → 调 {cli} → 回执
来源:"改体重 <id> 改成 X"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '体重',
    'wake_word': '查体重历史',
    'desc':     '体重历史记录(mode=history)',
    'main_prompt': {
        'cli':  'python scripts/render_weight_history.py --mode history --days 30',
        'text': """卡路里技能 · 体重历史

场景:用户看最近 N 天体重列表
数据:weight_log 最近 N 天
期望:AI 调 {cli} 默认 30 天 mode=history
来源:"查体重历史"
        """.strip(),
    },
    'variants': [
        {
            'label':  '查体重历史 上周',
            'cli':    'python scripts/render_weight_history.py --mode history --days 7',
            'prompt': '数据:weight_log 最近 7 天\n期望:--days 7\n来源:"查体重历史 上周"\n',
        },
        {
            'label':  '查体重历史 7/1 到 7/31',
            'cli':    'python scripts/render_weight_history.py --mode history --start 2026-07-01 --end 2026-07-31',
            'prompt': '数据:weight_log 整月\n期望:AI 解析区间 → --start --end\n来源:"查体重历史 7/1 到 7/31"\n',
        },
    ],
},
{
    'category': '体重',
    'wake_word': '查体重趋势',
    'desc':     '体重趋势分析(折线图 + 起始结束对比,mode=trend)',
    'main_prompt': {
        'cli':  'python scripts/render_weight_history.py --mode trend --days 30',
        'text': """卡路里技能 · 体重趋势

场景:用户看体重折线图走势
数据:weight_log 最近 30 天
期望:AI 调 {cli} 默认 30 天 mode=trend
来源:"查体重趋势"
        """.strip(),
    },
    'variants': [
        {
            'label':  '查体重趋势 上周',
            'cli':    'python scripts/render_weight_history.py --mode trend --days 7',
            'prompt': '数据:最近 7 天\n期望:--days 7\n来源:"查体重趋势 上周"\n',
        },
        {
            'label':  '查体重趋势 昨天',
            'cli':    'python scripts/render_weight_history.py --mode trend --start 2026-07-25 --end 2026-07-25',
            'prompt': '数据:weight_log 单日\n期望:--start --end 同值\n来源:"查体重趋势 昨天"\n',
        },
        {
            'label':  '查体重趋势 7/1 到 7/14',
            'cli':    'python scripts/render_weight_history.py --mode trend --start 2026-07-01 --end 2026-07-14',
            'prompt': '数据:区间\n期望:--start --end\n来源:"查体重趋势 7/1 到 7/14"\n',
        },
        {
            'label':  '查体重趋势 7 月',
            'cli':    'python scripts/render_weight_history.py --mode trend --start 2026-07-01 --end 2026-07-31',
            'prompt': '数据:整月\n期望:--start 1 号 --end 月底\n来源:"查体重趋势 7月"\n',
        },
        {
            'label':  '查体重趋势 最近 90 天',
            'cli':    'python scripts/render_weight_history.py --mode trend --days 90',
            'prompt': '数据:最近 90 天\n期望:--days 90\n来源:"查体重趋势 最近 90 天"\n',
        },
    ],
},
{
    'category': '体重',
    'wake_word': '对比体重',
    'desc':     '两时间段体重对比(mode=compare)',
    'main_prompt': {
        'cli':  'python scripts/render_weight_history.py --mode compare --days 30',
        'text': """卡路里技能 · 体重对比

场景:用户对比两段时间的体重差异
数据:weight_log 前期 vs 后期均重
期望:AI 调 {cli} mode=compare 默认 30 天
来源:"对比体重"
        """.strip(),
    },
    'variants': [
        {
            'label':  '对比体重 7/1 到 7/31',
            'cli':    'python scripts/render_weight_history.py --mode compare --start 2026-07-01 --end 2026-07-31',
            'prompt': '数据:整月\n期望:--start --end 月内\n来源:"对比体重 7月"\n',
        },
    ],
},
{
    'category': '体重',
    'wake_word': '查体重波动',
    'desc':     '体重波动分析(标准差 + 异常点,mode=volatility)',
    'main_prompt': {
        'cli':  'python scripts/render_weight_history.py --mode volatility --days 30',
        'text': """卡路里技能 · 体重波动

场景:用户看体重波动大小 + 异常点(2σ)
数据:weight_log 标准差 / 异常点
期望:AI 调 {cli} mode=volatility 默认 30 天
来源:"查体重波动"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '体重',
    'wake_word': '设体重目标',
    'desc':     '设置体重目标 + 截止日期',
    'main_prompt': {
        'cli':  'python scripts/calorie_tracker.py weight-goal <kg> [deadline YYYY-MM-DD]',
        'text': """卡路里技能 · 设体重目标

场景:用户要设减重/增重目标
数据:daily_goal 表 weight_goal + goal_deadline
期望:AI 解析 kg + 截止日期(可选) → 调 {cli}
来源:"设体重目标 70 2026-09-01"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '体重',
    'wake_word': '查体重目标',
    'desc':     '体重目标达成进度',
    'main_prompt': {
        'cli':  'python scripts/calorie_tracker.py weight-goal-progress',
        'text': """卡路里技能 · 查体重目标进度

场景:用户看体重目标完成度
数据:weight_goal + 最新体重 + 时间
期望:AI 调 {cli}
来源:"查体重目标"
        """.strip(),
    },
    'variants': [],
},

# ========== 🏃 运动 (6) ==========
{
    'category': '运动',
    'wake_word': '记运动',
    'desc':     '记录运动消耗',
    'main_prompt': {
        'cli':  'python scripts/exercise_tracker.py add --date YYYY-MM-DD --type <类型> --calories <卡> [--minutes N] [--reps N]',
        'text': """卡路里技能 · 记录运动

场景:用户做了一项运动,要记下来
数据:exercise_log(运动类型/消耗/时长/次数)
期望:AI 解析参数 → 调 {cli}
来源:"记运动 跑步 300 卡 30 分钟"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '运动',
    'wake_word': '改运动记录',
    'desc':     '更新运动记录',
    'main_prompt': {
        'cli':  'python scripts/exercise_tracker.py update --id <id> [--type] [--calories] [--minutes] ...',
        'text': """卡路里技能 · 改运动

场景:用户发现运动数据要改
数据:exercise_log 指定 id
期望:AI 解析字段 → 调 {cli} → 回执
来源:"改运动 <id> 改成 X"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '运动',
    'wake_word': '查运动记录',
    'desc':     '查询运动记录(mode=records)',
    'main_prompt': {
        'cli':  'python scripts/render_exercise_summary.py --mode records --days 7',
        'text': """卡路里技能 · 查运动记录

场景:用户看最近 N 天运动 list
数据:exercise_log 最近 7 天
期望:AI 调 {cli} mode=records
来源:"查运动记录"
        """.strip(),
    },
    'variants': [
        {
            'label':  '查运动记录 30 天',
            'cli':    'python scripts/render_exercise_summary.py --mode records --days 30',
            'prompt': '数据:30 天\n期望:--days 30\n来源:"查运动记录 30 天"\n',
        },
    ],
},
{
    'category': '运动',
    'wake_word': '查运动汇总',
    'desc':     '运动汇总统计(mode=summary)',
    'main_prompt': {
        'cli':  'python scripts/render_exercise_summary.py --mode summary --days 7',
        'text': """卡路里技能 · 运动汇总

场景:用户看运动卡路里总消耗 + 总时长 + 活跃天数
数据:exercise_log 最近 7 天聚合
期望:AI 调 {cli} mode=summary
来源:"查运动汇总"
        """.strip(),
    },
    'variants': [
        {
            'label':  '查运动汇总 7 月',
            'cli':    'python scripts/render_exercise_summary.py --mode summary --start 2026-07-01 --end 2026-07-31',
            'prompt': '数据:整月\n期望:AI 解析 → --start --end\n来源:"查运动汇总 7月"\n',
        },
    ],
},
{
    'category': '运动',
    'wake_word': '查运动类型',
    'desc':     '运动类型统计(力量/有氧/柔韧/日常)',
    'main_prompt': {
        'cli':  'python scripts/render_exercise_summary.py --mode stats --days 7',
        'text': """卡路里技能 · 运动类型分布

场景:用户看 4 类运动占比
数据:exercise_log GROUP BY category
期望:AI 调 {cli} mode=stats
来源:"查运动类型"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '运动',
    'wake_word': '查运动趋势',
    'desc':     '运动热量趋势(mode=trend,面积图)',
    'main_prompt': {
        'cli':  'python scripts/render_exercise_summary.py --mode trend --days 7',
        'text': """卡路里技能 · 运动趋势

场景:用户看每日运动消耗面积图
数据:exercise_log daily SUM(calories_burned)
期望:AI 调 {cli} mode=trend
来源:"查运动趋势"
        """.strip(),
    },
    'variants': [],
},

# ========== 💪 健身计划 (10) ==========
{
    'category': '健身计划',
    'wake_word': '查健身计划',
    'aliases':   ['查询健身计划'],
    'desc':     '查看训练计划 HTML 页面(DB 数据驱动)',
    'main_prompt': {
        'cli':  'python scripts/render_workout_plan.py',
        'text': """卡路里技能 · 查健身计划

场景:用户看完整的健身计划 + 今日复盘 section
数据:workout_plan_config + workout_plans
期望:AI 调 {cli} 生成 HTML
来源:"查健身计划" / "查询健身计划"
        """.strip(),
    },
    'variants': [
        {
            'label':  '查健身计划 --review',
            'cli':    'python scripts/render_workout_plan.py --review',
            'prompt': '数据:含今日复盘\n期望:--review 标志\n来源:"查健身计划 含复盘"\n',
        },
    ],
},
{
    'category': '健身计划',
    'wake_word': '制定健身计划',
    'desc':     'AI 采访式对话 → 校验 → 写入',
    'main_prompt': {
        'cli':  'AI 路由 → python scripts/plan_generator.py',
        'text': """卡路里技能 · 制定健身计划

场景:用户要新设一份完整健身计划
数据:workout_plans(week/day/session/movements)
期望:AI 采集 8 个维度(目标/经验/频率/部位/时间...) → 调 plan_generator.py
来源:"制定健身计划"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '健身计划',
    'wake_word': '改健身计划',
    'desc':     'AI 对话定位意图 → 改/增/删时段、调整周次',
    'main_prompt': {
        'cli':  'AI 路由 → python scripts/plan_generator.py',
        'text': """卡路里技能 · 改健身计划

场景:用户要修改既有健身计划的某部分
数据:workout_plans
期望:AI 解析意图(改哪个时段/增删哪个动作/调周次) → 调 plan_generator.py
来源:"改健身计划 周三加一组卧推"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '健身计划',
    'wake_word': '落地健身计划',
    'desc':     '将某天计划执行(补计划 + 记心愿 + 训记推送)',
    'main_prompt': {
        'cli':  '组合:补计划 + 记心愿 + 训记推送 → HTML:process_progress.html',
        'text': """卡路里技能 · 落地健身计划

场景:用户要把今天/某天的计划真正执行一次
数据:workout_plans + xunji_push
期望:AI 调 3 个子流程(补计划 + 记心愿 + 训记推送)→ 生成 process_progress.html
来源:"落地健身计划 2026-07-26"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '健身计划',
    'wake_word': '卡路里同步',
    'desc':     '批量落地 3 天 + 调「回写训记」',
    'main_prompt': {
        'cli':  '组合:落地健身计划 × 3 + 回写训记 → HTML:process_progress.html',
        'text': """卡路里技能 · 卡路里同步

场景:用户要把最近 3 天的计划批量落地
数据:workout_plans + xunji_backfill
期望:AI 调落地 × 3 + 回写训记 → process_progress.html
来源:"卡路里同步"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '健身计划',
    'wake_word': '回写训记',
    'desc':     '拉训记数据回写 exercise_log(幂等)',
    'main_prompt': {
        'cli':  'python scripts/xunji_bridge.py backfill [--date <DATE>] [--days <N>]',
        'text': """卡路里技能 · 回写训记

场景:用户要把训记的训练数据拉过来写入 exercise_log
数据:xunji API → exercise_log
期望:AI 调 {cli} --date 单日 / --days N
来源:"回写训记 2026-07-20" / "回写训记 最近 7 天"
        """.strip(),
    },
    'variants': [
        {
            'label':  '回写训记 最近 7 天',
            'cli':    'python scripts/xunji_bridge.py backfill --days 7',
            'prompt': '数据:xunji 最近 7 天\n期望:--days 7\n来源:"回写训记 最近 7 天"\n',
        },
    ],
},
{
    'category': '健身计划',
    'wake_word': '训记-覆盖X日的训练计划',
    'desc':     '用卡路里 plan 覆盖训记某天训练',
    'main_prompt': {
        'cli':  'python scripts/xunji_bridge.py overlay-plan --date <DATE>',
        'text': """卡路里技能 · 训记覆盖某日

场景:用户要把卡路里的 plan 推到训记去覆盖同一天
数据:workout_plans.date → xunji
期望:AI 解析日期 → 调 {cli} --date
来源:"训记-覆盖 2026-07-26 的训练计划"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '健身计划',
    'wake_word': '复盘训练',
    'desc':     '对指定时间段做 plan vs 实绩对比',
    'main_prompt': {
        'cli':  'python scripts/render_exercise_review_html.py --days 7',
        'text': """卡路里技能 · 复盘训练

场景:用户对比健身计划 vs 实际完成情况
数据:workout_plans + exercise_log,完成率/漏做/超额
期望:AI 调 {cli} 默认 7 天
来源:"复盘训练"
        """.strip(),
    },
    'variants': [
        {
            'label':  '复盘训练 今天',
            'cli':    'python scripts/render_exercise_review_html.py --start 2026-07-26 --end 2026-07-26',
            'prompt': '数据:当天\n期望:--start --end 同值\n来源:"复盘训练 今天"\n',
        },
        {
            'label':  '复盘训练 这周',
            'cli':    'python scripts/render_exercise_review_html.py --days 7',
            'prompt': '数据:本周\n期望:--days 7\n来源:"复盘训练 这周"\n',
        },
    ],
},
{
    'category': '健身计划',
    'wake_word': '扫禁忌',
    'desc':     '检测 plan/DB 中禁忌动作(腰/膝/肩)',
    'main_prompt': {
        'cli':  'python scripts/render_contraindication.py',
        'text': """卡路里技能 · 扫禁忌

场景:用户要扫出健身计划里可能伤腰/膝/肩的动作
数据:workout_plans.movements
期望:AI 调 {cli} 默认全身位 → 禁忌报告 HTML
来源:"扫禁忌"
        """.strip(),
    },
    'variants': [
        {
            'label':  '扫禁忌 腰',
            'cli':    'python scripts/render_contraindication.py --part 腰',
            'prompt': '数据:仅腰\n期望:--part 腰\n来源:"扫禁忌 腰"\n',
        },
        {
            'label':  '扫禁忌 膝',
            'cli':    'python scripts/render_contraindication.py --part 膝',
            'prompt': '数据:仅膝\n来源:"扫禁忌 膝"\n',
        },
        {
            'label':  '扫禁忌 肩',
            'cli':    'python scripts/render_contraindication.py --part 肩',
            'prompt': '数据:仅肩\n来源:"扫禁忌 肩"\n',
        },
    ],
},
{
    'category': '健身计划',
    'wake_word': '审计动作名',
    'desc':     '扫描 plan 里非训记官方动作名(push-plan 前必跑)',
    'main_prompt': {
        'cli':  'python scripts/audit_plan_names.py [--strict] [--fix-suggestions]',
        'text': """卡路里技能 · 审计动作名

场景:用户要在推送训记前先确认 plan 里的动作名都能映射
数据:workout_plans.movements vs xunji 官方动作名
期望:AI 调 {cli};strict 模式遇不匹配 exit 非 0
来源:"审计动作名"
        """.strip(),
    },
    'variants': [],
},

# ========== 📊 分析 (11) ==========
{
    'category': '分析',
    'wake_word': '查热量趋势',
    'desc':     '热量摄入趋势',
    'main_prompt': {
        'cli':  'python scripts/render_calorie_trend.py --days 7',
        'text': """卡路里技能 · 热量趋势

场景:用户看每日热量摄入趋势
数据:food_log SUM(calories) GROUP BY date
期望:AI 调 {cli}
来源:"查热量趋势"
        """.strip(),
    },
    'variants': [
        {
            'label':  '查热量趋势 上周',
            'cli':    'python scripts/render_calorie_trend.py --days 7',
            'prompt': '数据:已过去 7 天\n期望:--days 7\n',
        },
        {
            'label':  '查热量趋势 7 月',
            'cli':    'python scripts/render_calorie_trend.py --start 2026-07-01 --end 2026-07-31',
            'prompt': '数据:整月\n期望:--start --end\n',
        },
        {
            'label':  '查热量趋势 最近 30 天',
            'cli':    'python scripts/render_calorie_trend.py --days 30',
            'prompt': '数据:30 天\n期望:--days 30\n',
        },
    ],
},
{
    'category': '分析',
    'wake_word': '查营养结构',
    'desc':     '营养素占比分析',
    'main_prompt': {
        'cli':  'python scripts/render_nutrition_ratio.py --days 7',
        'text': """卡路里技能 · 营养结构

场景:用户看蛋白/碳水/脂肪占比
数据:food_log SUM 4 大宏量 → 百分比
期望:AI 调 {cli}
来源:"查营养结构"
        """.strip(),
    },
    'variants': [
        {
            'label':  '查营养结构 7 月',
            'cli':    'python scripts/render_nutrition_ratio.py --start 2026-07-01 --end 2026-07-31',
            'prompt': '数据:整月\n期望:--start --end\n',
        },
    ],
},
{
    'category': '分析',
    'wake_word': '查热量缺口',
    'desc':     '热量缺口分析(摄入 vs 运动 vs TDEE)',
    'main_prompt': {
        'cli':  'python scripts/render_calorie_deficit.py --days 7',
        'text': """卡路里技能 · 热量缺口

场景:用户看摄入 vs 运动消耗的缺口
数据:food_log + exercise_log + TDEE
期望:AI 调 {cli}
来源:"查热量缺口"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '分析',
    'wake_word': '查食物排行',
    'desc':     '食物排行榜(默认高热量榜)',
    'main_prompt': {
        'cli':  'python scripts/render_food_ranking.py --days 7',
        'text': """卡路里技能 · 食物排行(默认高热量)

场景:用户看 TOP 食物热量榜
数据:food_log SUM(calories) GROUP BY food_name
期望:AI 调 {cli}
来源:"查食物排行"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '分析',
    'wake_word': '查高热量榜',
    'desc':     '热量炸弹 TOP5',
    'main_prompt': {
        'cli':  'python scripts/render_food_ranking.py --days 7 --category high_calorie',
        'text': """卡路里技能 · 高热量榜

场景:用户看最高热量食物 TOP5
数据:同查食物排行 + category=high_calorie
期望:AI 调 {cli}
来源:"查高热量榜"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '分析',
    'wake_word': '查低热量榜',
    'desc':     '低热量健康 TOP5',
    'main_prompt': {
        'cli':  'python scripts/render_food_ranking.py --days 7 --category low_calorie',
        'text': """卡路里技能 · 低热量榜

场景:用户看最低热量食物 TOP5
数据:同查食物排行 + category=low_calorie
期望:AI 调 {cli}
来源:"查低热量榜"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '分析',
    'wake_word': '查频繁吃榜',
    'desc':     '最常吃的食物 TOP5',
    'main_prompt': {
        'cli':  'python scripts/render_food_ranking.py --days 7 --category frequent',
        'text': """卡路里技能 · 频繁吃榜

场景:用户看吃最多次的食物
数据:food_log COUNT GROUP BY food_name
期望:AI 调 {cli} --category frequent
来源:"查频繁吃榜"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '分析',
    'wake_word': '查高碳水榜',
    'desc':     '高碳水食物 TOP5',
    'main_prompt': {
        'cli':  'python scripts/render_food_ranking.py --days 7 --category high_carb',
        'text': """卡路里技能 · 高碳水榜

场景:用户看碳水最高的食物
数据:food_log SUM(carbs) GROUP BY food_name
期望:AI 调 {cli} --category high_carb
来源:"查高碳水榜"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '分析',
    'wake_word': '查高蛋白榜',
    'desc':     '高蛋白食物 TOP5',
    'main_prompt': {
        'cli':  'python scripts/render_food_ranking.py --days 7 --category high_protein',
        'text': """卡路里技能 · 高蛋白榜

场景:用户看蛋白最高的食物
数据:food_log SUM(protein) GROUP BY food_name
期望:AI 调 {cli} --category high_protein
来源:"查高蛋白榜"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '分析',
    'wake_word': '查运动分布',
    'desc':     '运动类型分布',
    'main_prompt': {
        'cli':  'python scripts/render_exercise_distribution.py --days 7',
        'text': """卡路里技能 · 运动分布

场景:用户看 4 类运动(力量/有氧/柔韧/日常)的时间/消耗分布
数据:exercise_log GROUP BY category
期望:AI 调 {cli} 默认 distribution
来源:"查运动分布"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '分析',
    'wake_word': '查运动贡献',
    'desc':     '运动对热量缺口的贡献占比',
    'main_prompt': {
        'cli':  'python scripts/render_exercise_distribution.py --days 7 --mode contribution',
        'text': """卡路里技能 · 运动贡献

场景:用户看运动在热量缺口里的占比
数据:exercise_log + food_log + TDEE
期望:AI 调 {cli} --mode contribution
来源:"查运动贡献"
        """.strip(),
    },
    'variants': [],
},

# ========== 📋 综合 (4) ==========
{
    'category': '综合',
    'wake_word': '设营养目标',
    'desc':     '设置每日营养目标',
    'main_prompt': {
        'cli':  'python scripts/calorie_tracker.py goal <热量> <蛋白> <碳水> <脂肪> [饮水ml]',
        'text': """卡路里技能 · 设营养目标

场景:用户要改每日 4 大宏量 + 饮水目标
数据:daily_goal 表
期望:AI 解析 4 个数字 → 调 {cli}
来源:"设营养目标 1850 150 200 50 2000"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '综合',
    'wake_word': '查营养目标',
    'desc':     '查看当前每日营养目标',
    'main_prompt': {
        'cli':  'python scripts/calorie_tracker.py get-goal',
        'text': """卡路里技能 · 查营养目标

场景:用户要查当前的 goal 值
数据:daily_goal 表
期望:AI 调 {cli}
来源:"查营养目标"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '综合',
    'wake_word': '查健康报告',
    'desc':     '四维度综合健康仪表盘',
    'main_prompt': {
        'cli':  'python scripts/render_health_dashboard.py --days 7',
        'text': """卡路里技能 · 查健康报告

场景:用户看 4 维健康仪表盘
数据:热量/营养/运动/体重 综合
期望:AI 调 {cli} 默认 7 天
来源:"查健康报告"
        """.strip(),
    },
    'variants': [
        {
            'label':  '查健康报告 本月',
            'cli':    'python scripts/render_health_dashboard.py --start 2026-07-01 --end 2026-07-26',
            'prompt': '数据:本月\n期望:AI 解析 → --start 1 号 --end 今天\n',
        },
    ],
},
{
    'category': '综合',
    'wake_word': '查卡路里数据',
    'desc':     '数据健康检查(lint_health)',
    'main_prompt': {
        'cli':  'python scripts/render_lint_health.py',
        'text': """卡路里技能 · 查卡路里数据

场景:用户要检查 DB 数据完整性
数据:lint_health() 扫描所有表
期望:AI 调 {cli} → lint_health.html
来源:"查卡路里数据"
        """.strip(),
    },
    'variants': [],
},

# ========== 🔄 复盘 (7) ==========
{
    'category': '复盘',
    'wake_word': '复盘',
    'desc':     '立即生成复盘 + 飞书发送(默认过去 7 天)',
    'main_prompt': {
        'cli':  'python scripts/render_review.py',
        'text': """卡路里技能 · 复盘

场景:用户要拉一份完整复盘报告(含 8 dim)
数据:review_engine 7 维 SQL + 衍生计算
期望:AI 调 {cli} → review_template.html → 飞书发送
来源:"复盘"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '复盘',
    'wake_word': '今日复盘',
    'aliases':   ['复盘今日', '日复盘'],
    'desc':     '当日复盘',
    'main_prompt': {
        'cli':  'python scripts/render_review.py --type day',
        'text': """卡路里技能 · 今日复盘

场景:用户要当日复盘
数据:今日全维
期望:AI 调 {cli} --type day
来源:"今日复盘"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '复盘',
    'wake_word': '本周复盘',
    'aliases':   ['复盘本周', '周复盘'],
    'desc':     '本周复盘(本周一-今天)',
    'main_prompt': {
        'cli':  'python scripts/render_review.py --type week',
        'text': """卡路里技能 · 本周复盘

场景:用户要本周复盘
数据:本周一-今天
期望:AI 调 {cli} --type week
来源:"本周复盘"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '复盘',
    'wake_word': '本月复盘',
    'aliases':   ['复盘本月', '月复盘'],
    'desc':     '本月复盘(本月 1 号-今天)',
    'main_prompt': {
        'cli':  'python scripts/render_review.py --type month',
        'text': """卡路里技能 · 本月复盘

场景:用户要本月复盘
数据:本月 1 号-今天
期望:AI 调 {cli} --type month
来源:"本月复盘"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '复盘',
    'wake_word': '本年复盘',
    'aliases':   ['复盘本年', '年复盘'],
    'desc':     '本年复盘(今年 1/1-今天)',
    'main_prompt': {
        'cli':  'python scripts/render_review.py --type year',
        'text': """卡路里技能 · 本年复盘

场景:用户要本年复盘
数据:今年 1/1-今天
期望:AI 调 {cli} --type year
来源:"本年复盘"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '复盘',
    'wake_word': '复盘日期范围',
    'desc':     '自定义日期范围复盘',
    'main_prompt': {
        'cli':  'python scripts/render_review.py --range 2026-07-01:2026-07-14',
        'text': """卡路里技能 · 复盘(自定义范围)

场景:用户要任意日期范围复盘
数据:指定 start:end
期望:AI 解析日期 → 调 {cli} --range X:Y
来源:"复盘 7/1 到 7/14" / "复盘 2026-07-01:2026-07-14"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '复盘',
    'wake_word': '开启定时复盘',
    'desc':     '启动 cron(默认 23:00 / 过去 7 天)',
    'main_prompt': {
        'cli':  'mavis cron create ...',
        'text': """卡路里技能 · 开启定时复盘

场景:用户要设每天自动跑复盘
数据:mavis cron
期望:AI 调 mavis cron create 装 cron
来源:"开启定时复盘"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '复盘',
    'wake_word': '关闭定时复盘',
    'desc':     '删除 cron',
    'main_prompt': {
        'cli':  'mavis cron delete ...',
        'text': """卡路里技能 · 关闭定时复盘

场景:用户要关掉每天自动复盘
数据:mavis cron
期望:AI 调 mavis cron delete
来源:"关闭定时复盘"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '复盘',
    'wake_word': '查定时复盘',
    'desc':     '查看当前定时复盘配置',
    'main_prompt': {
        'cli':  'mavis cron list',
        'text': """卡路里技能 · 查定时复盘

场景:用户要查 cron 配置
数据:mavis cron list
期望:AI 调 {cli}
来源:"查定时复盘"
        """.strip(),
    },
    'variants': [],
},

# ========== 🧬 身体成分 (5) ==========
{
    'category': '身体成分',
    'wake_word': '记体脂',
    'desc':     '皮褶钳测 7 点(Jackson-Pollock 自动算体脂率)',
    'main_prompt': {
        'cli':  'python scripts/body_composition.py add ... → HTML:body_composition_wizard.html',
        'text': """卡路里技能 · 记体脂

场景:用户用皮褶钳测了 7 点(胸/腹/大腿/三头/肩胛下/髂上/腋中)
数据:body_composition 表 7 皮褶字段(mm)+ 年龄/性别
期望:AI 走场景 2(预填 verify):render_body_composition_wizard.py 预填 args → 用户 verify → 复制 prompt → AI 调 body_composition.py add
  ★ 决 策 铁 则(v2.4.3 · SKILL.md §⚠️ 强制性规定 第 5 条):用户已给数据 → 场景 2(预填 wizard);未给数据 → 场景 1(空 wizard);用户说"直接录" → 场景 3(信任)
来源:"记体脂" / "记体脂 胸 8 腹 15 ..."(场景 2 自动判定)
        """.strip(),
    },
    'variants': [],
},
{
    'category': '身体成分',
    'wake_word': '查体脂',
    'desc':     '历史体脂记录',
    'main_prompt': {
        'cli':  'python scripts/render_body_composition_wizard.py → list 视图',
        'text': """卡路里技能 · 查体脂

场景:用户查历史体脂测量
数据:body_composition 表
期望:AI 调 render_body_composition_wizard.py(单页 + 折叠分组)
来源:"查体脂"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '身体成分',
    'wake_word': '查体脂趋势',
    'desc':     '体脂率时间线',
    'main_prompt': {
        'cli':  'python scripts/body_composition.py trend',
        'text': """卡路里技能 · 体脂趋势

场景:用户看 body_fat_pct 走势
数据:body_composition.body_fat_pct
期望:AI 调 trend → wizard HTML
来源:"查体脂趋势"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '身体成分',
    'wake_word': '删体脂',
    'desc':     '软删除体脂记录',
    'main_prompt': {
        'cli':  'python scripts/body_composition.py delete <id> → HTML:crud_receipt.html',
        'text': """卡路里技能 · 删体脂

场景:用户要软删某条体脂记录
数据:body_composition.is_deprecated
期望:AI 调 delete → crud_receipt.html 回执
来源:"删体脂 <id>"
        """.strip(),
    },
    'variants': [],
},

# ========== 📏 围度 (5) ==========
{
    'category': '围度',
    'wake_word': '记围度',
    'desc':     '13 部位围度(上身 5 + 下身 4 + 手臂 4)',
    'main_prompt': {
        'cli':  'python scripts/body_measurements.py add ... → HTML:body_measurements_wizard.html',
        'text': """卡路里技能 · 记围度

场景:用户量了 13 部位围度
数据:body_measurements 13 字段(cm)
期望:AI 走场景 2(预填 verify):render_body_measurements_wizard.py 预填 13 围度 → 用户 verify → AI 调 body_measurements.py add
  ★ 决 策 铁 则(v2.4.3):用户已给数据 → 场景 2;未给 → 场景 1;用户说"直接录" → 场景 3
来源:"记围度 胸 95 腰 80 臀 100..."
        """.strip(),
    },
    'variants': [],
},
{
    'category': '围度',
    'wake_word': '查围度',
    'desc':     '历史围度记录',
    'main_prompt': {
        'cli':  'python scripts/render_body_measurements_wizard.py → list 视图',
        'text': """卡路里技能 · 查围度

场景:用户查历史围度测量
数据:body_measurements 表
期望:AI 调 wizard HTML(13 部位折叠)
来源:"查围度"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '围度',
    'wake_word': '查围度趋势',
    'desc':     '单围度时间线',
    'main_prompt': {
        'cli':  'python scripts/body_measurements.py trend --metric <col>',
        'text': """卡路里技能 · 围度趋势

场景:用户看某一部位围度走势
数据:body_measurements.<col>
期望:AI 解析部位 → --metric waist-cm / chest-cm ...
来源:"查围度趋势 腰"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '围度',
    'wake_word': '删围度',
    'desc':     '软删除围度记录',
    'main_prompt': {
        'cli':  'python scripts/body_measurements.py delete <id> → HTML:crud_receipt.html',
        'text': """卡路里技能 · 删围度

场景:用户要软删某条围度记录
数据:body_measurements.is_deprecated
期望:AI 调 delete → crud_receipt.html 回执
来源:"删围度 <id>"
        """.strip(),
    },
    'variants': [],
},

# ========== 📸 身材照片 (5) ==========
{
    'category': '身材照片',
    'wake_word': '记身材照',
    'desc':     '记录身材照片',
    'main_prompt': {
        'cli':  'python scripts/body_photo_log_wizard.py → 用户填路径 → add',
        'text': """卡路里技能 · 记身材照

场景:用户要拍/上传身材照片入库
数据:body_photos(date/time/photo_path/tag/note)
期望:AI 调 log_wizard HTML(配置型)→ 用户填 → 复制 prompt → AI 调 add
来源:"记身材照"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '身材照片',
    'wake_word': '查身材照',
    'desc':     '查看照片历史(浏览 + 选 + 裁剪 + 调细节)',
    'main_prompt': {
        'cli':  'python scripts/render_body_photo_gif_planner.py --tag 正面',
        'text': """卡路里技能 · 查身材照

场景:用户要浏览身材照片(可筛选 + 裁剪 + 一键 GIF)
数据:body_photos 表
期望:AI 调 {cli} by tag → gif_planner.html(gallery + cropper)
来源:"查身材照 正面"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '身材照片',
    'wake_word': '生成身材照GIF',
    'desc':     '生成身材变化 GIF',
    'main_prompt': {
        'cli':  'python scripts/render_body_photo_gif_planner.py --tag X --photo-id ...',
        'text': """卡路里技能 · 生成身材 GIF

场景:用户要生成身材变化 GIF
数据:body_photos 多张照片
期望:AI 调 gif_planner.py 选照片 → crop → 生成 GIF
来源:"生成身材照GIF 正面"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '身材照片',
    'wake_word': '删身材照',
    'desc':     '删除身材照片',
    'main_prompt': {
        'cli':  'python scripts/body_photo_tracker.py delete <id>',
        'text': """卡路里技能 · 删身材照

场景:用户要删某张照片
数据:body_photos.id
期望:AI 解析 id → 调 {cli} → crud_receipt 回执
来源:"删身材照 <id>"
        """.strip(),
    },
    'variants': [],
},
{
    'category': '身材照片',
    'wake_word': '改照片标签',
    'desc':     '修改照片标签',
    'main_prompt': {
        'cli':  'python scripts/body_photo_tracker.py tag <id> <new_tag>',
        'text': """卡路里技能 · 改照片标签

场景:用户要改某张照片的 tag
数据:body_photos.tag
期望:AI 解析 id + 新 tag → 调 {cli} → 回执
来源:"改照片标签 <id> 改成 背面"
        """.strip(),
    },
    'variants': [],

# ========== 🎯 元触发 ==========
},
{
    'category': '综合',
    'wake_word': '设置档案',
    'desc':     '设置 user_profile(年龄/性别/身高/备注)',
    'main_prompt': {
        'cli':  'python scripts/render_profile_setup.py → 用户填 → 复制 prompt → set',
        'text': """卡路里技能 · 设置档案

场景:用户要设身高/年龄/性别(影响 BMI / TDEE / 营养目标)
数据:user_profile 表
期望:AI 调 profile_setup wizard HTML(配置型)→ 用户填 → 复制 prompt → AI 调 calorie_tracker.py profile set
来源:"设置档案" / "设置档案 30 male 177"
        """.strip(),
    },
    'variants': [
        {
            'label':  '设置档案 (直接传参)',
            'cli':    'python scripts/calorie_tracker.py profile set <age> <gender> --height <cm>',
            'prompt': '场景:用户给完整参数\n期望:AI 解析 → 调 calorie_tracker.py profile set\n来源:"设置档案 30 male 177"\n',
        },
    ],
},
{
    'category': '综合',
    'wake_word': '查档案',
    'desc':     '查看 user_profile + 最新体重',
    'main_prompt': {
        'cli':  'python scripts/render_crud_view.py --entity profile',
        'text': """卡路里技能 · 查档案

场景:用户要查自己的档案 + 最新体重
数据:user_profile + weight_log 最新
期望:AI 调 {cli}
来源:"查档案"
        """.strip(),
    },
    'variants': [],
},
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
