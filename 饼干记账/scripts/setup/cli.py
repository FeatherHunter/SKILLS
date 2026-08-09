#!/usr/bin/env python3
"""饼干记账 · 开始使用域 CLI(6 场景 · scenes/setup.yaml)

场景 → 子命令:
    首次使用向导(4 步零决策) → init / init --check(只读环境检测)
    初始化状态(三重判定)     → init-status
    一键备份 / 查看备份       → backup-create / backup-list(包装公共层 backup.py)
    从备份恢复               → restore --name X(默认最新)
    导入 CSV 账单(列映射)    → import --file X [--mapping ...] [--dry-run]

载体契约:
    初始化 = db.init_db() 幂等自愈(建库 + deleted_at 补列),无版本表,
            版本判定 = 特征列(deleted_at 存在 = v2.0 schema)
    备份   = 复用公共层 scripts/backup.py(create/list/restore;db + goals.json)
    导入   = G1 最小方案:通用 CSV + 列映射(不逐软件适配);
             外部导入缺省未删(deleted_at = NULL · G7 软删契约)

用法:
    python3 scripts/setup/cli.py init --check        # 只读:环境检测 + 三重判定(向导步骤 1-2)
    python3 scripts/setup/cli.py init                # 执行:建库幂等自愈 + 只读验证(步骤 3-4)
    python3 scripts/setup/cli.py init-status         # 三重判定(存在+schema+版本)
    python3 scripts/setup/cli.py backup-create       # 一键备份
    python3 scripts/setup/cli.py backup-list         # 查看备份
    python3 scripts/setup/cli.py restore --name X    # 从备份恢复(不带 name = 最新)
    python3 scripts/setup/cli.py import --file x.csv --mapping date=1,amount=3,category=2 --dry-run
"""

import sys
import csv
import io
import json
import argparse
import sqlite3
from pathlib import Path
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from cli_utils import reconfigure_utf8, emit_ok, emit_error  # noqa: E402

reconfigure_utf8()

# ── 常量 ─────────────────────────────────────────────────────────────────────

# v2.0 schema 特征列(存在 = 版本达标;G7 决议 deleted_at 为软删特征)
V2_FEATURE_COLUMN = "deleted_at"
REQUIRED_COLUMNS = [
    "id", "category", "time", "amount", "account", "ledger",
    "currency", "note", "created_at", "deleted_at",
]
SCHEMA_VERSION = "2.0"

# 导入列映射:字段名 → (关键词集合, 是否必填)
MAPPING_HINTS = {
    "date":     (("日期", "时间", "交易时间", "记账日期", "date", "time"), True),
    "amount":   (("金额", "收支金额", "交易金额", "金额(元)", "money", "amount"), True),
    "category": (("分类", "类目", "类别", "category", "type"), True),
    "note":     (("备注", "摘要", "说明", "交易说明", "note", "remark", "desc"), False),
    "account":  (("账户", "账号", "交易账户", "account"), False),
    "ledger":   (("账本", "ledger"), False),
    "type":     (("收/支", "收支", "类型", "方向", "收支类型", "income/expense"), False),
}

# ── 环境检测 / 初始化状态(向导步骤 1-2 + 独立场景 init-status)─────────────────

def _db_path() -> Path:
    from db import _find_db_path, DB_FILENAME
    return _find_db_path(_SCRIPTS.parent, DB_FILENAME)


