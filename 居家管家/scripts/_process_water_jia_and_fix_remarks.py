#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
1) ID 1028 水饺:加主图 + 增量 tag
2) ID 1026 鸡蛋:重写备注(从图 1 + 图 2 提取全部信息)
3) ID 1027 松饼:重写备注(从 4 张图提取全部信息 + 营养成分)
"""
import shutil
import subprocess
import sys
from pathlib import Path

CLI = r"D:\2Study\StudyNotes\SKILLS\居家管家\scripts\home_manager.py"
PHOTOS_DIR = r"D:\2Study\StudyNotes\.db\HomeHub\photos"

# === 1) 复制水饺主图到 PHOTOS_DIR ===
SRC = r"C:\Users\辰辰洋洋\.minimax\v2\assets\2026\07\30\18-22-57-107-asset_20260730-182257-107_9d91c46fa27d_f15d183e-img_v3_02143_eb4a8965-812d-4d4d-9cdb-e24d1daf019g.jpg"
DEST = f"{PHOTOS_DIR}\\待录入_水饺主图.jpg"
Path(PHOTOS_DIR).mkdir(parents=True, exist_ok=True)
shutil.copy(SRC, DEST)
print(f"[1] 水饺主图已复制 → {DEST}\n")

# === 2) ID 1028 水饺 update:主图 + 增量 tag ===
print("=" * 60)
print("[2] ID 1028 湾仔码头黑猪肉大白菜水饺 update")
print("=" * 60)
r = subprocess.run([
    sys.executable, CLI, "update",
    "--id", "1028",
    "--add-tag", "湾仔码头,咏梅代言,81只装,1.62kg,黑猪肉馅,大白菜,前腿肉100%,甄选自黑猪,干净配方,速冻面米食品,生制品,含肉类,皮弹馅大,汁多肉好,手挑鲜嫩大白菜,每100g 794kJ≈190kcal,营养成分表见包装侧面,日期见包装侧面",
    "--photo", DEST,
], capture_output=True, text=True, encoding="utf-8")
print(r.stdout)
if r.stderr: print("STDERR:", r.stderr)

# === 3) ID 1026 鸡蛋 重写备注(从图 1 整盒 + 图 2 标签特写 提取全部) ===
print("\n" + "=" * 60)
print("[3] ID 1026 Member's Mark 鲜鸡蛋 重写备注")
print("=" * 60)
EGG_REMARK = (
    "山姆会员商店极速达,Member's Mark 精选鲜鸡蛋 30 枚 1.59kg 盒装。"
    "【品牌】Member's Mark(山姆自有品牌,始于1989,品质保证)。"
    "【产地】安徽宣城宁国(CZ = 生产商 3,安徽绩溪源庆农业)。"
    "【标准号】GB 2749(鲜蛋国标)。"
    "【保质期】30 天(从生产日起算)。"
    "【生产日期】2026-07-28(喷码 20260728)。"
    "【过期日期】2026-08-26(喷码 20260826,剩 27 天)。"
    "【储存】必须 2-6°C 冷藏(不是常温)。"
    "【特色】70 项抗生素检测合格;全产业链 5 个放心(母鸡放心/食粮放心/喂养放心/洁净放心/追溯放心);谷物饲养。"
    "【条形码】6931184503084。"
    "【购买日】2026-07-30(极速达订单,流水号 2607301659405561281000171,¥18.90)。"
    "【用途】家庭早餐/烘焙常用。建议 7-15 天内食用完以保最佳口感。"
)
r = subprocess.run([
    sys.executable, CLI, "update",
    "--id", "1026",
    "--remark", EGG_REMARK,
], capture_output=True, text=True, encoding="utf-8")
print(r.stdout)
if r.stderr: print("STDERR:", r.stderr)

# === 4) ID 1027 松饼 重写备注(从 4 张图提取全部 + 营养成分) ===
print("\n" + "=" * 60)
print("[4] ID 1027 Jimmy Dean 鸡排松饼 重写备注")
print("=" * 60)
JD_REMARK = (
    "山姆会员商店极速达,Jimmy Dean 美式鸡排松饼组合装,1.256kg(鸡排 696g + 松饼 560g),共 8 份(1 鸡排+1 松饼 = 1 count,鸡排和松饼分开装),盒装含铝箔。"
    "【品牌】Jimmy Dean(始于 1989,品质保证,Quality Guaranteed)。"
    "【经销商】泰森华东食品发展有限公司(江苏南通市海门区包场镇海泰路 58 号,021-24117699)。"
    "【生产商】鸡排:日照泰森食品有限公司(山东日照莒县,代码 TRZ);松饼:杭州谷斯宝特面包工业有限公司(浙江杭州余杭,代码 TNT)。"
    "【标准号】鸡排:SB/T 10379(速冻调制食品);松饼:GB 7099(糕点国标)。"
    "【保质期】9 个月。"
    "【生产日期】2026-04-23(TRZ6135)。"
    "【过期日期】2027-01-17(剩 5.5 月)。"
    "【储存】必须 -18°C 及以下冷冻贮存(冷藏会坏)。"
    "【工艺】鲜炸鸡排:冰鲜鸡胸肉炸制,鸡胸肉含量 ≥48%;黄油松饼:含法国进口黄油 ≥6%。"
    "【过敏源】含麸质/大豆/乳。"
    "【加热方式(均无需解冻)】①空气炸锅 200°C:鸡排 6min,加松饼翻面再 6min ②烤箱 180°C:同 6+6min ③松饼微波中火 30s ④鸡排油炸 165°C 5min。"
    "【食用提示】锡纸包裹食用(防松饼碎掉,内层为食品纸可接触热食,不可做复热辅助)。"
    "【营养成分(per 100g)】鸡排:178 kcal(744kJ)/14.4g 蛋白/7.2g 脂肪(饱 0.9g)/13.7g 碳水(糖 1.9g)/598mg 钠;松饼:426 kcal(1782kJ)/6.2g 蛋白/23.8g 脂肪(饱 13.5g)/46.8g 碳水(糖 4.9g)/746mg 钠。"
    "【条形码】6923146015261。"
    "【购买日】2026-07-30(¥59.90)。"
)
r = subprocess.run([
    sys.executable, CLI, "update",
    "--id", "1027",
    "--remark", JD_REMARK,
], capture_output=True, text=True, encoding="utf-8")
print(r.stdout)
if r.stderr: print("STDERR:", r.stderr)
