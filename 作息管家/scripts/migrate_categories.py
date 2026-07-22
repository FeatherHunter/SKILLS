#!/usr/bin/env python3
"""
作息管家 - 历史分类归并脚本 (一次性诊断/迁移工具)

默认 dry-run:只打印报告,不修改数据库。
真正执行:python migrate_categories.py --apply

注意:
- 不改 schema,只 UPDATE category 字段
- 用户明确说"不需要修正历史"时,只跑 dry-run 做健康检查,不要 --apply
- 真跑前必须确认已有 .bak 备份
"""
import sqlite3
import sys
from pathlib import Path

# scripts/ 位于 SKILLS/作息管家/scripts,DB 位于 StudyNotes/.db/schedule_data.db
SKILL_DIR = Path(__file__).resolve().parent.parent
STUDYNOTES_DIR = SKILL_DIR.parent.parent
DB_PATH = STUDYNOTES_DIR / ".db" / "schedule_data.db"

# 旧分类 → 新分类 的映射表
MIGRATION_MAP = {
    # 维持
    "睡眠": "维持.睡眠",
    "午睡": "维持.睡眠",
    "洗漱": "维持.洗漱",
    "起居": "维持.洗漱",
    "起床/洗漱": "维持.洗漱",
    "个人护理": "维持.洗漱",
    "餐饮": "维持.用餐",
    "用餐": "维持.用餐",
    "饮食": "维持.用餐",
    "饮食记录": "维持.用餐",
    "做饭": "维持.做饭",
    "烹饪": "维持.做饭",
    "通勤": "维持.通勤",
    "交通": "维持.通勤",
    "外出": "维持.通勤",
    "采购": "维持.采购",
    "购物": "维持.采购",
    "买菜": "维持.采购",
    "医疗": "维持.就医",
    "就医": "维持.就医",

    # 健康
    "健康": "健康.保健",
    "健康管理": "健康.保健",
    "运动": "健康.运动",
    "运动准备": "健康.运动",
    "健身": "健康.健身",
    "健康·健身": "健康.健身",
    "修行": "健康.修行",
    "修炼": "健康.修行",
    "精神成长": "健康.修行",
    "健康·修行": "健康.修行",
    "运动/修行": "健康.修行",

    # 工作 / AI 调优
    "工作": "工作.AI调优",
    "工作·AI 配置": "工作.AI调优",
    "工作·技能排查": "工作.AI调优",
    "工作·Agent 调优": "工作.AI调优",
    "系统": "工作.AI调优",
    "系统配置": "工作.AI调优",
    "系统管理": "工作.AI调优",
    "技术配置": "工作.AI调优",
    "技术讨论": "工作.AI调优",
    "技术问题": "工作.AI调优",
    "技术调试": "工作.AI调优",
    "技术研究": "工作.AI调优",
    "技术探索": "工作.AI调优",
    "技术优化": "工作.AI调优",
    "技术": "工作.AI调优",
    "技能开发": "工作.AI调优",
    "技能调试": "工作.AI调优",
    "技能设计": "工作.AI调优",
    "卡路里": "工作.AI调优",
    "录入": "工作.AI调优",
    "测试": "工作.AI调优",
    "复盘": "工作.AI调优",
    "计划": "工作.AI调优",
    "准备": "工作.AI调优",

    # 学习/创作
    "学习": "学习.研究",
    "技术学习": "学习.技术",
    "创作": "创作.文字",

    # 投入
    "社交": "投入.社交",
    "社交/饮食": "投入.社交",
    "亲密": "投入.伴侣",
    "宠物": "投入.宠物",
    "在线活动": "投入.AI",

    # 调整
    "休息": "调整.休息",
    "休闲": "调整.休息",
    "休息/娱乐": "调整.休息",
    "个人事务/休息": "调整.休息",
    "娱乐": "调整.游戏",
    "混合": "调整.过渡",
    "自由": "调整.过渡",

    # 日常
    "日常": "日常.杂事",
    "生活": "日常.杂事",
    "生活事务": "日常.杂事",
    "生活管理": "日常.杂事",
    "事务": "日常.杂事",
    "其他": "日常.杂事",
    "推测": "日常.杂事",
    "未知": "日常.杂事",
    "个人": "日常.杂事",
    "个人事务": "日常.杂事",
    "个人事务/汽车": "日常.杂事",
    "居家/个人事务": "日常.杂事",
    "办事": "日常.代办",
    "心愿": "日常.代办",
    "记账": "日常.代办",
    "法律事务": "日常.行政",
    "劳动维权": "日常.行政",
    "整理": "日常.收拾",
    "家务": "日常.收拾",
    "居家": "日常.收拾",
    "居家管理": "日常.收拾",
    "居家整理": "日常.收拾",
    "居家清洁": "日常.收拾",
    "居家维修": "日常.收拾",
}

TABLES = ["schedule_records", "daily_summary", "schedule_plans"]


def category_counts(cur, table: str):
    cur.execute(f"SELECT category, COUNT(*) FROM {table} WHERE category IS NOT NULL GROUP BY category ORDER BY COUNT(*) DESC")
    return cur.fetchall()


def migrate(dry_run: bool = True):
    if not DB_PATH.exists():
        print(f"✗ DB not found: {DB_PATH}")
        return 1

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    print(f"DB: {DB_PATH}")
    print(f"MODE: {'DRY-RUN (不修改)' if dry_run else 'APPLY (会 UPDATE)'}")

    total_rows_to_update = 0
    total_updated = 0
    global_unmapped = {}

    for table in TABLES:
        rows = category_counts(cur, table)
        cats = [c for c, _ in rows]
        mapped = [(c, n, MIGRATION_MAP[c]) for c, n in rows if c in MIGRATION_MAP]
        unmapped = [(c, n) for c, n in rows if c not in MIGRATION_MAP]

        rows_to_update = sum(n for _, n, _ in mapped)
        total_rows_to_update += rows_to_update

        print(f"\n=== {table} ===")
        print(f"  分类数: {len(cats)}")
        print(f"  已映射分类: {len(mapped)} / 行数: {rows_to_update}")
        print(f"  未映射分类: {len(unmapped)}")

        if unmapped:
            print("  ⚠️ 未映射:")
            for c, n in unmapped:
                print(f"    - {c}: {n}")
                global_unmapped[f"{table}:{c}"] = n

        if not dry_run:
            updated_count = 0
            for old, new in MIGRATION_MAP.items():
                cur.execute(f"UPDATE {table} SET category=? WHERE category=?", (new, old))
                updated_count += cur.rowcount
            con.commit()
            total_updated += updated_count
            print(f"  ✓ 实际更新: {updated_count} 行")

    print("\n=== 汇总 ===")
    print(f"  将更新行数: {total_rows_to_update}")
    print(f"  未映射项数: {len(global_unmapped)}")
    if not dry_run:
        print(f"  实际更新行数: {total_updated}")
    else:
        print("  说明: 当前是 dry-run,没有修改数据库。")
        print("  如需真正迁移: python migrate_categories.py --apply")

    con.close()
    return 0


if __name__ == "__main__":
    dry_run = "--apply" not in sys.argv
    raise SystemExit(migrate(dry_run=dry_run))
