# SKILL 设计触发唤醒词

> 深入分析每个 SKILL 的所有 md 文件、脚本文件、features 目录
> 找出设计层面的全部唤醒词 + 对应功能
> 每条唤醒词附 **来源文件:行号**
>
> 生成日期：2026-05-26 | 二次校验：2026-05-26

---

## 1. 备忘录

### 来源文件
- `备忘录/SKILL.md` — 主定义 + 全部触发词

### 唤醒词与功能映射

| 唤醒词 | 功能 | 来源 |
|--------|------|------|
| 记一下、帮我记、备忘、添加、存一下 | 添加笔记 | `备忘录/SKILL.md:51` |
| 搜一下、搜索、查找、找一下、看看 | 搜索笔记 | `备忘录/SKILL.md:61` |
| 更新、修改、改一下 | 更新笔记 | `备忘录/SKILL.md:65` |
| 删除、删掉 | 删除笔记 | `备忘录/SKILL.md:70` |
| 看看、查看、详情 | 查看笔记详情 | `备忘录/SKILL.md:75` |
| 这个月、最近、上周 | 按时间搜索 | `备忘录/SKILL.md:79` |
| 改分类、换个分类 | 编辑笔记分类 | `备忘录/SKILL.md:83` |
| 提醒、定时 | 设置提醒 | `备忘录/SKILL.md:88` |
| 我有哪些提醒、提醒列表 | 查看提醒 | `备忘录/SKILL.md:95` |
| 已完成、哪些完成了、完成的提醒、完成情况 | 查询已完成提醒 | `备忘录/SKILL.md:102` |

### 特殊路由规则
- 所有「提醒」类请求 → 必须走备忘录 CLI — `备忘录/SKILL.md:39-44`

---

## 2. 饼干记账

### 来源文件
- `饼干记账/SKILL.md` — 主定义 + 触发词表

### 唤醒词与功能映射

| 唤醒词 | 功能 | 来源 |
|--------|------|------|
| 记账、花了X元、付了、消费、买了 | 记账（负数金额） | `饼干记账/SKILL.md:52` |
| 收到X元、收入、进账、工资 | 收入记录（正数金额） | `饼干记账/SKILL.md:53` |
| 发截图/账单图片 | 图片记账 | `饼干记账/SKILL.md:54` |
| 今天花了多少、今日支出、查账单 | 今日摘要 | `饼干记账/SKILL.md:55` |
| 这个月消费、本月支出 | 月度汇总 | `饼干记账/SKILL.md:56` |
| 上周花了多少、上月账单 | 周期对比 | `饼干记账/SKILL.md:57` |
| 最近的记录、最近N条 | 最近记录 | `饼干记账/SKILL.md:58` |
| 各类支出占比、分类明细 | 分类明细 | `饼干记账/SKILL.md:59` |
| 找一下XX的记录 | 搜索 | `饼干记账/SKILL.md:60` |

### 金额解析规则 — `饼干记账/SKILL.md:62-64`
- 花了/付了/消费/支出 → 负数
- 收到/收入/进账 → 正数

### 图片识别规则 — `饼干记账/SKILL.md:69-73`
1. 优先取「实付/实收/已支付/需付」
2. 其次取「合计/总计/总额/应付」
3. 忽略：单品价格、优惠减免、配送费、税额

---

## 3. 共享单车提醒

### 来源文件
- `共享单车提醒/SKILL.md` — 主定义 + 完整触发词列表

### 唤醒词与功能映射

| 唤醒词 | 功能 | 来源 |
|--------|------|------|
| 骑车了、正在骑车、骑完车、骑车中 | 创建循环提醒 | `共享单车提醒/SKILL.md:11` |
| 骑车回家、骑车上班 | 创建循环提醒 | `共享单车提醒/SKILL.md:11` |
| 扫了小黄车、扫了美团 | 创建循环提醒 | `共享单车提醒/SKILL.md:11` |
| 共享单车、小黄车、美团单车、哈啰、青桔 | 创建循环提醒 | `共享单车提醒/SKILL.md:11` |
| 电动车、电单车 | 创建循环提醒 | `共享单车提醒/SKILL.md:11` |
| 关了、锁了、已关、关车了、锁车了、车关了 | **取消提醒** | `共享单车提醒/SKILL.md:14` |

### 执行机制 — `共享单车提醒/SKILL.md:16-62`
1. 用户说开始骑车 → 回复确认 + 创建 cron 循环提醒
2. 每 3 分钟询问「车关了吗？」 — `SKILL.md:30-31`
3. 用户回复关车关键词 → 取消 cron 任务 — `SKILL.md:50-58`

---

## 4. 居家管家

### 来源文件
- `居家管家/SKILL.md` — 主定义 + 路由规则
- `居家管家/features/add.md` — 物品录入
- `居家管家/features/search.md` — 物品查找
- `居家管家/features/update.md` — 物品更新
- `居家管家/features/inventory.md` — 物品盘点
- `居家管家/features/fashion.md` — 穿搭推荐
- `居家管家/features/travel.md` — 旅游归位
- `居家管家/features/stats.md` — 频率统计
- `居家管家/features/tags.md` — 标签管理
- `居家管家/scripts/accounts.py` — 账号密码管理

### 唤醒词与功能映射

#### 第1层 — 显式触发 — `居家管家/SKILL.md:72`
| 唤醒词 | 功能 | 来源 |
|--------|------|------|
| 居家管家 | 进入「物品录入」 | `居家管家/SKILL.md:72` |

