# 测试数据隔离(SKILLS_DB_PATH_TEST)

Status: accepted

`daily_goal.weight_goal` 被某次 `weight-goal --help` 误写为字符串、7.27 有 4 条体重测试数据(id 132-135)混入生产库、Issue 3.4 反复出现 — 这些都是"测试数据污染生产"的同一根因的不同表现。

我们决定:**所有测试必须使用独立临时 DB,通过 `SKILLS_DB_PATH` 环境变量隔离;生产 `calorie_data.db` 永不被测试触碰**。

考虑过的选项:
- **加 `is_test` 列** — 每个数据表加 INTEGER 标志,所有查询默认 `WHERE is_test=0`。缺点:污染 schema;查询逻辑要处处加条件;仍有"忘了加 is_test=0"的漏网风险。
- **手动管理(用户写 SQL 清)** — 治标不治本,Issue 3.4 会反复出现。
- **当前方案(SKILLS_DB_PATH 隔离)** — `tests/conftest.py` 的 `temp_db` fixture 在 pytest 启动时 monkeypatch `SKILLS_DB_PATH` 到 `tmp_path_factory` 创建的临时目录,init schema;任何 `calorie_tracker.py` / `db.py` 调用 `find_db_path()` 都会拿到 temp 路径。生产 DB 永不被触碰。

后果:
- 多一个 fixture(15 行 + 拷贝 schema 逻辑)需维护,但消除了"测试数据漏到生产"这一类 bug。
- 现有 `tests/*.py` 不需要逐个改,只要走 `import scripts.db` 而不是 hardcode 路径,自动生效。
- Reversibility:删 conftest.py 即可回滚。

详见:`tests/conftest.py:1` + `tests/test_db_isolation.py:1`(seam 7 守门)。

---

# 扩展:L2 iso_db 强制隔离层(#400 重建 · 2026-08-16 · #386 Q6)

Status: accepted

## 背景

- 用户 shell 持久 `SKILLS_DB_PATH=D:\2Study\StudyNotes\.db`(生产)—— 未显式覆盖的 CLI / 子进程 / import 默认写生产。
- 原 `temp_db` 仅 session-scope + **显式请求**;不请求 `temp_db` 的测试/模块 import 会直接解析到生产路径。
- 模块级 `DB_PATH` 烘焙(如 `scripts/diet.py:22`)在 import 时固化,任何 monkeypatch 都晚于烘焙,失效。
- 08-09~14 事故:测试数据(996 行固定值)混入生产 `food_log`;08-11 事故:测试 `DELETE FROM exercise_log` 清空 8297 行真实数据。

## 决策

**L2 强制隔离层内联到 `tests/conftest.py`**(#400 重建后生效):

1. `pytest_configure`:pytest 启动**最早时机**强制 `setenv SKILLS_DB_PATH → mktemp`,覆盖用户 shell 持久生产 env。
   - 调试 opt-out:`SKILLS_KEEP_DB=1` 保留 caller 已设 env(仅打印警告,不硬断言)。
2. `iso_db_isolate`(session-scope **autouse** fixture):兜底二次 setenv + 验证 `find_db_path` 解析到 temp(非生产)。
3. `pytest_unconfigure`:清理 mktemp 目录。

## 为什么 pytest_configure + autouse 双重

- `pytest_configure` 保证任何 `scripts/*.py` 模块 import(模块级 `DB_PATH` 烘焙)发生在 setenv 之后。
- autouse 兜底第三方加载方式 / hook 注册差异(pytest 9.x 通过 `pytest_plugins=["iso_db"]` 加载外部插件时 hook 不可靠 → 内联最稳健)。

## 为什么不修 29 个烘焙文件(L1 verify 仅记录 · C1.5)

L2 autouse 在最早时机 setenv,**覆盖 find_db_path 式烘焙**(import 即读 temp,覆盖 26 个 find_db_path 式文件);改 29 文件 = 80 行 + 全 skill 回归 = 高工作量 + 新失败面。L1 verify 输出 `dbpath_baking_report.md` 记录不改代码。

**已知边界(对抗审查 A1)**:3 个文件(`body_composition.py` / `body_measurements.py` / `render_body_composition_wizard.py`)直接烘焙 `DB_PATH = SKILL_DIR / 'calorie_data.db'`(绕过 find_db_path/env),L2 setenv 对它们**无效**——测试侧靠各测试自行 `monkeypatch.setattr(mod, 'DB_PATH', temp)` 兜底(见 `test_modules_baked_after_plugin_get_temp_path` 的直烘焙断言)。ADR 此处措辞为「find_db_path 式烘焙全覆盖」而非「全烘焙覆盖」。

## 验收测试(tests/test_db_isolation.py · 15 个)

- 本地副本 + **真生产** `D:\2Study\StudyNotes\.db\calorie_data.db` 5 种 SQL(INSERT/UPDATE/DELETE/DROP/TRUNCATE)零触碰(写库前守卫:解析到生产则 FAIL 而非写)。
- `test_iso_db_plugin_loaded`:SKILLS_DB_PATH 已被 setenv 到 temp。
- `test_modules_baked_after_plugin_get_temp_path`:import scripts.diet 后 `diet.DB_PATH` 指向 temp(对抗式:烘焙被覆盖)。
- `test_cwd_sentry_*` × 5:cwd 哨兵模块单测(供 #404 L3 复用)。
- hardcode 扫:scripts/tests 无新增生产 DB 路径(已知 one-off 脚本豁免清单)。

## 范围

- L1 verify + L2 autouse + L4 pre-commit 注入 = 全仓共享;L3 cwd 哨兵 = 仅卡路里(#404)。
- 其他 skill 的 conftest 复制本层(或由 #402 L4 钩子注入兜底)。
