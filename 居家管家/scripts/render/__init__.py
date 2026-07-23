"""渲染器: HTML 模板注入数据 + CLI 命令构造

原 home_manager.html_render.py (Phase 7 挪包)
提供:
  - render_page(template_name, payload, output_path, message)
  - emit(payload, template_name, output_path, message)
  - build_command(draft, prefix)
  - split_tags(tags)
"""
import json
import shlex
from datetime import datetime
from pathlib import Path

# SKILL_DIR: 从本文件位置向上 3 级 = 居家管家/
SKILL_DIR = Path(__file__).parent.parent.parent
TEMPLATES_DIR = SKILL_DIR / "templates"
OUTPUT_DIR = SKILL_DIR / "output"


def render_page(template_name, payload, output_path=None, message=None):
    template_path = TEMPLATES_DIR / template_name
    if not template_path.exists():
        return {
            "status": "error",
            "data": {"template": template_name},
            "message": f"模板不存在: {template_path}",
        }
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        return {
            "status": "error",
            "data": {"template": template_name},
            "message": f"payload 状态校验失败: {payload.get('message') if isinstance(payload, dict) else '非字典类型'}",
        }
    html = template_path.read_text(encoding="utf-8")
    placeholder = "<!--INJECT-DATA-->"
    if html.count(placeholder) != 1:
        return {
            "status": "error",
            "data": {"template": template_name, "placeholder_count": html.count(placeholder)},
            "message": f"模板 {template_name} 必须包含恰好 1 个 {placeholder} 占位符，实际 {html.count(placeholder)} 个",
        }
    payload_text = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = html.replace(placeholder, payload_text, 1)
    if output_path:
        out = Path(output_path)
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = OUTPUT_DIR / f"{template_name.replace('.html', '')}_{stamp}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return {
        "status": "ok",
        "data": {"output": str(out), "template": template_name},
        "message": message or f"HTML 已生成: {out.name}",
    }


def emit(payload, template_name, output_path=None, message=None):
    result = render_page(template_name, payload, output_path, message)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "ok" else 1


def build_command(draft, prefix="python home_manager.py add"):
    parts = shlex.split(prefix)
    mapping = [
        ("--name", "name"),
        ("--category-id", "category_id"),
        ("--location", "location"),
        ("--owner", "owner"),
        ("--quantity", "quantity"),
        ("--price", "price"),
        ("--purchase-date", "purchase_date"),
        ("--expiration-date", "expiration_date"),
        ("--remark", "remark"),
        ("--tags", "tags"),
        ("--photo", "photo"),
        ("--location-status", "location_status"),
    ]
    for flag, key in mapping:
        value = draft.get(key)
        if value is None or value == "":
            continue
        if key == "tags" and isinstance(value, list):
            value = ",".join(str(t).strip() for t in value if str(t).strip())
        parts.extend([flag, str(value)])
    return " ".join(shlex.quote(p) for p in parts)


def split_tags(tags):
    if isinstance(tags, list):
        return [str(t).strip() for t in tags if str(t).strip()]
    return [t.strip() for t in str(tags or "").split(",") if t.strip()]