#### 第2层 — 场景关键词 — `居家管家/SKILL.md:76-85`
| 唤醒词 | 功能 | 来源 |
|--------|------|------|
| 找XX、XX在哪、有没有XX、XX还有多少、还剩多少XX、有多少XX | 物品查找 | `居家管家/SKILL.md:78` |
| XX换位置了、把XX放到XX、XX借给、XX坏了、XX用完了、XX吃了、XX扔了 | 物品更新 | `居家管家/SKILL.md:79` |
| 盘点XX、整理一下XX | 物品盘点 | `居家管家/SKILL.md:80` |
| 今天穿什么、推荐穿搭 | 穿搭推荐 | `居家管家/SKILL.md:81` |
| 带XX出去旅游、旅游回来了 | 旅游归位 | `居家管家/SKILL.md:82` |
| 高频物品、长期没碰的、物品统计 | 频率统计 | `居家管家/SKILL.md:83` |
| 标签合并、整理标签 | 标签管理 | `居家管家/SKILL.md:84` |
| 快递、有哪些快递、快递到了吗、查快递、我的快递、快递状态、有几个快递、快递还没到 | 查看快递 | `居家管家/SKILL.md:85` |
| 平台账号、数字凭证、激活码、API密钥 | 账号密码管理 | `居家管家/SKILL.md:3`（description） |

#### Lint 检查 — `居家管家/SKILL.md:114`
| 唤醒词 | 功能 | 来源 |
|--------|------|------|
| 健康检查、检查数据、lint、数据审计 | 数据健康检查 | `居家管家/SKILL.md:114` |

#### 物品更新子场景 — `居家管家/features/update.md:22-27`
| 用户说 | 操作 | 来源 |
|--------|------|------|
| XX借给朋友 | `--location-status "借用中"` | `features/update.md:24` |
| XX坏了 | `--location-status "维修中"` | `features/update.md:25` |
| 扔了/不要了 | `--location-status "已废弃"` | `features/update.md:26` |
| 用完了 | `--location-status "已用完"` | `features/update.md:27` |

#### 频率统计子场景 — `居家管家/features/stats.md:13-17`
| 用户说 | 类型 | 来源 |
|--------|------|------|
| 高频物品 | `frequent` | `features/stats.md:14` |
| 长期没碰的 | `dormant` | `features/stats.md:15` |
| 物品统计 | `summary` | `features/stats.md:16` |

#### 旅游归位子场景 — `居家管家/features/travel.md:7-8`
| 用户说 | 功能 | 来源 |
|--------|------|------|
| 居家管家 我要带XX出去旅游 | 出门前标记物品 | `features/travel.md:7` |
| 居家管家 旅游回来了 | 回家归位 | `features/travel.md:27` |

---

## 5. 卡路里

### 来源文件
- `卡路里/SKILL.md` — 主定义 + 触发词速查表（9 域 48 个唤醒词）
- `卡路里/scripts/calorie_tracker.py` — 热量追踪（12 命令）
- `卡路里/scripts/exercise_tracker.py` — 运动追踪（6 命令）
- `卡路里/scripts/sleep_tracker.py` — 睡眠追踪（3 命令）
- `卡路里/scripts/fitness_goals.py` — 健身目标（4 命令）
- `卡路里/scripts/analysis.py` — 数据分析（11 分析 + dashboard）

### 唤醒词与功能映射（动词+名词，分域组织）

#### 🍚 饮食记录（6 个）

| 唤醒词 | 功能 | CLI | 来源 |
|--------|------|-----|------|
| 记吃了 | 记录饮食 | `calorie_tracker.py add` | `SKILL.md` |
| 拍营养表 | 图片识别营养成分表 | `mmx vision → add` | `SKILL.md` |
| 删吃的 | 删除饮食记录 | `calorie_tracker.py delete` | `SKILL.md` |
| 查今天吃 | 今日饮食摘要 | `calorie_tracker.py summary` | `SKILL.md` |
| 查吃的记录 | 今日逐条记录 | `calorie_tracker.py list` | `SKILL.md` |
| 查热量历史 | 最近 N 天热量历史 | `calorie_tracker.py history` | `SKILL.md` |

#### 🏷️ 食品库（4 个）

| 唤醒词 | 功能 | CLI | 来源 |
|--------|------|-----|------|
| 查热量 | 搜索食品营养成分 | `calorie_tracker.py search-product` | `SKILL.md` |
| 存食品 | 添加食品营养成分表 | `calorie_tracker.py add-product` | `SKILL.md` |
| 改食品 | 更新食品营养成分 | `calorie_tracker.py update-product` | `SKILL.md` |
| 查食品库 | 列出全部食品 | `calorie_tracker.py list-products` | `SKILL.md` |

#### ⚖️ 体重（7 个）

| 唤醒词 | 功能 | CLI | 来源 |
|--------|------|-----|------|
| 记体重 | 记录体重 | `calorie_tracker.py weight` | `SKILL.md` |
| 查体重历史 | 体重历史记录 | `calorie_tracker.py weight-history` | `SKILL.md` |
| 查体重趋势 | 体重趋势分析 | `weight_analysis(trend)` | `SKILL.md` |
| 对比体重 | 两时间段体重对比 | `weight_analysis(compare)` | `SKILL.md` |
| 查体重波动 | 体重波动分析 | `weight_analysis(volatility)` | `SKILL.md` |
| 设体重目标 | 设定体重目标 | `set_weight_goal()` | `SKILL.md` |
| 查体重目标 | 体重目标达成进度 | `weight_analysis(milestone)` | `SKILL.md` |

#### 🏃 运动（6 个）

