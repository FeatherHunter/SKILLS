#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整处理 ID 1028 湾仔码头水饺:
1) update 重写备注(完整)
2) expiration_date 同步
3) add-product 食品库(用营养成分表)
4) add-product 黑猪前腿肉馅料 sub-product(可选,先 add 主产品)
"""
import subprocess
import sys
from pathlib import Path

HOME = r"D:\2Study\StudyNotes\SKILLS\居家管家\scripts\home_manager.py"
CAL = r"D:\2Study\StudyNotes\SKILLS\卡路里\scripts\calorie_tracker.py"

WATERJIA_REMARK = (
    "山姆会员商店极速达,湾仔码头 黑猪肉大白菜水饺 1.62kg(81 只装),袋装速冻。"
    "【品牌】湾仔码头(始于 1978 年香港,创始人「水饺皇后」臧健和臧姑娘,品质黑猪 + 干净配方)。"
    "【产品名】大白菜水饺(馅料:黑猪肉 + 大白菜)。"
    "【规格】净含量 1.62kg / 81 只装 / 馅料含量 ≥ 35% / 黑猪肉 ≥ 20.3% / 黑猪前腿肉(添加量) ≥ 15.5% / 大白菜 ≥ 16.0%。"
    "【类别】速冻面米食品(生制品、含肉类,非即食)。"
    "【标准号】GB 19295。"
    "【保质期】12 个月。"
    "【生产日期】2026-07-06(A3 21:58,代工厂代码 A = 上海品食冷冻食品有限公司,上海市浦东新区三林镇懿德路 399 号 1 号楼)。"
    "【过期日期】2027-07-05(剩约 11.5 月)。"
    "【储存】必须 -18°C 及以下冷冻保存。"
    "【工艺特色】汁多肉好 / 皮弹馅大 / 甄选黑猪原块前腿肉细腻部位,手工剔除筋膜 / 手挑鲜嫩大白菜。"
    "【过敏源】含**黑大豆 + 含麸质的谷物及其制品**,可能含有花生/坚果/蛋类/鱼类/甲壳类动物/乳成分。"
    "【推荐食用方法(无须解冻)】①**煮饺**:沸水加盖中火 5min,揭盖后中火 1.5min(每锅 ≤ 20 只) ②**蒸饺**:水沸后放蒸架加盖中大火 8min(每锅 ≤ 15 只) ③**煎饺**:煎锅稍煎 2min + 洒 150ml 水 + 加盖煎至水干(每锅 ≤ 15 只)。"
    "【营养成分(per 100g)】794 kJ(9% NRV) ≈ 190 kcal / 7.0g 蛋白(12%) / 8.1g 脂肪(14%,饱 3.0g/15%) / 22.1g 碳水(7%,糖 3.0g) / 594mg 钠(29%)。"
    "【委托方】通用磨坊贸易(上海)有限公司(上海市浦东新区瓷贤路 399 号,邮编 200124,客服 4008201380,Qualitychina@genmills.com)。"
    "【受委托生产】见包装生产日期后字母代号:A=上海品食冷冻食品(SC11131011500831)/ B=广州品食乐佳冻食品(SC11144011600836,广州市黄埔区埔南路 28 号,邮编 510760)/ C=通用磨坊食品(三河)(SC11113108200324,河北省廊坊市三河市泃阳西大街北侧,邮编 065200)。"
    "【配料表】小麦粉、黑猪肉(≥20.3%)、大白菜(≥16.0%)、水、葱、香辛料、洋葱、蚝油、食用盐、芝麻油、白砂糖、鸡精调味料、淀粉、味精、酱油(含焦糖色)、生姜、白胡椒、黑猪前腿肉(添加量 ≥15.5%)。"
    "【条形码】6923420012740。"
    "【版本号】ACS NO: W260410。"
    "【购买日】2026-07-30(¥49.90)。"
)

# 1) ID 1028 update 备注 + 过期日期
print("=" * 60)
print("[1] ID 1028 update(备注 + 过期日期 + tag 增量)")
print("=" * 60)
r = subprocess.run([
    sys.executable, HOME, "update",
    "--id", "1028",
    "--expiration-date", "2027-07-05",
    "--add-tag", "2026-07-06生产,2027-07-05过期,12个月保质期,A3代工厂(上海品食),GB 19295,通用磨坊,客服4008201380,黑大豆过敏,含麸质,可能含花生坚果蛋鱼甲壳乳,煮饺5+1.5min,蒸饺8min,煎饺2min+150ml水,馅料≥35%,黑猪肉≥20.3%,黑猪前腿肉≥15.5%,大白菜≥16%,A上海品食,B广州品食,C通用磨坊三河,SC11131011500831,SC11144011600836,SC11113108200324,条形码6923420012740,ACS W260410,7.0g蛋白,8.1g脂肪,3.0g饱和脂肪,22.1g碳水,3.0g糖,594mg钠,190kcal,创始人臧健和,水饺皇后",
    "--remark", WATERJIA_REMARK,
], capture_output=True, text=True, encoding="utf-8")
# 截断长输出
lines = r.stdout.split("\n")
for line in lines[:5] + (["..."] if len(lines) > 8 else []) + lines[-3:]:
    print(line)
if r.stderr: print("STDERR:", r.stderr)
print(f"exit: {r.returncode}\n")

# 2) add-product 食品库
print("=" * 60)
print("[2] add-product 食品库:湾仔码头黑猪肉大白菜水饺")
print("=" * 60)
SOURCE = "包装标签实测 2026-07-30(山姆极速达湾仔码头黑猪肉大白菜水饺,GB 19295,生产日 2026-07-06,过期日 2027-07-05)"
r = subprocess.run([
    sys.executable, CAL, "add-product",
    "湾仔码头 黑猪肉大白菜水饺(速冻面米生制品)",  # name
    "湾仔码头",                                          # brand
    "190",                                                # cal kcal/100g(794 kJ ≈ 190)
    "7.0",                                                # protein
    "8.1",                                                # fat
    "3.0",                                                # saturated_fat
    "22.1",                                               # carbs
    "3.0",                                                # sugar
    "0",                                                  # fiber(未标)
    "594",                                                # sodium
    f"GB 19295,保质期 12 个月,-18°C 冷冻,生产日 2026-07-06,过期日 2027-07-05。{SOURCE}",
], capture_output=True, text=True, encoding="utf-8")
print(r.stdout)
if r.stderr: print("STDERR:", r.stderr)
print(f"exit: {r.returncode}")
