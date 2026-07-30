#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""录入 3 件山姆食品,位置=快递/山姆"""
import subprocess
import sys

CLI = r"D:\2Study\StudyNotes\SKILLS\居家管家\scripts\home_manager.py"

items = [
    {
        "name": "Member's Mark 精选鲜鸡蛋",
        "category_id": "153",  # 生鲜食品/肉禽蛋
        "price": "18.90",
        "tags": "鸡蛋,Member's Mark,山姆自有品牌,30枚,1.59kg,盒装,白色外壳,蛋白质,早餐食材,家庭装,常温保存,未受精,生鲜",
        "remark": "山姆会员商店极速达,30 枚 1.59kg 盒装鲜鸡蛋,家庭早餐/烘焙常用。常温或冷藏保存,购买日 2026-07-30。建议 7-15 天内食用完。",
    },
    {
        "name": "Jimmy Dean 鸡排松饼组合",
        "category_id": "158",  # 加工食品/速食
        "price": "59.90",
        "tags": "速食,Jimmy Dean,鸡排松饼,1.256kg,西式早餐,冷藏保存,微波加热,蛋白质,美国品牌,家庭装,方便快捷,工作日早餐",
        "remark": "山姆会员商店极速达,Jimmy Dean 美式鸡排松饼组合装,1.256kg 盒装,需冷藏保存,微波或烤箱加热 1-2 分钟即食。适合工作日快速早餐。购买日 2026-07-30,保质期见包装。",
    },
    {
        "name": "湾仔码头 黑猪肉大白菜水饺",
        "category_id": "158",  # 加工食品/速食
        "price": "49.90",
        "tags": "速冻水饺,湾仔码头,黑猪肉,大白菜,1.62kg,81只,袋装,冷冻保存,水饺,中式快餐,家常主食,家庭装,煮蒸煎皆可",
        "remark": "山姆会员商店极速达,湾仔码头黑猪肉大白菜水饺,1.62kg 共 81 只,袋装速冻。需 -18°C 以下冷冻保存,水煮/蒸/煎均可。家庭正餐主食备用。购买日 2026-07-30,保质期 12 个月。",
    },
]

for i, it in enumerate(items, 1):
    print(f"\n========== 录入 {i}/3: {it['name']} ==========")
    r = subprocess.run([
        sys.executable, CLI, "add",
        "--name", it["name"],
        "--category-id", it["category_id"],
        "--location", "快递/山姆",
        "--quantity", "1",
        "--price", it["price"],
        "--purchase-date", "2026-07-30",
        "--tags", it["tags"],
        "--remark", it["remark"],
    ], capture_output=True, text=True, encoding="utf-8")
    print("STDOUT:")
    print(r.stdout)
    if r.stderr:
        print("STDERR:")
        print(r.stderr)
    print(f"exit: {r.returncode}")
