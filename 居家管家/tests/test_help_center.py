"""help_center.html v2.0 渲染验证(变体 B 一屏直达 · G8 规格 · fixture 无浏览器)

覆盖(G6 质量关卡):
- 模板结构:payload 在 wrap 外 / 原生 details 折叠 / 复制按钮 preventDefault 守护
- 场景资产契约(07 §2.2/§4):7 字段 + 9 域 + status 二态 + prompt 不暴露实现
- CLI 端到端:python home_manager.py help 生成 → payload JSON 解析 → 场景数一致
- 状态驱动(P1 裁决 #3):HELP_INITIALIZED env 覆盖初始化状态
"""
import os
import re
import json
import subprocess
import sys
from pathlib import Path

import yaml

SKILL = Path(__file__).parent.parent
HELP_HTML = SKILL / "templates" / "help_center.html"
SCENARIOS = SKILL / "references" / "scenarios.yaml"

DOMAIN_KEYS = ["items", "space", "outfit", "stats", "express",
               "receipt", "family", "setup", "link"]


def _load_data():
    return yaml.safe_load(SCENARIOS.read_text(encoding="utf-8"))


# ────────────────────────────────────────────────────────────
# 模板结构静态断言
# ────────────────────────────────────────────────────────────
def test_help_html_static():
    """HTML 结构正确性(v2.0 变体 B 必含元素)"""
    h = HELP_HTML.read_text(encoding="utf-8")

    # payload script 必须在 wrap 外(innerHTML+= 不摧毁注入数据)
    payload_pos = h.find('id="payload"')
    wrap_pos = h.find('<div class="wrap">')
    assert payload_pos > 0 and wrap_pos > 0, "缺少 payload 或 wrap"
    assert payload_pos < wrap_pos, "BUG: payload script 在 wrap 内(会摧毁)"

    # 必含元素(变体 B 一屏直达;模块/场景由 JS 动态构建,断言 className 构建器)
    for tag in ['<h1>', 'class="hero"', 'class="init-banner"', 'class="search-wrap"',
                'className=\'module\'', 'className=\'sub-module\'', 'className=\'scene\'',
                'type-badge', 'dev-banner', 'class="contact-box"',
                'class="copy-btn"', 'class="toast"', 'addEventListener', 'JSON.parse',
                'scenario_id']:
        assert tag in h, f"缺少标签/函数: {tag}"

    # 注入占位符(渲染器硬要求)
    assert h.count("<!--INJECT-DATA-->") == 1, "必须恰好 1 个 INJECT-DATA 占位符"
    assert "<!--SHARED-HELPERS-->" in h, "必须使用 SHARED-HELPERS 占位符"


def test_help_html_fold_mechanism():
    """折叠机制:原生 details/summary + 场景头部复制按钮 preventDefault 守护

    场景卡片头部(L3)复制按钮在 <summary> 内 —— 必须 preventDefault +
    stopPropagation,否则点击复制会触发 details toggle(整卡展开/收起)。
    """
    h = HELP_HTML.read_text(encoding="utf-8")

    # 1. 折叠用原生 details(浏览器内核处理,不靠 JS 委托)
    assert "createElement('details');m.className='module'" in h, "L1 域应为原生 details + module className"
    assert "createElement('details');se.className='sub-module'" in h, "L2 子功能应为原生 details"
    assert "createElement('details');card.className='scene'" in h, "L3 场景应为原生 details"
    assert "<summary>" in h, "应有 <summary>"

    # 2. 场景头部复制按钮 onclick 必须拦截 toggle
    assert "preventDefault" in h and "stopPropagation" in h, \
        "L3 复制按钮必须 preventDefault + stopPropagation(防 details toggle 冲突)"
    # 3. prompt 详情内复制按钮(L4)同样 stopPropagation
    assert "pin.onclick=function(e){if(e)e.stopPropagation" in h, \
        "L4 复制按钮必须 stopPropagation"

    # 4. 旧 div+JS 委托模式必须消失
    assert 'class="group-h"' not in h and 'class="s-head"' not in h, \
        "旧 v1 委托模式残留"


def test_help_html_has_no_self_reference():
    """HELP 不展示自身(07 §核心规则 2:避免死循环)"""
    h = HELP_HTML.read_text(encoding="utf-8")
    assert "居家管家 帮助" not in h or "help_center" not in h, \
        "HELP HTML 不应展示 HELP 自身唤醒词"


