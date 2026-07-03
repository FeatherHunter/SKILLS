"""
migrate_uncategorized.py — 把所有"_未分类"按 note 细分,无 note 回填

策略:
1. 有 note:按关键词规则链匹配 → 细分到具体 L2/L3
2. 无 note:在 note 末尾加 "[原分类:L1]" → 归 "X/_未归类"

【安全】
1. 默认 dry-run 模式
2. 修改前自动导出 CSV 备份(包含 note 变化)
3. 整体事务:任何环节出错自动回滚
4. EXCLUSIVE LOCK:防止并发写入
5. --force 跳过二次确认
6. --rollback 支持回滚

【使用】
python migrate_uncategorized.py            # dry-run
python migrate_uncategorized.py --execute --force
python migrate_uncategorized.py --rollback <backup.csv>
"""

import sys
import sqlite3
import csv
import re
from datetime import datetime
from pathlib import Path

# 复用 db.py
sys.path.insert(0, str(Path(__file__).parent))
from db import _find_db_path, SKILL_DIR, DB_FILENAME, TABLE_NAME, init_db

DB_PATH = _find_db_path(SKILL_DIR, DB_FILENAME)
BACKUP_DIR = Path(__file__).parent.parent / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

# 通用关键词规则链(从老数据 note 中提取)
GENERAL_RULES = [
    # === 餐饮类 ===
    ("note LIKE '%美团%' OR note LIKE '%美团平台%' OR note LIKE '%饿了么%' OR note LIKE '%外卖%'", "餐饮/外卖"),
    ("note LIKE '%馄饨%' OR note LIKE '%面馆%' OR note LIKE '%餐厅%' OR note LIKE '%饭店%' OR note LIKE '%食堂%' OR note LIKE '%麦当劳%' OR note LIKE '%肯德基%' OR note LIKE '%海底捞%' OR note LIKE '%必胜客%' OR note LIKE '%飞琼阁%' OR note LIKE '%双喜面馆%' OR note LIKE '%高嗲嗲%' OR note LIKE '%安年庆%' OR note LIKE '%天元中路店%' OR note LIKE '%好的便利店%' OR note LIKE '%无人售货%' OR note LIKE '%智咖时代%'", "餐饮/堂食"),
    ("note LIKE '%奶茶%' OR note LIKE '%一点点%' OR note LIKE '%喜茶%' OR note LIKE '%瑞幸%' OR note LIKE '%星巴克%' OR note LIKE '%蜜雪%' OR note LIKE '%茶百道%' OR note LIKE '%咖啡%' OR note LIKE '%红牛%'", "餐饮/咖啡奶茶"),
    ("note LIKE '%买菜%' OR note LIKE '%食材%' OR note LIKE '%调料%' OR note LIKE '%种菜%' OR note LIKE '%种植蔬菜%'", "餐饮/食材"),

    # === 居家/日用 ===
    ("note LIKE '%山姆%' OR note LIKE '%华润万家%' OR note LIKE '%购好超市%' OR note LIKE '%添油加醋%' OR note LIKE '%大润发%' OR note LIKE '%沃尔玛%' OR note LIKE '%家乐福%' OR note LIKE '%好又多%' OR note LIKE '%好想来%' OR note LIKE '%京东%' OR note LIKE '%淘宝%'", "居家/日用品"),

    # === 居家/房租水电 ===
    ("note LIKE '%电费%' OR note LIKE '%水费%' OR note LIKE '%燃气费%' OR note LIKE '%燃气%' OR note LIKE '%物业%' OR note LIKE '%房租%' OR note LIKE '%租金%' OR note LIKE '%未来住宿%'", "居家/房租水电"),

    # === 居家/还款 ===
    ("note LIKE '%利息%' OR note LIKE '%手续费%' OR note LIKE '%花呗%' OR note LIKE '%借呗%' OR note LIKE '%补%欠款%' OR note LIKE '%补21%' OR note LIKE '%补22%'", "居家/还款"),

    # === 居家/通讯 ===
    ("note LIKE '%翻墙%' OR note LIKE '%迅雷%' OR note LIKE '%身份证%' OR note LIKE '%充值服务%' OR note LIKE '%中兴通讯%' OR note LIKE '%话费%'", "居家/通讯"),

    # === 居家/维修 ===
    ("note LIKE '%钥匙%' OR note LIKE '%疏通下水道%' OR note LIKE '%灯开关%' OR note LIKE '%纸箱%'", "居家/维修"),

    # === 居家/清洁 ===
    ("note LIKE '%美团家政%' OR note LIKE '%清洁%'", "居家/清洁"),

    # === 居家/装饰 ===
    ("note LIKE '%过年食物和装饰%' OR note LIKE '%花卉%' OR note LIKE '%花盆%' OR note LIKE '%花店%' OR note LIKE '%园艺%' OR note LIKE '%种植%' OR note LIKE '%浇水%' OR note LIKE '%洒水%'", "居家/装饰"),

    # === 出行 ===
    ("note LIKE '%高德打车%' OR note LIKE '%美团打车%' OR note LIKE '%滴滴%' OR note LIKE '%打车%' OR note LIKE '%网约车%'", "出行/网约车"),
    ("note LIKE '%地铁%' OR note LIKE '%公交%' OR note LIKE '%巴士%' OR note LIKE '%哈啰%' OR note LIKE '%共享单车%' OR note LIKE '%小黄车%' OR note LIKE '%自行车%' OR note LIKE '%客车%'", "出行/公共交通"),
    ("note LIKE '%停车%' OR note LIKE '%财政局%'", "出行/车辆相关/停车"),
    ("note LIKE '%油费%' OR note LIKE '%汽油%' OR note LIKE '%中石油%' OR note LIKE '%玻璃水%' OR note LIKE '%汽车衣%'", "出行/车辆相关"),
    ("note LIKE '%飞机票%' OR note LIKE '%高铁%' OR note LIKE '%火车%' OR note LIKE '%长途%'", "出行/长途"),

    # === 玩乐/影音游戏 ===
    ("note LIKE '%腾讯%' OR note LIKE '%天游%' OR note LIKE '%游戏%' OR note LIKE '%wow%' OR note LIKE '%魔兽世界%' OR note LIKE '%金铲铲%' OR note LIKE '%爱奇艺%' OR note LIKE '%qq音乐%' OR note LIKE '%音乐%' OR note LIKE '%电影%' OR note LIKE '%网鱼%' OR note LIKE '%网吧%' OR note LIKE '%剧本杀%'", "玩乐/影音游戏"),

    # === 社交 ===
    ("note LIKE '%红包%' OR note LIKE '%🧧%'", "社交/红包"),
    ("note LIKE '%礼物%' OR note LIKE '%衣服礼物%' OR note LIKE '%生日小礼物%' OR note LIKE '%蛋糕%'", "社交/礼物"),
    ("note LIKE '%洋洋%' OR note LIKE '%苏浩%' OR note LIKE '%一起吃%' OR note LIKE '%自助%' OR note LIKE '%朋友%'", "社交/聚会"),
    ("note LIKE '%脱口秀%' OR note LIKE '%欢乐谷%' OR note LIKE '%演唱会%' OR note LIKE '%景区%' OR note LIKE '%景点%'", "玩乐/演出赛事"),

    # === 穿着 ===
    ("note LIKE '%男士内裤%' OR note LIKE '%内衣%' OR note LIKE '%内裤%'", "穿着/内衣袜"),
    ("note LIKE '%眼镜%' OR note LIKE '%眼镜框%' OR note LIKE '%帽子%' OR note LIKE '%背包%' OR note LIKE '%配饰%'", "穿着/包配"),
    ("note LIKE '%理发%' OR note LIKE '%发艺%' OR note LIKE '%美容%' OR note LIKE '%洗面奶%' OR note LIKE '%洗澡巾%'", "穿着/洗护"),
    ("note LIKE '%衣服%' OR note LIKE '%裤子%' OR note LIKE '%鞋子%' OR note LIKE '%雨衣%' OR note LIKE '%防晒服%' OR note LIKE '%羽绒服%' OR note LIKE '%打底裤%'", "穿着/_未归类"),

    # === 健康 ===
    ("note LIKE '%蓝芩%' OR note LIKE '%感冒药%' OR note LIKE '%药%' OR note LIKE '%药物%' OR note LIKE '%眼药水%' OR note LIKE '%烫伤膏%' OR note LIKE '%滴眼液%' OR note LIKE '%药房%' OR note LIKE '%大药房%'", "健康/药品"),
    ("note LIKE '%看病%' OR note LIKE '%医院%' OR note LIKE '%神经性皮炎%' OR note LIKE '%医药%' OR note LIKE '%皮炎%'", "健康/看病"),

    # === 宠物 ===
    ("note LIKE '%猫粮%' OR note LIKE '%狗粮%' OR note LIKE '%猫零食%' OR note LIKE '%猫薄荷%'", "宠物/食物"),
    ("note LIKE '%猫砂%' OR note LIKE '%猫窝%' OR note LIKE '%猫盆%' OR note LIKE '%猫洗澡%'", "宠物/用品"),
    ("note LIKE '%宠物医院%' OR note LIKE '%驱虫%' OR note LIKE '%猫药%' OR note LIKE '%治病%'", "宠物/医疗"),

    # === 学习 ===
    ("note LIKE '%培训%' OR note LIKE '%课程%' OR note LIKE '%学习%' OR note LIKE '%提升%'", "学习/课程培训"),
    ("note LIKE '%键盘%' OR note LIKE '%移动硬盘%' OR note LIKE '%pad%' OR note LIKE '%火山引擎%' OR note LIKE '%deepseek%' OR note LIKE '%玛昆%'", "学习/工具"),

    # === 居家/账本调整 ===
    ("note LIKE '%北京泉新高品%' OR note LIKE '%智咖时代%' OR note LIKE '%搬迁%' OR note LIKE '%搬家%'", "居家/账本调整"),
]

