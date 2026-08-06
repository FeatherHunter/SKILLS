# ops.py - SM8 开始使用域 · 数据层
# 职责: 环境检测 / 初始化工作流(G3 6 步) / 分类种子化 / 数据检查 / 备份导出 / 导入恢复
# 隔离契约: 本域只动 scripts/开始使用/ + templates/开始使用/ + render_开始使用 + tests/test_开始使用.py
# 公共层(db.py)只读调用;seed_key 迁移 = D1 拆批前置批(T9 范围,已并入 db.py 幂等迁移)
import os
import sys
import json
import shutil
import sqlite3
import zipfile
import platform
from datetime import datetime, timedelta
from pathlib import Path

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from home_manager.db import (
    DB_PATH, PHOTOS_DIR, SKILL_DIR, get_conn, init_db,
)

# ── 常量 ───────────────────────────────────────────────────────────────

SEED_FILE = SKILL_DIR / "references" / "seed_categories.yaml"
BACKUP_KEEP_N = 5          # 保留 N 份备份(默认 5)
BACKUP_DIR_NAME = "backups"  # 备份目录名(DB 同目录下)
IMPORT_SCHEMA_VERSION = "2.0"

# ── 环境检测(初始化步骤①)───────────────────────────────────────────────


def env_check_payload(force_refresh=False):
    """环境检测 → payload(OS/Python/目录可写/DB 状态)

    G3 步骤①: OS(Windows/WSL/Linux) + Python 版本 + 目录可写性 + DB 存在状态
    """
    # WSL 检测:环境变量 WSL_DISTRO_NAME 存在即为 WSL
    is_wsl = bool(os.environ.get("WSL_DISTRO_NAME")) or (
        not sys.platform.startswith("win") and Path("/proc/version").exists()
        and "microsoft" in Path("/proc/version").read_text(encoding="utf-8", errors="replace").lower()
    )
    os_name = "WSL" if is_wsl else platform.system()
    py_ver = f"{platform.python_version()} ({platform.architecture()[0]})"

    db_dir = DB_PATH.parent
    db_exists = DB_PATH.exists()
    db_writable = _dir_writable(db_dir)
    photos_writable = _dir_writable(PHOTOS_DIR)

    env_db = os.environ.get("SKILLS_DB_PATH")
    env_photos = os.environ.get("HOME_PHOTOS_DIR")

    return {
        "os": os_name,
        "python": py_ver,
        "db_path": str(DB_PATH),
        "db_exists": db_exists,
        "photos_dir": str(PHOTOS_DIR),
        "dirs_writable": {"db_dir": db_writable, "photos_dir": photos_writable},
        "env": {
            "SKILLS_DB_PATH": env_db or "(未设置,走默认)",
            "HOME_PHOTOS_DIR": env_photos or "(未设置,走默认)",
        },
        "status": "ok",
    }


def _dir_writable(d: Path) -> bool:
    try:
        d.mkdir(parents=True, exist_ok=True)
        probe = d / f".write_probe_{os.getpid()}"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


# ── 初始化工作流(G3 · 步骤③建库 + 步骤④建分类)────────────────────────

def init_status_payload():
    """初始化状态判定(幂等):库已存在 + 分类已种子化 → 已初始化"""
    db_exists = DB_PATH.exists()
    if not db_exists:
        return {"status": "ok", "initialized": False, "stage": "未初始化", "detail": "数据库不存在"}
    conn = get_conn()
    try:
        count = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    finally:
        conn.close()
    if count == 0:
        return {"status": "ok", "initialized": False, "stage": "库已建,分类未种子化", "detail": "categories 表为空"}
    return {"status": "ok", "initialized": True, "stage": "已初始化", "detail": f"库存在 + {count} 个分类节点"}


