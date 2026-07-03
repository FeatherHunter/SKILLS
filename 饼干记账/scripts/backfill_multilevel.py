"""
backfill_multilevel.py — 一次性 backfill 脚本
把旧的不含 / 的 category 值批量更新到 v3.1 多级分类体系

【安全设计】
1. 默认 dry-run 模式,只打印不写
2. 修改前自动导出 CSV 备份
3. 只动 category 字段,不动其他字段、行、时间、金额
4. 整体事务:任何环节出错自动回滚
5. EXCLUSIVE LOCK:防止并发写入
6. --execute 模式可加 --force 跳过二次确认
7. 提供 --rollback 参数:根据 CSV 备份反向还原

【使用】
python backfill_multilevel.py              # dry-run,预览
python backfill_multilevel.py --execute   # 实际执行(需 YES 确认)
python backfill_multilevel.py --execute --force  # 跳过 YES 确认
python backfill_multilevel.py --rollback <backup.csv>  # 回滚
"""

import sqlite3
import csv
import sys
from datetime import datetime
from pathlib import Path

# 复用 db.py 的路径查找逻辑
sys.path.insert(0, str(Path(__file__).parent))
from db import _find_db_path, SKILL_DIR, DB_FILENAME, TABLE_NAME, init_db

DB_PATH = _find_db_path(SKILL_DIR, DB_FILENAME)
BACKUP_DIR = Path(__file__).parent.parent / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

# 不动集合:backfill 时完全跳过,保留原值
# 当前为空:所有旧值都已有明确处理方案
SKIP_CATEGORIES = set()

# 旧值 → 新分类 映射表(用户确认)
# 特殊值 "__RED_PACKET__" 表示脚本按 amount 正负分流:
#   amount > 0 → 其他收入/红包
#   amount <= 0 → 社交/红包
CATEGORY_MAP = {
    "个人消费": "其他/_未分类",
    "个护": "居家/日用品/洗护",
    "书籍": "学习/书籍",
    "交通": "出行/_未分类",
    "人情": "社交/_未分类",
    "住房": "居家/_未分类",
    "借入": "其他收入/_未分类",
    "借出": "居家/赡养抚养",  # 用户揭示:给小孩生活费,加 v3.1 后用新 L2
    "还款": "其他/_未分类",   # 花呗/借呗/利息/补欠款,非典型消费
    "软件订阅": "其他/_未分类",  # 仅 1 条 VPN 类工具,不值得专门分类
    "其他": "其他/_未分类",
    "其它": "其他/_未分类",
    "出行": "出行/_未分类",
    "分红": "投资/分红",
    "办公": "学习/工具",
    "医疗": "健康/_未分类",
    "外卖": "餐饮/外卖",
    "娱乐": "玩乐/_未分类",
    "学习": "学习/_未分类",
    "宠物": "宠物/_未分类",
    "宠物用品": "宠物/用品",
    "家庭": "居家/_未分类",
    "工作": "其他/_未分类",
    "工资": "工资/基本工资",
    "年终奖": "奖金/年终奖",
    "捐赠": "社交/公益",
    "收款": "其他收入/_未分类",
    "教育": "学习/_未分类",
    "数码": "居家/家具家电/数码设备",
    "旅行": "玩乐/旅游",
    "日用": "居家/日用品",
    "日用品": "居家/日用品",
    "服饰": "穿着/_未分类",
    "水果": "餐饮/水果",
    "汽车": "出行/车辆相关/_未分类",
    "汽车养护": "出行/车辆相关/保养",
    "游戏": "玩乐/影音游戏/游戏",
    "烟酒": "餐饮/烟酒",
    "理发": "穿着/洗护/_未分类",
    "理财": "投资/理财",
    "生鲜水产": "餐饮/食材/_未分类",
    "生鲜肉类": "餐饮/食材/_未分类",
    "碳酸饮料": "餐饮/咖啡奶茶/其他饮品",
    "礼品": "社交/礼物",
    "礼物": "社交/礼物",
    "礼金": "社交/红包",
    "社交": "社交/_未分类",
    "租金": "居家/房租水电/房租",
    "纠正": "其他/_未分类",
    "红包": "__RED_PACKET__",  # 特殊:按 amount 正负分流
    "维修": "居家/维修",
    "美容": "穿着/洗护/_未分类",
    "蔬菜": "餐饮/食材/_未分类",
    "购物": "其他/_未分类",
    "运动": "玩乐/运动健身",
    "追星": "玩乐/_未分类",
    "通信": "居家/通讯",
    "通讯": "居家/通讯",
    "配送包装": "其他/_未分类",
    "零食": "餐饮/零食",
    "食品": "餐饮/_未分类",
    "餐饮": "餐饮/_未分类",
    "饮品": "餐饮/咖啡奶茶",
}

