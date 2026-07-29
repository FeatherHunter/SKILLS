# CLI 标志化与类型校验

Status: accepted

Issue 6 根因:`calorie_tracker.py` 用 `int(sys.argv[2])` 这种手写参数解析,导致:
- `weight-goal --help` → `int('--help')` 崩溃 或 字面值 `'--help'` 被当 kg 写库(实测)
- `list-products --help` → `int('--help')` 崩溃
- `weight-history --days 1` → `int('--days')` 崩溃
- `weight-goal abc` → `int('abc')` 崩溃

我们决定:**`weight-goal` 改用 `--weight-goal <kg> --deadline <date>` 标志位,所有数值型 subcommand 参数显式校验类型(CLI 层用 try/except ValueError),每个 subcommand 支持 `--help` 立即返回 usage + exit 0**。

考虑过的选项:
- **整体重构到 argparse** — 全 CLI 切到 argparse 子解析器。缺点:calorie_tracker.py 有 ~20 个 subcommand + 复杂 positional/keyword 混合,改动巨大,回归风险高;而且 argparse 的 sub-command 模式与现有 `command + positional + kw_args` 解析风格不匹配。
- **当前方案(标志化 + try/except + 顶层 --help 短路)** — 改动小(calorie_tracker.py 3 处编辑),针对性修 root cause,保留老接口加 deprecation warning 当 escape hatch。
- **完全删除老 CLI 行为** — 不留 escape hatch,直接破坏向性。已有 shell alias / 脚本会立刻失效。

后果:
- 老接口 `weight-goal <kg> [deadline]` 临时保留 3 个月,带 stderr deprecation warning。
- `--text` 标志保留 pipeline 用户的 plain text 输出能力(为 ticket 07 查食品库准备)。
- Reversibility:删 try/except + flag 解析,回到原状态即可。

详见:`tests/test_cli_validation.py:1`(seam 5 守门) + `scripts/calorie_tracker.py:127`(main 入口) + `docs/adr/0006-test-db-isolation.md`(测试隔离基础设施)。