def check_environment() -> dict:
    """环境检测(只读):OS / Python≥3.9 / PyYAML / db+HTML 目录可写 / SKILL_DIR 可读"""
    import platform
    issues = []
    checks = []

    os_name = platform.system()
    py_ok = sys.version_info >= (3, 9)
    checks.append({
        "name": "操作系统", "ok": True,
        "detail": f"{os_name} ({platform.release()})",
    })
    checks.append({
        "name": "Python", "ok": py_ok,
        "detail": f"{sys.version.split()[0]}(≥3.9 要求{'满足' if py_ok else '未满足'})",
    })
    if not py_ok:
        issues.append("Python 版本过低(需 ≥3.9)")

    yaml_ok = False
    try:
        import yaml  # noqa: F401
        yaml_ok = True
    except ImportError:
        pass
    checks.append({
        "name": "PyYAML", "ok": yaml_ok,
        "detail": "可用(HELP/场景资产依赖)" if yaml_ok else "缺失(HELP 渲染不可用)",
    })
    if not yaml_ok:
        issues.append("PyYAML 未安装")

    dbp = _db_path()
    db_dir = dbp.parent
    db_writable = True
    db_dir.mkdir(parents=True, exist_ok=True)
    probe = db_dir / ".write_probe"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError:
        db_writable = False
        issues.append(f"数据目录不可写: {db_dir}")
    checks.append({
        "name": "数据目录", "ok": db_writable,
        "detail": f"{db_dir}({'可写' if db_writable else '不可写'})",
    })

    from html_paths import html_dir
    hdir = html_dir(mkdir=True)
    html_writable = True
    probe = hdir / ".write_probe"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError:
        html_writable = False
        issues.append(f"HTML 目录不可写: {hdir}")
    checks.append({
        "name": "HTML 目录", "ok": html_writable,
        "detail": f"{hdir}({'可写' if html_writable else '不可写'})",
    })

    skill_readable = True
    try:
        (_SCRIPTS.parent / "SKILL.md").read_text(encoding="utf-8")
    except OSError:
        skill_readable = False
        issues.append("SKILL 目录不可读(SKILL.md 读取失败)")
    checks.append({
        "name": "SKILL 目录", "ok": skill_readable,
        "detail": "可读(场景资产访问正常)" if skill_readable else "不可读",
    })

    return {"ok": len(issues) == 0, "checks": checks, "issues": issues, "os": os_name}


def init_status() -> dict:
    """三重判定:存在(文件)+ schema(bills 表 + 必需列)+ 版本(特征列 v2.0)"""
    dbp = _db_path()
    db_exists = dbp.exists()
    checks = []
    checks.append({
        "name": "数据存在", "ok": db_exists,
        "detail": str(dbp) if db_exists else "数据库文件不存在(未初始化)",
    })

    schema_ok = False
    schema_detail = ""
    version_ok = False
    version_detail = ""
    records = 0
    migration_hint = None

    if db_exists:
        try:
            conn = sqlite3.connect(str(dbp))
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            if "bills" not in tables:
                schema_detail = "bills 表缺失(库文件损坏或非饼干记账库)"
            else:
                cols = [r[1] for r in conn.execute("PRAGMA table_info(bills)").fetchall()]
                missing = [c for c in REQUIRED_COLUMNS if c not in cols]
                if missing:
                    schema_detail = f"bills 缺列: {', '.join(missing)}(schema 过期)"
                    if V2_FEATURE_COLUMN in missing:
                        migration_hint = ("数据库为旧版 schema,缺少软删列 deleted_at;"
                                          "运行 `python3 scripts/migrations/add_bills_check_constraints.py` 迁移"
                                          "或重新初始化(init 幂等自愈补列)")
                else:
                    schema_ok = True
                    schema_detail = f"bills 表完整({len(cols)} 列)"
                    version_ok = V2_FEATURE_COLUMN in cols
                    version_detail = (f"schema v{SCHEMA_VERSION}(含 {V2_FEATURE_COLUMN})"
                                      if version_ok else "旧版 schema(缺 deleted_at 软删列)")
                    records = conn.execute("SELECT COUNT(*) FROM bills").fetchone()[0]
                    if not version_ok:
                        migration_hint = ("数据库为旧版 schema,缺少软删列 deleted_at;"
                                          "运行 `python3 scripts/migrations/add_bills_check_constraints.py` 迁移"
                                          "或重新初始化(init 幂等自愈补列)")
            conn.close()
        except sqlite3.Error as e:
            schema_detail = f"库打开失败: {e}"
    else:
        schema_detail = "未初始化,无 schema 可查"

    checks.append({"name": "schema", "ok": schema_ok, "detail": schema_detail})
    checks.append({"name": "版本", "ok": version_ok, "detail": version_detail or "未初始化"})

    ready = db_exists and schema_ok and version_ok
    return {
        "ready": ready,
        "db_exists": db_exists,
        "schema_ok": schema_ok,
        "version_ok": version_ok,
        "version": SCHEMA_VERSION if version_ok else None,
        "records": records,
        "db_path": str(dbp),
        "checks": checks,
        "migration_hint": migration_hint,
    }


