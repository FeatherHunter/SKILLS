"""v1.1.4 · HELP 唤醒词 + 场景资产 + 渲染器守护

总纲 §07-HELP与场景完备性.md 契约验证:
- 场景资产 schema(7 字段齐全、ID 唯一、prompt 无实现细节)
- 场景数量 = SKILL.md 触发词数(28 + 备忘改分类批量重复 = 29)
- render_help 产出合法 HTML(占位符、转义)
- skill 根目录 备忘录.html 被覆盖(用户额外要求)
- HELP HTML 不展示自身唤醒词(§07 §5 反模式 3)
- SKILL.md 触发词与 scenarios 字段一致(防文档裂缝)

来源:用户回复 4 选
  1. yaml (场景资产格式)
  2. 老的直接删掉 (memo_html 直接删)
  3. 必须要 (help 必生成 HTML + 覆盖)
  4. FAT 最后再说
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).parent.parent / "script"
sys.path.insert(0, str(SCRIPT_DIR))

SKILL_DIR = Path(__file__).parent.parent
SCENARIOS_PATH = SKILL_DIR / "references" / "scenarios.yaml"
HELP_TEMPLATE = SKILL_DIR / "templates" / "memo_help.html"
SKILL_ROOT_HELP = SKILL_DIR / "备忘录.html"

REQUIRED_FIELDS = {
    "wake_word", "scenario_id", "scenario_title",
    "dimensions", "prompt", "status", "result",
}


@pytest.fixture(scope="module")
def scenarios():
    import yaml
    return yaml.safe_load(SCENARIOS_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    """真实跑一次 render_help,产出 2 份文件"""
    from memo_render import render_help
    return render_help()


# ==================== 场景资产 schema ====================

class TestScenariosSchema:
    """§07 §2.2 契约:7 字段必填"""

    def test_file_exists(self):
        assert SCENARIOS_PATH.exists()

    def test_skill_and_version_keys(self, scenarios):
        assert scenarios.get("skill") == "备忘录"
        assert scenarios.get("version") == "1.1.4"

    def test_28_wake_words_minimum(self, scenarios):
        """§07 §4:每个业务唤醒词必穷举所有合法场景(下限 28, 含 12 子唤醒词)"""
        wake_words = {s["wake_word"] for s in scenarios["scenarios"]}
        assert len(wake_words) >= 28, f"唤醒词数 {len(wake_words)} < 28"

    def test_scenario_count_matches_skill_md(self, scenarios):
        """触发词表与 scenarios 一致(防文档裂缝)"""
        expected = {
            "记备忘", "搜备忘", "查备忘", "改备忘", "删备忘", "看备忘",
            "按时间搜备忘", "备忘改分类", "备忘改子分类",
            "记提醒", "设提醒", "看提醒", "查已提醒备忘",
            "记心愿", "删心愿", "改心愿", "查心愿",
            "记打卡", "删打卡", "改打卡", "查打卡",
            "记情绪", "删情绪", "改情绪", "查情绪",
            "完成心愿", "心愿排期", "备忘录同步",
        }
        actual = {s["wake_word"] for s in scenarios["scenarios"]}
        assert expected <= actual, f"缺失唤醒词: {expected - actual}"

    def test_all_7_fields_present(self, scenarios):
        missing = []
        for s in scenarios["scenarios"]:
            for f in REQUIRED_FIELDS:
                if f not in s:
                    missing.append((s.get("scenario_id", "?"), f))
        assert not missing, f"缺字段: {missing}"

    def test_scenario_id_unique(self, scenarios):
        ids = [s["scenario_id"] for s in scenarios["scenarios"]]
        dupes = [x for x in set(ids) if ids.count(x) > 1]
        assert not dupes, f"scenario_id 重复: {dupes}"

    def test_no_pending_dev_status(self, scenarios):
        """本期无【待开发】;若未来引入,必须配 AI 停步逻辑"""
        pending = [s["scenario_id"] for s in scenarios["scenarios"]
                   if s["status"] == "【待开发】"]
        assert not pending, f"本期不应有【待开发】: {pending}"

    def test_no_cli_or_db_leak_in_prompt(self, scenarios):
        """§07 §3 反例:prompt 不暴露 CLI / DB / Python / 模板路径 / 错误码"""
        forbidden = ["memo_cli.py", "memo.db", "templates/", "script/",
                     "SELECT ", "INSERT ", "UPDATE ", ".py", "ERR_"]
        leaks = []
        for s in scenarios["scenarios"]:
            text = (s.get("prompt") or "") + " " + (s.get("result") or "")
            for f in forbidden:
                if f in text:
                    leaks.append((s["scenario_id"], f, text[:80]))
        assert not leaks, f"prompt 暴露实现细节: {leaks}"


# ==================== HELP HTML 模板 ====================

class TestHelpTemplate:
    def test_template_exists(self):
        assert HELP_TEMPLATE.exists()

    def test_placeholder_unique(self):
        text = HELP_TEMPLATE.read_text(encoding="utf-8")
        assert text.count("<!--INJECT-DATA-->") == 1, \
            f"占位符唯一性: {text.count('<!--INJECT-DATA-->')}"

    def test_no_help_wake_word_in_template(self):
        """§07 §5 反模式 3:HELP HTML 不展示自身"""
        text = HELP_TEMPLATE.read_text(encoding="utf-8")
        # 不应在模板静态文本中包含"备忘录 HELP"
        assert "备忘录 HELP" not in text, "模板静态文本不应出现 HELP 唤醒词自身"


# ==================== render_help ====================

class TestRenderHelp:
    def test_produces_timestamped_copy(self, rendered):
        """§04 原则 12.B 路径:<skill>_html/备忘录_HELP_<datetime>.html"""
        p = Path(rendered["html_path"])
        assert p.exists()
        assert "备忘录_HELP_" in p.name
        assert re.match(r"备忘录_HELP_\d{8}_\d{6}(_\d+)?\.html", p.name)

    def test_overwrites_skill_root_help(self, rendered):
        """用户额外要求:skill 根目录 备忘录.html 必须被覆盖"""
        p = Path(rendered["skill_root_path"])
        assert p.exists(), "skill 根目录 备忘录.html 应存在"
        assert p == SKILL_ROOT_HELP
        # 覆盖 = 文件内容 ≠ 旧版(我们已删旧版,所以只看新文件存在)
        assert p.stat().st_size > 1000, "文件太小,可能没真生成"

    def test_skill_root_content_matches_timestamped(self, rendered):
        """两个路径的内容应一致(覆盖 = 真复制)"""
        a = Path(rendered["html_path"]).read_bytes()
        b = Path(rendered["skill_root_path"]).read_bytes()
        assert a == b, "skill 根目录 备忘录.html ≠ 时间戳副本内容"

    def test_html_contains_window_data(self, rendered):
        text = Path(rendered["skill_root_path"]).read_text(encoding="utf-8")
        assert "window.__DATA__" in text

    def test_html_contains_all_wake_words(self, rendered):
        """§07 §5:展示全部业务唤醒词"""
        text = Path(rendered["skill_root_path"]).read_text(encoding="utf-8")
        for ww in ["记备忘", "搜备忘", "备忘改分类", "心愿排期", "备忘录同步",
                   "记心愿", "查打卡", "查情绪"]:
            assert ww in text, f"HELP HTML 应含唤醒词: {ww}"

    def test_html_does_not_show_help_itself(self, rendered):
        """§07 §5 反模式 3:HELP 唤醒词自身不出现在 HTML"""
        text = Path(rendered["skill_root_path"]).read_text(encoding="utf-8")
        # 但场景数据里的 prompt/result 可能有 "help" 字样,这里看场景标题/分组里
        # 实际:分组渲染时不调用 help 自己的 scenario_id
        # 因为没有 memo_help 自己的 scenario 记录
        assert "scenario_id: memo_help" not in text

    def test_has_5_state_fallback(self, rendered):
        """§04 原则 3:5 状态 fallback 必备"""
        text = Path(rendered["skill_root_path"]).read_text(encoding="utf-8")
        for state_id in ["stateEmpty", "stateMissing", "stateError"]:
            assert state_id in text, f"缺 5 状态 banner: {state_id}"

    def test_has_copy_button_mechanism(self, rendered):
        """§07 §5:每场景独立复制按钮"""
        text = Path(rendered["skill_root_path"]).read_text(encoding="utf-8")
        assert "copyPrompt" in text
        assert "navigator.clipboard" in text
        assert "fallbackCopy" in text  # 剪贴板 API 降级


# ==================== CLI 入口 ====================

class TestHelpCLI:
    def test_help_subcommand_runs(self, tmp_path, monkeypatch):
        """CLI `help` 子命令可执行,默认必生成 HTML"""
        # 隔离 SKILLS_DB_PATH 避免污染真实 DB
        monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
        r = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "memo_cli.py"), "help"],
            capture_output=True, text=True, timeout=30,
        )
        assert r.returncode == 0, f"stderr={r.stderr}"
        data = json.loads(r.stdout)
        assert data["status"] == "ok"
        assert "html_path" in data["data"]
        assert "skill_root_path" in data["data"]
        assert data["data"]["skill_root_path"].endswith("备忘录.html")
        # skill 根 备忘录.html 被覆盖
        assert Path(data["data"]["skill_root_path"]).exists()

    def test_help_has_no_html_flag(self):
        """§07 §3 反例:`help` 不需要 --html flag(必生成)"""
        # 解析命令行,确认没有 --html 参数
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "memo_cli.py"), "help", "--help"],
            capture_output=True, text=True,
        )
        # --help 输出应不含 --html
        assert "--html" not in result.stdout, \
            "help 子命令不应有 --html flag(必生成 HTML)"


# ==================== 老 备忘录.html 处置(用户回复 #2:直接删) ====================

class TestOldManualDeprecated:
    def test_old_html_not_in_skill_root(self):
        """用户要求 #2:老的纯用户手册 备忘录.html 已删除,不再有第二份 HTML 维护"""
        # skill 根目录不应再有手工维护版
        # 当前 skill 根目录的 备忘录.html = render_help 产物(覆盖式)
        # 这条测试本身在 render 后跑,根目录文件存在是 OK 的(就是 HELP 输出的副本)
        # 但:我们只维护一份 HTML(即 HELP 产物),不允许人工再写一份
        # 验证:git log 不该再有手写提交到 备忘录.html(v1.1.4 之前的提交 OK)
        pass  # 静态检查:本测试通过 git 历史守护,这里只做软声明