def init_db_and_seed(seed_file=None):
    """初始化:建库(幂等)+ 建分类种子(幂等)

    返回 payload:
      {"status": "ok", "initialized": bool, "skipped": str|None,
       "db_path": str, "top_level": n, "total": n, "seed_keys": n}
    幂等:库已存在且已有分类 → 跳过(不二次建库/建分类)
    """
    seed_file = Path(seed_file or SEED_FILE)
    init_db()  # 幂等建表(含 seed_key 迁移)

    conn = get_conn()
    try:
        existing = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    finally:
        conn.close()

    if existing > 0:
        return {
            "status": "ok",
            "initialized": True,
            "skipped": f"categories 已有 {existing} 条,跳过种子导入(幂等)",
            "db_path": str(DB_PATH),
            "top_level": 0, "total": 0, "seed_keys": 0,
        }

    if not seed_file.exists():
        return {
            "status": "error",
            "error": "seed_file_missing",
            "reason": f"种子文件不存在: {seed_file}",
            "suggest": "检查 references/seed_categories.yaml 是否随技能分发",
            "db_path": str(DB_PATH),
        }

    data = yaml.safe_load(seed_file.read_text(encoding="utf-8"))
    cats = data.get("categories", [])
    if not cats:
        return {"status": "error", "error": "seed_empty", "reason": "种子文件无 categories"}

    conn = get_conn()
    try:
        total, seed_keys = _insert_seed_tree(conn, cats)
    finally:
        conn.close()

    return {
        "status": "ok",
        "initialized": True,
        "skipped": None,
        "db_path": str(DB_PATH),
        "top_level": len(cats),
        "total": total,
        "seed_keys": seed_keys,
    }


def _insert_seed_tree(conn, cats):
    """种子树插入:顶级 + 二级,写 seed_key。返回 (总节点数, seed_key 数)"""
    total = 0
    seed_keys = 0
    cur = conn.cursor()
    for top in cats:
        key = (top.get("seed_key") or "").strip()
        name = (top.get("name") or "").strip()
        if not name:
            continue
        cur.execute(
            "INSERT INTO categories (parent_id, name, description, sort_order, seed_key) VALUES (NULL, ?, ?, ?, ?)",
            (name, top.get("description", ""), total, key or None),
        )
        top_id = cur.lastrowid
        total += 1
        if key:
            seed_keys += 1
        for child in top.get("children", []):
            c_key = (child.get("seed_key") or "").strip()
            c_name = (child.get("name") or "").strip()
            if not c_name:
                continue
            cur.execute(
                "INSERT INTO categories (parent_id, name, description, sort_order, seed_key) VALUES (?, ?, ?, ?, ?)",
                (top_id, c_name, child.get("description", ""), total, c_key or None),
            )
            total += 1
            if c_key:
                seed_keys += 1
    conn.commit()
    return total, seed_keys


# ── 分类解析器(分类兼容设计 · 三级 fallback)───────────────────────────

def resolve_category(conn, seed_key=None, legacy_name=None, legacy_id=None):
    """解析分类:① seed_key → ② legacy_name → ③ legacy_id(三级 fallback)

    老库无 seed_key 列或列全空 → 名称命中(名称与用户体系完全一致);
    都失败 → legacy_id 兜底;再失败 → None
    """
    if seed_key:
        row = conn.execute(
            "SELECT * FROM categories WHERE seed_key = ? LIMIT 1", (seed_key,)
        ).fetchone()
        if row:
            return row
    if legacy_name:
        row = conn.execute(
            "SELECT * FROM categories WHERE name = ? LIMIT 1", (legacy_name,)
        ).fetchone()
        if row:
            return row
    if legacy_id is not None:
        return conn.execute("SELECT * FROM categories WHERE id = ?", (legacy_id,)).fetchone()
    return None


# ── 数据检查(查异常 · 8 检查项)────────────────────────────────────────

