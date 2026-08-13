#!/usr/bin/env python3
"""
饼干记账 · HELP HTML 渲染器 v4.0(Base 参数化 HELP · #303 task ④)

数据源: references/scenarios.yaml(合并器产物 · 7 域 scenes yaml 唯一事实源)
模板:   公共组件/assets/help_template.html(Base 参数化模板 · V4.16 定稿 · scene-data 契约 v1)
注入:   公共组件/injector.py(validate_help_data 硬拦截 + inject)

v4.0 变化(#303 · 2026-08-13):
- 原 templates/help.html 完全废弃删除(Base 统一模板,技能零模板副本 · 统一规则②)
- scene_data 技能侧展平: 7 域 → groups / sub → subgroups / wake_word 层消失并入场景卡 chip
  (源 yaml 3 层结构不动: 合并器 + 21 测试 + 7 域 CLI 对齐注释零改动)
- scripts/_shared_js.py 退役删除(唯一消费者 render_help.py 重写后消失)
- HELP 命名契约保留: $DATA_DIR/biscuit_accountant_html/饼干记账_HELP_<TS>.html + 根镜像 饼干记账.html
- 输出保持 utf-8-sig BOM(ADR-0002)

用法:
    python3 scripts/render_help.py               # 默认输出 + 根目录镜像
    python3 scripts/render_help.py --out X.html  # 指定输出
    python3 scripts/render_help.py --check       # 只校验数据源与契约,不写文件
"""

import os
import sys
import json
import argparse
import importlib.util
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
BASE_SKILL_DIR = SKILL_DIR.parent / "公共组件"
SCENARIOS_PATH = SKILL_DIR / "references" / "scenarios.yaml"
HELP_TEMPLATE_PATH = BASE_SKILL_DIR / "assets" / "help_template.html"

# 联系作者(仅 HELP · G4 决议:email/github/issues,无手机号)
CONTACT = {
    "email": "975559549@qq.com",
    "github": "https://github.com/FeatherHunter/SKILLS",
    "issues": "https://github.com/FeatherHunter/SKILLS/issues",
}

# HELP 唤醒词(与 SKILL.md §唤醒词总表 HELP 行同步 · 合并器/汇总同源)
HELP_WAKE_WORDS = ["饼干记账 HELP", "饼干记账 帮助", "查帮助", "能做什么"]

# 首次使用横幅文案(与旧 B2 模板一致 · 状态驱动:未初始化显示)
INIT_BANNER_TEXT = {
    "title": "🚀 第一次用饼干记账?",
    "subtitle": "从「初始化」开始 — 自动检测环境、确认数据目录、建库、验证,全程零决策。"
                "完成初始化后,本区域将不再出现。",
    "button_text": "📋 复制初始化 prompt",
}

# 初始化向导场景 id(横幅 prompt 取自该场景,逐字一致)
SETUP_INIT_SCENE_ID = "setup_init_wizard"


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


