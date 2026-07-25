"""备忘录 HTML 注入器(私有 · v1.1.0)

历史:
  v1.0.6: 抽取到 _shared/injector.py(跨 Skill 共享)
  v1.0.7: 加冲突保护 + 命名规则明确化
  v1.0.9: 删除跨 Skill 共享 · 但保留所有增强 · 降级为备忘录私有
          (f304e4f commit "清理已沉淀的旧模板目录" 把 _shared/ 删了)

为什么私有:
  - 跨 session 跨 commit 的依赖共享会被清理(清理者看不到下游依赖)
  - DRY 共享值得做,但需要 git submodule 或独立 package · 不是简单目录
  - 当前"简单目录"模式不可靠

设计要点(承袭《预置HTML并注入数据指导手册》§8):
  - 占位符 <!--INJECT-DATA--> 全文件恰好 1 次;不满足则 raise ValueError
  - </ 转义(防 JSON 含 </script> 提前闭合)
  - 文件名格式 <command_name>_<YYYYMMDD>_<HHMMSS>[_<N>].html
  - 同秒冲突保护:输出 <name>_<ts>.html 已存在 → 自动 _2 / _3 ...

公开 API:
  - inject_html(template_text, payload, placeholder='<!--INJECT-DATA-->') -> str
  - write_output(out_dir, name, html, ts=None) -> str  (out_dir 可为 str 或 Path)
  - render(payload, template_path, name='memo', out_dir=None) -> str
"""
import json
from datetime import datetime
from pathlib import Path


# 占位符默认(承袭 v1.0.6)
DEFAULT_PLACEHOLDER = '<!--INJECT-DATA-->'


def inject_html(template_text, payload, placeholder=DEFAULT_PLACEHOLDER):
    """读模板 + 注入 window.__DATA__ + 校验占位符唯一。

    Args:
        template_text: HTML 模板字符串(已 read_text)
        payload: dict,会被 JSON 序列化注入到 window.__DATA__
        placeholder: 默认 '<!--INJECT-DATA-->';不允许为空或重复

    Returns:
        str: 注入后的 HTML 文本

    Raises:
        ValueError: 占位符数量 != 1
    """
    if not placeholder:
        raise ValueError("placeholder 不能为空")
    count = template_text.count(placeholder)
    if count != 1:
        raise ValueError(
            f"占位符 '{placeholder}' 出现 {count} 次,期望 1"
        )
    # </ 转义(防 JSON 含 </script> 提前闭合 script 块)
    safe_payload = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    inject_str = f'<script>window.__DATA__ = {safe_payload};</script>'
    return template_text.replace(placeholder, inject_str, 1)


def write_output(out_dir, name, html, ts=None):
    """把 HTML 写到 out_dir/<name>_<YYYYMMDD>_<HHMMSS>[_<N>].html,返回路径。

    Args:
        out_dir: 输出目录(str 或 Path)· 不存在会自动 mkdir
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
    # 冲突保护(承袭 v1.0.7): 同秒内多次生成自动 _2 / _3
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
        template_path: 模板文件路径(str 或 Path)
        name: 输出文件名(name_*.html)
        out_dir: 输出目录;默认 = 模板父目录的 output/

    Returns:
        str: 输出文件路径
    """
    template_path = Path(template_path)
    if out_dir is None:
        out_dir = template_path.parent.parent / "output"
    template = template_path.read_text(encoding="utf-8")
    injected = inject_html(template, payload)
    return write_output(out_dir, name, injected)
