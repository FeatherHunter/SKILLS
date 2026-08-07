#!/usr/bin/env python3
"""
饼干记账 · HELP HTML 渲染器 v3.0(B2 全纵向折叠 · G4 决议落地)

数据源: references/scenarios.yaml(合并器产物 · 域 yaml 唯一事实源的汇总)
模板:   templates/help.html(B2 架构 · 复制自居家管家 help_center,适配饼干记账)

B2 特征(四级折叠 · 对标居家管家):
  一级 = 功能域(domains,7 域固定顺序)
  二级 = 子功能(sub,按场景出现顺序)
  三级 = 场景卡片(scene:id + 唤醒词 chip + 标题 + 复制 prompt)
  四级 = prompt 详情(展开后可见,深色代码块)
组件: hero 三步引导 / 首次使用横幅(状态驱动) / 搜索(跨域平铺) / 联系作者 / B1 toast
HELP 豁免复制数据/日志按钮(G4 D-3 · 导航类豁免)

输出:
  默认 $DATA_DIR/biscuit_accountant_html/饼干记账_HELP_<TS>.html(§12.B)
  同步镜像 SKILL 根目录 饼干记账.html(SKILL.md L10 强制)

用法:
    python3 scripts/render_help.py               # 默认输出 + 根目录镜像
    python3 scripts/render_help.py --out X.html  # 指定输出
    python3 scripts/render_help.py --check       # 只校验数据源,不写文件
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

try:
    import yaml
except ImportError:
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
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

SKILL_DIR = _SCRIPT_DIR.parent
SCENARIOS_PATH = SKILL_DIR / "references" / "scenarios.yaml"
TEMPLATE_PATH = SKILL_DIR / "templates" / "help.html"

DATA_PLACEHOLDER = "<!--INJECT-DATA-->"
SHARED_PLACEHOLDER = "<!--SHARED-HELPERS-->"

# 联系作者(仅 HELP · G4 决议:email/github/issues,无手机号)
CONTACT = {
    "email": "975559549@qq.com",
    "github": "https://github.com/FeatherHunter/SKILLS",
    "issues": "https://github.com/FeatherHunter/SKILLS/issues",
}

# HELP 唤醒词(与 SKILL.md §唤醒词总表 HELP 行同步 · 合并器/汇总同源)
HELP_WAKE_WORDS = ["饼干记账 HELP", "饼干记账 帮助", "查帮助", "能做什么"]


def load_summary() -> dict:
    """读合并器汇总(嵌套 sub → wake_word → scenes)"""
    if not SCENARIOS_PATH.exists():
        raise FileNotFoundError(f"场景汇总不存在(先跑合并器): {SCENARIOS_PATH}")
    with open(SCENARIOS_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data is None:
        raise ValueError(f"场景汇总为空: {SCENARIOS_PATH}")
    return data


def _is_initialized() -> bool:
    """初始化状态判定:DB 文件存在 = 已初始化(首次使用横幅隐藏)。

    env 覆盖:HELP_INITIALIZED=1/0 可强制指定(测试/镜像可重现性)。
    函数内 import + 每次调用重算路径,确保读取当前环境变量(测试可 monkeypatch)。
    """
    env = os.environ.get("HELP_INITIALIZED")
    if env is not None:
        return env.strip().lower() in ("1", "true", "yes")
    from db import DB_FILENAME, _find_db_path
    db_path = _find_db_path(SKILL_DIR, DB_FILENAME)
    return db_path.exists()


def build_help_payload(summary: dict) -> dict:
    """嵌套汇总 → B2 渲染 payload(domains[].subs[].scenes[] 展平)

    场景条目携带:id / wake_word / scenario_id / scenario_title / type / status /
                  prompt / result / sub / domain(供搜索与分组)
    """
    ts = os.environ.get("HELP_FIXED_TIMESTAMP") or datetime.now().strftime("%Y-%m-%d %H:%M")

    domains_meta = summary.get("domains", [])
    domains_data = {d["key"]: d for d in summary.get("scenes", [])}

    domains = []
    total_scenes = 0
    available = 0
    pending = 0
    for meta in domains_meta:
        key = meta["key"]
        dom = domains_data.get(key)
        subs = []
        if dom:
            for sub in dom.get("subs", []):
                scenes_flat = []
                for ww_entry in sub.get("wake_words", []):
                    ww = ww_entry["wake_word"]
                    for sc in ww_entry.get("scenes", []):
                        item = {
                            "id": sc.get("id", ""),
                            "wake_word": ww,
                            "scenario_id": sc.get("scenario_id", ""),
                            "scenario_title": sc.get("scenario_title", ""),
                            "type": sc.get("type", ""),
                            "status": sc.get("status", ""),
                            "prompt": sc.get("prompt", ""),
                            "result": sc.get("result", ""),
                            "sub": sub.get("name", ""),
                            "domain": key,
                        }
                        scenes_flat.append(item)
                        total_scenes += 1
                        if item["status"]:
                            pending += 1
                        else:
                            available += 1
                if scenes_flat:
                    subs.append({"name": sub.get("name", ""), "scenes": scenes_flat})
        domains.append({
            "key": key,
            "name": meta.get("name", key),
            "icon": meta.get("icon", "📦"),
            "subs": subs,
        })

    return {
        "status": "ok",
        "data": {
            "summary": {
                "title": "饼干记账 · 使用手册(HELP)",
                "subtitle": (
                    f"{len(domains_meta)} 功能域 · {total_scenes} 场景 · "
                    f"版本 {summary.get('version', '2.0')} · 更新于 {ts}"
                ),
                "metrics": [
                    {"label": "功能域", "value": str(len(domains_meta))},
                    {"label": "场景", "value": str(total_scenes)},
                    {"label": "可用", "value": str(available)},
                    {"label": "待开发", "value": str(pending)},
                ],
                "version": summary.get("version", "2.0"),
                "generated_at": ts,
            },
            "initialized": _is_initialized(),
            "domains": domains,
            "contact": CONTACT,
            "help_wake_words": summary.get("help_wake_words", HELP_WAKE_WORDS),
        },
        "message": "HELP 场景清单",
    }


def render_help(payload: dict, output_path: Path) -> Path:
    """注入 payload 到模板(INJECT-DATA + SHARED-HELPERS),写文件(utf-8-sig BOM)"""
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"模板不存在: {TEMPLATE_PATH}")

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    if template.count(DATA_PLACEHOLDER) != 1:
        raise RuntimeError(
            f"模板占位符 {DATA_PLACEHOLDER} 数量异常: 期望 1, 实际 {template.count(DATA_PLACEHOLDER)}"
        )
    shared_count = template.count(SHARED_PLACEHOLDER)
    if shared_count > 1:
        raise RuntimeError(f"模板 {SHARED_PLACEHOLDER} 最多出现 1 次,实际 {shared_count}")

    if shared_count == 1:
        from _shared_js import SHARED_JS
        template = template.replace(SHARED_PLACEHOLDER, SHARED_JS.strip(), 1)

    payload_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    template = template.replace(DATA_PLACEHOLDER, payload_json, 1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(template, encoding="utf-8-sig")
    return output_path


def default_output_path() -> Path:
    """默认输出路径(§12.B):$DATA_DIR/biscuit_accountant_html/饼干记账_HELP_<TS>[_N].html"""
    from html_paths import html_path
    return html_path("饼干记账_HELP")


def main():
    parser = argparse.ArgumentParser(description="饼干记账 · HELP 渲染器(B2)")
    parser.add_argument("--out", default=None, help="输出 HTML 路径")
    parser.add_argument("--check", action="store_true", help="只校验数据源与模板,不写文件")
    args = parser.parse_args()

    summary = load_summary()
    payload = build_help_payload(summary)
    data = payload["data"]
    print(f"📥 HELP 渲染(B2)")
    print(f"   场景汇总: {SCENARIOS_PATH}")
    print(f"   功能域: {len(data['domains'])} 个 · 场景: {data['summary']['metrics'][1]['value']} 个 · 待开发: {data['summary']['metrics'][3]['value']} 个")

    if args.check:
        print(f"\n✓ 校验通过(未写文件)")
        return 0

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    if template.count(DATA_PLACEHOLDER) != 1 or template.count(SHARED_PLACEHOLDER) > 1:
        raise RuntimeError("模板占位符异常(INJECT-DATA 必须 1 个,SHARED-HELPERS 最多 1 个)")

    output_path = Path(args.out) if args.out else default_output_path()
    render_help(payload, output_path)

    # 同步一份到 SKILL 根目录(SKILL.md L10 强制)
    skill_root_copy = SKILL_DIR / "饼干记账.html"
    skill_root_copy.write_bytes(output_path.read_bytes())
    print(f"✓ 已同步: {skill_root_copy}  (SKILL.md L10 镜像)")

    print(f"\n✓ 已生成: {output_path}")
    print(f"  用浏览器打开即可查看。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
