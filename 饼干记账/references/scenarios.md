# 饼干记账 · 场景资产（人类可读视图）

> **派生于 [`scenarios.json`](./scenarios.json)（唯一事实源）。**
> 修改请改 JSON；本文档可手工同步，或运行 `scripts/render_help.py --check` 校验一致性。

## 总览

- **唤醒词**：15 个（4 写入 + 6 查询 + 4 分析 + 1 统计）
- **场景总数**：57 个
- **待开发**：0 个（v2.3 全部可用）

> 注：HELP 唤醒词自身（`饼干记账 HELP` / `查帮助` / `能做什么`）不在场景清单内（§07 §2 反模式 #3）。

---

## 记支出（6 场景）

| scenario_id | 标题 | 核心 prompt |
|---|---|---|
| `expense_food_default` | 餐饮类支出（AI 推断分类） | 午饭花了 35 块 |
| `expense_transport` | 出行类支出 + 账户 | 打车 20 用支付宝付的 |
| `expense_default_category` | 未指定分类（AI 推断并告知） | 洗发水 80 |
| `expense_with_date` | 补记昨天支出 | 昨天买书 58 |
| `expense_with_ledger` | 指定账本记账 | 在旅行账本记一笔打车 50 |
| `expense_ambiguous_amount` | 金额不明确（AI 必须确认） | 午饭花了点钱 |

## 记收入（5 场景）

| scenario_id | 标题 | 核心 prompt |
|---|---|---|
| `income_salary` | 工资到账 | 工资 8000 到了 |
| `income_bonus` | 项目奖金 | 项目奖金 5000 |
| `income_sidejob` | 副业/兼职收入 | 副业赚了 2000 |
| `income_investment` | 基金分红 | 基金分红 300 |
| `income_redpacket` | 红包收入 | 收到红包 100 |

## 拍账单（4 场景）

| scenario_id | 标题 | 核心 prompt |
|---|---|---|
| `snap_clear_bill` | 清晰账单图片（自动识别） | [发一张外卖账单截图] |
| `snap_blurry_bill` | 模糊账单图片 | [发一张模糊的支付截图] |
| `snap_non_bill` | 非账单图片 | [发一张风景照片] |
| `snap_multi_amount` | 多金额账单（优先实付） | [发一张有优惠 + 合计 + 实付的账单] |

## 改记录（5 场景）

| scenario_id | 标题 | 核心 prompt |
|---|---|---|
| `update_amount` | 修改金额 | 把刚才那笔午饭改成 38 块 |
| `update_category` | 修改分类 | 把 ID=123 那条改成分类交通 |
| `update_note` | 修改备注（追加） | 改备注加一句牛奶 |
| `update_multi_fields` | 多字段一起改 | 把 ID=123 改成金额 -50 分类餐饮 账户微信 |
| `update_id_not_found` | ID 不存在 | 把 ID=99999 改成 50 |

## 查今天（3 场景 · 默认 HTML）

| scenario_id | 标题 | 核心 prompt |
|---|---|---|
| `query_today_normal` | 今日正常查询 | 今天花了多少 |
| `query_today_empty` | 今日无任何记录 | 今天花了多少（但今天还没记账） |
| `query_today_income_only` | 今日只有收入 | 今天收支情况（只有一笔红包） |

## 查日期（4 场景 · 默认 HTML）

| scenario_id | 标题 | 核心 prompt |
|---|---|---|
| `query_date_yesterday` | 查昨天 | 昨天花了多少 |
| `query_date_specific` | 查具体日期 | 5 月 1 号的账 |
| `query_date_relative` | 查相对日期（上周五） | 上周五花了多少 |
| `query_date_no_record` | 指定日期无记录 | 查 2025-01-01 那天的账 |

## 查范围（4 场景 · 默认 HTML）

| scenario_id | 标题 | 核心 prompt |
|---|---|---|
| `query_range_this_week` | 查本周 | 这周的账 |
| `query_range_last_week` | 查上周 | 上周消费情况 |
| `query_range_custom` | 查自定义区间 | 5 月 1 到 10 号的账 |
| `query_range_cross_month` | 跨月区间 | 4 月 25 到 5 月 5 号的账 |

## 查分类（4 场景 · 默认 HTML）