# 待处理的目标分类
TARGETS = [
    '餐饮/_未分类', '出行/_未分类', '玩乐/_未分类', '居家/_未分类',
    '餐饮/食材/_未分类', '社交/_未分类', '宠物/_未分类', '穿着/_未分类',
    '健康/_未分类', '学习/_未分类', '穿着/洗护/_未分类', '出行/车辆相关/_未分类',
    '居家/未归类',
]


def match_rule(note):
    """根据 note 关键词匹配规则,返回 (new_category, matched)"""
    if not note or not note.strip():
        l1 = None
        return None, False
    for where_clause, target_cat in GENERAL_RULES:
        # 提取所有 LIKE 关键词
        keywords = re.findall(r"'%([^%]+)%'", where_clause)
        if any(kw in note for kw in keywords):
            return target_cat, True
    return None, False


def find_all_targets():
    """找出所有目标记录"""
    conn = init_db()
    try:
        cursor = conn.cursor()
        placeholders = ','.join('?' * len(TARGETS))
        cursor.execute(f"SELECT id, category, note FROM {TABLE_NAME} WHERE category IN ({placeholders})", TARGETS)
        return cursor.fetchall()
    finally:
        conn.close()


def simulate():
    """模拟处理,展示分散效果"""
    records = find_all_targets()
    if not records:
        print("\u2713 没有目标记录")
        return

    print(f'\n=== 输入 {len(records)} 条 ===\n')

    new_cat_buckets = {}
    note_fill_count = 0
    for rid, cat, note in records:
        l1 = cat.split('/')[0]
        new_cat, matched = match_rule(note)
        if matched:
            final = new_cat
        else:
            final = f"{l1}/_未归类"
            if not note or not note.strip():
                note_fill_count += 1
        new_cat_buckets[final] = new_cat_buckets.get(final, 0) + 1

    print('按规则链 + 默认 L1 模拟分布:')
    for cat, cnt in sorted(new_cat_buckets.items(), key=lambda x: -x[1]):
        marker = " ← 新兜底" if cat.endswith("_未归类") else ""
        print(f'  → {cat}: {cnt} 笔{marker}')

    print(f'\n无 note 回填: {note_fill_count} 笔 → note 末尾加 "[原分类:L1]"')


