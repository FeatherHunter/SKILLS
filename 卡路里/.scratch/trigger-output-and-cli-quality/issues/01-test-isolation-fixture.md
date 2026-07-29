# 01 — 测试隔离 fixture(conftest.py + SKILLS_DB_PATH_TEST) + ADR-0006

**What to build:**
When pytest runs, every test sees a temporary DB that auto-cleans up. The production `calorie_data.db` is **never** touched by tests — opening it in a test session is a hard error. This is the foundation for safe parallel development: any ticket below that adds tests can run repeatedly without polluting user data.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] `tests/conftest.py` exposes a `temp_db` session-scoped fixture that:
  - creates `<SKILLS_DB_PATH>/test_calorie_data_<pid>.db` (or under `tempfile.gettempdir()`)
  - copies schema from production DB via `sqlite3` (so tests see real table shapes)
  - registers a finalizer that deletes the temp DB
- [ ] `calorie_tracker.py` and other CLI scripts detect pytest via `sys.argv[0]` or `PYTEST_CURRENT_TEST` env and auto-switch to `SKILLS_DB_PATH_TEST` when present; otherwise use `SKILLS_DB_PATH`
- [ ] `tests/test_db_isolation.py` exists and contains 2 cases: (a) a passing test that creates a weight_log row and confirms it lives in temp DB not prod; (b) a test that asserts no test file references the literal string `D:\.db\calorie_data.db` or any hard-coded absolute path
- [ ] `docs/adr/0006-test-db-isolation.md` written per ADR-FORMAT with Status: accepted, recording the decision "tests use isolated DB; no is_test column"
- [ ] `SKILL.md` §安装与配置 documents the new `SKILLS_DB_PATH_TEST` env var