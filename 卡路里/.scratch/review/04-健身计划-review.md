# 健身计划验收记录 · 2026-08-10/11

> 对应 #42（健身计划 31 场景验收）+ #252/#255/#256（查看类缺口闭环）
> 验收流程：逐场景 + 5 维对抗式审查 + 同类批量 + 每场景附 HELP prompt

## 一、查看类缺口闭环（#252/#255/#256，2026-08-11）

| Issue | 功能 | 状态 | commit | 关键点 |
|-------|------|------|--------|--------|
| #252 | 看完整计划 | ✅ close(08-10) | c00e6b2 + a4f914f | full 模式默认激活本周；5 处同步；重量列适配(—/自重) |
| #255 | 看某天练什么 | ✅ close(08-11) | f9b9266 + cb62f3e | day 模式(--date)；4 形态验证；verifier 审查修复 6 项；测试补齐 |
| #256 | 看某动作安排 | ✅ close(08-11) | cf1ba6a | action 模式(--name)；子串双匹配；频率/总组数/重量区间汇总；下次练习日；每周相同折叠 |

### #255 审查教训（verifier 独立审查发现）
- SKILL.md 执行面映射错误（day 被映射成 week）→ 已修
- day 模式零测试覆盖 → 补 test_day_mode_specific 4 态
- 非法日期裸崩 → --date 预解析 + 友好错误
- srcLine 复制粘贴错误（weight_log→workout_plans）→ 已修
- 5 处同步 ≠ 全部同步：SKILL.md frontmatter/速查表/执行面/模板行需逐处核对

## 二、#42 健身计划 31 场景验收（进行中）

场景结构（31 = 29 原 + 看完整计划 + 看某天练什么 + 看某动作安排）：

| 子功能 | 场景数 | 状态 |
|--------|--------|------|
| 看训练计划 | 10（含 #252/#255/#256） | 1-7 已交付待用户确认；#252/#255/#256 已验收 |
| 定训练计划 | 5 | 待渲染 |
| 改训练计划 | 5 | 待渲染 |
| 落地训练 | 5 | 待渲染 |
| 计划复盘 | 6 | 待渲染 |
| 安全检查 | 1 | 待渲染 |

验收 seed：8 周推拉腿计划（2026-07-20 起，周一 3 时段模拟：晨间有氧/推日/核心）+ 120 条动作实绩（完成率梯度 90/70/50/30%）。

## 三、#257 训练容量/负荷趋势（复盘增强 · 2026-08-11）

| 项 | 状态 | commit |
|----|------|--------|
| 数据层：周容量 Σ(kg×次数) 计划/实做 + 主项 TOP4 周序列 + 无实绩提示态 | ✅ | 待 commit |
| 视图层：周容量双柱 SVG + 主项负荷多线 SVG（Catmull-Rom + 标签碰撞避让）| ✅ | 待 commit |
| 顺路修复：模板注入解包 bug（原渲染实际是坏的）+ 热力图 1fr 撑破(390px 溢出 1170px) + 明细表无横向滚动 + NaN | ✅ | 待 commit |
| 复制按钮契约：复制 prompt/复制数据 双 tab（与 HELP 零差异）+ Toast「知道了」面板 | ✅ | 待 commit |
| 测试：test_exercise_review_volume.py 6 项 + 隔离守卫 test_isolated_when_solo.py | ✅ | 待 commit |
| 5 维审查：①复制契约 ②数据契约 ③375px(390/320 0 溢出) ④Apple 风 ⑤增强建议(待用户拍板) | ✅ 交付 | 报告入库 |

### #257 验收结论（2026-08-11 用户逐页确认通过 → close）

- **用户验收**：3 场景（本周/本月/全部）逐页确认 OK；复制区按反馈重构两轮：
  - v4：复制 prompt 标签 → 「复制数据」「复制日志」双主按钮（功能语义）+ 扩展按钮（当前场景外其余复盘场景入口，点击复制对应 prompt + 激活态高亮）
  - v5：隐藏黑色预览框（按钮直接复制 + Toast 反馈），页面更清爽