def _base_injector():
    """懒加载 Base 注入器(公共组件/injector.py), importlib 按文件路径加载防撞名。"""
    injector_path = BASE_SKILL_DIR / "injector.py"
    if not injector_path.exists():
        raise RuntimeError("Base Skill 资产缺失: 找不到 公共组件/injector.py")
    spec = importlib.util.spec_from_file_location("base_injector", injector_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _base_assets():
    """Base 公共 JS/CSS 资产文本(base.js / base.css)"""
    assets = BASE_SKILL_DIR / "assets"
    js = (assets / "base.js").read_text(encoding="utf-8").strip()
    css = (assets / "base.css").read_text(encoding="utf-8").strip()
    return js, css


def _find_setup_prompt(summary: dict):
    """取初始化向导场景 prompt(横幅复制内容);找不到返回 None(横幅不渲染)"""
    for dom in summary.get("scenes", []):
        for sub in dom.get("subs", []):
            for ww_entry in sub.get("wake_words", []):
                for sc in ww_entry.get("scenes", []):
                    if sc.get("scenario_id") == SETUP_INIT_SCENE_ID:
                        return sc.get("prompt", "")
    return None


def build_help_contract(summary: dict, *, initialized: bool | None = None,
                        ts: str | None = None) -> dict:
    """嵌套汇总 → scene-data 契约 v1(groups→subgroups→scenes)

    映射(#303 票面执行清单 1):
      - domains[].key/icon/name → groups[](7 Tab)
      - subs[].name → subgroups[](折叠组)
      - wake_words[] 层消失 → scenes[].wake_word(chip)
      - scenes[]: id → scenario_id / title → scenario_title / types[] ← type 单值包数组
                  prompt_template ← prompt / status 透传(现全空 = 可用)
      - metrics(7 域/71 场景/版本/时间戳) → 契约 title/subtitle + meta_blocks 透传
      - editable_fields 默认不接入(prompt 保持文本形态,#303 grilling Q 决议)
    """
    if ts is None:
        ts = os.environ.get("HELP_FIXED_TIMESTAMP") or datetime.now().strftime("%Y-%m-%d %H:%M")
    if initialized is None:
        initialized = _is_initialized()

    domains_meta = summary.get("domains", [])
    domains_data = {d["key"]: d for d in summary.get("scenes", [])}
    version = str(summary.get("version", "2.0"))

    groups = []
    total_scenes = 0
    for meta in domains_meta:
        key = meta["key"]
        dom = domains_data.get(key)
        subgroups = []
        if dom:
            for sub in dom.get("subs", []):
                scenes = []
                for ww_entry in sub.get("wake_words", []):
                    ww = ww_entry["wake_word"]
                    for sc in ww_entry.get("scenes", []):
                        item = {
                            "id": sc.get("scenario_id", ""),
                            "title": sc.get("scenario_title", ""),
                            "wake_word": ww,
                            "status": sc.get("status", ""),
                            "prompt_template": sc.get("prompt", ""),
                        }
                        t = sc.get("type", "")
                        if t:
                            item["types"] = [t]
                        scenes.append(item)
                        total_scenes += 1
                if scenes:
                    subgroups.append({
                        "id": f"{key}_{len(subgroups) + 1}",
                        "label": sub.get("name", ""),
                        "scenes": scenes,
                    })
        groups.append({
            "id": key,
            "icon": meta.get("icon", "grid"),
            "label": meta.get("name", key),
            "subgroups": subgroups,
        })

    summary_line = (f"{len(domains_meta)} 功能域 · {total_scenes} 场景 · "
                    f"版本 {version} · 更新于 {ts}")
    contract = {
        "skill_name": "饼干记账",
        # 大标题含技能名(验收反馈 #303:技能名应在大字行;eyebrow 小字仍显示技能名,9px 可接受)
        "title": "饼干记账 · 使用手册(HELP)",
        "subtitle": summary_line,
        "meta_blocks": [
            {"id": "help_summary", "title": "HELP 汇总", "html": f"<p>{summary_line}</p>"},
            {"id": "help_wake_words", "title": "HELP 唤醒词",
             "html": "<p>" + " / ".join(summary.get("help_wake_words", HELP_WAKE_WORDS)) + "</p>"},
        ],
        "contact": {
            "items": [
                {"label": "邮箱", "value": CONTACT["email"]},
                {"label": "GitHub", "value": CONTACT["github"], "url": True},
                {"label": "Issues", "value": CONTACT["issues"], "url": True},
            ],
            "copy_all": True,
        },
        "version": version,
        "groups": groups,
    }

    if not initialized:
        setup_prompt = _find_setup_prompt(summary)
        if setup_prompt:
            contract["init_banner"] = {
                "title": INIT_BANNER_TEXT["title"],
                "subtitle": INIT_BANNER_TEXT["subtitle"],
                "button_text": INIT_BANNER_TEXT["button_text"],
                "prompt": setup_prompt,
                "closable": True,
            }
    return contract


def render_html(contract: dict) -> str:
    """Base help_template 注入:契约校验(硬拦截) + 3 占位符注入(js/css/data)。"""
    if not HELP_TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Base HELP 模板缺失: {HELP_TEMPLATE_PATH}")
    template = HELP_TEMPLATE_PATH.read_text(encoding="utf-8")
    mod = _base_injector()
    ok, msg = mod.validate_help_data(contract)
    if not ok:
        raise ValueError(f"HELP 数据校验失败: {msg}")
    js, css = _base_assets()
    html, err = mod.inject(template, contract, js_asset=js, css_asset=css, strict=False)
    if err:
        raise RuntimeError(f"Base 注入失败: {err}")
    return html


def default_output_path() -> Path:
    """默认输出路径(§12.B):$DATA_DIR/biscuit_accountant_html/饼干记账_HELP_<TS>[_N].html"""
    from html_paths import html_path
    return html_path("饼干记账_HELP")


def main():
    parser = argparse.ArgumentParser(description="饼干记账 · HELP 渲染器(v4.0 · Base 参数化)")
    parser.add_argument("--out", default=None, help="输出 HTML 路径")
    parser.add_argument("--check", action="store_true", help="只校验数据源与契约,不写文件")
    args = parser.parse_args()

    summary = load_summary()
    contract = build_help_contract(summary)
    n_groups = len(contract["groups"])
    n_scenes = sum(len(sg["scenes"]) for g in contract["groups"] for sg in g["subgroups"])
    print(f"📥 HELP 渲染(v4.0 · Base 参数化)")
    print(f"   场景汇总: {SCENARIOS_PATH}")
    print(f"   功能域: {n_groups} 个 · 场景: {n_scenes} 个")

    if args.check:
        # 契约校验(硬拦截)通过才打印通过
        render_html(contract)
        print(f"\n✓ 校验通过(数据源 + 契约,未写文件)")
        return 0

    html = render_html(contract)
    output_path = Path(args.out) if args.out else default_output_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8-sig")

    # 同步一份到 SKILL 根目录(SKILL.md L10 强制 · 字节一致)
    skill_root_copy = SKILL_DIR / "饼干记账.html"
    skill_root_copy.write_bytes(output_path.read_bytes())
    print(f"✓ 已同步: {skill_root_copy}  (SKILL.md L10 镜像)")

    print(f"\n✓ 已生成: {output_path}")
    print(f"  用浏览器打开即可查看。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