| 唤醒词 | 功能 | CLI | 来源 |
|--------|------|-----|------|
| 记运动 | 记录运动消耗 | `exercise_tracker.py add` | `SKILL.md` |
| 改运动记录 | 更新运动记录 | `exercise_tracker.py update` | `SKILL.md` |
| 查运动记录 | 查询运动记录 | `exercise_tracker.py list` | `SKILL.md` |
| 查运动汇总 | 运动汇总统计 | `exercise_tracker.py summary` | `SKILL.md` |
| 查运动类型 | 运动类型统计 | `exercise_tracker.py stats` | `SKILL.md` |
| 查运动趋势 | 运动热量趋势 | `exercise_tracker.py trend` | `SKILL.md` |

#### 💪 健身目标（4 个）

| 唤醒词 | 功能 | CLI | 来源 |
|--------|------|-----|------|
| 设健身目标 | 添加健身目标 | `fitness_goals.py add` | `SKILL.md` |
| 查健身目标 | 查询健身目标 | `fitness_goals.py list` | `SKILL.md` |
| 改健身目标 | 更新健身目标 | `fitness_goals.py update` | `SKILL.md` |
| 删健身目标 | 删除健身目标 | `fitness_goals.py delete` | `SKILL.md` |

#### 😴 睡眠（5 个）

| 唤醒词 | 功能 | CLI | 来源 |
|--------|------|-----|------|
| 记睡眠 | 记录睡眠 | `sleep_tracker.py add` | `SKILL.md` |
| 改睡眠记录 | 更新睡眠记录 | `sleep_tracker.py update` | `SKILL.md` |
| 查睡眠记录 | 查询睡眠记录 | `sleep_tracker.py list` | `SKILL.md` |
| 记录起床 | 起床唤醒自动流程 | 录音机 → `sleep_tracker.py add` | `SKILL.md` |

#### 📊 分析（11 个）

| 唤醒词 | 功能 | CLI | 来源 |
|--------|------|-----|------|
| 查热量趋势 | 热量摄入趋势 | `diet_analysis(calorie_trend)` | `SKILL.md` |
| 查营养配比 | 营养素占比分析 | `diet_analysis(macro_ratio)` | `SKILL.md` |
| 查热量缺口 | 热量缺口分析 | `diet_analysis(deficit_analysis)` | `SKILL.md` |
| 查食物排行 | 食物排行榜（默认高热量） | `diet_food_ranking(high_calorie)` | `SKILL.md` |
| 查高热量榜 | 热量炸弹 TOP5 | `diet_food_ranking(high_calorie)` | `SKILL.md` |
| 查低热量榜 | 低热量健康 TOP5 | `diet_food_ranking(low_calorie)` | `SKILL.md` |
| 查频繁吃榜 | 最常吃的食物 TOP5 | `diet_food_ranking(frequent)` | `SKILL.md` |
| 查高碳水榜 | 高碳水食物 TOP5 | `diet_food_ranking(high_carb)` | `SKILL.md` |
| 查高蛋白榜 | 高蛋白食物 TOP5 | `diet_food_ranking(high_protein)` | `SKILL.md` |
| 查运动分布 | 运动类型分布 | `exercise_analysis(type_breakdown)` | `SKILL.md` |
| 查运动贡献 | 运动对缺口贡献 | `exercise_analysis(deficit_contribution)` | `SKILL.md` |

#### 📋 综合（5 个）

| 唤醒词 | 功能 | CLI | 来源 |
|--------|------|-----|------|
| 设营养目标 | 设置每日营养目标 | `calorie_tracker.py goal` | `SKILL.md` |
| 查营养目标 | 查看当前营养目标 | `get_goal()` | `SKILL.md` |
| 查健康报告 | 四维度综合仪表盘 | `dashboard()` | `SKILL.md` |
| 查卡路里数据 | 数据健康检查（Lint） | Lint 检查流程 | `SKILL.md` |

### 起床唤醒词处理流程 — `卡路里/SKILL.md`
1. 检测到唤醒词"记录起床" → 查询录音机数据库
2. 找到"最后一次人类消息"时间（入睡信号）和当前唤醒消息时间（起床信号）
3. 计算睡眠时长 = 起床时间 - 入睡前最后一条消息时间
4. 确认：「检测到你刚才睡了X小时，要不要记录？」
5. 睡眠归属于就寝那天

---

## 6. 录音机

### 来源文件
- `录音机/SKILL.md` — 主定义 + 触发词

### 唤醒词与功能映射

| 唤醒词 | 功能 | 来源 |
|--------|------|------|
| 记录语录 | 手动触发扫描入库 | `录音机/SKILL.md:18` |
| 扫描消息 | 手动触发扫描入库 | `录音机/SKILL.md:18` |
| 每日语录 | 查询当日消息 | `录音机/SKILL.md:18` |
| cron 自动触发 | 每10分钟自动扫描 | `录音机/SKILL.md:19` |

---

## 7. 每日检查

### 来源文件
- `每日检查/SKILL.md` — 主定义 + 10个问题列表
- `每日检查/scripts/daily_checker.py` — 数据检查
- `每日检查/scripts/screenshot.py` — Playwright 截图

### 唤醒词与功能映射

| 唤醒词 | 功能 | 来源 |
|--------|------|------|
| 每日检查、每日报告 | 触发完整检查流程 | `每日检查/SKILL.md:3` |
| cron 定时自动触发 | 自动生成报告 | `每日检查/SKILL.md:3` |

### 10个检查项 — `每日检查/SKILL.md:22-33`
1. 今天有体重记录吗（卡路里） — `SKILL.md:24`
2. 今天记录摄入热量了吗（卡路里） — `SKILL.md:25`
3. 今天记录运动了吗（卡路里） — `SKILL.md:26`
4. 有物品在快递运输中吗（居家管家） — `SKILL.md:27`
5. 有物品快过期/已过期/有过期风险吗（居家管家） — `SKILL.md:28`
6. 今日支出+剩余预算（饼干记账） — `SKILL.md:29`
7. 今日待办（备忘录） — `SKILL.md:30`
8. 最近有汇报行动吗（录音机） — `SKILL.md:31`
9. 当前时段在计划作息表中的安排（作息管家） — `SKILL.md:32`
10. 昨天睡眠总时长（作息管家） — `SKILL.md:33`

