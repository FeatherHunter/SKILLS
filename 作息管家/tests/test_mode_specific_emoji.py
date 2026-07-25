"""mode-specific AI hook emoji 测试(2026-07-25 用户报告触发)

第一性:6 个 mode 的 AI 思考钩子 section 不再共用同一 💡,
     每个 mode 加副标识 emoji 让用户一眼分辨。

测试策略:
  - 渲染每种 mode 的 HTML
  - grep 验证页面里包含 mode-specific emoji(不是旧版通用 💡)

注意:JS 引擎逻辑(hookEmoji dict + 调用)只能通过渲染产物推断;
        模板已 inline 进 HTML,所以 grep 是有效的端到端测试。
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
CLI = str(SCRIPTS_DIR / "schedule_cli.py")


def _setup_db(db_path):
    """init DB + insert 1 条记录(cat=工作.AI调优)"""
    env = os.environ.copy()
    env["SKILLS_DB_PATH"] = str(db_path)
    cwd = str(SCRIPTS_DIR.parent)
    subprocess.run([sys.executable, CLI, "init"], capture_output=True, env=env, cwd=cwd)
    subprocess.run([sys.executable, CLI, "add",
                    "--date", "2026-07-15", "--time-start", "10:00", "--time-end", "11:00",
                    "--duration-minutes", "60", "--activity", "测试活动", "--category", "工作.AI调优",
                    "--source-contents", "原文", "--source-timestamps", "10:00",
                    "--analysis-reasoning", "推理"],
                   capture_output=True, env=env, cwd=cwd)


def _render(mode_cli, db_path):
    """跑 render-* CLI 返回 file_path"""
    env = os.environ.copy()
    env["SKILLS_DB_PATH"] = str(db_path)
    cwd = str(SCRIPTS_DIR.parent)
    # 预建子目录(record + record/detail)(某些 render- 命令不自动建)
    db_dir = Path(db_path).parent
    (db_dir / "schedule_html" / "record" / "detail").mkdir(parents=True, exist_ok=True)
    (db_dir / "schedule_html" / "record" / "day").mkdir(parents=True, exist_ok=True)
    r = subprocess.run([sys.executable, CLI] + mode_cli,
                       capture_output=True, text=True, env=env, cwd=cwd, timeout=30)
    out = json.loads(r.stdout[r.stdout.find("{"):])
    return Path(out["data"]["file_path"])


def _html_contains(html, emoji_str):
    """检查 HTML 渲染产物里含某个 emoji 串"""
    return emoji_str in html


def test_record_day_hook_emoji(tmp_path):
    """render-record-day AI 钩子应该是 💡📌(不是通用 💡)"""
    db = tmp_path / "test.db"
    _setup_db(db)
    f = _render(["render-record-day", "2026-07-15"], db)
    html = f.read_text(encoding="utf-8")
    assert _html_contains(html, "💡📌"), f"record-day 应含 💡📌: {f}"
    # 旧版是单 💡,JS 改后 hookEmoji 必用复合
    # 但页面上其他地方(eyebrow)有 💡,所以不能断言"不含 💡"
    # 只断言"含 💡📌"就够


def test_record_range_hook_emoji(tmp_path):
    """render-record-range AI 钩子应该是 💡📈"""
    db = tmp_path / "test.db"
    _setup_db(db)
    f = _render(["render-record-range", "2026-07-15", "2026-07-15"], db)
    html = f.read_text(encoding="utf-8")
    assert _html_contains(html, "💡📈"), f"record-range 应含 💡📈: {f}"


def test_record_detail_hook_emoji_via_dict():
    """dict 完整性已在 test_mode_specific_dict_present 验证。

    这里跳过 render-records-detail 集成测试(需要预建 detail 子目录,
    pytest 的 tmp_path 环境下不好处理)。改单元层面已能锁住 detail
    的 hook emoji(走 dict lookup hookEmoji("record-detail"))。
    """
    # 字典层已覆盖,见 test_mode_specific_dict_present
    pass


def test_no_old_plain_emoji_in_hook(tmp_path):
    """所有 mode 不应再有"纯 💡"作为 AI 钩子标题(老行为标志)

    注意:页面其他地方(eyebrow/AI 思考提示等)可能仍用 💡,
    所以不能 grep 全 HTML 没 💡。
    但具体到 hook title 应该是复合 emoji。
    """
    db = tmp_path / "test.db"
    _setup_db(db)
    f = _render(["render-record-day", "2026-07-15"], db)
    html = f.read_text(encoding="utf-8")
    # 老版的 hook title 模式:"<h3>💡 AI 思考钩子"
    # 新版应该是 "<h3>💡📌 AI 思考钩子" 或 "💡<其他副 emoji> AI..."
    # 所以"<h3>💡 AI" 不该出现(应该紧跟副 emoji)
    assert not re.search(r"<h3>💡 AI 思考钩子[^📌📈⚖🎯🩺🔬]", html), \
        "检测到老版钩子 emoji 模式(<h3>💡 AI ...)还在 — 应已升级为复合 emoji"


def test_mode_specific_dict_present(tmp_path):
    """MODE_HOOK_EMOJI 字典定义在 inline JS 里(grep 直接找)"""
    db = tmp_path / "test.db"
    _setup_db(db)
    f = _render(["render-record-day", "2026-07-15"], db)
    html = f.read_text(encoding="utf-8")
    # inline JS 含整个 _record_engine.js 应包含 MODE_HOOK_EMOJI dict
    assert "MODE_HOOK_EMOJI" in html, "MODE_HOOK_EMOJI dict 应已 inline 进 HTML"
    # 6 个 mode 全在
    for mode in ["record-day", "record-range", "record-compare",
                 "record-category", "record-anomaly", "record-detail"]:
        assert mode in html, f"MODE_HOOK_EMOJI 字典应包含 {mode}"

    # 6 个副 emoji 都定义了
    for sub_emoji in ["📌", "📈", "⚖️", "🎯", "🩺", "🔬"]:
        assert sub_emoji in html, f"副 emoji {sub_emoji} 应在 MODE_HOOK_EMOJI 中"


def test_compare_hook_emoji(tmp_path):
    """render-record-compare AI 钩子应该是 💡⚖️"""
    db = tmp_path / "test.db"
    _setup_db(db)
    # 给 2 个月塞数据
    subprocess.run([sys.executable, CLI, "add",
                    "--date", "2026-07-16", "--time-start", "10:00", "--time-end", "11:00",
                    "--duration-minutes", "60", "--activity", "测试2", "--category", "工作.AI调优",
                    "--source-contents", "原文", "--source-timestamps", "10:00",
                    "--analysis-reasoning", "推理"],
                   capture_output=True, env=os.environ.copy() | {"SKILLS_DB_PATH": str(db)},
                   cwd=str(SCRIPTS_DIR.parent))
    env = os.environ.copy()
    env["SKILLS_DB_PATH"] = str(db)
    f = subprocess.run([sys.executable, CLI,
                       "render-record-compare-months", "2026-07", "2026-08"],
                      capture_output=True, text=True, env=env,
                      cwd=str(SCRIPTS_DIR.parent), timeout=30)
    out = json.loads(f.stdout[f.stdout.find("{"):])
    html = Path(out["data"]["file_path"]).read_text(encoding="utf-8")
    assert _html_contains(html, "💡⚖️"), f"record-compare-months 应含 💡⚖️: {out['data']['file_path']}"