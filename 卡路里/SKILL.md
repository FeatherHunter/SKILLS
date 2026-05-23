---
name: 卡路里
description: 卡路里与营养追踪技能。当用户提及"卡路里"、或描述饮食/体重/运动/营养相关意图时触发。记录每日饮食热量、蛋白质、碳水、脂肪摄入，查询今日/历史摄入摘要；记录体重并查看趋势、对比、目标进度；记录运动消耗并查看运动报表；设置每日营养目标和体重目标。当用户说"醒了"、"睡醒了"、"起床啦"等起床唤醒词时，自动查询数据库计算睡眠时长并确认记录。
metadata: { "openclaw": { "emoji": "🍎", "requires": { "python": ">=3.7" } } }
---

## ⚠️ 操作规范（强制）

本技能所有数据操作必须通过 CLI，禁止直连数据库。

---

## 📦 一键安装

将以下内容发送给 AI 即可安装本技能：

```
请帮我安装卡路里技能：读取 workspace/skills/卡路里/SKILL.md，初始化数据库，运行 python scripts/calorie_tracker.py summary 确认正常。
```

---

## 🤝 触发词速查表

> 用户说"卡路里 help"时显示本表

| 功能 | 触发词示例 |
|------|-----------|
| 记录饮食 | "吃了碗米饭" / "中午吃了biangbiang面" / 发营养成分表图片 |
| 删除记录 | "删掉那条记录" / "删除ID 3" |
| 查看今日 | "今天吃了什么" / "list" / "今天吃了多少卡" / "今日摘要" |
| 查询历史 | "最近7天吃了什么" / "这周热量多少" |
| 搜索食品 | "查一下鸡胸肉的热量" / "可乐的营养成分" |
| 添加食品到库 | "把这个存到食品库" / "添加营养成分表" |
| 更新食品库 | "更新ID 1的热量" |
| 查看食品库 | "看看食品库里有什么" |
| 记录体重 | "体重70公斤" / "今天69.5kg" |
| 体重历史 | "体重历史" / "最近30天体重" |
| 体重趋势/对比/波动 | "体重趋势" / "这周和上周比" / "体重波动" |
| 目标进度 | "离目标还差多久" / "按现在速度多久能到" |
| 记录运动 | "今天骑行了40分钟" / "做了30个俯卧撑" |
| 运动汇总/趋势/类型 | "运动摘要" / "运动趋势" / "运动类型" / "运动贡献" |
| 热量趋势/缺口 | "热量趋势" / "这周吃了多少" / "热量缺口" |
| 营养配比 | "营养配比" / "蛋白质够吗" / "碳水是不是吃多了" |
| 食物排行榜 | "食物排行榜" / "低热量榜" / "频繁吃榜" / "高碳水榜" / "高蛋白榜" |
| 设置目标 | "每天吃1800卡" / "goal 2000 150 200 60" / "我想瘦到70公斤" |
| 健身目标 | "设置俯卧撑目标" / "每天做50个俯卧撑" |
| 睡眠记录 | "昨晚睡了多久" / "睡眠7小时" / "昨晚11点睡的" |
| 综合报告 | "dashboard" / "给我看看整体情况" |
| 健康检查 | "健康检查" / "lint" / "检查数据" |

---

# 卡路里 - 热量追踪技能 v2.0

## 功能概述

- **食物记录**：记录热量、蛋白质、碳水、脂肪（克为单位）
- **每日目标**：设置热量和三大宏量营养素目标
- **体重追踪**：记录体重，自动计算BMI
- **健身目标**：设置每日/每周/每月/长期健身目标，支持暂停/进行中状态
- **睡眠记录**：记录每日睡眠时长和就寝/起床时间，**睡眠归属于就寝那天**
- **数据分析**：3大类11种分析维度 + dashboard综合报告

## 数据库结构

详见 [`references/database_schema.md`](references/database_schema.md)

共 7 张表：`entries`、`daily_goal`、`weight_log`、`exercise_log`、`nutrition_products`、`fitness_goals`、`sleep_records`

> **初始化说明**：`entries`/`daily_goal`/`weight_log`/`exercise_log`/`nutrition_products` 由 `calorie_tracker.py init_db()` 创建；`fitness_goals` 由 `fitness_goals.py init_table()` 创建；`sleep_records` 由 `sleep_tracker.py init_table()` 创建。

## 命令行用法

### 食物记录
```bash
python scripts/calorie_tracker.py add "鸡胸肉" 165 31 0 3 150   # 食物名 热量 蛋白 碳水 脂肪 克数
python scripts/calorie_tracker.py summary                        # 今日摘要
python scripts/calorie_tracker.py history 7                      # 最近7天历史
python scripts/calorie_tracker.py goal 1800 150 200 60           # 设置目标：热量 蛋白 碳水 脂肪
```

### 食品库
```bash
python scripts/calorie_tracker.py search-product "可乐"          # 搜索
python scripts/calorie_tracker.py add-product "可口可乐" "可口可乐" 42 0 0 0 10.6 10.6 0 20 "330ml"
python scripts/calorie_tracker.py update-product 1 --calories 45 # 更新
```

### 体重
```bash
python scripts/calorie_tracker.py weight 70 178                  # 记录体重(kg) 身高(cm)
python scripts/calorie_tracker.py weight-history 30              # 最近30天体重
```