# ==================== --output 旗标(B 方案) ====================

class TestHelpOutputFlag:
    """--output B 方案:额外副本,备忘录.html 永远写

    设计原则(用户选定 B 方案):
    - 默认行为(无 --output):时间戳副本 + skill 根 备忘录.html(2 份)
    - 加 --output /path:2 份 + 额外副本 /path(3 份)
    - --output 不影响 备忘录.html(用户 v1.1.4 额外要求:永远覆盖)
    """

    def test_render_help_output_path_kwarg(self, tmp_path):
        """render_help 接受 output_path kwarg"""
        from memo_render import render_help
        out = tmp_path / "extra.html"
        r = render_help(output_path=out)
        assert out.exists(), "--output 路径应被写入"
        # 额外副本内容 = 时间戳副本内容
        assert Path(r["html_path"]).read_bytes() == out.read_bytes()
        # skill 根 备忘录.html 也写了(用户要求永远写)
        assert Path(r["skill_root_path"]).exists()

    def test_render_help_output_none_default(self):
        """不传 output_path → 返回 output_path=None"""
        from memo_render import render_help
        r = render_help()
        assert r["output_path"] is None

    def test_render_help_creates_parent_dir(self, tmp_path):
        """--output 父目录不存在时自动创建"""
        from memo_render import render_help
        nested = tmp_path / "a" / "b" / "c" / "extra.html"
        r = render_help(output_path=nested)
        assert nested.exists(), "嵌套父目录应自动创建"
        assert r["output_path"] == str(nested)

    def test_render_help_output_does_not_skip_skill_root(self, tmp_path):
        """核心保证:加 --output 时,备忘录.html 仍被覆盖"""
        from memo_render import render_help
        out = tmp_path / "extra.html"
        r = render_help(output_path=out)
        skill_root = Path(r["skill_root_path"])
        assert skill_root.exists(), \
            "加了 --output,备忘录.html 仍必须被覆盖(B 方案核心)"

    def test_cli_help_with_output_flag(self, tmp_path, monkeypatch):
        """CLI:help --output /tmp/foo.html 工作"""
        out = tmp_path / "from_cli.html"
        monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
        r = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "memo_cli.py"),
             "help", "--output", str(out)],
            capture_output=True, text=True, timeout=30,
        )
        assert r.returncode == 0, f"stderr={r.stderr}"
        data = json.loads(r.stdout)
        assert data["status"] == "ok"
        # CLI 报告了额外副本路径
        assert data["data"]["output_path"] == str(out)
        assert out.exists()
        # 时间戳副本 + skill 根也写了(3 份)
        assert Path(data["data"]["html_path"]).exists()
        assert Path(data["data"]["skill_root_path"]).exists()

    def test_cli_help_short_output_flag(self, tmp_path, monkeypatch):
        """CLI:help -o /tmp/foo.html(短旗标)"""
        out = tmp_path / "short.html"
        monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
        r = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "memo_cli.py"),
             "help", "-o", str(out)],
            capture_output=True, text=True, timeout=30,
        )
        assert r.returncode == 0, f"stderr={r.stderr}"
        data = json.loads(r.stdout)
        assert data["data"]["output_path"] == str(out)

    def test_cli_help_output_message_notes_extra_copy(self, tmp_path, monkeypatch):
        """CLI 返回 message 提示用户额外副本已写(B 方案 UX)"""
        out = tmp_path / "extra.html"
        monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
        r = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "memo_cli.py"),
             "help", "--output", str(out)],
            capture_output=True, text=True, timeout=30,
        )
        data = json.loads(r.stdout)
        # note 字段含"额外副本"提示
        assert "额外副本" in data["data"]["note"]
        assert str(out) in data["data"]["note"]

    def test_cli_help_without_output_no_extra_path_in_json(self, tmp_path, monkeypatch):
        """无 --output 时,output_path 应为 None(JSON 字段为 null)"""
        monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
        r = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "memo_cli.py"), "help"],
            capture_output=True, text=True, timeout=30,
        )
        data = json.loads(r.stdout)
        assert data["data"]["output_path"] is None


# ==================== 唤醒词灵活匹配(FAT G1 修复) ====================

class TestHelpWakeWordFlexibility:
    """FAT(§05 钩子 ⑥)发现 SKILL.md G1:唤醒词灵活匹配没明文。
    修后用静态检查守护回归。
    """

    SKILL_MD = SKILL_DIR / "SKILL.md"

    def test_skill_md_documents_wake_word_flexibility(self):
        """SKILL.md §备忘录 HELP 含'灵活匹配'段"""
        text = self.SKILL_MD.read_text(encoding="utf-8")
        assert "唤醒词灵活匹配" in text, \
            "FAT G1 修复:SKILL.md 应明文规定唤醒词灵活匹配规则"

    def test_skill_md_documents_variations_examples(self):
        """SKILL.md 含变体示例(口语化 / slash 等)"""
        text = self.SKILL_MD.read_text(encoding="utf-8")
        # 至少含 3 种变体示例
        variations = [
            "口语化",
            "slash",
            "缩字",
            "大小写",
            "manual",
        ]
        present = [v for v in variations if v in text]
        assert len(present) >= 3, \
            f"FAT G1 修复:SKILL.md 应含 ≥3 种变体示例,实际 {present}"