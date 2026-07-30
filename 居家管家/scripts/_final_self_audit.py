#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""自查最终状态:3 件物品的备注字数、tag 数、关键字段、SC 编号"""
import sqlite3
import subprocess

DB = r"D:\2Study\StudyNotes\.db\home.db"
c = sqlite3.connect(DB).cursor()

for item_id in (1026, 1027, 1028):
    print(f"\n========== ID {item_id} ==========")
    c.execute("SELECT name, remark, photo FROM items WHERE id=?", (item_id,))
    row = c.fetchone()
    name, remark, photo = row
    print(f"NAME: {name}")
    print(f"PHOTO: {photo}")
    print(f"REMARK 长度: {len(remark)} 字")

    # tag 数
    c.execute("SELECT tag FROM item_tags WHERE item_id=?", (item_id,))
    tags = [t[0] for t in c.fetchall()]
    print(f"TAGS 数量: {len(tags)}")

    # 位置
    c.execute("SELECT location, location_status, expiration_date FROM item_locations WHERE item_id=?", (item_id,))
    for loc in c.fetchall():
        print(f"LOCATION: {loc[0]} | status={loc[1]} | exp={loc[2]}")

    # 关键字段校验
    checks = {
        "1026 鸡蛋": ["Member's Mark", "GB 2749", "德清源", "2026-08-26", "2-6", "北京德清源"],
        "1027 松饼": ["Jimmy Dean", "SB/T 10379", "GB 7099", "2027-01-17", "TRZ", "TNT", "谷斯宝特", "SC104", "SC124"],
        "1028 水饺": ["湾仔码头", "GB 19295", "2027-07-05", "上海品食", "广州品食", "通用磨坊", "A3", "qualitychina", "生制品", "粘皮", "非即食"],
    }
    # 找到对应 name 的 checks
    for k, v in checks.items():
        if k.startswith(str(item_id)):
            print(f"\n  关键字段校验({k}):")
            for keyword in v:
                present = "✓" if keyword in remark else "✗"
                print(f"    {present} {keyword}")

# 食品库
print("\n========== 食品库 3 条 ==========")
db2 = sqlite3.connect(r"D:\2Study\StudyNotes\.db\calorie_data.db").cursor()
db2.execute("SELECT id, product_name, brand, calories, protein, fat, sodium FROM nutrition_products WHERE id IN (1933, 1934, 1936) ORDER BY id")
for r in db2.fetchall():
    print(f"  ID {r[0]}: {r[1]} | {r[2]} | {r[3]}kcal/100g | 蛋白{r[4]}g | 脂肪{r[5]}g | 钠{r[6]}mg")

# 饼干记账
print("\n========== 饼干记账 4 笔 (7/30) ==========")
import json
r = subprocess.run([r"D:\2Study\StudyNotes\SKILLS\饼干记账\scripts\record_bill.py", "list", "--date", "2026-07-30", "--json"], capture_output=True, text=True, encoding="utf-8")
data = json.loads(r.stdout)
total = sum(rec["amount"] for rec in data["data"]["records"])
print(f"  笔数: {data['data']['count']}, 合计: {total:.2f}")
for rec in data["data"]["records"]:
    print(f"  ID {rec['id']}: {rec['category']} {rec['amount']:+.2f} | {rec['note']}")
