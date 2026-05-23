---
name: 饼干记账
description: 记账技能，支持文字/图片记账、查询统计、分类分析。触发词：记账、花了、收入、账单。
---

## 操作规范（强制）

- 所有数据操作通过 CLI（`scripts/record_bill.py`），禁止直连数据库
- 只读操作（查询/统计）不需确认，写入操作（记账）需用户确认
- 不支持删除和修改已有记录
- 金额必须明确，不能猜测

---

## 安装与配置

### 依赖

- Python 3.x（系统自带 sqlite3）

### 配置项

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `SKILLS_DB_PATH` | 数据库目录 | 技能目录下 `.db/` |

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
- **分析报表**：月度汇总、周期对比、分类明细

---

## 使用流程

| 用户说 | 触发功能 | AI 执行命令 |
|--------|----------|-------------|
| "记账"、"花了X元"、"付了"、"消费"、"买了" | 记账 | `add --category <分类> --amount <金额> --note "<备注>"` |
| "收到X元"、"收入"、"进账"、"工资" | 收入记录 | `add --category <分类> --amount +<金额> --note "<备注>"` |
| 发截图/账单图片 | 图片记账 | 识别图片金额，确认后执行 `add` |
| "今天花了多少"、"今日支出"、"查账单" | 今日摘要 | `summary` |
| "这个月消费"、"本月支出" | 月度汇总 | `monthly --month <YYYY-MM>` |
| "上周花了多少"、"上月账单" | 周期对比 | `compare --period week/month` |
| "最近的记录"、"最近N条" | 最近记录 | `recent --limit <N>` |
| "各类支出占比"、"分类明细" | 分类明细 | `breakdown` |
| "找一下XX的记录" | 搜索 | `search "<关键词>"` |

**记账解析规则：**
- "花了/付了/消费/支出" → 负数金额
- "收到/收入/进账" → 正数金额
- 未指定时间 → 默认当前时间
- 未指定分类 → 根据内容推断，告知用户可纠正
- 分类参考 `references/categories.md`

**图片识别规则：**
1. 优先取「实付/实收/已支付/需付」金额
2. 其次取「合计/总计/总额/应付」金额
3. 忽略：单品价格、优惠减免、配送费、税额、找零
4. 无法判断时，描述看到的内容并请用户确认

---

## 命令行参考

### 添加记录
```bash
python3 scripts/record_bill.py add --category 餐饮 --amount -35.0 --note "午饭"
# 可选参数：--time "2026-05-23 12:30:00" --account "" --ledger "生活" --currency "人民币"
```

### 查询今日
```bash
python3 scripts/record_bill.py list
```

### 查询指定日期
```bash
python3 scripts/record_bill.py list --date 2026-05-23
```

### 查询日期范围
```bash
python3 scripts/record_bill.py list --from 2026-05-01 --to 2026-05-31
```

### 按分类查询
```bash
python3 scripts/record_bill.py list --category 餐饮
```

### 搜索备注
```bash
python3 scripts/record_bill.py search "午饭"
```

### 今日摘要
```bash
python3 scripts/record_bill.py summary
```

### 月度汇总
```bash
python3 scripts/record_bill.py monthly --month 2026-05
```

### 周期对比
```bash
python3 scripts/record_bill.py compare --period week
python3 scripts/record_bill.py compare --period month
```

### 最近N条
```bash
python3 scripts/record_bill.py recent --limit 10
```

### 分类明细
```bash
python3 scripts/record_bill.py breakdown
python3 scripts/record_bill.py breakdown --from 2026-05-01 --to 2026-05-31
```

---

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| 图片模糊/看不清金额 | 描述看到的内容，请用户确认 |
| 图片非账单 | 告知用户并询问是否手动输入 |
| 未指定分类 | 根据内容推断，告知用户可纠正 |
| 金额不明确 | 请用户确认，不自动猜测 |
