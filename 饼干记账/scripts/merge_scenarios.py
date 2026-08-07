#!/usr/bin/env python3
"""
饼干记账 · 场景合并器(公共层 · T0 #164 清单第 4 项)

把 7 个域的 scenes/{域}.yaml(手写唯一源)合并为 references/scenarios.yaml(汇总,只读生成物)。

依据:
- G3 决议 #144:方案 1(域 yaml + 合并器 + 汇总);汇总 = 合并产物,只读不手改;重跑无 diff = 一致性证明
- G3 补充决议 2:嵌套结构 sub → wake_word → scenes;场景字段 = id/scenario_id/scenario_title/type/status/html/prompt/result;无 variants
- G3 补充决议 4:prompt head = 「请加载「饼干记账」技能,帮我<场景人话>(唤醒词:<唤醒词>):」
- T0 #164:7 域(setup/write/query/analysis/goal/account/link);汇总顶层 domains meta 取代 _categories

用法:
    python3 scripts/merge_scenarios.py            # 合并并写 references/scenarios.yaml
    python3 scripts/merge_scenarios.py --check    # 只校验 + 与现有汇总对比(无 diff 通过,不写文件)
    python3 scripts/merge_scenarios.py --out X.yaml
"""

import sys
import argparse
from pathlib import Path

try:
    import yaml
except ImportError:
    # 零安装兜底:优先找 vendor 目录下的 PyYAML(G6 D-1 决议)
    _script_dir = Path(__file__).parent.resolve()
    for _candidate in (_script_dir / "vendor", _script_dir.parent / "vendor"):
        if (_candidate / "yaml" / "__init__.py").exists():
            sys.path.insert(0, str(_candidate))
            import yaml  # noqa: F811
            break
    else:
        raise

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_SCRIPT_DIR = Path(__file__).parent.resolve()
SKILL_DIR = _SCRIPT_DIR.parent
SCENES_DIR = SKILL_DIR / "scenes"
SUMMARY_PATH = SKILL_DIR / "references" / "scenarios.yaml"

VERSION = "2.0"
SKILL_NAME = "饼干记账"

# 7 域 meta(固定声明;scenes 只含已枚举域,未枚举域 HELP 显示待开发)
DOMAINS = [
    {"key": "setup",    "name": "开始使用", "icon": "🚀"},
    {"key": "write",    "name": "写入",     "icon": "✏️"},
    {"key": "query",    "name": "查询",     "icon": "🔍"},
    {"key": "analysis", "name": "分析",     "icon": "📊"},
    {"key": "goal",     "name": "目标",     "icon": "🎯"},
    {"key": "account",  "name": "账户",     "icon": "💳"},
    {"key": "link",     "name": "联动",     "icon": "🔗"},
]
DOMAIN_KEYS = [d["key"] for d in DOMAINS]

# HELP 唤醒词(与 SKILL.md §唤醒词总表 HELP 行同步,4 条)
HELP_WAKE_WORDS = ["饼干记账 HELP", "饼干记账 帮助", "查帮助", "能做什么"]

REQUIRED_SCENE_FIELDS = ["id", "scenario_id", "scenario_title", "type", "status", "html", "prompt", "result"]
REQUIRED_HTML_FIELDS = ["template", "command_cn", "data_source"]
PROMPT_HEAD_PREFIX = "请加载「饼干记账」技能"


def load_domain_yaml(domain_key: str) -> dict | None:
    """读单个域 yaml;文件不存在返回 None,语法错误抛 ValueError(友好信息)"""
    path = SCENES_DIR / f"{domain_key}.yaml"
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"域文件 yaml 语法错误: {path.name} — {e}") from e
    if data is None:
        return None
    return data


class _BlockDumper(yaml.SafeDumper):
    """SafeDumper 子类:多行字符串用 block 标量(|)输出,保证汇总人类可读"""

    def _represent_str(self, data):
        style = "|" if "\n" in data else None
        return self.represent_scalar("tag:yaml.org,2002:str", data, style=style)


_BlockDumper.add_representer(str, _BlockDumper._represent_str)


def dump_summary(summary: dict) -> str:
    """序列化汇总(block 标量保持 prompt 可读)"""
    return yaml.dump(summary, Dumper=_BlockDumper, allow_unicode=True, sort_keys=False, width=120)


