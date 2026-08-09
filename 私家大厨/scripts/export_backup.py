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


# ── 扁平 17 表 → import 兼容嵌套格式(恢复=解压+逐个导入)─────────────
# import_orchestrator 只吃嵌套 recipe 格式(recipe_template.json 同构);
# export_recipes 输出扁平表 → 这里做无损转换,每菜一个嵌套 JSON。
def to_import_format(flat: dict) -> dict:
    """把 export_recipes 的单菜扁平记录转为 import_orchestrator 可消费的嵌套 dict。

    flat 结构: {_recipe, recipe_categories, recipe_seasons, ..., ingredients,
                cooking_steps, step_ingredients, step_techniques, tips, ...}
    """
    recipe = dict(flat.get("_recipe") or {})
    out = {
        "name": recipe.get("name"),
        "description": recipe.get("description"),
        "difficulty": recipe.get("difficulty"),
        "servings": recipe.get("servings"),
        "total_time": recipe.get("total_time_minutes"),
        "status": recipe.get("status"),
        "photo_url": recipe.get("photo_url"),
        "source": recipe.get("source"),
        "source_url": recipe.get("source_url"),
    }

    # 1:1 分类(cuisine_type → cuisine)
    cats = flat.get("recipe_categories") or []
    if cats:
        c = cats[0]
        out["category"] = {
            "cuisine": c.get("cuisine_type"),
            "region": c.get("region"),
            "country": c.get("country"),
        }

    # 1:N 标签表 → 字符串数组
    tag_map = {
        "recipe_seasons": "season",
        "recipe_cooking_methods": "method",
        "recipe_flavors": "flavor",
        "recipe_diet_tags": "tag",
        "recipe_meal_types": "meal_type",
    }
    for table, col in tag_map.items():
        rows = flat.get(table) or []
        values = [r.get(col) for r in rows if r.get(col)]
        if values:
            key = {
                "recipe_seasons": "seasons",
                "recipe_cooking_methods": "cooking_methods",
                "recipe_flavors": "flavors",
                "recipe_diet_tags": "diet_tags",
                "recipe_meal_types": "meal_types",
            }[table]
            out[key] = values

    # 食材:扁平行 → 嵌套(去 id/recipe_id)
    ing_rows = flat.get("ingredients") or []
    if ing_rows:
        out["ingredients"] = [{
            "name": r.get("name"),
            "quantity": r.get("quantity"),
            "unit": r.get("unit"),
            "category": r.get("category"),
            "sequence": r.get("sequence"),
            "is_optional": bool(r.get("is_optional")),
            "substitute": r.get("substitute"),
            "quantity_text": r.get("quantity_text"),
        } for r in ing_rows]

    # 步骤 + 步骤×食材桥(step_ingredients → steps[].ingredients_used)
    step_rows = flat.get("cooking_steps") or []
    si_rows = flat.get("step_ingredients") or []
    ing_id_to_name = {r["id"]: r.get("name") for r in ing_rows if r.get("id")}
    ing_id_to_unit = {r["id"]: r.get("unit") for r in ing_rows if r.get("id")}
    # step_id → ingredients_used[]
    si_by_step = {}
    for si in si_rows:
        sid = si.get("step_id")
        si_by_step.setdefault(sid, []).append({
            "name": ing_id_to_name.get(si.get("ingredient_id"), "?"),
            "quantity_used": si.get("quantity_used"),
            "introduced_at": si.get("introduced_at"),
            "unit": si.get("unit") or ing_id_to_unit.get(si.get("ingredient_id")),
        })
    if step_rows:
        out["steps"] = []
        for s in step_rows:
            step_item = {
                "sequence": s.get("sequence"),
                "action": s.get("action"),
                "duration": s.get("duration_minutes"),
                "heat_level": s.get("heat_level"),
                "temperature": s.get("temperature"),
                "expected_result": s.get("expected_result"),
            }
            used = si_by_step.get(s.get("id"))
            if used:
                step_item["ingredients_used"] = used
            out["steps"].append(step_item)

    # 步骤技法(step_techniques → techniques,step_id 换算回 sequence)
    tech_rows = flat.get("step_techniques") or []
    step_id_to_seq = {s.get("id"): s.get("sequence") for s in step_rows if s.get("id")}
    if tech_rows:
        out["techniques"] = [{
            "step_sequence": step_id_to_seq.get(t.get("step_id")),
            "technique_name": t.get("technique_name"),
            "description": t.get("description"),
            "key_points": t.get("key_points"),
        } for t in tech_rows]

    # 贴士(tips → step_sequence 换算;菜级 tip 无 step_id)
    tip_rows = flat.get("tips") or []
    if tip_rows:
        out["tips"] = [{
            "step_sequence": step_id_to_seq.get(t.get("step_id")),
            "content": t.get("content"),
            "category": t.get("category"),
            "priority": t.get("priority"),
        } for t in tip_rows]

    # 炊具
    cw_rows = flat.get("cookware") or []
    if cw_rows:
        out["cookware"] = [{"name": c.get("name"), "category": c.get("category")} for c in cw_rows]

    # 营养 1:1
    nut = flat.get("nutrition_info") or []
    if nut:
        n = nut[0]
        out["nutrition"] = {
            "serving_size": n.get("serving_size"),
            "serving_unit": n.get("serving_unit"),
            "calories": n.get("calories"),
            "protein": n.get("protein"),
            "fat": n.get("fat"),
            "carbs": n.get("carbs"),
            "fiber": n.get("fiber"),
            "sodium": n.get("sodium"),
        }

    # 背景 1:1
    bg = flat.get("background_knowledge") or []
    if bg:
        b = bg[0]
        out["background"] = {
            "origin_story": b.get("origin_story"),
            "historical_background": b.get("historical_background"),
            "cultural_significance": b.get("cultural_significance"),
        }

    # 烹饪历史(缺字段拒绝制:key 恒在,空数组 [] 合法)
    hist = flat.get("recipe_history") or []
    out["history"] = [{
        "cook_date": h.get("cook_date"),
        "cook_sequence": h.get("cook_sequence"),
        "rating": h.get("rating"),
        "feedback": h.get("feedback"),
    } for h in hist]

    # 派生关系(本菜为 child → parent_name 需库中已存在;恢复时父本先导入)
    # 缺字段拒绝制:key 恒在,空数组 [] 合法
    rels = flat.get("recipe_relations") or []
    rel_out = []
    for r in rels:
        if r.get("parent_id") == recipe.get("id"):
            continue  # 本菜是父本 → 对向关系由子本侧登记,跳过
        rel_out.append({
            "parent_name": r.get("parent_name_hint") or "",
            "relation_type": r.get("relation_type"),
            "change_summary": r.get("change_summary"),
        })
    out["relations"] = rel_out

    return out


