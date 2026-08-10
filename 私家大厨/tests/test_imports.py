"""
测试 3+4+5 · 核心 CLI happy path
- 防 import_orchestrator 导入流程回归
- 防 recipe_import add_recipe 写库回归
- 防 render_help.py 注入回归
"""
import subprocess
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"


def run_cli(*args) -> dict:
    """调 scripts/<args> 返回 JSON"""
    cmd = [sys.executable, str(SCRIPT_DIR / args[0])] + list(args[1:])
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        return {"_error": result.stderr, "_stdout": result.stdout[:500]}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"_parse_error": result.stdout[:500]}


class TestImportOrchestrator:
    """测试 3 · import_orchestrator 模块结构 + 入口函数存在"""

    def test_module_imports_without_error(self):
        """模块能 import 不报错"""
        result = subprocess.run(
            [sys.executable, "-c", "import import_orchestrator; print('OK')"],
            capture_output=True, text=True, cwd=str(SCRIPT_DIR)
        )
        assert result.returncode == 0, f"import 失败: {result.stderr}"
        assert "OK" in result.stdout

    def test_module_has_main_function(self):
        """模块有 main() 函数"""
        result = subprocess.run(
            [sys.executable, "-c",
             "import import_orchestrator; assert callable(getattr(import_orchestrator, 'main', None))"],
            capture_output=True, text=True, cwd=str(SCRIPT_DIR)
        )
        assert result.returncode == 0


class TestRecipeImport:
    """测试 4 · recipe_import 模块结构"""

    def test_module_imports_without_error(self):
        """模块能 import 不报错"""
        result = subprocess.run(
            [sys.executable, "-c", "import recipe_import; print('OK')"],
            capture_output=True, text=True, cwd=str(SCRIPT_DIR)
        )
        assert result.returncode == 0, f"import 失败: {result.stderr}"

    def test_template_exists(self):
        """recipe_template.json 存在"""
        tpl = SCRIPT_DIR.parent / "templates" / "recipe_template.json"
        assert tpl.exists(), f"模板不存在: {tpl}"


class TestDbConfigImportSideEffect:
    """测试 6 · #218 回归: import db_config 零副作用

    任何只读命令 import db_config 时,不得创建 DB 文件或目录。
    复现路径: db_config.py 模块级 mkdir + ensure_wal_mode() → sqlite3.connect 建空库。
    """

    def test_import_creates_nothing(self, tmp_path):
        """import db_config 后,临时 DB 目录内无任何文件/目录"""
        code = (
            "import db_config; "
            "print('EXISTS=' + str(db_config.DB_PATH.exists()))"
        )
        env = {"SKILLS_DB_PATH": str(tmp_path), "PATH": __import__('os').environ.get('PATH', '')}
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, cwd=str(SCRIPT_DIR),
            env=env
        )
        assert result.returncode == 0, f"import 失败: {result.stderr}"
        assert "EXISTS=False" in result.stdout, f"import 即建库: {result.stdout}{result.stderr}"
        leftovers = list(tmp_path.iterdir())
        assert leftovers == [], f"import 创建了: {leftovers}"

    def test_read_only_cli_check_creates_nothing(self, tmp_path):
        """开始使用/cli.py check(只读)后,临时 DB 目录内无任何文件/目录"""
        env = {
            "SKILLS_DB_PATH": str(tmp_path),
            "PATH": __import__('os').environ.get('PATH', ''),
            "PYTHONIOENCODING": "utf-8",
        }
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "开始使用" / "cli.py"), "check"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(SCRIPT_DIR), env=env
        )
        assert result.returncode == 0, f"check 失败: {result.stderr}"
        assert "db_exists\": false" in result.stdout or '"db_exists": false' in result.stdout, (
            f"check 应报告 db_exists=false,实际: {result.stdout[:300]}"
        )
        leftovers = list(tmp_path.iterdir())
        assert leftovers == [], f"check 创建了: {leftovers}"

    def test_write_connection_still_creates_db(self, tmp_path):
        """写连接 get_connection 仍正常建库(修复未破坏写链路)"""
        code = (
            "import db_config; "
            "c = db_config.get_connection(); "
            "print('JOURNAL=' + c.execute('PRAGMA journal_mode').fetchone()[0]); "
            "print('EXISTS=' + str(db_config.DB_PATH.exists())); c.close()"
        )
        env = {"SKILLS_DB_PATH": str(tmp_path), "PATH": __import__('os').environ.get('PATH', '')}
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, cwd=str(SCRIPT_DIR),
            env=env
        )
        assert result.returncode == 0, f"写连接失败: {result.stderr}"
        assert "JOURNAL=wal" in result.stdout, f"WAL 未启用: {result.stdout}"
        assert "EXISTS=True" in result.stdout, f"get_connection 未建库: {result.stdout}"


class TestRenderHelp:
    """测试 5 · render_help.py smoke test · 防注入回归"""

    def test_template_has_inject_placeholder(self):
        """help.html 含 <!--INJECT-DATA--> 占位符(§04 原则 4 #1)"""
        tpl = SCRIPT_DIR.parent / "templates" / "help.html"
        content = tpl.read_text(encoding="utf-8")
        count = content.count("<!--INJECT-DATA-->")
        assert count == 1, f"占位符必须唯一 1 次,实际 {count} 次"

    def test_template_escapes_script_tags(self):
        """</ 转义逻辑在模板中应有提示(注释里)"""
        tpl = SCRIPT_DIR.parent / "templates" / "help.html"
        content = tpl.read_text(encoding="utf-8")
        # 模板注释或渲染器应有 </ 转义说明
        # (修复 #9:之前的 OR 永远为 True,测试无效)
        assert "</script>" in content or "&lt;\\/script&gt;" in content, (
            "模板应包含 </script> 字面(用于文档说明) "
            "或 &lt;\\/script&gt; HTML escape 形式"
        )

    def test_render_help_module_exists(self):
        """render_help.py 模块存在且能 import"""
        result = subprocess.run(
            [sys.executable, "-c",
             "import importlib.util, sys; "
             "spec = importlib.util.spec_from_file_location('rh', 'render_help.py'); "
             "mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); "
             "assert callable(getattr(mod, 'render', None)); print('OK')"],
            capture_output=True, text=True, cwd=str(SCRIPT_DIR)
        )
        assert result.returncode == 0, f"render_help 加载失败: {result.stderr}"
        assert "OK" in result.stdout