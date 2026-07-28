"""render 层测试: 占位符校验 + 9 模板生成 + 12.A/12.B 命名"""
import re
from datetime import datetime
from pathlib import Path

import pytest

from render import render_page, emit, TEMPLATES_DIR


def test_payload_status_must_be_ok(tmp_path):
    """payload.status !== 'ok' → 在文件检查前就被拒 (用真实模板避免先触发模板不存在错误)"""
    bad_payload = {"status": "error", "data": {}, "message": "fail"}
    result = render_page("search_results.html", bad_payload, str(tmp_path / "out.html"))
    assert result["status"] == "error"
    assert "payload 状态校验失败" in result["message"]


def test_payload_must_be_dict(tmp_path):
    """非 dict payload → 拒"""
    result = render_page("search_results.html", "not a dict", str(tmp_path / "out.html"))
    assert result["status"] == "error"


def test_payload_without_data_still_renders(tmp_path):
    """status=ok 即使 data 缺失也接受 (模板用 data.data || data fallback)"""
    bad = {"status": "ok", "message": "no data field"}
    result = render_page("search_results.html", bad, str(tmp_path / "out.html"))
    assert result["status"] == "ok"


def test_template_not_found():
    """不存在的模板 → error"""
    payload = {"status": "ok", "data": {}, "message": ""}
    result = render_page("nonexistent_template.html", payload, "/tmp/x.html")
    assert result["status"] == "error"
    assert "模板不存在" in result["message"]


ALL_TEMPLATES = [
    "add_preview.html",
    "search_results.html",
    "item_detail.html",
    "list_overview.html",
    "inventory_check.html",
    "delivery_check.html",
    "expiring_alert.html",
    "outfit_picker.html",
    "travel_trip.html",
]


@pytest.mark.parametrize("template", ALL_TEMPLATES)
def test_template_uses_inject_data_placeholder(template):
    """9 模板都必须含 <!--INJECT-DATA--> 占位符"""
    path = TEMPLATES_DIR / template
    if not path.exists():
        pytest.skip(f"{template} not found at {path}")
    content = path.read_text(encoding="utf-8")
    assert content.count("<!--INJECT-DATA-->") == 1, \
        f"{template} 应含恰好 1 个 INJECT-DATA 占位符"


@pytest.mark.parametrize("template", ALL_TEMPLATES)
def test_template_uses_shared_helpers(template):
    """9 模板都应使用 SHARED-HELPERS 占位符 (R9 之后)"""
    path = TEMPLATES_DIR / template
    if not path.exists():
        pytest.skip(f"{template} not found at {path}")
    content = path.read_text(encoding="utf-8")
    assert "<!--SHARED-HELPERS-->" in content, \
        f"{template} 应使用 SHARED-HELPERS 占位符"


@pytest.mark.parametrize("template", ALL_TEMPLATES)
def test_template_has_payload_script_tag(template):
    """9 模板都必须含 <script id='payload'> 包裹 (回归: Phase 3 bug)"""
    path = TEMPLATES_DIR / template
    if not path.exists():
        pytest.skip(f"{template} not found at {path}")
    content = path.read_text(encoding="utf-8")
    assert '<script id="payload" type="application/json">' in content, \
        f"{template} 应含 <script id='payload'> 包裹"


def test_shared_js_includes_validate():
    """共享 JS 必须含 validate 函数 (R9 单一权威源)"""
    from render._shared import SHARED_JS
    assert "function validate" in SHARED_JS
    assert "function esc" in SHARED_JS
    assert "function arr" in SHARED_JS


def test_render_real_template_works(tmp_path):
    """用真实模板 (search_results.html) 验证生成流程"""
    payload = {
        "status": "ok",
        "data": {
            "summary": {"title": "test", "chips": []},
            "items": [{"id": 1, "name": "test_item", "category_id": 1,
                       "tags": [], "locations": [], "photo_base64": None}],
        },
        "message": "test",
    }
    out = tmp_path / "out.html"
    result = render_page("search_results.html", payload, str(out))
    assert result["status"] == "ok"
    content = out.read_text(encoding="utf-8")
    assert "test_item" in content  # 数据注入成功
    assert "<!--INJECT-DATA-->" not in content  # 占位符被替换
    assert "function validate" in content  # 共享 JS 注入成功


