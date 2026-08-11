# -*- coding: utf-8 -*-
"""技能互联 · check_public_contract.py 校验器单测（#273）

全部用 tmp registry + tmp 技能目录，不碰真 registry / 任何 DB
（数据库隔离红线：校验器不执行 fetch，测试自然零 DB 触碰）。
--what 端到端走真 skilllink.py，但只 import + 序列化注册表（不执行 fetch）。
"""
from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

LINK_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LINK_DIR))

import check_public_contract  # noqa: E402

VALID_DOMAINS_CODE = '''
PUBLIC_DOMAINS = {
    "sleep": {
        "name": "睡眠",
        "desc": "每日睡眠时长（分钟）",
        "fields": [
            {"name": "date", "type": "date", "unit": "", "desc": "日期"},
            {"name": "sleep_min", "type": "number", "unit": "分钟", "desc": "睡眠分钟"},
        ],
        "fetch": lambda start, end: [],
    },
}
'''


def _write_skill(root: Path, name: str, code: str) -> Path:
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "PUBLIC_DOMAINS.py").write_text(code, encoding="utf-8")
    return d


def _write_registry(root: Path, skills: dict) -> Path:
    """skills: {技能名: Path | str}（Path 写绝对路径，走 skilllink 绝对路径分支）"""
    if not skills:
        lines = ["skills: {}"]
    else:
        lines = ["skills:"]
        for name, path in skills.items():
            p = path if isinstance(path, str) else path.as_posix()
            lines.append(f"  {name}:\n    path: {p}\n    db_file: x.db")
    reg = root / "registry.yaml"
    reg.write_text("\n".join(lines), encoding="utf-8")
    return reg


def _run(argv: list[str]) -> tuple[int, str]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = check_public_contract.main(argv)
    return code, buf.getvalue()


def test_all_green(tmp_path):
    """registry 登记 + 合法注册表 + 反向无多余 → exit 0（含 --what 端到端）"""
    skill_dir = _write_skill(tmp_path, "假技能", VALID_DOMAINS_CODE)
    reg = _write_registry(tmp_path, {"假技能": skill_dir})
    code, out = _run(["--registry", str(reg), "--repo-root", str(tmp_path)])
    assert code == 0, out


def test_registered_without_file(tmp_path):
    """正向：登记了但缺 PUBLIC_DOMAINS.py → 红（登记 = 承诺，未兑现必须红）"""
    skill_dir = tmp_path / "空技能"
    skill_dir.mkdir()
    reg = _write_registry(tmp_path, {"空技能": skill_dir})
    code, out = _run(["--registry", str(reg), "--repo-root", str(tmp_path)])
    assert code == 1
    assert "缺 PUBLIC_DOMAINS.py" in out


def test_unregistered_file(tmp_path):
    """反向：有 PUBLIC_DOMAINS.py 但未登记 → 红（半接入悬空态）"""
    _write_skill(tmp_path, "未登记技能", VALID_DOMAINS_CODE)
    reg = _write_registry(tmp_path, {})
    code, out = _run(["--registry", str(reg), "--repo-root", str(tmp_path)])
    assert code == 1
    assert "未在 skill_registry.yaml 登记" in out


def test_missing_skill_dir(tmp_path):
    """正向：登记路径指向不存在的目录 → 红"""
    reg = _write_registry(tmp_path, {"幽灵技能": tmp_path / "不存在"})
    code, out = _run(["--registry", str(reg), "--repo-root", str(tmp_path)])
    assert code == 1
    assert "技能目录不存在" in out


def test_domains_not_dict(tmp_path):
    """结构：PUBLIC_DOMAINS 不是 dict → 红（skilllink.load_domains 报注册表无效）"""
    _write_skill(tmp_path, "假技能", "PUBLIC_DOMAINS = [1, 2, 3]\n")
    skill_dir = tmp_path / "假技能"
    reg = _write_registry(tmp_path, {"假技能": skill_dir})
    code, out = _run(["--registry", str(reg), "--repo-root", str(tmp_path)])
    assert code == 1
    assert "注册表加载失败" in out


def test_domain_missing_fetch(tmp_path):
    """结构：域缺可调用 fetch → 红"""
    code_src = '''
PUBLIC_DOMAINS = {
    "sleep": {"name": "睡眠", "desc": "d", "fields": [], "fetch": 42},
}
'''
    skill_dir = _write_skill(tmp_path, "假技能", code_src)
    reg = _write_registry(tmp_path, {"假技能": skill_dir})
    code, out = _run(["--registry", str(reg), "--repo-root", str(tmp_path)])
    assert code == 1
    assert "缺可调用 fetch" in out


def test_field_missing_type(tmp_path):
    """结构：字段缺 type → 红（契约 v1 §3 必填）"""
    code_src = '''
PUBLIC_DOMAINS = {
    "sleep": {
        "name": "睡眠", "desc": "d",
        "fields": [{"name": "date"}],
        "fetch": lambda start, end: [],
    },
}
'''
    skill_dir = _write_skill(tmp_path, "假技能", code_src)
    reg = _write_registry(tmp_path, {"假技能": skill_dir})
    code, out = _run(["--registry", str(reg), "--repo-root", str(tmp_path)])
    assert code == 1
    assert "缺 type" in out


def test_bad_type_enum(tmp_path):
    """结构：type 不在枚举（如中文「日期」）→ 红（#273 D4 机器标识）"""
    code_src = '''
PUBLIC_DOMAINS = {
    "sleep": {
        "name": "睡眠", "desc": "d",
        "fields": [{"name": "d", "type": "日期", "unit": "", "desc": "x"}],
        "fetch": lambda start, end: [],
    },
}
'''
    skill_dir = _write_skill(tmp_path, "假技能", code_src)
    reg = _write_registry(tmp_path, {"假技能": skill_dir})
    code, out = _run(["--registry", str(reg), "--repo-root", str(tmp_path)])
    assert code == 1
    assert "不在枚举" in out


def test_bad_fetch_signature(tmp_path):
    """结构：fetch 签名非 (start, end) → 红（inspect 静态验，不执行）"""
    code_src = '''
def fetch(start):
    return []

PUBLIC_DOMAINS = {
    "sleep": {"name": "睡眠", "desc": "d", "fields": [], "fetch": fetch},
}
'''
    skill_dir = _write_skill(tmp_path, "假技能", code_src)
    reg = _write_registry(tmp_path, {"假技能": skill_dir})
    code, out = _run(["--registry", str(reg), "--repo-root", str(tmp_path)])
    assert code == 1
    assert "签名须为 (start, end)" in out


def test_repo_root_dot_dirs_skipped(tmp_path):
    """反向扫描跳过 . 开头目录（.scratch/.git 等噪音不误报）"""
    dot = tmp_path / ".scratch"
    dot.mkdir()
    (dot / "PUBLIC_DOMAINS.py").write_text("x = 1\n", encoding="utf-8")
    skill_dir = _write_skill(tmp_path, "假技能", VALID_DOMAINS_CODE)
    reg = _write_registry(tmp_path, {"假技能": skill_dir})
    code, out = _run(["--registry", str(reg), "--repo-root", str(tmp_path)])
    assert code == 0, out
