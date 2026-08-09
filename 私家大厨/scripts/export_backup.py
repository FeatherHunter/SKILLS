#!/usr/bin/env python3
"""
私家大厨 · 导出备份(数据管理域 data-3 · 唤醒词「备份」· G10 定案)

打包下载:全量 17 表 JSON + 三照片目录 ZIP,纯文件操作不碰 schema。
完整恢复 = 解压 + 导入(import_orchestrator.py)。

产物(输出根 $CHEF_OUTPUT_DIR/backup/):
    私家大厨备份_<YYYYMMDD_HHMMSS>.zip
        ├── recipes_backup_<ts>.json      # 17 表全量 JSON(export_recipes 复用)
        └── photos/                       # 三照片目录(存在才打包)
        └── source_photos/
        └── work_photos/
    备份回执_<YYYYMMDD_HHMMSS>.html       # 08 双按钮 + 统计(回执)

用法:
    python scripts/export_backup.py [--include-archived] [--out <zip路径>]

CLI 输出(三段式):
    {status, data: {zip_path, receipt_path, recipe_count, tables, photo_counts}, message}
"""
import sys
import os
import json
import zipfile
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent

sys.path.insert(0, str(SCRIPT_DIR))
from output_config import get_output_root, get_output_dir  # noqa: E402
from align_08 import (build_copy_data, build_copy_log,  # noqa: E402
                      inject_08_layer, unique_output_path)
import export_recipes  # noqa: E402  (复用 17 表导出)


TEMPLATE_PATH = SKILL_DIR / "templates" / "backup_receipt.html"

# 三照片目录(G5 契约 · 同挂输出根目录 · 存在才打包)
PHOTO_DIRS = ["photos", "source_photos", "work_photos"]


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def pack_photos(output_root: Path) -> dict:
    """打包三照片目录(存在才打包),返回 {dir: file_count}"""
    counts = {}
    for name in PHOTO_DIRS:
        src = output_root / name
        if src.is_dir():
            counts[name] = sum(1 for f in src.rglob("*") if f.is_file())
        else:
            counts[name] = 0
    return counts


def create_backup(zip_path: Path, include_archived: bool = False) -> dict:
    """创建备份 ZIP:17 表 JSON + 三照片目录。

    返回:
        {
            "zip_path", "json_name", "recipe_count",
            "tables", "photo_counts", "created_at", "db_path",
        }
    """
    output_root = get_output_root()

    # 1. 17 表 JSON(临时文件 → 进 ZIP)
    json_name = f"recipes_backup_{_ts()}.json"
    tmp_json = Path(zip_path.parent) / f".{json_name}.tmp"
    result = export_recipes.export_recipes(str(tmp_json), include_archived=include_archived)
    recipe_count = result["recipe_count"]
    tables = result["tables"]

    # 2. 照片目录计数
    photo_counts = pack_photos(output_root)

    # 3. 写 ZIP
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(str(tmp_json), arcname=json_name)
        for name in PHOTO_DIRS:
            src = output_root / name
            if not src.is_dir():
                continue
            for f in sorted(src.rglob("*")):
                if f.is_file():
                    zf.write(str(f), arcname=f"{name}/{f.relative_to(src).as_posix()}")

    # 4. 清临时 JSON
    tmp_json.unlink(missing_ok=True)

    return {
        "zip_path": str(zip_path),
        "json_name": json_name,
        "recipe_count": recipe_count,
        "tables": tables,
        "photo_counts": photo_counts,
        "created_at": _now(),
        "db_path": result["db_path"],
        "include_archived": include_archived,
    }


def render_receipt(backup: dict) -> str:
    """渲染备份回执 HTML(08 双按钮硬标准)"""
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"模板不存在:{TEMPLATE_PATH}")

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    payload = {
        "title": "🗄️ 备份完成 · 私家大厨",
        "created_at": backup["created_at"],
        "zip_path": backup["zip_path"],
        "json_name": backup["json_name"],
        "recipe_count": backup["recipe_count"],
        "tables": backup["tables"],
        "photo_counts": backup["photo_counts"],
        "include_archived": backup["include_archived"],
    }

    # 注入数据(§04 原则 4 · <!--INJECT-DATA--> 唯一)
    placeholder = "<!--INJECT-DATA-->"
    count = template.count(placeholder)
    if count != 1:
        raise ValueError(f"占位符必须唯一 1 次,实际 {count} 次")
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
    payload_json = payload_json.replace("</", "<\\/")
    script_tag = f'<script>window.__DATA__ = {payload_json};</script>'
    output = template.replace(placeholder, script_tag, 1)

    # 08 对齐:复制数据(5 段)/复制日志(6 段)
    photo_total = sum(backup["photo_counts"].values())
    copy_data = build_copy_data(
        scene_id="data-3",
        command_cn="备份",
        target="全部食谱",
        payload={
            "zip_path": backup["zip_path"],
            "json_name": backup["json_name"],
            "recipe_count": backup["recipe_count"],
            "tables": backup["tables"],
            "photo_counts": backup["photo_counts"],
            "include_archived": backup["include_archived"],
        },
    )
    copy_log = build_copy_log(
        scene_id="data-3",
        command_cn="备份",
        wake_word="备份",
        thinking="意图理解 → 备份 → export_recipes 17 表 JSON + 三照片目录打包 ZIP → 回执",
        data_structure="window.__DATA__(zip/json/tables/photo_counts)· 读库(只读)+ 文件打包",
        call_chain="python export_backup.py [--include-archived]",
    )
    output = inject_08_layer(output, copy_data, copy_log,
                             extra_buttons=[{
                                 "label": "📥 备份文件信息已含路径",
                                 "text": backup["zip_path"],
                             }])

    # 输出路径(backup/ 子目录 · _N 防覆盖)
    out_dir = get_output_root() / "backup"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = unique_output_path(out_dir, f"备份回执_{_ts()}")
    out_path.write_text(output, encoding="utf-8")
    return str(out_path)


def main():
    include_archived = "--include-archived" in sys.argv
    output_path = None
    for i, arg in enumerate(sys.argv):
        if arg == "--out" and i + 1 < len(sys.argv):
            output_path = sys.argv[i + 1]

    try:
        if output_path:
            zip_path = Path(output_path)
        else:
            backup_dir = get_output_root() / "backup"
            backup_dir.mkdir(parents=True, exist_ok=True)
            zip_path = unique_output_path(backup_dir, f"私家大厨备份_{_ts()}", ext=".zip")

        backup = create_backup(zip_path, include_archived=include_archived)
        receipt_path = render_receipt(backup)

        print(json.dumps({
            "status": "success",
            "data": {
                "zip_path": backup["zip_path"],
                "receipt_path": receipt_path,
                "recipe_count": backup["recipe_count"],
                "tables": backup["tables"],
                "photo_counts": backup["photo_counts"],
                "include_archived": backup["include_archived"],
            },
            "message": f"已备份 {backup['recipe_count']} 道菜(17 表 JSON + 照片)到 {backup['zip_path']}"
        }, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "data": {"error": str(e)},
            "message": f"备份失败: {e}"
        }, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
