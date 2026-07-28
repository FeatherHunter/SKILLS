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
