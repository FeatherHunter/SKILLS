"""
测试 9 · 08-HTML 交互规范对齐层(T3 · 2026-08-09)

覆盖:
- build_copy_data 5 段契约 / build_copy_log 6 段契约
- unique_output_path `_N` 后缀防覆盖(12.X · 同秒连跑互不覆盖)
- inject_08_layer 占位符唯一性校验 + 双按钮 + 5 状态
- 7 模板均含 INJECT-08 占位符(双按钮注入点)
"""
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
sys.path.insert(0, str(SCRIPT_DIR))

import align_08  # noqa: E402


class TestCopyData5Segments:
    """复制数据(硬标准): 结构化 JSON 固定 5 段"""

    def test_keys_exact_5(self):
        d = align_08.build_copy_data("view-1", "查看食谱", "宫保虾球", {"id": "x"})
        assert list(d.keys()) == ["scene_id", "command_cn", "occurred_at", "target", "payload"]

    def test_payload_passthrough(self):
        d = align_08.build_copy_data("view-1", "查看食谱", "宫保虾球", {"id": "x"})
        assert d["scene_id"] == "view-1"
        assert d["command_cn"] == "查看食谱"
        assert d["target"] == "宫保虾球"
        assert d["payload"] == {"id": "x"}
        assert "occurred_at" in d and d["occurred_at"]

    def test_occurred_at_format(self):
        d = align_08.build_copy_data("s", "c", "t", {})
        import re
        assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", d["occurred_at"])


class TestCopyLog6Segments:
    """复制日志(硬标准): 6 段(场景标识/思考链/数据结构/调用链/时间戳+版本/异常)"""

    def test_keys_exact_6(self):
        log = align_08.build_copy_log("view-1", "查看食谱", "查看食谱")
        assert list(log.keys()) == ["scene", "thinking", "data_structure", "call_chain", "timestamp", "exception"]

    def test_timestamp_has_version(self):
        log = align_08.build_copy_log("view-1", "查看食谱", "查看食谱")
        assert align_08.SKILL_VERSION in log["timestamp"]

    def test_exception_default_empty(self):
        log = align_08.build_copy_log("s", "c", "w")
        assert log["exception"] == ""

    def test_exception_custom(self):
        log = align_08.build_copy_log("s", "c", "w", exception="recipe_not_found")
        assert log["exception"] == "recipe_not_found"


class TestUniqueOutputPath:
    """12.X `_N` 后缀防覆盖: N=1 起步,绝不覆盖"""

    def test_first_no_suffix(self, tmp_path):
        p = align_08.unique_output_path(tmp_path, "采购清单_辣椒炒肉_20260809_120000")
        assert p.name == "采购清单_辣椒炒肉_20260809_120000.html"

    def test_second_gets_1(self, tmp_path):
        p1 = align_08.unique_output_path(tmp_path, "数据视图_search_x_20260809_120000")
        p1.write_text("a", encoding="utf-8")
        p2 = align_08.unique_output_path(tmp_path, "数据视图_search_x_20260809_120000")
        assert p2.name == "数据视图_search_x_20260809_120000_1.html"

    def test_three_same_second_increment(self, tmp_path):
        """同秒连跑 3 次 → 3 个不同文件(_N 递增)"""
        stem = "做菜模式_辣椒炒肉_20260809_120000"
        p1 = align_08.unique_output_path(tmp_path, stem)
        p1.write_text("1", encoding="utf-8")
        p2 = align_08.unique_output_path(tmp_path, stem)
        p2.write_text("2", encoding="utf-8")
        p3 = align_08.unique_output_path(tmp_path, stem)
        p3.write_text("3", encoding="utf-8")
        assert p1.name.endswith(".html")
        assert p2.name.endswith("_1.html")
        assert p3.name.endswith("_2.html")
        names = {p1.name, p2.name, p3.name}
        assert len(names) == 3  # 3 个不同文件
        assert all(p.exists() for p in (p1, p2, p3))

    def test_never_overwrites_existing(self, tmp_path):
        """绝不覆盖:已存在同名时永远新后缀"""
        stem = "测试_20260809_120000"
        seen = []
        for _ in range(5):
            p = align_08.unique_output_path(tmp_path, stem)
            p.write_text("x", encoding="utf-8")
            seen.append(p.name)
        assert len(set(seen)) == 5
        assert seen == [
            "测试_20260809_120000.html",
            "测试_20260809_120000_1.html",
            "测试_20260809_120000_2.html",
            "测试_20260809_120000_3.html",
            "测试_20260809_120000_4.html",
        ]

    def test_custom_ext(self, tmp_path):
        p = align_08.unique_output_path(tmp_path, "x", ext=".json")
        assert p.name == "x.json"