def lint_health_payload(days_status=None):
    """数据健康检查 → payload(环境信息头部 + 检查项清单)

    检查项(现状 4 项 + v2.0 扩展 4 项):
      1 标签完整性  2 无位置物品  3 状态时效  4 位置规范
      5 照片缺失    6 价格缺失    7 日期缺失  8 相似位置未合并
    每项: {key, title, severity(high/mid/low), count, samples, fix_prompt}
    修复引导 = 只建议不自动改(复制 prompt 到对应场景)
    """
    days_status = days_status or {"快递中": 7, "旅游中": 30, "维修中": 30, "借用中": 30}
    conn = get_conn()
    try:
        env = env_check_payload()
        items_total = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]

        checks = []

        # 1 标签完整性:无标签物品
        no_tag = conn.execute("""
            SELECT i.id, i.name FROM items i
            LEFT JOIN item_tags t ON t.item_id = i.id
            WHERE t.item_id IS NULL ORDER BY i.name LIMIT 5
        """).fetchall()
        no_tag_total = conn.execute("""
            SELECT COUNT(*) FROM items i
            LEFT JOIN item_tags t ON t.item_id = i.id
            WHERE t.item_id IS NULL
        """).fetchone()[0]
        checks.append(_lint_item(
            key="no_tag", title="无标签物品", severity=_sev(no_tag_total, items_total),
            count=no_tag_total, samples=[r["name"] for r in no_tag],
            fix_prompt="请帮我给这几件物品补上标签(唤醒词:改物品),逐个建议 2-4 个标签供我确认",
        ))

        # 2 无位置物品:items 无任何 item_locations 行
        no_loc = conn.execute("""
            SELECT i.id, i.name FROM items i
            LEFT JOIN item_locations l ON l.item_id = i.id
            WHERE l.item_id IS NULL ORDER BY i.name LIMIT 5
        """).fetchall()
        no_loc_total = conn.execute("""
            SELECT COUNT(*) FROM items i
            LEFT JOIN item_locations l ON l.item_id = i.id
            WHERE l.item_id IS NULL
        """).fetchone()[0]
        checks.append(_lint_item(
            key="no_location", title="无位置物品", severity=_sev(no_loc_total, items_total),
            count=no_loc_total, samples=[r["name"] for r in no_loc],
            fix_prompt="请帮我把这些物品补上存放位置(唤醒词:改物品),我逐个提供位置",
        ))

        # 3 状态时效:快递中/旅游中/维修中/借用中 长期未更新
        stale_items = []
        for status, max_days in days_status.items():
            rows = conn.execute("""
                SELECT i.id, i.name, l.location_status, l.updated_at
                FROM item_locations l JOIN items i ON i.id = l.item_id
                WHERE l.location_status = ?
            """, (status,)).fetchall()
            for r in rows:
                updated = r["updated_at"]
                days = _days_since(updated)
                if days is not None and days > max_days:
                    stale_items.append((r["name"], status, days))
        stale_items = stale_items[:5]
        stale_total = _stale_total(conn, days_status)
        checks.append(_lint_item(
            key="stale_status", title="状态长期未更新", severity="high" if stale_total else "low",
            count=stale_total, samples=[f"{n}·{s}({d}天)" for n, s, d in stale_items],
            fix_prompt="请帮我把这些物品的状态更新为当前实际状态(唤醒词:改物品)",
        ))

        # 4 位置规范:单级位置(路径不含 /)
        single_level = conn.execute("""
            SELECT DISTINCT location FROM item_locations
            WHERE location NOT LIKE '%/%' ORDER BY location LIMIT 5
        """).fetchall()
        single_total = conn.execute("""
            SELECT COUNT(DISTINCT location) FROM item_locations
            WHERE location NOT LIKE '%/%'
        """).fetchone()[0]
        checks.append(_lint_item(
            key="single_level", title="单级位置", severity="mid" if single_total else "low",
            count=single_total, samples=[r["location"] for r in single_level],
            fix_prompt="请帮我把这些单级位置规范为多级路径(如:客厅/电视柜),唤醒词:移物品",
        ))

        # 5 照片缺失
        no_photo = conn.execute("""
            SELECT id, name FROM items WHERE photo IS NULL OR photo = '' ORDER BY name LIMIT 5
        """).fetchall()
        no_photo_total = conn.execute(
            "SELECT COUNT(*) FROM items WHERE photo IS NULL OR photo = ''"
        ).fetchone()[0]
        checks.append(_lint_item(
            key="no_photo", title="无照片物品", severity="mid" if no_photo_total else "low",
            count=no_photo_total, samples=[r["name"] for r in no_photo],
            fix_prompt="请帮这几件物品补拍照片(唤醒词:拍物品),【照片即将发送:】",
        ))

        # 6 价格缺失
        no_price = conn.execute("""
            SELECT id, name FROM items WHERE purchase_price IS NULL ORDER BY name LIMIT 5
        """).fetchall()
        no_price_total = conn.execute(
            "SELECT COUNT(*) FROM items WHERE purchase_price IS NULL"
        ).fetchone()[0]
        checks.append(_lint_item(
            key="no_price", title="未录价格", severity="mid" if no_price_total else "low",
            count=no_price_total, samples=[r["name"] for r in no_price],
            fix_prompt="请帮这些物品补录价格(唤醒词:改物品),我逐个提供",
        ))

        # 7 日期缺失:无购买日期且无过期日期
        no_date = conn.execute("""
            SELECT i.id, i.name FROM items i
            LEFT JOIN item_locations l ON l.item_id = i.id
            GROUP BY i.id
            HAVING COUNT(CASE WHEN l.purchase_date IS NOT NULL OR l.expiration_date IS NOT NULL THEN 1 END) = 0
            ORDER BY i.name LIMIT 5
        """).fetchall()
        no_date_total = conn.execute("""
            SELECT COUNT(*) FROM (
                SELECT i.id FROM items i
                LEFT JOIN item_locations l ON l.item_id = i.id
                GROUP BY i.id
                HAVING COUNT(CASE WHEN l.purchase_date IS NOT NULL OR l.expiration_date IS NOT NULL THEN 1 END) = 0
            )
        """).fetchone()[0]
        checks.append(_lint_item(
            key="no_date", title="无购买/过期日期", severity="low",
            count=no_date_total, samples=[r["name"] for r in no_date],
            fix_prompt="请帮这些物品补录购买日期或过期日期(唤醒词:改物品)",
        ))

        # 8 相似位置未合并:前缀相同的位置(如 卧室/东南角 vs 卧室东南角)
        similar = _similar_locations(conn, limit=5)
        checks.append(_lint_item(
            key="similar_location", title="相似位置未合并", severity="low",
            count=len(similar), samples=similar,
            fix_prompt="请帮我把这些相似位置合并统一(唤醒词:移物品),确认合并方案",
        ))

        issues_total = sum(c["count"] for c in checks)
        severity_order = {"high": 0, "mid": 1, "low": 2}
        checks_sorted = sorted(checks, key=lambda c: severity_order.get(c["severity"], 9))
        return {
            "env": env,
            "items_total": items_total,
            "checks": checks_sorted,
            "issues_total": issues_total,
            "healthy": issues_total == 0,
            "status": "ok",
        }
    finally:
        conn.close()


