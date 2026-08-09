"""
私家大厨 · T5 录入域实施测试(v4.0 缺字段拒绝制 · 三态采集表单)

覆盖:
  1. 导入回归(门禁 A · F1 a-d):
     - 官方 recipe_template.json(已修复 F9)原样导入成功(F1 a 清零)
     - null / 空串 / 缺 key → 拒绝 + 缺失清单一次列全(F1 a/b/d)
     - tips step_sequence 关联(F1 c): 合法关联写库、失效关联进清单
  2. 三态采集表单模板 + 渲染器(08 对齐 · 占位符唯一 · _N 防覆盖)
  3. 场景资产: add-4 待开发 → 可用
"""
import os
import sys
import json
import tempfile
import copy
from pathlib import Path
from datetime import datetime

SKILL_DIR = Path(__file__).resolve().parent.parent

# ── 模块级环境(先于 db_config/init_db import):临时库 + 临时输出目录 ──
_TMP = Path(tempfile.mkdtemp(prefix="chef_t5_test_"))
os.environ["SKILLS_DB_PATH"] = str(_TMP)
os.environ["CHEF_OUTPUT_DIR"] = str(_TMP / "out")
sys.path.insert(0, str(SKILL_DIR / "scripts"))
sys.path.insert(0, str(SKILL_DIR / "references"))

import pytest

import init_db
init_db.init_db()

import validators
import import_orchestrator
import render_add

TEMPLATE_PATH = SKILL_DIR / "templates" / "recipe_template.json"