# ── 12.A / 12.B 自动命名 (原则 12) ────────────────────────────────────────────

_OK_SEARCH_PAYLOAD = {
    "status": "ok",
    "data": {
        "summary": {"title": "test", "chips": []},
        "items": [{"id": 1, "name": "test_item", "category_id": 1,
                   "tags": [], "locations": [], "photo_base64": None}],
    },
    "message": "test",
}


def test_12a_autonaming_with_skills_data_dir(tmp_path, monkeypatch):
    """12.A 自动命名:不传 output_path,SKILLS_DATA_DIR 指向 tmp_path
    → 文件落在 tmp_path/home_manager_html/查物品_YYYYMMDD_HHMMSS.html
    """
    monkeypatch.setenv("SKILLS_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("SKILLS_DB_PATH", raising=False)

    result = render_page("search_results.html", _OK_SEARCH_PAYLOAD)
    assert result["status"] == "ok"
    out_path = Path(result["data"]["output"])

    # 路径根 = SKILLS_DATA_DIR, 子目录 = home_manager_html
    assert out_path.parent == tmp_path / "home_manager_html"
    # 文件名 = 查物品_<8位日期>_<6位时间>.html
    assert re.match(r"^查物品_\d{8}_\d{6}\.html$", out_path.name), \
        f"文件名不符合 12.A: {out_path.name}"
    # 文件确实写入
    assert out_path.exists()
    # 内容被注入
    assert "test_item" in out_path.read_text(encoding="utf-8")


def test_env_chain_skills_db_path_fallback(tmp_path, monkeypatch):
    """env 链:SKILLS_DATA_DIR 未设,SKILLS_DB_PATH 指向 tmp_path → 输出根 = tmp_path"""
    monkeypatch.delenv("SKILLS_DATA_DIR", raising=False)
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))

    result = render_page("search_results.html", _OK_SEARCH_PAYLOAD)
    assert result["status"] == "ok"
    out_path = Path(result["data"]["output"])

    # 路径根 = SKILLS_DB_PATH (兜底), 子目录 = home_manager_html
    assert out_path.parent == tmp_path / "home_manager_html"
    assert out_path.exists()


def test_env_chain_priority_data_dir_over_db_path(tmp_path, monkeypatch):
    """env 链优先级:SKILLS_DATA_DIR > SKILLS_DB_PATH
    两个都设时,SKILLS_DATA_DIR 胜出
    """
    data_dir = tmp_path / "data_root"
    db_dir = tmp_path / "db_root"
    monkeypatch.setenv("SKILLS_DATA_DIR", str(data_dir))
    monkeypatch.setenv("SKILLS_DB_PATH", str(db_dir))

    result = render_page("search_results.html", _OK_SEARCH_PAYLOAD)
    out_path = Path(result["data"]["output"])

    # 落在 data_dir 下,不是 db_dir
    assert out_path.parent == data_dir / "home_manager_html"
    assert not (db_dir / "home_manager_html").exists()


def test_output_override_bypasses_autonaming(tmp_path, monkeypatch):
    """--output 显式 override:写到指定路径,不触发自动命名,不强制 home_manager_html/"""
    monkeypatch.setenv("SKILLS_DATA_DIR", str(tmp_path))  # 即使设了 env,override 也优先

    custom = tmp_path / "custom.html"
    result = render_page("search_results.html", _OK_SEARCH_PAYLOAD, str(custom))
    assert result["status"] == "ok"
    assert custom.exists()
    # 没有创建 home_manager_html 子目录
    assert not (tmp_path / "home_manager_html").exists()


