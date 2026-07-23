"""render 层测试: 占位符校验 + 9 模板生成"""
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