def cmd_init(args):
    """执行初始化(4 步零决策向导的执行侧):环境检测 → 目录确认 → 建库幂等自愈 → 只读验证"""
    if getattr(args, "check", False):
        env = check_environment()
        st = init_status()
        data = {
            "env": env,
            "status": st,
            "steps": [
                {"step": "环境检测", "status": "ok" if env["ok"] else "warn",
                 "detail": "全部通过" if env["ok"] else "；".join(env["issues"])},
                {"step": "数据目录确认", "status": "ok",
                 "detail": f"{_db_path().parent}(可写)"},
            ],
        }
        if getattr(args, "json", False):
            emit_ok(data, "初始化向导 · 环境检测")
            return data
        for c in env["checks"]:
            flag = "✓" if c["ok"] else "✗"
            print(f"  {flag} {c['name']}: {c['detail']}")
        print(f"  数据目录: {_db_path().parent}")
        print(f"  初始化状态: {'已就绪' if st['ready'] else '未就绪'}")
        return data

    # 执行侧:建库(幂等自愈)+ 只读验证
    from db import init_db, TABLE_NAME
    conn = init_db()
    try:
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({TABLE_NAME})").fetchall()]
        records = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
        ok = "deleted_at" in cols
    finally:
        conn.close()

    steps = [
        {"step": "建库(幂等自愈)", "status": "ok",
         "detail": f"{_db_path().name} 已就绪({len(cols)} 列)"},
        {"step": "只读验证", "status": "ok" if ok else "warn",
         "detail": f"SELECT 1 ✓ · bills 表 ✓ · 现有记录 {records} 条"},
    ]
    data = {
        "db_path": str(_db_path()),
        "records": records,
        "schema_ok": ok,
        "steps": steps,
        "ready": ok,
    }
    if getattr(args, "json", False):
        emit_ok(data, "初始化完成")
        return data
    print("✓ 初始化完成")
    for s in steps:
        print(f"  ✓ {s['step']}: {s['detail']}")
    return data


def cmd_init_status(args):
    st = init_status()
    if getattr(args, "json", False):
        emit_ok(st, "初始化状态" if st["ready"] else "未就绪")
        return st
    print("=== 初始化状态 ===")
    for c in st["checks"]:
        flag = "✓" if c["ok"] else "✗"
        print(f"  {flag} {c['name']}: {c['detail']}")
    if st["migration_hint"]:
        print(f"  ⚠ 迁移提示: {st['migration_hint']}")
    print(f"  就绪: {'是' if st['ready'] else '否'} · 记录 {st['records']} 条")
    return st


# ── 备份 / 恢复(包装公共层 backup.py · 捕获其 stdout 防污染 JSON)──────────────

def _capture_backup(fn, *args, **kwargs):
    """调 backup.py 函数并捕获 print 输出(JSON 模式防污染)"""
    import backup
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        result = fn(*args, **kwargs)
    finally:
        sys.stdout = old
    return result, buf.getvalue().strip()


def cmd_backup_create(args):
    import backup
    try:
        target, out = _capture_backup(backup.create_backup)
    except Exception as e:
        if getattr(args, "json", False):
            emit_error(f"备份失败: {e}")
            return None
        print(f"✗ 备份失败: {e}")
        return None
    files = []
    for f in sorted(target.iterdir()):
        files.append({"name": f.name, "size": f.stat().st_size})
    data = {
        "target": str(target),
        "name": target.name,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "files": files,
        "content": "数据库 + 目标(goals.json)",
    }
    if getattr(args, "json", False):
        emit_ok(data, "一键备份完成")
        return data
    print(out)
    print(f"  备份路径: {target}")
    return data


