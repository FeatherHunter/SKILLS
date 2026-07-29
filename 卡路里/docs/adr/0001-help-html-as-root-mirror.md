# 卡路里.html 是最新 HELP 渲染的重命名

Status: proposed

旧 `卡路里.html` 是 SKILL.md 的 101KB markdown 镜像;新版 `卡路里_HELP_<TS>.html` 是 `_triggers.py` + `templates/help_center.html` 的渲染。两者并存导致 SoT 漂移,用户在根目录打开的可能是过期镜像。

我们决定 `卡路里.html` 等于最新 `卡路里_HELP_<TS>.html` 的重命名,SKILL.md 镜像契约(2026-07-25-body-metrics-design.md L23)退役。`_triggers.py`(data)+ `templates/help_center.html`(presentation)是 SoT 链,根 HTML 镜像只是输出物。

考虑过的选项:保留两个独立的 `<skill>.html` 与 `<skill>_HELP_<TS>.html`(双 artifact,用户困惑);用 git submodule 同步 SKILL.md 镜像(反而引入额外机器成本)。重命名是 SoT 链最干净的形式。

后果:失去"AI 能反读 markdown 镜像 HTML"的便利——但 SKILL.md 本身仍是 markdown SoT,该能力可由 AI 直接读 .md 而非镜像 HTML。reversibility 高(git revert)。

## Q2 决策落地(ticket 16 · 2026-07-29)

Q2 问题:重命名后的 `卡路里.html` 根镜像是否也包含 dashboard quick-actions 摘要(类似 iOS App Switcher)?

**决策:不包含。** 根镜像 = HELP 速查台单一职责。Dashboard quick-actions 是主页 `home_dashboard.html` 的职责,与 HELP 速查台是两个 surface。若根镜像同时含 HELP + dashboard,SoT 链会被混淆(用户不知打开根 `卡路里.html` 究竟是查唤醒词还是看仪表盘)。

影响:`render_help_center.py` 的 `build_data()` 只组装 TRIGGERS + CATEGORIES,不包含 quick_actions 数据。Q2 关闭。
