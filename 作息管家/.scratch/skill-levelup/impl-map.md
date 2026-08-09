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

## Child tickets（本地附录 · GitHub 父子关系为准）

| # | 票名 | 类型 | 阶段 | 状态 | 阻塞 |
|---|---|---|---|---|---|
| #225 | [T0 开源清仓+路径统一](https://github.com/FeatherHunter/SKILLS/issues/225) | task | 1 串行 | open | — |
| #226 | [T1 注册通道+合并器](https://github.com/FeatherHunter/SKILLS/issues/226) | task | 1 串行 | open | ← T0 |
| #227 | [T2 记录链路升级](https://github.com/FeatherHunter/SKILLS/issues/227) | task | 1 串行 | open | ← T1 |
| #228 | [T3 复盘链路升级](https://github.com/FeatherHunter/SKILLS/issues/228) | task | 1 串行 | open | ← T2（同文件串行） |
| #229 | [T4 批量导入](https://github.com/FeatherHunter/SKILLS/issues/229) | task | 2 并行 | open | ← T1 |
| #230 | [T5 制定次日计划](https://github.com/FeatherHunter/SKILLS/issues/230) | task | 2 并行 | open | ← T1 |
| #231 | [T6 周视图](https://github.com/FeatherHunter/SKILLS/issues/231) | task | 2 并行 | open | ← T1 |
| #232 | [T7 首次使用+onboarding](https://github.com/FeatherHunter/SKILLS/issues/232) | task | 2 并行 | open | ← T1 |
| #233 | [T8 场景资产+文档+镜像](https://github.com/FeatherHunter/SKILLS/issues/233) | task | 3 收尾 | open | ← 全部 |

Frontier（可认领）：#225 T0（唯一无阻塞，先决）。

## Not yet specified

- T2/T3 具体改造点的行级清单（认领票时展开）
- T8 场景替换关系的精确映射（记录→#0 系列 / 制定计划→#17 / 批量导入→#0-json）

## Out of scope

- git 历史清洗（Q10 + 对抗式审查矛盾 1，人类接受）
- macOS / CI（Q2 / Q12）
- 新增规格级决策（实施阶段禁止新增功能，只修规格内缺陷）