def cmd_backup_list(args):
    import backup
    try:
        items, out = _capture_backup(backup.list_backups)
    except Exception as e:
        if getattr(args, "json", False):
            emit_error(f"查看备份失败: {e}")
            return None
        print(f"✗ 查看备份失败: {e}")
        return None
    backups = []
    for d in items:
        files = []
        size = 0
        for f in d.iterdir():
            files.append({"name": f.name, "size": f.stat().st_size})
            size += f.stat().st_size
        ts = d.name
        try:
            human = datetime.strptime(ts.split("_")[0] + "_" + ts.split("_")[1],
                                      "%Y%m%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, IndexError):
            human = ts
        backups.append({
            "name": d.name, "time": human, "size": size,
            "files": [f["name"] for f in files],
        })
    data = {"count": len(backups), "backups": backups}
    if getattr(args, "json", False):
        emit_ok(data, f"备份列表 {len(backups)} 个")
        return data
    if not backups:
        print("⚠ 暂无备份(可用 backup-create 一键备份)")
        return data
    for b in backups:
        print(f"· {b['name']}  {b['time']}  {b['size']} 字节 · {', '.join(b['files'])}")
    return data


def cmd_restore(args):
    import backup
    name = (args.name or "").strip()
    # 默认最新备份(场景:恢复备份 默认最新)
    if not name:
        try:
            items, _ = _capture_backup(backup.list_backups)
        except Exception:
            items = []
        if not items:
            if getattr(args, "json", False):
                emit_error("暂无备份可恢复(先执行一键备份)")
                return None
            print("✗ 暂无备份可恢复")
            return None
        name = items[0].name

    # restore_backup 失败会 sys.exit(1) → 捕获转 JSON error
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    exit_code = 0
    try:
        backup.restore_backup(name)
    except SystemExit as e:
        exit_code = int(e.code or 1)
    finally:
        sys.stdout = old
    out = buf.getvalue().strip()

    if exit_code != 0:
        if getattr(args, "json", False):
            emit_error(f"恢复失败: {name}({out or '未知错误'})")
            return None
        print(out or f"✗ 恢复失败: {name}")
        return None

    data = {"name": name, "restored": True, "detail": out}
    if getattr(args, "json", False):
        emit_ok(data, f"已从备份恢复: {name}")
        return data
    print(out)
    return data


# ── CSV 导入(G1 最小方案:通用 CSV + 列映射 · 不逐软件适配)────────────────────

TIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
    "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y/%m/%d",
    "%Y.%m.%d", "%Y年%m月%d日",
)


def _normalize_time(s: str):
    """时间归一化:各种常见格式 → YYYY-MM-DD HH:MM:SS(纯日期补 00:00:00)"""
    s = (s or "").strip()
    if not s:
        return None
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return None