# 特殊规则:旧值不只映射到单一分类,而是按 note/amount 走规则链
# 规则按顺序执行,先匹配先改,后匹配兜底
# 格式: (note 关键词 LIKE 表达式 或 "amount > 0", 新分类)
SPECIAL_RULES_KEYS = set(["购物", "书籍", "办公", "其他/_未分类", "其他收入/_未分类"])

# 购物(70 条)按 note 关键词规则细分
SHOPPING_RULES = [
    ("amount > 0", "其他收入/退款"),
    ("note LIKE '%猫粮%' OR note LIKE '%狗粮%'", "宠物/食物"),
    ("note LIKE '%水果%' OR note LIKE '%水果店%'", "餐饮/水果"),
    ("note LIKE '%零食%'", "餐饮/零食"),
    ("note LIKE '%可乐%' OR note LIKE '%芬达%' OR note LIKE '%东方树叶%' OR note LIKE '%桶装水%' OR note LIKE '%矿泉水%' OR note LIKE '%雪碧%' OR note LIKE '%农夫山泉%'", "餐饮/咖啡奶茶/其他饮品"),
    ("note LIKE '%外卖%' OR note LIKE '%饿了么%'", "餐饮/外卖"),
    ("note LIKE '%水饺%' OR note LIKE '%包子%' OR note LIKE '%炸鸡%' OR note LIKE '%鸡胸%' OR note LIKE '%蔬菜%' OR note LIKE '%洋葱%' OR note LIKE '%胡萝卜%' OR note LIKE '%腰果%' OR note LIKE '%开心果%' OR note LIKE '%白砂糖%' OR note LIKE '%黄瓜%' OR note LIKE '%花生%' OR note LIKE '%巧克力%' OR note LIKE '%甜甜圈%' OR note LIKE '%可颂%' OR note LIKE '%菜%'", "餐饮/食材"),
    ("note LIKE '%内裤%' OR note LIKE '%袜子%' OR note LIKE '%内衣%'", "穿着/内衣袜"),
    ("note LIKE '%手机%' OR note LIKE '%充电%' OR note LIKE '%耳机%' OR note LIKE '%电动牙刷%' OR note LIKE '%键盘%' OR note LIKE '%鼠标%' OR note LIKE '%落地镜%' OR note LIKE '%自拍杆%' OR note LIKE '%智能插座%' OR note LIKE '%蓝牙%' OR note LIKE '%氮化镓%'", "居家/家具家电/数码设备"),
    ("note LIKE '%网线%' OR note LIKE '%晾衣%' OR note LIKE '%收纳%' OR note LIKE '%纸面巾%' OR note LIKE '%留香珠%' OR note LIKE '%海绵%' OR note LIKE '%手套%' OR note LIKE '%遮光%' OR note LIKE '%理线器%' OR note LIKE '%防烫%' OR note LIKE '%加长%' OR note LIKE '%反光%' OR note LIKE '%省钱卡%' OR note LIKE '%淘宝卡%'", "居家/日用品"),
    ("1=1", "居家/_未分类"),  # 兜底
]

# 书籍(23 条):食谱→餐饮/食材,其余→玩乐
BOOKS_RULES = [
    ("note LIKE '%食谱%'", "餐饮/食材"),
    ("1=1", "玩乐/影音游戏/书籍影视"),
]

# 办公(17 条):硬件→居家/数码,其余→学习/工具
OFFICE_RULES = [
    ("note LIKE '%键盘%' OR note LIKE '%鼠标%' OR note LIKE '%智能插座%'", "居家/家具家电/数码设备"),
    ("1=1", "学习/工具"),
]