def validate(data: dict, domain_key: str, errors: list) -> int:
    """校验单个域 yaml 的结构契约;返回场景数,错误追加到 errors"""
    if not isinstance(data, dict):
        errors.append(f"[{domain_key}] 顶层必须是映射,实际 {type(data).__name__}")
        return 0
    version = data.get("version")
    if version != VERSION:
        errors.append(f"[{domain_key}] version 期望 {VERSION!r},实际 {version!r}")
    if data.get("domain") != domain_key:
        errors.append(f"[{domain_key}] domain 字段期望 {domain_key!r},实际 {data.get('domain')!r}")

    subs = data.get("subs")
    if not isinstance(subs, list):
        errors.append(f"[{domain_key}] 缺少 subs 列表")
        return 0

    seen_subs = set()
    seen_ww_in_domain = set()
    count = 0
    for sub in subs:
        if not isinstance(sub, dict) or not sub.get("name"):
            errors.append(f"[{domain_key}] sub 条目缺少 name")
            continue
        sub_name = sub["name"]
        if sub_name in seen_subs:
            errors.append(f"[{domain_key}] sub 重名:{sub_name!r}")
        seen_subs.add(sub_name)

        wake_words = sub.get("wake_words")
        if not isinstance(wake_words, list):
            errors.append(f"[{domain_key}] sub {sub_name!r} 缺少 wake_words 列表")
            continue
        for ww_entry in wake_words:
            if not isinstance(ww_entry, dict) or not ww_entry.get("wake_word"):
                errors.append(f"[{domain_key}] sub {sub_name!r} 存在缺 wake_word 的条目")
                continue
            ww = ww_entry["wake_word"]
            if ww in seen_ww_in_domain:
                errors.append(f"[{domain_key}] 唤醒词在域内重复:{ww!r}")
            seen_ww_in_domain.add(ww)

            scenes = ww_entry.get("scenes")
            if not isinstance(scenes, list):
                errors.append(f"[{domain_key}] 唤醒词 {ww!r} 缺少 scenes 列表")
                continue
            for sc in scenes:
                count += 1
                _validate_scene(sc, domain_key, ww, errors)
    return count


def _validate_scene(sc, domain_key: str, ww: str, errors: list):
    """校验单个场景条目"""
    if not isinstance(sc, dict):
        errors.append(f"[{domain_key}/{ww}] 场景条目必须是映射")
        return
    for field in REQUIRED_SCENE_FIELDS:
        if field not in sc:
            errors.append(f"[{domain_key}/{ww}] 场景缺字段 {field!r}(scenario_id={sc.get('scenario_id')!r})")
    html = sc.get("html")
    if isinstance(html, dict):
        for field in REQUIRED_HTML_FIELDS:
            if field not in html:
                errors.append(f"[{domain_key}/{ww}] html 缺字段 {field!r}(scenario_id={sc.get('scenario_id')!r})")
    prompt = sc.get("prompt", "")
    if not prompt or not prompt.strip():
        errors.append(f"[{domain_key}/{ww}] prompt 为空(scenario_id={sc.get('scenario_id')!r})")
    elif not prompt.strip().startswith(PROMPT_HEAD_PREFIX):
        errors.append(
            f"[{domain_key}/{ww}] prompt 首行不符合骨架(scenario_id={sc.get('scenario_id')!r}):"
            f" 应以 {PROMPT_HEAD_PREFIX!r} 开头,实际 {prompt.strip().splitlines()[0][:40]!r}"
        )


def build_summary(domain_data: dict) -> dict:
    """把 7 域数据合并为汇总结构(嵌套 sub → wake_word → scenes)"""
    scenes = []
    for d in DOMAINS:
        data = domain_data.get(d["key"])
        if data is None:
            continue  # 未枚举域:只出现在 domains meta,scenes 不含
        subs = []
        for sub in data.get("subs", []):
            ww_list = []
            for ww_entry in sub.get("wake_words", []):
                scenes_body = []
                for sc in ww_entry.get("scenes", []):
                    item = {k: sc.get(k) for k in REQUIRED_SCENE_FIELDS}
                    scenes_body.append(item)
                ww_list.append({"wake_word": ww_entry["wake_word"], "scenes": scenes_body})
            subs.append({"name": sub["name"], "wake_words": ww_list})
        scenes.append({"key": d["key"], "name": d["name"], "icon": d["icon"], "subs": subs})

    return {
        "version": VERSION,
        "skill": SKILL_NAME,
        "help_wake_words": HELP_WAKE_WORDS,
        "domains": [dict(d) for d in DOMAINS],
        "scenes": scenes,
    }


