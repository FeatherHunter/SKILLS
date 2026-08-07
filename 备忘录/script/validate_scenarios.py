#!/usr/bin/env python3
"""备忘录场景资产校验器(私有 · #31 Q7 共享校验模块)

单一真相:测试(test_help.py)与生产(memo_render.py 渲染前)共用本模块,
保证坏数据不进 HELP HTML,且守门逻辑不分裂成两份实现。

历史:
  v1.0(#35):从 test_help.py 内联断言抽取。7 字段契约 + #31 8 决策
  新增约束(category 白名单 / subfunction 长度 / dependencies 非空 /
  无 order / 无 aliases / 无 wake_word_index)+ #33 归类落地。
"""
import re
from dataclasses import dataclass, field
from typing import Dict, List

REQUIRED_FIELDS = {
    "wake_word", "scenario_id", "scenario_title", "type",
    "dimensions", "prompt", "status", "result",
}

# type 流程类型白名单(08-HTML交互规范 · 与居家管家 scenes 同词汇 + 查看+回执,#179 对齐)
TYPE_WHITELIST = {
    "采集+回执", "查看", "查看+回执", "查看+选择", "查看+选择+回执",
    "向导+采集+回执", "向导+回执", "选择+回执",
}

# 无 order / 无 aliases / 无反向索引(#31 Q4/Q1/Q6 · 防回归:这些字段不许出现)
FORBIDDEN_FIELDS = {"order", "aliases", "wake_words", "wake_word_index"}

# prompt 不得暴露实现细节(§07 §3 反例)
PROMPT_FORBIDDEN = ["memo_cli.py", "memo.db", "templates/", "script/",
                    "SELECT ", "INSERT ", "UPDATE ", ".py", "ERR_"]


@dataclass
class ValidationResult:
    errors: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def __bool__(self) -> bool:
        return self.ok


def validate_scenarios(data: Dict) -> ValidationResult:
    """校验场景资产 dict(scenarios.yaml 解析结果)。

    Args:
        data: yaml.safe_load(scenarios.yaml) 的返回值

    Returns:
        ValidationResult: errors 列表,空 = 合法
    """
    res = ValidationResult()

    if not isinstance(data, dict):
        res.errors.append("顶层必须是 dict")
        return res

    # skill / version 基础键
    if data.get("skill") != "备忘录":
        res.errors.append(f"skill 应为 备忘录,实际 {data.get('skill')!r}")
    if not data.get("version"):
        res.errors.append("缺少 version")

    # categories 列表(#31 Q2)
    categories = data.get("categories")
    if not isinstance(categories, list) or not categories:
        res.errors.append("缺少 categories 列表(8 分类,#31 Q2)")
        return res
    cat_keys = []
    for c in categories:
        if not isinstance(c, dict) or "key" not in c or "name" not in c:
            res.errors.append(f"categories 元素缺 key/name: {c!r}")
            continue
        cat_keys.append(c["key"])
    if len(set(cat_keys)) != len(cat_keys):
        res.errors.append("categories key 重复")

    # scenarios 列表
    scenarios = data.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        res.errors.append("缺少 scenarios 列表")
        return res

    ids = []
    for s in scenarios:
        if not isinstance(s, dict):
            res.errors.append(f"场景非 dict: {s!r}")
            continue
        sid = s.get("scenario_id", "?")
        # 7 必填字段
        for f in sorted(REQUIRED_FIELDS):
            if f not in s:
                res.errors.append(f"[{sid}] 缺必填字段 {f}")
        # type 白名单(08 契约 · #179)
        tp = s.get("type")
        if tp not in TYPE_WHITELIST:
            res.errors.append(f"[{sid}] type={tp!r} 不在白名单 {sorted(TYPE_WHITELIST)}")
        # 唯一性(scenario_id 跨场景唯一;wake_word 允许多对一:
        # 备忘改分类 单条+批量 共用唤醒词,#33 归类确认)
        ids.append(sid)
        # 禁字段(#31 Q4/Q1/Q6)
        for f in sorted(FORBIDDEN_FIELDS):
            if f in s:
                res.errors.append(f"[{sid}] 不应含字段 {f}(#31 决策禁止)")
        # category 白名单(#31 Q2 · #33 落地)
        cat = s.get("category")
        if cat is None:
            res.errors.append(f"[{sid}] 缺 category(必填,#31 Q5)")
        elif cat not in cat_keys:
            res.errors.append(f"[{sid}] category={cat!r} 不在白名单 {cat_keys}")
        # subfunction 长度(#31 Q3)
        sub = s.get("subfunction")
        if sub is not None and (not isinstance(sub, str) or len(sub) > 24):
            res.errors.append(f"[{sid}] subfunction 非法: {sub!r}(须 ≤24 字字符串或空)")
        # dependencies 非空(#32 决议)
        deps = s.get("dependencies")
        if deps is not None and not str(deps).strip():
            res.errors.append(f"[{sid}] dependencies 存在但为空(#32 决议:须非空)")
        # prompt 泄漏(#35 继承 §07 §3)
        text = (s.get("prompt") or "") + " " + (s.get("result") or "")
        for f in PROMPT_FORBIDDEN:
            if f in text:
                res.errors.append(f"[{sid}] prompt/result 暴露实现细节: {f}")
        # 中文尖括号占位符(用户反馈 · 需手动删 < >)
        placeholders = re.findall(r'<[\u4e00-\u9fff]+>', (s.get("prompt") or ""))
        if placeholders:
            res.errors.append(f"[{sid}] prompt 含 <中文占位符>: {placeholders}")

    if len(ids) != len(set(ids)):
        dupes = [x for x in set(ids) if ids.count(x) > 1]
        res.errors.append(f"scenario_id 重复: {dupes}")

    return res


def validate_scenarios_file(path) -> ValidationResult:
    """加载 yaml 文件并校验(生产路径便捷入口)。"""
    import yaml
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return validate_scenarios(data)


if __name__ == "__main__":
    import sys
    from pathlib import Path

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if target is None:
        target = Path(__file__).parent.parent / "references" / "scenarios.yaml"
    r = validate_scenarios_file(target)
    if r.ok:
        print("OK · scenarios.yaml 校验通过")
    else:
        print("FAILED:")
        for e in r.errors:
            print(f"  - {e}")
        sys.exit(1)
