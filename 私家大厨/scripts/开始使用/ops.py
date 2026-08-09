# ops.py - 私家大厨 · 开始使用域(setup-1 首次使用 4 步向导)数据层
#
# 职责: 环境检测(缺失自动安装) / 环境变量持久化引导 / 建库(幂等 · 17 表判定) / 向导与回执 payload
# 隔离契约: 本域只动 scripts/开始使用/ + templates/开始使用/ + render_开始使用 + scenes/开始使用.yaml + tests/test_开始使用.py
#
# G1 收敛(2026-08-07): 4 步向导 = 环境检测 → 环境变量配置 → 建库(幂等) → 完成回执
#   示例数据/偏好档案砍除(空库直接录第一道菜即 onboarding);老库仅提示迁移不自动迁移
import os
import sys
import platform
import sqlite3
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_config import DB_PATH
from output_config import get_output_root

# 17 张业务表齐全 = 老库已初始化(与 init_db.py DDL 对应)
EXPECTED_TABLES = 17

# 输出目录 env 优先级与 output_config.ENV_ORDER 对齐(SKILLS_DATA_DIR > CHEF_OUTPUT_DIR)
OUTPUT_ENV_KEYS = ("SKILLS_DATA_DIR", "CHEF_OUTPUT_DIR")
DB_ENV_KEY = "SKILLS_DB_PATH"


def _is_wsl() -> bool:
    """WSL 检测: 环境变量 WSL_DISTRO_NAME 存在,或 /proc/version 含 microsoft"""
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    if sys.platform.startswith("win"):
        return False
    try:
        return "microsoft" in Path("/proc/version").read_text(
            encoding="utf-8", errors="replace").lower()
    except OSError:
        return False


def _dir_writable(d: Path) -> bool:
    """目录可写探针(创建 + 写删临时文件)"""
    try:
        d.mkdir(parents=True, exist_ok=True)
        probe = d / f".write_probe_{os.getpid()}"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _module_ok(name: str) -> bool:
    import importlib.util
    return importlib.util.find_spec(name) is not None


def _table_count() -> int:
    """当前 DB 的业务表数量(17 表齐全 = 已初始化;不建库不写库,只读)"""
    if not DB_PATH.exists():
        return 0
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        try:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            return len(rows)
        finally:
            conn.close()
    except sqlite3.OperationalError:
        return 0


# ── 步骤 1 · 环境检测 ──────────────────────────────────────────────────

def env_check_payload() -> dict:
    """环境检测 → payload(OS/Python/pyyaml/DB 状态/输出目录可写/env 现状)

    缺失项进 missing(供「自动安装: 装前展示命令 → 确认 → 执行 → 重检」)
    """
    os_name = "WSL" if _is_wsl() else platform.system()
    py_ver = f"{platform.python_version()} ({platform.architecture()[0]})"
    pyyaml_ok = _module_ok("yaml")

    try:
        out_root = str(get_output_root())
        out_err = None
    except RuntimeError as e:
        out_root = None
        out_err = str(e)

    db_exists = DB_PATH.exists()
    tables = _table_count()
    missing = []
    if not pyyaml_ok:
        missing.append("pyyaml")

    return {
        "os": os_name,
        "python": py_ver,
        "pyyaml": pyyaml_ok,
        "db_path": str(DB_PATH),
        "db_exists": db_exists,
        "db_tables": tables,
        "db_initialized": tables >= EXPECTED_TABLES,
        "output_root": out_root,
        "output_root_error": out_err,
        "output_dir_writable": _dir_writable(Path(out_root)) if out_root else False,
        "env": {
            DB_ENV_KEY: os.environ.get(DB_ENV_KEY) or "(未设置,走默认)",
            "SKILLS_DATA_DIR": os.environ.get("SKILLS_DATA_DIR") or "(未设置)",
            "CHEF_OUTPUT_DIR": os.environ.get("CHEF_OUTPUT_DIR") or "(未设置,走默认)",
        },
        "missing": missing,
        "status": "ok",
    }