- **关键 commit**：7873ff1（隔离根治）/ f0c30e2（容量功能）/ b2bfa31（审计归档）/ 6e603fc（最终确认）/ a11d494（复制区重构）
- **测试**：全量 374 passed + 20 xfailed；专属 7 项（容量聚合 6 + 隔离守卫 1）
- **体验增强建议 3 条**（用户未拍板，未实现，记录备查）：①容量环比一句话结论（推荐）②Y 轴计划水平线 ③折线图例 ↑↓ 箭头

### #257 重大事故记录（2026-08-11 生产库数据被清空 → 已恢复）

**事故**：新测试文件单独跑时，conftest 的 temp_db（session 级非 autouse）未被激活，SKILLS_DB_PATH 用户环境变量 = 生产库目录 `D:\2Study\StudyNotes\.db` → 测试 DELETE 直接清空生产库：
- exercise_log 8297 行（2021-03-10 ~ 2026-07-31 真实运动记录）
- workout_plans 100 行 + workout_plan_config 1 行（4周训练计划 v14）

**恢复**（12:07）：从 `calorie_data.db.bak_del_20260810_194205`（8/10 18:40 备份）定向恢复三表，未整库覆盖（food_log 生产 704 vs 备份 1065 证明备份后有变动）；sqlite_sequence 修复；现场快照 `calorie_data_accident_20260811_120727.db` 保留。

**根因**（比表面更深一层）：
1. temp_db 非 autouse → 单独跑新测试文件时隔离不激活（直接事故）
2. `analysis/_utils.py` + `plan_generator.py` 的模块级 `DB_PATH` 在 pytest collection 阶段固化生产路径（早于 conftest setenv）→ 即使隔离激活，分析函数仍读写生产库（全量跑 actual 全 0 的真相）

**根治**：
- 两处 `_get_db()` 改动态解析 find_db_path（与 render_workout_plan #6 模式一致）
- 新测试显式依赖 temp_db + monkeypatch 模块 DB_PATH
- test_workout_plan_modes.py seed_plan 补 temp_db 依赖（同类雷）
- 全量 376 passed 验证

## 四、后续

- #258 周期剩余进度（概览增强 · 第 X/Y 周 + 剩余训练日）
- #42 剩余 24 场景批量渲染验收（定/改/落地/复盘/安全）
- 遗留：#255 超周期循环语义（如需「超出周期」提示挂 #258 同源）；#256 动作别名表/单字噪音（观察真实使用）
- 备份 cron 8/11 起持续失败（WinError 206 文件名过长）→ 建议另派 agent 处理

### #258 周期剩余进度 闭环（2026-08-11 验收通过）

**需求**：计划概览增强周期剩余进度——第 X/Y 周 + 剩余周数/训练日 + 结束态提示（功能域第一性原理审查缺口，不新增唤醒词）。

**实现**：
- `render_workout_plan.py`：build_overview_data 增 current_week/remaining_weeks/remaining_training_days/period_status/period_start/period_end；新增 `_period_progress`（三态 active/unstarted/finished，线性真实周次不取模）
- **剩余训练日口径 = B（用户拍板 · 精确到天）**：从明天起逐日数到周期结束，循环周次映射查训练日集合——改过某周结构也能数对，比「完整周×每周天数」更精确
- `workout_plan_view.html`：renderOverview 顶部周期进度条（第 X/Y 周 + 完成百分比，固定蓝色=时间维度）+ KPI 追加剩余周数/剩余训练日（7 卡）+ 三态文案（finished 琥珀警示「周期结束≠完成率达标」，修正绿色误读）；复制数据按钮同步周期进度行；375px `nth-child(odd):last-child` 通用通栏规则
- 测试 `tests/test_overview_period.py` 7 项（active 第2周/末周/周中 + unstarted + finished + HTML 结构 + 结束态文案），显式依赖 temp_db；渲染级断言不锁状态值（避免时间炸弹）

**对抗式审查修复 3 项**：①时间炸弹测试（周期结束日期后必挂 → 改结构断言）②SKILL.md 619 行速查表同步 ③CSS nth-child(7) 写死 → 通用规则

**循环语义验证**：概览线性周次（生命周期）vs calc_plan_week 取模（内容循环）分层成立——重定计划 DELETE+INSERT 覆盖 config（plan_generator.py:192），start_date 单一事实源自动复位。

**验收**：场景 HTML 三态实测（375/390/414 0 溢出 0 JS 错误）+ 5 维审查 + 对抗式审查报告入库；测试全量 381 passed + 20 xfailed。
