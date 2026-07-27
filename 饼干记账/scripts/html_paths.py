"""HTML 输出路径工具 - 同步卡路里 §4.1 规范 (v2.5)

依据《卡路里 v2.4.8 跨Skill HTML 输出规范》(2026-07-24):

  HTML_DIR = DATA_DIR / f"{SKILL_HTML_NAME}_html"
  文件名   = <command_zh>_<YYYYMMDD>_<HHMMSS>[_<N>].html

DATA_DIR 与 biscuit_accountant.db 同级, 跟随 SKILLS_DB_PATH 环境变量
(复用 db.py 的 _find_db_path, fallback D:/.db/)。

HTML 子目录: 卡路里 = "calorie" -> "calorie_html/" ;
            饼干记账 = "biscuit_accountant" -> "biscuit_accountant_html/"

<command_zh> 命名约定(对齐卡路里 v2.4.8 中文化):
  - 静态 command: CLI 名 -> 中文
  - 中文示例: 今日摘要_20260727_123000.html / 收支总览_20260727_123000.html
  - 同秒冲突自动追加 _2 / _3 后缀
"""

import glob
from datetime import datetime
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent.resolve()
SKILL_DIR = _SCRIPT_DIR.parent

SKILL_HTML_NAME = "biscuit_accountant"


COMMAND_NAMES = {
    "summary":   "今日摘要",
    "list":      "查询记录",
    "recent":    "最近记录",
    "search":    "备注搜索",
    "monthly":   "月度汇总",
    "compare":   "周期对比",
    "breakdown": "分类明细",
    "overview":  "收支总览",
    "stats":     "记账统计",
    "help":      "能力速查",
}


LIST_VARIANTS = {
    "date":     "查日期",
    "range":    "查范围",
    "category": "查分类",
    "default":  "查询记录",
}


def list_variant(args) -> str:
    """根据 list 命令的参数选细分中文名"""
    if getattr(args, "date", None):
        return LIST_VARIANTS["date"]
    if getattr(args, "from_date", None) and getattr(args, "to_date", None):
        return LIST_VARIANTS["range"]
    if getattr(args, "category", None):
        return LIST_VARIANTS["category"]
    return LIST_VARIANTS["default"]


def find_db_path() -> Path:
    """复用 db.py 的 _find_db_path (SKILLS_DB_PATH env var + D:/.db fallback)"""
    from db import _find_db_path, DB_FILENAME
    return _find_db_path(SKILL_DIR, DB_FILENAME)


def html_dir(*, mkdir: bool = True) -> Path:
    """返回 HTML 输出根目录 ($DATA_DIR / biscuit_accountant_html/)"""
    db_path = find_db_path()
    html_d = db_path.parent / f"{SKILL_HTML_NAME}_html"
    if mkdir:
        html_d.mkdir(parents=True, exist_ok=True)
    return html_d


def html_name(command: str, html_dir=None) -> Path:
    """生成合规文件名(只返回文件名,不含目录)

    命名格式: <command>_<YYYYMMDD>_<HHMMSS>[_<N>].html
    冲突保护: 同秒内已有 N 个同名文件 -> 追加 _(N+1)
    """
    search_dir = Path(html_dir) if html_dir else Path.cwd()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{command}_{ts}.html"

    existing = glob.glob(str(search_dir / f"{command}_{ts}*.html"))
    if not existing:
        return Path(base)
    n = len(existing) + 1
    return Path(f"{command}_{ts}_{n}.html")


def html_path(command: str) -> Path:
    """一站式: 返回 <HTML_DIR>/<command>_<TS>[_N].html 完整可写路径

    副作用: 会自动创建 HTML_DIR(若不存在)
    """
    hd = html_dir(mkdir=True)
    nm = html_name(command, html_dir=hd)
    return hd / nm


def resolve_command_name(cli_name: str, args=None) -> str:
    """CLI 名 -> 中文名

    Args:
        cli_name: CLI 子命令名 ("summary" / "list" / "monthly" 等)
        args: argparse 解析后的 args(用于 list 变体细分)
    """
    if cli_name == "list" and args is not None:
        return list_variant(args)
    return COMMAND_NAMES.get(cli_name, cli_name)
