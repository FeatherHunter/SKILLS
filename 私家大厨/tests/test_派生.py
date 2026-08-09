"""
私家大厨 · T12 派生域实施测试(v4.0 · rel-3 从已有派生新菜 / rel-2 家族树 / rel-1 回执)

覆盖:
  1. 母本读取(rel-3): 存在 → 导入契约 dict;不存在 / 已废弃 → 拒绝
  2. 同事务派生写库(rel-3 · 门禁 A e2e):
     「做咖喱鸡,类似咖喱牛腩」→ 新菜谱 + 派生关系一次建成;diff 含「牛腩 → 鸡」
     派生自身非法 / 缺 change_summary / 母本废弃 → 拒绝
  3. 家族树(rel-2): 祖先链(多代)/ 后代链(多代)/ 无关系单根 / 未找到
  4. 模板 + 渲染器: 4 模板占位符唯一 · 渲染冒烟 · _N 防覆盖
  5. 场景资产: 派生.yaml rel-3 可用
"""
import os
import sys
import json
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent

# ── 路径注入 ──
sys.path.insert(0, str(SKILL_DIR / "scripts"))
sys.path.insert(0, str(SKILL_DIR / "references"))

import pytest

import validators
import import_orchestrator
import recipe_manager
import render_派生
from 派生 import ops

TEMPLATE_PATH = SKILL_DIR / "templates" / "recipe_template.json"
TEMPLATE_DIR = SKILL_DIR / "templates" / "派生"

# ── 共享 env 基线修复(对抗式审查发现 · 2026-08-09)─────────────
# 本文件字母序最后,模块级代码在收集阶段最后执行。此时共享 os.environ 已被
# 并行 T8 会话的 test_做菜.py 模块级 setenv 指向「它自己的空临时库」
# (其 init_db 建表落在首个导入者缓存的 DB_PATH,env 与库错位)→ 全量跑时
# test_render_data 等 subprocess 测试继承错误 env 报 no such table: recipes。
# 修复:把 SKILLS_DB_PATH 纠正回「首个导入者缓存的 DB 目录」(有表,test_add 基线)。
# 不动 T8 文件(隔离契约),只在本域做防御;fixture 内不再动 env(进程内走 DB_PATH patch)。
import db_config  # noqa: E402
os.environ["SKILLS_DB_PATH"] = str(Path(db_config.DB_PATH).parent)


@pytest.fixture(scope="session", autouse=True)
def _t12_isolated_db():
    """T12 进程内 DB 隔离:patch db_config.DB_PATH 到本 session 临时库(用毕还原)。

    共享 env 已由模块级基线修复处理(见上);进程内 DB_PATH 是 import 时缓存常量,
    env 对已导入模块无效,因此直接 patch DB_PATH,避免测试数据落进共享测试库。
    """
    import db_config
    tmp = Path(tempfile.mkdtemp(prefix="chef_t12_"))
    os.environ["CHEF_OUTPUT_DIR"] = str(tmp / "out")
    original_db_path = db_config.DB_PATH
    db_config.DB_PATH = tmp / "chef_data.db"
    import init_db
    init_db.init_db()
    yield tmp
    db_config.DB_PATH = original_db_path


def _load_template() -> dict:
    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _insert_recipe(name: str, **overrides) -> str:
    """写一道完整菜谱,返回 recipe_id"""
    data = _load_template()
    data["name"] = name
    data.update(overrides)
    result = import_orchestrator.orchestrate_import(data)
    assert result["status"] == "success", f"造数失败: {result.get('message')}"
    return result["data"]["recipe_id"]


def _archive(name: str) -> None:
    """把菜标记为已废弃"""
    from db import query, execute
    row = query("SELECT id FROM recipes WHERE name = ?", (name,))
    assert row, f"菜不存在: {name}"
    execute("UPDATE recipes SET status = '已废弃' WHERE id = ?", (row[0]["id"],))


def _relations() -> list:
    from db import query
    return query("""
        SELECT p.name AS parent_name, c.name AS child_name, rr.relation_type, rr.change_summary
        FROM recipe_relations rr
        JOIN recipes p ON rr.parent_id = p.id
        JOIN recipes c ON rr.child_id = c.id
    """)


# ══════════════════════════════════════════════════════════════
# 1. 母本读取(rel-3)
# ══════════════════════════════════════════════════════════════