---

## 8. 面试管家

### 来源文件
- `面试管家/interview-system-main-flow.md` — 主流程 SOP
- `面试管家/SOPs/` — 各轮次 SOP
- `面试管家/interviewer-personas/` — 面试官角色
- `面试管家/templates/` — 报告模板

### 唤醒词与功能映射

| 唤醒词 | 功能 | 来源 |
|--------|------|------|
| 我要面试 | 进入面试精通系统 | `面试管家/interview-system-main-flow.md:11` |
| 准备面试 | 进入面试精通系统 | `面试管家/interview-system-main-flow.md:11` |
| 开始面试训练 | 进入面试精通系统 | `面试管家/interview-system-main-flow.md:11` |
| 准备XXX面试 | 指定知识点面试 | `面试管家/interview-system-main-flow.md:12` |
| 模拟面试XXX | 指定知识点模拟面试 | `面试管家/interview-system-main-flow.md:13` |
| 来一次模拟面试 | 通用模拟面试 | `面试管家/interview-system-main-flow.md:13` |

### 主流程 — `面试管家/interview-system-main-flow.md:19-50`
Step 0: 前置检查 → Step 1: 学习状态检测 + 诊断测试 → Step 2: 目标设定 → Step 3-5: 各轮次面试

---

## 9. 目录树

### 来源文件
- `目录树/SKILL.md` — 主定义 + 触发词 + 视觉规范
- `目录树/scripts/generate.py` — 生成脚本
- `目录树/scripts/generate_v2.py` — v2 生成脚本

### 唤醒词与功能映射

| 唤醒词 | 功能 | 来源 |
|--------|------|------|
| 目录树 | 递归扫描目录，生成树状 HTML | `目录树/SKILL.md:26` |
| 目录导航 | 递归扫描目录，生成树状 HTML | `目录树/SKILL.md:27` |

### 视觉风格 — `目录树/SKILL.md:13-20`
- 亮色单色背景 + 新禅意科技美学
- 背景色 `#f6f5f1` — `SKILL.md:14`
- 墨灰纹理 — `SKILL.md:15`
- 磨砂玻璃效果 — `SKILL.md:16`

---

## 10. 深夜书单

### 来源文件
- `深夜书单/SKILL.md` — 主定义 + 下载策略

### 唤醒词与功能映射

| 唤醒词 | 功能 | 来源 |
|--------|------|------|
| 深夜书单 | 启动电子书下载任务 | 推断自目录名 |
| 找本书 | 启动电子书下载任务 | 推断自 SKILL.md:1 |
| 下载电子书 | 启动电子书下载任务 | 推断自 SKILL.md:1 |

### 下载策略（按顺序尝试） — `深夜书单/SKILL.md:5-29`
1. LibGen — `SKILL.md:8`
2. Z-Library 镜像 — `SKILL.md:13`
3. 学术资源 — `SKILL.md:18`
4. GitHub 免费书 — `SKILL.md:23`
5. 高校图书馆镜像 — `SKILL.md:28`

### 领域 — `深夜书单/SKILL.md:3`
佛学、毛泽东、国学、AI（随机选择）

---

## 11. 私家大厨

### 来源文件
- `私家大厨/SKILL.md` — 主定义 + 路由表（7个优先级）
- `私家大厨/features/add.md` — 录入食谱
- `私家大厨/features/view.md` — 查看食谱 + 做菜模式
- `私家大厨/features/search.md` — 搜索筛选
- `私家大厨/features/update.md` — 修改食谱
- `私家大厨/features/history.md` — 烹饪历史
- `私家大厨/features/shopping.md` — 采购清单

### 唤醒词与功能映射（按优先级 P1→P7）

#### P1：做菜模式 — `私家大厨/SKILL.md:109-118`
| 唤醒词 | 路由 | 来源 |
|--------|------|------|
| 做菜模式 | `view.md` → 做菜模式 | `SKILL.md:113` |
| 开始做XX | `view.md` → 做菜模式 | `SKILL.md:114` |
| 进入烹饪 | `view.md` → 做菜模式 | `SKILL.md:115` |
| 开始烹饪 | `view.md` → 做菜模式 | `SKILL.md:116` |
| 做这道菜 | `view.md` → 做菜模式 | `SKILL.md:117` |

#### P2：查看食谱 — `私家大厨/SKILL.md:124-135`
| 唤醒词 | 路由 | 来源 |
|--------|------|------|
| 看看XX怎么做 | `view.md` → 查看食谱 | `SKILL.md:128` |
| XX菜谱 | `view.md` → 查看食谱 | `SKILL.md:129` |
| XX做法 | `view.md` → 查看食谱 | `SKILL.md:130` |
| XX步骤 | `view.md` → 查看食谱 | `SKILL.md:131` |
| XX详情 | `view.md` → 查看食谱 | `SKILL.md:132` |
| 查看XX | `view.md` → 查看食谱 | `SKILL.md:133` |
| 给我看XX | `view.md` → 查看食谱 | `SKILL.md:134` |

#### P3：搜索筛选 — `私家大厨/SKILL.md:141-151`
| 唤醒词 | 路由 | 来源 |
|--------|------|------|
| 找XX | `search.md` | `SKILL.md:145` |
| 搜一下XX | `search.md` | `SKILL.md:146` |
| 有哪些XX | `search.md` | `SKILL.md:147` |
| 哪些菜 | `search.md` | `SKILL.md:148` |
| 什么菜 | `search.md` | `SKILL.md:149` |
| 哪个 | `search.md` | `SKILL.md:150` |

