---
name: 饼干记账
description: 记账技能。写入类:记支出、记收入、拍账单、批量录入、改记录、撤销、恢复、记报销、记退款、记借出、记借入、记收回、记偿还、记分期。查询类:查今天、查某天、查月、查区间、查分类、搜备注、查标签、查账户、查账本、查欠款、查待报销。分析类:看月度、看总览、看分类、看对比、看趋势、看大额、做统计、看洞察、看借贷。目标/账户/联动:设定预算、看预算、设定目标、看目标、账户转账、买东西联动、吃饭联动。**所有查询/分析类唤醒词默认 invoke HTML 工作流**(scripts/bill_inject.py + templates),写入类保持文字回执。能力速查:说「饼干记账 HELP」/「查帮助」/「能做什么」。完整 70 个唤醒词见 references/路由表.md
---

**🔗 联动提示：** 完成本技能主操作后，检查技能路由器（`图片路由/SKILL.md`）的联动规则，判断是否需要联动其他技能（如用户提到买了实物→询问是否录入居家管家；用户提到食物→询问是否记录卡路里）。详见路由器的联动规则表。

## 强制性规定（最高优先级）

1. **该技能的所有优化和变动、脚本的所有变动都要体现在 `饼干记账.html` 上** — HTML 是技能的可视化手册，任何功能变更必须同步更新
2. **本规定优先级最高**，高于下方所有操作规范
3. **对该技能的所有文件、脚本的任何一行修改都需要明确得到用户的 1 次确认** — 禁止未经确认的自动修改

---

## 操作规范（强制）

- 所有数据操作通过 CLI（`scripts/write|query|analysis/cli.py` 三域入口），禁止直连数据库
- 只读操作（查询/分析/统计）不需确认；写入操作（记支出/记收入/拍账单/改记录）需用户确认
- 不支持删除已有记录；修改功能见「改记录」流程
- 金额必须明确，不能猜测

---

## 安装与配置

### 依赖

- Python 3.x（系统自带 sqlite3）

### 配置项

| 环境变量 | 说明 | 
|----------|------|
| `SKILLS_DB_PATH` | 数据库目录 |

### 一键安装

```
请帮我初始化饼干记账技能：
1. 检查 Python 环境
2. 引导我配置环境变量
3. 显示当前环境变量配置
4. 告诉我如何更改数据目录
```

---

## 功能概述

- **文字记账**：解析自然语言，提取金额、分类、备注
- **图片记账**：看图识别账单金额，用户确认后记录
- **查询统计**：今日/指定日期/日期范围/分类查询
- **分析报表**：月度汇总、周期对比、分类明细、收支总览

---

## 唤醒词总表

> 全量 70 个唤醒词(2026-08-08 路由表定案);编号见 references/路由表.md;新增在域区间内追加