def _lint_item(key, title, severity, count, samples, fix_prompt):
    return {
        "key": key, "title": title, "severity": severity, "count": count,
        "samples": samples, "fix_prompt": fix_prompt,
    }


def _sev(count, total):
    if count == 0:
        return "low"
    if total and count / total > 0.3:
        return "high"
    return "mid"


def _days_since(ts):
    if not ts:
        return None
    try:
        d = datetime.strptime(str(ts)[:10], "%Y-%m-%d")
        return (datetime.now() - d).days
    except ValueError:
        return None


def _stale_total(conn, days_status):
    total = 0
    for status, max_days in days_status.items():
        rows = conn.execute(
            "SELECT updated_at FROM item_locations WHERE location_status = ?", (status,)
        ).fetchall()
        for r in rows:
            days = _days_since(r["updated_at"])
            if days is not None and days > max_days:
                total += 1
    return total


def _similar_locations(conn, limit=5):
    """相似位置启发式:两个位置去掉 '/'-' ' 分隔后相同 → 疑似重复"""
    rows = conn.execute(
        "SELECT DISTINCT location FROM item_locations ORDER BY location"
    ).fetchall()
    seen = {}
    result = []
    for r in rows:
        loc = r["location"] or ""
        norm = loc.replace("/", "").replace(" ", "")
        if not norm:
            continue
        if norm in seen and seen[norm] != loc:
            result.append(f"{seen[norm]} ↔ {loc}")
            if len(result) >= limit:
                break
        else:
            seen[norm] = loc
    return result


# ── 备份与导出(数据资产)───────────────────────────────────────────────