#### P4：修改食谱 — `私家大厨/SKILL.md:157-172`
| 唤醒词 | 路由 | 来源 |
|--------|------|------|
| 改成 | `update.md` | `SKILL.md:161` |
| 换成 | `update.md` | `SKILL.md:162` |
| 加食材、加个食材 | `update.md` | `SKILL.md:163-164` |
| 修改 | `update.md` | `SKILL.md:165` |
| 难度 | `update.md` | `SKILL.md:166` |
| 不想要 | `update.md`（废弃） | `SKILL.md:167` |
| 废弃 | `update.md`（废弃） | `SKILL.md:168` |
| 不要了 | `update.md`（废弃） | `SKILL.md:169` |

#### P5：烹饪历史 — `私家大厨/SKILL.md:178-188`
| 唤醒词 | 路由 | 来源 |
|--------|------|------|
| 做过 | `history.md` | `SKILL.md:182` |
| 评分 | `history.md` | `SKILL.md:183` |
| 历史 | `history.md` | `SKILL.md:184` |
| 复盘 | `history.md` | `SKILL.md:185` |
| 记录 | `history.md` | `SKILL.md:186` |
| 烹饪记录 | `history.md` | `SKILL.md:187` |

#### P6：采购清单 — `私家大厨/SKILL.md:194-203`
| 唤醒词 | 路由 | 来源 |
|--------|------|------|
| 采购 | `shopping.md` | `SKILL.md:198` |
| 清单 | `shopping.md` | `SKILL.md:199` |
| 买 | `shopping.md` | `SKILL.md:200` |
| 要买 | `shopping.md` | `SKILL.md:201` |
| 准备食材 | `shopping.md` | `SKILL.md:202` |

#### P7：录入食谱 — `私家大厨/SKILL.md:209-217`
| 唤醒词 | 路由 | 来源 |
|--------|------|------|
| 录入 | `add.md` | `SKILL.md:213` |
| 新建 | `add.md` | `SKILL.md:214` |
| 添加 | `add.md` | `SKILL.md:215` |
| 收藏 | `add.md` | `SKILL.md:216` |

#### 兜底规则 — `私家大厨/SKILL.md:99`
- 无任何触发词命中 → 默认走 `search.md`（可能是纯菜名输入）

---

## 12. 思维导师

### 来源文件
- `思维导师/SKILL.md` — 主定义 + 两种模式

### 唤醒词与功能映射

| 唤醒词 | 功能 | 来源 |
|--------|------|------|
| 元提示 | 模式一：分析场景，提供 1-3 个元提示模板 | `思维导师/SKILL.md:27` |
| 思维导师 | 进入思维导师模式 | `思维导师/SKILL.md:27` |
| 描述具体问题/困惑/场景 | 模式二：追问澄清 → 优化提问 → 专属元提示 | `思维导师/SKILL.md:27` |

---

## 13. 贴心助理

### 来源文件
- `贴心助理/SKILL.md` — 主定义 + 核心原则

### 唤醒词与功能映射

| 唤醒词 | 功能 | 来源 |
|--------|------|------|
| 贴心助理 | 进入主动关心模式 | `贴心助理/SKILL.md:2`（name） |
| 你看看我、最近怎么样、关心一下我 | 手动触发 | `贴心助理/SKILL.md:56` |
| cron 自动触发 | 每1小时自动执行 | `贴心助理/SKILL.md:51` |

### 核心原则 — `贴心助理/SKILL.md:18-30`
- 以 daily_recorder 中用户发言为核心 — `SKILL.md:20`
- 每次最多推送 1 条 — `SKILL.md:24`
- 像朋友一样说话 — `SKILL.md:28`

---

## 14. 图片路由

### 来源文件
- `图片路由/SKILL.md` — 主定义 + 路由判断逻辑

### 唤醒词与功能映射

| 唤醒词 | 功能 | 来源 |
|--------|------|------|
| 用户发送图片（无论是否有文字） | 自动触发图片识别 | `图片路由/SKILL.md:18` |

### 路由逻辑 — `图片路由/SKILL.md:30-35`
1. 收到图片 → subagent 调用 `mmx vision describe` 识别内容 — `SKILL.md:26`
2. 判断是否与以下技能相关 — `SKILL.md:27`：
   - 涉及金额/交易 → 饼干记账 — `SKILL.md:32`
   - 涉及物品存放 → 居家管家 — `SKILL.md:33`
   - 涉及食物/营养 → 卡路里 — `SKILL.md:34`
3. 相关 → 推荐技能组合 → 用户确认 → 执行 — `SKILL.md:28`
4. 不相关 → 正常聊天 — `SKILL.md:40`

---

## 15. 小龙虾CC交互

### 来源文件
- `小龙虾CC交互/SKILL.md` — 桥接文件 + YAML 定义
- `小龙虾CC交互/references/cli-reference.md` — CLI 参考

### 唤醒词与功能映射

| 唤醒词 | 功能 | 来源 |
|--------|------|------|
| 让 Claude Code 写代码 | 启动 Claude Code CLI 多轮交互 | `小龙虾CC交互/SKILL.md:20` |
| 和 claude code 交互 | 启动 Claude Code CLI 多轮交互 | `小龙虾CC交互/SKILL.md:21` |
| 多轮写代码 | 启动 Claude Code CLI 多轮交互 | `小龙虾CC交互/SKILL.md:22` |
| claude code 多轮 | 启动 Claude Code CLI 多轮交互 | `小龙虾CC交互/SKILL.md:23` |

