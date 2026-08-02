#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_help_center.py — 卡路里唤醒词速查台 HTML 渲染器(v3.0)

对应 SKILL.md 唤醒词: 卡路里HELP

设计(v3.0 · 2026-07-31 · Phase 1 基础设施):
- 数据源:scripts/_triggers.py(运行时 SoT)+ .scratch/scene_data/*.json(开发期)
- 2 层折叠:L1 分类 + L2 子功能 → 平铺场景(无变体)
- 3 种 output_type: process / result / receipt
- 占位符唯一:<!--INJECT-DATA--> 恰好 1 次
- 结果型 · 原则 10 出口设计:每个场景 1 个 [📋 复制 prompt] 按钮

数据流(任务 2):
  1. 读 .scratch/scene_data/*.json(开发期,优先,新 13 字段 schema)
  2. 读 scripts/_triggers.py(运行时 SoT,补齐其他分类的 80 唤醒词)
  3. 合并:同 wake_word 用 scene_data 覆盖(用户确认过的优先)
  4. 注入到 templates/help_center.html,输出 卡路里_HELP_<TS>.html
  5. ADR-0001 镜像到 <skill_dir>/卡路里.html

用法:
    python scripts/render_help_center.py              # 默认:triggers + scene_data 合并
    python scripts/render_help_center.py --dev        # 只读 scene_data(开发期)
    python scripts/render_help_center.py --runtime    # 只读 _triggers.py(运行时,纯净 SoT)
    python scripts/render_help_center.py --output <p> # 显式覆盖输出
    python scripts/render_help_center.py --no-mirror  # 跳过 ADR-0001 根镜像
"""
import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR  = Path(__file__).resolve().parent
SKILL_DIR   = SCRIPT_DIR.parent
TEMPLATE    = SKILL_DIR / 'templates' / 'help_center.html'
SCENE_DIR   = SKILL_DIR / '.scratch' / 'scene_data'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path                          # noqa: E402
from _triggers import CATEGORIES as TRIG_CATEGORIES, TRIGGERS  # noqa: E402


# === 11 分类(新结构,Phase 2 将按此重组) ===
# icon / name / key / subfunction 折叠提示默认开
CATEGORIES_V3 = [
    ('🏠', '主页',       'home'),
    ('🍚', '饮食',       'diet'),
    ('⚖️', '体重',       'weight'),
    ('🏃', '运动',       'exercise'),
    ('💪', '健身计划',   'workout'),
    ('🎯', '目标管理',   'goal'),
    ('🧬', '身体细节',   'body_detail'),
    ('📸', '身材照片',   'body_photo'),
    ('🛠', '基础信息',   'profile'),
    ('📊', '分析',       'analysis'),
    ('🔗', '技能协同',   'cross_skill'),
]

# === 旧 → 新 category 映射(Phase 2 期间双轨运行) ===
# 旧 trigger.category → 新 cat.key
CATEGORY_LEGACY_MAP = {
    '主页':      'home',
    '饮食记录':  'diet',     # 饮食记录 + 食品库 → 饮食
    '食品库':    'diet',
    '体重':      'weight',
    '运动':      'exercise',
    '健身计划':  'workout',
    '分析':      'analysis',
    '综合':      'profile',  # 设营养/查营养/查健康/查卡路里/设置档案/查档案 → 基础信息(临时)
    '复盘':      'analysis', # 复盘 → 分析(临时)
    '身体成分':  'body_detail',
    '围度':      'body_detail',
    '身材照片':  'body_photo',
}

# 旧 category → 新展示名(用于老 trigger 在新模板里的归类)
CATEGORY_LEGACY_NAME = {
    '主页':      '主页',
    '饮食记录':  '饮食',
    '食品库':    '饮食',
    '体重':      '体重',
    '运动':      '运动',
    '健身计划':  '健身计划',
    '分析':      '分析',
    '综合':      '基础信息',
    '复盘':      '分析',
    '身体成分':  '身体细节',
    '围度':      '身体细节',
    '身材照片':  '身材照片',
}

# 旧 category → 默认 subfunction(把旧 trigger 装进"既有用法"子功能组)
SUBFUNC_LEGACY = {
    '主页':      '既有唤醒词',
    '饮食记录':  '既有唤醒词',
    '食品库':    '既有唤醒词',
    '体重':      '既有唤醒词',
    '运动':      '既有唤醒词',
    '健身计划':  '既有唤醒词',
    '分析':      '既有唤醒词',
    '综合':      '既有唤醒词',
    '复盘':      '既有唤醒词',
    '身体成分':  '既有唤醒词',
    '围度':      '既有唤醒词',
    '身材照片':  '既有唤醒词',
}

# 分类 → 子功能显式顺序(2026-08-02 用户拍板:基础信息 = 设置资料 → 看档案 → 改档案)
# 中文字典序不可靠(改<看<设),按此表排序;未列出的子功能按插入序(字典序兜底)
SUBFUNC_ORDER = {
    '基础信息': ['设置资料', '看档案', '改资料'],
    # 目标管理:领域闭环 定 → 看 → 改(2026-08-02 对齐 #8 ③)
    '目标管理': ['定目标', '看目标', '改目标'],
    # 身体细节:记 → 看 → 比 → 删(2026-08-02 · ticket #9)
    '身体细节': ['记身体细节', '看身体细节', '比身体细节', '删身体细节'],
}


def _trig_to_scene(t: dict) -> dict:
    """把旧 TRIGGERS 格式转 v3 scene 格式(去变体,平铺)

    Phase 2 新增:若 trigger 已是新 13 字段 scene 格式(含 output_type / prompt_template),
    直接透传(不再走 legacy 转换),保证 --runtime 模式与 scene_data 等价。
    """
    if 'output_type' in t and 'prompt_template' in t:
        scene = dict(t)
        scene.setdefault('_legacy', False)
        return scene

    legacy_cat = t.get('category', '')
    main = t.get('main_prompt', {}) or {}
    return {
        'key':                 f'legacy_{t.get("wake_word", "")}',
        'name':                t.get('wake_word', ''),
        'wake_word':           t.get('wake_word', ''),
        'category':            CATEGORY_LEGACY_NAME.get(legacy_cat, legacy_cat),
        'subfunction':         SUBFUNC_LEGACY.get(legacy_cat, '既有唤醒词'),
        'output_type':         'result',
        'html_template':       '',
        'data_source':         main.get('cli', '') or '',
        'prompt_template':     main.get('text', ''),
        'user_intent':         t.get('desc', ''),
        'data_fields':         [],
        'depends_on_external': False,
        'order':               0,
        '_legacy':             True,    # 内部标记
    }


def load_scene_data_files() -> list[dict]:
    """读 .scratch/scene_data/*.json(开发期,新 13 字段 schema)"""
    if not SCENE_DIR.exists():
        return []
    scenes = []
    for f in sorted(SCENE_DIR.glob('*.json')):
        if f.name == 'schema.json':
            continue
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            print(f'⚠️ scene_data 文件 {f.name} JSON 解析失败: {e}', file=sys.stderr)
            continue
        items = data if isinstance(data, list) else [data]
        for s in items:
            s['_from'] = f.name
            scenes.append(s)
    return scenes


def load_triggers() -> list[dict]:
    """读 _triggers.py(运行时 SoT)"""
    return [_trig_to_scene(t) for t in TRIGGERS]


def merge_scenes(scene_data: list[dict], triggers: list[dict]) -> list[dict]:
    """合并策略:
       - scene_data 优先(用户确认过的新 schema)
       - triggers 补齐(老 wake_word 全部留下,标记 _legacy)
       - 同 wake_word: scene_data 覆盖 triggers
    """
    by_wake = {}
    # 先放 triggers(老)
    for t in triggers:
        by_wake[t['wake_word']] = t
    # 再覆盖 scene_data(新)
    for s in scene_data:
        s['_legacy'] = False
        by_wake[s['wake_word']] = s
    return list(by_wake.values())


def build_data(mode: str = 'merged') -> dict:
    """组装速查台数据契约
    Args:
        mode: 'dev' 只读 scene_data;'runtime' 只读 _triggers;'merged' 两者合并
    """
    scene_data = load_scene_data_files() if mode in ('dev', 'merged') else []
    triggers   = load_triggers()           if mode in ('runtime', 'merged') else []

    if mode == 'dev':
        scenes = scene_data
        source = 'dev(scene_data)'
    elif mode == 'runtime':
        scenes = triggers
        source = 'runtime(_triggers.py)'
    else:
        scenes = merge_scenes(scene_data, triggers)
        source = 'merged(scene_data + _triggers.py)'

    # 按 (category, subfunction, order) 排序
    # subfunction 用显式顺序表(SUBFUNC_ORDER)替代中文字典序(2026-08-02)
    def _sub_key(s):
        order_list = SUBFUNC_ORDER.get(s.get('category', ''), [])
        sub = s.get('subfunction', '')
        if sub in order_list:
            return (order_list.index(sub), sub)
        return (len(order_list), sub)  # 未配置的子功能排在表后,字典序兜底

    scenes.sort(key=lambda s: (
        s.get('category', '~'),
        *_sub_key(s),
        s.get('order', 9999),
        s.get('name', ''),
    ))

    by_category: dict[str, int] = {}
    for s in scenes:
        by_category[s.get('category', '?')] = by_category.get(s.get('category', '?'), 0) + 1

    return {
        'status': 'ok',
        'meta':   {
            'source':      source,
            'mode':        mode,
            'rendered_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'scene_data_count':  len(scene_data),
            'triggers_count':    len(triggers),
        },
        'data': {
            'summary': {
                'total_categories': len(by_category),
                'total_scenes':     len(scenes),
                'total_prompts':    len(scenes),   # 1 prompt / scene(无变体)
                'by_category':      by_category,
            },
            'categories': [{'icon': ic, 'name': nm, 'key': ky} for ic, nm, ky in CATEGORIES_V3],
            'scenes':     scenes,
        },
        'message': f'已加载 {len(scenes)} 场景 / {len(by_category)} 分类 · 数据源:{source}',
    }


def render_html(data: dict) -> str:
    template = TEMPLATE.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError('模板缺少唯一占位符 <!--INJECT-DATA-->')

    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    inject  = f'<script>window.__DATA__ = {payload};</script>'
    return template.replace('<!--INJECT-DATA-->', inject, 1)


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
    p = argparse.ArgumentParser(description='渲染卡路里唤醒词速查台 HTML (v3.0)')
    g = p.add_mutually_exclusive_group()
    g.add_argument('--dev',     action='store_true', help='只读 .scratch/scene_data/*.json')
    g.add_argument('--runtime', action='store_true', help='只读 _triggers.py(纯净 SoT)')
    p.add_argument('--output',   help='输出文件路径(默认走 html_path 新规范)')
    p.add_argument('--no-mirror', action='store_true', help='跳过 ADR-0001 根镜像')
    args = p.parse_args()

    if args.dev:
        mode = 'dev'
    elif args.runtime:
        mode = 'runtime'
    else:
        mode = 'merged'

    try:
        data  = build_data(mode=mode)
        html  = render_html(data)
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

    sm = data['data']['summary']
    print(f'✅ {out_path}')
    print(f'   模式: {mode} · {sm["total_scenes"]} 场景 / {sm["total_categories"]} 分类')
    print(f'   数据源: {data["meta"]["source"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
