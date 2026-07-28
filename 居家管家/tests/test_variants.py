"""唤醒词变体(variants)结构契约测试(总纲 §钩子 3 · 变体管理)

验证 references/scenarios.yaml 中 TOP 5 核心唤醒词的 variants 字段:
- 每个 variant 是 {direction: str, phrase: str} 结构
- direction ∈ {同义, 口语, 模糊}(钩子 3 字面)
- 每 scenario 至少 2 个 direction(钩子 3 要求"2-3 变体")
- phrase 非空 + 无禁用字符(正斜杠 反斜杠 冒号 星号 问号 引号 尖括号 竖线)

TOP 5 核心(按 audit 使用频率,grilling Q7=audit):
查物品 / 看物品 / 录物品 / 盘物品 / 统物品
"""
import re
from pathlib import Path

import pytest
import yaml

SKILL_DIR = Path(__file__).parent.parent
SCENARIOS_YAML = SKILL_DIR / "references" / "scenarios.yaml"

TOP5_WAKE_WORDS = ["查物品", "看物品", "录物品", "盘物品", "统物品"]
VALID_DIRECTIONS = {"同义", "口语", "模糊"}
FORBIDDEN_CHARS = re.compile(r'[/\\:*?"<>|]')


def _load_scenarios():
    """加载 scenarios.yaml,返回 scenarios 列表(每个是一个 scenario dict)。

    单一加载点:所有 test case 复用,避免重复 IO。yaml.safe_load 安全加载。
    """
    data = yaml.safe_load(SCENARIOS_YAML.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"scenarios.yaml 顶层应为 dict,实际 {type(data).__name__}"
    assert "scenarios" in data, "scenarios.yaml 缺 'scenarios' 顶层 key"
    scenarios = data["scenarios"]
    assert isinstance(scenarios, list), f"'scenarios' 应为 list,实际 {type(scenarios).__name__}"
    return scenarios


def _scenarios_for_wake_word(scenarios, wake_word):
    """返回某个 wake_word 的所有 scenario(一个唤醒词可能多个 scenario)。

    variants 字段挂在 scenario 级别。TOP 5 核心词中,有的词(如查物品)有多个 scenario;
    我们要求**至少一个** scenario 携带 variants(不必每个都带,因为变体是唤醒词级而非场景级)。
    """
    return [s for s in scenarios if s.get("wake_word") == wake_word]


def _variants_for_wake_word(scenarios, wake_word):
    """返回某 wake_word 的所有 scenario 的 variants 合并列表。

    若多个 scenario 都有 variants,合并去重校验。若都没有,返回空列表。
    """
    merged = []
    for s in _scenarios_for_wake_word(scenarios, wake_word):
        v = s.get("variants")
        if v:
            merged.extend(v)
    return merged


def test_top5_scenarios_have_variants():
    """TOP 5 核心唤醒词在 scenarios.yaml 中至少一个 scenario 携带 variants 字段(非空)。"""
    scenarios = _load_scenarios()
    missing = []
    for ww in TOP5_WAKE_WORDS:
        variants = _variants_for_wake_word(scenarios, ww)
        if not variants:
            missing.append(ww)
    assert not missing, (
        f"TOP 5 核心唤醒词缺 variants 字段(应为非空 list):{missing}。"
        f"见 references/scenarios.yaml,每个 TOP 5 唤醒词至少一个 scenario 加 variants。"
    )


def test_variants_have_direction_label():
    """每个 variant 的 direction ∈ {{同义, 口语, 模糊}}(钩子 3 字面,3 方向)。"""
    scenarios = _load_scenarios()
    bad = []
    for ww in TOP5_WAKE_WORDS:
        for v in _variants_for_wake_word(scenarios, ww):
            d = v.get("direction")
            if d not in VALID_DIRECTIONS:
                bad.append((ww, v, d))
    assert not bad, (
        f"variant.direction 必须是 {VALID_DIRECTIONS} 之一,以下不合法:{bad}"
    )


def test_variants_have_at_least_2_directions():
    """每 TOP 5 唤醒词至少 2 个 direction(钩子 3 要求 2-3 变体,2 是下限)。"""
    scenarios = _load_scenarios()
    short = []
    for ww in TOP5_WAKE_WORDS:
        variants = _variants_for_wake_word(scenarios, ww)
        directions = {v.get("direction") for v in variants if v.get("direction") in VALID_DIRECTIONS}
        if len(directions) < 2:
            short.append((ww, directions))
    assert not short, (
        f"每 TOP 5 唤醒词至少 2 个 direction(同义/口语/模糊 取 2),以下不足:{short}"
    )


def test_variant_phrases_non_empty():
    """每个 variant 的 phrase 字段是非空字符串(strip 后非空)。"""
    scenarios = _load_scenarios()
    bad = []
    for ww in TOP5_WAKE_WORDS:
        for i, v in enumerate(_variants_for_wake_word(scenarios, ww)):
            phrase = v.get("phrase")
            if not isinstance(phrase, str) or not phrase.strip():
                bad.append((ww, i, v))
    assert not bad, f"variant.phrase 必须是非空字符串,以下不合法:{bad}"


def test_variants_no_forbidden_chars():
    """variant.phrase 不含 Windows 文件名禁用字符(/ \\ : * ? \" < > |)。

    因为 phrase 可能被复制成 HTML 文件名片段或日志 key,禁用字符会破坏路径。
    """
    scenarios = _load_scenarios()
    bad = []
    for ww in TOP5_WAKE_WORDS:
        for v in _variants_for_wake_word(scenarios, ww):
            phrase = v.get("phrase", "")
            if FORBIDDEN_CHARS.search(phrase):
                bad.append((ww, phrase))
    assert not bad, (
        f"variant.phrase 含禁用字符(/ \\ : * ? \" < > |):{bad}"
    )
