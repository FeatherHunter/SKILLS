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

    # BUG FIX 2: JS 中 group id 用纯英文序号(P1-11b 后是 cat-0/cat-1 类别)
    assert "'cat-' + i" in h or '"cat-" + i' in h, "BUG: group id 应是纯英文 cat-N 形式"

    # BUG FIX 3: 不应有 inline onclick 属性
    assert "onclick=" not in h, "BUG: 仍有 inline onclick"

    # BUG FIX 4: 不应有 wwIdOf 这种把 wake_word 直接当 id 的函数
    assert "wwIdOf" not in h, "BUG: 仍用 wake_word 当 id"

    # 必含的标签/函数(round 2 对齐卡路里 HELP v2 风格)
    for tag in ['<h1>', 'class="hero"', 'class="stats"', 'class="toc"',
                "class=\"group", "class=\"scenarios", "class=\"scenario",
                "class=\"copy-btn", "class=\"toast", "class=\"variant-block",
                'addEventListener', 'JSON.parse']:
        assert tag in h, f"缺少标签/函数: {tag}"


def test_help_html_fold_mechanism():
    """折叠机制回归守护(2026-07-29 修复:querySelector('.wrap') 委托失效 bug)

    根因:旧版用 <div class="group-h"> + JS classList.toggle('open') 事件委托,
    且委托绑在 document.querySelector('.wrap'),而页面有 2 个 .wrap(hero 一个、
    主内容一个),querySelector 返回第一个(hero),导致主内容区的 group-h/s-head
    点击事件永不触发 → 一级、二级都无法展开折叠,违反总纲 §07 §148
    ("dimensions/result/prompt 详情可以折叠但必须能展开查看")。

    修复:对齐卡路里/作息管家,改用原生 <details>/<summary>,折叠由浏览器内核处理,
    零 JS 也能展开;复制按钮移出 summary 放入 s-body,避免 summary toggle 冲突。

    本测试用纯字符串断言守护此修复,防止回归(无需浏览器/jsdom)。
    """
    h = HELP_HTML.read_text(encoding="utf-8")

    # 1. 折叠用原生 details(浏览器内核处理,不靠 JS 委托)
    assert "details class=\"group\"" in h, "L1 group 应为原生 <details class=\"group\">"
    assert "details class=\"scenario\"" in h, "L2 scenario 应为原生 <details class=\"scenario\">"
    assert "<summary>" in h, "应有 <summary>"

    # 2. 旧的 div+JS 委托模式必须彻底消失(根因消除)
    # 注意:用精确匹配(class= / CSS 选择器 .group-h),避免误伤注释/文档里的 "s-head" 文本
    assert 'class="group-h"' not in h, "BUG: 仍有 class=\"group-h\"(应改用 <summary>)"
    assert 'class="s-head"' not in h, "BUG: 仍有 class=\"s-head\"(应改用 <summary>)"
    assert ".group-h" not in h, "BUG: CSS 仍有 .group-h 选择器"
    assert ".s-head{" not in h and ".s-head " not in h and ".s-head\n" not in h, "BUG: CSS 仍有 .s-head 选择器"
    assert "classList.toggle('open'" not in h, "BUG: 仍用 classList.toggle('open') JS 委托"
    # 关键:不再有绑错容器的 querySelector('.wrap') 委托
    assert "querySelector('.wrap')" not in h, "BUG: 仍用 querySelector('.wrap') 委托(会命中 hero wrap 导致主内容区点击失效)"

    # 3. 复制按钮不应在 <summary> 内(避免点击触发 details toggle 冲突)
    #    模板里 summary 闭合后才出现 copy-btn
    for sm in _all_summaries(h):
        assert "copy-btn" not in sm, "BUG: copy-btn 不应在 <summary> 内(会与 details toggle 冲突)"


def _all_summaries(h: str) -> list:
    """从模板字符串里抽出所有 <summary>...</summary> 片段(用于断言 copy-btn 不在其中)"""
    import re
    return re.findall(r"<summary>(.*?)</summary>", h, re.DOTALL)



def test_help_html_renders():
    """用 Python 模拟 IIFE 关键路径,确认渲染产出"""
    import yaml, json
    from pathlib import Path
    SKILL = Path(__file__).parent.parent
    data = yaml.safe_load((SKILL / "references" / "scenarios.yaml").read_text(encoding="utf-8"))
    scenarios = data["scenarios"]

    # P1-11b:按 category 分组(A 套 11 类)
    CATEGORY_ORDER = ["找东西", "存东西", "改东西", "盘点",
                      "出门", "回家", "看统计", "账号", "检查", "标签", "帮助"]
    by_cat = {}
    for s in scenarios:
        by_cat.setdefault(s.get("category", "其他"), []).append(s)
    groups = [(cat, by_cat[cat]) for cat in CATEGORY_ORDER if cat in by_cat]
    # 应有 11 类(可能略少,看 yaml 是否覆盖)
    assert len(groups) >= 8, f"应 ≥ 8 个类别,实际 {len(groups)}"

    # 每条 scenario 必须有 8 字段契约(总纲 07 §2.2)
    required_fields = {"wake_word", "scenario_id", "scenario_title",
                        "category", "dimensions", "prompt", "status", "result"}
    for s in scenarios:
        missing = required_fields - set(s.keys())
        assert not missing, f"场景 {s.get('scenario_id', '?')} 缺字段: {missing}"

    # category 必须在白名单内
    valid_cats = set(CATEGORY_ORDER)
    for s in scenarios:
        assert s.get("category") in valid_cats, \
            f"{s['scenario_id']} category={s.get('category')!r} 不在白名单"

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