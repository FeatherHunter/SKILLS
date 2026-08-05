"""SM8 开始使用域测试(fixture 临时库 · 不碰生产库 · G6)

覆盖场景: 首次使用(环境检测/建库/种子/幂等)+ 数据检查(8 检查项)
+ 备份导出(全量打包/保留 N 份/JSON/CSV)+ 导入恢复(校验/冲突/回滚)
seam: scripts/开始使用/ops.py 公共函数(monkeypatch DB_PATH/PHOTOS_DIR)
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

import home_manager.db as db
from 开始使用 import ops


@pytest.fixture
def sm8_env(tmp_path, monkeypatch):
    """SM8 隔离环境:DB_PATH/PHOTOS_DIR 指向 tmp(全新库,fresh 初始化场景)"""
    db_path = tmp_path / "home.db"
    photos = tmp_path / "photos"
    monkeypatch.setattr(db, "DB_PATH", db_path)
    monkeypatch.setattr(db, "PHOTOS_DIR", photos)
    monkeypatch.setattr(ops, "DB_PATH", db_path)
    monkeypatch.setattr(ops, "PHOTOS_DIR", photos)
    photos.mkdir(parents=True, exist_ok=True)
    return tmp_path


# ── 首次使用 · 环境检测 ───────────────────────────────────────────────

def test_env_check_reports_fresh_state(sm8_env):
    """环境检测:OS/Python/目录可写/库不存在 → 未初始化"""
    p = ops.env_check_payload()
    assert p["status"] == "ok"
    assert p["os"] in ("Windows", "WSL", "Linux", "Darwin")
    assert p["python"]
    assert p["db_exists"] is False
    assert p["dirs_writable"]["db_dir"] is True
    assert p["dirs_writable"]["photos_dir"] is True


def test_init_status_fresh(sm8_env):
    """初始化状态:库不存在 → 未初始化"""
    p = ops.init_status_payload()
    assert p["initialized"] is False


def test_init_seeds_full_tree(sm8_env):
    """初始化:建库 + 种子 60 节点(8 顶级 + 52 二级)+ seed_key"""
    p = ops.init_db_and_seed()
    assert p["status"] == "ok"
    assert p["initialized"] is True
    assert p["top_level"] == 8, f"顶级应 8,实际 {p['top_level']}"
    assert p["total"] == 60, f"节点应 60,实际 {p['total']}"
    assert p["seed_keys"] == 60, f"seed_key 应 60,实际 {p['seed_keys']}"

    conn = sqlite3.connect(str(sm8_env / "home.db"))
    try:
        conn.row_factory = sqlite3.Row
        assert conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 60
        # seed_key 具体值抽查
        food = conn.execute(
            "SELECT id FROM categories WHERE seed_key = 'food'").fetchone()
        assert food, "缺 food 顶级 seed_key"
        shoes = conn.execute(
            "SELECT id FROM categories WHERE seed_key = 'clothing_shoes'").fetchone()
        assert shoes, "缺 clothing_shoes 二级 seed_key"
        # 名称与用户体系完全一致(8 顶级名)
        tops = {r["name"] for r in conn.execute(
            "SELECT name FROM categories WHERE parent_id IS NULL")}
        assert tops == {"食物与饮品", "衣物与穿戴", "家居与陈设", "工具与器材",
                        "数码与电子", "健康与医药", "文体与娱乐", "资产与凭证"}, tops
    finally:
        conn.close()


def test_init_idempotent(sm8_env):
    """初始化幂等:已初始化 → 跳过,不二次建库建分类"""
    first = ops.init_db_and_seed()
    assert first["status"] == "ok"
    second = ops.init_db_and_seed()
    assert second["status"] == "ok"
    assert second["skipped"], "第二次应跳过种子导入"
    conn = sqlite3.connect(str(sm8_env / "home.db"))
    try:
        assert conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 60
    finally:
        conn.close()


def test_init_status_after_seed(sm8_env):
    """初始化状态:种子化后 → 已初始化"""
    ops.init_db_and_seed()
    p = ops.init_status_payload()
    assert p["initialized"] is True
    assert "分类" in p["detail"]


# ── 分类解析器(三级 fallback)─────────────────────────────────────────

def test_resolve_by_seed_key(sm8_env):
    """解析器①:seed_key 命中"""
    ops.init_db_and_seed()
    conn = sqlite3.connect(str(sm8_env / "home.db"))
    try:
        conn.row_factory = sqlite3.Row
        row = ops.resolve_category(conn, seed_key="clothing_shoes")
        assert row and row["name"] == "鞋类"
    finally:
        conn.close()


def test_resolve_fallback_to_name(sm8_env):
    """解析器②:无 seed_key(老库)→ 名称命中"""
    conn = sqlite3.connect(str(sm8_env / "home.db"))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("INSERT INTO categories (parent_id, name) VALUES (NULL, '测试老分类')")
        conn.commit()
        row = ops.resolve_category(conn, seed_key="whatever", legacy_name="测试老分类")
        assert row and row["name"] == "测试老分类"
    finally:
        conn.close()


def test_resolve_fallback_to_id(sm8_env):
    """解析器③:都失败 → id 兜底"""
    conn = sqlite3.connect(str(sm8_env / "home.db"))
    try:
        conn.row_factory = sqlite3.Row
        row = ops.resolve_category(conn, seed_key="nope", legacy_name="也不在", legacy_id=999)
        assert row is None, "id 不存在 → None"
        cur = conn.cursor()
        cur.execute("INSERT INTO categories (parent_id, name) VALUES (NULL, 'X')")
        cid = cur.lastrowid
        conn.commit()
        row = ops.resolve_category(conn, seed_key="nope", legacy_name="也不在", legacy_id=cid)
        assert row and row["id"] == cid
    finally:
        conn.close()


# ── 数据检查(查异常)──────────────────────────────────────────────────

def _seed_issue_item(conn, name="TEST_无标签无位置无照片无价格"):
    cur = conn.cursor()
    cur.execute("INSERT INTO items (name, category, remark, photo) VALUES (?, '分类', '', NULL)",
                (name,))
    return cur.lastrowid


def test_lint_healthy_empty_db(sm8_env):
    """空库(种子后)→ 全部检查项 0 问题,healthy=True"""
    ops.init_db_and_seed()
    p = ops.lint_health_payload()
    assert p["status"] == "ok"
    assert p["healthy"] is True
    assert p["issues_total"] == 0
    assert len(p["checks"]) == 8, f"应 8 检查项,实际 {len(p['checks'])}"


def test_lint_detects_issues(sm8_env):
    """注入问题数据 → 对应检查项命中(无标签/无位置/无照片/无价格/无日期)"""
    ops.init_db_and_seed()
    conn = sqlite3.connect(str(sm8_env / "home.db"))
    try:
        conn.row_factory = sqlite3.Row
        _seed_issue_item(conn)
        conn.commit()
    finally:
        conn.close()

    p = ops.lint_health_payload()
    assert p["healthy"] is False
    assert p["issues_total"] > 0
    by_key = {c["key"]: c for c in p["checks"]}
    assert by_key["no_tag"]["count"] == 1
    assert by_key["no_location"]["count"] == 1
    assert by_key["no_photo"]["count"] == 1
    assert by_key["no_price"]["count"] == 1
    # 每项都有修复引导(只建议不自动改)
    for c in p["checks"]:
        assert c["fix_prompt"], f"{c['key']} 缺修复引导"
        assert "改物品" in c["fix_prompt"] or "拍物品" in c["fix_prompt"] or "移物品" in c["fix_prompt"]


def test_lint_stale_status_detected(sm8_env):
    """状态时效:快递中 10 天(>7)→ 命中"""
    ops.init_db_and_seed()
    conn = sqlite3.connect(str(sm8_env / "home.db"))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("INSERT INTO items (name, category) VALUES ('TEST_快递', '分类')")
        iid = cur.lastrowid
        cur.execute("""
            INSERT INTO item_locations (item_id, location, quantity, location_status, updated_at)
            VALUES (?, '快递', 1, '快递中', datetime('now', '-10 days'))
        """, (iid,))
        conn.commit()
    finally:
        conn.close()
    p = ops.lint_health_payload()
    by_key = {c["key"]: c for c in p["checks"]}
    assert by_key["stale_status"]["count"] == 1


def test_lint_similar_locations(sm8_env):
    """相似位置:卧室/东南角 ↔ 卧室东南角 → 命中"""
    ops.init_db_and_seed()
    conn = sqlite3.connect(str(sm8_env / "home.db"))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        for name, loc in [("TEST_A", "卧室/东南角"), ("TEST_B", "卧室东南角")]:
            cur.execute("INSERT INTO items (name, category) VALUES (?, '分类')", (name,))
            iid = cur.lastrowid
            cur.execute(
                "INSERT INTO item_locations (item_id, location, quantity) VALUES (?, ?, 1)",
                (iid, loc))
        conn.commit()
    finally:
        conn.close()
    p = ops.lint_health_payload()
    by_key = {c["key"]: c for c in p["checks"]}
    assert by_key["similar_location"]["count"] >= 1


# ── 备份与导出 ───────────────────────────────────────────────────────

def test_backup_creates_zip(sm8_env):
    """备份:生成 zip(db+照片)"""
    ops.init_db_and_seed()
    (sm8_env / "photos" / "a.jpg").write_bytes(b"x" * 100)
    p = ops.backup_payload()
    assert p["status"] == "ok"
    f = Path(p["file"])
    assert f.exists() and f.suffix == ".zip"
    assert p["size"] > 0
    assert p["days_since_last"] == 0
    # zip 内容:home.db + photos
    import zipfile
    with zipfile.ZipFile(f) as zf:
        names = zf.namelist()
    assert "home.db" in names
    assert "photos/a.jpg" in names


def test_backup_prunes_keep_n(sm8_env):
    """保留 N 份:6 次备份 → 只留 5"""
    ops.init_db_and_seed()
    for _ in range(6):
        ops.backup_payload(keep_n=5)
    files = list((sm8_env / "backups").glob("home_backup_*.zip"))
    assert len(files) == 5, f"应保留 5 份,实际 {len(files)}"


def test_backup_list_and_delete(sm8_env):
    """备份历史列表 + 删除(确认式)"""
    ops.init_db_and_seed()
    ops.backup_payload()
    lst = ops.backup_list_payload()
    assert lst["status"] == "ok"
    assert lst["count"] == 1
    name = lst["history"][0]["file"]
    d = ops.delete_backup_payload(name)
    assert d["status"] == "ok"
    assert ops.backup_list_payload()["count"] == 0
    bad = ops.delete_backup_payload("home_backup_nope.zip")
    assert bad["status"] == "error"


def test_export_json_roundtrip(sm8_env):
    """导出 JSON:全表可解析,含 schema_version"""
    ops.init_db_and_seed()
    conn = sqlite3.connect(str(sm8_env / "home.db"))
    try:
        conn.execute("INSERT INTO items (name, category) VALUES ('TEST_导出物', '分类')")
        conn.commit()
    finally:
        conn.close()
    p = ops.export_payload(fmt="json")
    assert p["status"] == "ok"
    data = json.loads(Path(p["file"]).read_text(encoding="utf-8"))
    assert data["schema_version"] == ops.IMPORT_SCHEMA_VERSION
    assert any(i["name"] == "TEST_导出物" for i in data["items"])


def test_export_csv(sm8_env):
    """导出 CSV:便携表格"""
    ops.init_db_and_seed()
    p = ops.export_payload(fmt="csv")
    assert p["status"] == "ok"
    text = Path(p["file"]).read_text(encoding="utf-8")
    assert "id,name" in text.splitlines()[0]


# ── 导入与恢复 ───────────────────────────────────────────────────────

def _make_export_file(sm8_env, names=("TEST_导入A", "TEST_导入B")):
    """构造一份 JSON 导出文件(含 items + locations + tags)"""
    data = {
        "schema_version": ops.IMPORT_SCHEMA_VERSION,
        "exported_at": "2026-08-05 00:00:00",
        "items": [{"id": 1, "name": names[0], "category": "分类"},
                  {"id": 2, "name": names[1], "category": "分类"}],
        "item_locations": [{"item_id": 1, "location": "客厅/电视柜", "quantity": 1,
                            "reason": "", "location_status": "在家",
                            "purchase_date": None, "expiration_date": None}],
        "item_tags": [{"item_id": 1, "tag": "红色"}],
        "categories": [],
    }
    f = sm8_env / "export_test.json"
    f.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return f


def test_import_preview(sm8_env):
    """导入前校验 + 冲突预览:新件 + 同名冲突计数"""
    ops.init_db_and_seed()
    conn = sqlite3.connect(str(sm8_env / "home.db"))
    try:
        conn.execute("INSERT INTO items (name, category) VALUES ('TEST_导入A', '分类')")
        conn.commit()
    finally:
        conn.close()
    f = _make_export_file(sm8_env)
    p = ops.import_preview_payload(str(f))
    assert p["status"] == "ok"
    assert p["valid"] is True
    assert p["items_total"] == 2
    assert p["duplicate_count"] == 1, "TEST_导入A 已在库 → 冲突 1"
    assert p["new_count"] == 1
    assert p["conflicts"][0]["name"] == "TEST_导入A"


def test_import_execute_skip_mode(sm8_env):
    """确认导入(skip):新增 1,跳过 1;导入前自动备份"""
    ops.init_db_and_seed()
    conn = sqlite3.connect(str(sm8_env / "home.db"))
    try:
        conn.execute("INSERT INTO items (name, category) VALUES ('TEST_导入A', '分类')")
        conn.commit()
    finally:
        conn.close()
    f = _make_export_file(sm8_env)
    p = ops.import_execute_payload(str(f), mode="skip")
    assert p["status"] == "ok"
    assert p["imported"] == 1
    assert p["skipped"] == 1
    assert p["overwritten"] == 0
    assert p["backup_file"] and Path(p["backup_file"]).exists(), "导入前应自动备份"
    # 位置/标签随导入
    conn = sqlite3.connect(str(sm8_env / "home.db"))
    try:
        conn.row_factory = sqlite3.Row
        new = conn.execute(
            "SELECT i.id FROM items i WHERE i.name='TEST_导入B'").fetchone()
        assert new, "TEST_导入B 应已导入"
        loc = conn.execute(
            "SELECT location FROM item_locations WHERE item_id=?", (new["id"],)).fetchone()
        assert loc and loc["location"] == "客厅/电视柜"
        tag = conn.execute(
            "SELECT tag FROM item_tags WHERE item_id=?", (new["id"],)).fetchone()
        assert tag and tag["tag"] == "红色"
    finally:
        conn.close()


def test_import_execute_overwrite(sm8_env):
    """确认导入(overwrite):同名覆盖"""
    ops.init_db_and_seed()
    conn = sqlite3.connect(str(sm8_env / "home.db"))
    try:
        conn.execute("INSERT INTO items (name, category, remark) VALUES ('TEST_导入A', '分类', '旧备注')")
        conn.commit()
    finally:
        conn.close()
    f = _make_export_file(sm8_env)
    p = ops.import_execute_payload(str(f), mode="overwrite")
    assert p["status"] == "ok"
    assert p["overwritten"] == 1
    assert p["imported"] == 1


def test_import_bad_file_returns_error(sm8_env):
    """非法文件:不存在 / 非 JSON → 错误(不触碰库)"""
    bad = ops.import_preview_payload(str(sm8_env / "nope.json"))
    assert bad["status"] == "error"
    f = sm8_env / "bad.json"
    f.write_text("not json", encoding="utf-8")
    bad2 = ops.import_preview_payload(str(f))
    assert bad2["status"] == "error"


def test_import_failure_rolls_back(sm8_env):
    """导入失败 → 回滚(数据不变)"""
    ops.init_db_and_seed()
    f = sm8_env / "broken.json"
    f.write_text(json.dumps({
        "schema_version": ops.IMPORT_SCHEMA_VERSION,
        "items": [{"id": 1, "name": "TEST_正常"}, {"id": 2, "name": None}],
        "item_locations": [{"item_id": 999999, "location": "?"}],  # FK 违例 → 触发回滚
        "item_tags": [],
        "categories": [],
    }), encoding="utf-8")
    p = ops.import_execute_payload(str(f), mode="skip", auto_backup=False)
    assert p["status"] == "error"
    conn = sqlite3.connect(str(sm8_env / "home.db"))
    try:
        assert conn.execute(
            "SELECT COUNT(*) FROM items WHERE name='TEST_正常'").fetchone()[0] == 0
    finally:
        conn.close()


# ── CLI 端到端(G6: 每场景 ≥1 端到端)─────────────────────────────────

def _run_cli(tmp_path, *args):
    env = {**os.environ, "SKILLS_DB_PATH": str(tmp_path)}
    r = subprocess.run(
        [sys.executable, str(Path(__file__).parent.parent / "scripts" / "开始使用" / "cli.py"), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=env, timeout=60,
    )
    assert r.returncode == 0, f"CLI 失败: {args} stderr={r.stderr}"
    return json.loads(r.stdout)


def test_cli_init_and_lint(tmp_path):
    """CLI:check → init → init-status → lint 端到端(全新库)"""
    p = _run_cli(tmp_path, "check")
    assert p["status"] == "ok"
    p = _run_cli(tmp_path, "init")
    assert p["total"] == 60
    p = _run_cli(tmp_path, "init-status")
    assert p["initialized"] is True
    p = _run_cli(tmp_path, "lint")
    assert p["status"] == "ok"
    assert len(p["checks"]) == 8


def test_cli_backup_export_import(tmp_path):
    """CLI:backup → backup-list → export → import-preview 端到端"""
    _run_cli(tmp_path, "init")
    p = _run_cli(tmp_path, "backup")
    assert p["status"] == "ok"
    p = _run_cli(tmp_path, "backup-list")
    assert p["count"] == 1
    p = _run_cli(tmp_path, "export", "--format", "json")
    assert p["status"] == "ok"
    # 导入预览(空库 → 无冲突)
    p = _run_cli(tmp_path, "import-preview", "--file", p["file"])
    assert p["status"] == "ok"


# ── HTML 模板结构(08 对齐 · fixture 无浏览器)─────────────────────────

TEMPLATES = Path(__file__).parent.parent / "templates" / "开始使用"
TEMPLATE_FILES = [
    "first_use_wizard.html", "health_report.html",
    "backup_receipt.html", "import_restore.html", "error_receipt.html",
]


def test_all_templates_present():
    for name in TEMPLATE_FILES:
        assert (TEMPLATES / name).exists(), f"缺模板 {name}"


def test_templates_have_contract_placeholders():
    """每个模板:恰好 1 个 INJECT-DATA + 共享 helpers + 复制按钮"""
    for name in TEMPLATE_FILES:
        h = (TEMPLATES / name).read_text(encoding="utf-8")
        assert h.count("<!--INJECT-DATA-->") == 1, f"{name} INJECT-DATA 数量错误"
        assert "<!--SHARED-HELPERS-->" in h, f"{name} 缺共享 helpers"
        assert "navigator.clipboard" in h or "safeWriteText" in h, f"{name} 缺复制能力"
        assert "复制数据" in h, f"{name} 缺复制数据按钮(硬标准)"
        assert "复制日志" in h, f"{name} 缺复制日志按钮(硬标准)"
        assert "esc(" in h, f"{name} 缺转义(XSS 防护)"


def test_first_use_wizard_has_steps():
    """首次使用向导:步骤条 + 重试 + 幂等提示"""
    h = (TEMPLATES / "first_use_wizard.html").read_text(encoding="utf-8")
    assert "steps" in h, "缺步骤条"
    assert "一键重试" in h, "缺一键重试(失败恢复)"
    assert "已初始化" in h, "缺幂等提示"


def test_health_report_has_fix_guidance():
    """数据检查:勾选 → 复制修复引导(只建议)"""
    h = (TEMPLATES / "health_report.html").read_text(encoding="utf-8")
    assert "copySelectedFixes" in h, "缺勾选复制"
    assert "只建议" in h, "缺'只建议不自动改'原则"


def test_import_has_preannounce():
    """导入:预告式文件选择(【导入文件即将发送:】)"""
    h = (TEMPLATES / "import_restore.html").read_text(encoding="utf-8")
    assert "导入文件即将发送" in h, "缺预告式文件占位"


def test_error_receipt_contract():
    """错误回执:操作名/原因/建议 + 修正重试 + 复制数据/日志"""
    h = (TEMPLATES / "error_receipt.html").read_text(encoding="utf-8")
    for tag in ["失败原因", "建议下一步", "修正重试", "复制数据", "复制日志"]:
        assert tag in h, f"错误回执缺 {tag}"


def test_render_first_use_end_to_end(sm8_env, tmp_path):
    """渲染端到端:init → 向导 HTML 生成(payload 可解析)"""
    ops.init_db_and_seed()
    from render_开始使用 import emit_sm8
    env = ops.env_check_payload()
    steps = [
        {"title": "环境检测", "status": "done"},
        {"title": "路径确认", "status": "done"},
        {"title": "建库", "status": "done"},
        {"title": "建分类", "status": "done"},
        {"title": "引导录入", "status": "current"},
        {"title": "完成回执", "status": "pending"},
    ]
    out = tmp_path / "wizard.html"
    rc = emit_sm8(
        "first_use_wizard.html",
        {"wizard": {"steps": steps, "stage": "pending"}, "env": env},
        scene_id="SM8-1", wake_word="首次使用", command_cn="首次使用",
        output_path=str(out),
    )
    assert rc == 0
    h = out.read_text(encoding="utf-8")
    m = re.search(r'<script id="payload" type="application/json">([\s\S]*?)</script>', h)
    assert m, "找不到 payload"
    payload = json.loads(m.group(1))
    assert payload["status"] == "ok"
    assert payload["data"]["meta"]["scene_id"] == "SM8-1"