def build_import_files(records: list, tmp_dir: Path) -> list:
    """把扁平导出转为 import 兼容嵌套 JSON(每菜一个文件)。

    返回 [{name, path, status}] — 恢复 = 逐个 import_orchestrator.py <path>。
    """
    files = []
    ing_by_id = {}
    for rec in records:
        rid = (rec.get("_recipe") or {}).get("id")
        if rid:
            ing_by_id[rid] = (rec.get("_recipe") or {}).get("name")
    # 预解析:recipe_relations 只有 parent_id/child_id,补 parent_name_hint
    for rec in records:
        rid = (rec.get("_recipe") or {}).get("id")
        for r in rec.get("recipe_relations") or []:
            r["parent_name_hint"] = ing_by_id.get(r.get("parent_id"), "")
    for rec in records:
        nested = to_import_format(rec)
        name = (nested.get("name") or "untitled")
        safe = name.strip().replace("/", "_").replace("\\", "_")[:60] or "untitled"
        # 防同名菜覆盖:同名加 _N 后缀
        candidate = tmp_dir / f"{safe}.json"
        n = 1
        while candidate.exists():
            candidate = tmp_dir / f"{safe}_{n}.json"
            n += 1
        candidate.write_text(json.dumps(nested, ensure_ascii=False, indent=2), encoding="utf-8")
        files.append({"name": name, "path": str(candidate)})
    return files


def create_backup(zip_path: Path, include_archived: bool = False) -> dict:
    """创建备份 ZIP:17 表 JSON + import 兼容嵌套 JSON + 三照片目录。

    返回:
        {
            "zip_path", "json_name", "recipe_count",
            "tables", "photo_counts", "import_files", "created_at", "db_path",
        }
    """
    output_root = get_output_root()

    # 1. 17 表 JSON(临时文件 → 进 ZIP)
    json_name = f"recipes_backup_{_ts()}.json"
    tmp_json = Path(zip_path.parent) / f".{json_name}.tmp"
    result = export_recipes.export_recipes(str(tmp_json), include_archived=include_archived)
    recipe_count = result["recipe_count"]
    tables = result["tables"]

    # 1b. import 兼容嵌套 JSON(每菜一个 → recipes_import/ 子目录)
    import_dir = Path(zip_path.parent) / f".import_{_ts()}"
    import_dir.mkdir(parents=True, exist_ok=True)
    import_files = build_import_files(result["recipes"], import_dir)

    # 2. 照片目录计数
    photo_counts = pack_photos(output_root)

    # 3. 写 ZIP
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(str(tmp_json), arcname=json_name)
        for f in import_files:
            zf.write(f["path"], arcname=f"recipes_import/{Path(f['path']).name}")
        for name in PHOTO_DIRS:
            src = output_root / name
            if not src.is_dir():
                continue
            for f in sorted(src.rglob("*")):
                if f.is_file():
                    zf.write(str(f), arcname=f"{name}/{f.relative_to(src).as_posix()}")

    # 4. 清临时文件
    tmp_json.unlink(missing_ok=True)
    import shutil
    shutil.rmtree(import_dir, ignore_errors=True)

    return {
        "zip_path": str(zip_path),
        "json_name": json_name,
        "recipe_count": recipe_count,
        "tables": tables,
        "photo_counts": photo_counts,
        "import_files": import_files,
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
        "import_files": backup["import_files"],
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
            "import_files": len(backup["import_files"]),
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
                "import_files": [f["name"] for f in backup["import_files"]],
                "include_archived": backup["include_archived"],
            },
            "message": f"已备份 {backup['recipe_count']} 道菜(17 表 JSON + import 兼容 JSON + 照片)到 {backup['zip_path']}"
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
