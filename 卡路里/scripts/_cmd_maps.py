"""HTML 输出文件名 · 动态参数中文化映射表

v2.4.8 起 · 配套 scripts/html_paths.py · 中文化的 command 字段拼接:

  <command>_<YYYYMMDD>_<HHMMSS>[_<N>].html

各 render 脚本根据 args.mode / args.category / args.part 拼 command 时,
调用本模块的 map_*() 函数,保证生成的中文文件名可读、可 grep。

约定:
  - key 永远是英文(CLI 参数值),value 是中文
  - 调用方负责默认值 / fallback
  - 增删项必须同步 SKILL.md §触发词速查表 + 完整 HTML 模板清单
"""

# weight_history.py --mode(查体重历史 / 趋势 / 对比 / 波动)
WEIGHT_MODE_MAP = {
    "history":   "历史",
    "trend":     "趋势",
    "compare":   "对比",
    "volatility":"波动",
}

# exercise_summary.py --mode(查运动记录 / 汇总 / 类型 / 趋势)
EXERCISE_SUMMARY_MODE_MAP = {
    "records": "记录",
    "summary": "汇总",
    "stats":   "类型",
    "trend":   "趋势",
}

# exercise_distribution.py --mode(查运动分布 / 贡献)
EXERCISE_DISTRIBUTION_MODE_MAP = {
    "distribution": "分布",
    "contribution": "贡献",
}

# food_ranking.py --category(5 榜单 + 全部)
FOOD_RANKING_CATEGORY_MAP = {
    "high_calorie": "高热量",
    "low_calorie":  "低热量",
    "frequent":     "常吃",
    "high_carb":    "高碳水",
    "high_protein": "高蛋白",
    # 'all' 用单独常量处理,不走 category
}

# contraindication.py --part(扫禁忌 · 部位)
# 中文部分部位本身就是中文,只需把 'all' 映射成 '全部'
CONTRAINDICATION_PART_MAP = {
    "腰":   "腰",
    "膝":   "膝",
    "肩":   "肩",
    "all":  "全部",
}