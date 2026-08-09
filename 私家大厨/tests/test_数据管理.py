"""
测试 10 · 数据管理域(T13 · G10 定案)

覆盖:
- export_backup.py:ZIP 含 17 表 JSON + 三照片目录(存在才打包)· 纯文件操作不碰 schema
- backup_receipt.html:回执含 08 双按钮占位符 + INJECT-DATA 唯一
- batch_edit.html:改前/改后对比确认(预览差异按钮/可编辑输入/对比面板)
- SKILL.md:体检/批量改/备份 3 唤醒词登记(路由表 + 唤醒词清单)
"""
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATES_DIR = SKILL_DIR / "templates"
CLI_INIT = SCRIPT_DIR / "开始使用" / "cli.py"
IMPORT = SCRIPT_DIR / "recipe_import.py"
FIXTURE = TEMPLATES_DIR / "recipe_template.json"  # 宫保虾球
sys.path.insert(0, str(SCRIPT_DIR))


def make_env(tmp_path: Path) -> dict:
    """隔离环境: 临时 DB 目录 + 临时输出目录(覆盖外部 env · 防 test_add/派生 模块级 env 泄漏)"""
    env = dict(os.environ)
    env["SKILLS_DB_PATH"] = str(tmp_path / "db")
    env["CHEF_OUTPUT_DIR"] = str(tmp_path / "chef_out")
    return env


def seeded_env(tmp_path: Path) -> dict:
    """建库 + 导入宫保虾球 + 返回 env(供 CLI 子进程使用)"""
    env = make_env(tmp_path)
    r = subprocess.run(
        [sys.executable, str(CLI_INIT), "init"],
        capture_output=True, text=True, encoding="utf-8", env=env,
    )
    assert r.returncode == 0, r.stderr
    r = subprocess.run(
        [sys.executable, str(IMPORT), "import", str(FIXTURE), "--merge"],
        capture_output=True, text=True, encoding="utf-8", env=env,
    )
    assert r.returncode == 0, r.stderr
    return env