### 运动
```bash
python scripts/exercise_tracker.py add --date 2026-05-23 --type 骑行 --calories 300 --minutes 40
python scripts/exercise_tracker.py list --days 7
python scripts/exercise_tracker.py summary --days 7
python scripts/exercise_tracker.py trend --days 7
```

### 健身目标
```bash
python scripts/fitness_goals.py add "每日俯卧撑" --type daily --exercise 俯卧撑 --unit 个 --target 50 --start 2026-05-23
python scripts/fitness_goals.py list --status active
python scripts/fitness_goals.py update 1 --target 60
python scripts/fitness_goals.py delete 1
```

### 睡眠记录
```bash
python scripts/sleep_tracker.py add 2026-05-22 --hours 7.5 --bed 23:30 --wake 07:00
python scripts/sleep_tracker.py update 2026-05-22 --hours 8 --note "睡得不错"
python scripts/sleep_tracker.py list --days 7
```

> **睡眠归属规则**：睡眠归属于**就寝那天**。例如"昨晚11:30睡的，今天7:00醒"，记录在就寝日。

### 分析接口（11种维度）
```python
weight_analysis(start, end, 'trend')       # 趋势|compare|milestone|volatility
diet_analysis(start, end, 'calorie_trend') # calorie_trend|macro_ratio|food_ranking|deficit_analysis
exercise_analysis(start, end, 'exercise_trend') # exercise_trend|type_breakdown|deficit_contribution
dashboard(start, end)                      # 综合四维度仪表盘
```

---

## AI 触发指引

**重要提示**：所有命令使用技能目录下的 `scripts/` 路径前缀。

### 触发场景：记录饮食

**完整流程（重要）**：

#### Step 1：解析用户输入
提取：食物名、克数（如有）

#### Step 2：模糊查询 nutrition_products 表
执行：`python scripts/calorie_tracker.py search-product <食物名>`

#### Step 3：根据查询结果分流

**Path A：找到匹配结果（≥1条）**
```
列表显示 → 用户选择 → 确认克数 → 计算热量/100 × 克数 → 执行 add → 返回今日汇总
```

**Path B：库中没找到，用户提供了营养成分表图片**
```
调用 mmx vision describe 识别图片 → 展示结果 → 用户确认 → add-product 存库 → 继续 Path A
```

**Path C：库中没找到，用户无法提供营养成分表**
```
讨论估算克数 → mmx search 查询参考数据 → 用户确认 → 执行 add（参考数据不存库）
```

#### Step 4：返回确认信息
```
✓ 已记录：<食物名> (<热量>卡, <克数>克)
餐次：<早/午/晚/下午茶/夜宵>
今日：<热量>/<目标>卡 | 蛋白<蛋白>/<目标>g | 碳<碳>/<目标>g | 脂<脂>/<目标>g
```

### 触发场景：添加食品营养成分表
1. 解析输入或图片 → 提取营养成分
2. 执行：`python scripts/calorie_tracker.py add-product <产品名> <品牌> <热量> <蛋白> <脂肪> <饱和脂肪> <碳水> <糖> <纤维> <钠> [备注]`

### 触发场景：查询/搜索营养成分
执行：`python scripts/calorie_tracker.py search-product <关键词>`

### 触发场景：查看今日摄入
执行：`python scripts/calorie_tracker.py summary`

### 触发场景：设置目标
执行：`python scripts/calorie_tracker.py goal <热量> [蛋白] [碳水] [脂肪]`

### 触发场景：记录体重
执行：`python scripts/calorie_tracker.py weight <体重> [身高]`

### 触发场景：管理健身目标
执行：`python scripts/fitness_goals.py add <名称> --type <daily|weekly|monthly|longterm> --exercise <运动> --unit <单位> --target <值> --start <日期>`

### 触发场景：记录睡眠

**起床唤醒词处理流程：**
1. 检测到唤醒词（"醒了"/"睡醒了"/"起床啦"）→ 查询录音机数据库计算睡眠时长
2. 确认：「检测到你刚才睡了X小时，要不要记录？」（不提及"卡路里"三字）
3. 确认后执行：`python scripts/sleep_tracker.py add <就寝日期> --hours <时长> --bed <就寝时间> --wake <起床时间>`

**普通触发词：**
解析输入 → 执行 `python scripts/sleep_tracker.py add ...`（睡眠归属就寝日）

---

## 示例对话

**用户**：吃了碗米饭
**AI**：米饭大概 200克，232卡，4g蛋白，50g碳水，0.5g脂肪 → ✓ 已记录，今日 232/1800卡

**用户**：体重70公斤
**AI**：✓ 体重已记录 70.0公斤，BMI 22.1（正常范围）

---

## 联动说明

| 技能 | 联动场景 |
|------|---------|
| 居家管家 | 购买食品时同步记录物品位置和数量 |
| 饼干记账 | 记录饮食消费时同步记录支出金额 |

原则：先完成主技能操作，再询问是否联动，不强制。

---

## Lint 检查（数据健康检查）

**触发词**：`"健康检查"` / `"检查数据"` / `"lint"` / `"数据审计"`

检查项：数据新鲜度（今日是否记录体重/饮食/运动）、体重目标进度、热量趋势预警（连续3天超标）、热量缺口分析、运动连续性（连续7天未运动预警）。

原则：发现问题列出清单，只建议不自动修改。

---

## TypeScript 配置生成

表结构变化后运行 `python scripts/generate_ts_config.py` 重新生成 `config-calorie.ts`。
