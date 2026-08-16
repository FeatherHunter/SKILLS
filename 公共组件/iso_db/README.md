# iso_db · production DB isolation

跨技能测试隔离基础设施(#400 / #386 决策 C1.9 落地)。

## 实施状态(2026-08-14)

⚠️ **重要**: pytest 9.x 通过 `pytest_plugins = ["iso_db"]` 加载外部 plugin 时,
hook 注册不可靠(实测模块被加载但 `pytest_configure` 未被调用)。

**解决方案**: iso_db 隔离层**直接内联**到 卡路里/tests/conftest.py L17-145。
plugin.py 保留作为参考实现。

## 包含

- `plugin.py` · 参考实现(已弃用,pytest 9.x 不可用)
- `cwd_sentry.py` · cwd 哨兵(CLI/demo 路径自动隔离),由 #404 L3 复用

## 卡路里 conftest.py 启用方案(已生效)

```python
# 卡路里/tests/conftest.py L17-145
def pytest_configure(config):
    # 强制覆盖 SKILLS_DB_PATH → mktemp (opt-out: SKILLS_KEEP_DB=1)
    ...

@pytest.fixture(scope="session", autouse=True)
def iso_db_isolate(tmp_path_factory, request):
    # 兜底:再次 setenv + 拷 schema + 验证 find_db_path 解析到 temp
    ...
```

## 工作原理

```
pytest 启动
    ↓
pytest_configure hook (conftest.py 内联)
    ↓ setenv SKILLS_DB_PATH=temp (强制覆盖用户 shell 持久 env)
    ↓
任何 import 的 scripts/*.py 模块
    ↓ 模块级 DB_PATH = find_db_path(...) 自动读到 temp
    ↓
test 函数执行
    ↓
iso_db_isolate autouse fixture 二次 setenv 兜底
    ↓
pytest 退出
    ↓
pytest_unconfigure 清理 temp 目录
```

## 验收测试

`卡路里/tests/test_db_isolation.py` 15 个测试:
- `test_writes_dont_touch_prod_db` · INSERT 隔离(本地副本)
- `test_writes_dont_touch_real_prod_db_via_insert/update/delete/drop/truncate` · 真生产 DB 5 种 SQL 隔离
- `test_iso_db_plugin_loaded` · 验证 SKILLS_DB_PATH 已被 setenv 到 temp
- `test_modules_baked_after_plugin_get_temp_path` · adversarial: import scripts.diet 后 diet.DB_PATH 指向 temp
- `test_cwd_sentry_*` · cwd_sentry 模块单测(给 #404 验收)
- `test_no_scripts_file_hardcodes_prod_db_path` · 扫 scripts/*.py hardcode
- `test_no_test_file_hardcodes_prod_db_path` · 扫 tests/*.py hardcode

## opt-out(调试用)

设置 `SKILLS_KEEP_DB=1` 保留 caller 已设的 SKILLS_DB_PATH(不强制覆盖)。

## 引用

- #380: 卡路里 food_log bug
- #386: 11 项防复发决策
- #400: 本 ticket 的实施产物
- #402: pre-commit 注入 (依赖 #400)
- #404: L3 cwd 哨兵 (依赖 #400, 复用 cwd_sentry.py)
