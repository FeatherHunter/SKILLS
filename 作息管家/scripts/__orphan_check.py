"""孤儿审计：查 schedule_plans 里所有飞书 event_id，找出没人引用的孤儿。

用途：清理飞书孤儿事件前的安全审计。
  - 找出"飞书侧存在 + 本地没人引用"的 feishu_event_id
  - 用户可放心在飞书 App / lark-cli 删这些孤儿

设计原理：本地 schedule_plans 是 source of truth，飞书是镜像。
本地 0 引用的飞书 event_id = 孤儿 = 可删。
"""
import sys
import os
os.chdir('scripts')
sys.path.insert(0, 'scripts')

from schedule_db import get_connection


def main():
    conn = get_connection()
    try:
        c = conn.cursor()

        # 1) 所有有 feishu_event_id 的 active 事件
        c.execute('''
            SELECT DISTINCT feishu_event_id
            FROM schedule_plans
            WHERE feishu_event_id IS NOT NULL AND is_active = 1
        ''')
        all_fs = [r[0] for r in c.fetchall()]

        # 2) 每个飞书 event_id 引用次数
        orphans = []  # 引用次数 = 0 的孤儿
        protected = []  # 引用次数 ≥ 1 的
        for fs in all_fs:
            c.execute('''
                SELECT COUNT(*) FROM schedule_plans
                WHERE feishu_event_id = ? AND is_active = 1
            ''', (fs,))
            refs = c.fetchone()[0]
            if refs == 0:
                orphans.append(fs)
            else:
                # 查具体哪些事件引用
                c.execute('''
                    SELECT id, date, time_start, time_end, title
                    FROM schedule_plans
                    WHERE feishu_event_id = ? AND is_active = 1
                ''', (fs,))
                protected.append((fs, refs, c.fetchall()))
    finally:
        conn.close()

    print("=" * 80)
    print(f"📊 飞书侧总 event_id 数: {len(all_fs)}")
    print(f"  受保护（有本地引用）: {len(protected)}")
    print(f"  孤儿（无本地引用）: {len(orphans)}")
    print("=" * 80)

    if protected:
        print(f"\n🛡️ 受保护飞书 event_id ({len(protected)} 个 — 删飞书会破坏本地同步)")
        print("-" * 80)
        for fs, refs, rows in protected:
            print(f"  {fs} (本地 {refs} 条引用)")
            for r in rows:
                print(f"    id={r[0]} {r[1]} {r[2]}-{r[3]} '{r[4]}'")

    if orphans:
        print(f"\n🦅 孤儿飞书 event_id ({len(orphans)} 个 — 可放心删飞书)")
        print("-" * 80)
        for fs in orphans:
            clean_id = fs.rstrip("_0") if fs.endswith("_0") else fs
            print(f"  lark-cli calendar +delete --event_id {clean_id}")
            print(f"    完整 event_id: {fs}")
            print()

    if not orphans and not protected:
        print("\n✅ 无飞书事件需要审计")


if __name__ == "__main__":
    main()