### 技术实现 — `小龙虾CC交互/SKILL.md:32-64`
- 通过 `exec` 调用 claude CLI — `SKILL.md:36-40`
- 使用 `--session-id` 和 `--resume` 实现多轮交互 — `SKILL.md:44-54`

---

## 16. 学习规划师

### 来源文件
- `学习规划师/SKILL.md` — 主定义 + 文件路径规范

### 唤醒词与功能映射

| 唤醒词 | 功能 | 来源 |
|--------|------|------|
| 学习规划师 | 进入学习计划制定 | `学习规划师/SKILL.md:2`（name） |
| 制定计划 | 生成/优化计划 | `学习规划师/SKILL.md:77` |
| 生成百日计划 | 生成长期计划 | `学习规划师/SKILL.md:77` |
| 优化计划 | 优化现有计划 | `学习规划师/SKILL.md:77` |
| cron 触发（每日 08:00） | 自动生成今日计划 | `学习规划师/SKILL.md:66` |

### 文件输出路径 — `学习规划师/SKILL.md:24-29`
- 长期：`plans/{YYYYMMDD}_百日计划.md` — `SKILL.md:25`
- 月：`plans/{YYYYMM}_月计划.md` — `SKILL.md:26`
- 周：`plans/{YYYYWW}_周计划.md` — `SKILL.md:27`
- 日：`plans/{YYYYMMDD}_今日计划.md` — `SKILL.md:28`
- JD：`jd/{YYYYMMDD}_{公司简称}.md` — `SKILL.md:29`

---

## 17. 学习系统

### 来源文件
- `学习系统/MAIN/learning-system-main.md` — 主定义 + 七阶段学习法 + 触发条件
- `学习系统/MAIN/modules/` — 各模块定义
- `学习系统/scripts/learning.py` — CLI 入口

### 唤醒词与功能映射

| 唤醒词 | 功能 | 来源 |
|--------|------|------|
| 我要学XXX、开始学习XXX、学习XXX、帮我学XXX | 学习新知识 | `学习系统/MAIN/learning-system-main.md:196` |
| 我要复习、今天要复习什么 | 复习列表 | `学习系统/MAIN/learning-system-main.md:226` |
| 复习XXX | 复习指定知识 | `学习系统/MAIN/learning-system-main.md:239` |
| 我要精通XXX、继续精通XXX、开始精通流程 | 精通流程（主动） | `学习系统/MAIN/learning-system-main.md:253` |
| 基础流程完成时"是否继续进入精通流程？" | 精通流程（被动） | `学习系统/MAIN/learning-system-main.md:182` |
| 我要精通（无XXX）、我可以精通什么 | 精通列表 | `学习系统/MAIN/learning-system-main.md:268` |
| 我的学习进度、XXX学到哪了、查看学习状态、当前Level是多少 | 进度查询 | `学习系统/MAIN/learning-system-main.md:279` |
| 有哪些XXX、想学XXX相关的 | 知识探索 | `学习系统/MAIN/learning-system-main.md:294` |
| 综合练习、系统设计题、给我一道大题 | 能力整合（模式一：已知域） | `学习系统/MAIN/learning-system-main.md:308` |
| 随机挑战、随机出题、来道开放题 | 能力整合（模式二：探索域） | `学习系统/MAIN/learning-system-main.md:318` |

### 入口总览表 — `学习系统/MAIN/learning-system-main.md:169-180`
| 用户说 | 识别为 |
|--------|--------|
| 我要学XXX / 开始学习XXX / 学习XXX | 学习新知识 |
| 我要复习 / 今天要复习什么 | 复习列表 |
| 复习XXX | 复习指定知识 |
| 我要精通XXX / 继续精通XXX | 精通流程 |
| 我要精通（无XXX）/ 我可以精通什么 | 精通列表 |
| 我的学习进度 / XXX学到哪了 | 进度查询 |
| 有哪些XXX / 想学XXX相关的 | 知识探索 |
| 综合练习 / 系统设计题 / 给我一道大题 | 能力整合（模式一） |
| 随机挑战 / 随机出题 / 来道开放题 | 能力整合（模式二） |

### 七阶段 — `学习系统/MAIN/learning-system-main.md`
1. 采集 → 2. 整理 → 3. 初学 → 4. 练习 → 5. 复习 → 6. 精通 → 7. 教授

---

## 18. 作息管家

### 来源文件
- `作息管家/SKILL.md` — 主定义 + 功能速查表
- `作息管家/scripts/schedule_cli.py` — CLI 入口
- `作息管家/references/CLI命令.md` — 命令参考

### 唤醒词与功能映射

| 唤醒词 | 功能 | 来源 |
|--------|------|------|
| 同步作息、更新作息表 | 同步作息 | `作息管家/SKILL.md:15` |
| 总结作息、生成摘要 | 生成摘要 | `作息管家/SKILL.md:16` |
| 作息记录、今天干了什么 | 查询作息 | `作息管家/SKILL.md:17` |
| 查计划、今天计划 | 查询计划 | `作息管家/SKILL.md:18` |
| 新建计划、更新计划 | 设置计划 | `作息管家/SKILL.md:19` |

### 核心规则 — `作息管家/SKILL.md`
- 睡眠归属就寝日 — `SKILL.md:14`
- 时间必须连续（00:00-23:59） — `SKILL.md:14`
- source_contents 必须是消息原文 — `SKILL.md:14`

---

## 19. Github导航台

### 来源文件
- `Github导航台/SKILL.md` — 主定义 + 触发词 + 视觉规范
- `Github导航台/generate_nav.py` — 生成导航数据
- `Github导航台/deploy.py` — 部署脚本

### 唤醒词与功能映射

