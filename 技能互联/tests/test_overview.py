# -*- coding: utf-8 -*-
"""技能互联 · overview_render.py 互联总览单测（#276）

覆盖:
  状态判定（与 check_public_contract 同口径）: 未登记 → 灰 / 登记+契约有效 → 绿 /
    登记但缺注册表 → 红
  注入管线: 占位符硬拦截全部解析（INJECT-DATA / SHARED-HELPERS / SHARED-CSS）
  输出路径: SKILLS_DB_PATH 环境变量生效（测试天然隔离，不落生产目录）
全部用 tmp registry + tmp 技能目录 + tmp 输出；--what 不执行 fetch，
不碰任何 DB（数据库隔离红线 · AGENTS.md）。末尾冒烟测试用真 registry 但输出仍隔离到 tmp。
"""
from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

LINK_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LINK_DIR))

import overview_render  # noqa: E402

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


def _write_skill(root: Path, name: str, code: str | None) -> Path:
    """建技能目录；code 非 None 时写入 PUBLIC_DOMAINS.py（None = 只建目录）"""
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    if code is not None:
        (d / "PUBLIC_DOMAINS.py").write_text(code, encoding="utf-8")
    return d


def _write_registry(root: Path, skills: dict) -> Path:
    """skills: {技能名: Path | None}（Path = 指向技能目录；None = 登记但目录空）"""
    if not skills:
        lines = ["skills: {}"]
    else:
        lines = ["skills:"]
        for name, path in skills.items():
            if path is None:
                lines.append(f"  {name}:\n    path: {root.as_posix()}/幽灵目录\n    db_file: x.db")
            else:
                lines.append(f"  {name}:\n    path: {path.as_posix()}\n    db_file: x.db")
    reg = root / "registry.yaml"
    reg.write_text("\n".join(lines), encoding="utf-8")
    return reg


def _run(argv: list[str]) -> tuple[int, str]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = overview_render.main(argv)
    return code, buf.getvalue()


def _render(tmp_path: Path, registry: Path) -> tuple[int, dict, Path]:
    out = tmp_path / "overview.html"
    code, text = _run(["--registry", str(registry), "--repo-root", str(tmp_path),
                       "--out", str(out)])
    return code, json.loads(text), out


def test_all_pending_when_empty_registry(tmp_path):
    """空登记簿 → 6 技能全灰（公开「还没接」状态）"""
    reg = _write_registry(tmp_path, {})
    code, result, out = _render(tmp_path, reg)
    assert code == 0
    assert result["data"]["connected_count"] == 0
    assert result["data"]["pending_count"] == 6
    assert result["data"]["broken_count"] == 0
    html = out.read_text(encoding="utf-8")
    assert "未接入" in html


def test_connected_skill_green(tmp_path):
    """登记 + 契约有效 → 作息管家绿 + 域展示（--what 端到端跑通）"""
    skill_dir = _write_skill(tmp_path, "作息管家", VALID_DOMAINS_CODE)
    reg = _write_registry(tmp_path, {"作息管家": skill_dir})
    code, result, out = _render(tmp_path, reg)
    assert code == 0
    assert result["data"]["connected_count"] == 1
    assert result["data"]["pending_count"] == 5
    assert result["data"]["domain_count"] == 1
    html = out.read_text(encoding="utf-8")
    assert "已接入" in html
    assert "睡眠" in html


def test_registered_missing_file_broken(tmp_path):
    """登记了但缺 PUBLIC_DOMAINS.py → 红（登记 = 承诺，未兑现必须公示）"""
    reg = _write_registry(tmp_path, {"作息管家": None})
    code, result, out = _render(tmp_path, reg)
    assert code == 0
    assert result["data"]["connected_count"] == 0
    assert result["data"]["broken_count"] == 1
    html = out.read_text(encoding="utf-8")
    assert "登记异常" in html


def test_build_payload_snapshot():
    """payload 信封: 摘要/分区/结构化 skills 齐全（scene-data 契约 §4）"""
    skills = [
        {"name": "作息管家", "status": "connected",
         "domains": [{"name": "sleep", "cn": "睡眠", "desc": "d", "fields": []}]},
        {"name": "卡路里", "status": "pending", "reason": "未接入"},
    ]
    payload = overview_render.build_payload(skills, Path("registry.yaml"))
    ov = payload["data"]["overview"]
    assert ov["connected_count"] == 1
    assert ov["pending_count"] == 1
    assert ov["target_total"] == 2
    assert payload["data"]["scene"]["snapshot"]["sections"][0]["heading"] == "已接入（绿）"
    assert payload["data"]["meta"]["command_cn"]


def test_injector_hard_gate_resolves(tmp_path):
    """注入管线硬拦截: 三个占位符全部解析 + Base 资产注入"""
    reg = _write_registry(tmp_path, {})
    code, _, out = _render(tmp_path, reg)
    assert code == 0
    html = out.read_text(encoding="utf-8")
    assert "<!--INJECT-DATA-->" not in html
    assert "<!--SHARED-HELPERS-->" not in html
    assert "<!--SHARED-CSS-->" not in html
    assert "hm-status" in html          # Base CSS 注入
    assert "function statusBadge" in html  # Base JS 注入


def test_default_out_path_uses_skills_db_path(tmp_path, monkeypatch):
    """输出路径: SKILLS_DB_PATH 生效（默认不落 D:/.db 生产目录）"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    p = overview_render.default_out_path()
    assert p.parent == tmp_path / "skilllink_html"
    assert p.name.startswith("技能互联_HELP_")
    assert p.name.endswith(".html")


def test_real_registry_render_to_tmp(tmp_path):
    """冒烟: 真 registry（仓库登记簿）渲染，输出隔离到 tmp。

    只读 yaml + --what（不执行 fetch，不碰任何 DB）；repo-root 用真仓库根
    （registry 里是相对路径）。契约 drift 时会红——与 test_contract_gate 同精神。
    """
    reg = LINK_DIR / "skill_registry.yaml"
    if not reg.exists():
        pytest.skip("真 registry 不存在")
    out = tmp_path / "overview.html"
    code, text = _run(["--out", str(out)])
    assert code == 0, text
    assert out.exists()