def _load_template() -> dict:
    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _scan_null_empty(node, path="", out=None):
    """递归扫描 null / 空串(供模板守卫测试)"""
    if out is None:
        out = []
    if isinstance(node, dict):
        for k, v in node.items():
            _scan_null_empty(v, f"{path}.{k}" if path else k, out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _scan_null_empty(v, f"{path}[{i}]", out)
    elif node is None or (isinstance(node, str) and not node.strip()):
        out.append(path)
    return out


# ══════════════════════════════════════════════════════════════
# 1. 导入回归 · 门禁 A
# ══════════════════════════════════════════════════════════════

class TestOfficialTemplateImport:
    """官方模板原样导入成功(F1 a 清零 · 不再 NOT NULL 连环炸)"""

    def test_validation_passes(self):
        """模板通过校验链(修复后无 null/空串)"""
        result = validators.validate_recipe_for_import(_load_template())
        assert result["valid"], f"模板校验失败: {[e.get('field') for e in result['errors']]}"

    def test_import_succeeds(self):
        """orchestrate_import 全量写库成功(主表 + 子表),无 DB 约束连环炸"""
        data = _load_template()
        result = import_orchestrator.orchestrate_import(data)
        assert result["status"] == "success", f"导入失败: {result.get('message')}"
        assert result["data"]["recipe_id"]

    def test_dry_run_ok(self):
        """dry-run 短路不写库"""
        result = import_orchestrator.orchestrate_import(_load_template(), dry_run=True)
        assert result["status"] == "dry_run"

    def test_template_has_no_null_or_empty(self):
        """模板资产守卫:修复后不允许 null / 空串残留(F9)"""
        bad = _scan_null_empty(_load_template())
        assert bad == [], f"模板仍含 null/空串: {bad}"


class TestMissingManifest:
    """缺字段导入 → 拒绝 + 缺失清单一次列全(F1 a/b/d)"""

    def test_null_fields_rejected_with_manifest(self):
        """null 值 → 拒绝,清单一次列全(官方模板 6 处 null 场景)"""
        data = _load_template()
        data["photo_url"] = None
        data["source"] = None
        data["source_url"] = None
        data["ingredients"][0]["quantity_text"] = None
        data["ingredients"][0]["substitute"] = None
        data["ingredients"][1]["quantity_text"] = None
        result = validators.validate_recipe_for_import(data)
        assert not result["valid"]
        manifest = [e for e in result["errors"] if e.get("type") == "missing_field"]
        paths = {e.get("path") for e in manifest}
        assert {"photo_url", "source", "source_url",
                "ingredients[0].quantity_text", "ingredients[0].substitute",
                "ingredients[1].quantity_text"} <= paths, f"清单未一次列全: {paths}"

    def test_empty_string_rejected(self):
        """空串 → 拒绝 + 缺失清单(F1 d 空串外键陷阱)"""
        data = _load_template()
        data["tips"][0]["content"] = ""
        data["ingredients"][0]["category"] = "   "
        result = validators.validate_recipe_for_import(data)
        assert not result["valid"]
        paths = {e.get("path") for e in result["errors"] if e.get("type") == "missing_field"}
        assert "tips[0].content" in paths
        assert "ingredients[0].category" in paths

    def test_missing_keys_rejected(self):
        """字段缺失(key 不存在)→ 拒绝 + 清单"""
        data = _load_template()
        del data["steps"]
        del data["techniques"]
        result = validators.validate_recipe_for_import(data)
        assert not result["valid"]
        paths = {e.get("path") for e in result["errors"] if e.get("type") == "missing_field"}
        assert "steps" in paths and "techniques" in paths

    def test_placeholder_word_rejected(self):
        """占位符词(黑名单)仍拒绝,与缺失清单并存"""
        data = _load_template()
        data["source"] = "未知"
        result = validators.validate_recipe_for_import(data)
        assert not result["valid"]
        assert any(e.get("type") == "placeholder" and e.get("field") == "source"
                   for e in result["errors"])

    def test_unit_fallback_from_ingredients(self):
        """step.ingredients_used[].unit 缺时由 ingredients[].unit 兜底(不报缺失)"""
        data = _load_template()
        for i, s in enumerate(data["steps"]):
            for si in s.get("ingredients_used", []):
                si.pop("unit", None)
        result = validators.validate_recipe_for_import(data)
        assert result["valid"], f"unit 兜底失败: {[e.get('field') for e in result['errors']]}"

    def test_unit_missing_without_fallback(self):
        """unit 无兜底 → 拒绝 + 清单"""
        data = _load_template()
        data["ingredients"][0]["unit"] = None
        for s in data["steps"]:
            for si in s.get("ingredients_used", []):
                if si.get("name") == "虾":
                    si.pop("unit", None)
        result = validators.validate_recipe_for_import(data)
        assert not result["valid"]
        assert any(e.get("path") == "ingredients[0].unit" for e in result["errors"])


class TestTipsStepLinkage:
    """F1 c · step 级 tip 的 JSON 导入路径打通(step_sequence → step_id)"""

    def test_step_tip_linked_to_step(self):
        """step_sequence=1 的 tip 写库后 step_id 指向 sequence=1 的步骤"""
        data = _load_template()
        result = import_orchestrator.orchestrate_import(data)
        assert result["status"] == "success"
        recipe_id = result["data"]["recipe_id"]

        from db import get_connection
        conn = get_connection()
        try:
            step = conn.execute(
                "SELECT id FROM cooking_steps WHERE recipe_id=? AND sequence=1", (recipe_id,)
            ).fetchone()
            tip = conn.execute(
                "SELECT step_id, ingredient_id FROM tips WHERE recipe_id=?", (recipe_id,)
            ).fetchone()
        finally:
            conn.close()
        assert step and tip
        assert tip["step_id"] == step["id"], "tip.step_id 未解析到 sequence=1 的步骤(F1 c)"

    def test_bad_step_sequence_in_manifest(self):
        """step_sequence 指向不存在的步骤 → 拒绝 + 清单(F1 c)"""
        data = _load_template()
        data["tips"][0]["step_sequence"] = 99
        result = validators.validate_recipe_for_import(data)
        assert not result["valid"]
        assert any("tips[0].step_sequence" == e.get("path") for e in result["errors"])

    def test_recipe_level_tip_ok(self):
        """无 step_sequence 的 tip = 菜级 tip,合法导入(step_id 允许空)"""
        data = _load_template()
        data["tips"] = [{"content": "这道菜整体偏甜,怕腻可以少放糖", "category": "调味", "priority": 1}]
        result = validators.validate_recipe_for_import(data)
        assert result["valid"], f"菜级 tip 被拒: {[e.get('field') for e in result['errors']]}"

    def test_techniques_require_step_sequence(self):
        """技法必须挂步骤(step_techniques.step_id NOT NULL)→ 缺了拒绝"""
        data = _load_template()
        data["techniques"][0].pop("step_sequence")
        result = validators.validate_recipe_for_import(data)
        assert not result["valid"]
        assert any("techniques[0].step_sequence" == e.get("path") for e in result["errors"])


# ══════════════════════════════════════════════════════════════
# 2. 三态采集表单 · 模板 + 渲染器
# ══════════════════════════════════════════════════════════════

class TestCollectTemplates:
    """采集/回执模板 08 对齐:占位符唯一 · 双按钮硬标准"""

    def test_collect_placeholder_unique(self):
        tpl = SKILL_DIR / "templates" / "录入" / "采集.html"
        content = tpl.read_text(encoding="utf-8")
        assert content.count("<!--INJECT-DATA-->") == 1

    def test_receipt_placeholder_unique(self):
        tpl = SKILL_DIR / "templates" / "录入" / "回执.html"
        content = tpl.read_text(encoding="utf-8")
        assert content.count("<!--INJECT-DATA-->") == 1

    def test_collect_has_copy_buttons(self):
        """复制数据 + 复制日志双按钮(08 §4 硬标准)"""
        tpl = (SKILL_DIR / "templates" / "录入" / "采集.html").read_text(encoding="utf-8")
        assert "btn-copy-data" in tpl and "btn-copy-log" in tpl

    def test_receipt_has_copy_buttons(self):
        tpl = (SKILL_DIR / "templates" / "录入" / "回执.html").read_text(encoding="utf-8")
        assert "btn-copy-data" in tpl and "btn-copy-log" in tpl

    def test_collect_three_states_present(self):
        """三态:confirmed / guessed / missing(G2 决策)"""
        tpl = (SKILL_DIR / "templates" / "录入" / "采集.html").read_text(encoding="utf-8")
        assert "confirmed" in tpl and "guessed" in tpl and "missing" in tpl

    def test_collect_confirm_disabled_logic(self):
        """确认写入按钮缺失未补全时置灰禁用"""
        tpl = (SKILL_DIR / "templates" / "录入" / "采集.html").read_text(encoding="utf-8")
        assert "disabled" in tpl


class TestRenderAdd:
    """render_add.py 渲染(占位符注入 · _N 防覆盖)"""

    def _collect_payload(self):
        return {
            "scene_id": "add-4",
            "scene_title": "结构化模板录入(表单)",
            "wake_word": "录入食谱",
            "command_cn": "录入食谱",
            "occurred_at": "2026-08-09 12:00:00",
            "stage": "填写",
            "target": "宫保虾球",
            "fields": [
                {"path": "name", "label": "菜名", "value": "宫保虾球", "state": "confirmed", "note": ""},
                {"path": "difficulty", "label": "难度", "value": "中等", "state": "guessed", "note": "推测"},
                {"path": "photo_url", "label": "照片URL", "value": "", "state": "missing", "note": "必补"}
            ],
            "payload": {"name": "宫保虾球"}
        }

    def test_collect_renders_html(self, monkeypatch):
        """采集渲染:注入成功 + 双通道文件名"""
        class _FixedNow:
            @staticmethod
            def now():
                return datetime(2026, 8, 9, 12, 0, 0)
        monkeypatch.setattr(render_add, "datetime", _FixedNow)
        path = render_add.render(render_add.TEMPLATE_COLLECT, self._collect_payload(),
                                 "录入采集_宫保虾球")
        assert path.exists()
        html = path.read_text(encoding="utf-8")
        assert "window.__DATA__" in html
        assert "宫保虾球" in html

    def test_n_suffix_on_same_second(self, monkeypatch):
        """同秒重复渲染 → _N 防覆盖(08 12.A 精神)"""
        class _FixedNow:
            @staticmethod
            def now():
                return datetime(2026, 8, 9, 12, 0, 0)
        monkeypatch.setattr(render_add, "datetime", _FixedNow)
        payload = self._collect_payload()
        slug = "录入采集_N防覆盖测试"  # 独立 slug,避免与 test_collect_renders_html 同秒产物互撞
        first = render_add.render(render_add.TEMPLATE_COLLECT, payload, slug)
        second = render_add.render(render_add.TEMPLATE_COLLECT, payload, slug)
        assert first != second
        assert second.name.endswith("_2.html"), f"期望 _2 后缀,实际 {second.name}"

    def test_receipt_success_renders(self):
        """成功回执:结果 + diff + 撤销"""
        payload = {
            "mode": "success",
            "scene_id": "add-5",
            "scene_title": "JSON 文件导入",
            "wake_word": "导入食谱",
            "command_cn": "导入食谱",
            "occurred_at": "2026-08-09 12:05:00",
            "target": "宫保虾球",
            "operation": "导入食谱「宫保虾球」",
            "result": "成功导入食谱「宫保虾球」",
            "recipe_id": "8f3b435b-0000",
            "diff": [{"action": "add", "field": "recipes", "summary": "新增主记录"}],
            "undo_prompt": "请撤销刚才的录入「宫保虾球」",
            "payload": {"name": "宫保虾球"}
        }
        path = render_add.render(render_add.TEMPLATE_RECEIPT, payload, "录入回执_成功")
        assert path.exists()
        html = path.read_text(encoding="utf-8")
        assert "window.__DATA__" in html and "撤销" in html

    def test_receipt_failure_renders(self):
        """失败回执(08 §6.1):操作名/失败原因/关键数据/建议下一步 + 修正重试"""
        payload = {
            "mode": "failure",
            "scene_id": "add-6",
            "scene_title": "导入校验失败(补齐后重试)",
            "wake_word": "导入食谱",
            "command_cn": "导入食谱",
            "occurred_at": "2026-08-09 12:06:00",
            "target": "宫保虾球",
            "operation": "导入食谱「宫保虾球」",
            "failure_reason": "缺 3 个必填字段(photo_url/source/quantity_text)",
            "key_data": {"missing": ["photo_url", "source", "quantity_text"]},
            "next_step": "补齐缺失字段后重新导入",
            "retry_prompt": "请修正缺失字段后重新导入:photo_url/source/quantity_text",
            "payload": {}
        }
        path = render_add.render(render_add.TEMPLATE_RECEIPT, payload, "录入回执_失败")
        assert path.exists()
        html = path.read_text(encoding="utf-8")
        assert "window.__DATA__" in html
        assert "失败原因" in html and "修正重试" in html


# ══════════════════════════════════════════════════════════════
# 3. 场景资产 · add-4 可用化
# ══════════════════════════════════════════════════════════════

class TestSceneAsset:
    def test_add4_status_available_in_domain_yaml(self):
        """scenes/录入.yaml: add-4 结构化模板 = 可用(T5 交付)"""
        import yaml
        scenes = yaml.safe_load((SKILL_DIR / "scenes" / "录入.yaml").read_text(encoding="utf-8"))
        add4 = next(s for s in scenes["scenes"] if s["id"] == "add-4")
        assert add4["status"] == "", f"add-4 仍为待开发: {add4['status']}"

    def test_add4_status_available_in_total(self):
        """references/scenarios.yaml(合并器产物): add_from_template = 可用"""
        import yaml
        total = yaml.safe_load((SKILL_DIR / "references" / "scenarios.yaml").read_text(encoding="utf-8"))
        found = False
        for g in total.get("scenarios", []):
            for sc in g.get("scenarios", []):
                if sc.get("scenario_id") == "add_from_template":
                    found = True
                    assert sc.get("status") == "", f"总账 add-4 仍为待开发: {sc.get('status')}"
        assert found, "总账中未找到 add_from_template"

    def test_add_templates_referenced_in_scenes(self):
        """录入域 6 场景统一映射 templates/录入/采集.html(G2 决策)"""
        import yaml
        scenes = yaml.safe_load((SKILL_DIR / "scenes" / "录入.yaml").read_text(encoding="utf-8"))
        for s in scenes["scenes"]:
            assert s["html"]["template"] == "录入/采集.html", f"{s['id']} 模板映射不一致"