| scenario_id | 标题 | 核心 prompt |
|---|---|---|
| `query_category_food` | 查餐饮类记录 | 餐饮类的所有记录 |
| `query_category_transport` | 查交通类支出 | 交通花了多少 |
| `query_category_sublevel` | 查多级分类 | 看奶茶的所有记录 |
| `query_category_empty` | 该分类无记录 | 宠物类的记录 |

## 查最近（4 场景 · 默认 HTML）

| scenario_id | 标题 | 核心 prompt |
|---|---|---|
| `query_recent_5` | 最近 5 条 | 最近 5 条记录 |
| `query_recent_default` | 最近 10 条（默认） | 最近的记录 |
| `query_recent_20` | 最近 20 条 | 看一下最近 20 条 |
| `query_recent_empty` | 库为空 | 最近记录（全新用户） |

## 搜备注（3 场景 · 默认 HTML）

| scenario_id | 标题 | 核心 prompt |
|---|---|---|
| `search_keyword_multi` | 关键词命中多条 | 搜一下午饭 |
| `search_keyword_one` | 关键词命中 1 条 | 有没有生日蛋糕的记录 |
| `search_keyword_none` | 关键词无命中 | 搜外星人 |

## 看月度（3 场景 · 默认 HTML）

| scenario_id | 标题 | 核心 prompt |
|---|---|---|
| `monthly_current` | 本月汇总 | 这个月消费汇总 |
| `monthly_specific` | 指定月份汇总 | 3 月份的账 |
| `monthly_empty` | 指定月份无记录 | 看 2024 年 1 月的汇总 |

## 看对比（3 场景 · 默认 HTML）

| scenario_id | 标题 | 核心 prompt |
|---|---|---|
| `compare_week` | 周对比（本周 vs 上周） | 这周和上周比怎么样 |
| `compare_month` | 月对比（本月 vs 上月） | 本月和上月比 |
| `compare_no_last_period` | 上期数据缺失 | 新用户看月度对比（上月无记录） |

## 看分类（3 场景 · 默认 HTML）

| scenario_id | 标题 | 核心 prompt |
|---|---|---|
| `breakdown_current_month` | 本月分类明细 | 各类支出占比 |
| `breakdown_range` | 指定区间分类明细 | 5 月的分类明细 |
| `breakdown_single_category` | 仅 1 个分类（占比 100%） | 只看餐饮支出占比（只记过餐饮） |

## 看总览（3 场景 · 默认 HTML）

| scenario_id | 标题 | 核心 prompt |
|---|---|---|
| `overview_current` | 本月收支总览 | 本月收支情况 |
| `overview_specific` | 指定月份总览 | 3 月收支情况 |
| `overview_empty` | 指定月份无记录 | 看 2027 年 1 月的总览 |

## 做统计（3 场景 · 默认 HTML）

| scenario_id | 标题 | 核心 prompt |
|---|---|---|
| `stats_long_term` | 长期用户统计 | 我记账情况怎么样 |
| `stats_new_user` | 全新用户（0 笔） | 做统计（还没记过账） |
| `stats_just_started` | 刚开始记账 | 做统计（刚开始记账） |

---

## 渲染 & 验证

```bash
# 生成 HELP HTML(默认输出到 D:/Downloads/饼干记账_HELP_<timestamp>.html)
python3 scripts/render_help.py

# 仅校验场景资产 schema,不写文件
python3 scripts/render_help.py --check
```

## 自检（§07 §10）

- [x] 15 个唤醒词 × 62 个合法场景（穷举）
- [x] 每个场景 7 字段必填
- [x] prompt 不暴露 CLI / DB / 路径 / 错误码
- [x] status 二态正确（v2.3 全部 `""`，0 个待开发）
- [x] 5 者一一对应（唤醒词声明 ↔ 场景资产 ↔ prompt ↔ 底层工作流 ↔ HELP HTML）
- [x] HELP 自身不展示在 HELP HTML 中
- [x] 每场景独立复制按钮 + 复制成功反馈 + 剪贴板降级
- [x] 5 状态 fallback（正常 / 空 / 缺失 / 错误 / 离线）
- [x] 搜索 / 折叠（粘性搜索栏 + 输入即时过滤）