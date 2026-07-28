# 备忘录 Skill · 重构决策日志

> A.4 范式: .scratch/<feature>/decisions.md (轻量 ADR)
> 创建: 2026-07-28 · Grilling R3 后

## Round 1 · B 范围 + 术语(8 决策)

| # | 题 | 决策 | 落地文件 |
|---|---|---|---|
| B.1 | 子范围粒度 | 全部 6 项都做(含 CHANGELOG L538) | (执行待 B.13 commit 4) |
| B.2 | 版本号 SoT | SKILL.md 是 SoT, _meta.json 是镜像 | ADR-0001 |
| B.3 | 触发词 / 唤醒词 | 用"唤醒词" | CONTEXT.md |
| B.4 | 用例 / 场景 | 用"场景" | CONTEXT.md |
| B.5 | 4 元组 / 4 段 prompt | 显式区分(4 元 / 4 段) | CONTEXT.md |
| B.6 | HTML 镜像命名 | "HTML 镜像" + 别名 "HELP HTML" | CONTEXT.md |
| B.7 | SKILL.md L927+L1034 | 删 L1034, 保留 L927 | ADR-0002 |
| B.8 | reference/ vs references/ | 合并为 references/ | ADR-0002 |

## Round 2 · B 执行细节(5 决策)

| # | 题 | 决策 | 落地文件 |
|---|---|---|---|
| B.9 | 4 状态 fallback | success / empty / missing_data / error(5→4) | ADR-0003 |
| B.10 | scenarios.yaml L21+L23 重复 key | 删 L21 块 + EOF 补换行 | ADR-0003 |
| B.11 | CHANGELOG L538 "106/106" | 加注释 + 末尾建 174/174 基准 | ADR-0003 |
| B.12 | 唤醒词 4 元组化 | 保持 2-3 元混合(总纲允许) | ADR-0003 |
| B.13 | B 阶段 commit 分片 | 4 个 commit(全中文) | ADR-0003 + CONTEXT.md |

**Commit 格式硬规则(ADR-0003)**:

```
[<skill 中文名>] <主题> · <细节(可选)>
```

或 `<类型>: <skill 中文名> <主题> · <细节>`,类型词必须中文(`功能`/`修复`/`文档`/`杂务`/`测试`),emoji 可选。

❌ 禁用英文类型前缀(`fix:` `docs:` `feat:` `chore:`)和英文括号类型(`fix(...)` `docs(...)`)。

## Round 3 · A 结构文件(5 决策)

| # | 题 | 决策 | 落地文件 |
|---|---|---|---|
| A.1 | SKILL.md YAML frontmatter | 5 字段(name/version/status/description/last_updated) | ADR-0004 |
| A.2 | README.md 章节大纲 | 5 章节(这是什么/何时使用/快速开始/文件清单/状态) | ADR-0004 |
| A.3 | pytest.ini 配置 | 6 项(testpaths/python_files/classes/functions/addopts/strict-markers) | ADR-0004 |
| A.4 | .scratch/ 范式 | 5 文件(spec/verify/issues/decisions/artifacts) | ADR-0004 + 本目录结构 |
| A.5 | AGENTS.md 升级 | 13 行 → 25-30 行(项目定位/路径约定/决策位置/commit/HTML 镜像) | ADR-0004 |

## Round 4 · D 工程仪式(5 决策 · 用户隐含接受 · 未显式回答)

> 用户在 R3 后说"全部按照你推荐爱的来",R4 HTML 生成后未显式回答,直接说"如果 grill 结束了就开始 to-spec",按惯例视为隐含接受。

| # | 题 | 决策 | 落地文件 |
|---|---|---|---|
| D.1 | FAT 协议执行策略 | exempt(无 fresh agent) | ADR-0005 |
| D.2 | Tested-By 字段位置 | commit message 行末 + CHANGELOG 双写 | ADR-0005 |
| D.3 | 改动前 3 问形态 | SKILL.md 顶部加段(强制肉眼自检) | ADR-0005 + SKILL.md(待执行) |
| D.4 | 豁免矩阵存放 | 独立 ADR-0005 | ADR-0005 |
| D.5 | D 阶段 commit 分片 | 2 commit(决策入库 + 仪式落地) | ADR-0005 |

## 累计 ADR 文件清单

| ADR | 主题 | 阶段 | Grilling |
|---|---|---|---|
| 0001 | 版本号单一事实源为 SKILL.md | B | R1 |
| 0002 | SKILL.md 参考文档章节去重 + 双目录合并 | B | R1 |
| 0003 | B 阶段执行层决策 + commit 格式约束 | B | R2 |
| 0004 | A 阶段结构文件决策 | A | R3 |
| 0005 | D 阶段豁免矩阵 + 工程仪式 | D | R4(隐含接受) |

## 待决(后续轮次)

| 轮次 | 主题 | 预计题数 |
|---|---|---|
| R5 | C 架构合规(5 层自检 / injector / 跨 Skill) | 5(可能跳过 — R1-R2 已涵盖大部分) |
| to-spec | 整体重构 spec 输出 | — |

## 历史(不变量)

- 5 状态 fallback 改为 4 状态 — **不存在所谓离线的场景** (R1 明确)
- injector 私有化保留 — **不重提 _shared/ 共享** (v1.1.0 教训)
- CHANGELOG 历史数字保留 — **不伪造审计轨迹** (R2 B.11)
