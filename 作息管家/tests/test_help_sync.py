"""ADR-0001 · 作息管家.html 稳定入口同步测试

锁住:
- help_render.py render() 主流程完成后,自动同步到根目录作息管家.html
- data.mirror_path 字段返回根目录作息管家.html 的绝对路径
- 镜像内容与主输出 100% 一致(byte-identical)
- scenarios.yaml 改动 → 跑 render() → 作息管家.html 自动更新(配合 §05 钩子 #1)

 Tested-By seam:
- 调用 help_render.render(out_path) 观察返回 JSON 字段
- 读取 file_path 和 mirror_path 比对内容
"""
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def test_render_syncs_to_root_mirror(tmp_path, monkeypatch):
    """跑 render() 后,根目录作息管家.html 与主输出内容一致 + 返回 mirror_path"""
    import help_render

    # 隔离 SKILL_DIR:把 SKILL_DIR monkeypatch 到 tmp_path 下,避免污染真根目录
    monkeypatch.setattr(help_render, "SKILL_DIR", tmp_path)
    monkeypatch.setattr(help_render, "TEMPLATE_PATH", SKILL_DIR / "templates" / "help_center.html")
    monkeypatch.setattr(help_render, "SCENARIOS_PATH", SKILL_DIR / "references" / "scenarios.yaml")

    out_path = tmp_path / "schedule_html" / "help" / "作息管家_HELP_20260728_120000.html"
    result = help_render.render(out_path)

    assert result["status"] == "ok", f"render 失败: {result}"
    data = result["data"]
    # 关键契约:mirror_path 必须返回
    assert "mirror_path" in data, "data.mirror_path 字段缺失(ADR-0001 契约)"
    mirror_path = Path(data["mirror_path"])
    # 镜像在根目录(tmp_path 隔离版),文件名是作息管家.html
    assert mirror_path.name == "作息管家.html"
    assert mirror_path.parent == tmp_path, f"镜像应在 SKILL_DIR 根,实际 {mirror_path.parent}"
    # 镜像内容与主输出 byte-identical
    assert mirror_path.exists(), f"镜像文件不存在: {mirror_path}"
    main_bytes = Path(data["file_path"]).read_bytes()
    mirror_bytes = mirror_path.read_bytes()
    assert main_bytes == mirror_bytes, (
        f"镜像内容与主输出不一致(ADR-0001 §1):"
        f"main={len(main_bytes)}B mirror={len(mirror_bytes)}B"
    )


def test_render_rerun_overwrites_mirror(tmp_path, monkeypatch):
    """第二次跑 render() 覆盖根目录镜像(总纲 §04 原则 12 例外,作息管家.html 唯一)"""
    import help_render

    monkeypatch.setattr(help_render, "SKILL_DIR", tmp_path)
    monkeypatch.setattr(help_render, "TEMPLATE_PATH", SKILL_DIR / "templates" / "help_center.html")
    monkeypatch.setattr(help_render, "SCENARIOS_PATH", SKILL_DIR / "references" / "scenarios.yaml")

    out1 = tmp_path / "schedule_html" / "help" / "作息管家_HELP_20260728_120000.html"
    r1 = help_render.render(out1)
    assert r1["status"] == "ok"
    first_mtime = Path(r1["data"]["mirror_path"]).stat().st_mtime

    # 略等避免同秒;再跑一次新路径
    import time
    time.sleep(0.05)
    out2 = tmp_path / "schedule_html" / "help" / "作息管家_HELP_20260728_120001.html"
    r2 = help_render.render(out2)
    assert r2["status"] == "ok"
    second_path = Path(r2["data"]["mirror_path"])
    # 镜像路径稳定不变(ADR-0001 §1:根目录作息管家.html 永远最新)
    assert second_path == Path(r1["data"]["mirror_path"])
    # 内容覆盖(应等于第二次主输出)
    assert second_path.read_bytes() == Path(r2["data"]["file_path"]).read_bytes()
    # mtime 应更新(覆盖写)
    assert second_path.stat().st_mtime >= first_mtime