def test_local_time_timestamp_matches_now(tmp_path, monkeypatch):
    """时间戳用本地时间(datetime.now()),接近测试执行时刻(允许 1 秒误差)"""
    monkeypatch.setenv("SKILLS_DATA_DIR", str(tmp_path))
    before = datetime.now()
    result = render_page("search_results.html", _OK_SEARCH_PAYLOAD)
    after = datetime.now()

    out_path = Path(result["data"]["output"])
    # 提取文件名里的时间戳
    m = re.search(r"_(\d{8})_(\d{6})\.html$", out_path.name)
    assert m, f"时间戳格式不符: {out_path.name}"
    stamped = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
    # 时间戳应在 [before-1s, after+1s] 区间(strftime 截断到秒,允许 1 秒误差)
    from datetime import timedelta
    assert before - timedelta(seconds=1) <= stamped <= after + timedelta(seconds=1), \
        f"时间戳 {stamped} 不在 [{before}, {after}] 区间"


def test_overwrite_same_name_file(tmp_path, monkeypatch):
    """同名文件已存在时,直接覆盖,不报错,内容为新版本"""
    monkeypatch.setenv("SKILLS_DATA_DIR", str(tmp_path))
    out_dir = tmp_path / "home_manager_html"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 先写入旧内容
    target = out_dir / "查物品_20260101_120000.html"
    target.write_text("OLD_CONTENT", encoding="utf-8")

    # mock datetime.now() 返回固定时刻,触发覆盖
    import render as render_mod
    from datetime import datetime as real_dt

    class FixedDT(real_dt):
        @classmethod
        def now(cls):
            return real_dt(2026, 1, 1, 12, 0, 0)

    monkeypatch.setattr(render_mod, "datetime", FixedDT)
    result = render_page("search_results.html", _OK_SEARCH_PAYLOAD)

    assert result["status"] == "ok"
    assert target.exists()
    new_content = target.read_text(encoding="utf-8")
    assert "OLD_CONTENT" not in new_content
    assert "test_item" in new_content


def test_subdir_autocreate(tmp_path, monkeypatch):
    """子目录不存在时,render_page 自动创建,不抛异常"""
    monkeypatch.setenv("SKILLS_DATA_DIR", str(tmp_path))
    # tmp_path 下还没有 home_manager_html
    assert not (tmp_path / "home_manager_html").exists()

    result = render_page("search_results.html", _OK_SEARCH_PAYLOAD)
    assert result["status"] == "ok"
    assert (tmp_path / "home_manager_html").exists()
    assert (tmp_path / "home_manager_html").is_dir()


def test_filename_no_reserved_chars(tmp_path, monkeypatch):
    """文件名不含文件系统保留字符 / \\ : * ? \" < > |"""
    monkeypatch.setenv("SKILLS_DATA_DIR", str(tmp_path))
    result = render_page("search_results.html", _OK_SEARCH_PAYLOAD)
    out_path = Path(result["data"]["output"])
    reserved = set('/\\:*?"<>|')
    assert not any(c in out_path.name for c in reserved), \
        f"文件名含保留字符: {out_path.name}"


# ── T02: 完整 template→command_cn 映射表 + 12.B HELP 命名 ─────────────────────

# 9 个非 help_center template 的 expected command_cn(与 render 层映射表一致)
TEMPLATE_TO_EXPECTED_CN = {
    "search_results.html": "查物品",
    "delivery_check.html": "查快递",
    "add_preview.html": "录物品",
    "item_detail.html": "看物品",
    "list_overview.html": "统物品",
    "inventory_check.html": "盘物品",
    "expiring_alert.html": "查过期",
    "outfit_picker.html": "穿什么",
    "travel_trip.html": "出行清单",
}