class TestBackupZip:
    """导出备份(data-3):ZIP 含 JSON + 照片 · 纯文件操作"""

    def test_create_backup_zip_contains_json(self, tmp_path, monkeypatch):
        import export_backup
        import output_config

        chef_out = tmp_path / "chef_out"
        chef_out.mkdir(exist_ok=True)
        (chef_out / "source_photos").mkdir(exist_ok=True)
        (chef_out / "source_photos" / "菜_a.jpg").write_bytes(b"jpg1")
        (chef_out / "photos").mkdir(exist_ok=True)
        (chef_out / "photos" / "菜_b.png").write_bytes(b"png1")
        monkeypatch.setenv("CHEF_OUTPUT_DIR", str(chef_out))

        zip_path = tmp_path / "backup_test.zip"
        backup = export_backup.create_backup(zip_path)

        assert backup["recipe_count"] >= 0
        assert backup["zip_path"] == str(zip_path)
        assert set(backup["photo_counts"].keys()) == {"photos", "source_photos", "work_photos"}
        # photos/source_photos 有文件,work_photos 不存在 → 0
        assert backup["photo_counts"]["photos"] == 1
        assert backup["photo_counts"]["source_photos"] == 1
        assert backup["photo_counts"]["work_photos"] == 0

        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            # 至少一个 17 表 JSON
            json_names = [n for n in names if n.endswith(".json")]
            assert json_names, "ZIP 必须含 JSON"
            # 照片按目录名归档
            assert any(n.startswith("source_photos/") for n in names)
            assert any(n.startswith("photos/") for n in names)
            # JSON 可解析且含 17 表字段
            data = json.loads(zf.read(json_names[0]).decode("utf-8"))
            assert "recipes" in data
            assert "tables" in data

    def test_create_backup_no_photo_dirs(self, tmp_path, monkeypatch):
        """无照片目录 → 全部 0,仍能出 ZIP(降级不炸)"""
        import export_backup

        chef_out = tmp_path / "chef_out2"
        chef_out.mkdir(exist_ok=True)
        monkeypatch.setenv("CHEF_OUTPUT_DIR", str(chef_out))

        zip_path = tmp_path / "backup_empty.zip"
        backup = export_backup.create_backup(zip_path)
        assert sum(backup["photo_counts"].values()) == 0
        with zipfile.ZipFile(zip_path) as zf:
            assert [n for n in zf.namelist() if n.endswith(".json")]

    def test_main_cli_success(self, tmp_path, monkeypatch):
        """CLI 三段式:success + data 含 zip_path/receipt_path(隔离 env,防模块级 env 泄漏)"""
        chef_out = tmp_path / "chef_out3"
        chef_out.mkdir(exist_ok=True)
        monkeypatch.setenv("CHEF_OUTPUT_DIR", str(chef_out))
        env = seeded_env(tmp_path)

        out_zip = tmp_path / "cli_test.zip"
        r = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "export_backup.py"), "--out", str(out_zip)],
            capture_output=True, text=True, encoding="utf-8", env=env,
        )
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert data["status"] == "success"
        assert data["data"]["zip_path"] == str(out_zip)
        assert data["data"]["receipt_path"] and Path(data["data"]["receipt_path"]).exists()
        assert "photo_counts" in data["data"]
        assert data["data"]["import_files"]  # import 兼容文件非空

    def test_restore_roundtrip_e2e(self, tmp_path):
        """验收 e2e:备份 → 解压 → recipes_import 逐个导入新库 → 17 表数据完整恢复"""
        import sqlite3
        env = seeded_env(tmp_path)
        out_zip = tmp_path / "rt.zip"
        r = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "export_backup.py"), "--out", str(out_zip)],
            capture_output=True, text=True, encoding="utf-8", env=env,
        )
        assert r.returncode == 0, r.stderr
        assert json.loads(r.stdout)["status"] == "success"

        # 解压 → recipes_import/
        unz = tmp_path / "unz"
        unz.mkdir()
        with zipfile.ZipFile(out_zip) as zf:
            zf.extractall(unz)
        imp_dir = unz / "recipes_import"
        files = sorted(imp_dir.glob("*.json"))
        assert files, "ZIP 必须含 recipes_import/ 嵌套 JSON(恢复=解压+导入)"

        # 新库逐个导入
        db2 = tmp_path / "db2"
        db2.mkdir()
        env2 = dict(env)
        env2["SKILLS_DB_PATH"] = str(db2)
        r = subprocess.run(
            [sys.executable, str(CLI_INIT), "init"],
            capture_output=True, text=True, encoding="utf-8", env=env2,
        )
        assert r.returncode == 0, r.stderr
        for f in files:
            r = subprocess.run(
                [sys.executable, str(SCRIPT_DIR / "import_orchestrator.py"), str(f)],
                capture_output=True, text=True, encoding="utf-8", env=env2,
            )
            assert r.returncode == 0, f"恢复导入失败 {f.name}: {r.stdout[:400]}"

        # 17 表完整性断言(种子=宫保虾球:2 食材/2 步骤/2 季节/2 做法/2 口味/1 技法/1 tip/1 背景/1 营养)
        conn = sqlite3.connect(str(db2 / "chef_data.db"))
        expect = {
            "recipes": 1, "recipe_categories": 1, "recipe_seasons": 2,
            "recipe_cooking_methods": 2, "recipe_flavors": 2, "recipe_diet_tags": 1,
            "recipe_meal_types": 1, "ingredients": 2, "cooking_steps": 2,
            "step_ingredients": 1, "step_techniques": 1, "tips": 1,
            "background_knowledge": 1, "cookware": 1, "nutrition_info": 1,
        }
        for t, n in expect.items():
            got = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            assert got == n, f"{t}: 期望 {n} 行,恢复后 {got} 行"
        row = conn.execute("SELECT name, difficulty, servings FROM recipes").fetchone()
        assert row[0] == "宫保虾球" and row[1] == "中等"
        conn.close()

    def test_restore_incomplete_recipe_blocked_by_reject_rule(self, tmp_path):
        """边界:源数据缺 tips/techniques(如真实老库辣椒炒肉)的菜,恢复时被 T5 拒绝制如实拦截。

        这不是备份缺陷——备份 JSON 完整保留原样;恢复走录入域拒绝制,
        缺 tips/techniques 时校验列出缺失,AI 引导用户补 1 条真实值(与录入语义一致)。
        """
        env = seeded_env(tmp_path)
        # 用转换器直接构造一个缺 tips/techniques 的嵌套 dict(模拟真实老库缺字段)
        sys.path.insert(0, str(SCRIPT_DIR))
        import export_backup
        flat = {
            "_recipe": {"id": "x1", "name": "老菜", "difficulty": "简单", "servings": 1,
                        "total_time_minutes": 10, "status": "未做", "photo_url": "p",
                        "source": "s", "source_url": "u", "description": "老库缺 tips"},
            "recipe_categories": [], "recipe_seasons": [], "recipe_cooking_methods": [],
            "recipe_flavors": [], "recipe_diet_tags": [], "recipe_meal_types": [],
            "ingredients": [], "cooking_steps": [], "step_ingredients": [],
            "step_techniques": [], "tips": [], "recipe_history": [],
            "background_knowledge": [], "recipe_relations": [], "cookware": [],
            "nutrition_info": [],
        }
        nested = export_backup.to_import_format(flat)
        # 转换如实:空 tips/techniques 不造假填充(键缺失 = 缺字段,交给拒绝制拦截)
        assert "tips" not in nested or nested["tips"] == []
        assert "techniques" not in nested or nested["techniques"] == []

        # 导入被拒绝制拦截:错误列出 tips/techniques 缺失(友好,非静默丢数据)
        import import_orchestrator
        res = import_orchestrator.orchestrate_import(nested)
        assert res["status"] == "error"
        fields = [e.get("field") for e in (res.get("errors") or [])]
        assert "tips" in fields and "techniques" in fields

    def test_receipt_html_has_08_and_payload(self, tmp_path, monkeypatch):
        """回执 HTML:08 双按钮 + INJECT-DATA 已替换(无残留占位符)"""
        chef_out = tmp_path / "chef_out4"
        chef_out.mkdir(exist_ok=True)
        monkeypatch.setenv("CHEF_OUTPUT_DIR", str(chef_out))
        env = seeded_env(tmp_path)

        out_zip = tmp_path / "receipt_test.zip"
        r = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "export_backup.py"), "--out", str(out_zip)],
            capture_output=True, text=True, encoding="utf-8", env=env,
        )
        data = json.loads(r.stdout)
        receipt = Path(data["data"]["receipt_path"]).read_text(encoding="utf-8")
        assert "<!--INJECT-DATA-->" not in receipt        # 已注入
        assert "window.__DATA__" in receipt               # 数据注入
        assert "复制数据" in receipt and "复制日志" in receipt  # 08 双按钮
        assert "window.__A08__" in receipt
        assert "备份回执" in receipt or "备份完成" in receipt


