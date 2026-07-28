# 06 — SKILL.md §🧪 FAT 协议 + 分级 Tested-By(钩子 6)

**What to build:** AI agent reading SKILL.md sees explicit FAT (Fresh Agent 黑盒测试) protocol section, knows the Tested-By 分级 rule (改代码 → pytest-pass,改 SKILL.md → fresh-agent), and commits are properly tagged with the right测试门槛。

**Blocked by:** None — can start immediately。

**Status:** ready-for-agent

**Source:** spec.md §User Stories 6, 7, 17, 18 · Q2=yes · 总纲钩子 6 + 原则 7。

**Acceptance criteria:**

- [ ] SKILL.md 新增 §🧪 FAT 协议 章节(插入位置:`## §📌 输出位置` 之后 / `## 场景资产` 之前)
- [ ] 章节明确定义分级 Tested-By:
  - **改代码 / 数据 / CLI**:`Tested-By: pytest-pass-YYYY-MM-DD`(124 pytest 全 PASS 即可 commit)
  - **改 SKILL.md**(触发词 / 路由表 / 说明 / frontmatter):`Tested-By: fresh-agent-v1`(必须 fresh agent 实际跑过)
  - **豁免**:`Tested-By: exempt` + 豁免依据(typo / 格式调整 / 注释)
- [ ] 章节列出 FAT 协议 9 步(从总纲 §05 工程仪式 复制):选 3-5 核心唤醒词 → fresh context → 最小化加载 → ≥ 3 人类 prompt → 证据 → 对比预期 → pass/fail → fail 改 SKILL.md → 人工审查
- [ ] **Risk C** 显式声明:"Tested-By 字段缺失 / 错误标签 / 与 commit 内容不符 = 总纲 8 反模式之 silent failure,需立即补全或 revert"
- [ ] 章节引用总纲钩子 6 + §05 工程仪式 FAT 协议
- [ ] pytest 全 124 PASS(无代码改动)

**Risk C:** Tested-By 流于形式 — 已在 §FAT 协议 章节引用总纲 8 反模式 silent failure 威慑

**Decision trace:**
- Q2 = yes: 接受分级(非 strict-only)
- 理由:拓宽定义后,需用分级子规则防止 SKILL.md 退化;silent failure 反模式引用让 AI 有 external 压力
- 测试门槛显式 = AI 写 commit message 时有据可依