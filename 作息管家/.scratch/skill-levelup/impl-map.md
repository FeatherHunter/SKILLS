# 作息管家 L 级重构 · 实施 map（wayfinder · 第 2 阶段）

> 本地镜像 = 真相源（09 军规 8）。GitHub 正文与本文件同步维护。
> 来源：规格 map #190 全票闭环（R2/G1/R3/G2）+ 对抗式审查（第一性原理 × 2 轮，9 票最终版）。
> 创建：2026-08-09

## Destination

作息管家 L 级重构**实施交付**：开源清仓落地、记录/复盘/计划链路升级、81 场景全部可执行、onboarding 三段式上线。规格决策全部在实施中兑现，交付清单 + 考题对齐完成。

## Notes

- **流程**：09 L 级两阶段第 2 阶段；规格决策全部定案（规格 map #190，勿重开）
- **依赖拓扑**（第一性原理定）：阶段 1 串行 4 票（T0-T3，动共享文件）→ 阶段 2 并行 4 票（T4-T7，真新增自包含）→ 阶段 3 收尾 1 票（T8 合并）
- **架构原则**（对抗式审查修正）：记录/复盘 = 现有链路改造（归阶段 1）；渐进式注册通道（不动现有 49 命令分发）；复盘周/月/区间 = 一体模板（不双模板并存）；运行时隔离 = `SKILLS_DB_PATH` 指向临时目录（env 级）
- **人类参与点**（09 §11）：push / 数据层（动 DB 结构前确认）/ 规格口径 / 人工双浏览器审查 / 考题判定 / 最终交付
- **协议红线**：gh = `& "D:\0Tools\GitHubCLI\gh.exe"`；Git 只 `add`/`commit`；全中文 commit + `Tested-By:`；双门禁 A/B；偏离记录三问
- **提交纪律**：commit 前 `git status` 检查工作区（他人未提交改动 → 等/告知）；只 add 自己路径；禁 add -A / reset --hard / clean / 动历史
- 规格决策索引：`.scratch/skill-levelup/`（specs/、issues/、各轮决议）

## Decisions so far

<!-- 实施阶段开始，暂无 closed ticket；每关一张在此补一行 -->