def export_backup():
    """导出所有目标记录的 id + 当前 category + 当前 note"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"migrate_uncategorized_{timestamp}.csv"
    conn = init_db()
    try:
        cursor = conn.cursor()
        placeholders = ','.join('?' * len(TARGETS))
        with open(backup_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'old_category', 'old_note'])
            cursor.execute(f"SELECT id, category, note FROM {TABLE_NAME} WHERE category IN ({placeholders})", TARGETS)
            for row in cursor.fetchall():
                writer.writerow([row[0], row[1], row[2] or ''])
        return backup_file
    finally:
        conn.close()


def execute_migration():
    """整体事务执行迁移"""
    conn = init_db()
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN EXCLUSIVE")

        total_updated = 0
        placeholders = ','.join('?' * len(TARGETS))

        for target in TARGETS:
            l1 = target.split('/')[0]
            cursor.execute(f"SELECT id, note FROM {TABLE_NAME} WHERE category=?", (target,))
            rows = cursor.fetchall()
            for rid, note in rows:
                new_cat, matched = match_rule(note)
                if matched:
                    # 有 note + 匹配 → 改 category
                    cursor.execute(f"UPDATE {TABLE_NAME} SET category=? WHERE id=?", (new_cat, rid))
                    total_updated += 1
                else:
                    # 无 note 或没匹配 → 改 note + category
                    if note and note.strip():
                        new_note = note
                    else:
                        new_note = f"[原分类:{l1}]"
                    new_cat = f"{l1}/_未归类"
                    cursor.execute(f"UPDATE {TABLE_NAME} SET category=?, note=? WHERE id=?", (new_cat, new_note, rid))
                    total_updated += 1

        conn.commit()
        return total_updated
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def rollback(backup_file: Path):
    """根据备份反向还原 category 和 note"""
    if not backup_file.exists():
        print(f"\u2717 备份文件不存在: {backup_file}")
        return
    conn = init_db()
    try:
        cursor = conn.cursor()
        rolled = 0
        failed = 0
        with open(backup_file, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                old_cat = row['old_category']
                old_note = row['old_note']
                cursor.execute(f"UPDATE {TABLE_NAME} SET category=?, note=? WHERE id=?",
                               (old_cat, old_note, int(row['id'])))
                if cursor.rowcount:
                    rolled += 1
                else:
                    failed += 1
            conn.commit()
            print(f"\u2713 回滚成功 {rolled} 条,失败 {failed} 条")
    finally:
        conn.close()


def main():
    if "--rollback" in sys.argv:
        idx = sys.argv.index("--rollback")
        if idx + 1 >= len(sys.argv):
            print("用法: python migrate_uncategorized.py --rollback <backup.csv>")
            return
        rollback(Path(sys.argv[idx + 1]))
        return

    print(f"将操作的数据库: {DB_PATH}")
    print(f"备份目录: {BACKUP_DIR}")
    print(f"目标分类: {len(TARGETS)} 个\n")

    # 1. 模拟
    simulate()

    if "--execute" not in sys.argv:
        print("\n(dry-run 模式,未做任何修改。要执行请加 --execute 参数)")
        return

    # 2. execute 模式
    print("\n\u26a0\ufe0f 即将执行迁移:")
    print("  \u2022 有 note 匹配关键词 → 细分到 L2/L3")
    print("  \u2022 无 note → note 加 '[原分类:L1]' + category 改 'X/_未归类'")
    print("  \u2022 任何环节出错自动回滚")
    print("  \u2022 执行前导出 CSV 备份")

    if "--force" not in sys.argv:
        try:
            resp = input("\n输入 YES 确认执行(其它任意输入取消): ").strip()
        except EOFError:
            print("\n\u2717 非交互模式,已取消")
            return
        if resp != "YES":
            print("已取消")
            return

    backup = export_backup()
    print(f"\n\u2713 备份已保存: {backup}")

    try:
        updated = execute_migration()
        print(f"\n\u2713 已更新 {updated} 条记录")
        print(f"回滚: python migrate_uncategorized.py --rollback {backup}")
    except Exception as e:
        print(f"\n\u2717 执行失败,已自动回滚: {e}")


if __name__ == "__main__":
    main()