def test_help_html_no_internal_info():
    """用户可见文案不得泄漏内部实现(07 §prompt 抽象精神)

    开发内部信息:SM 编号/已定稿/yaml 路径/总纲引用 —— 都不应出现在
    用户可见的 HELP HTML 中(元信息可在 payload 保留,模板不渲染)。
    """
    h = HELP_HTML.read_text(encoding="utf-8")
    # 模板层:开发标签/内部路径不应被渲染
    assert "已定稿" not in h, "模块头不应显示 'SM1 已定稿' 开发标签"
    assert "references/scenarios.yaml 渲染" not in h, "不应暴露 yaml 路径"
    assert "总纲 07" not in h, "不应暴露总纲内部引用"
    # payload 构建层:subtitle 应用户友好
    from help_center import build_help_payload
    payload = build_help_payload()
    sub = payload["data"]["summary"]["subtitle"]
    assert "references" not in sub and "总纲" not in sub, \
        f"subtitle 泄漏内部信息: {sub}"
    assert "更新于" in sub, "subtitle 应有用户可读的更新时间"


def test_help_html_init_banner_hidden_css():
    """首次使用横幅状态驱动守护(2026-08-06 修复)

    BUG 根因:.init-banner{display:flex} 覆盖 hidden 属性 UA 样式 display:none,
    导致横幅无论 initialized 与否都显示(用户反馈:HELP 一直提示第一次使用)。
    修复:.init-banner[hidden]{display:none} 恢复 hidden 语义。
    """
    h = HELP_HTML.read_text(encoding="utf-8")
    assert ".init-banner[hidden]{display:none}" in h, \
        "必须显式 .init-banner[hidden]{display:none}(防 display:flex 覆盖 hidden)"
    assert 'id="initBanner" hidden' in h, "横幅元素默认必须带 hidden 属性"
    assert "initBanner.hidden=false" in h, "仅未初始化时移除 hidden"


def test_help_html_deep_link():
    """#hash 场景直达:展开祖先链 + 定位(体验增强 · 对抗式审查 #1)"""
    h = HELP_HTML.read_text(encoding="utf-8")
    assert "function goToScene(" in h, "缺 goToScene 直达函数"
    assert "function openChain(" in h, "缺 openChain 祖先链展开"
    assert "location.hash" in h, "缺 hash 解析"
    assert "scrollIntoView" in h, "缺滚动定位"
    assert "getElementById('s-'+scenario_id)" in h, "场景卡片 id 必须为 s-{scenario_id}"


def test_help_html_search_shortcut():
    """/ 快捷键聚焦搜索(体验增强 · 对抗式审查 #3)"""
    h = HELP_HTML.read_text(encoding="utf-8")
    assert "e.key==='/'" in h, "缺 / 快捷键"
    assert "isContentEditable" in h, "输入态必须忽略快捷键"
    assert "preventDefault" in h, "快捷键必须 preventDefault"


def test_help_html_mobile_touch_target():
    """移动端场景头部一行布局:复制按钮视觉紧凑(28px,与行内元素平衡)+ 标题截断(体验增强 · 对抗式审查 #2)"""
    h = HELP_HTML.read_text(encoding="utf-8")
    assert "min-height:28px" in h, "移动端复制按钮应视觉紧凑(28px,与 chip/徽章平衡)"
    assert ".scene-head .scene-id{display:none}" in h, "移动端应隐藏低价值 scene-id(一行布局)"
    assert "text-overflow:ellipsis" in h, "移动端标题必须截断(一行布局)"


# ────────────────────────────────────────────────────────────
# 场景资产契约(07 §2.2 / §4)
# ────────────────────────────────────────────────────────────
def test_scenarios_schema_contract():
    """59 场景落库:7 字段契约 + 9 域 + 二态 + prompt 契约"""
    data = _load_data()
    assert data.get("version") == "2.0", "版本应为 2.0"
    assert len(data.get("domains", [])) == 9, "应为 9 功能域"
    assert [d["key"] for d in data["domains"]] == DOMAIN_KEYS, "9 域 key 顺序固定"

    scenarios = data["scenarios"]
    assert len(scenarios) >= 56, f"应 ≥ 56 场景,实际 {len(scenarios)}"

    # 07 §2.2 最小必填 7 字段 + v2.0 扩展字段
    required = {"wake_word", "scenario_id", "scenario_title", "dimensions",
                "prompt", "status", "result"}
    extended = {"id", "domain", "sub", "type", "html"}
    for s in scenarios:
        missing = required - set(s.keys())
        assert not missing, f"场景 {s.get('scenario_id', '?')} 缺字段: {missing}"
        missing_x = extended - set(s.keys())
        assert not missing_x, f"场景 {s.get('scenario_id', '?')} 缺 v2 扩展字段: {missing_x}"
        assert s["domain"] in DOMAIN_KEYS, f"{s['scenario_id']} domain 非法: {s['domain']}"
        assert s.get("html", {}).get("command_cn"), \
            f"{s['scenario_id']} 缺 html.command_cn(HTML 映射字段)"

    # status 二态(07 §4):空字符串 或 【待开发】
    for s in scenarios:
        assert s.get("status", "") in ("", "【待开发】"), \
            f"非法 status: {s.get('status')!r}"

    # prompt 契约(07 §6):不暴露 CLI / DB / Python / 模板路径
    for s in scenarios:
        p = s["prompt"]
        for forbidden in ["python", "home_manager", "cli", "sqlite", ".py", "scripts/"]:
            assert forbidden not in p.lower(), f"prompt 暴露实现细节: {s['scenario_id']} 含 {forbidden!r}"

    # 唤醒词非空 + 场景 id 唯一
    ids = [s["scenario_id"] for s in scenarios]
    assert len(ids) == len(set(ids)), "scenario_id 必须唯一"
    for s in scenarios:
        assert s["wake_word"].strip(), f"{s['scenario_id']} 唤醒词为空"


