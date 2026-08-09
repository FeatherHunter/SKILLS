# 触发词权威源迁移与路由契约(frontmatter → _triggers.py)

Status: accepted

Issue #235 表面症状:用户说"卡路里HELP"时 AI 手写 HTML 绕过 `render_help_center.py`。对抗审查确认两层根因:
1. **路由层**:frontmatter description 9855 字符(opencode 规范上限 1024),「卡路里HELP」埋在 92.9% 位置 → 模型注意力盲区;且 description 触发词未经机械校验,含 16 个权威源无法定位的词。
2. **执行层**:SKILL.md 无 fail-fast 契约——渲染成败判据缺失,AI 失败时手写 HTML 兜底。

我们决定:
1. **权威源迁移**:触发词权威从 frontmatter description 迁至 `scripts/_triggers.py`(运行时 SoT,ADR-0001 已有 SoT 链)。check_trigger_consistency.py 对照基准同步迁移(HTML 模板表 ⊆ 权威源、render docstring ⊆ 权威源)。frontmatter 只做路由摘要(≤1024 字符 + HELP 置顶 + 触发词有效性校验——精确词或裸词别名双条件,裸词别名机制见 SKILL.md L447 实证)。
2. **路由契约**:description 526 字符、HELP 第 60 字符;68 个触发词全部对齐权威源。
3. **执行契约**:SKILL.md L16 新增渲染失败处理契约——判据 = 退出码 0 + 产物文件存在;失败输出错误回执,严禁手写 HTML 兜底。
4. **文档一致性**:§AI 触发场景详述 新增新旧词对照总表(新词优先路由,旧词过渡兼容,L636"过渡期可用"保留)。

考虑过的选项:
- **description 保留全量触发词**(9855 字符)——路由注意力盲区,否决(#235 根因)。
- **description 触发词 ⊆ 权威源精确匹配**——误杀合法裸词别名(「对比体重」=「对比体重：最近 30 天 vs 之前 30 天」,L447 明示),否决。
- **force_html frontmatter 字段**——opencode 忽略未知 frontmatter 字段(源码实证),无效,否决。
- **当前方案**——五处词表(description/HTML 表/docstring/速查表/_triggers.py)以 _triggers.py 为单点事实源,check 机械校验三边 + description 路由契约,速查表新旧对照引导。

后果:
- frontmatter description 只做路由摘要,不再承担词表权威——新增 trigger 须先入 _triggers.py。
- check 对照 3 新增 description 词有效性校验,红队测试确认能拦截假词(exit 1)。
- check 对照 4 覆盖全部入口脚本(不只 render_*),防回归盲区修复。
- 速查表 legacy 段保留旧词(过渡期可用),附新旧对照表导航。

详见:`scripts/check_trigger_consistency.py` + `SKILL.md §触发词速查表 / §AI 触发场景详述` + GitHub #235。
