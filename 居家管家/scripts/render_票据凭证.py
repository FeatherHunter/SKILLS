"""SM6 票据凭证域 · 渲染入口(render_{域} · 隔离契约文件集)

职责: 域 HTML 渲染的对外入口, 复用公共 render 注入管线(只调不改)。
      HTML 输出遵循总纲 12.A 命名: <root>/home_manager_html/<command_cn>_<YYYYMMDD>_<HHMMSS>.html
"""
import sys
from pathlib import Path

_scripts_dir = Path(__file__).parent.resolve()
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from render import render_page, resolve_output_root  # noqa: E402

from 票据凭证.payloads import (  # noqa: E402
    purchase_payload, warranty_payload, certificates_payload, accounts_payload,
    TEMPLATE_CN, SCENE_META, VERSION,
)


def render(template_name, payload, output_path=None):
    """域渲染: template_name ∈ 票据凭证/*.html"""
    command_cn = TEMPLATE_CN.get(template_name, "票据凭证")
    if output_path is None:
        from datetime import datetime
        out_dir = resolve_output_root() / "home_manager_html"
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(out_dir / f"{command_cn}_{stamp}.html")
    return render_page(template_name, payload, output_path)


__all__ = [
    "render", "render_page", "resolve_output_root",
    "purchase_payload", "warranty_payload", "certificates_payload", "accounts_payload",
    "TEMPLATE_CN", "SCENE_META", "VERSION",
]
