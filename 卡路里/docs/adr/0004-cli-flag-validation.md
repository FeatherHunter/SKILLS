# CLI 标志化与类型校验

Status: accepted · **supersedes 3-month deprecation framework(v2.5.5 · 2026-07-29)**

**设计哲学**:卡路里**不接受 deprecation 期,所有破坏性变更立即生效**。`--legacy-positional` 之类的逃生口不写 — 老脚本必须随 schema 升级而升级。

Issue 6 根因:`calorie_tracker.py` 用 `int(sys.argv[2])` 这种手写参数解析,导致:
- `weight-goal --help` → `int('--help')` 崩溃 或 字面值 `'--help'` 被当 kg 写库(实测)
- `list-products --help` → `int('--help')` 崩溃
- `weight-history --days 1` → `int('--days')` 崩溃
- `weight-goal abc` → `int('abc')` 崩溃

我们决定:**`weight-goal` 改用 `--weight-goal <kg> --deadline <date>` 标志位,所有数值型 subcommand 参数显式校验类型(CLI 层用 try/except ValueError),每个 subcommand 支持 `--help` 立即返回 usage + exit 0**。

考虑过的选项:
- **整体重构到 argparse** — 全 CLI 切到 argparse 子解析器。缺点:calorie_tracker.py 有 ~20 个 subcommand + 复杂 positional/keyword 混合,改动巨大,回归风险高;而且 argparse 的 sub-command 模式与现有 `command + positional + kw_args` 解析风格不匹配。
- **当前方案(标志化 + try/except + 顶层 --help 短路)** — 改动小(calorie_tracker.py 3 处编辑),针对性修 root cause。
- **完全删除老 CLI 行为** — 不留 escape hatch,直接破坏向性。~~已有 shell alias / 脚本会立刻失效~~ → v2.5.5 后:这是**期望行为**,老脚本必须同步升级。

后果:
- 老接口 `weight-goal <kg> [deadline]` **立即失效**(v2.5.5 起,不留 deprecation 期)。命令文档/SKILL.md 同步移除老用法说明。
- `--text` 标志保留 pipeline 用户的 plain text 输出能力(为 ticket 07 查食品库准备)。**注**:`--text` 是新功能的 escape hatch,不是 deprecated flag — 保留。
- Reversibility:从 git 历史恢复 v2.5.5 前版本即可(此 ADR 之前的所有 commit 都保留)。

详见:`tests/test_cli_validation.py:1`(seam 5 守门) + `scripts/calorie_tracker.py:127`(main 入口) + `docs/adr/0006-test-db-isolation.md`(测试隔离基础设施)。

---

## 附录:CLI 演进史(供考古)

- **v2.5 之前** — `weight-goal <kg> [deadline]` positional,无 type 校验,`'--help'` 会被写库
- **v2.5** — 引入 `--weight-goal --deadline` flag + `--legacy-positional` 3 个月 deprecation 期(2026-10-29 删除)
- **v2.5.5 (本 ADR supersede)** — 删除 `--legacy-positional` + 3 月 deprecation 文字;确立"不存 deprecation 库存"哲学