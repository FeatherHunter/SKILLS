# 03 — pytest 配置 + 结构体检(CI 入口)

**Parent**: `00-memo-skill-v1.1.5-refactor-spec.md`

**What to build:**
自动化 CI / 开发者本地运行 pytest,获得一致的测试入口契约 + 7 个结构合规体检。具体讲:pytest 启动时自动读 `pytest.ini` 6 项配置,只扫 `tests/` 目录,匹配 `test_*.py` / `Test*` / `test_*` 命名约定,启用 `--strict-markers` 防 typo,支持 `slow` marker;同时新增 `tests/test_skill_structure.py` 文件,7 个断言守护结构合规(YAML frontmatter 存在 + _meta.json 与 SKILL.md 版本一致 + 5 个 ADR 存在 + README.md 存在 + pytest.ini 存在 + AGENTS.md 含项目定位关键词)。

**Blocked by:** None — 可立即开始

**Status:** ready-for-agent

## Acceptance criteria

- [ ] `备忘录/pytest.ini` 存在,含 `[pytest]` 段
- [ ] pytest.ini 6 项配置:`testpaths = tests` / `python_files = test_*.py` / `python_classes = Test*` / `python_functions = test_*` / `addopts = -ra -q --strict-markers` / `markers` 区(slow marker)
- [ ] `tests/test_skill_structure.py` 存在,~30 行,~6-8 个 test_ 函数
- [ ] test_skill_structure.py 含 7 个断言(frontmatter / _meta.json / 5 ADR / README / pytest.ini / AGENTS.md)
- [ ] `pytest tests/` 跑出 180+ 测试,全过
- [ ] `pytest --strict-markers` 不报"未注册 marker"警告
- [ ] 不加 `xfail_strict`(防 22 xfailed 连锁失败)

## Out of scope

- 现有 13 个 test_*.py 文件(0 改动)
- `xfail_strict`(本 spec 不引入)
- CI workflow 文件(本仓库无 GitHub Actions)
