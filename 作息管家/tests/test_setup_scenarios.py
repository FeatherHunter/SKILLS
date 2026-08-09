"""首次使用域测试(实施 T7 · 2026-08-09)

覆盖:
- check 环境检测 payload(DB 状态/白名单/飞书三档)
- render-first-use 渲染(6 步步骤条/检查项/待办/验证/08 双按钮/锚点注入)
- 阶段判定: need_init(未建库) / already(已建库) / error(目录不可写)
- setup.yaml 片段满足合并器字段契约(update_scenarios.validate_fragment)
- COMMANDS 注册表契约(渐进式注册通道 · T1)

隔离约定(conftest 头部 + 操作规范 §7): 涉路径用例一律 SKILLS_DB_PATH=临时目录,
禁止无 env 跑 CLI 落生产库。
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import pytest

import setup_scenarios as ss
import schedule_db
from update_scenarios import validate_fragment


@pytest.fixture
def tmp_db_env(monkeypatch, tmp_path):
    """SKILLS_DB_PATH → 临时目录(隔离契约 §7);飞书探测打桩(避免真实 lark-cli 探测)"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    monkeypatch.setattr(ss, "_feishu_payload", lambda: {
        "tier": "missing", "cli_installed": False, "authenticated": False,
        "calendar_writable": False, "last_error": None,
    })
    return tmp_path


@pytest.fixture
def built_db(tmp_db_env, monkeypatch):
    """在临时目录真实建库(打补 schedule_db 模块级路径常量,绕过 import 时快照)"""
    d = tmp_db_env
    monkeypatch.setattr(schedule_db, "DB_DIR", d)
    monkeypatch.setattr(schedule_db, "DB_PATH", d / "schedule_data.db")
    monkeypatch.setattr(schedule_db, "DR_DB_PATH", d / "daily_recorder.db")
    schedule_db.init_db()
    return d


# ── check 环境检测 ────────────────────────────────────────────────────

def test_check_payload_shape(tmp_db_env):
    ck = ss._check_env()
    assert ck["status"] == "ok"
    assert ck["os"] in ("Windows", "Linux", "Darwin", "WSL")
    assert ck["python_ok"] is True
    assert ck["db_dir"] == str(tmp_db_env)
    assert ck["db_path"] == str(tmp_db_env / "schedule_data.db")
    assert ck["db_ready"] is False
    assert ck["db_tables"] == 0
    assert ck["whitelist_ready"] is True
    assert ck["env_skills_db_path"] == str(tmp_db_env)
    assert ck["feishu"]["tier"] == "missing"


def test_check_after_init(built_db):
    ck = ss._check_env()
    assert ck["db_ready"] is True
    assert ck["db_tables"] >= ss.EXPECTED_TABLES


def test_check_feishu_full(tmp_db_env, monkeypatch):
    monkeypatch.setattr(ss, "_feishu_payload", lambda: {
        "tier": "full", "cli_installed": True, "authenticated": True,
        "calendar_writable": True, "last_error": None,
    })
    ck = ss._check_env()
    assert ck["feishu"]["tier"] == "full"
    items, _todos, verify = ss._build_report(ck)
    feishu_item = next(i for i in items if i["name"] == "飞书联动")
    assert feishu_item["status"] == "ok"
    assert verify[-1] == {"text": "飞书同步已配置", "status": "ok"}


# ── 阶段判定 ──────────────────────────────────────────────────────────

def test_scene_stage_need_init(tmp_db_env):
    scene = ss._build_scene(ss._check_env())
    assert scene["wizard"]["stage"] == "need_init"
    assert [s["title"] for s in scene["wizard"]["steps"]] == [
        "环境检测", "路径确认", "建库+初始化", "状态确认", "初始化报告", "完成"]
    assert scene["next"]["label"] == "开始初始化(复制指令给 AI)"
    assert "init" in scene["next"]["prompt"]


def test_scene_stage_already(built_db):
    scene = ss._build_scene(ss._check_env())
    assert scene["wizard"]["stage"] == "already"
    assert all(s["status"] == "done" for s in scene["wizard"]["steps"])
    assert scene["next"]["label"] == "开始使用(复制指令给 AI)"
    extra_labels = [x["label"] for x in scene["next_extra"]]
    assert "配置飞书(复制指令给 AI)" in extra_labels  # 飞书未配置 → 强引导不缺席