def test_render_message_includes_mirror(tmp_path, monkeypatch):
    """render() 返回的 message 提及镜像同步(便于 agent 看到双路径)"""
    import help_render

    monkeypatch.setattr(help_render, "SKILL_DIR", tmp_path)
    monkeypatch.setattr(help_render, "TEMPLATE_PATH", SKILL_DIR / "templates" / "help_center.html")
    monkeypatch.setattr(help_render, "SCENARIOS_PATH", SKILL_DIR / "references" / "scenarios.yaml")

    out_path = tmp_path / "schedule_html" / "help" / "作息管家_HELP_20260728_120002.html"
    result = help_render.render(out_path)
    assert result["status"] == "ok"
    # message 提到"已同步"或"镜像"
    assert "已同步" in result["message"] or "镜像" in result["message"], (
        f"message 应提及镜像同步,实际: {result['message']}"
    )


def test_escape_for_js_preserves_json_quotes():
    """T8 修复 · escape_for_js 不得二次转义 json.dumps 的 backslash

    历史 bug 链(2026-08-09 T8 实测):旧实现对 json.dumps 输出再执行 `\` → `\\`,
    把内容里的 `\"`(JSON 对双引号的编码)破坏成 `\\"`,浏览器端 JS 解析 `\\` 为
    单个反斜杠后 `"` 提前闭合字符串 → "Invalid or unexpected token"
    (plan_result_history_none 的 `"0%"` 首次触发,HELP 页 cat-block 全灭)。
    修复:escape_for_js 只做 < / > / 转义,不再动 backslash。
    断言:escape_for_js(json.dumps(x)) 仍是合法 JSON,且 round-trip 无损。
    """
    import json
    import help_render

    payload = {
        "text": '贴合率显示"0%",逐段"无参考"提示',
        "multiline": "第一行\n第二行",
        "backslash": "C:\\temp\\x",
        "script": "</script><b>",
    }
    encoded = help_render.escape_for_js(json.dumps(payload, ensure_ascii=False))
    # 仍是合法 JSON
    decoded = json.loads(encoded)
    assert decoded["text"] == payload["text"]
    assert decoded["multiline"] == payload["multiline"]
    assert decoded["backslash"] == payload["backslash"]
    # 防 </script> 提前闭合仍生效
    assert "<" not in encoded.replace("\\u003c", "")
    assert "\\u003c" in encoded


def test_no_wake_word_lands_uncategorized(monkeypatch):
    """T8 对抗式补漏 · CATEGORY_MAP 必须覆盖全部唤醒词(防御性兜底不得出现)

    L 级重构新增 周视图/首次使用 后曾落「未分类(防御性兜底)」:
    help 页 5 模块分类缺登记 → 场景不可达分类浏览。修复后锁定:
    所有 85 场景的唤醒词均归入 write/query/plan/analyze/admin 之一。

    注:test_help_mobile_responsive 的 mock 渲染会把 help_render reload 到
    临时副本且不还原(既有测试污染),此处显式钉死真实场景资产路径,自足不依赖
    模块全局态。
    """
    import help_render

    real_path = Path(__file__).resolve().parent.parent / "references" / "scenarios.yaml"
    monkeypatch.setattr(help_render, "SCENARIOS_PATH", real_path)
    scenarios, err = help_render.load_scenarios()
    assert err is None
    cats = help_render.group_by_category(scenarios)
    uncat = [c for c in cats if c.get("key") == "_uncategorized"]
    assert not uncat, f"存在未分类兜底: {uncat[0].get('wake_words', [])}"
    total = sum(len(c.get("wake_words", [])) for c in cats)
    wake_set = {s["wake_word"] for s in scenarios}
    assert total == len(wake_set), f"分类覆盖 {total} != 唤醒词 {len(wake_set)}"
    # 新场景必在分类内
    keys = {w.get("wake_word") for c in cats for w in c.get("wake_words", [])}
    for ww in ("周视图", "首次使用", "复盘今日", "复盘本周", "复盘本月", "复盘区间"):
        assert ww in keys, f"唤醒词未分类: {ww}"