# "其他/_未分类" 和 "其他收入/_未分类" 的规则链(98 笔)
# 目标:干掉"其他"和"未分类"两个分类
# 兜底:居家/未归类(临时,提示用户后续手动处理)
OTHER_CATEGORY_RULES = [
    # 1. 退款(正数 amount 优先,因退款是收入)
    ("amount > 0", "其他收入/退款"),

    # 2. 还款(花呗/借呗/利息/补欠款/补21/补22/手续费/转账利息)
    ("note LIKE '%花呗%' OR note LIKE '%借呗%' OR note LIKE '%利息%' OR note LIKE '%补欠款%' OR note LIKE '%补21%' OR note LIKE '%补22%' OR note LIKE '%补%欠款%' OR note LIKE '%手续费%' OR note LIKE '%转账利息%'", "居家/还款"),

    # 3. 共同(旅行境外系列)
    ("note LIKE '%共同%' OR note LIKE '%韩元%' OR note LIKE '%日元%' OR note LIKE '%高铁%' OR note LIKE '%打车%' OR note LIKE '%寄存%' OR note LIKE '%船小费%' OR note LIKE '%缆车%' OR note LIKE '%团签%' OR note LIKE '%主厨餐厅%' OR note LIKE '%仙境坊%' OR note LIKE '%一兰拉面%' OR note LIKE '%福冈%' OR note LIKE '%韩国%' OR note LIKE '%日本%'", "玩乐/旅游/境外"),

    # 4. 诈骗
    ("note LIKE '%诈骗%'", "居家/意外损失"),

    # 5. 工作(AI 工具/工作相关 + EMS + 打印)
    ("note LIKE '%ChatGPT%' OR note LIKE '%qoder%' OR note LIKE '%minimax%' OR note LIKE '%deepseek%' OR note LIKE '%token%' OR note LIKE '%image2%' OR note LIKE '%工作%' OR note LIKE '%EMS给公司%' OR note LIKE '%EMS%' OR note LIKE '%催告函%' OR note LIKE '%特快%' OR note LIKE '%打印费%' OR note LIKE '%打印%'", "居家/工作"),

    # 6. 通讯(网络服务/支付宝)
    ("note LIKE '%翻墙%' OR note LIKE '%支付宝%'", "居家/通讯"),

    # 7. 礼品/红包
    ("note LIKE '%父亲节%' OR note LIKE '%节日红包%' OR note LIKE '%红包%'", "社交/红包/节日"),
    ("note LIKE '%礼品%' OR note LIKE '%领导%' OR note LIKE '%感谢%'", "社交/礼物/感谢"),

    # 8. 日用品(消毒液/快递费/包装费)
    ("note LIKE '%次氯酸%' OR note LIKE '%消毒%' OR note LIKE '%快递费%' OR note LIKE '%包装费%' OR note LIKE '%山姆包装%' OR note LIKE '%山姆给自己%'", "居家/日用品"),

    # 9. 餐饮外卖
    ("note LIKE '%餐厅%' OR note LIKE '%一兰拉面%' OR note LIKE '%面条%' OR note LIKE '%饭%'", "餐饮/外卖"),

    # 10. 旅游收入
    ("note LIKE '%旅游%'", "其他收入/退款"),

    # 11. 返现
    ("note LIKE '%返现%'", "其他收入/返现"),

    # 12. 补账
    ("note = '补'", "其他收入/补账"),

    # 13. 账本调整(账本纠正/兑换韩元/理发正数)
    ("note LIKE '%账本纠正%' OR note LIKE '%兑换韩元%' OR note LIKE '%理发%'", "居家/账本调整"),

    # 兜底
    ("1=1", "居家/未归类"),
]


