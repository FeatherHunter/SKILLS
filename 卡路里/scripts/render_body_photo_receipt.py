#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_body_photo_receipt.py — 身材照片回执 HTML 渲染器(回执型 · ticket #10)

对应 SKILL.md 唤醒词(6 个):
  - 记身材照       → --live-add(存一张 / 含备注 / 批量)
  - 删身材照       → --live-delete
  - 改照片标签     → --live-tag-set(覆盖整套)
  - 加照片标签     → --live-tag-add(追加 + 判重)
  - 删照片标签     → --live-tag-remove(移除,至少保留 1 个)
对应模板: templates/body_photo_receipt.html

设计(对齐 #8 经验 R1-R8):
  - live 写库 + 回执一体(同 render_crud_receipt.py --live-profile-set)
  - --chain 强制(R3 思考链,未传报错 exit2)
  - 回执含内嵌缩略图预览(base64,飞书友好)
  - 批量存逐张明细(缩略图 + 标签 + 状态 成功/跳过/失败+原因)+ 汇总条数
  - 距上次同标签拍照间隔(规律拍照 = 身材追踪第一性原理)
  - 标签操作:改前/改后对比 + 完整标签列表 + 无变化明示(C9)
  - 复制数据(用户口径)+ 复制日志(排障口径,R2)

用法:
    python scripts/render_body_photo_receipt.py --live-add <照片路径> --tag 正面 --chain "1.解析→2.写库→3.回执"
    python scripts/render_body_photo_receipt.py --live-add <p1> <p2> --tag 正面 --note "早起" --chain "1.解析→2.写库→3.回执"
    python scripts/render_body_photo_receipt.py --live-delete --id 3 --chain "1.列候选→2.确认→3.删除→4.回执"
    python scripts/render_body_photo_receipt.py --live-tag-set --id 3 --tag-list "正面,侧面" --chain "1.解析→2.写库→3.回执"
    python scripts/render_body_photo_receipt.py --live-tag-add --id 3 --tag 背部 --chain "1.解析→2.写库→3.回执"
    python scripts/render_body_photo_receipt.py --live-tag-remove --id 3 --tag 正面 --chain "1.解析→2.写库→3.回执"
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'body_photo_receipt.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_scene_path  # noqa
from render_crud_view import _chain_valid, _quote_arg  # 校验+引号单一来源(2026-08-02)


# ===== 工具(单一来源 import body_photo_tracker,不复制实现) =====
def _tracker():
    import body_photo_tracker as bpt
    return bpt


def embed_photo_base64(photo, max_dim=500):
    """缩略图 base64(复用 viewer 实现,图片不存在时静默降级)"""
    import render_body_photo_gif_planner as gp
    try:
        photos_dir = _tracker().get_photos_dir()
        p = gp.embed_photo_as_base64(photo, photos_dir, max_dim=max_dim)
        return p
    except Exception:
        return dict(photo)


# ===== 各 action 的 live 构建器 =====

def build_live_add(photo_paths, tag, note=''):
    """存照片(一张/含备注/批量):复制文件 + 写库 + 组装回执

    呈现数据:照片缩略图预览 / 日期 / 标签 / 距上次同标签拍照间隔;
    批量时逐张明细(缩略图+标签+状态 成功/跳过/失败+原因)+ 汇总条数。
    """
    bpt = _tracker()
    scene = '批量存照片' if len(photo_paths) > 1 else ('存照片（含备注）' if note else '存一张照片')

    items = []
    ok_count = 0
    for p in photo_paths:
        src = Path(p)
        if not src.exists():
            items.append({'status': '失败', 'reason': f'文件不存在: {p}', 'photo_path': p})
            continue
        try:
            added = bpt.add_photos([str(src)], tag, note)
            photo_id = added[0][0]
            row = bpt.get_photo_row(photo_id)
            row['status'] = '成功'
            row['reason'] = ''
            row = embed_photo_base64(row)
            items.append(row)
            ok_count += 1
        except Exception as e:
            items.append({'status': '失败', 'reason': str(e), 'photo_path': p})

    # 距上次同标签拍照间隔(取第一个标签)
    distance = None
    if ok_count:
        tags = bpt.parse_tags(tag)
        if tags:
            from datetime import date as _date
            d = bpt.days_since_tag_photo(tags[0], _date.today().isoformat())
            if d is not None:
                distance = {'tag': tags[0], 'days': d}

    summary = f"已存入 {ok_count} 张身材照"
    if distance:
        summary += f";距上次「{distance['tag']}」照已隔 {distance['days']} 天"
    if len(items) > ok_count:
        summary += f",{len(items) - ok_count} 张未存入"

    return {
        'status': 'ok',
        'data': {
            'scene': scene, 'action': 'add', 'op': 'create',
            'record_id': items[0]['id'] if ok_count and 'id' in items[0] else None,
            'summary': summary,
            'items': items, 'tag_diff': None, 'distance': distance,
            'no_change': False,
            'meta': {
                'action_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'entity_type': scene, 'wake_word': '记身材照',
                'source': 'body_photos (写库回执)',
            },
        },
        'message': f'已生成{scene} 回执',
    }


def build_live_delete(photo_id):
    """删身材照:删除前快照(含缩略图)→ 物理删 + 回执"""
    bpt = _tracker()
    snapshot = bpt.get_photo_row(photo_id)
    if not snapshot:
        raise ValueError(f"照片 #{photo_id} 不存在")
    snapshot = embed_photo_base64(snapshot, max_dim=800)
    bpt.delete_photo(photo_id)
    summary = (f"已删除身材照 #{photo_id}({snapshot['date']} · "
               f"{'、'.join(snapshot['tag_list']) or '无标签'})"
               f"{(' · ' + snapshot['note']) if snapshot.get('note') else ''}")
    return {
        'status': 'ok',
        'data': {
            'scene': '删身材照', 'action': 'delete', 'op': 'delete',
            'record_id': photo_id,
            'summary': summary,
            'items': [dict(snapshot, status='已删除', reason='')],
            'tag_diff': None, 'distance': None,
            'no_change': False,
            'meta': {
                'action_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'entity_type': '删身材照', 'wake_word': '删身材照',
                'source': 'body_photos (删除快照)',
            },
        },
        'message': f'已生成删身材照 回执',
    }


def _tag_op_data(photo_id, before, after, scene, wake_word, summary, no_change):
    return {
        'status': 'ok',
        'data': {
            'scene': scene, 'action': scene, 'op': 'update',
            'record_id': photo_id,
            'summary': summary,
            'items': [],
            'tag_diff': {'before': before, 'after': after},
            'distance': None,
            'no_change': no_change,
            'meta': {
                'action_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'entity_type': scene, 'wake_word': wake_word,
                'source': 'body_photos (标签更新)',
            },
        },
        'message': f'已生成{scene} 回执',
    }


def build_live_tag_set(photo_id, tag_list):
    """改照片标签:覆盖整套。改前/改后 + 完整标签列表"""
    bpt = _tracker()
    photo = bpt.get_photo_row(photo_id)
    if not photo:
        raise ValueError(f"照片 #{photo_id} 不存在")
    before = photo['tag_list']
    tags = bpt.validate_tags(bpt.parse_tags(tag_list))
    bpt.update_tag(photo_id, bpt.serialize_tags(tags))
    after = bpt.parse_tags(bpt.serialize_tags(tags))
    no_change = before == after
    summary = (f"照片 #{photo_id} 标签已改为:{'、'.join(after)}"
               + (";以上标签与原来一致,未产生实际变化" if no_change else ""))
    return _tag_op_data(photo_id, before, after, '改照片标签', '改照片标签', summary, no_change)


def build_live_tag_add(photo_id, tag):
    """加照片标签:追加(判重)。新增后完整标签列表 + 判重提示"""
    bpt = _tracker()
    photo = bpt.get_photo_row(photo_id)
    if not photo:
        raise ValueError(f"照片 #{photo_id} 不存在")
    before = photo['tag_list']
    tags = bpt.validate_tags(bpt.parse_tags(tag))
    if len(tags) != 1:
        raise ValueError(f"加标签一次只加 1 个,收到 {len(tags)} 个: {tags!r}")
    new_tag = tags[0]
    if new_tag in before:
        return _tag_op_data(photo_id, before, before, '加照片标签', '加照片标签',
                            f"⚠ 标签「{new_tag}」已存在(当前标签:{'、'.join(before)}),未做修改", True)
    bpt.tag_add(photo_id, new_tag)
    after = bpt.get_photo_row(photo_id)['tag_list']
    summary = f"已为照片 #{photo_id} 追加标签「{new_tag}」,当前标签:{'、'.join(after)}"
    return _tag_op_data(photo_id, before, after, '加照片标签', '加照片标签', summary, False)


def build_live_tag_remove(photo_id, tag):
    """删照片标签:移除(至少保留 1 个)。删除前/删除后列表"""
    bpt = _tracker()
    photo = bpt.get_photo_row(photo_id)
    if not photo:
        raise ValueError(f"照片 #{photo_id} 不存在")
    before = photo['tag_list']
    tags = bpt.parse_tags(tag)
    if len(tags) != 1:
        raise ValueError(f"删标签一次只删 1 个,收到 {len(tags)} 个: {tags!r}")
    rm_tag = tags[0]
    if rm_tag not in before:
        return _tag_op_data(photo_id, before, before, '删照片标签', '删照片标签',
                            f"⚠ 标签「{rm_tag}」不存在(当前标签:{'、'.join(before)}),未做修改", True)
    if len(before) <= 1:
        raise ValueError(f"照片 #{photo_id} 只有「{rm_tag}」1 个标签,每张照片至少保留 1 个标签(删空语义)")
    bpt.tag_remove(photo_id, rm_tag)
    after = bpt.get_photo_row(photo_id)['tag_list']
    summary = f"已从照片 #{photo_id} 移除标签「{rm_tag}」,剩余标签:{'、'.join(after)}"
    return _tag_op_data(photo_id, before, after, '删照片标签', '删照片标签', summary, False)


# ===== 渲染 =====

def render_html(data):
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError('模板缺少唯一占位符')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    return template.replace('<!--INJECT-DATA-->', f'<script>window.__DATA__ = {payload};</script>', 1)


def emit_send_protocol(output_path):
    print(f"⚠️ ACTION=SEND_TO_USER | HTML={output_path.absolute()}")


def main():
    p = argparse.ArgumentParser(description='渲染身材照片回执 HTML(写库 + 回执一体)')
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--mock', help='mock JSON(测试)')
    g.add_argument('--live-add', nargs='+', metavar='PATH', help='存照片:照片路径(可多个=批量)')
    g.add_argument('--live-delete', action='store_true', help='删身材照(--id)')
    g.add_argument('--live-tag-set', action='store_true', help='改照片标签(覆盖整套,--id --tag-list)')
    g.add_argument('--live-tag-add', action='store_true', help='加照片标签(追加,--id --tag)')
    g.add_argument('--live-tag-remove', action='store_true', help='删照片标签(移除,--id --tag)')
    p.add_argument('--id', type=int, help='照片 ID(delete/tag 类)')
    p.add_argument('--tag', help='标签(单个,add/tag-add/tag-remove 用;add 支持逗号多标签)')
    p.add_argument('--tag-list', help='整套标签列表(改照片标签,逗号分隔)')
    p.add_argument('--note', default='', help='备注(add 用)')
    p.add_argument('--chain', help='AI 思考链(必填·强制规则:未传=AI 未按 SKILL.md 流程执行 · 2026-08-02)')
    p.add_argument('--output')
    args = p.parse_args()

    # ⭐ 思考链强制校验(R3 · 2026-08-02 用户拍板)
    if not args.mock and not _chain_valid(args.chain):
        print('❌ --chain 缺失或无效:AI 思考链是排障日志的必要字段(强制规则)', file=sys.stderr)
        print('   未传 = AI 未按 SKILL.md 流程执行,行为不可控。', file=sys.stderr)
        print('   请传入你的实际处理步骤,例如:', file=sys.stderr)
        print('     --chain "1.解析用户意图→2.调用CLI写库→3.生成回执"', file=sys.stderr)
        return 2

    # 参数完整性校验
    if args.live_delete and not args.id:
        print('❌ --live-delete 需要 --id', file=sys.stderr)
        return 1
    if args.live_tag_set and (not args.id or not args.tag_list):
        print('❌ --live-tag-set 需要 --id 与 --tag-list', file=sys.stderr)
        return 1
    if (args.live_tag_add or args.live_tag_remove) and (not args.id or not args.tag):
        print('❌ --live-tag-add/--live-tag-remove 需要 --id 与 --tag', file=sys.stderr)
        return 1

    try:
        if args.mock:
            data = json.loads(Path(args.mock).read_text(encoding='utf-8'))
            cmd_name = '身材照片回执'
        elif args.live_add:
            data = build_live_add(args.live_add, args.tag, args.note)
            cmd_name = data['data']['scene']
        elif args.live_delete:
            data = build_live_delete(args.id)
            cmd_name = '删身材照'
        elif args.live_tag_set:
            data = build_live_tag_set(args.id, args.tag_list)
            cmd_name = '改照片标签'
        elif args.live_tag_add:
            data = build_live_tag_add(args.id, args.tag)
            cmd_name = '加照片标签'
        else:
            data = build_live_tag_remove(args.id, args.tag)
            cmd_name = '删照片标签'

        if not args.mock:
            data['data']['meta']['chain'] = args.chain.strip()
            data['data']['meta']['wake_word'] = cmd_name
            argv = sys.argv[1:]
            if '--output' in argv:
                i = argv.index('--output')
                argv = argv[:i] + argv[i + 2:] if i + 1 < len(argv) else argv[:i]
            data['data']['meta']['render_cmd'] = (
                f"python scripts/{Path(__file__).name} " + ' '.join(_quote_arg(a) for a in argv))
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    out_path = Path(args.output) if args.output else html_scene_path(SKILL_DIR, cmd_name, 'receipt')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    print(f'✅ {out_path}')
    print(f'   操作: {data["data"]["op"]} | 场景: {cmd_name}')
    emit_send_protocol(out_path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
