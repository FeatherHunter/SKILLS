## Agent 技能

### Issue 跟踪

Issue 以本地 markdown 文件形式存放在 `.scratch/<功能名>/` 下。详见 `docs/agents/issue-tracker.md`。

### Triage 标签

沿用五个标准标签:`needs-triage`、`needs-info`、`ready-for-agent`、`ready-for-human`、`wontfix`。详见 `docs/agents/triage-labels.md`。

### 领域文档

单一上下文:仓库根目录一份 `CONTEXT.md` + `docs/adr/`。详见 `docs/agents/domain.md`。

### AI 工具能力

AI 在本项目可调用以下本地工具。**写测试、排错、查资料、验证 HTML 时主动用**。

| 工具 | 路径 / 命令 | 何时用 |
|---|---|---|
| **playwright** | `D:\0Tools\Python313\Scripts\playwright.exe` (1.58.0) | HTML 自动化测试、`playwright codegen` 录制浏览器操作生成脚本 |
| **mmx search** | `mmx search query --q "..."` | 查最新文档 / API / 行为 / 最新 commit;数据来自网络 |
| **mmx vision** | `mmx vision describe --image ...` | 截图识别 / OCR / 画面理解 |
| **mmx text/image/video/speech/music** | `mmx <resource> ...` | 内容生成;**已有约定**:`references/文字成片-mmx免key生成6秒片段.md` |

mmx 已 auth(region=cn, base=`api.minimaxi.com`),API key 已配,无需重新登录。
