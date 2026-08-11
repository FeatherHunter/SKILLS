# -*- coding: utf-8 -*-
"""技能互联 · skilllink.py 命令真身单测（#274 试点）

覆盖契约 v1（docs/契约规范-v1.md）：
  §5 统一信封 / §6 失败降级（未接入 · 无此域+清单 · 执行出错）/ §7 --what 问能力
测试用 tmp 技能目录（mock fetch，不碰任何真 DB）——数据库隔离红线默认满足。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SKILL_LINK_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_LINK_DIR))

import skilllink  # noqa: E402


@pytest.fixture
def fake_skill(tmp_path):
    """构造一个带 PUBLIC_DOMAINS.py 的假技能目录；返回 (registry_yaml_path, skill_dir)"""
    skill_dir = tmp_path / "假技能"
    skill_dir.mkdir()
    (skill_dir / "PUBLIC_DOMAINS.py").write_text(
        """
def fetch_sleep(start, end):
    return [{"date": "2026-08-01", "sleep_min": 450},
            {"date": "2026-08-02", "sleep_min": 480}]

PUBLIC_DOMAINS = {
    "sleep": {
        "name": "睡眠",
        "desc": "每日睡眠时长（分钟）",
        "fields": [
            {"name": "date", "type": "date", "unit": "", "desc": "日期"},
            {"name": "sleep_min", "type": "number", "unit": "分钟", "desc": "睡眠分钟"},
        ],
        "fetch": fetch_sleep,
    },
}
""",
        encoding="utf-8",
    )
    registry = tmp_path / "registry.yaml"
    registry.write_text(
        f"skills:\n  假技能:\n    path: {skill_dir.as_posix()}\n    db_file: x.db\n",
        encoding="utf-8",
    )
    return registry, skill_dir


def _run(args: list[str]) -> tuple[dict, int]:
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        code = skilllink.main(args)
    return json.loads(buf.getvalue()), code


def test_what_returns_domains(fake_skill):
    """§7 --what：输出注册表（含中文名/说明/字段列表）"""
    registry, _ = fake_skill
    result, code = _run(["--skill", "假技能", "--registry", str(registry), "--what"])
    assert code == 0
    assert result["ok"] is True
    assert result["skill"] == "假技能"
    assert len(result["domains"]) == 1
    d = result["domains"][0]
    assert d["name"] == "sleep"
    assert d["cn"] == "睡眠"
    assert d["desc"]
    assert [f["name"] for f in d["fields"]] == ["date", "sleep_min"]


def test_read_returns_unified_envelope(fake_skill):
    """§5 统一信封：ok/skill/domain/meta/data"""
    registry, _ = fake_skill
    result, code = _run([
        "--skill", "假技能", "--registry", str(registry),
        "--domain", "sleep", "--from", "2026-08-01", "--to", "2026-08-10",
    ])
    assert code == 0
    assert result["ok"] is True
    assert result["skill"] == "假技能"
    assert result["domain"] == "sleep"
    assert result["meta"]["start"] == "2026-08-01"
    assert result["meta"]["end"] == "2026-08-10"
    assert result["meta"]["generated_at"]
    assert result["data"] == [
        {"date": "2026-08-01", "sleep_min": 450},
        {"date": "2026-08-02", "sleep_min": 480},
    ]


def test_unknown_domain_returns_domains_list(fake_skill):
    """§6 无此域：error + 现有域清单（AI 自救）"""
    registry, _ = fake_skill
    result, code = _run([
        "--skill", "假技能", "--registry", str(registry),
        "--domain", "nope", "--from", "2026-08-01", "--to", "2026-08-10",
    ])
    assert code == 1
    assert result["ok"] is False
    assert "没有这个域" in result["error"]
    assert result["domains"] == ["sleep"]


def test_skill_not_registered():
    """§6 未接入：注册表无此技能 → error + 现有技能清单"""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        registry = Path(td) / "registry.yaml"
        registry.write_text("skills:\n  作息管家:\n    path: x\n    db_file: y.db\n",
                            encoding="utf-8")
        result, code = _run(["--skill", "不存在的技能", "--registry", str(registry), "--what"])
        assert code == 1
        assert result["ok"] is False
        assert "未接入" in result["error"]
        assert result["skills"] == ["作息管家"]


def test_missing_public_domains(tmp_path):
    """§6 未接入：技能目录没有 PUBLIC_DOMAINS.py"""
    skill_dir = tmp_path / "空技能"
    skill_dir.mkdir()
    registry = tmp_path / "registry.yaml"
    registry.write_text(
        f"skills:\n  空技能:\n    path: {skill_dir.as_posix()}\n    db_file: x.db\n",
        encoding="utf-8",
    )
    result, code = _run(["--skill", "空技能", "--registry", str(registry), "--what"])
    assert code == 1
    assert result["ok"] is False
    assert "未接入" in result["error"]


def test_fetch_raises_returns_error(fake_skill):
    """§6 命令执行出错：fetch 抛异常 → error=具体原因"""
    skill_dir = fake_skill[1]
    (skill_dir / "PUBLIC_DOMAINS.py").write_text(
        """
def fetch_sleep(start, end):
    raise RuntimeError("DB 打不开")

PUBLIC_DOMAINS = {
    "sleep": {"name": "睡眠", "desc": "d", "fields": [], "fetch": fetch_sleep},
}
""",
        encoding="utf-8",
    )
    registry, _ = fake_skill
    result, code = _run([
        "--skill", "假技能", "--registry", str(registry),
        "--domain", "sleep", "--from", "2026-08-01", "--to", "2026-08-10",
    ])
    assert code == 1
    assert result["ok"] is False
    assert "命令执行出错" in result["error"]
    assert "RuntimeError" in result["error"]


def test_missing_from_to(fake_skill):
    """查数据缺 --from/--to → 参数错误"""
    registry, _ = fake_skill
    result, code = _run(["--skill", "假技能", "--registry", str(registry), "--domain", "sleep"])
    assert code == 1
    assert result["ok"] is False
    assert "--from" in result["error"]
