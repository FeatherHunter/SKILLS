#!/usr/bin/env python3
"""check_trigger_consistency.py — 卡路里 SKILL trigger 一致性检查

3 边单向对照:
  1. SKILL.md §完整 HTML 模板清单 的"强制 trigger"列  ⊆  SKILL.md frontmatter 触发词
  2. scripts/render_*.py docstring 声明的 trigger  ⊆  SKILL.md frontmatter 触发词

注意:frontmatter 触发词可以不在 HTML 模板表(那是"可文字答 trigger",V1.3 §⚠️ 强制性规定 第 4 条明示合法)。

docstring 格式:
  A. 单行: 对应 SKILL.md 唤醒词:trigger1 / trigger2 / ...
  B. 多行: 对应 SKILL.md 唤醒词(N 个):  ←同一行结束
            - trigger1/alias → mode=...
            - trigger2       → mode=...

用法:
    python scripts/check_trigger_consistency.py
    # 退出码: 0 = 一致, 1 = 有 drift
"""

import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
RENDER_DIR = SKILL_DIR / "scripts"


def parse_frontmatter_triggers(text: str) -> set:
    """提取 frontmatter 触发词

    v2.4.13 起:支持"主词(口语变体)"形式(如 `记吃了(刚吃了 / 刚才吃了 ...)`),内部用 `、` 分隔各主词,
    主词后括号内是口语变体注释,提取主词时跳过括号内容做规范化。
    """
    m = re.search(r'触发词:([^\n]+)', text)
    if not m:
        return set()
    out = set()
    for t in m.group(1).split('、'):
        t = t.strip()
        if not t:
            continue
        # 去括号(口语变体)
        t = re.sub(r'[（(][^）)]*[）)]', '', t).strip()
        if t:
            out.add(t)
    return out


def parse_html_template_triggers(text: str) -> set:
    sec = re.search(
        r'### 完整 HTML 模板清单.*?(?=^---|\n## |\Z)',
        text, re.DOTALL | re.MULTILINE,
    )
    if not sec:
        return set()
    triggers = set()
    for line in sec.group(0).split('\n'):
        if not line.startswith('| `templates/') and not line.startswith('| `process_progress') \
                and not line.startswith('| `home_dashboard'):
            continue
        cols = line.split('|')
        if len(cols) < 3:
            continue
        cell = cols[2]
        for part in re.split(r'[/／、\n|]+', cell):
            t = part.strip().strip('`').strip()
            t = re.sub(r'[（(][^）)]*[）)]', '', t).strip()
            if not t:
                continue
            triggers.add(t)
    return triggers


# render docstring 里常见的 trigger 别名(语义同 SKILL.md canonical 触发词)
# 例如 render_nutrition_label.py 注释提到 "识别营养表" / "营养成分确认",
# 实际 SKILL.md 触发词是 "拍营养表"(同一 HTML 接受多入口)。
TRIGGER_ALIASES = {
    '识别营养表': '拍营养表',
    '营养成分确认': '拍营养表',
}


def normalize_trigger(t: str) -> str:
    """标准化 trigger 字符串(去反引号/括号/别名映射)"""
    t = t.strip()
    # 去所有反引号
    t = t.replace('`', '').strip()
    # 去括号注释
    t = re.sub(r'[（(][^）)]*[）)]', '', t).strip()
    # alias 映射
    t = TRIGGER_ALIASES.get(t, t)
    return t


def parse_render_docstring_triggers() -> dict:
    """支持 A/B 两种 docstring 格式(行级匹配,不跨行)"""
    results = {}
    for f in sorted(RENDER_DIR.glob('render_*.py')):
        text = f.read_text(encoding='utf-8')
        m = re.search(r'"""([\s\S]*?)"""', text)
        if not m:
            results[f.name] = set()
            continue
        doc = m.group(1)
        lines = doc.split('\n')

        triggers = set()
        in_trigger_block = False

        for line in lines:
            stripped = line.strip()
            if '对应 SKILL.md 唤醒词' in stripped and ':' in stripped:
                after = stripped.split(':', 1)[1].strip()
                if after:
                    for t in re.split(r'[/／、]+', after):
                        t = normalize_trigger(t)
                        if not t or t in ('触发词', 'mode', '模式'):
                            continue
                        triggers.add(t)
                    in_trigger_block = False
                else:
                    in_trigger_block = True
                continue

            if in_trigger_block:
                if '对应模板:' in stripped:
                    in_trigger_block = False
                    continue
                if not stripped.startswith('-'):
                    continue
                content = stripped[1:].strip()
                content = re.split(r'→|->', content, 1)[0]
                for t in re.split(r'[/／、]+', content):
                    t = normalize_trigger(t)
                    if not t or t in ('模式', 'mode'):
                        continue
                    triggers.add(t)

        results[f.name] = triggers
    return results


def main():
    text = SKILL_MD.read_text(encoding='utf-8')
    fm = parse_frontmatter_triggers(text)
    html = parse_html_template_triggers(text)
    render_map = parse_render_docstring_triggers()

    issues = []

    # ticket 03 · ADR-0002: 校验 _triggers.py 中 alias_of 关系(指向已存在的 wake_word)
    sys.path.insert(0, str(RENDER_DIR))
    try:
        from _triggers import TRIGGERS as _TRIG
        all_wakes = {t['wake_word'] for t in _TRIG}
        for t in _TRIG:
            ao = t.get('alias_of')
            if ao is None:
                continue
            if ao not in all_wakes:
                issues.append(
                    f'[_triggers.py alias_of] wake_word="{t["wake_word"]}" 的 '
                    f'alias_of="{ao}" 未在 TRIGGERS 中找到(必须指向已存在的 wake_word)'
                )
    except Exception as e:
        issues.append(f'[_triggers.py 导入失败] {e}')

    # 对照 1: HTML 模板表 ⊆ frontmatter
    only_html = html - fm
    if only_html:
        issues.append(f'[HTML 模板 → frontmatter] {len(only_html)} 个 trigger 在强制表但 frontmatter 未列:')
        for t in sorted(only_html):
            issues.append(f'  - {t}')

    # 对照 2: render docstring ⊆ frontmatter
    for fn, ts in sorted(render_map.items()):
        if not ts:
            continue
        not_in_fm = ts - fm
        if not_in_fm:
            issues.append(f'[{fn} docstring → frontmatter] {len(not_in_fm)} 个 trigger 不在 frontmatter:')
            for t in sorted(not_in_fm):
                issues.append(f'  - {t}')

    print(f'frontmatter trigger 数: {len(fm)}')
    print(f'HTML 模板表 trigger 数: {len(html)}')
    all_render = set().union(*render_map.values())
    print(f'render docstring 涉及 trigger 数: {len(all_render)}')

    # 信息输出:frontmatter 有但 HTML 表无的 trigger(可文字答,合法但需开发者主动确认)
    text_only = fm - html
    if text_only:
        print(f'\n[info] frontmatter 有但 HTML 表无({len(text_only)} 个,可文字答,合法):')
        for t in sorted(text_only):
            print(f'  - {t}')
        print('  提示:这些 trigger 无 HTML 模板,AI 可文字答。如有 HTML 模板请加 §完整 HTML 模板清单。')

    print()
    if not issues:
        print('✅ HTML 模板表 ↔ frontmatter ↔ render docstring 三边一致')
        sys.exit(0)

    n_classes = sum(1 for x in issues if x.startswith('['))
    print(f'⚠ 发现 {n_classes} 类 drift:')
    for x in issues:
        print(x)
    sys.exit(1)


if __name__ == '__main__':
    main()