class TestInject08Layer:
    """共享动作层注入: 占位符唯一 + 双按钮 + 5 状态"""

    def test_placeholder_required(self):
        import pytest
        with pytest.raises(ValueError):
            align_08.inject_08_layer("<html></html>", {}, {})

    def test_double_placeholder_rejected(self):
        import pytest
        html = "<!--INJECT-08-->\n<!--INJECT-08-->"
        with pytest.raises(ValueError):
            align_08.inject_08_layer(html, {}, {})

    def test_inject_adds_bar_and_states(self):
        cd = align_08.build_copy_data("view-1", "查看食谱", "宫保虾球", {})
        cl = align_08.build_copy_log("view-1", "查看食谱", "查看食谱")
        out = align_08.inject_08_layer("<div><!--INJECT-08--></div>", cd, cl)
        assert "复制数据" in out and "复制日志" in out       # 双按钮
        assert "loading" in out and "confirm" in out         # 5 状态含 loading/confirm
        assert "empty" in out and "error" in out             # 5 状态含 empty/error
        assert "__A08__" in out                              # 数据注入
        assert "window.A08" in out                           # 共享 JS

    def test_injected_payload_has_5_and_6_segments(self):
        cd = align_08.build_copy_data("view-1", "查看食谱", "宫保虾球", {})
        cl = align_08.build_copy_log("view-1", "查看食谱", "查看食谱")
        out = align_08.inject_08_layer("<div><!--INJECT-08--></div>", cd, cl)
        # 提取 window.__A08__ JSON 验证段数
        import re
        m = re.search(r"window\.__A08__ = (\{.*?\});", out, re.S)
        assert m
        payload = json.loads(m.group(1))
        assert list(payload["copy_data"].keys()) == ["scene_id", "command_cn", "occurred_at", "target", "payload"]
        assert list(payload["copy_log"].keys()) == ["scene", "thinking", "data_structure", "call_chain", "timestamp", "exception"]


class TestAllTemplatesHave08Placeholder:
    """7 模板双按钮硬标准: 全部含 INJECT-08 占位符(08 §4 无一例外)"""

    TEMPLATES = [
        "recipe_view.html", "cooking_mode.html", "shopping_view.html",
        "data_view.html", "help.html", "batch_edit.html", "data_quality_report.html",
    ]

    def test_each_template_has_placeholder(self):
        for name in self.TEMPLATES:
            content = (TEMPLATES_DIR / name).read_text(encoding="utf-8")
            assert content.count("<!--INJECT-08-->") == 1, f"{name} 必须含恰好 1 个 INJECT-08 占位符"

    def test_each_template_has_inject_data(self):
        for name in self.TEMPLATES:
            content = (TEMPLATES_DIR / name).read_text(encoding="utf-8")
            if name == "cooking_mode.html":
                # cooking_mode 走 <body> 注入(无 INJECT-DATA 占位符,渲染器替换 <body>)
                assert "<body>" in content
                continue
            assert content.count("<!--INJECT-DATA-->") == 1, f"{name} INJECT-DATA 必须唯一"