@pytest.mark.parametrize("template,expected_cn", list(TEMPLATE_TO_EXPECTED_CN.items()))
def test_12a_naming_for_all_templates(template, expected_cn, tmp_path, monkeypatch):
    """每个非 help_center template 自动命名时使用正确的中文 command_cn"""
    monkeypatch.setenv("SKILLS_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("SKILLS_DB_PATH", raising=False)

    # 每个模板需要的最小 ok payload(共享 search 的结构,大多模板容错)
    payload = {
        "status": "ok",
        "data": {"summary": {"title": "test"}, "items": []},
        "message": "test",
    }
    result = render_page(template, payload)
    assert result["status"] == "ok", f"{template} 渲染失败: {result.get('message')}"
    out_path = Path(result["data"]["output"])

    # 文件名前缀 = expected_cn
    assert out_path.name.startswith(f"{expected_cn}_"), \
        f"{template} → 期望前缀 '{expected_cn}_', 实际 '{out_path.name}'"
    assert out_path.parent == tmp_path / "home_manager_html"
    assert out_path.exists()


def test_12b_help_naming_uses_skill_cn_name_and_HELP_keyword(tmp_path, monkeypatch):
    """12.B HELP HTML 命名:<skill 中文名>_HELP_<YYYYMMDD>_<HHMMSS>.html"""
    monkeypatch.setenv("SKILLS_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("SKILLS_DB_PATH", raising=False)

    # help_center 的最小 ok payload
    payload = {
        "status": "ok",
        "data": {"categories": [], "scenarios": []},
        "message": "test help",
    }
    result = render_page("help_center.html", payload)
    assert result["status"] == "ok", f"help_center 渲染失败: {result.get('message')}"
    out_path = Path(result["data"]["output"])

    # 路径
    assert out_path.parent == tmp_path / "home_manager_html"
    # 文件名 = 居家管家_HELP_YYYYMMDD_HHMMSS.html
    assert re.match(r"^居家管家_HELP_\d{8}_\d{6}\.html$", out_path.name), \
        f"文件名不符合 12.B: {out_path.name}"
    assert out_path.exists()


def test_help_keyword_is_greppable(tmp_path, monkeypatch):
    """_HELP_ 保留字在文件名中段,可被 grep 一抓出来"""
    monkeypatch.setenv("SKILLS_DATA_DIR", str(tmp_path))
    payload = {"status": "ok", "data": {"categories": [], "scenarios": []}, "message": ""}
    result = render_page("help_center.html", payload)
    out_path = Path(result["data"]["output"])
    # _HELP_ 作为保留字,在文件名中段
    assert "_HELP_" in out_path.name
    # 不在开头也不在结尾(_HELP_ 前后都有内容)
    name = out_path.name
    help_idx = name.index("_HELP_")
    assert help_idx > 0, "_HELP_ 不应在文件名开头"
    assert help_idx + len("_HELP_") < len(name), "_HELP_ 不应在文件名结尾"


def test_travel_trip_uses_chuxing_qingdan_superset_name(tmp_path, monkeypatch):
    """travel_trip 用综合名 '出行清单'(涵盖带物品 pack + 归物品 return,不拆 template)"""
    monkeypatch.setenv("SKILLS_DATA_DIR", str(tmp_path))
    payload = {"status": "ok", "data": {"summary": {}, "items": []}, "message": ""}
    result = render_page("travel_trip.html", payload)
    out_path = Path(result["data"]["output"])
    assert out_path.name.startswith("出行清单_"), \
        f"travel_trip 应映射到 '出行清单',实际: {out_path.name}"


def test_delivery_check_distinguished_from_search_results(tmp_path, monkeypatch):
    """delivery_check 映射到 '查快递',与 search_results 的 '查物品' 区分开
    CLI 在 --status 快递中 时自动切 template,文件名也跟着变
    """
    monkeypatch.setenv("SKILLS_DATA_DIR", str(tmp_path))
    payload = {"status": "ok", "data": {"summary": {}, "items": []}, "message": ""}

    r1 = render_page("search_results.html", payload)
    r2 = render_page("delivery_check.html", payload)
    name1 = Path(r1["data"]["output"]).name
    name2 = Path(r2["data"]["output"]).name
    assert name1.startswith("查物品_")
    assert name2.startswith("查快递_")
    assert name1 != name2
