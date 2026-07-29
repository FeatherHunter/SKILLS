Status: ready-for-agent

# 06 — ADR-0001 contract: SKILL.md 镜像契约退役

**What to build:** 旧 `卡路里.html = SKILL.md 镜像` 的文档契约退役,统一为 `<skill>.html = 最新 HELP render` 的 SoT。

依据:ADR-0001 contract 阶段。

**Blocked by:** 05

- [ ] `docs/superpowers/specs/2026-07-25-body-metrics-design.md` L23 "SKILL.md ↔ 卡路里.html 同 commit" 改写为 "`<skill>.html` 由 render_help_center 自动产出,无需手动 sync"
- [ ] `docs/agents/domain.md` 添加注释:`卡路里.html` 是 generated artifact,不是 SoT
- [ ] 任何 commit-time hook / PR template 提及 "镜像同步" 的 改 改 / 删除
- [ ] 检查现有 commit 历史中是否仍有 "doc: sync 卡路里.html with SKILL.md" 类 描述,确认无遗留引用
- [ ] README / CHANGELOG(若有) 删除 "SKILL.md 镜像" 提 法