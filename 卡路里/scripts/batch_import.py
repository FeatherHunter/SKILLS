#!/usr/bin/env python3
"""批量导入食品库工具 - batch_import.py

================================================================================
数据治理原则（与 Mavis 用户共识 · 2026-06-30）
================================================================================
- source 字段如实记录"这条数据是怎么来的",不是"理想来源"
- AI 不知道就写"未知"或"AI 估算,未查证",不要编造权威来源
- 不维护"推荐来源枚举",完全自由,只要非空
- 重复处理:逐条询问,支持"全部应用此选择"批量模式
================================================================================

子命令:
  import <file> [--dry-run]   批量导入 JSONL(默认询问重复处理)
  validate <file>             只校验不写入
  dedupe                      全库去重检查(只报告)
  export --source X --output F  按条件导出 JSONL

JSONL 字段:
  必填(7):product_name, calories, protein, fat, carbohydrates, sodium, source
  可选(6):brand, saturated_fat, sugar, dietary_fiber, note, is_deprecated

去重判定:product_name + brand 完全相同视为同一条
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

# 数据库查找复用 db.py
sys.path.insert(0, str(Path(__file__).parent))
from db import find_db_path


REQUIRED_FIELDS = ['product_name', 'calories', 'protein', 'fat', 'carbohydrates', 'sodium', 'source']
NUMERIC_FIELDS = ['calories', 'protein', 'fat', 'saturated_fat', 'carbohydrates', 'sugar', 'dietary_fiber', 'sodium']


# ==============================================================================
# 校验
# ==============================================================================

def validate_record(record):
    """校验单条记录,返回 (is_valid, error_msg)"""
    # 1. 必填字段
    for field in REQUIRED_FIELDS:
        if field not in record or record[field] is None:
            return False, f"缺少必填字段: {field}"
        # source 必须是非空字符串（数据治理：必须如实标注,不能空着）
        if field == 'source':
            if not isinstance(record[field], str) or not record[field].strip():
                return False, "source 必须是非空字符串(如实记录数据来源,可以是'未知')"
        # product_name 同样要求非空字符串
        if field == 'product_name':
            if not isinstance(record[field], str) or not record[field].strip():
                return False, "product_name 必须是非空字符串"

    # 2. 数值字段范围
    for field in NUMERIC_FIELDS:
        if field in record and record[field] is not None:
            v = record[field]
            if not isinstance(v, (int, float)):
                return False, f"{field} 必须是数字,当前: {type(v).__name__}"
            if v < 0:
                return False, f"{field} 必须 >= 0,当前: {v}"

    return True, None


# ==============================================================================
# 数据库操作
# ==============================================================================

def get_db_path():
    """获取技能数据库路径"""
    skill_dir = Path(__file__).parent.parent
    return find_db_path(skill_dir)


def connect_db(db_path):
    """连接数据库,返回 row_factory=Row 的连接"""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def check_duplicate(conn, product_name, brand):
    """检查重复,返回 (existing_id, is_deprecated) 或 (None, None)
    只查询 is_deprecated=0 的有效条目(已废弃的不算重复)
    """
    cur = conn.cursor()
    if brand is None or brand == '':
        cur.execute(
            'SELECT id, is_deprecated FROM nutrition_products '
            'WHERE is_deprecated = 0 AND product_name = ? AND (brand IS NULL OR brand = "")',
            (product_name,)
        )
    else:
        cur.execute(
            'SELECT id, is_deprecated FROM nutrition_products '
            'WHERE is_deprecated = 0 AND product_name = ? AND brand = ?',
            (product_name, brand)
        )
    row = cur.fetchone()
    return (row['id'], row['is_deprecated']) if row else (None, None)


def insert_record(conn, record):
    """插入新记录,返回新 id"""
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO nutrition_products (
            product_name, brand, calories, protein, fat, saturated_fat,
            carbohydrates, sugar, dietary_fiber, sodium, source, is_deprecated, note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        record['product_name'].strip(),
        record.get('brand') or None,
        record['calories'],
        record['protein'],
        record['fat'],
        record.get('saturated_fat'),
        record['carbohydrates'],
        record.get('sugar'),
        record.get('dietary_fiber'),
        record['sodium'],
        record['source'].strip(),
        record.get('is_deprecated', 0),
        record.get('note', ''),
    ))
    return cur.lastrowid


def update_record(conn, record, existing_id):
    """覆盖更新已有记录"""
    cur = conn.cursor()
    cur.execute('''
        UPDATE nutrition_products SET
            calories = ?, protein = ?, fat = ?, saturated_fat = ?,
            carbohydrates = ?, sugar = ?, dietary_fiber = ?, sodium = ?,
            source = ?, is_deprecated = ?, note = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (
        record['calories'],
        record['protein'],
        record['fat'],
        record.get('saturated_fat'),
        record['carbohydrates'],
        record.get('sugar'),
        record.get('dietary_fiber'),
        record['sodium'],
        record['source'].strip(),
        record.get('is_deprecated', 0),
        record.get('note', ''),
        existing_id,
    ))


def deprecate_record(conn, existing_id):
    """标记记录为废弃"""
    cur = conn.cursor()
    cur.execute(
        'UPDATE nutrition_products SET is_deprecated = 1, '
        'updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        (existing_id,)
    )


# ==============================================================================
# 重复处理交互
# ==============================================================================

def prompt_duplicate_action(product_name, existing_id, is_deprecated):
    """询问重复处理动作：覆盖/跳过/废弃/全部应用"""
    print(f"\n⚠️  重复: '{product_name}' (已存在 ID={existing_id}, is_deprecated={is_deprecated})")
    print(f"   [o]覆盖  [s]跳过  [d]标废弃  [a]全部应用此选择(再问一次具体动作)")
    while True:
        choice = input("   请输入 (o/s/d/a): ").strip().lower()
        if choice in ('o', 's', 'd', 'a'):
            return choice
        print("   无效输入")


def prompt_apply_all_specific(product_name, existing_id):
    """全部应用模式下,询问具体动作"""
    print(f"\n⚠️  '{product_name}' (ID={existing_id}) - 全部应用模式")
    print(f"   [o]覆盖  [s]跳过  [d]标废弃")
    while True:
        choice = input("   请输入 (o/s/d): ").strip().lower()
        if choice in ('o', 's', 'd'):
            return choice
        print("   无效输入")


# ==============================================================================
# 文件读取
# ==============================================================================

def read_jsonl(file_path):
    """读 JSONL 文件,返回 (records, parse_errors)
    records: [(line_num, record_dict), ...]
    errors: [(line_num, error_msg), ...]"""
    records = []
    errors = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append((line_num, f"JSON 解析失败: {e}"))
                continue
            records.append((line_num, rec))
    return records, errors


# ==============================================================================
# 子命令:import
# ==============================================================================

def cmd_import(args):
    """import 子命令"""
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"❌ 文件不存在: {file_path}")
        return 1

    records, parse_errors = read_jsonl(file_path)

    print(f"📥 批量导入: {file_path}")
    print(f"   总行数: {len(records)} (含 {len(parse_errors)} 行 JSON 解析失败)")
    for ln, err in parse_errors:
        print(f"   ⚠️  第 {ln} 行: {err}")

    # 校验所有记录
    valid_records = []
    for line_num, rec in records:
        ok, err = validate_record(rec)
        if not ok:
            name = rec.get('product_name', '<unknown>')
            print(f"   ❌ 第 {line_num} 行: {name} - {err}")
        else:
            valid_records.append((line_num, rec))

    print(f"   校验通过: {len(valid_records)} 条")

    if args.dry_run:
        print(f"\n🔍 Dry-run 模式,不写入数据库")
        return 0

    if not valid_records:
        print(f"\n✅ 无可导入记录,退出")
        return 0

    # 连接数据库
    db_path = get_db_path()
    conn = connect_db(db_path)

    stats = {'inserted': 0, 'updated': 0, 'skipped': 0, 'deprecated': 0, 'failed': 0}
    failures = []
    apply_all = None  # 'o'/'s'/'d' - 重复处理时统一应用的动作

    try:
        for line_num, rec in valid_records:
            product_name = rec['product_name'].strip()
            brand = rec.get('brand') or None

            try:
                existing_id, is_deprecated = check_duplicate(conn, product_name, brand)

                if existing_id is None:
                    new_id = insert_record(conn, rec)
                    conn.commit()
                    stats['inserted'] += 1
                    print(f"   ✅ 第 {line_num} 行: 新增 '{product_name}' (ID={new_id})")
                else:
                    # 重复,询问
                    if apply_all is not None:
                        choice = apply_all
                    else:
                        choice = prompt_duplicate_action(product_name, existing_id, is_deprecated)
                        if choice == 'a':
                            apply_all = prompt_apply_all_specific(product_name, existing_id)
                            choice = apply_all

                    if choice == 'o':
                        update_record(conn, rec, existing_id)
                        conn.commit()
                        stats['updated'] += 1
                        print(f"   🔄 第 {line_num} 行: 覆盖 ID={existing_id} '{product_name}'")
                    elif choice == 's':
                        stats['skipped'] += 1
                        print(f"   ⏭️  第 {line_num} 行: 跳过 ID={existing_id} '{product_name}'")
                    elif choice == 'd':
                        deprecate_record(conn, existing_id)
                        conn.commit()
                        stats['deprecated'] += 1
                        print(f"   🗑️  第 {line_num} 行: 标废弃 ID={existing_id} '{product_name}'")
            except Exception as e:
                conn.rollback()
                stats['failed'] += 1
                failures.append((line_num, product_name, str(e)))
                print(f"   ❌ 第 {line_num} 行: '{product_name}' - 失败: {e}")
    finally:
        conn.close()

    # 输出汇总
    print(f"\n{'='*60}")
    print(f"📊 导入完成")
    print(f"   ✅ 新增: {stats['inserted']}")
    print(f"   🔄 覆盖: {stats['updated']}")
    print(f"   ⏭️  跳过: {stats['skipped']}")
    print(f"   🗑️  废弃: {stats['deprecated']}")
    print(f"   ❌ 失败: {stats['failed']}")
    if failures:
        print(f"\n❌ 失败明细:")
        for ln, name, err in failures:
            print(f"   第 {ln} 行: {name} - {err}")

    return 0


# ==============================================================================
# 子命令:validate
# ==============================================================================

def cmd_validate(args):
    """validate 子命令:只校验不写"""
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"❌ 文件不存在: {file_path}")
        return 1

    records, parse_errors = read_jsonl(file_path)

    print(f"🔍 校验: {file_path}")
    print(f"   总行数: {len(records)}")
    print(f"   JSON 解析失败: {len(parse_errors)}")

    valid = 0
    for line_num, rec in records:
        ok, err = validate_record(rec)
        if ok:
            valid += 1
        else:
            name = rec.get('product_name', '<unknown>')
            print(f"   ❌ 第 {line_num} 行: {name} - {err}")

    print(f"\n   校验通过: {valid} / {len(records)}")
    return 0 if valid == len(records) else 1


# ==============================================================================
# 子命令:dedupe
# ==============================================================================

def cmd_dedupe(args):
    """dedupe 子命令:全库去重检查(只报告,不修改)"""
    db_path = get_db_path()
    conn = connect_db(db_path)
    cur = conn.cursor()
    cur.execute('''
        SELECT product_name, brand, COUNT(*) as cnt, GROUP_CONCAT(id) as ids
        FROM nutrition_products
        WHERE is_deprecated = 0
        GROUP BY product_name, brand
        HAVING cnt > 1
    ''')
    dups = cur.fetchall()
    conn.close()

    print(f"🔍 全库去重检查 (is_deprecated=0)")
    if not dups:
        print(f"   ✅ 无重复")
        return 0

    print(f"   ⚠️  找到 {len(dups)} 组重复:")
    for row in dups:
        print(f"   - '{row['product_name']}' (brand={row['brand']}): {row['cnt']} 条 → IDs: {row['ids']}")
    return 0


# ==============================================================================
# 子命令:export
# ==============================================================================

def cmd_export(args):
    """export 子命令:导出为 JSONL"""
    db_path = get_db_path()
    conn = connect_db(db_path)
    cur = conn.cursor()

    conditions = ['is_deprecated = 0']
    params = []
    if args.source:
        conditions.append('source = ?')
        params.append(args.source)

    where = ' AND '.join(conditions)
    cur.execute(f'SELECT * FROM nutrition_products WHERE {where} ORDER BY id', params)
    rows = cur.fetchall()
    conn.close()

    output = Path(args.output)
    with open(output, 'w', encoding='utf-8') as f:
        for row in rows:
            rec = {
                'product_name': row['product_name'],
                'brand': row['brand'],
                'calories': row['calories'],
                'protein': row['protein'],
                'fat': row['fat'],
                'saturated_fat': row['saturated_fat'],
                'carbohydrates': row['carbohydrates'],
                'sugar': row['sugar'],
                'dietary_fiber': row['dietary_fiber'],
                'sodium': row['sodium'],
                'source': row['source'],
                'is_deprecated': row['is_deprecated'],
                'note': row['note'],
            }
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')

    print(f"📤 导出 {len(rows)} 条 → {output}")
    return 0


# ==============================================================================
# main
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='食品库批量导入/管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python batch_import.py validate data/p0.jsonl
  python batch_import.py import data/p0.jsonl --dry-run
  python batch_import.py import data/p0.jsonl
  python batch_import.py dedupe
  python batch_import.py export --source "中国食物成分表第6版" --output export.jsonl
        '''
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # import
    imp = subparsers.add_parser('import', help='从 JSONL 导入')
    imp.add_argument('file', help='JSONL 文件路径')
    imp.add_argument('--dry-run', action='store_true', help='只校验不写入')

    # validate
    val = subparsers.add_parser('validate', help='只校验不导入')
    val.add_argument('file', help='JSONL 文件路径')

    # dedupe
    subparsers.add_parser('dedupe', help='全库去重检查')

    # export
    exp = subparsers.add_parser('export', help='导出为 JSONL')
    exp.add_argument('--source', help='按 source 过滤(精确匹配)')
    exp.add_argument('--output', required=True, help='输出文件路径')

    args = parser.parse_args()

    if args.command == 'import':
        return cmd_import(args)
    elif args.command == 'validate':
        return cmd_validate(args)
    elif args.command == 'dedupe':
        return cmd_dedupe(args)
    elif args.command == 'export':
        return cmd_export(args)


if __name__ == '__main__':
    sys.exit(main())