def test_scene_stage_error_when_dir_not_writable(tmp_db_env, monkeypatch):
    monkeypatch.setattr(ss, "_dir_writable", lambda d: False)
    scene = ss._build_scene(ss._check_env())
    assert scene["wizard"]["stage"] == "error"
    assert scene["wizard"]["steps"][0]["status"] == "fail"
    assert "重试" in scene["next"]["label"]


# ── 报告数据契约(items/todos/verify · 对标备忘录 init-report)────────────

def test_report_contract(tmp_db_env):
    ck = ss._check_env()
    items, todos, verify = ss._build_report(ck)
    names = [i["name"] for i in items]
    assert names == ["Python 可运行", "数据位置可写", "数据库已建", "分类白名单就绪", "飞书联动"]
    assert all(i["status"] in ("ok", "warn", "err", "fail", "skip") for i in items)
    assert any(t["title"].startswith("飞书配置") for t in todos)
    assert any(t["title"].startswith("自定义数据目录") for t in todos)
    assert verify[0] == "Python 可运行"
    assert verify[-1]["status"] == "skip"  # 飞书未配置三态


# ── 渲染 + 注入 ───────────────────────────────────────────────────────

def _extract_payload(html: str) -> dict:
    anchor = '<script id="payload" type="application/json">'
    start = html.find(anchor) + len(anchor)
    end = html.find("</script>", start)
    return json.loads(html[start:end])


def test_render_html_need_init(tmp_db_env):
    check = ss._check_env()
    out = ss._render_to(check)
    html = out["html"]
    assert out["stage"] == "need_init"
    # 锚点注入可解析 + 占位符清零
    payload = _extract_payload(html)
    assert payload["data"]["meta"]["mode"] == "first-use"
    assert len(payload["data"]["scene"]["wizard"]["steps"]) == 6
    assert "{{ title }}" not in html and "{{ TITLE }}" not in html
    assert "{{ template_name }}" not in html
    # 08 双按钮 + 阶段动作
    assert "复制数据" in html and "复制日志" in html
    assert "开始初始化(复制指令给 AI)" in html
    assert "6 步向导" in html


def test_render_html_already_contains_report_sections(built_db):
    out = ss._render_to(ss._check_env())
    html = out["html"]
    assert out["stage"] == "already"
    for section in ("环境信息", "检查项", "待办指引", "完成验证清单", "下一步"):
        assert section in html
    assert "配置飞书" in html          # 飞书强引导区
    assert "飞书同步未配置" in html
    assert "开始使用(复制指令给 AI)" in html
    payload = _extract_payload(html)
    assert payload["data"]["verify"][-1]["status"] == "skip"


def test_render_html_error(tmp_db_env, monkeypatch):
    monkeypatch.setattr(ss, "_dir_writable", lambda d: False)
    out = ss._render_to(ss._check_env())
    assert out["stage"] == "error"
    assert "一键重试" in out["html"]


def test_cmd_render_first_use_writes_file(tmp_db_env, capsys):
    ss.cmd_render_first_use(["--out", str(tmp_db_env / "out.html")])
    out_path = tmp_db_env / "out.html"
    assert out_path.exists()
    html = out_path.read_text(encoding="utf-8")
    assert _extract_payload(html)["data"]["scene"]["wizard"]["stage"] == "need_init"
    captured = capsys.readouterr()
    assert "首次使用初始化报告已生成" in captured.out


def test_cmd_check_outputs_json(tmp_db_env, capsys):
    ss.cmd_setup_check([])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["status"] == "ok"
    assert data["db_dir"] == str(tmp_db_env)


# ── setup.yaml 片段字段契约(合并器 · T1)────────────────────────────────

def test_setup_yaml_fragment_passes_merger_validation():
    import yaml
    frag_path = Path(__file__).parent.parent / "scenarios" / "setup.yaml"
    entries = yaml.safe_load(frag_path.read_text(encoding="utf-8")) or []
    assert isinstance(entries, list) and len(entries) == 1
    errors = validate_fragment(entries, frag_path.name)
    assert errors == []
    e = entries[0]
    assert e["scenario_id"] == "first_use"
    assert e["wake_word"] == "首次使用"
    assert e["status"] == ""


def test_commands_registry_contract():
    assert set(ss.COMMANDS) == {"check", "render-first-use"}
    for handler in ss.COMMANDS.values():
        assert callable(handler)