class TestMotherRead:
    def test_mother_returns_import_contract(self):
        """存在 → 导入契约 dict,不含时间戳/history/relations"""
        _insert_recipe("咖喱牛腩")
        mother = ops.get_mother("咖喱牛腩")
        assert mother["name"] == "咖喱牛腩"
        assert "created_at" not in mother and "updated_at" not in mother
        assert mother["history"] == [] and mother["relations"] == []
        assert mother["ingredients"] and mother["steps"] and mother["nutrition"]
        # 能通过校验链 → 可被 orchestrate_import 直接消费
        check = validators.validate_recipe_for_import(dict(mother))
        assert check["valid"], f"母本不满足导入契约: {check.get('errors')}"

    def test_mother_not_found_rejected(self):
        with pytest.raises(ValueError):
            ops.get_mother("不存在的菜")

    def test_mother_archived_rejected(self):
        """母本已废弃 → 拒绝 + 提示(边界 · G9 不造值)"""
        _insert_recipe("旧菜")
        _archive("旧菜")
        with pytest.raises(ValueError, match="已废弃"):
            ops.get_mother("旧菜")


# ══════════════════════════════════════════════════════════════
# 2. 同事务派生写库(rel-3)
# ══════════════════════════════════════════════════════════════

class TestDeriveCommit:
    def test_derive_recipe_and_relation_in_one(self):
        """门禁 A e2e: 「做咖喱鸡,类似咖喱牛腩」→ 新菜谱+派生关系一次建成"""
        _insert_recipe("咖喱牛腩")
        derived = _load_template()
        derived["name"] = "咖喱鸡"
        derived["ingredients"][0]["name"] = "鸡"
        derived["steps"][0]["ingredients_used"][0]["name"] = "鸡"
        derived["description"] = "咖喱鸡,鸡块嫩滑,咖喱浓郁"

        result = ops.derive_commit({
            "recipe": derived,
            "parent_name": "咖喱牛腩",
            "relation_type": "派生",
            "change_summary": "牛腩换鸡,减咖喱量",
        })
        assert result["status"] == "success", result.get("message")
        assert result["recipe_id"]
        assert result["relation"]["parent_name"] == "咖喱牛腩"
        assert result["relation"]["child_name"] == "咖喱鸡"

        # 新菜谱 + 派生关系同事务建成
        rels = _relations()
        assert any(r["parent_name"] == "咖喱牛腩" and r["child_name"] == "咖喱鸡"
                   and r["change_summary"] == "牛腩换鸡,减咖喱量" for r in rels)
        # diff 含关键差异
        diff = result["diff"]
        assert any(d["action"] == "mod" and d["field"] == "name" and "咖喱牛腩" in d["summary"] for d in diff)
        assert any("牛腩" in d["summary"] and "鸡" in d["summary"] for d in diff)
        # 新菜独立可导出
        exported = recipe_manager.export_as_dict("咖喱鸡")
        assert exported and exported["name"] == "咖喱鸡"

    def test_derive_self_rejected(self):
        _insert_recipe("自引用菜")
        data = _load_template()
        data["name"] = "自引用菜"
        result = ops.derive_commit({
            "recipe": data, "parent_name": "自引用菜",
            "relation_type": "派生", "change_summary": "自己变自己",
        })
        assert result["status"] == "error"
        assert "自身" in result["message"]

    def test_derive_missing_change_summary_rejected(self):
        _insert_recipe("母菜A")
        data = _load_template()
        data["name"] = "子菜B"
        result = ops.derive_commit({
            "recipe": data, "parent_name": "母菜A",
            "relation_type": "派生", "change_summary": "",
        })
        assert result["status"] == "error"
        assert "改动说明" in result["message"]

    def test_derive_mother_archived_rejected(self):
        _insert_recipe("废母")
        _archive("废母")
        data = _load_template()
        data["name"] = "废子"
        result = ops.derive_commit({
            "recipe": data, "parent_name": "废母",
            "relation_type": "派生", "change_summary": "试试",
        })
        assert result["status"] == "error"
        assert "已废弃" in result["message"]

    def test_derive_mother_not_found_rejected(self):
        data = _load_template()
        data["name"] = "孤儿菜"
        result = ops.derive_commit({
            "recipe": data, "parent_name": "不存在母本",
            "relation_type": "派生", "change_summary": "试试",
        })
        assert result["status"] == "error"
        assert "未找到母本" in result["message"]


# ══════════════════════════════════════════════════════════════
# 3. 家族树(rel-2)
# ══════════════════════════════════════════════════════════════

