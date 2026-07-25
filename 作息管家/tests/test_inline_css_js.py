"""真单文件测试(2026-07-25 第一性修复 commit 准备)

第一性:HTML 自称"单文件自包含,无外部依赖",
但 5 个 record 模板 + detail + receipt_edit 实际依赖外部 _record_styles.css + _record_engine.js。
在 Chrome file:// 下能用,飞书/邮件消息预览拿不到 CSS/JS → JS 不跑 → 数据不显示。

修复:`inject_into_template` 把 CSS/JS inline 进 HTML。
本测试锁住"真单文件"属性。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
CLI = str(SCRIPTS_DIR / "schedule_cli.py")


def _gen_html(extra_args=None, db_path=None):
    """生成一个新 HTML,返回文件路径"""
    import os
    env = os.environ.copy()
    env["SKILLS_DB_PATH"] = str(db_path)
    cwd = str(SCRIPTS_DIR.parent)
    # 加 1 条测试数据
    subprocess.run([sys.executable, CLI, "init"], capture_output=True, env=env, cwd=cwd)
    subprocess.run([sys.executable, CLI, "add",
                    "--date", "2026-07-15", "--time-start", "10:00", "--time-end", "11:00",
                    "--duration-minutes", "60", "--activity", "测试", "--category", "工作.AI调优",
                    "--source-contents", "原文", "--source-timestamps", "10:00",
                    "--analysis-reasoning", "推理"],
                   capture_output=True, env=env, cwd=cwd)
    # 渲染
    args = extra_args or ["render-record-day", "2026-07-15"]
    r = subprocess.run([sys.executable, CLI] + args,
                       capture_output=True, text=True, env=env, cwd=cwd, timeout=30)
    out = json.loads(r.stdout[r.stdout.find("{"):])
    return Path(out["data"]["file_path"])


def test_no_external_stylesheet_ref(tmp_path):
    """HTML 不应有 <link href="_record_styles.css"> 引用(应 inline 进 <style>)"""
    f = _gen_html(db_path=tmp_path / "test.db")
    html = f.read_text(encoding="utf-8")
    assert '<link rel="stylesheet" href="_record_styles.css">' not in html, \
        f"仍含外部 CSS 引用,inline 没生效:{f}"
    # 应含 inline <style>
    assert "<style>" in html, "inline <style> 缺失"


def test_no_external_js_src_ref(tmp_path):
    """HTML 不应有 <script src="_record_engine.js"> 引用(应 inline)"""
    f = _gen_html(db_path=tmp_path / "test.db")
    html = f.read_text(encoding="utf-8")
    assert '<script src="_record_engine.js">' not in html, \
        f"仍含外部 JS 引用,inline 没生效:{f}"
    # 应含 inline <script>(包裹 JS 内容)
    assert "var MODE_LABELS" in html, "inline JS(MODE_LABELS)缺失"


def test_css_content_inlined(tmp_path):
    """CSS 内容(Apple 风基础样式)— 通过 _record_styles.css 内容特征检测"""
    f = _gen_html(db_path=tmp_path / "test.db")
    html = f.read_text(encoding="utf-8")
    # CSS 含 ":root{"(变量定义)和 "linear-gradient"
    assert ":root{" in html, "inlined CSS 缺失 :root 变量"
    assert "linear-gradient" in html, "inlined CSS 缺失 linear-gradient"


def test_js_content_inlined(tmp_path):
    """JS 内容(_record_engine.js)— 通过关键函数名检测"""
    f = _gen_html(db_path=tmp_path / "test.db")
    html = f.read_text(encoding="utf-8")
    # JS 含 MODE_HANDLERS + renderDay / renderCompare 等分发函数
    assert "MODE_HANDLERS" in html, "inlined JS 缺失 MODE_HANDLERS"
    assert "function renderDay" in html or "renderDay" in html, "inlined JS 缺失 renderDay"
    assert "renderCompare" in html, "inlined JS 缺失 renderCompare"


def test_payload_still_injected(tmp_path):
    """inline 后 payload 仍正确注入"""
    f = _gen_html(db_path=tmp_path / "test.db")
    html = f.read_text(encoding="utf-8")
    m = re.search(r'<script id="payload"[^>]*>(.*?)</script>', html, re.DOTALL)
    assert m is not None, "payload 锚点缺失"
    p = json.loads(m.group(1))
    assert p["status"] == "ok"
    assert p["data"]["meta"]["mode"] == "record-day"
    assert p["data"]["meta"]["record_count"] == 1


def test_filename_compliant(tmp_path):
    """命名合规仍生效(手册 §4.1)"""
    f = _gen_html(db_path=tmp_path / "test.db")
    assert re.match(r"^[a-z_]+_\d{8}_\d{6}\.html$", f.name), f"命名错:{f.name}"


def test_html_works_offline(tmp_path):
    """真单文件 — 把 HTML 拷到一个空目录,浏览器应能正常渲染

    (模拟用户分享 HTML 到飞书/邮件:文件被孤立,但单文件应能自渲染)
    """
    f = _gen_html(db_path=tmp_path / "test.db")
    # 把 HTML 拷到新空目录(无 CSS/JS 同伴)
    isolated = tmp_path / "isolated.html"
    f.rename(isolated)
    html = isolated.read_text(encoding="utf-8")
    # 关键:html 里能找到所有关键内容
    assert html.count("<style>") >= 1, "应有 inline <style>"
    # inline JS 用注释开头(看 _record_engine.js 头部),允许 <script>\n\n/* ... */\nvar MODE_LABELS
    assert "var MODE_LABELS" in html, "应有 inline JS(MODE_LABELS)"
    assert 'id="payload"' in html, "应有 payload 锚点"
    assert len(html) > 30000, f"单文件应 >30KB,实际 {len(html)}"


def test_receipt_edit_also_single_file(tmp_path):
    """receipt_edit(蓝调纠正回执)也应单文件

    receipt_edit 模板用自己内嵌的 IIFE JS 渲染 diff 表,不依赖
    _record_engine.js 的 MODE_HANDLERS 分发(因为 payload.mode 是
    'record-receipt-edit' 不在 _record_engine.js 的 modes 列表里)。
    因此 inject 不该把 _record_engine.js 内容塞进去。
    """
    db = tmp_path / "test.db"
    import os
    env = os.environ.copy()
    env["SKILLS_DB_PATH"] = str(db)
    cwd = str(SCRIPTS_DIR.parent)
    subprocess.run([sys.executable, CLI, "init"], capture_output=True, env=env, cwd=cwd)
    subprocess.run([sys.executable, CLI, "add",
                    "--date", "2026-07-15", "--time-start", "10:00", "--time-end", "11:00",
                    "--duration-minutes", "60", "--activity", "测试", "--category", "工作.AI调优",
                    "--source-contents", "原文", "--source-timestamps", "10:00",
                    "--analysis-reasoning", "推理"],
                   capture_output=True, env=env, cwd=cwd)
    # 先 correct-record 创建 edit_count
    subprocess.run([sys.executable, CLI, "correct-record", "1",
                    "--category", "工作.开发"],
                   capture_output=True, env=env, cwd=cwd)
    # 再 render-record-receipt-edit
    r = subprocess.run([sys.executable, CLI, "render-record-receipt-edit", "1",
                        "--diff", '{"category":{"old":"工作.AI调优","new":"工作.开发"}}'],
                       capture_output=True, text=True, env=env, cwd=cwd)
    out = json.loads(r.stdout[r.stdout.find("{"):])
    f = Path(out["data"]["file_path"])
    html = f.read_text(encoding="utf-8")
    # 无外部 link/script 引用
    assert '<link rel="stylesheet" href="_record_styles.css">' not in html
    assert '<script src="_record_engine.js"></script>' not in html
    # 也不应有错误的 <script src="_record_styles.css">(原模板笔误,2026-07-25 修)
    assert 'src="_record_styles.css"' not in html
    # 也不应有错误的 <script src="_record_engine.js">(receipt_edit 用自己 JS)
    assert 'src="_record_engine.js"' not in html
    # 应有 inline <style>(自带蓝调 CSS)
    assert html.count("<style>") >= 1