def find_old_categories():
    """找出所有不含 / 的 category 值及记录数"""
    conn = init_db()
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT category, COUNT(*) as cnt
            FROM {TABLE_NAME}
            WHERE category != ''
              AND category NOT LIKE '%/%'
            GROUP BY category
            ORDER BY category
        """)
        return cursor.fetchall()
    finally:
        conn.close()


def preview_changes():
    """预览要做的修改,返回 (old_cat, new_cat_or_marker, count) 列表(已过滤 SKIP)"""
    old_cats = find_old_categories()
    if not old_cats:
        print("\u2713 数据库中没有旧值(category 都不含 /),无需 backfill")
        return []

    print(f"\n=== 即将更新的 category 值(按映射表) ===")
    print(f"{'原值':<20} {'记录数':<8} {'新值/操作'}")
    print("-" * 70)
    changes = []
    skipped = []
    unmapped = []

    for cat, cnt in old_cats:
        if cat in SKIP_CATEGORIES:
            skipped.append((cat, cnt))
            print(f"{cat:<20} {cnt:<8} [跳过,保留原值]")
            continue

        if cat in CATEGORY_MAP:
            new_cat = CATEGORY_MAP[cat]
        else:
            new_cat = f"{cat}/_未分类"
            unmapped.append(cat)
        changes.append((cat, new_cat, cnt))
        display = new_cat
        if new_cat == "__RED_PACKET__":
            display = "(脚本按 amount 正负分流)"
        print(f"{cat:<20} {cnt:<8} {display}")

    if skipped:
        skip_total = sum(cnt for _, cnt in skipped)
        print(f"\n\u26a0 跳过 {len(skipped)} 个旧值(共 {skip_total} 条,保留原值):")
        for cat, cnt in skipped:
            print(f"  - {cat} ({cnt} 条)")

    if unmapped:
        print(f"\n\u26a0 警告: {len(unmapped)} 个旧值不在映射表,默认用机械后缀:")
        for c in unmapped:
            print(f"  - {c}")

    will_change_total = sum(cnt for _, _, cnt in changes)
    print(f"\n将修改 {len(changes)} 个旧值,共 {will_change_total} 条记录")
    if skipped:
        skip_total = sum(cnt for _, cnt in skipped)
        print(f"将跳过 {len(skipped)} 个旧值,共 {skip_total} 条记录(保留原值)")
    return changes


def export_backup(changes):
    """导出备份 CSV:每个旧值对应的所有记录 id + 原 category + 新 category"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"backfill_{timestamp}.csv"

    conn = init_db()
    try:
        cursor = conn.cursor()
        with open(backup_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'old_category', 'new_category'])
            for old_cat, new_cat, _ in changes:
                cursor.execute(f"""
                    SELECT id FROM {TABLE_NAME}
                    WHERE category = ? AND category NOT LIKE '%/%'
                """, (old_cat,))
                for (record_id,) in cursor.fetchall():
                    writer.writerow([record_id, old_cat, new_cat])
        return backup_file
    finally:
        conn.close()


def simulate_rule_distribution():
    """模拟关键词规则在每个特殊旧值上的分布(Python 模拟 SQL LIKE)"""
    import re
    conn = init_db()
    try:
        cursor = conn.cursor()

        for old_cat, rules in [("购物", SHOPPING_RULES), ("书籍", BOOKS_RULES), ("办公", OFFICE_RULES)]:
            cursor.execute("SELECT id, amount, note FROM bills WHERE category=?", (old_cat,))
            rows = cursor.fetchall()
            if not rows:
                continue

            print(f"\n【{old_cat}】 {len(rows)} 条 — 按规则链模拟分布:")
            buckets = {}
            for _, amount, note in rows:
                matched = False
                for where_clause, new_cat in rules:
                    if where_clause == "amount > 0":
                        if amount > 0:
                            buckets[new_cat] = buckets.get(new_cat, 0) + 1
                            matched = True
                            break
                    elif where_clause == "1=1":
                        buckets[new_cat] = buckets.get(new_cat, 0) + 1
                        matched = True
                        break
                    else:
                        # 提取 LIKE 表达式:note LIKE '%kw1%' OR note LIKE '%kw2%'...
                        keywords = re.findall(r"'%([^%]+)%'", where_clause)
                        if note and any(kw in note for kw in keywords):
                            buckets[new_cat] = buckets.get(new_cat, 0) + 1
                            matched = True
                            break
                if not matched:
                    buckets["❌ 未匹配"] = buckets.get("❌ 未匹配", 0) + 1

            for cat, cnt in sorted(buckets.items(), key=lambda x: -x[1]):
                print(f"  → {cat}: {cnt} 条")
    finally:
        conn.close()


def _apply_rule_chain(cursor, old_cat, rules):
    """按规则链顺序执行 UPDATE,先匹配先改,后匹配兜底"""
    total = 0
    for where_clause, new_cat in rules:
        cursor.execute(f"""
            UPDATE {TABLE_NAME}
            SET category = ?
            WHERE category = ? AND ({where_clause})
        """, (new_cat, old_cat))
        total += cursor.rowcount
    return total