def collect_stats(summary: dict) -> dict:
    """统计:域数(已枚举)/场景数/唤醒词数/pending"""
    domain_count = len(summary["scenes"])
    scene_total = 0
    ww_total = 0
    pending = 0
    for dom in summary["scenes"]:
        for sub in dom["subs"]:
            for ww in sub["wake_words"]:
                ww_total += 1
                for sc in ww["scenes"]:
                    scene_total += 1
                    if sc.get("status"):
                        pending += 1
    return {
        "domains": domain_count,
        "wake_words": ww_total,
        "scenes": scene_total,
        "pending": pending,
    }


def validate_global(summary: dict, errors: list):
    """跨域全局校验:scenario_id 唯一 / 场景 id 唯一 / wake_word 唯一"""
    seen_sid = {}
    seen_id = {}
    seen_ww = {}
    for dom in summary["scenes"]:
        for sub in dom["subs"]:
            for ww in sub["wake_words"]:
                ww_key = ww["wake_word"]
                if ww_key in seen_ww:
                    errors.append(f"唤醒词全局重复:{ww_key!r}({seen_ww[ww_key]} 与 {dom['key']})")
                else:
                    seen_ww[ww_key] = dom["key"]
                for sc in ww["scenes"]:
                    sid = sc.get("scenario_id")
                    if sid in seen_sid:
                        errors.append(f"scenario_id 全局重复:{sid!r}({seen_sid[sid]} 与 {dom['key']})")
                    else:
                        seen_sid[sid] = dom["key"]
                    scid = sc.get("id")
                    if scid in seen_id:
                        errors.append(f"场景 id 全局重复:{scid!r}({seen_id[scid]} 与 {dom['key']})")
                    else:
                        seen_id[scid] = dom["key"]


def main():
    parser = argparse.ArgumentParser(description="饼干记账 · 场景合并器(域 yaml → 汇总)")
    parser.add_argument("--out", default=None, help="输出路径(默认 references/scenarios.yaml)")
    parser.add_argument("--check", action="store_true", help="只校验 + 与现有汇总对比(无 diff 通过),不写文件")
    args = parser.parse_args()

    errors = []
    domain_data = {}
    per_domain = {}
    for d in DOMAINS:
        data = load_domain_yaml(d["key"])
        if data is None:
            print(f"⏭  跳过未枚举域: {d['key']} ({d['name']})")
            continue
        count = validate(data, d["key"], errors)
        per_domain[d["key"]] = count
        domain_data[d["key"]] = data

    summary = build_summary(domain_data)
    validate_global(summary, errors)

    if errors:
        print(f"✗ 校验失败:{len(errors)} 个错误")
        for e in errors:
            print(f"  - {e}")
        return 1

    stats = collect_stats(summary)
    print(f"✓ 校验通过:已枚举域 {stats['domains']}/7,场景 {stats['scenes']} 个,唤醒词 {stats['wake_words']} 个,pending {stats['pending']}")
    for k, v in per_domain.items():
        print(f"   · {k}: {v} 场景")

    if args.check:
        if SUMMARY_PATH.exists():
            existing = SUMMARY_PATH.read_text(encoding="utf-8")
            new = dump_summary(summary)
            if existing.rstrip("\n") == new.rstrip("\n"):
                print(f"✓ 与现有汇总无 diff(一致性保持)")
                return 0
            print(f"✗ 汇总有 diff(需重新生成并提交)")
            return 1
        print(f"⚠ 汇总不存在({SUMMARY_PATH}),--check 无法对比")
        return 1

    output_path = Path(args.out) if args.out else SUMMARY_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(dump_summary(summary), encoding="utf-8")
    print(f"✓ 已生成汇总: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
