"""HTML 输出路径工具 — 手册 §4.1 合规版本

依据《预置HTML+注入数据指导手册》§4.1 · 输出目录与命名规范(跨Skill通用,2026-07-24 加):

  HTML_DIR = DATA_DIR / f"{SKILL_HTML_NAME}_html"
  文件名 = <command_name>_<YYYYMMDD>_<HHMMSS>[_<N>].html

DATA_DIR 与 calorie_data.db 同级,跟随 SKILLS_DB_PATH 环境变量(fallback D:/.db/)。
HTML 子目录命名:卡路里 = "calorie" → "/.../calorie_html/"

<command_name> 命名约定(v2.4.8 起 · 中文化):
  - 静态 command(如 render_home.py 的 '主页仪表盘'):直接传中文
  - 动态 command(如 food_ranking_{category}):拼接用中文(category 映射见 scripts/_cmd_maps.py)
  - 中文示例:主页仪表盘_20260726_123000.html / 热量趋势_20260726_123000.html
  - 同秒冲突自动追加 _2 / _3 后缀

⭐ 场景 HTML 命名规则(v1.0 · 2026-08-02 用户拍板 · 新场景开发必读):
  文件名 = <场景名>_<类型中文>_<TS>.html
  - 类型中文映射:process→过程 / result→结果 / receipt→回执
  - 例:查档案_结果_20260802_131014.html / 设活动量_回执_20260802_131014.html
  - 一个场景可能多类型(wizard=过程 + 回执),靠类型后缀区分同一场景不同产物
  - 统一用 html_scene_path(skill_dir, 场景名, output_type) 生成,禁止手拼
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
        command: CLI 子命令名(中文化后,例 "主页仪表盘" / "体重记录回执_mock")
        html_dir: 用于检测冲突的目录;默认 cwd
                  (建议显式传 html_dir(skill_dir) 以避免跨进程误判)

    Returns:
        Path: 仅文件名(不含目录),例如 Path("主页仪表盘_20260726_103045.html")
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
        command: CLI 子命令名(中文化,如 "主页仪表盘" / "热量趋势")

    Returns:
        Path: 完整输出路径(目录保证存在),如 .../calorie_html/主页仪表盘_20260726_103045.html
    """
    hd = html_dir(skill_dir, mkdir=True)
    nm = html_name(command, html_dir=hd)
    return hd / nm


# ⭐ 场景 HTML 类型后缀(v1.0 · 2026-08-02 用户拍板)
OUTPUT_TYPE_LABELS = {
    'process': '过程',
    'result':  '结果',
    'receipt': '回执',
}


def html_scene_path(skill_dir, scene_name, output_type):
    """场景 HTML 输出路径:<场景名>_<类型中文>_<TS>.html

    规则(2026-08-02 用户拍板 · 新场景开发必读):
      - 类型中文:process→过程 / result→结果 / receipt→回执
      - 例:查档案_结果_20260802_131014.html / 设活动量_回执_20260802_131014.html
      - 一个场景多类型时靠后缀区分(wizard=过程 + 回执)
      - 所有场景 HTML 生成必须走本函数,禁止手拼 html_path()

    Args:
        skill_dir: Skill 根目录
        scene_name: 场景名(如 "查档案" / "设活动量")
        output_type: 'process' / 'result' / 'receipt'

    Returns:
        Path: .../calorie_html/查档案_结果_20260802_131014.html
    """
    label = OUTPUT_TYPE_LABELS.get(output_type, '')
    command = f"{scene_name}_{label}" if label else scene_name
    return html_path(skill_dir, command)
    nm = html_name(command, html_dir=hd)
    return hd / nm