def execute_changes(changes):
    """整体事务执行 backfill,异常自动回滚"""
    conn = init_db()
    try:
        cursor = conn.cursor()
        # EXCLUSIVE LOCK 防止并发写入
        cursor.execute("BEGIN EXCLUSIVE")

        total_updated = 0
        for old_cat, new_cat_or_marker, _ in changes:
            if new_cat_or_marker == "__RED_PACKET__":
                # 特殊:红包按 amount 正负分流
                cursor.execute(f"""
                    UPDATE {TABLE_NAME}
                    SET category = CASE
                        WHEN amount > 0 THEN '其他收入/红包'
                        ELSE '社交/红包'
                    END
                    WHERE category = ? AND category NOT LIKE '%/%'
                """, (old_cat,))
                total_updated += cursor.rowcount
            elif old_cat == "购物":
                total_updated += _apply_rule_chain(cursor, "购物", SHOPPING_RULES)
            elif old_cat == "书籍":
                total_updated += _apply_rule_chain(cursor, "书籍", BOOKS_RULES)
            elif old_cat == "办公":
                total_updated += _apply_rule_chain(cursor, "办公", OFFICE_RULES)
            elif old_cat in ("其他/_未分类", "其他收入/_未分类"):
                total_updated += _apply_rule_chain(cursor, old_cat, OTHER_CATEGORY_RULES)
            else:
                cursor.execute(f"""
                    UPDATE {TABLE_NAME}
                    SET category = ?
                    WHERE category = ? AND category NOT LIKE '%/%'
                """, (new_cat_or_marker, old_cat))
                total_updated += cursor.rowcount

        conn.commit()
        return total_updated
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def rollback(backup_file: Path):
    """根据备份 CSV 反向 UPDATE 还原"""
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
                cursor.execute(f"""
                    UPDATE {TABLE_NAME}
                    SET category = ?
                    WHERE id = ? AND category = ?
                """, (row['old_category'], int(row['id']), row['new_category']))
                if cursor.rowcount:
                    rolled += 1
                else:
                    failed += 1
            conn.commit()
            print(f"\u2713 回滚成功 {rolled} 条,失败 {failed} 条(可能已被手动改过)")
    finally:
        conn.close()


def main():
    if "--rollback" in sys.argv:
        idx = sys.argv.index("--rollback")
        if idx + 1 >= len(sys.argv):
            print("用法: python backfill_multilevel.py --rollback <backup.csv>")
            return
        rollback(Path(sys.argv[idx + 1]))
        return

    # 1. 展示 DB 路径(dry-run 也要展示)
    print(f"将操作的数据库: {DB_PATH}")
    print(f"备份目录: {BACKUP_DIR}")
    print()

    # 2. 预览变更
    changes = preview_changes()
    if not changes:
        return

    # 3. dry-run 模式:展示关键词规则模拟后直接退出
    if "--execute" not in sys.argv:
        simulate_rule_distribution()
        print("\n(dry-run 模式,未做任何修改。要执行请加 --execute 参数)")
        return

    # 4. execute 模式:最后确认
    print("\n\u26a0\ufe0f 即将执行 backfill:")
    print("  \u2022 所有旧 category 值会改成 L1/_未分类")
    print("  \u2022 任何环节出错会自动回滚(整体事务)")
    print("  \u2022 执行前会导出 CSV 备份到 backups/ 目录")

    # --force 跳过二次确认(用于脚本调用)
    if "--force" not in sys.argv:
        try:
            resp = input("\n输入 YES 确认执行(其它任意输入取消): ").strip()
        except EOFError:
            print("\n\u2717 非交互模式,已取消(避免误执行)")
            return
        if resp != "YES":
            print("已取消")
            return

    # 5. 备份 + 执行
    backup = export_backup(changes)
    print(f"\n\u2713 备份已保存: {backup}")

    try:
        updated = execute_changes(changes)
        print(f"\n\u2713 已更新 {updated} 条记录")
        print(f"\n回滚命令(如有需要):")
        print(f"  python backfill_multilevel.py --rollback {backup}")
    except Exception as e:
        print(f"\n\u2717 执行失败,已自动回滚: {e}")


if __name__ == "__main__":
    main()