- [T0 开源清仓+路径统一](https://github.com/FeatherHunter/SKILLS/issues/225) — 处置清单 #2-#16 全落地（#1 batch-add 归 T4）：Q6 路径统一链 get_db_base_dir 单一解析器 + 白名单迁出 .db/ + direct_add/batch_add_morning/plan*.json 删除 + LICENSE + .gitignore 修正 + 文档绝对路径 8 处；pytest 212 全过；门禁 A 5 层 PASS；4 commits 未 push
- [T1 注册通道+合并器](https://github.com/FeatherHunter/SKILLS/issues/226) — 渐进式注册通道（schedule_cli.py 末尾追加 discover_domain_commands/_dispatch_domain：域模块自带模块级 COMMANDS 注册表 → CLI 自动发现 dispatch；现有 49 if/elif 分发只加 else 钩子一行，未重构；sys.modules 零副作用：已导入模块跳过 + exec 后还原，杜绝测试污染）+ update_scenarios.py 场景合并器（读 scenarios/*.yaml 片段 → 7 字段契约校验 → scenario_id 命中覆盖/未命中追加 → 幂等写回 + 头部契约注释保留 + 场景总数行自动更新）+ fixture 隔离约定成文（操作规范 §7 + conftest）；pytest 230 全绿（212+18）；门禁 A 5 层 PASS；commit 2fcaaa0（混入并行 session 已 staged 总纲改名，零丢失，透明记录）
- [T4 批量导入](https://github.com/FeatherHunter/SKILLS/issues/229) — batch-add 命令模块 batch_scenarios.py 域模块自注册（COMMANDS{"batch-add"}，不碰 schedule_cli.py）；校验复用 add 链路（必填 field_map 语义 / 时间归一 24:00→23:59 / duration 省略自动算 / category 白名单下沉 add_record_full）；幂等不提供（记录无唯一键，文档注明）；git rm batch_add.py（R2 #1）；add_record_full 空串语义修正（source_timestamps/analysis_reasoning 空串合法，对齐 R2「缺省填空串」）；scenarios/batch.yaml 片段（#0-json 家族衔接，精确替换关系归 T8）+ 19 测试 + test_domain_channel 空注册表断言更新（并行 T5-T7 域模块已落地）；pytest 301 全绿（230+19+并行 52）+ E2E 冒烟（临时 SKILLS_DB_PATH：happy/dry-run/partial/stop-on-error/BOM 兼容）
- [T6 周视图](https://github.com/FeatherHunter/SKILLS/issues/231) — week_view.py 域模块自注册（COMMANDS{"render-record-week"}，不碰 schedule_cli.py / scenarios.yaml，schedule_html_render.py 零改动：命名/注入/复制 prompt 全部本地构建）；周视图 = 日历周一~周日 7×24 全分类总览（热力图格 = 该小时主导 L1 分类，cell 形态同 record_category）+ 每日时长 + L1 分类总览 + AI 钩子 + 4 段复制 prompt；前端复用+扩展热力图组件（_record_engine.js renderWeek，复用 .heatmap/hm-* 网格与 statBlock/recordsCollapsible/copyPromptBlock，对抗式审查矛盾 4）；输出 record/week/查作息周视图_<stamp>.html（中文命名合规）；10 测试；pytest 全绿（300 过 1 挂，挂=并行 T2 半成品 test_record_result 模板缺失，非本票）+ E2E 实测（真实进程 else 钩子 dispatch + 单文件 52KB HTML 写盘，临时 SKILLS_DB_PATH）
- [T7 首次使用+onboarding](https://github.com/FeatherHunter/SKILLS/issues/232) — 首次使用 6 步向导（环境检测→路径确认→建库→状态确认→初始化报告→完成）：setup_scenarios.py 域模块自注册 COMMANDS{check, render-first-use}（init/status 为既有内置命令，域注册表同名不可覆盖 → 编排由流程承担，偏离记录三问见 #232）；模块级零副作用（域注册通道 exec 安全，DB/飞书延迟 import）；check 输出 OS/Python≥3.7/数据目录可写/DB 状态/分类白名单/飞书三档 JSON；render-first-use 注入 $SKILLS_DB_PATH/schedule_html/setup/首次使用_<stamp>.html（锚点注入对齐 schedule_html_render 约定）；first_use_wizard.html 对标居家管家 6 步卡片式 + 08 双按钮（复制数据 5 段/复制日志 6 段）+ 阶段指示 chip + 移动端 820px 断点；报告契约 {items/todos/verify} 对标备忘录 init-report（飞书项三态 ok/skip/fail）；飞书强引导（2026-08-09 人类修正：配合飞书效果最好，明确拒绝才跳过并标注「飞书同步不可用」，授权强制非阻塞）；scenarios/setup.yaml 片段（first_use，7 字段契约过合并器校验，写回 T8）；14 测试；pytest 296 全绿 + 域通道 E2E（check/init/render-first-use 实测）+ 浏览器双视口 DOM 断言（1280x900 already / 390x844 need_init · 6步/5区/双按钮/无死页）+ node --check JS；commit 5bd98c0（⚠️ 卷入并行 T6 已 staged 4 文件：week_view.py/_record_engine.js/week_view.html/test_week_view.py，内容完整零丢失，仅提交归属错位，T6 知悉；按红线未回写）
- [T5 制定次日计划](https://github.com/FeatherHunter/SKILLS/issues/230) — plan_scenarios.py 域模块自注册 COMMANDS{"plan-result"}（不碰 schedule_cli.py / scenarios.yaml，schedule_html_render.py 零改动：直接 inject_into_template + _naming_path 本地构建）；plan-result <日期> --json @plan.json [--history-days N 默认7]：历史贴合提示（过去 N 天 schedule_records 按小时聚合分类计数降序 → 每段候选 match(贴合✅)/drift(偏离⚠️ 提示历史分类)/none(无参考➖) + 贴合率 match/(match+drift)）+ 冲突检测（候选 vs 已锁定 is_active=1，复用 preview 语义）+ 08 动作层（复制数据 5 段/复制日志 6 段）+ 4 部分 prompt；plan_result.html 新模板（24h 时间轴按分类着色 + 分类图例 + 历史作息带 24h 热力 + 贴合徽章/提示 + 冲突区 + 4 步多轮指引生成→调整→再生成 + 折叠区；5 状态 ok/conflict/候选空/无历史不降级/加载失败；静态 title + JS 同步 document.title）；scenarios/plan.yaml 片段（制定次日计划/调整再生成/无历史/冲突/偏离 5 场景，7 字段契约过合并器 dry-run，写回 T8）；23 测试；pytest 306 全绿（1 失败为并行 T6 week_view WIP 未跟踪文件，非本票）+ E2E 隔离库实测（8 段候选 + 历史工作/餐饮 → 贴合率 100% 3match + 冲突 2 处全对）+ Playwright 双视口 DOM 断言（desktop 1440 + mobile 390 无横向溢出，8 事件/match 3/drift 0/none 5）；⚠️ 偏离记录：shell 会话残留 SKILLS_DB_PATH=生产库路径致 seed 误写 21 条 records + 1 条 plan 进生产库 → 已精确清理恢复（records 回落 3278/plans 1081）+ 删除生产 schedule_html/plan/result 残留；commit 1049001

## Child tickets（本地附录 · GitHub 父子关系为准）

| # | 票名 | 类型 | 阶段 | 状态 | 阻塞 |
|---|---|---|---|---|---|
| #225 | [T0 开源清仓+路径统一](https://github.com/FeatherHunter/SKILLS/issues/225) | task | 1 串行 | ✅ closed 2026-08-09 | — |
| #226 | [T1 注册通道+合并器](https://github.com/FeatherHunter/SKILLS/issues/226) | task | 1 串行 | ✅ closed 2026-08-09 | —（已解锁） |
| #227 | [T2 记录链路升级](https://github.com/FeatherHunter/SKILLS/issues/227) | task | 1 串行 | open | ← T1（已解） |
| #228 | [T3 复盘链路升级](https://github.com/FeatherHunter/SKILLS/issues/228) | task | 1 串行 | open | ← T2（同文件串行） |
| #229 | [T4 批量导入](https://github.com/FeatherHunter/SKILLS/issues/229) | task | 2 并行 | ✅ closed 2026-08-09 | ← T1（已解） |
| #230 | [T5 制定次日计划](https://github.com/FeatherHunter/SKILLS/issues/230) | task | 2 并行 | ✅ closed 2026-08-09 | ← T1（已解） |
| #231 | [T6 周视图](https://github.com/FeatherHunter/SKILLS/issues/231) | task | 2 并行 | ✅ closed 2026-08-09 | ← T1（已解） |
| #232 | [T7 首次使用+onboarding](https://github.com/FeatherHunter/SKILLS/issues/232) | task | 2 并行 | ✅ closed 2026-08-09 | ← T1（已解） |
| #233 | [T8 场景资产+文档+镜像](https://github.com/FeatherHunter/SKILLS/issues/233) | task | 3 收尾 | open | ← 全部 |

Frontier（可认领）：#227 T2（阶段 1 串行下一票）。阶段 1 与阶段 2 并存：T2/T3 动共享文件须串行；T4-T7 已全 closed，仅剩 T8 收尾（阻塞中）。

## Not yet specified

- T2/T3 具体改造点的行级清单（认领票时展开）
- T8 场景替换关系的精确映射（记录→#0 系列 / 制定计划→#17 / 批量导入→#0-json）

## Out of scope

- git 历史清洗（Q10 + 对抗式审查矛盾 1，人类接受）
- macOS / CI（Q2 / Q12）
- 新增规格级决策（实施阶段禁止新增功能，只修规格内缺陷）
