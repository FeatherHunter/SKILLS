# 0005 D 阶段豁免矩阵与工程仪式

D 阶段 5 决策的捕获文件。同时记录 FAT 豁免矩阵 + Tested-By 字段约定 + 改动前 3 问。

## Status
accepted · 2026-07-28 · Grilling R4 / D.1 + D.2 + D.3 + D.4 + D.5

## D.1 · FAT 协议执行策略

不做 FAT,所有 commit 标 `Tested-By: exempt`(本仓库无 fresh agent)。

**理由**:
- 本仓库为单仓库,无独立 fresh agent 配置,FAT 无法自动跑
- 174 pytest 中 `test_help.py` 已用 subprocess 调真 CLI,等同于 FAT 的部分效果(49 个测试函数守护"prompt → 行为"链路)
- `Tested-By: exempt` 是总纲 §05 L100 合规选项,需依据,本 ADR 即依据

**未来迁移路径**: 若用户接入 fresh agent,本 ADR 追加 "激活 FAT" 子节,所有后续 commit 改标 `Tested-By: fresh-agent-v1`。

## D.2 · Tested-By 字段位置

双写:commit message 行末 + CHANGELOG.md 版本段末尾。

**commit 格式**(从 v1.1.5 起强制):
```
[备忘录] v1.1.5 · <主题> · <细节>
Tested-By: exempt(无 fresh agent · 详见 ADR-0005)
```

**CHANGELOG 格式**:
```markdown
## [v1.1.5] · 2026-07-28

**Tested-By**: exempt(无 fresh agent · 详见 ADR-0005)
```

**理由**:
- commit message 给 git 工具读(grep / blame)
- CHANGELOG 给人读(快速浏览某版本是否经过端到端测试)
- 不选 git notes:不污染 log 是优点,但 `git log` 默认不显示,失去审计意义

## D.3 · 改动前 3 问形态

SKILL.md 顶部加 3 问段(强制肉眼自检,非强制书面回答)。

**SKILL.md 加段位置**: frontmatter 之后,`## 强制性规定` 之前。

**段内容**(待执行):
```markdown
## 改动前 3 问(总纲 §05 L5-11 · 强制肉眼自检)

每次改动前必答(可不写下来,但要在脑子里过):

1. **影响哪些文件?** — 列出本次改动涉及的所有文件路径
2. **数据迁移?** — 是否需要 schema 变更 / 数据迁移 / 兼容老版本?
3. **回滚方案?** — 如果改动有 bug,如何 revert? 是否会丢数据?

豁免: 仅文档/注释/comment 改动可豁免(如本段本身的修订)
```

**理由**:
- SKILL.md 是 Agent 字面执行的依据(总纲 L13)
- "强制肉眼自检"而非"强制回答":总纲 L5-11 字面是"必答",但答在哪没规定;写下来太重,不写下来又怕忘
- 豁免规则(仅 doc/comment)避免每次小注释改动都要 3 问

## D.4 · 豁免矩阵

| 变更类型 | 是否豁免 FAT | 依据 |
|---|---|---|
| SKILL.md 任何字符改动 | ❌ 不豁免 | 总纲 §05 L100 |
| 纯 doc/comment 改动 | ✅ 豁免 | 本 ADR |
| 纯测试改动 | ✅ 豁免 | 174 pytest 守护 |
| script 改动 | ❌ 不豁免(需回归 174) | 本 ADR |
| templates 改动 | ❌ 不豁免(需 4 状态 fallback 守护) | B.9 决策 |
| docs/adr/ 改动 | ✅ 豁免(决策文件,不涉及运行时) | 本 ADR |

## D.5 · D 阶段 commit 分片策略

2 个 commit:

1. **`[备忘录] v1.1.5 · D-0 仪式决策入库(ADR-0005 · FAT exempt + Tested-By + 3 问 + 豁免矩阵)`**
   — 仅决策文件入库(本 ADR)

2. **`[备忘录] v1.1.5 · D-1 仪式落地(SKILL.md 顶部 3 问段 + CHANGELOG Tested-By 行 + commit Tested-By 行末格式启用)`**
   — 文档实际改动

**理由**: 决策与落地分开:先固化"规则是什么",再改"按规则改文件"。commit 2 是个分水岭:从此以后 commit 都要带 Tested-By(规则自生效)。

## 与其他 ADR 的关系

- **ADR-0003** commit 全中文硬规则 → Tested-By 行末格式补充(本 ADR D.2)
- **ADR-0004** A.4 .scratch 5 文件范式 → 本 ADR 落地于 `.scratch/grilling-alignment/`
- **B.13** commit 分片 → D.5 与之同模式(决策 + 落地两阶段)
