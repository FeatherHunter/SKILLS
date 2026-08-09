"""居家管家 v2.0 HELP 中心渲染器(总纲 07 § · G8 规格 · 变体 B 生产化)

输入: references/scenarios.yaml(场景资产唯一事实源 · 9 域 59 场景)
输出: help_center.html(变体 B 一屏直达: hero + 首次使用横幅 + sticky 搜索 + 4 层折叠 + 联系作者)

分组策略(v2.0 · G1/G7 定稿):
  一级 = 9 功能域(domains,顺序固定)
  二级 = 子功能(sub,按场景出现顺序)
  三级 = 场景卡片(scene)
  四级 = prompt 详情(展开后可见)

状态注入(P1 裁决 #3 · 2026-08-05):
  首次使用横幅 = 状态驱动,初始化完成后整个区域消失。
  生产 = render 时从库注入初始化状态:DB 文件存在 → 已初始化(横幅隐藏);
  不存在 → 未初始化(横幅显示)。重装/换电脑重新出现。

不展示 HELP 自身(07 §核心规则 2)。
"""
import os
import sys
import yaml
from pathlib import Path
from datetime import datetime

SKILL_DIR = Path(__file__).parent.parent
SCENARIOS = SKILL_DIR / "references" / "scenarios.yaml"
TEMPLATE = "help_center.html"

# 联系作者(仅 HELP · G7 决策补充 2026-08-04)
# 不含手机号:开源 PII 保护(issue #150 · 人类明确约束)
CONTACT = {
    "email": "975559549@qq.com",
    "github": "https://github.com/FeatherHunter/SKILLS",
    "issues": "https://github.com/FeatherHunter/SKILLS/issues",
}


def _is_initialized() -> bool:
    """初始化状态判定:DB 文件存在 = 已初始化(首次使用横幅隐藏)。

    env 覆盖:HELP_INITIALIZED=1/0 可强制指定(测试/镜像可重现性)。
    函数内 import + 每次调用重算路径,确保读取当前环境变量(测试可 monkeypatch)。
    """
    env = os.environ.get("HELP_INITIALIZED")
    if env is not None:
        return env.strip().lower() in ("1", "true", "yes")
    from home_manager.db import DB_FILENAME, _find_db_path
    db_path = _find_db_path(SKILL_DIR, DB_FILENAME)
    return db_path.exists()


def build_help_payload() -> dict:
    """读 scenarios.yaml → 渲染 payload(v2.0 · 9 域结构)

    分组规则:
      一级 = domain(domains 列表顺序,9 域固定)
      二级 = sub(按场景出现顺序去重)
      三级 = 场景(按 yaml 出现顺序)
    每场景携带: id / wake_word / scenario_title / type(08 流程类型徽章)/
                status(二态)/ prompt / result / html 映射字段
    """
    data = yaml.safe_load(SCENARIOS.read_text(encoding="utf-8"))
    domains_meta = data.get("domains", [])
    scenarios = data.get("scenarios", [])

    # 时间戳: 支持环境变量固定(构建时 / 测试时一致),默认当前时间
    ts = os.environ.get("HELP_FIXED_TIMESTAMP") or datetime.now().strftime('%Y-%m-%d %H:%M')

    # 域元信息索引
    meta_by_key = {d["key"]: d for d in domains_meta}

    # 按 domain 分组(保插入序)
    by_domain = {}
    for s in scenarios:
        by_domain.setdefault(s.get("domain", "其他"), []).append(s)

    domains = []
    total_wake = set()
    available = 0
    pending = 0
    for d in domains_meta:
        key = d["key"]
        scenes = by_domain.get(key, [])
        # 子功能分组(保序)
        subs = []
        seen = set()
        for s in scenes:
            sub = s.get("sub", "其他")
            if sub not in seen:
                seen.add(sub)
                subs.append({"name": sub, "scenes": [s for s in scenes if s.get("sub") == sub]})
        for s in scenes:
            total_wake.add(s.get("wake_word", ""))
            if s.get("status", "") == "":
                available += 1
            else:
                pending += 1
        domains.append({
            "key": key,
            "name": d["name"],
            "icon": d.get("icon", "📦"),
            "sm": d.get("sm", ""),
            "subs": subs,
        })

    return {
        "status": "ok",
        "data": {
            "summary": {
                "title": "居家管家 · 使用手册(HELP)",
                "subtitle": f"9 功能域 · {len(scenarios)} 场景 · 版本 {data.get('version', '2.0')} · 更新于 {ts}",
                "metrics": [
                    {"label": "功能域", "value": str(len(domains_meta))},
                    {"label": "场景", "value": str(len(scenarios))},
                    {"label": "可用", "value": str(available)},
                    {"label": "待开发", "value": str(pending)},
                ],
                "version": data.get("version", "2.0"),
                "generated_at": ts,
            },
            "initialized": _is_initialized(),
            "domains": domains,
            "contact": CONTACT,
        },
        "message": "HELP 中心",
    }


if __name__ == "__main__":
    from render import render_page
    payload = build_help_payload()
    out = sys.argv[1] if len(sys.argv) > 1 else None
    print(render_page(TEMPLATE, payload, out))
