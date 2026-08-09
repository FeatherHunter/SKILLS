# 场景合并器.py - 域场景 yaml → references/scenarios.yaml 合并器(基础设施奠基 · T1)
# 用法: python 场景合并.py [--scenes-dir 场景目录] [--scenarios 总账路径] [--only 文件名] [--dry-run] [--prune]
#
# 语义: 对 scenes/{域}.yaml 中的每个场景,按 (scenario_id) 匹配总账:
#   - 命中: 用 yaml 提供的字段覆盖(wake_word/scenario_title/type/status/html/prompt/result/dimensions/variants)
#   - 未命中: 追加到对应 wake_word 组(不存在则新建组)
#   - 不动的字段原样保留
#   - --prune: 删除总账中不在任何域 yaml 里的孤儿场景(规格阶段收敛/改名后的旧资产)
# 各域只写自己的 scenes/{域}.yaml;改总账的唯一通道 = 本合并器。
#
# 结构差异适配(居家管家先例 → 私家大厨):
#   居家管家总账 = 扁平 scenarios 列表(每项含 id/domain)
#   私家大厨总账 = 嵌套结构: scenarios → [{wake_word, scenarios: [{scenario_id, ...}]}]
#   域 yaml     = 扁平 scenes 列表(每项含 id/domain/sub/wake_word/scenario_id/type/status/html/variants)
# 匹配键 = scenario_id(跨版本稳定,对齐 §07 契约)
#
# --prune 动机(T1 实施核查): 规格阶段 G1-G10 大规模收敛/改名(如 shopping_single_recipe →
#   shopping_generate、record_cook_full → record_cook),总账残留 26 个孤儿场景;
#   合并器作为改总账唯一通道,必须能清理,否则总账永远带着旧资产。
import argparse
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
DEFAULT_SCENES_DIR = SKILL_DIR / "scenes"
DEFAULT_SCENARIOS = SKILL_DIR / "references" / "scenarios.yaml"

# 域 yaml 里允许覆盖总账的字段(其余字段总账为准)
PATCH_FIELDS = ("wake_word", "scenario_title", "dimensions", "type", "status",
                "prompt", "result", "html", "variants")


def load_yaml(path):
    try:
        import yaml
    except ImportError:
        sys.exit("缺少 pyyaml: pip install pyyaml")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def dump_yaml(data, path):
    import yaml
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def merge_scenes(scenarios_root, domain, scenes):
    """把 domain 的 scenes 列表合并进总账(嵌套结构,按 scenario_id 匹配)"""
    groups = scenarios_root.get("scenarios") or []
    by_id = {s.get("scenario_id"): s for s in scenes if s.get("scenario_id")}

    # 第一轮: 在既有 wake_word 组内按 scenario_id 匹配覆盖
    updated = []
    for group in groups:
        group_scenes = group.get("scenarios") or []
        for gs in group_scenes:
            sid = gs.get("scenario_id")
            if sid in by_id:
                patch = by_id.pop(sid)
                for k in PATCH_FIELDS:
                    if k in patch:
                        gs[k] = patch[k]
                updated.append(sid)

    # 第二轮: 未命中的场景追加到对应 wake_word 组(不存在则新建)
    added = []
    for sid, patch in by_id.items():
        ww = patch.get("wake_word") or "未分组"
        group = next((g for g in groups if g.get("wake_word") == ww), None)
        if group is None:
            group = {"wake_word": ww, "scenarios": []}
            groups.append(group)
        entry = {"scenario_id": sid, "domain": domain}
        for k in PATCH_FIELDS:
            if k in patch:
                entry[k] = patch[k]
        group["scenarios"].append(entry)
        added.append(sid)

    return updated, added


def collect_domain_ids(scenes_dir, only=None):
    """收集全部域 yaml 的 scenario_id 集合(供 --prune 判孤儿)"""
    ids = set()
    for yaml_path in sorted(scenes_dir.glob("*.yaml")):
        if only and yaml_path.name != only:
            continue
        data = load_yaml(yaml_path)
        for s in (data.get("scenes") or []):
            if s.get("scenario_id"):
                ids.add(s["scenario_id"])
    return ids


def prune_orphans(scenarios_root, domain_ids):
    """删除总账中不在任何域 yaml 的孤儿场景,返回被删 id 列表"""
    removed = []
    groups = scenarios_root.get("scenarios") or []
    for group in groups:
        keep = []
        for gs in (group.get("scenarios") or []):
            sid = gs.get("scenario_id")
            if sid and sid not in domain_ids:
                removed.append(sid)
            else:
                keep.append(gs)
        group["scenarios"] = keep
    # 清理空组
    scenarios_root["scenarios"] = [g for g in groups if g.get("scenarios")]
    return removed


def main():
    ap = argparse.ArgumentParser(description="域场景 yaml 合并进 references/scenarios.yaml")
    ap.add_argument("--scenes-dir", default=str(DEFAULT_SCENES_DIR))
    ap.add_argument("--scenarios", default=str(DEFAULT_SCENARIOS))
    ap.add_argument("--only", default=None, help="只合并指定文件名(如 做菜.yaml);默认合并全部")
    ap.add_argument("--dry-run", action="store_true", help="只报告不写盘")
    ap.add_argument("--prune", action="store_true", help="删除总账中不在任何域 yaml 的孤儿场景")
    args = ap.parse_args()

    scenarios = load_yaml(args.scenarios)
    scenes_dir = Path(args.scenes_dir)
    total_updated, total_added = [], []
    for yaml_path in sorted(scenes_dir.glob("*.yaml")):
        if args.only and yaml_path.name != args.only:
            continue
        data = load_yaml(yaml_path)
        domain = (data.get("domain") or {}).get("name", yaml_path.stem)
        updated, added = merge_scenes(scenarios, domain, data.get("scenes") or [])
        print(f"• {yaml_path.name} (domain={domain}): 更新 {len(updated)} 条,新增 {len(added)} 条")
        total_updated += updated
        total_added += added

    removed = []
    if args.prune:
        domain_ids = collect_domain_ids(scenes_dir, args.only)
        removed = prune_orphans(scenarios, domain_ids)
        print(f"• prune: 删除孤儿 {len(removed)} 条")
        for sid in removed:
            print(f"    - {sid}")

    print(f"合计:更新 {len(total_updated)} / 新增 {len(total_added)} / 删除孤儿 {len(removed)}")
    if not args.dry_run and (total_updated or total_added or removed):
        dump_yaml(scenarios, args.scenarios)
        print(f"✓ 已写回 {args.scenarios}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
