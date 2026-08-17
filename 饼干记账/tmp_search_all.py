# -*- coding: utf-8 -*-
"""
按 8/11-8/14 14 笔食物,每笔估算一份默认分量 + 查库匹配食物 + 算营养
"""
import json, subprocess, sys

# 14 笔(按时间排序)
items = [
    {"id": 7009, "time": "2026-08-11 12:55:00", "amount": -37.60, "name": "棒约翰牛肉多多披萨(美团外卖)", "default_grams": 350, "note": "9 寸薄底,1/3 个 + 吃 2-3 块(估)"},

    {"id": 7005, "time": "2026-08-11 20:45:19", "amount": -19.70, "name": "谢大冬·浇头拌面·馄饨锅贴(爆炒腰花拌面+猪肝)", "default_grams": 450, "note": "全吃完(默认估算)"},

    {"id": 7008, "time": "2026-08-11 21:05:00", "amount": -22.50, "name": "小仓生活可乐芬达饮料5瓶(闪购)", "default_grams": 1500, "note": "5 瓶 × 330ml 默认全喝"},

    {"id": 7006, "time": "2026-08-11 22:01:21", "amount": -19.00, "name": "港师傅菠萝包(榴莲忘返·榴莲+海盐乳酪)", "default_grams": 150, "note": "1 个"},

    {"id": 7002, "time": "2026-08-09 17:41:04", "amount": -31.99, "name": "潮州砂锅粥(牛肉炒米粉+海蛎煎蛋)", "default_grams": 500, "note": "全吃完(8/9 单实际是 8/9 时间,正确归属 8/9)"},

    {"id": 7011, "time": "2026-08-12 03:10:00", "amount": -17.30, "name": "谢大冬·浇头拌面·馄饨锅贴(青椒肉丝盖饭+卤蛋)", "default_grams": 450, "note": "全吃完(默认估算)"},

    {"id": 7019, "time": "2026-08-12 13:53:00", "amount": -15.89, "name": "印象长沙·山湘土菜(南京南站店)闪购 共1件", "default_grams": 400, "note": "全吃完"},

    {"id": 7020, "time": "2026-08-12 17:42:00", "amount": -38.90, "name": "棒约翰·0.1薄脆腊肠比萨(标准装)", "default_grams": 350, "note": "1/3 个 + 吃 2-3 块"},

    {"id": 7012, "time": "2026-08-13 11:48:58", "amount": -16.70, "name": "谢大冬·浇头拌面·馄饨锅贴(皮肚肥肠面)", "default_grams": 450, "note": "全吃完"},

    {"id": 7013, "time": "2026-08-13 18:21:13", "amount": -15.95, "name": "印象长沙·山湘土菜(攸县香干炒肉+香米饭套餐)", "default_grams": 400, "note": "全吃完"},

    {"id": 7014, "time": "2026-08-13 18:23:28", "amount": -17.90, "name": "印象长沙·山湘土菜(酸菜炒牛肉+香米饭套餐·给对象买的)", "default_grams": 0, "note": "⚠️ 给对象买的 · 自己没吃 · 跳过"},

    {"id": 7021, "time": "2026-08-14 13:12:00", "amount": -14.80, "name": "熊麻婆现炒浇头面·饭(辣皮子过油肉盖饭)闪购·花呗", "default_grams": 450, "note": "全吃完"},

    {"id": 7046, "time": "2026-08-14 18:44:15", "amount": -59.90, "name": "山姆极速达-海鲜烧烤组合(32串)500g", "default_grams": 500, "note": "全吃完"},

    {"id": 7047, "time": "2026-08-14 18:44:15", "amount": -84.90, "name": "山姆极速达-Member's Mark歌剧院蛋糕1*8s", "default_grams": 250, "note": "1 块 ~ 250g"},
]

# 查每条关键词(从 name 提取)
def search(q):
    r = subprocess.run(
        ['python', r'D:\2Study\StudyNotes\SKILLS\卡路里\scripts\calorie_tracker.py',
         'search-product', q],
        capture_output=True, text=True, encoding='utf-8'
    )
    return r.stdout

# 关键词映射
queries = {
    "棒约翰牛肉多多披萨": "披萨",
    "谢大冬·浇头拌面·馄饨锅贴(爆炒腰花拌面+猪肝)": "拌面",
    "小仓生活可乐芬达饮料5瓶": "可乐",
    "港师傅菠萝包(榴莲忘返·榴莲+海盐乳酪)": "菠萝包",
    "潮州砂锅粥(牛肉炒米粉+海蛎煎蛋)": "砂锅粥",
    "谢大冬·浇头拌面·馄饨锅贴(青椒肉丝盖饭+卤蛋)": "盖饭",
    "印象长沙·山湘土菜(南京南站店)闪购 共1件": "湘菜",
    "棒约翰·0.1薄脆腊肠比萨(标准装)": "披萨",
    "谢大冬·浇头拌面·馄饨锅贴(皮肚肥肠面)": "皮肚面",
    "印象长沙·山湘土菜(攸县香干炒肉+香米饭套餐)": "香干",
    "印象长沙·山湘土菜(酸菜炒牛肉+香米饭套餐·给对象买的)": "酸菜炒牛肉",
    "熊麻婆现炒浇头面·饭(辣皮子过油肉盖饭)闪购·花呗": "辣皮子过油肉",
    "山姆极速达-海鲜烧烤组合(32串)500g": "海鲜烧烤",
    "山姆极速达-Member's Mark歌剧院蛋糕1*8s": "蛋糕",
}

# 对每条查库取 top 1
print("=== 查库匹配 ===")
for name, q in queries.items():
    out = search(q)
    lines = out.split('\n')
    # 取第一行匹配产品(过 4 行表头)
    found = []
    for ln in lines:
        if '|' in ln and not ln.startswith('---') and 'ID' not in ln and '产品名称' not in ln and '找到' not in ln and not ln.startswith('\u2500'):
            parts = [p.strip() for p in ln.split('|') if p.strip()]
            if parts and parts[0].isdigit():
                found.append(parts)
                if len(found) >= 3:
                    break
    print(f"\n[{name}] -> 关键词: {q}")
    for f in found:
        print('  ', f)