def test_domains_match_scene_grouping():
    """每个域都有场景,无孤儿域(场景子功能分组完整)"""
    data = _load_data()
    scenarios = data["scenarios"]
    for d in data["domains"]:
        scenes = [s for s in scenarios if s["domain"] == d["key"]]
        assert scenes, f"域 {d['key']} 无场景"
        subs = {s["sub"] for s in scenes}
        assert len(subs) >= 1, f"域 {d['key']} 无子功能"


def test_first_use_scene_exists():
    """首次使用场景位必须存在(P1 裁决 #3:初始化横幅 = 状态驱动场景位)"""
    data = _load_data()
    first_use = [s for s in data["scenarios"] if s["scenario_id"] == "first_use"]
    assert len(first_use) == 1, "必须存在 first_use 场景(初始化横幅数据源)"
    assert first_use[0]["wake_word"] == "首次使用"


# ────────────────────────────────────────────────────────────
# CLI 端到端 + 状态驱动
# ────────────────────────────────────────────────────────────
def test_help_payload_via_skills_dir(tmp_path):
    """实际跑 `python home_manager.py help` 验证 payload JSON(v2.0 9 域结构)"""
    env = {
        **os.environ,
        "HOME": os.environ.get("HOME", "/tmp"),
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "SKILLS_DB_PATH": str(tmp_path),
    }
    out = tmp_path / "help.html"
    r = subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "home_manager.py"), "help", "--output", str(out)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=env, cwd=str(SKILL / "scripts"),
        timeout=60,
    )
    assert r.returncode == 0, f"help 命令失败: {r.stderr}"
    assert out.exists(), "help.html 未生成"

    h = out.read_text(encoding="utf-8")

    # payload script 必须在 wrap 外
    payload_pos = h.find('id="payload"')
    wrap_pos = h.find('<div class="wrap">')
    assert payload_pos > 0 and wrap_pos > 0
    assert payload_pos < wrap_pos, f"BUG: payload({payload_pos}) 不在 wrap({wrap_pos}) 之前"

    m = re.search(r'<script id="payload" type="application/json">([\s\S]*?)</script>', h)
    assert m, "找不到 payload script"
    payload = json.loads(m.group(1))
    assert payload["status"] == "ok"
    data = payload["data"]

    # 9 域结构
    assert len(data["domains"]) == 9, "payload 应为 9 域"
    total_scenes = sum(
        len(scene)
        for dom in data["domains"]
        for sub in dom["subs"]
        for scene in [sub["scenes"]]
    )
    yaml_data = yaml.safe_load(SCENARIOS.read_text(encoding="utf-8"))
    assert total_scenes == len(yaml_data["scenarios"]), "payload 场景数 ≠ yaml 场景数"

    # 每场景必含渲染字段
    for dom in data["domains"]:
        for sub in dom["subs"]:
            for s in sub["scenes"]:
                for field in ["id", "wake_word", "scenario_title", "type", "status", "prompt"]:
                    assert field in s, f"payload 场景缺 {field}: {s.get('scenario_id')}"

    # 联系作者区(仅 HELP · G7)
    assert data.get("contact", {}).get("email"), "payload 缺联系作者 email"

    # 状态驱动字段
    assert "initialized" in data, "payload 缺 initialized 字段"


def test_help_initialized_env_override(tmp_path, monkeypatch):
    """初始化状态 env 覆盖(HELP_INITIALIZED=1/0)"""
    from help_center import _is_initialized
    monkeypatch.setenv("HELP_INITIALIZED", "1")
    assert _is_initialized() is True
    monkeypatch.setenv("HELP_INITIALIZED", "0")
    assert _is_initialized() is False
    monkeypatch.delenv("HELP_INITIALIZED")
    # 无 env → 按 DB 文件存在性判断(tmp_path 空目录 = 未初始化)
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    assert _is_initialized() is False
    # DB 文件存在 = 已初始化
    (tmp_path / "home.db").write_text("x", encoding="utf-8")
    assert _is_initialized() is True
