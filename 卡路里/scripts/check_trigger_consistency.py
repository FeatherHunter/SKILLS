#!/usr/bin/env python3
"""check_trigger_consistency.py — 卡路里 SKILL trigger 一致性检查

3 边单向对照(v2.4.19 · #242/#235 配套 · 权威源迁移):
  1. SKILL.md §完整 HTML 模板清单 的"强制 trigger"列  ⊆  scripts/_triggers.py 权威源
  2. scripts/render_*.py docstring 声明的 trigger  ⊆  scripts/_triggers.py 权威源
  3. frontmatter description 路由契约:≤1024 字符 + 含「卡路里HELP」锚点

历史(v2.4.18c 前):对照基准是 frontmatter description 全量触发词。
#235 发现:9855 字符 description 把 HELP 触发词埋没在注意力盲区(92.9% 位置),
opencode 规范 description ≤ 1024 字符。故权威源迁移到 _triggers.py(运行时 SoT,
ADR-0001),frontmatter 只做路由摘要(HELP 置顶 + 高频词),全量触发词以
_triggers.py + SKILL.md §触发词速查表 为准。

注意:权威源 trigger 可以不在 HTML 模板表(那是"可文字答 trigger",V1.3 §⚠️ 强制性规定 第 4 条明示合法)。

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


def parse_frontmatter_triggers(text: str, known_wake_words: set | None = None) -> set:
    """提取 frontmatter 触发词

    v2.4.13 起:支持"主词(口语变体)"形式(如 `记吃了(刚吃了 / 刚才吃了 ...)`),内部用 `、` 分隔各主词,
    主词后括号内是口语变体注释,提取主词时跳过括号内容做规范化。

    2026-08-02 ticket #4 修复:词本身含括号的场景名(记体重（含备注）/看体重曲线（带目标）/体重复盘（本周）/
    定体重目标(自动算截止))不能被当口语变体剥掉。解法 = 数据驱动锚点:传入 _triggers.py 的 wake_word 全集,
    条目以某个已知 wake_word 开头 → 该 wake_word 即主词;否则回退剥所有括号(旧 legacy 词)。
    """
    m = re.search(r'触发词:([^\n]+)', text)
    if not m:
        return set()
    out = set()
    known = sorted(known_wake_words or [], key=len, reverse=True)  # 长词优先(带括号的比不带的长)
    for t in m.group(1).split('、'):
        t = t.strip()
        if not t:
            continue
        if known:
            hit = next((k for k in known if t == k or t.startswith(k + '(') or t.startswith(k + '（')), None)
            if hit:
                out.add(hit)
                continue
        # 回退:剥所有括号(旧 legacy 词,无词内括号)
        t = re.sub(r'[（(][^）)]*[）)]', '', t).strip()
        if t:
            out.add(t)
    return out


def _strip_variant_parens(t: str) -> str:
    """去口语变体括号(内容含 / 才剥),词本身括号保留(记体重（含备注）)"""
    return re.sub(r'[（(][^）)]*[/／][^）)]*[）)]', '', t).strip()


def parse_html_template_triggers(text: str, known_wake_words: set | None = None) -> set:
    sec = re.search(
        r'### 完整 HTML 模板清单.*?(?=^---|\n## |\Z)',
        text, re.DOTALL | re.MULTILINE,
    )
    if not sec:
        return set()
    triggers = set()
    known = sorted(known_wake_words or [], key=len, reverse=True)
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
            if not t:
                continue
            # 2026-08-02 ticket #4:锚点优先(词本身含括号的场景名),回退只剥口语变体,再回退剥所有括号(旧 legacy 注释)
            if known:
                hit = next((k for k in known if t == k or t.startswith(k + '(') or t.startswith(k + '（')), None)
                if hit:
                    triggers.add(hit)
                    continue
            t2 = _strip_variant_parens(t)
            if t2 and t2 != t:
                triggers.add(t2)
                continue
            t3 = re.sub(r'[（(][^）)]*[）)]', '', t).strip()
            if t3:
                triggers.add(t3)
    return triggers


# render docstring 里常见的 trigger 别名(语义同 SKILL.md canonical 触发词)
# 例如 render_nutrition_label.py 注释提到 "识别营养表" / "营养成分确认",
# 实际 SKILL.md 触发词是 "拍营养表"(同一 HTML 接受多入口)。
TRIGGER_ALIASES = {
    '识别营养表': '拍营养表',
    '营养成分确认': '拍营养表',
}


_KNOWN_WAKE = None  # 2026-08-02 ticket #4:docstring 解析的已知 wake_word 锚点(词本身含括号的场景名)


def normalize_trigger(t: str) -> str:
    """标准化 trigger 字符串(去反引号/括号/别名映射)

    2026-08-02 ticket #4:已知 wake_word 锚点优先(记体重（含备注）等词内括号不再被剥),
    回退只剥口语变体括号,再回退剥所有括号(旧 legacy 注释)。
    """
    t = t.strip().replace('`', '').strip()
    if _KNOWN_WAKE:
        hit = next((k for k in _KNOWN_WAKE if t == k or t.startswith(k + '(') or t.startswith(k + '（')), None)
        if hit:
            return TRIGGER_ALIASES.get(hit, hit)
    t2 = _strip_variant_parens(t).strip()
    if t2 and t2 != t:
        return TRIGGER_ALIASES.get(t2, t2)
    t3 = re.sub(r'[（(][^）)]*[）)]', '', t).strip()
    return TRIGGER_ALIASES.get(t3, t3)


def parse_render_docstring_triggers(known_wake_words=None) -> dict:
    """支持 A/B 两种 docstring 格式(行级匹配,不跨行)"""
    global _KNOWN_WAKE
    _KNOWN_WAKE = known_wake_words or None
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
    sys.path.insert(0, str(RENDER_DIR))
    try:
        from _triggers import TRIGGERS as _TRIG
        _known = {t['wake_word'] for t in _TRIG}
    except Exception:
        _known = None
    fm = parse_frontmatter_triggers(text, known_wake_words=_known)
    html = parse_html_template_triggers(text, known_wake_words=_known)
    render_map = parse_render_docstring_triggers(known_wake_words=_known)

    issues = []

    # 权威源(v2.4.19 · #242/#235 配套):触发词权威 = _triggers.py 运行时 SoT,
    # 不是 frontmatter。frontmatter description 只做路由摘要(HELP 置顶 + 高频词),
    # 全量触发词以 _triggers.py + SKILL.md §触发词速查表 为准。
    try:
        from _triggers import TRIGGERS as _TRIG
        authority = {t['wake_word'] for t in _TRIG}
    except Exception as e:
        issues.append(f'[_triggers.py 导入失败] {e}')
        authority = set()

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

    # 对照 1: HTML 模板表 ⊆ 权威源(_triggers.py)
    # 元词豁免:卡路里HELP 渲染的是速查台本身(render_help_center.py 专属),
    # 不是场景数据,允许不在 _triggers.py(_triggers.py 是速查台的数据源,不能自指)。
    META_WORDS = {'卡路里HELP'}
    only_html = (html - authority) - META_WORDS
    if only_html:
        issues.append(f'[HTML 模板 → _triggers.py] {len(only_html)} 个 trigger 在强制表但权威源未列:')
        for t in sorted(only_html):
            issues.append(f'  - {t}')

    # 对照 2: render docstring ⊆ 权威源(_triggers.py)(同样豁免元词)
    for fn, ts in sorted(render_map.items()):
        if not ts:
            continue
        not_in_fm = (ts - authority) - META_WORDS
        if not_in_fm:
            issues.append(f'[{fn} docstring → _triggers.py] {len(not_in_fm)} 个 trigger 不在权威源:')
            for t in sorted(not_in_fm):
                issues.append(f'  - {t}')

    # 对照 3(v2.4.19 · #235 配套):frontmatter description 路由契约
    #   - description ≤ 1024 字符(opencode 规范;超长稀释注意力,HELP 触发词被埋没)
    #   - 「卡路里HELP」必须在 description 中(HELP 是路由首要锚点)
    #   - 触发词有效性:description 里每个触发词必须能在权威源(_triggers.py)定位
    #     (v2.4.19 对抗审查补 · #235):精确命中 或 是权威词的裸词别名
    #     (如「对比体重」⊂「对比体重：本周 vs 上周」,SKILL.md L447 明示裸词别名机制)
    import re as _re
    fm_text = _re.search(r'^description:\s*[>|]?\s*\n?(.*?)(?=\n\s*metadata:|\n---)', text, _re.M | _re.S)
    desc_len = len(''.join(fm_text.group(1).split())) if fm_text else 0
    if desc_len > 1024:
        issues.append(
            f'[frontmatter description] {desc_len} 字符 > 1024 上限(opencode 规范;'
            f'超长会把「卡路里HELP」等路由锚点埋没在注意力盲区)'
        )
    if '卡路里HELP' not in (fm_text.group(1) if fm_text else ''):
        issues.append('[frontmatter description] 缺少「卡路里HELP」路由锚点(必须置顶)')
    if fm_text:
        _fm_seg = _re.search(r'触发词:(.+?)(?:完整触发词|\Z)', fm_text.group(1), _re.S)
        _seg = _fm_seg.group(1) if _fm_seg else ''
        _desc_words = [w.strip() for w in _seg.split('、') if w.strip()]
        _bad = []
        for _w in _desc_words:
            if _w in authority:
                continue
            # 裸词别名:某权威词以该词开头且去掉变体部分(：/（ 后的描述)后等于该词
            _is_alias = any(
                a.startswith(_w) and a[len(_w):].startswith(('：', '（', '(', ':'))
                for a in authority
            )
            if not _is_alias:
                _bad.append(_w)
        if _bad:
            issues.append(
                f'[frontmatter description] {len(_bad)} 个触发词无法在权威源定位'
                f'(须为 _triggers.py 精确词或裸词别名):'
            )
            for _b in _bad:
                issues.append(f'  - {_b}')

    # 对照 4(v2.4.19 · #242 配套):所有入口脚本必须带 _io_guard 编码防护
    # (GBK/cp1252 控制台 print emoji 会 UnicodeEncodeError → AI 误判渲染失败)
    # 覆盖范围(v2.4.19 对抗审查补):全部 scripts/*.py 入口(有 __main__ 块),
    # 不只 render_*.py —— 未来新增 CLI 缺 guard 也要被抓住(防回归盲区修复)。
    # 纯库模块(如 render_goal_common.py)被入口 import,其 print 由入口进程承载,guard 由入口提供。
    import ast as _ast
    no_guard = []
    for _f in sorted(RENDER_DIR.glob('*.py')):
        _t = _f.read_text(encoding='utf-8-sig', errors='replace')
        if '_io_guard' in _t:
            continue
        try:
            _tree = _ast.parse(_t)
        except SyntaxError:
            continue
        _is_entry = any(
            isinstance(_n, _ast.If) and isinstance(_n.test, _ast.Compare)
            and isinstance(_n.test.left, _ast.Name) and _n.test.left.id == '__name__'
            for _n in _ast.walk(_tree)
        )
        if _is_entry:
            no_guard.append(_f.name)
    if no_guard:
        issues.append(
            f'[_io_guard 编码防护] {len(no_guard)} 个入口脚本缺少 guard_io()'
            f'(GBK 控制台 print emoji 会崩 · #242):'
        )
        for _n in no_guard:
            issues.append(f'  - {_n}')

    print(f'权威源(_triggers.py) trigger 数: {len(authority)}')
    print(f'HTML 模板表 trigger 数: {len(html)}')
    all_render = set().union(*render_map.values())
    print(f'render docstring 涉及 trigger 数: {len(all_render)}')
    print(f'frontmatter description 长度: {desc_len} 字符(规范 ≤1024)')

    # 信息输出:权威源有但 HTML 表无的 trigger(可文字答,合法但需开发者主动确认)
    text_only = authority - html
    if text_only:
        print(f'\n[info] 权威源有但 HTML 表无({len(text_only)} 个,可文字答,合法):')
        for t in sorted(text_only):
            print(f'  - {t}')
        print('  提示:这些 trigger 无 HTML 模板,AI 可文字答。如有 HTML 模板请加 §完整 HTML 模板清单。')

    print()
    if not issues:
        print('✅ HTML 模板表 ↔ _triggers.py ↔ render docstring 三边一致 + description 路由契约合规')
        sys.exit(0)

    n_classes = sum(1 for x in issues if x.startswith('['))
    print(f'⚠ 发现 {n_classes} 类 drift:')
    for x in issues:
        print(x)
    sys.exit(1)


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    main()