class TestBackupReceiptTemplate:
    """backup_receipt.html 模板契约"""

    def test_placeholders(self):
        content = (TEMPLATES_DIR / "backup_receipt.html").read_text(encoding="utf-8")
        assert content.count("<!--INJECT-DATA-->") == 1
        assert content.count("<!--INJECT-08-->") == 1
        assert "5 状态 fallback" in content  # 守卫

    def test_scene_asset_registered(self):
        """数据管理.yaml 已登记 3 唤醒词 + backup_receipt.html 模板"""
        import yaml
        scene_file = SKILL_DIR / "scenes" / "数据管理.yaml"
        data = yaml.safe_load(scene_file.read_text(encoding="utf-8"))
        wakes = {s["wake_word"]: s for s in data["scenes"]}
        assert set(wakes) == {"体检", "批量改", "备份"}
        assert "数据管理/backup_receipt.html" in wakes["备份"]["html"]["template"]
        # 合并后的 scenarios.yaml 也要含(合并器同步)
        merged = yaml.safe_load((SKILL_DIR / "references" / "scenarios.yaml").read_text(encoding="utf-8"))
        merged_wakes = [s["wake_word"] for s in merged["scenarios"]]
        assert "体检" in merged_wakes and "批量改" in merged_wakes and "备份" in merged_wakes


class TestBatchEditCompare:
    """批量编辑(data-2):改前/改后对比确认(T13 · G8 补齐)"""

    def test_template_has_diff_features(self):
        content = (TEMPLATES_DIR / "batch_edit.html").read_text(encoding="utf-8")
        # 对比面板 + 预览按钮 + 可编辑输入 + 差异收集
        assert "diff-panel" in content
        assert "diff-btn" in content
        assert "edit-input" in content
        assert "collectDiff" in content
        assert "改前 / 改后对比" in content
        # 08 双按钮占位符(T3 已注入层)
        assert content.count("<!--INJECT-08-->") == 1
        assert content.count("<!--INJECT-DATA-->") == 1

    def test_render_batch_edit_smoke(self, tmp_path, monkeypatch):
        """渲染 smoke:成功出 HTML(改前/改后对比 UI 不崩)"""
        chef_out = tmp_path / "chef_out_be"
        chef_out.mkdir(exist_ok=True)
        monkeypatch.setenv("CHEF_OUTPUT_DIR", str(chef_out))
        env = seeded_env(tmp_path)
        out = tmp_path / "be.html"
        r = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "render_batch_edit.py"), "宫保虾球", "--out", str(out)],
            capture_output=True, text=True, encoding="utf-8", env=env,
        )
        assert r.returncode == 0, r.stderr
        html = out.read_text(encoding="utf-8")
        assert "diff-panel" in html
        assert "window.__DATA__" in html
        assert "复制数据" in html and "复制日志" in html


class TestSkillMdRegistration:
    """3 唤醒词登记:SKILL.md 路由表 + 唤醒词清单(J. 数据管理)"""

    def test_route_table_has_3_wake_words(self):
        content = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        route_line = [l for l in content.splitlines() if "体检 / 批量改 / 备份" in l]
        assert route_line, "跨 Skill 路由表必须登记 体检/批量改/备份"
        assert "export_backup.py" in route_line[0]

    def test_wake_word_list_has_j_section(self):
        content = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        assert "### J. 数据管理（3个" in content
        assert "| 体检 |" in content
        assert "| 批量改 |" in content
        assert "| 备份 |" in content
        # 头部计数同步更新
        assert "唤醒词清单（39个）" in content
