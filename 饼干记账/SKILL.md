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
1. 确认 Python 3.x 已安装
2. 执行 python3 scripts/record_bill.py summary 验证数据库自动初始化
```

---

## 功能概述

- **文字记账**：解析自然语言，提取金额、分类、备注
- **图片记账**：看图识别账单金额，用户确认后记录
- **查询统计**：今日/指定日期/日期范围/分类查询
- **分析报表**：月度汇总、周期对比、分类明细

---

## 使用流程

### Step 1：判断输入类型

| 输入类型 | 处理方式 |
|----------|----------|
| 纯文字 | 直接解析金额、分类、备注 |
| 纯图片（无文字） | 识别图片内容，展示识别结果，用户确认后记账 |
| 图片+文字 | 看图判断金额，用户文字作为备注或分类提示 |

### Step 2：解析账单信息

提取字段：

| 字段 | 说明 |
|------|------|
| `amount` | 金额（元，负数为支出，正数为收入） |
| `category` | 分类，参考 `references/categories.md` |
| `time` | 时间（默认当前时间） |
| `note` | 备注（可选） |

**文字解析关键词：**
- "花了 / 付了 / 消费 / 支出" → 负数金额
- "收到 / 收入 / 进账" → 正数金额

### Step 3：图片识别（如有图片）

**直接观察图片内容，按以下优先级判断金额：**

1. 「实付 / 实收 / 已支付 / 需付 / 支付金额」→ 用户最终付出的钱
2. 「合计 / 总计 / 总额 / 应付」→ 订单总价
3. 忽略：单品价格、优惠减免、配送费、税额、找零
4. 若有多个候选，选语义最接近「最终实际支付」的数字
5. 无法判断时，描述看到的内容并请用户确认金额

### Step 4：执行记录

```bash
python3 scripts/record_bill.py add \
  --category 餐饮 \
  --amount -35.0 \
  --time "2026-05-23 12:30:00" \
  --note "午饭"
```

### Step 5：回复用户

```
✓ 已记录：餐饮 -35.00
```

---

## 命令行功能

### 添加记录
```bash
python3 scripts/record_bill.py add --category 餐饮 --amount -35.0 --note "午饭"
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

---

## AI 触发指引

### 触发场景：用户提到记账/消费/收入

触发词：
- "记账"、"花了"、"付了"、"消费"
- "收到钱"、"进账"、"收入"
- 发截图/账单图片（无需文字，AI 自动识别）

操作步骤：
1. 解析用户输入，提取：分类、时间、金额、备注
2. 执行：`python3 scripts/record_bill.py add --category <分类> --amount <金额> --time "<时间>" --note "<备注>"`
3. 返回确认信息

### 触发场景：用户要查看账单

触发词：
- "今天花了多少"、"查一下账单"
- "今日支出"、"今日收入"

操作步骤：
1. 执行：`python3 scripts/record_bill.py summary`

### 触发场景：用户要查历史

触发词：
- "上周花了多少"、"上月账单"
- "这个月消费"

操作步骤：
1. 执行：`python3 scripts/record_bill.py monthly --month <YYYY-MM>`
