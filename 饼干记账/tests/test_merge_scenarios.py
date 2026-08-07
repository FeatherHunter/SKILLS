"""merge_scenarios.py 合并器测试(公共层 · T0 #164)

覆盖:汇总结构 / 跨域唤醒词唯一 / scenario_id 唯一 / 字段契约 / prompt 骨架 / 幂等
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import merge_scenarios as ms  # noqa: E402


def _scene(**overrides) -> dict:
    """构造一个合法场景条目(字段齐全)"""
    base = {
        "id": "t-1-1",
        "scenario_id": "test_scene",
        "scenario_title": "测试场景",
        "type": "查看",
        "status": "",
        "html": {"template": "测试/t.html", "command_cn": "测试", "data_source": "bills"},
        "prompt": "请加载「饼干记账」技能,帮我测试(唤醒词:测试):\n",
        "result": "HTML 展示测试结果",
    }
    base.update(overrides)
    return base


def _domain(key: str, scenes=None) -> dict:
    return {
        "version": ms.VERSION,
        "domain": key,
        "subs": [
            {
                "name": "测试",
                "wake_words": [
                    {"wake_word": "测试词", "scenes": scenes or [_scene()]},
                ],
            }
        ],
    }


# ── 汇总结构 ──────────────────────────────────────────────────────────────────


class TestSummary:
    def test_domains_declares_all_seven(self):
        """汇总 domains meta 固定声明 7 域(即使未枚举)"""
        summary = ms.build_summary({})
        assert len(summary["domains"]) == 7
        keys = [d["key"] for d in summary["domains"]]
        assert keys == ["setup", "write", "query", "analysis", "goal", "account", "link"]

    def test_scenes_only_enumerated_domains(self):
        """scenes 只含已枚举域;未枚举域不出现在 scenes"""
        summary = ms.build_summary({"setup": _domain("setup")})
        assert len(summary["scenes"]) == 1
        assert summary["scenes"][0]["key"] == "setup"

    def test_help_wake_words_preserved(self):
        summary = ms.build_summary({})
        assert summary["help_wake_words"] == ["饼干记账 HELP", "饼干记账 帮助", "查帮助", "能做什么"]

    def test_nested_structure(self):
        """嵌套结构:域 → sub → wake_word → scenes"""
        summary = ms.build_summary({"setup": _domain("setup")})
        dom = summary["scenes"][0]
        assert dom["subs"][0]["name"] == "测试"
        assert dom["subs"][0]["wake_words"][0]["wake_word"] == "测试词"
        sc = dom["subs"][0]["wake_words"][0]["scenes"][0]
        assert sc["scenario_id"] == "test_scene"
        assert set(sc.keys()) == {"id", "scenario_id", "scenario_title", "type", "status", "html", "prompt", "result"}

    def test_real_three_domains_count(self):
        """真实 3 域合并:28 场景(write 9 + query 13 + setup 6)"""
        domain_data = {}
        for key in ms.DOMAIN_KEYS:
            data = ms.load_domain_yaml(key)
            if data is not None:
                domain_data[key] = data
        summary = ms.build_summary(domain_data)
        stats = ms.collect_stats(summary)
        assert stats["scenes"] == 28
        assert stats["wake_words"] == 23


# ── 全局校验 ──────────────────────────────────────────────────────────────────


class TestGlobalValidation:
    def test_wake_word_global_conflict_detected(self):
        """跨域唤醒词重复必须报错(合并器抓「恢复」冲突的先例)"""
        errors = []
        summary = ms.build_summary({"write": _domain("write"), "setup": _domain("setup")})
        ms.validate_global(summary, errors)
        assert any("唤醒词全局重复" in e for e in errors)

    def test_scenario_id_global_conflict_detected(self):
        errors = []
        summary = ms.build_summary({"write": _domain("write"), "setup": _domain("setup")})
        ms.validate_global(summary, errors)
        assert any("scenario_id 全局重复" in e for e in errors)

    def test_scene_id_global_conflict_detected(self):
        errors = []
        summary = ms.build_summary({"write": _domain("write"), "setup": _domain("setup")})
        ms.validate_global(summary, errors)
        assert any("场景 id 全局重复" in e for e in errors)

    def test_clean_summary_no_errors(self):
        errors = []
        summary = ms.build_summary({"write": _domain("write", scenes=[_scene()])})
        ms.validate_global(summary, errors)
        assert errors == []


# ── 域内校验 ──────────────────────────────────────────────────────────────────


class TestDomainValidation:
    def test_missing_required_field(self):
        errors = []
        ms.validate({"version": ms.VERSION, "domain": "setup", "subs": []}, "setup", errors)
        assert errors == []

    def test_bad_scene_missing_field(self):
        errors = []
        bad = _scene()
        del bad["result"]
        ms.validate(_domain("setup", [bad]), "setup", errors)
        assert any("缺字段 'result'" in e for e in errors)

    def test_bad_html_missing_field(self):
        errors = []
        bad = _scene(html={"template": "x.html"})
        ms.validate(_domain("setup", [bad]), "setup", errors)
        assert any("html 缺字段 'command_cn'" in e for e in errors)

    def test_empty_prompt_rejected(self):
        errors = []
        bad = _scene(prompt="   \n")
        ms.validate(_domain("setup", [bad]), "setup", errors)
        assert any("prompt 为空" in e for e in errors)

    def test_prompt_head_rule(self):
        errors = []
        bad = _scene(prompt="帮我查一下(唤醒词:测试):\n")
        ms.validate(_domain("setup", [bad]), "setup", errors)
        assert any("prompt 首行不符合骨架" in e for e in errors)

    def test_domain_field_mismatch(self):
        errors = []
        ms.validate(_domain("write"), "setup", errors)
        assert any("domain 字段" in e for e in errors)

    def test_duplicate_wake_word_in_domain(self):
        errors = []
        data = _domain("setup")
        data["subs"][0]["wake_words"].append({"wake_word": "测试词", "scenes": [_scene(id="t-2", scenario_id="x2")]})
        ms.validate(data, "setup", errors)
        assert any("唤醒词在域内重复" in e for e in errors)


# ── 幂等 ──────────────────────────────────────────────────────────────────────


class TestIdempotency:
    def test_dump_is_deterministic(self):
        domain_data = {}
        for key in ms.DOMAIN_KEYS:
            data = ms.load_domain_yaml(key)
            if data is not None:
                domain_data[key] = data
        summary = ms.build_summary(domain_data)
        d1 = ms.yaml.safe_dump(summary, allow_unicode=True, sort_keys=False, width=120)
        d2 = ms.yaml.safe_dump(summary, allow_unicode=True, sort_keys=False, width=120)
        assert d1 == d2
