"""v1.1.5 · 结构体检(white-box 静态存在性守护)

单一辅助 seam(spec 00 · Testing Decisions):
  只验"文件存在 + 关键字符串",不深入实现细节,~30 行。
  主 seam 仍是 CLI 子进程(test_help.py 等已大量使用)。

覆盖范围:
  1. SKILL.md YAML frontmatter 5 字段齐全
  2. _meta.json version == SKILL.md frontmatter version(SoT 一致性)
  3. docs/adr/0001-0005.md 5 个 ADR 存在
  4. README.md 存在(ticket 01 落地)
  5. pytest.ini 存在 + 6 项配置
  6. AGENTS.md 含项目定位关键词
"""
import json
import re
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
META_JSON = SKILL_DIR / "_meta.json"
AGENTS_MD = SKILL_DIR / "AGENTS.md"
README_MD = SKILL_DIR / "README.md"
PYTEST_INI = SKILL_DIR / "pytest.ini"
ADR_DIR = SKILL_DIR / "docs" / "adr"


def _parse_frontmatter():
    """简易 YAML frontmatter 解析(避免引入 pyyaml 依赖,frontmatter 5 字段都是标量)。"""
    text = SKILL_MD.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, "SKILL.md 缺 YAML frontmatter(--- ... ---)"
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm


class TestSkillStructure:
    """7 项结构合规体检(white-box · 静态存在性)。"""

    def test_skill_md_has_yaml_frontmatter_5_fields(self):
        fm = _parse_frontmatter()
        for key in ("name", "version", "status", "description", "last_updated"):
            assert key in fm, f"frontmatter 缺字段: {key}"
            assert fm[key], f"frontmatter 字段 {key} 为空"

    def test_meta_json_version_matches_skill_md_frontmatter(self):
        fm = _parse_frontmatter()
        meta = json.loads(META_JSON.read_text(encoding="utf-8"))
        assert meta["version"] == fm["version"], (
            f"_meta.json version={meta['version']!r} ≠ SKILL.md frontmatter version={fm['version']!r}"
        )

    def test_5_adr_files_exist(self):
        for n in range(1, 6):
            # 文件名前缀为 000N,后缀主题不限(glob 兜底)
            matches = list(ADR_DIR.glob(f"000{n}-*.md"))
            assert matches, f"docs/adr/000{n}-*.md 不存在"

    def test_readme_md_exists(self):
        assert README_MD.exists(), "README.md 不存在"

    def test_pytest_ini_exists_with_6_configs(self):
        assert PYTEST_INI.exists(), "pytest.ini 不存在"
        text = PYTEST_INI.read_text(encoding="utf-8")
        assert "[pytest]" in text, "pytest.ini 缺 [pytest] 段"
        for key in (
            "testpaths",
            "python_files",
            "python_classes",
            "python_functions",
            "addopts",
            "markers",
        ):
            assert key in text, f"pytest.ini 缺配置项: {key}"
        assert "--strict-markers" in text, "pytest.ini addopts 缺 --strict-markers"

    def test_agents_md_contains_positioning_keyword(self):
        text = AGENTS_MD.read_text(encoding="utf-8")
        # 项目定位段必须含核心关键词
        assert "跨设备随手记录" in text, "AGENTS.md 缺项目定位关键词"
        assert "29" in text and "唤醒词" in text, "AGENTS.md 缺唤醒词数量描述"

    def test_agents_md_references_adr_0003_commit_rule(self):
        text = AGENTS_MD.read_text(encoding="utf-8")
        assert "0003" in text, "AGENTS.md 未引用 ADR-0003 commit 全中文硬规则"
