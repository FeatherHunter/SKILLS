"""渲染器: HTML 模板注入数据 + CLI 命令构造

原 home_manager.html_render.py (Phase 7 挪包)
提供:
  - render_page(template_name, payload, output_path, message)
  - emit(payload, template_name, output_path, message)
  - build_command(draft, prefix)
  - split_tags(tags)
"""
import json
import os
import shlex
import sys
from datetime import datetime
from pathlib import Path

from ._shared import SHARED_JS, CHARTS_JS

# SKILL_DIR: 从本文件位置向上 3 级 = 居家管家/
SKILL_DIR = Path(__file__).parent.parent.parent
TEMPLATES_DIR = SKILL_DIR / "templates"

# Skill 标识(与 Python 包名一致),用于 HTML 输出子目录
SKILL_SLUG = "home_manager"
SKILL_CN_NAME = "居家管家"
HTML_SUBDIR = f"{SKILL_SLUG}_html"

DATA_PLACEHOLDER = "<!--INJECT-DATA-->"
SHARED_PLACEHOLDER = "<!--SHARED-HELPERS-->"
CHARTS_PLACEHOLDER = "<!--CHARTS-HELPERS-->"

# template → command_cn 静态映射表(原则 12.A 中文前缀)
# help_center 走 12.B 路径,不在此表
TEMPLATE_TO_COMMAND_CN = {
    "search_results.html": "查物品",
    "delivery_check.html": "查快递",
    "add_preview.html": "录物品",
    "item_detail.html": "看物品",
    "list_overview.html": "统物品",
    "inventory_check.html": "盘物品",
    "expiring_alert.html": "查过期",
    "outfit_picker.html": "穿什么",
    "travel_trip.html": "出行清单",
    # ── SM4 统计总览域(T5)──
    "stats/overview.html": "统物品",
    "stats/idle.html": "查闲置",
    "stats/expiring.html": "查过期",
    "stats/inventory_stat.html": "盘点统计",
    # ── SM7 家庭协作域(T8)──
    "family_borrow.html": "借用",
    "family_members.html": "家人档案",
    # ── SM2 空间与位置域(T3)──
    "位置/space_view.html": "空间视图",
    "位置/location_manage.html": "管位置",
    "位置/fixed_spot.html": "固定位",
    "位置/suggest_storage.html": "收纳建议",
    "位置/receipt.html": "位置回执",
    "位置/confirm.html": "位置确认",
    "位置/error.html": "位置错误",
    # ── SM1 物品管理域(T2)──
    "物品/add_form.html": "录物品",
    "物品/receipt.html": "操作回执",
    "物品/error.html": "操作失败",
    "物品/search_list.html": "查物品",
    "物品/detail.html": "看物品",
    "物品/locate.html": "紧急定位",
    "物品/browse.html": "筛选浏览",
    "物品/duplicates.html": "查重复",
    "物品/confirm.html": "确认操作",
    "物品/undo_select.html": "撤销操作",
    "物品/relations.html": "物品关联",
    "物品/tag_manage.html": "管标签",
    "物品/category_manage.html": "管分类",
    "物品/photos.html": "查看照片",
    "物品/photo_wall.html": "照片墙",
    "物品/inventory_round.html": "盘物品",
    "物品/inventory_diff.html": "差异处理",
    "物品/inventory_records.html": "盘点记录",
    "物品/move_checklist.html": "搬家盘点",
    "物品/history.html": "历史",
}


def _fallback_output_root():
    """全局 fallback HTML 输出根:Windows → D:/.db,WSL → /mnt/d/.db
    沿用 home_manager.db._fallback_db_dir 的策略,DB 目录与 HTML 根同级。
    """
    if sys.platform == 'win32':
        return Path('D:/.db')
    d_drive = Path('/mnt/d')
    if d_drive.exists():
        return d_drive / '.db'
    raise RuntimeError(
        'SKILLS_DATA_DIR 未设置,且 D: 盘未挂载到 /mnt/d/。'
        '请设置 SKILLS_DATA_DIR 或 SKILLS_DB_PATH 环境变量。'
    )


def resolve_output_root():
    """env 链解析 HTML 输出根:$SKILLS_DATA_DIR > $SKILLS_DB_PATH > fallback
    (总纲 §原则 12.X env var 优先级)
    """
    env_data = os.environ.get("SKILLS_DATA_DIR")
    if env_data:
        return Path(env_data)
    env_db = os.environ.get("SKILLS_DB_PATH")
    if env_db:
        return Path(env_db)
    return _fallback_output_root()


def _auto_output_path(template_name):
    """根据 template_name 构造自动命名输出路径(原则 12.A / 12.B)
    - 12.A 数据/过程:`<root>/<skill>_html/<command_cn>_<YYYYMMDD>_<HHMMSS>.html`
    - 12.B HELP:`<root>/<skill>_html/<skill 中文名>_HELP_<YYYYMMDD>_<HHMMSS>.html`
    时间戳用本地时间(见 ADR-0001)。冲突直接覆盖(见 SKILL.md §输出位置)。
    """
    root = resolve_output_root()
    out_dir = root / HTML_SUBDIR
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if template_name == "help_center.html":
        # 12.B HELP 命名
        filename = f"{SKILL_CN_NAME}_HELP_{stamp}.html"
    else:
        # 12.A 数据/过程命名
        command_cn = TEMPLATE_TO_COMMAND_CN.get(template_name, template_name.replace(".html", ""))
        filename = f"{command_cn}_{stamp}.html"
    return out_dir / filename


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

    # INJECT-DATA 占位符校验: 必须恰好 1 个
    if html.count(DATA_PLACEHOLDER) != 1:
        return {
            "status": "error",
            "data": {"template": template_name, "placeholder_count": html.count(DATA_PLACEHOLDER)},
            "message": f"模板 {template_name} 必须包含恰好 1 个 {DATA_PLACEHOLDER} 占位符，实际 {html.count(DATA_PLACEHOLDER)} 个",
        }

    # SHARED-HELPERS 占位符校验: 0 或 1 个
    shared_count = html.count(SHARED_PLACEHOLDER)
    if shared_count > 1:
        return {
            "status": "error",
            "data": {"template": template_name, "shared_count": shared_count},
            "message": f"模板 {template_name} {SHARED_PLACEHOLDER} 最多出现 1 次，实际 {shared_count} 次",
        }

    # CHARTS-HELPERS 占位符校验: 0 或 1 个(图表共享组件, T5 创建)
    charts_count = html.count(CHARTS_PLACEHOLDER)
    if charts_count > 1:
        return {
            "status": "error",
            "data": {"template": template_name, "charts_count": charts_count},
            "message": f"模板 {template_name} {CHARTS_PLACEHOLDER} 最多出现 1 次，实际 {charts_count} 次",
        }

    # 先注入共享 JS (如有), 再注入图表组件(如有), 最后注入数据
    if shared_count == 1:
        html = html.replace(SHARED_PLACEHOLDER, SHARED_JS.strip(), 1)
    if charts_count == 1:
        html = html.replace(CHARTS_PLACEHOLDER, CHARTS_JS.strip(), 1)
    payload_text = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = html.replace(DATA_PLACEHOLDER, payload_text, 1)

    if output_path:
        out = Path(output_path)
    else:
        out = _auto_output_path(template_name)
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