| 类型 | 唤醒词 | 功能 | CLI 指令 | 默认输出 |
|------|--------|------|----------|----------|
| 写入 | `记支出` | 记一笔支出 | `write add` | 文字回执 |
| 写入 | `记收入` | 记一笔收入 | `write add` | 文字回执 |
| 写入 | `拍账单` | 拍账单记账(图片识别) | `write add(图片识别)` | 文字回执 |
| 写入 | `批量录入` | 批量录入多笔 | `write add(批量)` | 文字回执 |
| 写入 | `记退款` | 记一笔退款(冲销原支出) | `write add + update(#已退款)` | 文字回执 |
| 写入 | `记报销` | 记一笔报销支出(#待报销) | `write add(#待报销)` | 文字回执 |
| 写入 | `报销到账` | 报销到账(记收入 + 流转标签) | `write add + update(标签流转)` | 文字回执 |
| 写入 | `记借出` | 借给别人钱 | `write add(借贷账本)` | 文字回执 |
| 写入 | `记借入` | 向别人借钱 | `write add(借贷账本)` | 文字回执 |
| 写入 | `记收回` | 收回借出的钱 | `write add + update(#已还)` | 文字回执 |
| 写入 | `记偿还` | 偿还借入的钱 | `write add + update(#已还)` | 文字回执 |
| 写入 | `记分期` | 记一笔分期(平摊预写) | `write add×N(平摊预写)` | 文字回执 |
| 写入 | `改记录` | 修改已有记录 | `write update` | 文字回执 |
| 写入 | `撤销` | 撤销一条记录(软删) | `write update(deleted_at)` | 文字回执 |
| 写入 | `恢复` | 恢复已撤销记录 | `write update(deleted_at=NULL)` | 文字回执 |
| 查询 | `查今天` | 查今天收支 | `query summary` | **HTML** |
| 查询 | `查昨天` | 查昨天收支 | `query list --date` | **HTML** |
| 查询 | `查某天` | 查某一天的账 | `query list --date` | **HTML** |
| 查询 | `查最近` | 查最近记录 | `query recent` | **HTML** |
| 查询 | `查周` | 查某周的账 | `query list --from --to` | **HTML** |
| 查询 | `查月` | 查某个月的账 | `query list --from --to` | **HTML** |
| 查询 | `查区间` | 查任意时间段 | `query list --from --to` | **HTML** |
| 查询 | `查分类` | 查某分类的账 | `query list --category` | **HTML** |
| 查询 | `搜备注` | 搜索备注关键词 | `query search` | **HTML** |
| 查询 | `查标签` | 查标签(#tag 聚合) | `query tag --tag` | **HTML** |
| 查询 | `查账户` | 查某账户流水 | `query list --account` | **HTML** |
| 查询 | `查账本` | 查某账本的记录 | `query list --ledger` | **HTML** |
| 查询 | `查欠款` | 查未还欠款(借贷状态) | `query debt` | **HTML** |
| 查询 | `查待报销` | 查待报销 | `query reimburse` | **HTML** |
| 查询 | `查分期` | 查进行中的分期 | `query installment` | **HTML** |
| 分析 | `看月度` | 某月收支汇总 | `analysis monthly` | **HTML** |
| 分析 | `看年度` | 年度收支汇总 | `analysis monthly(年) + trend` | **HTML** |
| 分析 | `看总览` | 时间段收支总览 | `analysis overview` | **HTML** |
| 分析 | `看周报` | 本周简报(对比上周) | `analysis compare week` | **HTML** |
| 分析 | `看分类` | 钱花在哪些分类 | `analysis breakdown` | **HTML** |
| 分析 | `看账户` | 各账户花销情况 | `analysis breakdown(账户)` | **HTML** |
| 分析 | `看账本` | 各账本收支汇总 | `analysis breakdown(账本)` | **HTML** |
| 分析 | `看结构` | 收入支出来源去向 | `analysis breakdown×2` | **HTML** |
| 分析 | `看对比` | 本期和上期对比 | `analysis compare` | **HTML** |
| 分析 | `看双区间` | 两段时间对比 | `analysis compare(区间)` | **HTML** |
| 分析 | `看同比` | 今年和去年同比 | `analysis compare(同比)` | **HTML** |
| 分析 | `看分类对比` | 两段时间分类差异 | `analysis compare(分类)` | **HTML** |
| 分析 | `看趋势` | 每月收支走势 | `analysis trend(待实施)` | **HTML** |
| 分析 | `看分类趋势` | 某分类的月度变化 | `analysis trend(分类·待实施)` | **HTML** |
| 分析 | `看大额` | 大额支出排行 | `analysis top(待实施)` | **HTML** |
| 分析 | `看高频` | 高频消费排行 | `analysis top(频次·待实施)` | **HTML** |
| 分析 | `看分布` | 金额区间分布 | `analysis distribution(待实施)` | **HTML** |
| 分析 | `做统计` | 记账情况统计 | `analysis stats` | **HTML** |
| 分析 | `看活跃` | 记账活跃度 | `analysis activity(待实施)` | **HTML** |
| 分析 | `看洞察` | AI 消费洞察 | `analysis insight(待实施·接洞察生成器)` | **HTML** |
| 分析 | `看异常` | 异常波动检测 | `analysis anomaly(待实施·接洞察生成器)` | **HTML** |
| 分析 | `看借贷` | 借贷总览 | `analysis debt(待实施·#借贷)` | **HTML** |
| 分析 | `看报销` | 报销汇总 | `analysis reimburse(待实施·#待报销)` | **HTML** |
| 分析 | `看分期` | 分期总览 | `analysis installment(待实施·#分期)` | **HTML** |
| 分析 | `看退款` | 退款统计 | `analysis refund(待实施·#退款)` | **HTML** |
| 目标 | `设定预算` | 设定月度预算 | `goal set-budget --amount X [--month] [--category]` | **HTML 表单+回执** |
| 目标 | `看预算` | 查看预算执行 | `goal budget [--month]` | **HTML** |
| 目标 | `设定目标` | 设定储蓄目标 | `goal set-saving --name X --amount Y [--deadline]` | **HTML 表单+回执** |
| 目标 | `看目标` | 查看目标进度 | `goal saving [--name]` | **HTML** |
| 账户 | `新增账户` | 新增账户 | `account add(待实施)` | **HTML** |
| 账户 | `改账户` | 修改账户 | `account update(待实施)` | **HTML** |
| 账户 | `账户转账` | 账户间转账 | `account transfer(待实施·#转账)` | **HTML** |
| 账户 | `看账户汇总` | 查看账户汇总 | `account summary(待实施)` | **HTML** |
| 联动 | `买东西` | 买东西联动(记账 + 录物品) | `link form + receipt` | **HTML 表单+回执** |
| 联动 | `吃饭` | 吃饭联动(记账 + 记卡路里) | `link form + receipt` | **HTML 表单+回执** |
| 开始使用 | `初始化` | 首次使用向导(4 步零决策) | `setup init(待实施·4 步向导)` | **HTML** |
| 开始使用 | `初始化状态` | 初始化状态(是否已就绪) | `setup init-status(待实施)` | **HTML** |
| 开始使用 | `备份` | 一键备份 | `backup create ✓` | **HTML** |
| 开始使用 | `恢复备份` | 从备份恢复 | `backup restore ✓` | **HTML** |
| 开始使用 | `导入` | 导入 CSV 账单(列映射向导) | `setup import(待实施·CSV)` | **HTML** |
| HELP | `查帮助` | 能力速查 HELP | `render_help.py` | **HTML** |
| HELP | `能做什么` | 能力速查 HELP | `render_help.py` | **HTML** |

## 📌 输出位置（§04 原则 12.A / 12.B）

> **本 Skill 走 §04 原则 12.A / 12.B**，HTML 路径名规则固化如下，不可随意改动：

| 类型 | §12 分类 | 文件名规范 | 触发命令 |
|------|----------|------------|----------|
| **数据 / 过程 HTML**（12.A）| §12.A | `$DATA_DIR/biscuit_accountant_html/<command_zh>_<YYYYMMDD>_<HHMMSS>[_N].html` | `bill_inject.py <query_type> [args]` |
| **HELP HTML**（12.B）| §12.B | `$DATA_DIR/biscuit_accountant_html/饼干记账_HELP_<YYYYMMDD>_<HHMMSS>[_N].html` | `render_help.py` |

- `<command_zh>` 由 `scripts/html_paths.resolve_command_name()` 解析（如 `今日摘要` / `月度汇总` / `收支总览`）
- 同秒冲突自动追加 `_2` / `_3` 后缀
- `$DATA_DIR` 跟随 `SKILLS_DB_PATH` 环境变量（fallback `D:/.db/`）
- HELP 路径名固定以 `饼干记账_HELP_` 前缀（grep 一抓就出，便于检索历史 HELP 页）

---

## 使用流程

### Step 1：判断输入类型

| 输入类型 | 处理方式 |
|----------|----------|
| 纯文字 | 直接匹配唤醒词，解析金额、分类、备注 |
| 纯图片（无文字） | 进入「拍账单」流程，识别图片内容，展示结果，用户确认后记账 |
| 图片+文字 | 看图判断金额，用户文字作为备注或分类提示 |

### Step 2：匹配唤醒词

用户输入 → 匹配上述 14 个唤醒词之一 → 进入对应功能流程。

**自然语言别名映射（AI 解析时同时匹配）：**

| 用户说 | 路由到 |
|--------|--------|
| "花了X"、"付了"、"消费"、"买了" | → `记支出` |
| "收到X"、"进账"、"工资"、"赚了" | → `记收入` |
| "截图"、"发照片" | → `拍账单` |
| "改下"、"改记录"、"改成X"、"改X"、"修正"、"编辑" | → `改记录` |
| "今天花了多少"、"今日支出"、"查账" | → `查今天` |
| "昨天花了多少"、"5月1号的账" | → `查日期` |
| "这周的账"、"上周消费"、"5月1到10号" | → `查范围` |
| "餐饮类的记录"、"交通花了多少" | → `查分类` |
| "最近的记录"、"最近5条" | → `查最近` |
| "找一下XX"、"有没有XX的记录" | → `搜备注` |
| "这个月消费"、"本月支出"、"月度汇总" | → `看月度` |
| "这周和上周比"、"本月和上月比" | → `看对比` |
| "各类支出占比"、"分类明细" | → `看分类` |
| "收支情况"、"本月收支" | → `看总览` |
| "记了多少笔"、"记账情况" | → `做统计` |

### Step 3：解析参数

#### 记支出

| 用户说 | 解析结果 |
|--------|----------|
| "午饭35" | 分类=餐饮/外卖/午餐, 金额=-35 |
| "奶茶25" | 分类=餐饮/咖啡奶茶/奶茶, 金额=-25 |
| "打车20用支付宝" | 分类=出行/网约车, 金额=-20, 账户=支付宝 |
| "洗发水80" | 分类=居家/日用品(默认,如上下文有"理发/发廊"则→穿着/洗护), 金额=-80 |
| "昨天买书58" | 分类=玩乐/影音游戏/书籍影视(默认,如上下文有"教材/考试/备考"则→学习/书籍), 金额=-58, 时间=昨天 |
| "记账到旅行账本" | 账本=旅行 |

**文字解析关键词：**
- "花了 / 付了 / 消费 / 支出 / 买了" → 负数金额
- 未指定时间 → 默认当前时间
- 未指定分类 → 根据内容推断，告知用户可纠正
- 分类参考 `references/categories.md`(L1/L2/L3 三级 + 歧义词智能判断)

#### 记收入

| 用户说 | 解析结果 |
|--------|----------|
| "工资8000" | 分类=工资/基本工资, 金额=+8000 |
| "绩效3000" | 分类=工资/绩效, 金额=+3000 |
| "项目奖金5000" | 分类=奖金/项目奖金, 金额=+5000 |
| "副业赚了2000" | 分类=兼职/副业, 金额=+2000 |
| "基金分红300" | 分类=投资/分红, 金额=+300 |
| "红包100" | 分类=其他收入/红包, 金额=+100 |

**文字解析关键词：**
- "收到 / 收入 / 进账 / 工资 / 赚了" → 正数金额

#### 拍账单

| 用户输入 | 处理方式 |
|----------|----------|
| 发截图/账单图片 | 识别金额，展示结果，用户确认后记录 |
| 发模糊图片 | 描述看到的内容，请用户确认金额 |
| 发非账单图片 | 告知非账单，询问是否手动输入 |

**图片识别规则：**
1. 优先取「实付 / 实收 / 已支付 / 需付」金额
2. 其次取「合计 / 总计 / 总额 / 应付」金额
3. 忽略：单品价格、优惠减免、配送费、税额、找零
4. 无法判断时，描述看到的内容并请用户确认

#### 改记录

| 用户说 | 解析结果 |
|--------|----------|
| "把那条午饭改成 38" | id=查最近匹配项, amount=-38 |
| "改备注加牛奶" | id=用户指定或查最近匹配, note="原备注+牛奶" |
| "ID=123 改成分类=交通" | id=123, category=交通 |
| "把刚记的那笔改一下" | id=查最近第 1 条,字段待用户告知 |

**改记录流程(AI 层负责 diff + 确认):**
1. 通过 `查最近` / `查日期` / `搜备注` 定位目标记录的 ID(必要时把候选展示给用户挑)
2. 用户告知要改哪些字段、改成什么 → AI 计算 原值 → 新值 的 diff
3. **展示 diff 给用户,等待"确认"**(未确认前不调 update CLI)
4. 用户回复「确认」→ AI 调 `update --id <ID> [...新字段]`
5. CLI 返回结果 → AI 反馈「已修改」

**确认模板:**
```
📝 待修改(ID=123):
  分类:    餐饮     →  餐饮(未改)
  金额:    -35.00   →  -38.00
  备注:    午饭     →  午饭+牛奶
确认改?(回复「确认」或「取消」)
```

#### 查今天

无参数。返回今日 count / expense / income / net + 分类聚合 + 明细。

> **查询域通用规则**：全部查询 = 仅结果型 HTML（缺参 → AI 文字反问，不猜不补）；结果 HTML 默认动作区「复制数据 / 复制日志」；无数据 → 空态提示。

#### 查日期

| 用户说 | 解析结果 |
|--------|----------|
| "查昨天" | --date = 昨天日期 |
| "5月1号的账" | --date = 2026-05-01 |
| "上周五花了多少" | --date = 计算后的日期 |

#### 查范围

| 用户说 | 解析结果 |
|--------|----------|
| "这周的账" | --from 本周一 --to 今天 |
| "上周消费" | --from 上周一 --to 上周日 |
| "5月1到10号" | --from 2026-05-01 --to 2026-05-10 |

#### 查分类

| 用户说 | 解析结果 |
|--------|----------|
| "餐饮类的记录" | --category 餐饮 |
| "交通花了多少" | --category 交通 |
| "支付宝里餐饮花了多少" | --category 餐饮 --account 支付宝 --type expense |
| "旅行账本这个月的" | --category + --ledger 旅行 + --from/--to |

注意：分类支持 L1 前缀匹配（传「餐饮」命中 餐饮/外卖/午餐 等全部子分类）；可组合 时间/账户/账本/收支方向。返回 KPI(支出/收入/净额)+ 分类聚合 + 逐条记录。如需分类汇总统计，使用「看分类」。

#### 查最近

| 用户说 | 解析结果 |
|--------|----------|
| "最近5条" | --limit 5 |
| "最近的记录" | --limit 10（默认） |
| "近7天的记录" | --days 7 |
| "最近按金额从大到小" | --limit 10 --sort amount_desc |

返回：KPI(笔数/支出/收入/净额)+ 明细（默认时间倒序，可金额排序）。

#### 搜备注

| 用户说 | 解析结果 |
|--------|----------|
| "搜午饭" | keyword = 午饭 |
| "有没有咖啡的记录" | keyword = 咖啡 |

#### 查标签

| 用户说 | 解析结果 |
|--------|----------|
| "查 #旅行 的记录" | --tag 旅行 |
| "带 #待报销 的" | --tag 待报销 |

返回：#tag 聚合卡(笔数/支出/收入)+ 命中明细。精确匹配（#旅行 不误伤 #旅行计划）。

#### 查账户

| 用户说 | 解析结果 |
|--------|----------|
| "支付宝的流水" | --account 支付宝 |
| "招行这个月的" | --account 招行 --from/--to |

返回：该账户 KPI(支出/收入/净额)+ 明细。

#### 查账本

| 用户说 | 解析结果 |
|--------|----------|
| "旅行账本的记录" | --ledger 旅行 |
| "借贷账本" | --ledger 借贷 |

返回：该账本 KPI(支出/收入/净额)+ 明细。

#### 查欠款

| 用户说 | 解析结果 |
|--------|----------|
| "查欠款" | debt |
| "小明还欠多少" | debt --target 小明 |

聚合 `#未还` 记录：借出未还总额 + 借入未还总额 + 未还列表(对象/方向/金额/时间)。对象从备注 `#借给{X}` / `#向{X}借` 提取。

#### 查待报销

| 用户说 | 解析结果 |
|--------|----------|
| "查待报销" | reimburse |

聚合 `#待报销` 记录：总额 + 列表(金额/分类/日期)。

#### 查分期

| 用户说 | 解析结果 |
|--------|----------|
| "查分期" | installment |
| "手机的期数" | installment --name 手机 |

按备注 `#分期 {名目} 第X期/N` 分组：分期卡(名目/总额/每期/期数/已还期数/剩余期数+金额)+ 记录明细。已还期数按「日期 ≤ 今天」推断（分期写入即固定）。

#### 看月度

| 用户说 | 解析结果 |
|--------|----------|
| "本月汇总" | --month = 当前月（YYYY-MM） |
| "3月份的账" | --month = 2026-03 |

返回：支出/收入/净额 + 分类明细。

#### 看对比

| 用户说 | 解析结果 |
|--------|----------|
| "这周和上周比" | --period week |
| "本月和上月比" | --period month |

返回：本期/上期的支出/收入/净额 + 变化率。

#### 看分类

| 用户说 | 解析结果 |
|--------|----------|
| "各类支出占比" | 无参数，默认本月 |
| "5月的分类明细" | --from 2026-05-01 --to 2026-05-31 |

返回：各分类总支出/占比/笔数/均值。

#### 看总览

| 用户说 | 解析结果 |
|--------|----------|
| "本月收支" | --month = 当前月（默认） |
| "3月收支情况" | --month = 2026-03 |

返回：笔数/支出/收入/净额。

#### 做统计

无参数。返回总笔数、记账天数、首笔时间、最近记录时间。

### 目标域流程细则（4 场景 · 2026-08-09 落地 · 载体 goals.json）

目标域 4 场景统一遵守：

- **载体**：`goals.json`（与 db 同级，跟随 `SKILLS_DB_PATH`，备份机制已包含）。结构 = `{"budgets": [...], "savings": [...]}`，全部由 CLI 读写，AI 不手改。
- **实际数据 = bills 聚合**：预算执行 = 当月支出 vs 预算；目标进度 = 目标期内收入-支出累计（目标期 = 创建当月起 ~ 截止日/今天）。
- **渲染**：全部走 `scripts/goal/render.py <mode>`（采集表单 ×2 + 进度条视图 ×2），结果视图带「复制数据 / 复制日志」（B1 toast）。

#### 设定预算

| 用户说 | 解析结果 |
|--------|----------|
| "设个3000的月预算" | `set-budget --amount 3000`（默认本月） |
| "8月餐饮预算500" | `set-budget --amount 500 --month 2026-08 --category 餐饮` |
| "预算提到4000" | 先 `budget` 查现有 → 冲突提示 → 用户确认后加 `--force` |

**覆盖语义（数据契约）**：同月同类预算已存在 → CLI 返回 `conflict` + 原值（不覆盖）；AI 展示「已存在 X 元预算，确认覆盖为 Y？」→ 用户确认 → 加 `--force` 重跑。采集表单在渲染时自动查冲突并在表单顶部展示警示条。

#### 看预算

| 用户说 | 解析结果 |
|--------|----------|
| "预算花到哪了" | `budget`（默认本月） |
| "8月的预算执行" | `budget --month 2026-08` |

返回：结果型 HTML（进度条：预算 vs 实际 / 剩余 / 超支提示）。每预算进度条含状态机：≤90% 预算内（绿）/ 90%~100% 接近上限（橙）/ >100% 已超支（红，警示色）。KPI 汇总口径：总预算存在 → （总预算金额，当月全部支出）；否则 → 分类预算之和 vs 分类实际之和（避免重复计数）。

#### 设定目标

| 用户说 | 解析结果 |
|--------|----------|
| "存个换手机的目标10000" | `set-saving --name 换手机 --amount 10000` |
| "年底前存到1万" | `set-saving --name X --amount 10000 --deadline 2026-12-31` |

#### 看目标

| 用户说 | 解析结果 |
|--------|----------|
| "目标存到多少了" | `saving` |
| "看换手机那个目标" | `saving --name 换手机` |

返回：结果型 HTML（各目标进度：已存 / 目标 / 百分比 / 剩余 / 预计达成日）。预计达成日 = 按月均净存（已存 ÷ 目标期月数）推算；月均 ≤ 0 → 暂无预计；已达 → 标记 🎉；预计日晚于截止日 → 进度落后（红）。

### 写入流程细则（内置能力 + 特殊场景 · 2026-08-08 定稿）

所有写入类场景（记支出/记收入/拍账单/批量录入/记退款/记借出/记借入/记收回/记偿还/记分期）统一遵守：

#### 1. 分类选择器（过程型 HTML 必用）

信息不全面时，AI 生成过程型 HTML（采集表单）让用户补全：
- **AI 智能推荐**：根据用户话语义 + 现有分类库（references/categories.md）推荐：
  - 已有分类 → 标记「AI 推荐的已有分类」
  - 库里没有 → 标记「推荐新建分类」
- **手动选择**：下拉列出全部现有分类（L1/L2/L3 层级）
- **新建分类**：按钮 → 输入新分类名 → **校验相似**（已有「餐饮/外卖」时提示「是否使用已有的?」→ 拦一字之差）
- 原则：分类规范是数据质量核心，宁可让用户选，不让 AI 自造

#### 2. 智能预填（记支出/记收入）

用户话里有明确名目（如「交房租」）时：
- AI 检索历史同类记录（同分类 或 备注关键词匹配）
- 有 → 过程型 HTML 预填上次值（金额/分类/账户/账本/备注），标注「⚡ 根据 X 月 X 日的房租记录预填,可直接确认或修改」
- 无历史 → 正常空表单（不猜、不预填）
- **预填只是省填写**：不自动确认，用户可改可忽略

#### 3. 重复检测提示（写入时）

写入前 AI 检索近期相似记录（同分类 + 同金额 + 时间接近）：
- 疑似重复 → 提示「这笔和 X 月 X 日的 35 元午饭很像,确认要再记一笔吗?」
- 用户确认 → 继续写入；否认 → 正常写入

#### 4. tag 约定（备注 #tag）

| tag | 含义 | 使用场景 |
|---|---|---|
| #待报销 | 垫付待报销 | 记报销 |
| #报销到账 | 报销已回款 | 报销到账 |
| #退款 | 收到的退款 | 记退款 |
| #已退款 | 原支出已冲销 | 记退款（标记原支出） |
| #借出 / #借入 | 借贷方向 | 记借出 / 记借入 |
| #未还 / #已还 | 借贷状态机 | 借出/借入（#未还）→ 收回/偿还（#已还） |
| #收回 / #偿还 | 借贷回款 | 记收回 / 记偿还 |
| #分期 | 分期分摊记录 | 记分期（每笔备注 名目 第X期/N） |

#### 5. 特殊场景 AI 流程

**记退款**：① 查原支出（描述定位）② 记收入（分类=退款/冲销，备注 `#退款 原支出:[ID/描述]`）③ 原支出备注追加 `#已退款` ④ 回执两笔；找不到原支出 → AI 反问

**记借出/记借入**：记支出/收入（分类=借贷/借出|借入，账本=借贷，备注=`#借出 #借给{对象} #未还` / `#借入 #向{对象}借 #未还`）

**记收回/记偿还**：① 查 `#未还` 记录定位（对象/金额匹配）② 记反向（收回=收入 / 偿还=支出，分类=借贷/收回|偿还，账本=借贷，备注=`#收回 原记录ID`）③ 原记录备注 `#未还`→`#已还` ④ 回执两笔

**记分期**：每期=总价÷期数（除不尽首期补差额）→ 写 N 笔支出（分类=分期/{名目}，金额=每期，时间=首期日起每月同日，备注=`#分期 {名目} 第X期/N`）→ 向导确认（分摊预览）→ 回执总览；记录=消费分摊，写入即固定（提前还清不影响记录）

### 联动流程细则（买东西联动 / 吃饭联动 · 2026-08-09 落地）

联动域 2 场景 = **场景簇 + 回执按钮**（G2 决议）：主操作 = 记支出（复用 write add），联动 = 回执按钮（可选）。

#### 买东西联动（唤醒词：买东西）

1. AI 解析 金额/物品/分类（选填，默认 居家/家电）→ 调 `link/cli.py form purchase` 渲染采集表单（含联动预告条）
2. 用户确认（复制 prompt）→ AI 调 `write/cli.py add` 记支出（分类/金额/备注，备注建议含物品名，如 `空气炸锅`）
3. AI 调 `link/cli.py receipt purchase --id <ID> --item <物品>` 渲染回执 HTML：
   - 已记录账单卡（ID/金额/分类/账户/账本/时间/备注）
   - 联动按钮「🔗 同时录入居家管家」→ 点击复制联动 prompt（预告式：请加载「居家管家」技能,帮我录入刚买的物品(唤醒词:录物品)：物品/数量/金额/分类）→ 用户粘贴给 AI → AI 调居家管家「录物品」
   - 「↩ 撤销这笔」+ 复制数据/复制日志（08 硬标准）
4. 用户只记账不联动 → 正常回执，按钮可选不用

#### 吃饭联动（唤醒词：吃饭）

1. AI 解析 金额/吃了/分类（选填，默认 餐饮）→ 调 `link/cli.py form meal` 渲染采集表单
2. 用户确认 → AI 调 `write/cli.py add` 记支出
3. AI 调 `link/cli.py receipt meal --id <ID> --ate <吃了>` 渲染回执 HTML：
   - 联动按钮「🔗 同时记卡路里」→ 点击复制联动 prompt（请加载「卡路里」技能,帮我记一餐(唤醒词:记一餐)：吃了/餐别/备注）→ AI 调卡路里「记一餐」

**通用**：联动 prompt 只在回执按钮上（预告式，点击才复制）；缺金额 → AI 反问（不猜测）；联动 = 可选，不强制。

### Step 4：执行指令

```bash
# 记支出(多级分类:L1/L2/L3 用 / 分隔)
python3 scripts/scripts/write/cli.py add --category 餐饮/外卖/午餐 --amount -35.0 --note "午饭"
python3 scripts/scripts/write/cli.py add --category 餐饮/咖啡奶茶/奶茶 --amount -25.0

# 改记录(按 ID)
python3 scripts/scripts/write/cli.py update --id 123 --note "午饭+牛奶"
python3 scripts/scripts/write/cli.py update --id 123 --amount -38.0 --category 餐饮
python3 scripts/scripts/write/cli.py update --id 123 --amount -50 --account 微信 --ledger 餐饮

# 记收入
python3 scripts/scripts/write/cli.py add --category 工资/基本工资 --amount 8000.0 --note "5月工资"

# 查今天
python3 scripts/scripts/query/cli.py summary

# 查日期
python3 scripts/scripts/query/cli.py list --date 2026-05-27

# 查范围
python3 scripts/scripts/query/cli.py list --from 2026-05-01 --to 2026-05-31

# 查分类
python3 scripts/scripts/query/cli.py list --category 餐饮

# 查最近
python3 scripts/scripts/query/cli.py recent --limit 10
python3 scripts/scripts/query/cli.py recent --days 7 --sort amount_desc

# 搜备注
python3 scripts/scripts/query/cli.py search "午饭"

# 查标签(#tag 聚合)
python3 scripts/scripts/query/cli.py tag --tag 旅行

# 查欠款 / 查待报销 / 查分期(状态族聚合)
python3 scripts/scripts/query/cli.py debt --target 小明
python3 scripts/scripts/query/cli.py reimburse
python3 scripts/scripts/query/cli.py installment --name 手机

# 看月度
python3 scripts/scripts/analysis/cli.py monthly --month 2026-05

# 看对比
python3 scripts/scripts/analysis/cli.py compare --period week

# 看分类
python3 scripts/scripts/analysis/cli.py breakdown
python3 scripts/scripts/analysis/cli.py breakdown --from 2026-05-01 --to 2026-05-31

# 看总览
python3 scripts/scripts/analysis/cli.py overview
python3 scripts/scripts/analysis/cli.py overview --month 2026-05

# 做统计
python3 scripts/scripts/analysis/cli.py stats
```

### Step 5：回复用户

```
✓ 已记录：餐饮 -35.00
```

### Step 6：HTML 可视化查询（v2.3 · 默认工作流）

> **🎯 默认行为（§04 原则 11 HTML-First）：**
> 所有查询/分析/统计类唤醒词命中后，AI **默认** 调用 `scripts/bill_inject.py` 生成可视化 HTML 交付给用户。
> 文字答仅在用户**明确说**「不要 HTML」「给我文字版」「就告诉我数字」时才走。

**支持 13 种查询类型（全部默认 HTML）：**

| 类型 | CLI 子命令 | 适用场景 | bill_inject.py 调用 |
|---|---|---|---|
| 今日摘要 | `summary` | 看今日收支 | `bill_inject.py summary` |
| 列表 | `list` / `recent` / `search` | 看记录明细 | `bill_inject.py list --date 2026-07-27` |
| 查标签 | `tag` | #tag 聚合 | `bill_inject.py tag --tag 旅行` |
| 查欠款 | `debt` | 未还借贷聚合 | `bill_inject.py debt` |
| 查待报销 | `reimburse` | #待报销 清单 | `bill_inject.py reimburse` |
| 查分期 | `installment` | #分期 分期卡 | `bill_inject.py installment` |
| 月度汇总 | `monthly` | 看月度分类排行 | `bill_inject.py monthly --month 2026-07` |
| 周期对比 | `compare` | 本周 vs 上周 / 本月 vs 上月 | `bill_inject.py compare --period week` |
| 分类明细 | `breakdown` | 看各类支出占比（SVG 环形图） | `bill_inject.py breakdown --from ... --to ...` |
| 收支总览 | `overview` | 看月度 4 个 KPI | `bill_inject.py overview --month 2026-07` |
| 记账统计 | `stats` | 看总笔数 / 天数 | `bill_inject.py stats` |

**调用流程（AI 必走）：**

```bash
# 标准路径（自动调 CLI + 注入 HTML 模板 + 输出文件）
python3 scripts/bill_inject.py summary
python3 scripts/bill_inject.py monthly --month 2026-07
python3 scripts/bill_inject.py breakdown --from 2026-07-01 --to 2026-07-31
python3 scripts/bill_inject.py compare --period week
python3 scripts/bill_inject.py search "咖啡"
```

**错误处理（§04 原则 11 反模式 #3）：**
- HTML 生成失败 → **保留错误页 HTML** 交付给用户（bill_inject.py 自动处理）
- ❌ **禁止**降级为文字答（这是 fail mode,不是 fallback）
- 用户明确要文字 → 才走 `python3 scripts/scripts/query/cli.py summary`（无 --json）

**默认输出路径（v2.5 同步卡路里 §4.1）**：`$DATA_DIR/biscuit_accountant_html/<command_zh>_<YYYYMMDD>_<HHMMSS>[_N].html`
  - `DATA_DIR` 跟随 `SKILLS_DB_PATH` 环境变量（fallback `D:/.db/`）
  - 中文化 command 名：summary → 今日摘要 / monthly → 月度汇总 / overview → 收支总览
  - 同秒冲突自动追加 `_2` / `_3` 后缀

**指定输出路径**：`python3 scripts/bill_inject.py summary --out C:/Users/xxx/Desktop/x.html`

**交付给用户**：用 `<media src="..." type="file" />` 把生成的 HTML 文件交付，用户双击在浏览器打开即可看到可视化效果。

**模板特性（query_view.html）**：
- 单文件离线运行（无 CDN / 无 chart.js 依赖）
- Apple 视觉风格（圆角卡片 / 系统字体 / 蓝橙绿红配色）
- 自适应桌面 + 平板 + 手机
- 5 种状态：正常 / 空态 / 缺数据 / 错误 / 离线
- SVG 环形图（breakdown 用）
- 一键复制 ID 回 AI（每条记录含 ID）

**目标域 HTML（goal/render.py · 2026-08-09 落地）：**

| 场景 | CLI 子命令 | 模板 | goal/render.py 调用 |
|---|---|---|---|
| 设定预算（采集表单） | `set-budget` | `templates/目标/budget_form.html` | `goal/render.py set-budget --amount 3000 --month 2026-08` |
| 看预算（进度条） | `budget` | `templates/目标/budget_view.html` | `goal/render.py budget --month 2026-08` |
| 设定目标（采集表单） | `set-saving` | `templates/目标/saving_form.html` | `goal/render.py set-saving --name 换手机 --amount 10000` |
| 看目标（进度条） | `saving` | `templates/目标/saving_view.html` | `goal/render.py saving` |

目标域结果视图同样默认 HTML 交付（进度条 + 复制数据/日志），采集表单默认「填写确认 + 复制确认 prompt」。

**调用流程（AI 必走）：**

```bash
# 标准路径（自动调 CLI + 注入 HTML 模板 + 输出文件）
python3 scripts/goal/render.py set-budget --amount 3000
python3 scripts/goal/render.py budget
python3 scripts/goal/render.py set-saving --name 换手机 --amount 10000 --deadline 2026-12-31
python3 scripts/goal/render.py saving
```

**错误处理（§04 原则 11 反模式 #3）：**
- HTML 生成失败 → **保留错误页 HTML** 交付给用户（goal/render.py 自动处理）
- ❌ **禁止**降级为文字答（这是 fail mode,不是 fallback）
- 用户明确要文字 → 才走 `python3 scripts/scripts/goal/cli.py budget`（无 --json）

**默认输出路径（v2.5 同步卡路里 §4.1）**：`$DATA_DIR/biscuit_accountant_html/<command_zh>_<YYYYMMDD>_<HHMMSS>[_N].html`
  - `DATA_DIR` 跟随 `SKILLS_DB_PATH` 环境变量（fallback `D:/.db/`）
  - 中文化 command 名：set-budget → 设定预算 / budget → 看预算 / set-saving → 设定目标 / saving → 看目标
  - 同秒冲突自动追加 `_2` / `_3` 后缀

**指定输出路径**：`python3 scripts/goal/render.py budget --out C:/Users/xxx/Desktop/x.html`

**交付给用户**：用 `<media src="..." type="file" />` 把生成的 HTML 文件交付，用户双击在浏览器打开即可看到可视化效果。

**模板特性（templates/目标/*.html）**：
- 单文件离线运行（无 CDN / 无图表库依赖）
- Apple 视觉风格（圆角卡片 / 系统字体 / 蓝橙绿红配色）
- 自适应桌面 + 平板 + 手机
- 结果视图 5 种状态：正常 / 空态 / 缺数据 / 错误 / 离线
- 进度条组件（预算 vs 实际 / 已存 vs 目标）+ 状态机警示色（预算内绿 / 接近上限橙 / 已超支红；目标进行中蓝 / 落后红 / 达成绿）
- 采集表单：字段回显 + 覆盖冲突警示条 + 一键复制确认 prompt（对齐 scenes/goal.yaml）

### Step 7：HELP 能力速查（v2.4 升级）

当用户说「饼干记账 HELP」「饼干记账 帮助」「查帮助」「能做什么」时，AI 调用 `scripts/render_help.py` 生成 HELP HTML 并交付。

```bash
# 默认输出
python3 scripts/render_help.py
# 输出路径（v2.5.1）：$DATA_DIR/biscuit_accountant_html/饼干记账_HELP_<YYYYMMDD>_<HHMMSS>[_N].html

# 指定输出
python3 scripts/render_help.py --out /path/to/help.html

# 仅校验场景资产 schema（CI 用）
python3 scripts/render_help.py --check
```

**HELP HTML 契约（§07）：**
- 来源：`references/scenarios.json`（唯一事实源，含 `_categories` 元数据）+ `templates/help.html`（模板）
- 展示 **5 类别**（📝 写入类 / 🔍 查询类 / 📊 分析类 / 📈 统计类 / ❓ HELP）× **15 唤醒词** × **91 个合法场景**
- **3 层折叠**（类别 → 唤醒词 → 场景，**默认全部折叠**，点击 `<summary>` 展开）
- 每场景独立「📋 复制 prompt」按钮 + **iOS 风格 Toast 通知**（4.5s 自动消失）
- 粘性搜索栏 + 「全部展开 / 全部折叠」快捷键
- 移动端 fallback toggle（部分 Android WebView 兼容）
- 5 状态 fallback + 移动端适配

---

## 命令行参考

共 10 个子命令：

| 子命令 | 说明 | 必需参数 | 可选参数 |
|--------|------|----------|----------|
| `add` | 添加账单 | `--category`, `--amount` | `--time`, `--account`, `--ledger`, `--currency`, `--note` |
| `update` | 修改账单 | `--id` (必需) | `--category`, `--amount`, `--time`, `--account`, `--ledger`, `--currency`, `--note`(至少传一个) |
| `list` | 查询记录 | （无） | `--date`, `--from`+`--to`, `--category`, `--account`, `--ledger`, `--type`(expense/income), **`--json`** |
| `search` | 搜索备注 | `keyword`（位置参数） | **`--json`** |
| `summary` | 今日摘要 | （无） | **`--json`** |
| `tag` | 查标签(#tag 聚合) | `--tag` | **`--json`** |
| `debt` | 查欠款(#未还 聚合) | （无） | `--target`, **`--json`** |
| `reimburse` | 查待报销(#待报销) | （无） | **`--json`** |
| `installment` | 查分期(#分期 聚合) | （无） | `--name`, **`--json`** |
| `monthly` | 月度汇总 | `--month` | **`--json`** |
| `compare` | 周期对比 | （无） | `--period` (week/month, 默认 week), **`--json`** |
| `recent` | 最近N条 | （无） | `--limit` (默认 10), `--days`, `--sort`(amount_desc/amount_asc), **`--json`** |
| `breakdown` | 分类明细 | （无） | `--from`, `--to`, **`--json`** |
| `overview` | 收支总览 | （无） | `--month` (默认当月), **`--json`** |
| `stats` | 记账统计 | （无） | **`--json`** |
| `form` | 联动采集表单渲染(买东西联动/吃饭联动) | `purchase`/`meal`(位置参数) | `--amount`, `--item`/`--ate`, `--category`, `--category-hint`, `--account`, `--ledger`, `--time`, `--note`, `--currency`, `--out` |
| `receipt` | 联动回执渲染(回执带联动按钮) | `purchase`/`meal` + `--id`(必需) | `--item`/`--ate`, `--out` |
| `set-budget` | 设定月度预算(goal) | `--amount` | `--month`(默认本月), `--category`(不填=总预算), `--force`(覆盖), **`--json`** |
| `budget` | 查看预算执行(goal) | （无） | `--month`, `--category`, **`--json`** |
| `set-saving` | 设定储蓄目标(goal) | `--name`, `--amount` | `--deadline`, **`--json`** |
| `saving` | 查看目标进度(goal) | （无） | `--name`, **`--json`** |

> **JSON 契约**：所有查询命令加 `--json` 后输出 `{status: "ok"|"error", data: {...}, message: "..."}` 三段式。`bill_inject.py` 用此契约注入 HTML 模板。写入类命令（add/update）不支持 `--json`，保持纯文本输出。目标域 4 命令（`set-budget` / `budget` / `set-saving` / `saving`）在 `scripts/goal/cli.py`（HTML 渲染走 `scripts/goal/render.py`）；`set-budget` 覆盖冲突时返回 `status: "ok"` + `data.conflict: true`（原值在 `data.existing`），AI 据此提示用户确认后加 `--force`。

---

## 分类参考

分类采用 **L1/L2/L3 三级** 结构(支出)/ **L1/L2 二级** 结构(收入),用 `/` 分隔(如 `餐饮/外卖/午餐`)。

**AI 解析必读 `references/categories.md` 的「分类心法」章节** — 心法包含 5 个判断维度(主体/目的/对象/工具vs体验/谁付费)和边界示例。**不要"关键词查表",要按意图推场景。** 关键词表只在心法覆盖不到时兜底。

**支出 L1(10 个):** 餐饮、居家、穿着、出行、玩乐、学习、健康、社交、宠物、其他

**收入 L1(5 个):** 工资、奖金、兼职、投资、其他收入

> 旧数据中不带 `/` 的分类(如 `餐饮`、`交通`)自动视为 L1,无需迁移。

---

## 与其他工具的边界

本 Skill 的 **5 层骨架**（数据层 `db.py` / 操作层 `analyze.py` / 规则层 `validators.py` / 接口层 `write|query|analysis/cli.py`(三域) / 文档层 `references/`+`templates/`）**不含** `config-cookie-accounting.ts`。

| 文件 | 归属 | 维护方 | 与本 Skill 的关系 |
|------|------|--------|-------------------|
| `config-cookie-accounting.ts` | SkillBoard 数据层视图（legacy） | 独立维护 | 不在 5 层骨架内；权威分类体系以 [`references/categories.md`](references/categories.md) 为准 |
| `references/categories-mapping.md` | 本 Skill 文档层 | 本 Skill 维护 | 桥接 `config-cookie-accounting.ts`（9 L1）→ `categories.md`（10 L1）；仅做语义映射，不修改任何一方的字段 |

> **若未来澄清 `config-cookie-accounting.ts` 为废弃**：需独立 spec 处理；本 Skill 当前仅做桥接文档（`references/categories-mapping.md`），不删不改 `config-cookie-accounting.ts`。

---

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| 图片模糊/看不清金额 | 描述看到的内容，请用户确认 |
| 图片非账单 | 告知用户并询问是否手动输入 |
| 未指定分类 | 根据内容推断，告知用户可纠正 |
| 金额不明确 | 请用户确认，不自动猜测 |