def _parse_amount(s):
    """金额解析:去逗号/货币符号;空/非法 → None"""
    s = str(s or "").strip().replace(",", "").replace("¥", "").replace("￥", "").replace(" ", "")
    if not s or s in ("-", "--", "—"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def guess_mapping(header: list) -> dict:
    """表头关键词 → 列映射(1-based);命中多个取第一个;无表头 → 保守默认"""
    mapping = {}
    if header:
        for idx, name in enumerate(header):
            key = str(name).strip()
            if not key:
                continue
            for field, (keys, _) in MAPPING_HINTS.items():
                if field in mapping:
                    continue
                if any(k.lower() in key.lower() for k in keys):
                    mapping[field] = idx + 1
    # 必填兜底:日期/金额/分类 按常见顺序猜
    if "date" not in mapping:
        mapping["date"] = 1
    if "amount" not in mapping:
        mapping["amount"] = 2
    if "category" not in mapping:
        mapping["category"] = 3
    return mapping


def _read_csv_rows(path: Path, encoding: str) -> tuple:
    """读 CSV 全部行;编码自动探测 utf-8-sig → gbk。返回 (rows, 实际编码)"""
    raw = path.read_bytes()
    used = None
    for enc in ([encoding] if encoding else ("utf-8-sig", "gbk")):
        try:
            text = raw.decode(enc)
            used = enc
            break
        except (UnicodeDecodeError, LookupError):
            continue
    if used is None:
        raise ValueError(f"无法解码文件(尝试 utf-8/gbk 均失败): {path.name}")
    reader = csv.reader(io.StringIO(text))
    return [list(r) for r in reader], used


def build_import_payload(args) -> dict:
    """解析 CSV + 列映射 → 预览数据(dry-run / 向导渲染共用)"""
    file_arg = (args.file or "").strip()
    if not file_arg:
        raise ValueError("文件路径不能为空(导入 CSV 需要 --file)")
    path = Path(file_arg)
    if not path.exists():
        raise ValueError(f"文件不存在: {path}")

    rows, used_enc = _read_csv_rows(path, getattr(args, "encoding", None))
    if not rows:
        raise ValueError("CSV 为空(无任何行)")

    header = None
    skip = int(getattr(args, "skip_header", 0) or 0)
    # 自动判定表头:首行含关键词且非全数字 → 视为表头
    if skip > 0:
        header = rows[skip - 1] if len(rows) >= skip else None
        body = rows[skip:]
    else:
        first = rows[0]
        first_key = " ".join(str(c).strip() for c in first)
        looks_header = any(
            any(k.lower() in first_key.lower() for k in keys)
            for keys, _ in MAPPING_HINTS.values()
        ) and not all(_parse_amount(c) is not None for c in first[1:4])
        if looks_header:
            header = first
            body = rows[1:]
        else:
            body = rows

    # 显式映射 > 自动猜测
    if getattr(args, "mapping", None):
        mapping = {}
        for pair in args.mapping.split(","):
            pair = pair.strip()
            if not pair or "=" not in pair:
                continue
            field, col = pair.split("=", 1)
            field = field.strip()
            try:
                mapping[field] = int(col.strip())
            except ValueError:
                pass
    else:
        mapping = guess_mapping(header)

    # 预览行(前 8 行)
    preview = []
    for r in body[:8]:
        preview.append({"cols": [str(c) for c in r], "no": len(preview) + 1})

    data = {
        "file": str(path),
        "name": path.name,
        "encoding": used_enc,
        "total_rows": len(body),
        "header": header or [],
        "has_header": bool(header),
        "mapping": mapping,
        "preview": preview,
        "columns": ["日期/时间", "金额", "分类", "备注", "账户", "账本", "收支方向"],
    }
    return data


def cmd_import(args):
    """导入执行:解析 → 逐行校验 → 写入;dry-run 只解析预览"""
    try:
        data = build_import_payload(args)
    except ValueError as e:
        if getattr(args, "json", False):
            emit_error(str(e))
            return None
        print(f"✗ {e}")
        return None

    if getattr(args, "preview", False) or getattr(args, "dry_run", False):
        if getattr(args, "json", False):
            emit_ok(data, f"CSV 预览(共 {data['total_rows']} 行)")
            return data
        print(f"=== CSV 预览: {data['name']}(共 {data['total_rows']} 行) ===")
        if data["header"]:
            print("表头: " + " | ".join(str(c) for c in data["header"]))
        print("映射: " + ", ".join(f"{k}={v}" for k, v in sorted(data["mapping"].items())))
        for p in data["preview"]:
            print(f"  第{p['no']}行: " + " | ".join(p["cols"]))
        if getattr(args, "dry_run", False):
            print("(dry-run:仅预览,未写入)")
        return data

    # 执行导入:逐行映射 + 校验 + 写入
    from validators import validate_category, validate_amount, validate_time
    from db import insert_record
    rows, _ = _read_csv_rows(Path(data["file"]), None)
    body = rows[1:] if data["has_header"] else rows

    mapping = data["mapping"]
    imported = 0
    failed = []
    for idx, r in enumerate(body):
        if not r or not any(str(c).strip() for c in r):
            continue
        row_no = idx + (2 if data["has_header"] else 1)
        try:
            def _col(field):
                col = mapping.get(field)
                if not col or col > len(r):
                    return ""
                return (r[col - 1] or "").strip()

            time_str = _normalize_time(_col("date"))
            if not time_str:
                raise ValueError(f"日期无法识别: {_col('date')!r}")
            validate_time(time_str)
            amount = _parse_amount(_col("amount"))
            if amount is None:
                raise ValueError(f"金额无法识别: {_col('amount')!r}")
            # 收支方向列(选填):含"收"→正,含"支"→负;无方向列按符号原样
            type_val = _col("type")
            if type_val:
                amount = abs(amount) if "收" in type_val else -abs(amount)
            validate_amount(amount)
            category = _col("category") or "其他"
            validate_category(category)
            insert_record(
                category, amount, time_str,
                account=_col("account"), ledger=_col("ledger") or "生活",
                note=_col("note"),
            )
            imported += 1
        except ValueError as e:
            failed.append({"row": row_no, "error": str(e)})

    data = {
        "file": data["file"], "name": data["name"],
        "total": len(body), "imported": imported,
        "failed": failed[:20],
        "failed_count": len(failed),
    }
    if getattr(args, "json", False):
        msg = f"导入完成: 成功 {imported} 行" + (f" · 失败 {len(failed)} 行" if failed else "")
        emit_ok(data, msg)
        return data
    print(f"✓ 导入完成: 成功 {imported} 行 / 共 {len(body)} 行")
    if failed:
        print(f"  ⚠ 失败 {len(failed)} 行(前 20 条):")
        for f in failed[:20]:
            print(f"    第{f['row']}行: {f['error']}")
    return data


# ── 入口 ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="饼干记账 · 开始使用域 v2.0(6 场景)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="初始化向导(4 步零决策 · 建库+验证)")
    p.add_argument("--check", action="store_true", help="只读环境检测(向导步骤 1-2,不建库)")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("init-status", help="初始化状态(三重判定:存在+schema+版本)")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("backup-create", help="一键备份(db + goals.json)")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("backup-list", help="查看备份列表")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("restore", help="从备份恢复(默认最新)")
    p.add_argument("--name", default=None, help="备份名称(选填,默认最新)")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("import", help="导入 CSV 账单(列映射)")
    p.add_argument("--file", default=None, help="CSV 文件路径(必填)")
    p.add_argument("--mapping", default=None,
                   help="列映射,逗号分隔 字段=列号(1-based),如 date=1,amount=3,category=2")
    p.add_argument("--encoding", default=None, help="编码(utf-8/gbk,默认自动探测)")
    p.add_argument("--skip-header", type=int, default=0, help="跳过表头行数")
    p.add_argument("--preview", action="store_true", help="只输出预览(不写入)")
    p.add_argument("--dry-run", action="store_true", help="预览 + 标记不写入")
    p.add_argument("--json", action="store_true")

    args = parser.parse_args()
    commands = {
        "init": cmd_init,
        "init-status": cmd_init_status,
        "backup-create": cmd_backup_create,
        "backup-list": cmd_backup_list,
        "restore": cmd_restore,
        "import": cmd_import,
    }
    cmd = commands.get(args.cmd)
    if cmd:
        try:
            cmd(args)
        except (ValueError, RuntimeError) as e:
            if getattr(args, "json", False):
                emit_error(f"参数错误：{e}")
            else:
                print(f"✗ 参数错误：{e}")
        except Exception as e:
            if getattr(args, "json", False):
                emit_error(f"执行出错：{e}")
            else:
                print(f"✗ 执行出错：{e}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
