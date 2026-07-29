# AGENTS.md — 卡路里

## Agent skills

### Issue tracker

Issues 以本地 markdown 文件形式存放在 `.scratch/<feature>/` 目录下。详见 `docs/agents/issue-tracker.md`。

### Triage labels

沿用 5 个默认 triage 标签(见 `docs/agents/triage-labels.md`)。

### Domain docs

单一上下文(single-context)布局。详见 `docs/agents/domain.md`。

### SoT 链(ADR-0001 · 2026-07-29)

- `卡路里.html`(根目录)= `render_help_center.py` 自动产出的最新 HELP render,**不是 SKILL.md 镜像**。
- SoT 链:`scripts/_triggers.py`(data)+ `templates/help_center.html`(presentation)→ `calorie_html/卡路里_HELP_<TS>.html`(artifact)→ `卡路里.html`(根 mirror)。
- 旧 101KB SKILL.md 镜像契约退役(详见 `docs/adr/0001-help-html-as-root-mirror.md`)。
