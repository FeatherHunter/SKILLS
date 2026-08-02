#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_crud_view.py — 通用状态查看 HTML 渲染器(报告型)

对应 SKILL.md 唤醒词(2 个):
  - 查档案   → 显示 user_profile 字段(含活动量/系数/TDEE)
  - 查定时复盘 → 显示 mavis cron 任务配置
对应模板: templates/crud_view.html

调试支持(2026-08-02 用户拍板):
  --chain <文本>   AI 思考链注入(meta.chain,不进 UI;「复制日志」按钮可带出)
  UI 隐藏原始数据/数据来源(用户视图干净);「复制日志」含 原始数据/来源/时间/思考链
"""
import argparse, json, sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'crud_view.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path, html_scene_path  # noqa


def _load_data(input_path):
    raw = json.loads(Path(input_path).read_text(encoding='utf-8'))
    if raw.get('status') != 'ok':
        raise ValueError('数据状态非 ok')
    return raw


def render_html(data):
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError('模板缺少唯一占位符')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    return template.replace('<!--INJECT-DATA-->', f'<script>window.__DATA__ = {payload};</script>', 1)


def build_data(entity_type):
    '''从 DB 真实查询 entity_type 状态(无需 mock)'''
    from db import find_db_path
    import sqlite3
    db_path = find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if entity_type == 'profile':
        # 真实查 user_profile + weight_log 最新一条
        cur.execute("SELECT * FROM user_profile ORDER BY id DESC LIMIT 1")
        prof = cur.fetchone()
        if not prof:
            return None
        cur.execute("SELECT date, time, weight_kg, bmi FROM weight_log ORDER BY date DESC, time DESC LIMIT 1")
        w = cur.fetchone()
        prof_d = dict(prof)
        weight_d = dict(w) if w else {}
        # BMR + TDEE（activity 系数读 user_profile.activity_level · ticket #8）
        age = prof['age'] or 30
        h = prof['height_cm'] or 175
        w_kg = weight_d.get('weight_kg', 70)
        gender = prof['gender'] or 'male'
        activity_level = prof['activity_level'] or 'moderate'
        # Mifflin-St Jeor
        bmr = round(10 * w_kg + 6.25 * h - 5 * age + (5 if gender == 'male' else -161), 0)
        from analysis._utils import get_activity_factor, ACTIVITY_LEVEL_LABELS
        activity_factor = get_activity_factor(activity_level)
        activity_label = ACTIVITY_LEVEL_LABELS.get(activity_level, activity_level)
        tdee = round(bmr * activity_factor, 0)
        bmi = weight_d.get('bmi')
        height_str = f'{h:g} cm' if h else '—'
        bmi_str = f'{bmi} (正常)' if bmi and 18.5 <= bmi <= 24 else f'{bmi} (超重)' if bmi and bmi > 24 else '—' if bmi else '—'
        weight_str = f"{w_kg} kg ({weight_d.get('date')} {weight_d.get('time', '')[:5]})" if w_kg else '—'

        return {
            'status': 'ok',
            'data': {
                'entity': {
                    'type': '用户档案 + 体重',
                    'title': '👤 查档案',
                    'subtitle': '我的档案 + 最新体重',
                    'section_title': '档案 + 当前体重'
                },
                'kpis': [
                    {'label':'年龄', 'value':str(age), 'extra':prof['gender'] or '—'},
                    {'label':'身高', 'value':height_str, 'extra':'BMR/TDEE 计算'},
                    {'label':'当前体重', 'value':f"{w_kg} kg" if w_kg else '—', 'extra':weight_d.get('date', '—') if w else '无记录'},
                    {'label':'当前 BMI', 'value':f'{bmi}' if bmi else '—', 'extra':bmi_str}
                ],
                'fields': [
                    {'key':'年龄(AGE)', 'value':str(age)},
                    {'key':'性别(GENDER)', 'value':prof['gender'] or '—'},
                    {'key':'身高(HEIGHT_CM)', 'value':height_str},
                    {'key':'活动量(ACTIVITY_LEVEL)', 'value':f'{activity_label} ({activity_level})'},
                    {'key':'活动系数', 'value':f'× {activity_factor}（{activity_label}档）'},
                    {'key':'最近体重', 'value':weight_str},
                    {'key':'最近 BMI', 'value':bmi_str},
                    {'key':'BMR(Mifflin-St Jeor)', 'value':f'{bmr:,} 卡/天'},
                    {'key':'TDEE(BMR × 活动系数)', 'value':f'{tdee:,} 卡/天'},
                    {'key':'档案创建', 'value':prof['created_at'] or '—'},
                    {'key':'档案更新', 'value':prof['updated_at'] or '—'},
                    {'key':'备注', 'value':prof['note'] or '(空)'}
                ],
                'raw': {**prof_d, 'weight': weight_d} if weight_d else prof_d,
                'meta': {
                    'fetched_at': datetime.now().isoformat(timespec='seconds')[:16].replace('T', ' '),
                    'source': 'user_profile + weight_log (latest)',
                    'wake_word': '查档案',   # 自描述:渲染器知道自己在服务哪个唤醒词(2026-08-02)
                }
            },
            'message': '已生成查档案 报告'
        }
    # 后续可加 cron
    return None






def _quote_arg(a: str) -> str:
    """参数加引号(含空格/引号/特殊字符时),保证 render_cmd 可复制直接执行(2026-08-02)"""
    if not a:
        return '""'
    if any(ch in a for ch in (' ', '"', "'", '\\', '&', '|', '>', '<', '(', ')')):
        return '"' + a.replace('"', '\\"') + '"'
    return a


def _chain_valid(chain):
    """思考链有效性校验(2026-08-02 用户拍板):非空 + 含步骤特征 + 拒绝偷懒占位"""
    chain = (chain or '').strip()
    if len(chain) < 8:
        return False
    if not any(m in chain for m in ('→', '->', '1.', '1、', '2.', '第一步')):
        return False
    if chain.lower() in ('x', 'xx', 'xxx', '思考链', 'chain', '无', 'none'):
        return False
    return True


def main():
    p = argparse.ArgumentParser(description='渲染状态查看 HTML(查档案/查定时复盘)')
    p.add_argument('--entity', choices=['profile','cron'], help='DB 实体类型(与 --mock 二选一)')
    p.add_argument('--mock', help='mock JSON(与 --entity 二选一)')
    p.add_argument('--chain', help='AI 思考链(必填·强制规则:未传=AI 未按 SKILL.md 流程执行 · 2026-08-02)')
    p.add_argument('--wake-word', help='唤醒词(覆盖渲染器自推断,供「复制日志」带出)')
    p.add_argument('--output')
    args = p.parse_args()

    # ⭐ 思考链强制校验(2026-08-02 用户拍板):live 模式必传 + 有效性校验,防止 AI 偷懒
    if not args.mock and not _chain_valid(args.chain):
        print('❌ --chain 缺失或无效:AI 思考链是排障日志的必要字段(强制规则)', file=sys.stderr)
        print('   未传 = AI 未按 SKILL.md 流程执行,行为不可控。', file=sys.stderr)
        print('   请传入你的实际处理步骤,例如:', file=sys.stderr)
        print("     --chain \"1.识别唤醒词→2.调CLI读DB→3.计算BMI/BMR/TDEE(系数1.55)\"", file=sys.stderr)
        return 2

    try:
        if args.mock:
            data = _load_data(args.mock)
        elif args.entity:
            data = build_data(args.entity)
            if not data:
                print(f'❌ DB 中没有 {args.entity} 记录', file=sys.stderr)
                return 1
        else:
            print('❌ 需要 --mock 或 --entity', file=sys.stderr)
            return 1
        # 调试元数据注入(不进 UI,复制日志可带出;2026-08-02 自描述改进)
        meta = data['data']['meta']
        if args.chain:
            meta['chain'] = args.chain
        if args.wake_word:   # 显式传参覆盖渲染器自推断
            meta['wake_word'] = args.wake_word
        # 完整可复现命令:python scripts/render_crud_view.py <args>(含脚本名,2026-08-02)
        argv = sys.argv[1:]
        if '--output' in argv:
            i = argv.index('--output')
            argv = argv[:i] + argv[i + 2:] if i + 1 < len(argv) else argv[:i]
        # 含空格/特殊字符的参数加引号(2026-08-02 修复:render_cmd 必须可复制直接执行)
        meta['render_cmd'] = f"python scripts/{Path(__file__).name} " + ' '.join(_quote_arg(a) for a in argv)
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1
    out_path = Path(args.output) if args.output else html_scene_path(SKILL_DIR, '查档案', 'result')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    d = data['data']
    print(f'✅ {out_path}')
    print(f'   实体: {d["entity"]["type"]} | {d["entity"]["title"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
