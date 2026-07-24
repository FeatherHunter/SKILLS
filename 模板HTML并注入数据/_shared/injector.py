"""共享 HTML 注入器

被多个 Skill 的 _render.py 复用,避免每 Skill 各自写 _inject。
使用方式:
    sys.path.insert(0, "../../模板HTML并注入数据/_shared")
    from injector import inject_html, write_output

v1.0.5 (2026-07-24) 规范:
  **命名规则**(承袭实践,《手册》§7 同步):
    <command_name>_<YYYYMMDD>_<HHMMSS>[_<N>].html
    - command_name: CLI 子命令名(如 memo_query / sync_report / wish_plan ...)
    - YYYYMMDD_HHMMSS: 本地时间
    - _<N>: 同秒内多次生成的冲突保护(N=2/3/4 ...)

  **输出目录**(由调用方决定,本模块不预设):
    通常 = DB_PATH.parent / f"{SKILL_HTML_NAME}_html"
    例:/mnt/d/.db/memo_html/  (备忘录 · SKILL_HTML_NAME="memo")
    跨 skill 共用 SKILLS_DB_PATH 时通过 skill 子目录隔离

设计要点(来自《预置HTML并注入数据指导手册》§8):
  - 占位符 <!--INJECT-DATA--> 全文件恰好 1 次;不满足则 raise
  - </ 转义(防 JSON 含 </script> 提前闭合)
  - 生成副本到 out_dir,绝不修改原模板

历史:
  v1.0.0 (2026-07-24) · 来自备忘录 memo_render.py 抽取
  v1.0.5 (2026-07-24) · 命名规则明确化 + 冲突保护
"""
import json
import sys
from datetime import datetime
from pathlib import Path


def inject_html(template_text, payload, placeholder='<!--INJECT-DATA-->'):
    """读模板 + 注入 window.__DATA__ + 校验占位符唯一。

    Args:
        template_text: 模板 HTML 文本(已 read_text)
        payload: dict,会被 JSON 序列化注入到 window.__DATA__
        placeholder: 默认 '<!--INJECT-DATA-->';不允许为空或重复

    Returns:
        str: 注入后的 HTML 文本

    Raises:
        ValueError: 占位符数量 ≠ 1
    """
    if not placeholder:
        raise ValueError("placeholder 不能为空")
    count = template_text.count(placeholder)
    if count != 1:
        raise ValueError(f"占位符 '{placeholder}' 出现 {count} 次,期望 1")
    safe_payload = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    inject_str = f'<script>window.__DATA__ = {safe_payload};</script>'
    return template_text.replace(placeholder, inject_str, 1)


def write_output(out_dir, name, html, ts=None):
    """把 HTML 写到 out_dir/name_<YYYYMMDD>_<HHMMSS>[_<N>].html,返回路径。

    Args:
        out_dir: 输出目录(Path)
        name: 文件名前缀(如 'memo_query')
        html: 注入后的 HTML 文本
        ts: 可选时间戳字符串(测试用),默认 now()

    Returns:
        str: output 文件路径
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if ts is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"{name}_{ts}.html"
    # 冲突保护:同秒内多次生成自动追加 _2 / _3 ...
    if out_path.exists():
        n = 2
        while True:
            candidate = out_dir / f"{name}_{ts}_{n}.html"
            if not candidate.exists():
                out_path = candidate
                break
            n += 1
    out_path.write_text(html, encoding="utf-8")
    return str(out_path)


def render(payload, template_path, name="memo", out_dir=None):
    """一站式:读模板 + 注入 + 输出。

    Args:
        payload: 注入数据
        template_path: 模板文件路径
        name: 输出文件名(name_*.html)
        out_dir: 输出目录,默认与模板同级的 output/(已废弃,调用方应传入 SKILLS_DB_PATH 关联路径)

    Returns:
        str: 输出文件路径
    """
    template_path = Path(template_path)
    if out_dir is None:
        # v1.0.5 之前默认 fallback · 新代码应显式传 out_dir
        out_dir = template_path.parent.parent / "output"
    template = template_path.read_text(encoding="utf-8")
    injected = inject_html(template, payload)
    return write_output(out_dir, name, injected)