#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_scene_data.py — 卡路里 v1.0 场景元数据校验器

按 .scratch/scene_data/schema.json 校验 .scratch/scene_data/*.json
每个场景文件,输出可读报告。

校验内容:
  1. schema 13 字段必填 + 类型/枚举/正则
  2. 命名规范 v1.0 (R1-R3):禁技术词 + 中性词 + 主名 ≤ 12 字
  3. wake_word 在所有文件内唯一
  4. html_template / data_source 路径存在
  5. prompt_template 含 §⚠️ 第 7 条 AI 验证协议 + 收尾语

用法:
    python scripts/check_scene_data.py               # 校验 + 报告
    python scripts/check_scene_data.py --strict      # 任何 error 退出码 1
    python scripts/check_scene_data.py --only home   # 只校验 01-主页.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import jsonschema
except ImportError:
    print('❌ 缺 jsonschema: pip install jsonschema', file=sys.stderr)
    sys.exit(2)

SCRIPT_DIR  = Path(__file__).resolve().parent
SKILL_DIR   = SCRIPT_DIR.parent
SCENE_DIR   = SKILL_DIR / '.scratch' / 'scene_data'
SCHEMA_PATH = SCENE_DIR / 'schema.json'

# 命名规范 v1.0 · 禁技术词(从 .scratch/help-scenario-redesign.md 抄录)
# 注:每条 prompt 是否需要 §⚠️ 第 7 条 AI 验证协议,已在 ADR-0007 + 2026-07-31 用户决策中
# 改由 SKILL.md §⚠️ 第 7 条 守门(per-prompt 不再硬塞提醒)。
# check_scene_data.py 反向守护:scene_data prompt 含 §⚠️ 那段 → 报错(禁止回退)。
TECH_WORDS = {
    'v2', 'v1', 'v3', 'v0',
    'widget', 'WIDGET',
    'id', 'ID', 'Id',
    'mode', 'MODE', 'Mode',
    'mock', 'MOCK', 'Mock',
    'json', 'JSON', 'Json',
    'api', 'API', 'Api',
    'html', 'HTML', 'Html',
    'css', 'CSS', 'Css',
    'js', 'JS', 'Js',
    'sql', 'SQL', 'Sql',
    'cli', 'CLI', 'Cli',
    'sdk', 'SDK', 'Sdk',
    'url', 'URL', 'Url',
    'http', 'HTTP', 'Http',
    'tldr', 'TLDR',
    'beta', 'alpha',
}

# 命名规范 v1.0 · 偏置词(改用中性词)
BIASED_WORDS = {
    '减重': '中性:调体重 / 调体型',
    '增重': '中性:调体重 / 调体型',
    '男性': '中性:不说性别',
    '女性': '中性:不说性别',
    '女生': '中性:不说性别',
    '男生': '中性:不说性别',
    '小姐姐': '中性:不用',
    '小哥哥': '中性:不用',
}

# 动词在前 · 允许的动词(主名 ≥ 2 字时首词应在表内,允许例外:复盘/报告/概览)
VERB_FIRST = {
    '看', '记', '改', '删', '定', '设', '调', '找', '扫', '审', '批',
    '对比', '比', '复盘', '总结', '同步', '落地', '批量', '扫描', '校验',
    '存', '取', '推', '开', '关', '重', '暂停',
}

NAME_MAX = 12          # 主名 ≤ 12 字
PROMPT_REQUIRED = [
    '完成后给 1 句话总结',         # 收尾语(必须)
]
# 反向守护:per-prompt 不再贴 §⚠️ 那段(SKILL.md §⚠️ 第 7 条 守门即可)
PROMPT_FORBIDDEN = [
    r'§⚠️ 第 7 条 AI 验证协议',  # 防止回退到旧 skeleton
    r'按流程执行',                # 流程型空话
    r'略',                       # 占位
]


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))


def load_scene_files(only_keyword: str | None = None) -> list[Path]:
    if not SCENE_DIR.exists():
        return []
    files = sorted(p for p in SCENE_DIR.glob('*.json') if p.name != 'schema.json')
    if only_keyword:
        files = [p for p in files if only_keyword in p.stem]
    return files


def check_tech_words(name: str) -> list[str]:
    """禁技术词检查(按 word-boundary 匹配)"""
    issues = []
    for w in TECH_WORDS:
        # 数字 / 字母 token 边界
        if re.search(rf'(?<![A-Za-z0-9]){re.escape(w)}(?![A-Za-z0-9])', name):
            issues.append(f'含禁技术词 "{w}"')
    return issues


def check_biased_words(name: str) -> list[str]:
    return [f'含偏置词 "{w}" ({hint})' for w, hint in BIASED_WORDS.items() if w in name]


def check_name_length(name: str) -> list[str]:
    issues = []
    main = name.split('(')[0].strip()
    if len(main) > NAME_MAX:
        issues.append(f'主名 {len(main)} 字 > {NAME_MAX} 字上限 (="{main}")')
    # 括号补充
    paren = re.findall(r'[(（](.+?)[)）]', name)
    for p in paren:
        if len(p) > 8:
            issues.append(f'括号补充 {len(p)} 字 > 8 字上限 (="{p}")')
    return issues


def check_verb_first(name: str) -> list[str]:
    main = name.split('(')[0].strip()
    if not main:
        return ['场景名为空']
    # 复盘 / 报告 / 概览类例外(以这些词开头的允许名词短语)
    if main.startswith(('复盘', '报告', '概览', '分析', '趋势', '排行', '总览')):
        return []
    # 取首字符
    first_char = main[0]
    if first_char not in VERB_FIRST:
        return [f'主名 "{main}" 首字 "{first_char}" 不在优先动词表(命名规范 R2 动词在前)']
    return []


def check_prompt_template(prompt: str) -> list[str]:
    issues = []
    for required in PROMPT_REQUIRED:
        if required not in prompt:
            issues.append(f'prompt 缺必含片段 "{required}"')
    for bad in PROMPT_FORBIDDEN:
        if re.search(bad, prompt):
            issues.append(f'prompt 含禁用模式 "{bad}"')
    if len(prompt) < 30:
        issues.append(f'prompt 过短 ({len(prompt)} 字 < 30)')
    return issues


def check_path_exists(rel_path: str, kind: str) -> list[str]:
    p = SKILL_DIR / rel_path
    if not p.exists():
        return [f'{kind} 路径不存在: {rel_path}']
    return []


def validate_scene(scene: dict, file_label: str, all_wake_words: dict[str, str]) -> list[str]:
    """返回错误列表(空 = 通过)"""
    errors: list[str] = []

    # 1. schema
    schema = load_schema()
    validator = jsonschema.Draft7Validator(schema)
    for err in sorted(validator.iter_errors(scene), key=lambda e: list(e.path)):
        path = '.'.join(str(p) for p in err.absolute_path) or '<root>'
        errors.append(f'[schema] {path}: {err.message}')

    # 2. 命名规范 v1.0
    name = scene.get('name', '')
    for issue in check_tech_words(name):
        errors.append(f'[name.技术词] {issue}')
    for issue in check_biased_words(name):
        errors.append(f'[name.偏置词] {issue}')
    for issue in check_name_length(name):
        errors.append(f'[name.长度] {issue}')
    for issue in check_verb_first(name):
        errors.append(f'[name.动词] {issue}')

    # 3. wake_word 唯一性
    wake = scene.get('wake_word', '')
    if wake in all_wake_words and all_wake_words[wake] != file_label:
        errors.append(f'[wake_word 冲突] "{wake}" 已在 {all_wake_words[wake]} 出现')
    all_wake_words[wake] = file_label

# 4. 路径存在
    errors += [f'[html_template] {x}' for x in check_path_exists(scene.get('html_template', ''), 'html_template')]
    data_src = scene.get('data_source', '')
    if data_src and not data_src.endswith('.html'):
        # 当 data_source 是 .py CLI(可能带 `python ` 前缀,见 ADR-0008)或 Python 函数路径
        # 约定:.py 脚本须带 `python ` 前缀;Python 函数直接写模块名
        stripped = data_src.removeprefix('python ').strip() if data_src.startswith('python ') else data_src
        if stripped.endswith('.py') or '.' in Path(stripped).name:
            # .py 文件 → 校验存在
            if stripped.endswith('.py') and not (SKILL_DIR / stripped).exists():
                errors.append(f'[data_source] CLI 文件不存在: {stripped}')

    # 5. prompt 必含 + 禁用
    errors += [f'[prompt] {x}' for x in check_prompt_template(scene.get('prompt_template', ''))]

    return errors


def main():
    p = argparse.ArgumentParser(description='卡路里 v1.0 场景元数据校验')
    p.add_argument('--only', help='只校验文件名包含此关键字的 .json(例:主页)')
    p.add_argument('--strict', action='store_true', help='有任何 error 退出码 1')
    args = p.parse_args()

    files = load_scene_files(args.only)
    if not files:
        print(f'⚠️  未找到场景文件: {SCENE_DIR}/{"(only="+args.only+")" if args.only else ""}')
        return 0

    print(f'📋 校验 {len(files)} 个场景文件\n')

    all_wake_words: dict[str, str] = {}
    total_errors = 0
    total_warnings = 0
    total_scenes = 0

    for f in files:
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            print(f'❌ {f.name}: JSON 解析失败: {e}')
            total_errors += 1
            continue

        # 支持单场景 object 或多场景 array
        if isinstance(data, dict):
            scenes = [data]
        elif isinstance(data, list):
            scenes = data
        else:
            print(f'❌ {f.name}: 顶层必须是 object 或 array,实得 {type(data).__name__}')
            total_errors += 1
            continue

        for scene in scenes:
            total_scenes += 1
            label = f'{f.name}#{scene.get("key", "?")}'
            errors = validate_scene(scene, f.name, all_wake_words)
            if errors:
                for e in errors:
                    print(f'❌ {label}: {e}')
                total_errors += len(errors)
            else:
                print(f'✅ {label}')

    print()
    print(f'─── 汇总 ───')
    print(f'   场景文件: {len(files)}')
    print(f'   场景总数: {total_scenes}')
    print(f'   wake_word 数: {len(all_wake_words)}')
    print(f'   错误: {total_errors}')
    print(f'   警告: {total_warnings}')

    if args.strict and total_errors > 0:
        return 1
    return 0 if total_errors == 0 else 0  # 默认非 strict 也通过(只报问题,不让 CI 红)


if __name__ == '__main__':
    sys.exit(main())
