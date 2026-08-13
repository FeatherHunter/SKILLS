#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_help_center.py — 卡路里唤醒词速查台 HTML 渲染器(v4.0 · Base 参数化 HELP)

对应 SKILL.md 唤醒词: 卡路里HELP

设计(v4.0 · 2026-08-13 · #316 Base 重构 task ④):
- 数据源: scripts/_triggers.py **唯一权威**(运行时 SoT · #291 grilling Q4 拍板)
- 开发期 .scratch/scene_data/*.json 已转只读归档(2026-08-13 起不再消费, 不物理删除)
- 转换层: _triggers → scene-data 契约 v1(groups→subgroups→scenes · 公共组件/docs/scene-data-contract.md)
- 渲染: 公共组件/injector.py 注入 assets/help_template.html(Base 零翻译零适配 · 契约校验硬拦截)
- 文件契约保留(统一规则③): 卡路里_HELP_<TS>.html(calorie_html/)+ 根镜像 卡路里.html(ADR-0001)

缺口处置(#316 用户拍板 2026-08-13):
- 36 条 11-技能协同(JSON 独有)不迁入运行时: 归档 + 归属 #270 技能互联消费方票
- 23 条 legacy(_triggers 独有: 查榜 13 / 复盘 9 / 有备注 1)全部保留, 归 分析/既有唤醒词

用法:
    python scripts/render_help_center.py              # 默认: _triggers 唯一权威渲染 + 根镜像
    python scripts/render_help_center.py --output <p> # 显式覆盖输出
    python scripts/render_help_center.py --no-mirror  # 跳过 ADR-0001 根镜像
"""
import argparse
import importlib.util
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
BASE_SKILL_DIR = SKILL_DIR.parent / '公共组件'
HELP_TEMPLATE = BASE_SKILL_DIR / 'assets' / 'help_template.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path                          # noqa: E402
from _triggers import TRIGGERS                            # noqa: E402


# === 11 分类(展示序;技能协同无运行时 trigger, 不生成分组) ===
CATEGORIES_V3 = [
    ('🏠', '主页',       'home'),
    ('🍚', '饮食',       'diet'),
    ('⚖️', '体重',       'weight'),
    ('🏃', '运动',       'exercise'),
    ('💪', '健身计划',   'workout'),
    ('🎯', '目标管理',   'goal'),
    ('🧬', '身体细节',   'body_detail'),
    ('📸', '身材照片',   'body_photo'),
    ('⚙️', '基础信息',   'profile'),
    ('📊', '分析',       'analysis'),
]

# legacy category → 展示名(23 条 v2 时代触发词归入 v3 分类)
CATEGORY_LEGACY_NAME = {
    '复盘': '分析',
}

# 分类 → 子功能显式顺序(2026-08-02 用户拍板);未列出的子功能按首次出现序, 既有唤醒词恒最后
SUBFUNC_ORDER = {
    '基础信息': ['设置资料', '看档案', '改资料'],
    '目标管理': ['定目标', '看目标', '改目标'],
    '身体细节': ['记身体细节', '看身体细节', '比身体细节', '删身体细节'],
    '运动': ['记运动', '改运动', '看运动', '运动分析', '运动复盘'],
    '身材照片': ['存身材照', '看身材照', '比身材照', '管身材照'],
    '饮食': ['记饮食', '改饮食', '看饮食', '查食品', '看营养', '看排行', '饮食复盘', '餐别分布'],
    '健身计划': ['定训练计划', '看训练计划', '改训练计划', '落地训练', '计划复盘', '安全检查'],
}

OUTPUT_TYPE_LABELS = {
    'process': '过程',
    'result':  '结果',
    'receipt': '回执',
}


def _base_injector():
    """懒加载 Base 注入器(公共组件/injector.py), importlib 按文件路径加载防撞名。"""
    injector_path = BASE_SKILL_DIR / 'injector.py'
    if not injector_path.exists():
        raise RuntimeError('Base Skill 资产缺失: 找不到 公共组件/injector.py')
    spec = importlib.util.spec_from_file_location('base_injector', injector_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _base_assets():
    assets = BASE_SKILL_DIR / 'assets'
    js = (assets / 'base.js').read_text(encoding='utf-8').strip()
    css = (assets / 'base.css').read_text(encoding='utf-8').strip()
    return js, css


def build_contract() -> dict:
    """转换层: _triggers.py(唯一权威) → scene-data 契约 v1。

    映射:
      - 新 13 字段 scene: key→id / name→title / wake_word / output_type→types(过程/结果/回执) / prompt_template
      - legacy(v2 时代 23 条): 归 分析/既有唤醒词, types 不标(未分类), prompt = main_prompt.text
      - 子功能顺序: SUBFUNC_ORDER 优先 → 首次出现序 → 「既有唤醒词」恒最后
      - 11-技能协同无运行时 trigger, 不生成分组(36 条已归档, 归属 #270)
    """
    legacy_name = CATEGORY_LEGACY_NAME

    def _is_new(t: dict) -> bool:
        return 'output_type' in t and 'prompt_template' in t

    # 组装 scene 列表: 新格式在前(保持 _triggers 设计序), legacy 后置
    new_scenes = [t for t in TRIGGERS if _is_new(t)]
    legacy_scenes = [t for t in TRIGGERS if not _is_new(t)]

    groups = []
    group_index = {}
    for icon, name, key in CATEGORIES_V3:
        g = {'id': key, 'icon': icon, 'label': name, 'subgroups': []}
        groups.append(g)
        group_index[name] = g

    def _sub_key(cat_name: str, sub: str):
        order_list = SUBFUNC_ORDER.get(cat_name, [])
        if sub in order_list:
            return (0, order_list.index(sub), sub)
        if sub == '既有唤醒词':
            return (2, 0, sub)
        return (1, 0, sub)  # 未配置子功能按首次出现序(在 _scenes 内稳定排序)

    def _push(scene: dict, cat_name: str, sub: str):
        g = group_index.get(cat_name)
        if g is None:
            return
        sg = next((x for x in g['subgroups'] if x['label'] == sub), None)
        if sg is None:
            sg = {'id': f"{g['id']}_{len(g['subgroups']) + 1}", 'label': sub, 'scenes': []}
            g['subgroups'].append(sg)
        sg['scenes'].append(scene)

    # 新格式: 按 (子功能键, order, name) 稳定排序
    new_sorted = sorted(new_scenes, key=lambda t: (
        _sub_key(t.get('category', ''), t.get('subfunction', '')),
        t.get('order', 9999),
        t.get('name', ''),
    ))
    for t in new_sorted:
        cat = t.get('category', '')
        sub = t.get('subfunction') or '既有唤醒词'
        scene = {
            'id': t.get('key') or t.get('wake_word', ''),
            'title': t.get('name') or t.get('wake_word', ''),
            'wake_word': t.get('wake_word', ''),
            'status': '',
            'prompt_template': t.get('prompt_template', ''),
        }
        ot = OUTPUT_TYPE_LABELS.get(t.get('output_type', ''))
        if ot:
            scene['types'] = [ot]
        _push(scene, cat, sub)

    # legacy: 归 分析/既有唤醒词(名称映射), 按 wake_word 排序
    legacy_sorted = sorted(legacy_scenes, key=lambda t: t.get('wake_word', ''))
    for t in legacy_sorted:
        cat = legacy_name.get(t.get('category', ''), t.get('category', '分析'))
        scene = {
            'id': f"legacy_{t.get('wake_word', '')}",
            'title': t.get('wake_word', ''),
            'wake_word': t.get('wake_word', ''),
            'status': '',
            'prompt_template': (t.get('main_prompt') or {}).get('text', ''),
        }
        _push(scene, cat, '既有唤醒词')

    # 子功能最终排序(空组不生成)
    result_groups = []
    for g in groups:
        if not g['subgroups']:
            continue
        g['subgroups'].sort(key=lambda sg: _sub_key(g['label'], sg['label']))
        result_groups.append(g)

    total = sum(len(sg['scenes']) for g in result_groups for sg in g['subgroups'])
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    return {
        'skill_name': '卡路里',
        'title': '唤醒词速查台',
        'subtitle': f'{len(result_groups)} 分类 · {total} 场景 · 更新于 {now}',
        'contact': {
            'items': [
                {'label': 'GitHub', 'value': 'https://github.com/FeatherHunter/SKILLS'},
                {'label': 'Issues', 'value': 'https://github.com/FeatherHunter/SKILLS/issues'},
            ],
        },
        'groups': result_groups,
    }


def render_html(contract: dict) -> str:
    """Base help_template 注入: 契约校验(硬拦截) + 3 占位符注入。"""
    template = HELP_TEMPLATE.read_text(encoding='utf-8')
    mod = _base_injector()
    ok, msg = mod.validate_help_data(contract)
    if not ok:
        raise ValueError(f'HELP 数据校验失败: {msg}')
    js, css = _base_assets()
    html, err = mod.inject(template, contract, js_asset=js, css_asset=css, strict=False)
    if err:
        raise RuntimeError(f'Base 注入失败: {err}')
    return html


def mirror_to_root(help_html_path: Path, skill_dir: Path) -> Path | None:
    """ADR-0001: 把最新 HELP render 复制到 <skill_dir>/卡路里.html 根镜像"""
    mirror = skill_dir / '卡路里.html'
    archive_dir = skill_dir / '.scratch' / 'card-html-redesign' / 'archive'
    archive_dir.mkdir(parents=True, exist_ok=True)

    if mirror.exists():
        ts = datetime.now().strftime('%Y%m%d')
        backup = archive_dir / f'卡路里_SKILL镜像_{ts}.html'
        n = 1
        while backup.exists():
            backup = archive_dir / f'卡路里_SKILL镜像_{ts}_{n}.html'
            n += 1
        try:
            mirror.replace(backup)
        except Exception as e:
            print(f'⚠ mirror 备份失败(继续覆盖): {e}', file=sys.stderr)

    try:
        shutil.copy2(str(help_html_path), str(mirror))
        return mirror
    except Exception as e:
        print(f'⚠ mirror 复制失败: {e}', file=sys.stderr)
        return None


def main():
    p = argparse.ArgumentParser(description='渲染卡路里唤醒词速查台 HTML (v4.0 · Base 参数化 HELP)')
    p.add_argument('--output', help='输出文件路径(默认走 html_path 新规范)')
    p.add_argument('--no-mirror', action='store_true', help='跳过 ADR-0001 根镜像')
    args = p.parse_args()

    try:
        contract = build_contract()
        html = render_html(contract)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, '卡路里_HELP')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')

    if not args.no_mirror:
        mirror = mirror_to_root(out_path, SKILL_DIR)
        if mirror:
            print(f'   镜像 → {mirror}')

    total = sum(len(sg['scenes']) for g in contract['groups'] for sg in g['subgroups'])
    print(f'✅ {out_path}')
    print(f'   模式: _triggers.py 唯一权威 · {total} 场景 / {len(contract["groups"])} 分类')
    return 0


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    sys.exit(main())