class TestRelationTree:
    def _chain(self):
        """A → B → C(A 派生 B,B 派生 C)+ D 从 A 派生(多后代)
        菜名带 T12 前缀(全量跑共享 test_add 临时库,避免与官方模板「宫保虾球」/其他用例撞名
        导致 _resolve_recipe_id 模糊匹配到无关系旧行);只预插母本,子菜全部 derive_commit 创建"""
        _insert_recipe("T12宫保鸡丁")
        for child, summary in (("T12宫保虾球", "鸡丁换虾球"), ("T12宫保杏鲍菇", "鸡丁换杏鲍菇")):
            r = ops.derive_commit({
                "recipe": _dish(child), "parent_name": "T12宫保鸡丁",
                "relation_type": "派生", "change_summary": summary,
            })
            assert r["status"] == "success", r.get("message")
        r = ops.derive_commit({
            "recipe": _dish("T12宫保牛蛙"), "parent_name": "T12宫保虾球",
            "relation_type": "改良", "change_summary": "虾球换牛蛙,减辣",
        })
        assert r["status"] == "success", r.get("message")

    def test_tree_ancestors_and_descendants_multi_generation(self):
        """牛蛙: 祖先链 虾球(1)→鸡丁(2);后代链 无"""
        self._chain()
        tree = ops.relation_tree("T12宫保牛蛙")
        assert tree["found"] and tree["root"]["name"] == "T12宫保牛蛙"
        assert {a["name"] for a in tree["ancestors"]} == {"T12宫保虾球", "T12宫保鸡丁"}
        levels = {a["name"]: a["level"] for a in tree["ancestors"]}
        assert levels["T12宫保虾球"] == 1 and levels["T12宫保鸡丁"] == 2
        assert tree["descendants"] == []

    def test_tree_root_with_descendants(self):
        """鸡丁: 后代 虾球/杏鲍菇(level 1);牛蛙 经由虾球(level 2)"""
        self._chain()
        tree = ops.relation_tree("T12宫保鸡丁")
        assert tree["found"]
        desc = {d["name"]: d["level"] for d in tree["descendants"]}
        assert desc["T12宫保虾球"] == 1 and desc["T12宫保杏鲍菇"] == 1
        assert desc["T12宫保牛蛙"] == 2
        assert tree["ancestors"] == []

    def test_tree_single_root_no_relations(self):
        _insert_recipe("原创菜")
        tree = ops.relation_tree("原创菜")
        assert tree["found"] and tree["root"]["name"] == "原创菜"
        assert tree["count"] == 0 and tree["ancestors"] == [] and tree["descendants"] == []

    def test_tree_not_found(self):
        tree = ops.relation_tree("不存在")
        assert not tree["found"] and tree["root"] is None


def _dish(name: str) -> dict:
    """造派生子菜(最小可导入 dict)"""
    d = _load_template()
    d["name"] = name
    return d


# ══════════════════════════════════════════════════════════════
# 4. 模板 + 渲染器(08 对齐 · 占位符唯一 · _N 防覆盖)
# ══════════════════════════════════════════════════════════════

