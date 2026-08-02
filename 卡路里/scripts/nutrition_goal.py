#!/usr/bin/env python3
"""每日营养目标 — 热量/蛋白/碳水/脂肪/饮水

数据存储：daily_goal 表（固定 id=1）
- calorie_goal / protein_goal / carbs_goal / fat_goal — 四大营养目标
- water_goal — 饮水目标（v2.2 新增）
- weight_goal / goal_deadline — 体重目标（被 weight_goal.py 写）

设置约束（v2.2 修改）：
- 必须 4 参全传（calorie/protein/carbs/fat）
- 第 5 参可选饮水
- 自洽性校验：蛋白*4 + 碳*4 + 脂*9 vs 热量目标，相差 > 50 卡给警告
"""

import sys
from pathlib import Path

from db import find_db_path, get_db, init_db

try:
    from analysis._utils import get_activity_factor  # TDEE 活动系数唯一来源(ticket #8)
except Exception:
    def get_activity_factor(level=None):
        return 1.55

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "calorie_data.db"
DB_PATH = find_db_path(SKILL_DIR, DB_FILENAME)


def _get_db():
    if not DB_PATH.exists():
        init_db(DB_PATH)
    return get_db(DB_PATH)


def set_nutrition_goal(calorie_goal, protein_goal, carbs_goal, fat_goal, water_goal=None):
    """设置每日营养目标（v2.2 支持饮水目标）

    Args:
        calorie_goal: 热量目标（卡）
        protein_goal: 蛋白质目标（克）
        carbs_goal: 碳水目标（克）
        fat_goal: 脂肪目标（克）
        water_goal: 饮水目标（ml），可选
    """
    # 强制 4 参检查
    if None in (protein_goal, carbs_goal, fat_goal):
        print("Error: goal 必须 4 个参数全传")
        print("  用法: goal <热量> <蛋白> <碳水> <脂肪> [饮水ml]")
        print("  示例: goal 1850 150 200 50 2000")
        return False

    try:
        calorie_goal = int(calorie_goal)
        protein_goal = int(protein_goal)
        carbs_goal = int(carbs_goal)
        fat_goal = int(fat_goal)
        if calorie_goal <= 0:
            print("Error: 热量目标必须为正数")
            return False
        if protein_goal < 0 or carbs_goal < 0 or fat_goal < 0:
            print("Error: 营养目标不能为负数")
            return False
    except ValueError:
        print("Error: 参数必须是数字")
        return False

    if water_goal is not None:
        try:
            water_goal = int(water_goal)
            if water_goal < 0:
                print("Error: 饮水目标不能为负数")
                return False
        except ValueError:
            print("Error: 饮水目标必须是数字")
            return False

    # 自洽性提示
    calculated = protein_goal * 4 + carbs_goal * 4 + fat_goal * 9
    diff = calculated - calorie_goal

    conn = _get_db()
    c = conn.cursor()

    if water_goal is not None:
        c.execute('''
            INSERT OR REPLACE INTO daily_goal (id, calorie_goal, protein_goal, carbs_goal, fat_goal, water_goal, updated_at)
            VALUES (1, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (calorie_goal, protein_goal, carbs_goal, fat_goal, water_goal))
    else:
        c.execute('''
            INSERT OR REPLACE INTO daily_goal (id, calorie_goal, protein_goal, carbs_goal, fat_goal, updated_at)
            VALUES (1, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (calorie_goal, protein_goal, carbs_goal, fat_goal))

    conn.commit()
    conn.close()

    print(f"✓ 每日目标已设置：")
    print(f"  热量：{calorie_goal}卡")
    print(f"  蛋白质：{protein_goal}克")
    print(f"  碳水：{carbs_goal}克")
    print(f"  脂肪：{fat_goal}克")
    if water_goal is not None:
        print(f"  饮水：{water_goal}ml")
    if abs(diff) <= 50:
        print(f"  自洽性：换算 {calculated} 卡（差异 {diff:+d}）✅")
    return True


def get_nutrition_goal():
    """获取每日目标（返回 sqlite3.Row 或 None）

    列顺序：id, calorie_goal, protein_goal, carbs_goal, fat_goal,
            weight_goal, goal_deadline, water_goal, updated_at
    """
    conn = _get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM daily_goal WHERE id = 1')
    row = c.fetchone()
    conn.close()
    return row


# ============ G1.2 智能推荐（ticket 06 · 遗留决策 #1 默认参数）============
# cut -500 / maintain 0 / bulk +400 kcal；protein 2.0/1.6/1.8 g/kg；
# water 35/30/30 ml/kg；fat 25%/30%/25%
PROFILES = {
    'cut':      {'calorie_adj': -500, 'protein_g_per_kg': 2.0, 'water_ml_per_kg': 35, 'fat_pct': 0.25},
    'maintain': {'calorie_adj': 0,    'protein_g_per_kg': 1.6, 'water_ml_per_kg': 30, 'fat_pct': 0.30},
    'bulk':     {'calorie_adj': +400, 'protein_g_per_kg': 1.8, 'water_ml_per_kg': 30, 'fat_pct': 0.25},
}
PROFILE_LABELS = {'cut': '减脂', 'maintain': '维持', 'bulk': '增肌'}
# 每周减重速率（kg/周）≈ 热量缺口 × 7 / 7700
PROFILE_WEEKLY_RATE = {'cut': 0.5, 'maintain': 0.0, 'bulk': 0.4}


def _latest_weight_kg():
    """读最新体重（kg）；无记录返回 None"""
    conn = _get_db()
    try:
        row = conn.execute('SELECT weight_kg FROM weight_log ORDER BY date DESC, id DESC LIMIT 1').fetchone()
    except Exception:
        row = None
    conn.close()
    return row[0] if row else None


def _profile_basis(weight_kg, height_cm, age, gender):
    """从 user_profile 读档案，缺字段用默认值 + 标记缺省"""
    defaults = {'weight_kg': weight_kg, 'height_cm': height_cm, 'age': age, 'gender': gender,
                'activity_level': 'moderate'}
    missing = []
    conn = _get_db()
    try:
        row = conn.execute('SELECT age, gender, height_cm, activity_level FROM user_profile WHERE id = 1').fetchone()
    except Exception:
        row = None
    conn.close()
    if row:
        if row['age'] is not None:
            defaults['age'] = row['age']
        else:
            missing.append('年龄')
        if row['gender'] is not None:
            defaults['gender'] = row['gender']
        else:
            missing.append('性别')
        if row['height_cm'] is not None:
            defaults['height_cm'] = row['height_cm']
        else:
            missing.append('身高')
        defaults['activity_level'] = row['activity_level'] or 'moderate'
    else:
        missing = ['年龄', '性别', '身高']
    if defaults['weight_kg'] is None:
        missing.append('体重')
    return defaults, missing


def recommend_nutrition_goal(profile='cut', weight_kg=None, height_cm=None, age=None, gender=None):
    """G1.2 AI 智能推荐：3 套模板（cut/maintain/bulk）+ 1 定制

    Args:
        profile: 'cut' / 'maintain' / 'bulk'
        weight_kg / height_cm / age / gender: 显式覆盖档案（AI 定制时传）

    Returns:
        dict {profile, tdee, calorie_goal, protein_goal, carbs_goal, fat_goal,
              water_goal, weekly_rate_kg, basis, plan_reasons, missing}
    """
    if profile not in PROFILES:
        raise ValueError(f"profile 必须是 {sorted(PROFILES)} 之一，实得 {profile!r}")

    if weight_kg is None:
        weight_kg = _latest_weight_kg()
    defaults, missing = _profile_basis(weight_kg, height_cm, age, gender)

    w = defaults['weight_kg'] or 70.0
    h = defaults['height_cm'] or 175.0
    a = defaults['age'] or 30
    g = defaults['gender'] or 'male'

    # BMR（Mifflin-St Jeor）+ TDEE（activity 系数读 user_profile.activity_level · ticket #8）
    bmr = 10 * w + 6.25 * h - 5 * a + (5 if g == 'male' else -161)
    tdee = bmr * get_activity_factor(defaults['activity_level'])

    p = PROFILES[profile]
    cal = int(tdee + p['calorie_adj'])
    protein = int(w * p['protein_g_per_kg'])
    fat = int(cal * p['fat_pct'] / 9)
    carbs = max(int((cal - protein * 4 - fat * 9) / 4), 0)
    water = int(w * p['water_ml_per_kg'])

    # 卡路里校验（自洽性）：蛋白×4 + 碳×4 + 脂×9 vs 热量目标
    calculated = protein * 4 + carbs * 4 + fat * 9
    diff = calculated - cal

    reasons = [
        f"{PROFILE_LABELS[profile]}模板：TDEE {int(tdee)} 卡 × 热量调整 {p['calorie_adj']:+d} 卡 → 每日 {cal} 卡",
        f"蛋白 {protein} g（体重 {w:.1f} kg × {p['protein_g_per_kg']} g/kg）",
        f"脂肪 {fat} g（占热量 {int(p['fat_pct']*100)}%）· 碳水 {carbs} g（余量）",
        f"饮水 {water} ml（体重 × {p['water_ml_per_kg']} ml/kg）",
        f"预计每周减重速率 {PROFILE_WEEKLY_RATE[profile]:.1f} kg（Δ{cal} - TDEE {int(tdee)}）",
    ]
    if abs(diff) > 50:
        reasons.append(f"⚠️ 自洽性校验：宏量换算 {calculated} 卡，与热量目标差 {diff:+d} 卡（>50 建议复核）")

    return {
        'profile': profile,
        'profile_label': PROFILE_LABELS[profile],
        'tdee': int(tdee),
        'bmr': int(bmr),
        'calorie_goal': cal,
        'protein_goal': protein,
        'carbs_goal': carbs,
        'fat_goal': fat,
        'water_goal': water,
        'weekly_rate_kg': PROFILE_WEEKLY_RATE[profile],
        'basis': {'weight_kg': round(w, 1), 'height_cm': h, 'age': a, 'gender': g},
        'plan_reasons': reasons,
        'missing': missing,
        'self_check': {'calculated_kcal': calculated, 'diff_kcal': diff},
    }


def recommend_water_goal(weight_kg=None, season=None):
    """G1.7 定饮水目标（自动算）：按体重 + 季节推推荐值

    Args:
        weight_kg: 体重（默认取最新记录）
        season: '夏' / '冬' / None（按月份推断）

    Returns:
        dict {weight_kg, season, recommended_water_ml, basis, old_water_goal}
    """
    if weight_kg is None:
        weight_kg = _latest_weight_kg()
    w = weight_kg or 70.0

    if season is None:
        import datetime
        month = datetime.date.today().month
        season = '夏' if month in (6, 7, 8, 9) else '冬'
    ml_per_kg = 35 if season == '夏' else 30
    recommended = int(w * ml_per_kg)

    old = None
    row = get_nutrition_goal()
    if row is not None:
        old = row['water_goal']

    return {
        'weight_kg': round(w, 1),
        'season': season,
        'ml_per_kg': ml_per_kg,
        'recommended_water_ml': recommended,
        'old_water_goal': old,
        'basis': f"体重 {w:.1f} kg × {ml_per_kg} ml/kg（{'夏季偏高' if season == '夏' else '冬季常规'}）",
    }


def update_water_goal(water_goal):
    """G3.3 改饮水目标（单独）：只改 water_goal，其他 4 项宏量不动

    Args:
        water_goal: 新饮水目标（ml）

    Returns:
        dict {id, updated_at, rows_affected, old_water_goal, new_water_goal} 或 None(校验失败)
    """
    try:
        water_goal = int(water_goal)
        if water_goal < 0:
            print("Error: 饮水目标不能为负数")
            return None
    except ValueError:
        print("Error: 饮水目标必须是数字")
        return None

    old = None
    row = get_nutrition_goal()
    if row is not None:
        old = row['water_goal']

    conn = _get_db()
    c = conn.cursor()
    c.execute('''
        UPDATE daily_goal
        SET water_goal = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
    ''', (water_goal,))
    rows_affected = c.rowcount
    conn.commit()
    c.execute('SELECT id, updated_at FROM daily_goal WHERE id = 1')
    r = c.fetchone()
    conn.close()
    return {
        'id': r[0] if r else 1,
        'updated_at': r[1] if r else None,
        'rows_affected': rows_affected,
        'old_water_goal': old,
        'new_water_goal': water_goal,
    }