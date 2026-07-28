# 备忘录 Skill · 整体重构 spec

> A.4 范式: .scratch/<feature>/spec.md
> 创建: 2026-07-28 · Grilling R3

## 目标

用 `SKILL开发总纲V1.0` 作为权威规范,把备忘录 skill 从"功能完整但结构松散"升级到"功能完整 + 结构合规 + 工程仪式齐全"。最终交付:一个能通过总纲 §02-§07 全部硬规则的 skill。

## 阶段划分(P1 路线 · 依赖关系升序)

```
B 内容一致性 ──► A 结构合规 ──► D 工程仪式 ──► C 架构合规
   (R1+R2)         (R3)          (R4)         (R5)
```

### B 内容一致性(已完成 R1+R2)

- 术语统一: 触发词 → 唤醒词, 用例 → 场景, 4 元组 vs 4 段 prompt 显式区分, HTML 镜像 + HELP HTML 双命名
- 内容清理: _meta.json 升 1.1.4, SKILL.md 删 L1034 重复章节, reference/ → references/ 合并, scenarios.yaml L21 块删除
- 历史数字: CHANGELOG L538 加注释,末尾建新基准 174/174
- 4 元组: 保持 2-3 元混合,不强制升级
- commit 全中文约束入库(ADR-0003)

### A 结构合规(R3 完成决策 · 待执行)

- YAML frontmatter 5 字段
- README.md 5 章节
- pytest.ini 6 项配置
- .scratch/ 5 文件范式
- AGENTS.md 升级到 25-30 行

### D 工程仪式(R4 待决策)

- FAT 协议执行策略
- Tested-By 字段位置
- 改动前 3 问形态
- 豁免矩阵存放位置

### C 架构合规(R5 待决策)

- 5 层自检清单全跑
- 触发词 4 元组化评估(已决定保持现状,本阶段跳过)
- injector 私有 vs 复用 _assets(已决策保持私有 v1.1.0 决策)
- 5 状态 fallback 4 状态化(已在 R2 B.9 决策)

## 不在范围内

- **跨 Skill 共享**(`_shared/` 抽取):v1.1.0 已固化为私有,不重提
- **历史 commit 回填 Tested-By**:历史不可改
- **CHANGELOG 历史数字修订**:伪造审计风险

## 验收标准

1. 总纲 §02 5 层自检清单 100% 通过
2. 总纲 §03 触发词设计 ≥ 8 已满足(29 + 1 HELP)
3. 总纲 §04 13 原则全部满足(原则 3 已改为 4 状态,需向总纲提 ADR)
4. 总纲 §05 工程仪式(FAT / Tested-By / 3 问)全补齐
5. 总纲 §06 附录 RULE Forms 不适用
6. 总纲 §07 HELP + 场景完备性 7 字段契约全满足
7. 总纲 ADR-0002 "无规模逃生口" 100% 合规

## 当前进度

| 阶段 | 决策 | 执行 | 入库 |
|---|---|---|---|
| B | ✅ 13/13 (R1+R2) | ⏳ 待执行 | ⏳ 4 commits (B.13) · 1 已入库 |
| A | ✅ 5/5 (R3) | ⏳ 待执行 | ⏳ 1 commit |
| D | ✅ 5/5 (R4) | ⏳ 待执行 | ⏳ 2 commits |
| C | ⏳ 大部分已在 R1-R2 完成 | — | 归入"Out of Scope" |

**已发布 issue**: `issues/01-memo-skill-v1.1.5-refactor-spec.md` (`ready-for-agent`)

## 工作目录

本目录(`.scratch/grilling-alignment/`) 是本次重构的工作目录,遵循 A.4 范式:

- `spec.md` — 本文件
- `decisions.md` — R1+R2+R3 决策摘要(轻量 ADR)
- `verify.ps1` — 验收脚本(R5 后写)
- `issues/` — 问题追踪(本轮未产生独立 issue)
- `artifacts/` — 历史 HTML 报告
  - `r1.html` — R1 决策(术语/范围 8 题)
  - `r2.html` — R2 决策(执行细节 5 题)
  - `r3.html` — R3 决策(结构文件 5 题)
