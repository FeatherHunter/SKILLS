"""HTML 输出路径工具 — 手册 §4.1 合规版本

依据《预置HTML+注入数据指导手册》§4.1 · 输出目录与命名规范(跨Skill通用,2026-07-24 加):

  HTML_DIR = DATA_DIR / f"{SKILL_HTML_NAME}_html"
  文件名 = <command_name>_<YYYYMMDD>_<HHMMSS>[_<N>].html

DATA_DIR 与 calorie_data.db 同级,跟随 SKILLS_DB_PATH 环境变量(fallback D:/.db/)。
HTML 子目录命名:卡路里 = "calorie" → "/.../calorie_html/"
"""

import glob
from datetime import datetime
from pathlib import Path

from db import find_db_path


SKILL_HTML_NAME = "calorie"


def html_dir(skill_dir, *, mkdir=True):
    """返回 HTML 输出根目录(DATA_DIR / calorie_html/)

    Args:
        skill_dir: Skill 根目录(通常传 Path(__file__).parent.parent)
        mkdir: True 自动创建目录;False 仅返回路径(不创建)

    Returns:
        Path: HTML 子目录绝对路径
    """
    db_path = find_db_path(skill_dir)
    html_d = db_path.parent / f"{SKILL_HTML_NAME}_html"
    if mkdir:
        html_d.mkdir(parents=True, exist_ok=True)
    return html_d


def html_name(command, html_dir=None):
    """生成合规文件名(只返回文件名,不含目录)

    命名格式:<command>_<YYYYMMDD>_<HHMMSS>[_<N>].html
    冲突保护:同秒内已有 N 个同名文件 → 追加 _(N+1)

    Args:
        command: CLI 子命令名(如 home_dashboard / weight_log_receipt)
        html_dir: 用于检测冲突的目录;默认 cwd
                  (建议显式传 html_dir(skill_dir) 以避免跨进程误判)

    Returns:
        Path: 仅文件名(不含目录),例如 Path("home_dashboard_20260724_103045.html")
    """
    search_dir = Path(html_dir) if html_dir else Path.cwd()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{command}_{ts}.html"

    existing = glob.glob(str(search_dir / f"{command}_{ts}*.html"))
    if not existing:
        return Path(base)
    n = len(existing) + 1
    return Path(f"{command}_{ts}_{n}.html")


def html_path(skill_dir, command):
    """一站式:返回 <HTML_DIR>/<command>_<TS>[_N].html 完整可写路径

    副作用:会自动创建 HTML_DIR(若不存在)

    Args:
        skill_dir: Skill 根目录
        command: CLI 子命令名

    Returns:
        Path: 完整输出路径(目录保证存在)
    """
    hd = html_dir(skill_dir, mkdir=True)
    nm = html_name(command, html_dir=hd)
    return hd / nm