| 唤醒词 | 功能 | 来源 |
|--------|------|------|
| 更新文档导航 | 扫描目录 → 生成 structure.json → 部署 | `Github导航台/SKILL.md`（触发词区域） |
| 导航台 | 扫描目录 → 生成 structure.json → 部署 | `Github导航台/SKILL.md`（触发词区域） |
| docs 导航 | 扫描目录 → 生成 structure.json → 部署 | `Github导航台/SKILL.md`（触发词区域） |

### 视觉风格 — `Github导航台/SKILL.md`
- 历史图书馆数字档案网站风格
- 深勃艮第红、墨黑、黄铜金色调
- Garamond 衬线字体

---

## 20. 勋章

### 来源文件
- `勋章/SKILL.md` — 主定义 + 设计规范 + 触发链
- `勋章/materials.md` — 素材参考
- `勋章/scripts/medal.py` — 勋章生成
- `勋章/scripts/generate_medal_gif.py` — GIF 生成

### 唤醒词与功能映射

| 唤醒词 | 功能 | 来源 |
|--------|------|------|
| 勋章、颁发勋章 | 生成精美 GIF 勋章 | `勋章/SKILL.md:3` |
| 证书 | 生成精美 GIF 证书 | `勋章/SKILL.md:3` |
| 奖杯 | 生成精美 GIF 奖杯 | `勋章/SKILL.md:3` |
| 刚睡、22:30睡的 | 早睡链 → 颁发"早睡党" | `勋章/SKILL.md:822` |
| 学了什么 | 学习链 → 颁发"开始学习" | `勋章/SKILL.md:837` |
| 休息、躺了一天 | 休息链 → 颁发"休闲党" | `勋章/SKILL.md:853` |
| 称了体重 | 体重链 → 颁发"体重记录" | `勋章/SKILL.md:869` |
| 跑了步、骑了车 | 运动链 → 颁发"开始运动" | `勋章/SKILL.md:885` |
| 今天做了XX | 通用触发 → 默认颁发 badge | `勋章/SKILL.md:897` |

### 勋章触发条件 — `勋章/SKILL.md:509-554`
| 等级 | 触发条件 | 来源 |
|------|---------|------|
| Badge（勋章） | 做了任何值得肯定的事 | `SKILL.md:511` |
| Certificate（证书） | 完成了有份量的事或达到了某个节点 | `SKILL.md:530` |
| Trophy（奖杯） | 赢了——不管是赢别人还是赢自己 | `SKILL.md:547` |

### 触发链体系 — `勋章/SKILL.md:815-897`
| 链 | 基础触发 | 进阶触发 | 终极触发 |
|----|---------|---------|---------|
| 早睡链 | 刚睡→早睡党 | 累计7次→早睡达人 | 连续14天→早睡里程碑 |
| 学习链 | 学了→开始学习 | 累计10h→学习达人 | 连续7天→学习里程碑 |
| 休息链 | 休息→休闲党 | 连续2天→躺平达人 | 连续5天→摆烂警告 |
| 体重链 | 称了→体重记录 | 下降0.5kg→体重下降 | — |
| 运动链 | 跑了→开始运动 | — | — |

### 设计原则 — `勋章/SKILL.md:12-14`
- 勋章的魂在「静谧」 — `SKILL.md:12`
- 证书的魂在「神秘」 — `SKILL.md:13`
- 奖杯的魂在「不可战胜」 — `SKILL.md:14`

### 禁用词汇 — `勋章/SKILL.md:24-30`
- 蓝色 → 精确色相 — `SKILL.md:28`
- 金属质感 → 具体材质 — `SKILL.md:29`
- 清新禅意风格 → 视觉现象描述 — `SKILL.md:30`

---

## 21. 医药国际注册

### 来源文件
- `医药国际注册/SKILL.md` — 主定义 + 6套方法论索引
- `医药国际注册/快速探索法.md` — 了解新市场
- `医药国际注册/规范注册法.md` — 正式注册项目
- `医药国际注册/多角色决策法.md` — 策略决策
- `医药国际注册/流水线作业法.md` — 批量编制资料
- `医药国际注册/持续迭代法.md` — 缺陷信回复
- `医药国际注册/项目管控法.md` — 多国项目管理
- `医药国际注册/CTD模块撰写.md` — CTD 文档编制
- `医药国际注册/缺陷信回复.md` — 缺陷信处理
- `医药国际注册/法规调研报告模板.md` — 模板
- `医药国际注册/注册申请信模板.md` — 模板
- `医药国际注册/缺陷信回复模板.md` — 模板

### 唤醒词与功能映射

| 唤醒词 | 功能 | 方法论 | 来源 |
|--------|------|--------|------|
| 医药国际注册、药品注册、国际注册 | 通用入口 | — | `SKILL.md:11` |
| FDA注册 | 美国注册 | 规范注册法 | `SKILL.md:11` |
| EMA注册 | 欧盟注册 | 规范注册法 | `SKILL.md:11` |
| NAFDAC注册 | 尼日利亚注册 | 规范注册法 | `SKILL.md:11` |
| CEMAC注册 | 中非注册 | 规范注册法 | `SKILL.md:11` |
| CTD文档、注册申报 | 文档编制 | 流水线作业法 | `SKILL.md:12` |
| 仿制药注册 | 仿制药专项 | 规范注册法 | `SKILL.md:12` |
| 注册策略 | 策略决策 | 多角色决策法 | `SKILL.md:12` |
| 法规查询 | 法规调研 | 快速探索法 | `SKILL.md:12` |
| 缺陷信回复 | 缺陷信处理 | 持续迭代法 | `SKILL.md:13` |
| 注册项目管理 | 项目管控 | 项目管控法 | `SKILL.md:13` |
| 多国注册、注册进度跟踪 | 多国管理 | 项目管控法 | `SKILL.md:13` |
| 注册计划 | 计划管理 | — | `SKILL.md:13` |
| 注册文档 | 文档管理 | — | `SKILL.md:13` |
| 药政局、国际药品注册 | 通用入口 | — | `SKILL.md:14` |