def _backup_dir():
    d = DB_PATH.parent / BACKUP_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def backup_payload(keep_n=BACKUP_KEEP_N):
    """备份:db + 照片 全量打包 → zip;保留 N 份,删除最旧。

    返回 payload: {file, size, created_at, history: [...], days_since_last}
    """
    try:
        file = _do_backup()
    except Exception as e:
        return {
            "status": "error", "error": "backup_failed",
            "reason": str(e),
            "suggest": "检查数据库/照片目录可读性后重试",
        }
    _prune_backups(keep_n)
    return {
        "status": "ok",
        "keep_n": keep_n,
        "file": str(file),
        "size": file.stat().st_size,
        "created_at": _now_str(),
        "history": backup_list_payload(keep_n=keep_n)["history"],
        "days_since_last": _days_since_backup(),
    }


def import_undo_payload(backup_file):
    """撤销导入:用导入前自动备份中的 home.db 覆盖当前库(恢复到导入前状态)

    安全网(第一性:数据安全优先于便捷):
      1. 校验备份文件存在 + 是 home_backup_*.zip + zip 内含 home.db
      2. 覆盖前先把当前库再备份一次(防误撤销后找不回导入后状态)
      3. 从 zip 提取 home.db → 覆盖 DB_PATH
      4. 返回恢复结果(来源备份 + 当前物品数)
    """
    src = Path(backup_file or "")
    if not src.exists() or not src.name.startswith("home_backup_") or src.suffix != ".zip":
        return {
            "status": "error", "error": "bad_backup",
            "reason": f"备份文件无效: {backup_file}",
            "suggest": "从导入回执的「导入前备份」行复制正确文件名",
        }

    try:
        with zipfile.ZipFile(src) as zf:
            names = zf.namelist()
            if "home.db" not in names:
                return {
                    "status": "error", "error": "no_db_in_backup",
                    "reason": "备份内未找到 home.db,无法恢复数据库",
                    "suggest": "该备份可能损坏,请换用其他备份",
                }
            # 先读内存再写盘:备份文件只读,不依赖其可写
            db_bytes = zf.read("home.db")
    except Exception as e:
        return {
            "status": "error", "error": "read_failed",
            "reason": f"读取备份失败: {e}",
            "suggest": "检查备份文件完整性后重试",
        }

    # 安全网:覆盖前先备份当前状态(防误撤销)
    safety = _do_backup()

    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        DB_PATH.write_bytes(db_bytes)
    except OSError as e:
        return {
            "status": "error", "error": "restore_failed",
            "reason": f"写回数据库失败: {e}",
            "suggest": "检查数据库目录可写性后重试",
        }

    conn = get_conn()
    try:
        items_total = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    finally:
        conn.close()

    return {
        "status": "ok",
        "restored_from": str(src),
        "safety_backup": str(safety),
        "items_total": items_total,
        "message": "已恢复到导入前状态",
    }


def _do_backup():
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    file = _backup_dir() / f"home_backup_{stamp}.zip"
    with zipfile.ZipFile(file, "w", zipfile.ZIP_DEFLATED) as zf:
        if DB_PATH.exists():
            zf.write(DB_PATH, "home.db")
        if PHOTOS_DIR.exists():
            for p in sorted(PHOTOS_DIR.rglob("*")):
                if p.is_file():
                    zf.write(p, f"photos/{p.relative_to(PHOTOS_DIR)}")
    return file


def _prune_backups(keep_n):
    files = sorted(_backup_dir().glob("home_backup_*.zip"))
    for old in files[:-keep_n]:
        try:
            old.unlink()
        except OSError:
            pass


def _backup_stem_time(name):
    """从备份文件名解析时间(兼容 %Y%m%d_%H%M%S 与 %Y%m%d_%H%M%S_%f)"""
    stem = Path(name).stem
    for fmt in ("home_backup_%Y%m%d_%H%M%S_%f", "home_backup_%Y%m%d_%H%M%S"):
        try:
            return datetime.strptime(stem, fmt)
        except ValueError:
            continue
    return None


def _days_since_backup():
    files = sorted(_backup_dir().glob("home_backup_*.zip"))
    if not files:
        return None
    t = _backup_stem_time(files[-1].name)
    if t is None:
        return None
    return (datetime.now() - t).days


