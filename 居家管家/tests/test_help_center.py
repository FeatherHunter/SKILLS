"""help_center.html 渲染验证(无浏览器,用 JS 模拟 DOM)"""
import subprocess
import re
import json
from pathlib import Path

HELP_HTML = Path(__file__).parent.parent / "templates" / "help_center.html"


def test_help_html_static():
    """HTML 结构正确性 + BUG FIX 验证"""
    h = HELP_HTML.read_text(encoding="utf-8")

    # BUG FIX 1: payload script 必须在 wrap 外
    payload_pos = h.find('id="payload"')
    wrap_pos = h.find('<div class="wrap">')
    assert payload_pos > 0 and wrap_pos > 0, "缺少 payload 或 wrap"
    assert payload_pos < wrap_pos, "BUG: payload script 仍在 wrap 内(innerHTML+= 会摧毁)"

    # BUG FIX 2: JS 中 group id 用纯英文序号(g-0, g-1, ...)
    assert "'g-' + i" in h or '"g-" + i' in h, "BUG: group id 应是纯英文 g-N 形式"

    # BUG FIX 3: 不应有 inline onclick 属性
    assert "onclick=" not in h, "BUG: 仍有 inline onclick"

    # BUG FIX 4: 不应有 wwIdOf 这种把 wake_word 直接当 id 的函数
    assert "wwIdOf" not in h, "BUG: 仍用 wake_word 当 id"

    # 必含的标签/函数
    for tag in ['<h1>', 'class="metrics"', 'class="toc"',
                "class=\"group", "class=\"scenarios", "class=\"scenario",
                "class=\"copy-btn", 'addEventListener', 'JSON.parse']:
        assert tag in h, f"缺少标签/函数: {tag}"


def test_help_html_renders():
    """用 Python 模拟 IIFE 关键路径,确认渲染产出"""
    import yaml, json
    from pathlib import Path
    SKILL = Path(__file__).parent.parent
    data = yaml.safe_load((SKILL / "references" / "scenarios.yaml").read_text(encoding="utf-8"))
    scenarios = data["scenarios"]

    # 分组
    grouped = {}
    for s in scenarios:
        grouped.setdefault(s["wake_word"], []).append(s)
    groups = [{"wake_word": w, "scenarios": ss} for w, ss in grouped.items()]
    # P1-9c-fix-2 后 7 个 update 子项合并 → 24 个唤醒词; ≥ 20 视为合规
    assert len(groups) >= 20, f"应 ≥ 20 个唤醒词,实际 {len(groups)}"

    # 核心唤醒词必须存在(防止合并过激)
    must_have = {"查物品", "看物品", "录物品", "改物品", "盘物品", "统物品",
                  "查过期", "看标签", "合标签", "查账号", "居家管家 帮助"}
    actual = {g["wake_word"] for g in groups}
    missing = must_have - actual
    assert not missing, f"缺失核心唤醒词: {missing}"

    # 合并不应出现 7 个旧 update 子项(总纲 03 §铁律 2)
    deprecated = {"修物品", "借物品", "废物品", "移物品", "补物品", "减物品", "标物品"}
    actual = {g["wake_word"] for g in groups}
    leaked = deprecated & actual
    assert not leaked, f"应已合并的 update 子项仍独立 group: {leaked}"

    # 所有 prompt 不暴露 CLI / DB / Python 路径(总纲 07 §2)
    for s in scenarios:
        p = s["prompt"]
        for forbidden in ["python", "home_manager", "cli", "sqlite", ".py", "scripts/"]:
            assert forbidden not in p.lower(), f"prompt 暴露实现细节: {p!r} 含 {forbidden!r}"

    # 7 字段齐全(总纲 07 §2.2)
    required_fields = {"wake_word", "scenario_id", "scenario_title",
                        "dimensions", "prompt", "status", "result"}
    for s in scenarios:
        missing = required_fields - set(s.keys())
        assert not missing, f"场景 {s.get('scenario_id', '?')} 缺字段: {missing}"

    # status 二态(07 §4): 仅空字符串 或 【待开发】
    for s in scenarios:
        assert s.get("status", "") in ("", "【待开发】"), \
            f"非法 status: {s.get('status')!r}"

    # P1-10 prompt 尾部填入形式(用户反馈:复制后不需删改)
    # 无字段场景(如 inventory_all) 可保持纯意图,无需 "请填入:"
    # 无字段场景(纯意图类)可保持简答,无 "请填入:";
    # 一律要求足 echo=on 的人类阅读体验:尾签可填。
    no_field_ids = {"inventory_all", "stats_summary", "outfit_pick",
                    "lint_health", "travel_return", "help_center",
                    "tag_list", "account_list", "search_express"}
    for s in scenarios:
        p = s.get("prompt", "")
        sid = s.get("scenario_id", "")
        if sid in no_field_ids:
            continue  # 无字段场景可不带 tail-input
        assert "请填入:" in p, f"prompt 缺尾部填入格式: {sid!r} → {p[:60]!r}"
        assert "___" in p, f"prompt 缺字段占位符 ___: {sid!r}"
        forbidden = ["[物品名]", "[位置]", "[标签]", "[状态]", "[N]", "[新值]",
                      "[旧位置]", "[新位置]", "[数量]", "[物品名,放在",
                      "[平台", "[用户名]", "[密码]", "[密钥]", "[日期]",
                      "[物品清单]", "[分类(衣物", "[参考物品名]"]
        bad = [f for f in forbidden if f in p]
        assert not bad, f"prompt {sid!r} 含旧占位符 {bad}"


def test_help_payload_via_skills_dir(tmp_path):
    """实际跑 `python home_manager.py help` 然后验证 payload JSON 解析成功"""
    import os, subprocess
    global json
    skill_dir = Path(__file__).parent.parent
    env = {
        **os.environ,
        "HOME": os.environ.get("HOME", "/tmp"),
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "SKILLS_DB_PATH": str(tmp_path),
    }
    out = tmp_path / "help.html"
    r = subprocess.run(
        ["python3", str(skill_dir / "scripts" / "home_manager.py"), "help", "--output", str(out)],
        capture_output=True, text=True, env=env, cwd=str(skill_dir / "scripts"),
        timeout=60,
    )
    assert r.returncode == 0, f"help 命令失败: {r.stderr}"
    assert out.exists(), "help.html 未生成"

    h = out.read_text(encoding="utf-8")

    # payload script 必须在 wrap 外(关键修复验证)
    payload_pos = h.find('id="payload"')
    wrap_pos = h.find('<div class="wrap">')
    assert payload_pos > 0 and wrap_pos > 0
    assert payload_pos < wrap_pos, f"BUG 未修: payload({payload_pos}) 不在 wrap({wrap_pos}) 之前"

    # JSON 解析必须成功(用户看到的内容源)
    import yaml
    m = re.search(r'<script id="payload" type="application/json">([\s\S]*?)</script>', h)
    assert m, "找不到 payload script"
    payload = json.loads(m.group(1))
    assert payload["status"] == "ok"
    assert payload["data"]["groups"]
    total_scenarios = sum(len(g["scenarios"]) for g in payload["data"]["groups"])
    yaml_data = yaml.safe_load((skill_dir / "references" / "scenarios.yaml").read_text(encoding="utf-8"))
    assert total_scenarios == len(yaml_data["scenarios"])