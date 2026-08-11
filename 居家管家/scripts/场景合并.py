# 场景合并器.py - 域场景 yaml → references/scenarios.yaml 合并器(公共层奠基 · T2)
# 用法: python 场景合并.py [--scenes-dir 场景目录] [--scenarios 总账路径] [--dry-run]
# 语义: 对 scenes/SM{n}.yaml 中的每个场景,按 (id) 匹配总账:
#   - 命中: 用 yaml 提供的字段覆盖(wake_word/scenario_title/type/status/html)
#   - 未命中: 追加到对应 domain 末尾
#   - 不动的字段(prompt/result/variants 等)原样保留
# 各域只写自己的 scenes/SM{n}.yaml;改总账的唯一通道 = 本合并器。
import argparse
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
DEFAULT_SCENES_DIR = SKILL_DIR / "scenes"
DEFAULT_SCENARIOS = SKILL_DIR / "references" / "scenarios.yaml"


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


def merge_scenes(scenarios, domain, scenes):
    """把 domain 的 scenes 列表合并进总账"""
    by_id = {s.get("id"): s for s in scenes if s.get("id")}
    updated, added = [], []
    for s in scenarios["scenarios"]:
        if s.get("domain") == domain and s.get("id") in by_id:
            patch = by_id[s["id"]]
            for k in ("wake_word", "scenario_title", "scenario_id", "type", "status", "html", "prompt", "result"):
                if k in patch:
                    s[k] = patch[k]
            updated.append(s["id"])
            del by_id[s["id"]]
    for sid, patch in by_id.items():
        entry = {"id": sid, "domain": domain}
        entry.update(patch)
        scenarios["scenarios"].append(entry)
        added.append(sid)
    return updated, added


def main():
    ap = argparse.ArgumentParser(description="域场景 yaml 合并进 references/scenarios.yaml")
    ap.add_argument("--scenes-dir", default=str(DEFAULT_SCENES_DIR))
    ap.add_argument("--scenarios", default=str(DEFAULT_SCENARIOS))
    ap.add_argument("--only", default=None, help="只合并指定文件名(如 SM1.yaml);默认合并全部")
    ap.add_argument("--dry-run", action="store_true", help="只报告不写盘")
    args = ap.parse_args()

    scenarios = load_yaml(args.scenarios)
    scenes_dir = Path(args.scenes_dir)
    total_updated, total_added = [], []
    for yaml_path in sorted(scenes_dir.glob("SM*.yaml")):
        if args.only and yaml_path.name != args.only:
            continue
        data = load_yaml(yaml_path)
        domain = data.get("domain")
        updated, added = merge_scenes(scenarios, domain, data.get("scenes") or [])
        print(f"• {yaml_path.name} (domain={domain}): 更新 {len(updated)} 条,新增 {len(added)} 条")
        total_updated += updated
        total_added += added

    print(f"合计:更新 {len(total_updated)} / 新增 {len(total_added)}")
    if not args.dry_run and (total_updated or total_added):
        dump_yaml(scenarios, args.scenarios)
        print(f"✓ 已写回 {args.scenarios}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
