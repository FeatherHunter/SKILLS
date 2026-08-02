## 项目定位

跨设备随手记录 · 结构化备忘 + 心愿 + 打卡 + 情绪追踪。
29 个业务唤醒词 + 1 个 HELP 唤醒词,通过 SQLite 持久化 + 飞书 task 双向联动。

## 路径约定

- 入口规范:`SKILL.md`(AI 决策用完整规范,1038 行)
- 元数据:`_meta.json`(版本号镜像,SoT 为 SKILL.md frontmatter)
- 脚本:`script/`(5 个 Python 模块:memo_cli / memo_render / injector / feishu_sync / reminder_scheduler)
- 场景资产:`references/scenarios.yaml`(HELP HTML 唯一事实源,29 场景 × 7 字段)
- 参考文档:`references/`(schema.md / examples.md / cron.md)
- HTML 模板:`templates/`(6 个:1 HELP + 1 结果型查询 + 1 同步报告 + 3 过程型向导)
- 测试:`tests/`(基线 pytest 入口 `pytest tests/`)
- 工作目录:`.scratch/<feature>/`(A.4 5 文件范式:spec/verify/issues/decisions/artifacts)

## 决策文件位置

- 永久 ADR → `docs/adr/0001-N.md`(序号持续追加,按 INDEX:ADR-0007 HELP 4 级重构等)
- 临时决策 → `.scratch/<feature>/decisions.md`(轻量 ADR,不进 docs/adr/)
- 术语表 → `CONTEXT.md`(唤醒词 / 场景 / 4 元 / 4 段 prompt / HTML 镜像 / 渲染产物 / 模板静态扫描 / 搜索意图 / 场景资产 / 【待开发】)

## commit 格式

全中文硬规则(详见 `docs/adr/0003-b-execution-fallback.md`):

```
[备忘录] <主题> · <细节(可选)>
Tested-By: exempt(无 fresh agent · 详见 ADR-0005)
```

❌ 禁用英文类型前缀(`fix:` `docs:` `feat:` `chore:`)和英文括号类型(`fix(...)` `docs(...)` 等)。
从 v1.1.5 起所有 commit 必须含 `Tested-By` 行末(详见 `docs/adr/0005-d-exemptions-and-rituals.md`)。

## HTML 镜像约定

- `备忘录.html` 是 SKILL.md 镜像(v1.1.4 起由 `memo_cli.py help` 自动生成,不再手写)
- 改 `references/scenarios.yaml` 或 `templates/memo_help.html` 后必须跑一次 `help` 命令刷新
- `.githooks/pre-commit` 会在测试运行后自动还原 `备忘录.html` 到 HEAD 版本(测试副产物不入 commit)