---

## 22. 深夜书单-PDF书籍转为md

### 来源文件
- `深夜书单-PDF书籍转为md/SKILL.md` — 主定义 + OCR 处理流程

### 唤醒词与功能映射

| 唤醒词 | 功能 | 来源 |
|--------|------|------|
| PDF转md | 启动 OCR 处理流程 | 推断自 SKILL.md:1 |
| OCR处理 | 启动 OCR 处理流程 | 推断自 SKILL.md:1 |
| 扫描图书馆 | 扫描图书馆目录找待处理 PDF | `SKILL.md:11` |

### 处理流程 — `深夜书单-PDF书籍转为md/SKILL.md:9-30`
1. 扫描图书馆目录 → 找到第一本待处理 PDF — `SKILL.md:11`
2. 用 pymupdf 获取总页数 — `SKILL.md:28`
3. 逐页调用智谱 GLM Layout API 解析 — `SKILL.md:7`
4. 输出 `page_*.md` 文件

---

## 23. 百科采集

### 来源文件
- `百科采集/SKILL.md` — 主定义 + 工作流

### 唤醒词与功能映射

| 唤醒词 | 功能 | 来源 |
|--------|------|------|
| 百科采集、采集百科 | 启动百科知识采集 | 推断自 SKILL.md:1 |
| 今天学什么 | 随机领域百科 | 推断自 SKILL.md:4 |

### 工作流 — `百科采集/SKILL.md:9-30`
1. 随机选领域（22个领域可选） — `SKILL.md:12-13`
2. Tavily 深度搜索 — `SKILL.md:15`
3. 失败时切换 MiniMax 搜索 — `SKILL.md:20`
4. 迭代直到成功 — `SKILL.md:23`
5. 生成 Markdown 文档 — `SKILL.md:26`

---

## 24. 洋洋定制

### 来源文件
- `洋洋定制/llm-wiki/SKILL.md` — LLM Wiki 技能定义

### 唤醒词与功能映射

| 唤醒词 | 功能 | 来源 |
|--------|------|------|
| 洋洋定制 | 进入定制模式 | 推断自目录名 |
| 创建wiki、知识库 | 创建 LLM Wiki | `洋洋定制/llm-wiki/SKILL.md:29` |
| 添加源、处理源 | 向 Wiki 添加知识源 | `洋洋定制/llm-wiki/SKILL.md:30` |
| 审计wiki、健康检查 | 检查 Wiki 质量 | `洋洋定制/llm-wiki/SKILL.md:32` |

---

## 唤醒词冲突分析

以下唤醒词在多个 SKILL 中出现，可能导致触发冲突：

| 唤醒词 | 冲突技能 | 来源 | 建议 |
|--------|---------|------|------|
| 看看、查看、详情 | 备忘录 `SKILL.md:75` / 私家大厨 `SKILL.md:128-134` | 需上下文消歧 |
| 删除、删掉 | 备忘录 `SKILL.md:70` / 卡路里（已改为"删吃的"，无冲突） | 卡路里已改造，无冲突 |
| 记录 | 私家大厨 `SKILL.md:186` / 录音机 `SKILL.md:18` | 需上下文消歧 |
| 搜索、查找 | 备忘录 `SKILL.md:61` / 饼干记账 `SKILL.md:60` / 居家管家 | 需上下文消歧 |
| 添加 | 备忘录 `SKILL.md:51` / 私家大厨 `SKILL.md:215` / 居家管家 | 需上下文消歧 |
| 改、修改 | 备忘录 `SKILL.md:65` / 私家大厨 `SKILL.md:165` / 居家管家 | 需上下文消歧 |
| 最近 | 备忘录 `SKILL.md:79` / 饼干记账 `SKILL.md:58` / 卡路里（已改为"查热量历史"，无冲突） | 备忘录/饼干记账需消歧，卡路里已改造 |
| 提醒 | 备忘录 `SKILL.md:88` / 共享单车提醒 `SKILL.md:11` | 备忘录优先（强制路由） |
| 健康检查、lint、检查数据 | 居家管家 `SKILL.md:114` / 卡路里（已改为"查卡路里数据"，无冲突） | 居家管家保留，卡路里已改造 |
| 复习XXX | 学习系统 `learning-system-main.md:239` | 学习系统独占 |
| 有哪些XXX、想学XXX相关的 | 学习系统 `learning-system-main.md:294` / 私家大厨 `SKILL.md:147` | 需上下文消歧（"有哪些"在两个技能中都出现） |
| 刚睡、22:30睡的 | 勋章 `SKILL.md:822` / 卡路里（已改为"记睡眠"，无冲突） / 作息管家 | 勋章触发颁奖，卡路里/作息管家触发睡眠记录——可能联动 |
| 称了体重 | 勋章 `SKILL.md:869` / 卡路里（已改为"记体重"，无冲突） | 勋章触发颁奖，卡路里触发体重记录——可能联动 |
| 跑了步、骑了车 | 勋章 `SKILL.md:885` / 卡路里（已改为"记运动"，无冲突） | 勋章触发颁奖，卡路里触发运动记录——可能联动 |
| 学了什么 | 勋章 `SKILL.md:837` / 学习系统 `learning-system-main.md:196` | 勋章触发颁奖，学习系统触发学习流程——可能联动 |
| 休息、躺了一天 | 勋章 `SKILL.md:853` / 作息管家 | 勋章触发颁奖，作息管家记录休息——可能联动 |