class TestRenderDerive:
    @pytest.mark.parametrize("template", sorted(p.name for p in TEMPLATE_DIR.glob("*.html")))
    def test_placeholder_unique(self, template):
        html = (TEMPLATE_DIR / template).read_text(encoding="utf-8")
        assert html.count("<!--INJECT-DATA-->") == 1, f"{template} 占位符不唯一"
        assert "window.__DATA__" in html

    def test_render_smoke_and_n_suffix(self):
        """4 个渲染路径冒烟 + 同秒重复渲染 _N 防覆盖"""
        tmp = Path(tempfile.mkdtemp(prefix="chef_t12_render_"))
        out1 = tmp / "a.html"
        out2 = tmp / "b.html"

        # rel-3 derive-edit
        edit_payload = {
            "scene_id": "derive_from_existing", "scene_title": "从已有派生新菜",
            "wake_word": "从已有派生新菜", "command_cn": "从已有派生新菜",
            "occurred_at": "2026-08-09 12:00:00", "target": "咖喱鸡",
            "mother": {"name": "咖喱牛腩", "difficulty": "中等", "servings": 2, "total_time": 40},
            "change_summary": "牛腩换鸡,减咖喱量", "relation_type": "派生",
            "fields": [
                {"path": "name", "label": "菜名", "value": "咖喱鸡", "state": "guessed"},
                {"path": "description", "label": "描述", "value": "咖喱鸡", "state": "guessed"},
                {"path": "ingredients[0].name", "label": "食材1", "value": "鸡", "state": "guessed"},
            ],
            "payload": {"recipe": {"name": "咖喱鸡"}, "parent_name": "咖喱牛腩",
                        "relation_type": "派生", "change_summary": "牛腩换鸡"},
            "logs": {},
        }
        p = tmp / "edit.json"
        p.write_text(json.dumps(edit_payload, ensure_ascii=False), encoding="utf-8")
        assert render_派生.cmd_derive_edit(str(p), str(out1))
        assert out1.exists() and "咖喱鸡" in out1.read_text(encoding="utf-8")
        assert render_派生.cmd_derive_edit(str(p), str(out2))
        assert out2.exists()

        # rel-1 confirm
        cf = tmp / "confirm.json"
        cf.write_text(json.dumps({
            "scene_id": "add_relation", "scene_title": "添加派生关系",
            "wake_word": "添加派生关系", "command_cn": "添加派生关系",
            "occurred_at": "2026-08-09 12:00:00",
            "parent_name": "咖喱牛腩", "child_name": "咖喱鸡",
            "relation_type": "派生", "change_summary": "牛腩换鸡",
        }, ensure_ascii=False), encoding="utf-8")
        assert render_派生.cmd_confirm(str(cf), str(tmp / "c.html"))

        # rel-3 receipt success
        rc = tmp / "receipt_success.json"
        rc.write_text(json.dumps({
            "mode": "success", "scene_id": "derive_from_existing",
            "scene_title": "从已有派生新菜", "wake_word": "从已有派生新菜",
            "command_cn": "从已有派生新菜", "occurred_at": "2026-08-09 12:00:01",
            "operation": "从咖喱牛腩派生咖喱鸡", "target": "咖喱鸡",
            "result": "新菜谱「咖喱鸡」创建成功",
            "recipe_id": "abc-123",
            "relation": {"parent_name": "咖喱牛腩", "child_name": "咖喱鸡",
                         "relation_type": "派生", "change_summary": "牛腩换鸡"},
            "diff": [{"action": "mod", "field": "name", "summary": "咖喱牛腩 → 咖喱鸡"}],
            "undo_prompt": "请撤销刚才从咖喱牛腩派生咖喱鸡的创建",
        }, ensure_ascii=False), encoding="utf-8")
        assert render_派生.cmd_receipt(str(rc), str(tmp / "d.html"))

        # rel-3 receipt failure
        rf = tmp / "receipt_fail.json"
        rf.write_text(json.dumps({
            "mode": "failure", "scene_id": "derive_from_existing",
            "scene_title": "从已有派生新菜", "wake_word": "从已有派生新菜",
            "command_cn": "从已有派生新菜", "occurred_at": "2026-08-09 12:00:02",
            "operation": "从咖喱牛腩派生咖喱鸡", "target": "咖喱鸡",
            "failure_reason": "母本「咖喱牛腩」已废弃,不能派生",
            "key_data": {"parent_name": "咖喱牛腩", "child_name": "咖喱鸡"},
            "next_step": "换一个未废弃的母本,或先恢复母本",
            "retry_prompt": "请换个母本重新派生",
        }, ensure_ascii=False), encoding="utf-8")
        assert render_派生.cmd_receipt(str(rf), str(tmp / "e.html"))

        # rel-2 tree(真数据走库)
        _insert_recipe("树根菜")
        assert render_派生.cmd_tree("树根菜", str(tmp / "f.html"))
        html = (tmp / "f.html").read_text(encoding="utf-8")
        assert "家族树" in html and "树根菜" in html

        # 默认输出路径 + _N 防覆盖(同秒两次渲染 → 2 个文件)
        import render_派生 as r2
        first = r2._pick_output("派生", "防覆盖测试")
        first.parent.mkdir(parents=True, exist_ok=True)
        first.write_text("x", encoding="utf-8")
        second = r2._pick_output("派生", "防覆盖测试")
        assert second != first and second.name.endswith("_2.html")


# ══════════════════════════════════════════════════════════════
# 5. 场景资产
# ══════════════════════════════════════════════════════════════

class TestSceneAssets:
    def test_rel3_available(self):
        """rel-3 待开发 → 可用(合并器同源)"""
        import yaml
        scenes = yaml.safe_load((SKILL_DIR / "scenes" / "派生.yaml").read_text(encoding="utf-8"))
        rel3 = next(s for s in scenes["scenes"] if s["id"] == "rel-3")
        assert rel3["status"] == "", f"rel-3 status 应为可用: {rel3['status']!r}"

    def test_total_scene_count_unchanged(self):
        """3 场景卡不变(场景清单定稿后不增删)"""
        import yaml
        scenes = yaml.safe_load((SKILL_DIR / "scenes" / "派生.yaml").read_text(encoding="utf-8"))
        assert [s["id"] for s in scenes["scenes"]] == ["rel-1", "rel-2", "rel-3"]
