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
