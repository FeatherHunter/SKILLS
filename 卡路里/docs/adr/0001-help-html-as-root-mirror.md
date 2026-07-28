# 卡路里.html 是最新 HELP 渲染的重命名

Status: proposed

旧 `卡路里.html` 是 SKILL.md 的 101KB markdown 镜像;新版 `卡路里_HELP_<TS>.html` 是 `_triggers.py` + `templates/help_center.html` 的渲染。两者并存导致 SoT 漂移,用户在根目录打开的可能是过期镜像。

我们决定 `卡路里.html` 等于最新 `卡路里_HELP_<TS>.html` 的重命名,SKILL.md 镜像契约(2026-07-25-body-metrics-design.md L23)退役。`_triggers.py`(data)+ `templates/help_center.html`(presentation)是 SoT 链,根 HTML 镜像只是输出物。

考虑过的选项:保留两个独立的 `<skill>.html` 与 `<skill>_HELP_<TS>.html`(双 artifact,用户困惑);用 git submodule 同步 SKILL.md 镜像(反而引入额外机器成本)。重命名是 SoT 链最干净的形式。

后果:失去"AI 能反读 markdown 镜像 HTML"的便利——但 SKILL.md 本身仍是 markdown SoT,该能力可由 AI 直接读 .md 而非镜像 HTML。reversibility 高(git revert)。