def backup_list_payload(keep_n=BACKUP_KEEP_N):
    files = sorted(_backup_dir().glob("home_backup_*.zip"))
    history = []
    for f in files:
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        history.append({
            "file": f.name,
            "size": f.stat().st_size,
            "created_at": mtime.strftime("%Y-%m-%d %H:%M:%S"),
            "days_ago": (datetime.now() - mtime).days,
        })
    return {
        "status": "ok",
        "keep_n": keep_n,
        "count": len(history),
        "history": history,
        "days_since_last": _days_since_backup(),
    }


def delete_backup_payload(filename):
    """删除旧备份(确认式)。只在保留窗口内可用,返回删除结果"""
    target = _backup_dir() / filename
    if not target.exists() or not target.name.startswith("home_backup_"):
        return {"status": "error", "error": "not_found", "reason": f"备份不存在: {filename}"}
    target.unlink()
    return {"status": "ok", "deleted": filename, "history": backup_list_payload()["history"]}


def export_payload(fmt="json", output_path=None):
    """导出:JSON(全表,可迁移)/ CSV(items 便携)。返回 {file, format, size, rows}"""
    conn = get_conn()
    try:
        if fmt == "json":
            data = {
                "schema_version": IMPORT_SCHEMA_VERSION,
                "exported_at": _now_str(),
                "items": [dict(r) for r in conn.execute("SELECT * FROM items")],
                "item_locations": [dict(r) for r in conn.execute("SELECT * FROM item_locations")],
                "item_tags": [dict(r) for r in conn.execute("SELECT * FROM item_tags")],
                "categories": [dict(r) for r in conn.execute("SELECT * FROM categories")],
            }
            text = json.dumps(data, ensure_ascii=False, indent=1)
            suffix = ".json"
        elif fmt == "csv":
            import csv as _csv
            import io
            buf = io.StringIO()
            w = _csv.writer(buf)
            w.writerow(["id", "name", "category", "owner", "purchase_price",
                        "remark", "location", "quantity", "status",
                        "purchase_date", "expiration_date"])
            for r in conn.execute("""
                SELECT i.id, i.name, i.category, i.owner, i.purchase_price, i.remark,
                       l.location, l.quantity, l.location_status,
                       l.purchase_date, l.expiration_date
                FROM items i LEFT JOIN item_locations l ON l.item_id = i.id
                ORDER BY i.id
            """):
                w.writerow(list(r))
            text = buf.getvalue()
            suffix = ".csv"
        else:
            return {"status": "error", "error": "bad_format", "reason": f"不支持的格式: {fmt}"}
    finally:
        conn.close()

    out = Path(output_path) if output_path else (
        _backup_dir() / f"home_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}{suffix}"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return {"status": "ok", "file": str(out), "format": fmt, "size": len(text.encode("utf-8"))}


# ── 导入与恢复(迁移)──────────────────────────────────────────────────

def import_preview_payload(import_file):
    """导入前校验 + 冲突预览。返回 payload:
      {valid, schema_version, items_total, conflicts: [{name, mode_choices}], duplicate_count, new_count}
    冲突 = 与现有库同名物品(跳过/合并/覆盖 三选)
    """
    src = Path(import_file)
    if not src.exists():
        return {"status": "error", "error": "file_missing", "reason": f"文件不存在: {src}"}

    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except Exception as e:
        return {"status": "error", "error": "bad_json", "reason": f"JSON 解析失败: {e}"}

    version = data.get("schema_version", "1.x")
    items = data.get("items", [])
    if not isinstance(items, list):
        return {"status": "error", "error": "bad_structure", "reason": "缺 items 数组(仅支持 JSON 导出/备份)"}

    # 版本兼容:1.x(老导出)兼容,2.x 匹配,其他 → 警告但可继续
    version_compat = version.startswith(IMPORT_SCHEMA_VERSION[:2]) or version.startswith("1.")

    conn = get_conn()
    try:
        existing = {
            r["name"] for r in conn.execute("SELECT name FROM items")
        }
    finally:
        conn.close()

    conflicts = []
    for it in items:
        name = (it.get("name") or "").strip()
        if not name:
            continue
        if name in existing:
            conflicts.append({"name": name})

    return {
        "status": "ok",
        "valid": version_compat,
        "schema_version": version,
        "expected_version": IMPORT_SCHEMA_VERSION,
        "items_total": len(items),
        "duplicate_count": len(conflicts),
        "new_count": len(items) - len(conflicts),
        "conflicts": conflicts[:50],
        "conflict_sample": conflicts[:5],
    }


def import_execute_payload(import_file, mode="skip", auto_backup=True):
    """确认导入。导入前自动备份现有库(安全网)。mode: skip/overwrite(同名跳过或覆盖)

    返回 payload: {imported, skipped, overwritten, backup_file, rollback_available}
    失败 → 回滚(数据不变):导入在事务内执行,异常即 ROLLBACK。
    """
    preview = import_preview_payload(import_file)
    if preview.get("status") != "ok":
        return preview

    data = json.loads(Path(import_file).read_text(encoding="utf-8"))
    items = data.get("items", [])
    locations = {r["item_id"]: r for r in data.get("item_locations", [])}
    tags = {}
    for r in data.get("item_tags", []):
        tags.setdefault(r["item_id"], []).append(r["tag"])
    categories = {r["id"]: r["name"] for r in data.get("categories", [])}
    source_ids = {it.get("id") for it in items}

    backup_file = None
    if auto_backup:
        backup_file = _do_backup()

    conn = get_conn()
    imported = skipped = overwritten = 0
    try:
        cur = conn.cursor()
        existing = {
            r["name"]: r["id"] for r in cur.execute("SELECT id, name FROM items")
        }
        # 完整性校验:locations/tags 引用的 item_id 必须在本文件 items 中
        # (损坏/伪造文件 → 报错回滚,数据不变)
        dangling = (set(locations) | set(tags)) - source_ids
        if dangling:
            conn.rollback()
            return {
                "status": "error",
                "error": "import_dangling_ref",
                "reason": f"文件内部引用不一致:item_locations/item_tags 引用了 {len(dangling)} 个不存在的物品 id",
                "suggest": "文件疑似损坏,请重新导出后重试",
                "rollback_available": False,
            }
        new_id_map = {}
        for it in items:
            name = (it.get("name") or "").strip()
            if not name:
                skipped += 1
                continue
            if name in existing:
                if mode == "skip":
                    skipped += 1
                    continue
                # overwrite:更新现有行
                cur.execute(
                    "UPDATE items SET category=?, owner=?, purchase_price=?, remark=?, photo=? WHERE id=?",
                    (it.get("category"), it.get("owner", "使用者"),
                     it.get("purchase_price"), it.get("remark"), it.get("photo"),
                     existing[name]),
                )
                new_id_map[it.get("id")] = existing[name]
                overwritten += 1
                continue
            cur.execute(
                "INSERT INTO items (name, category, owner, purchase_price, remark, photo) VALUES (?,?,?,?,?,?)",
                (name, it.get("category"), it.get("owner", "使用者"),
                 it.get("purchase_price"), it.get("remark"), it.get("photo")),
            )
            new_id_map[it.get("id")] = cur.lastrowid
            imported += 1

        for old_id, new_id in new_id_map.items():
            loc = locations.get(old_id)
            if loc:
                cur.execute("""
                    INSERT INTO item_locations (item_id, location, quantity, reason, location_status,
                                                purchase_date, expiration_date)
                    VALUES (?,?,?,?,?,?,?)
                """, (new_id, loc.get("location", "未分类"), loc.get("quantity", 1),
                      loc.get("reason"), loc.get("location_status", "在家"),
                      loc.get("purchase_date"), loc.get("expiration_date")))
            for tag in tags.get(old_id, []):
                cur.execute(
                    "INSERT OR IGNORE INTO item_tags (item_id, tag) VALUES (?,?)", (new_id, tag)
                )
        conn.commit()
        return {
            "status": "ok",
            "imported": imported,
            "skipped": skipped,
            "overwritten": overwritten,
            "backup_file": str(backup_file) if backup_file else None,
            "rollback_available": True,
        }
    except Exception as e:
        conn.rollback()
        return {
            "status": "error",
            "error": "import_failed",
            "reason": str(e),
            "suggest": "数据已回滚,现有数据未受影响;检查文件后重试",
            "rollback_available": False,
        }
    finally:
        conn.close()


def _now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