def install_cmds_payload() -> dict:
    """自动安装命令(步骤 1 缺失时: 装前展示 → 确认 → 执行 → 重检)

    - pyyaml: pip install --user pyyaml(用户目录,不碰系统环境)
    - python: 本技能以 Python 运行,进程内必存在;若目标机缺失由用户按系统安装(Windows 建议用户目录)
    """
    pyyaml_missing = not _module_ok("yaml")
    return {
        "python": {
            "detected": True,
            "note": "Python 已检测到(本技能以 Python 运行)",
        },
        "pyyaml": {
            "detected": not pyyaml_missing,
            "cmd": f"{sys.executable} -m pip install --user pyyaml" if pyyaml_missing else None,
            "note": "pyyaml 缺失时执行(用户目录安装);已存在则跳过",
        },
        "status": "ok",
    }


# ── 步骤 2 · 环境变量配置(持久化)──────────────────────────────────────

def _default_db_dir() -> str:
    return "D:/.db" if sys.platform == "win32" else "/mnt/d/.db"


def _default_out_dir() -> str:
    return "D:/CookHub" if sys.platform == "win32" else "/mnt/d/CookHub"


def env_persist_payload() -> dict:
    """环境变量持久化引导(步骤 2 · 非阻塞)

    - Windows: setx(注意: 当前进程不生效,建库/输出用目标路径而非已改 env)
    - Linux/WSL: export 追加 ~/.bashrc
    - 已设置的变量不重复生成命令;全部已设置 → configured=True
    """
    is_win = sys.platform == "win32"
    targets = [
        {"key": DB_ENV_KEY, "value": os.environ.get(DB_ENV_KEY) or _default_db_dir()},
        {"key": "SKILLS_DATA_DIR", "value": os.environ.get("SKILLS_DATA_DIR") or _default_out_dir()},
    ]
    commands = []
    missing = []
    for t in targets:
        if os.environ.get(t["key"]):
            continue
        missing.append(t["key"])
        if is_win:
            commands.append(f'setx {t["key"]} "{t["value"]}"')
        else:
            commands.append(f'echo \'export {t["key"]}="{t["value"]}"\' >> ~/.bashrc')

    return {
        "platform": "win" if is_win else ("wsl" if _is_wsl() else "posix"),
        "missing": missing,
        "configured": not missing,
        "commands": commands,
        "note": "Windows 的 setx 不作用于当前进程,执行后请新开终端;未生效期间建库/输出直用目标路径",
        "legacy_chef_output_dir": os.environ.get("CHEF_OUTPUT_DIR") or "(未设置,走默认)",
        "status": "ok",
    }


# ── 步骤 3 · 建库(幂等 · 17 表判定)────────────────────────────────────

def init_payload() -> dict:
    """建库(幂等,可重试)

    - 老库(17 表齐全) → 视为已初始化,跳过建库,仅提示迁移命令,不自动迁移
    - 无库/空库/部分库 → init_db()(CREATE TABLE IF NOT EXISTS 幂等补全)
    """
    tables = _table_count()
    if tables >= EXPECTED_TABLES:
        return {
            "status": "ok",
            "initialized": True,
            "skipped": f"老库已初始化({tables} 表齐全),跳过建库",
            "db_path": str(DB_PATH),
            "tables": tables,
            "migration_hint": "老库仅提示迁移,不自动迁移: 需补的迁移见 scripts/migrations/*.sql(手动执行,勿直接跑 init_db 重建)",
        }

    try:
        import contextlib
        import io as _io
        import init_db
        buf = _io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                init_db.init_db()
        except Exception as e:
            return {
                "status": "error",
                "error": "init_failed",
                "reason": f"{e}({buf.getvalue().strip()[-200:]})",
                "suggest": "检查数据库目录可写性后重试",
            }
    except Exception as e:
        return {
            "status": "error",
            "error": "init_failed",
            "reason": str(e),
            "suggest": "检查数据库目录可写性后重试",
        }

    new_tables = _table_count()
    return {
        "status": "ok",
        "initialized": new_tables >= EXPECTED_TABLES,
        "created": True,
        "skipped": None,
        "db_path": str(DB_PATH),
        "tables": new_tables,
        "migration_hint": None,
    }
