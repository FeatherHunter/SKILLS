#!/usr/bin/env python3
"""卡路里 - CLI 入口

业务逻辑拆分到各领域模块（每个 ≤ 350 行）：
- diet.py           — 饮食记录（add_meal / delete_meal / list_meals / get_daily_summary）
- water.py          — 饮水记录（add_water）
- nutrition_goal.py — 每日营养目标（set_nutrition_goal / get_nutrition_goal）
- weight.py         — 体重记录（log_weight / update_weight / get_weight_history）
- weight_goal.py    — 体重目标（set_weight_goal / get_weight_goal / print_goal_progress）
- exercise.py       — 运动记录（add_exercise / get_exercise_log / print_exercise_summary）
- product_library.py — 食品库 CRUD（add_product / search_products / update_product / list_products）
- calorie_history.py — 热量历史（get_calorie_history）
- db.py             — 数据库基础（find_db_path / connection / get_db / init_db）

更完整的 CLI（带 update/list/stats/trend 等子命令）见：
- exercise_tracker.py
- fitness_goals.py
- sleep_tracker.py
- body_photo_tracker.py
"""

import sys
from datetime import date, datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 业务模块导入
import diet
import water
import nutrition_goal
import weight
import weight_goal
import exercise
import product_library
import calorie_history


def _parse_kw_args(args):
    """解析 --key value 风格的参数为 dict

    注意：value 不能以 -- 开头，否则视为 flag
    """
    kwargs = {}
    i = 0
    while i < len(args):
        if args[i].startswith('--'):
            key = args[i][2:]
            if i + 1 < len(args) and not args[i+1].startswith('--'):
                kwargs[key] = args[i+1]
                i += 2
            else:
                i += 1
        else:
            i += 1
    return kwargs


def usage():
    """Print usage information"""
    print("""
卡路里 - 用法

命令：
  add <食物> <卡路里> <蛋白质> [碳水] [脂肪] [克数] [备注]
                                   添加食物记录（可用 --date / --time / --meal 补录历史）
  delete <id>                       删除记录
  list                              列出今日记录
  summary                           今日摘要
  goal <热量> <蛋白> <碳水> <脂肪> [饮水ml]
                                   设置每日目标
  water <ml> [--date YYYY-MM-DD]    记录饮水
  weight <公斤> <身高cm> [备注]     记录体重（身高必传）
  weight-update <id> [--weight <kg>] [--height <身高cm>] [--note <备注>]
                                   更新体重记录
  weight-history [天数]             体重历史（默认30天）
  weight-goal <kg> [截止日期 YYYY-MM-DD]
                                   设置体重目标
  weight-goal-progress              查看体重目标进度
  exercise-add <类型> <卡> [--minutes N] [--reps N]
                                   记录运动
  exercise-summary [--days N]       运动汇总（默认7天）
  history [天数]                    热量历史（默认7天）

  add-product <名称> <品牌> <热量> <蛋白质> <脂肪> <饱和脂肪> <碳水> <糖> <膳食纤维> <钠> [备注]
                                   添加食品营养成分表
  search-product <关键词>           搜索营养成分
  update-product <id> [--字段 值]   更新营养成分
  list-products [数量]              列出所有营养成分

示例：
  add "鸡胸肉" 165 31 0 3 150
  add "面包" 150 3 20 5 80 --date 2026-06-20 --time 15:00 --meal 午餐
  goal 1800 150 200 50 2000
  water 500
  weight 70 178
  weight-goal 73 2026-07-01
  add-product "可口可乐" "可口可乐" 42 0 0 0 10.6 10.6 0 20 "经典款330ml"
  search-product "可乐"
  update-product 1 --calories 45 --note "更新包装"
""")


def main():
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    command = sys.argv[1]

    try:
        if command == "add":
            if len(sys.argv) < 5:
                print("Error: add requires <food> <calories> <protein> [carbs] [fat] [grams] [note]")
                print("  用法: add <食物> <热量> <蛋白> [碳水] [脂肪] [克数] [备注] [--date YYYY-MM-DD] [--time HH:MM] [--meal 餐次]")
                print("  示例: add \"鸡胸肉\" 165 31 0 3 150")
                print("  示例: add \"面包\" 150 3 20 5 80 --date 2026-06-20 --time 15:00 --meal 午餐")
                sys.exit(1)

            positional = []
            args = sys.argv[2:]
            kw_args = []
            i = 0
            while i < len(args):
                if args[i].startswith('--'):
                    kw_args.append(args[i])
                    i += 1
                else:
                    positional.append(args[i])
                    i += 1

            food = positional[0] if len(positional) > 0 else None
            calories = positional[1] if len(positional) > 1 else None
            protein = positional[2] if len(positional) > 2 else None
            carbs = positional[3] if len(positional) > 3 else '0'
            fat = positional[4] if len(positional) > 4 else '0'
            grams = positional[5] if len(positional) > 5 else '100'
            note = positional[6] if len(positional) > 6 else ''

            if not food or not calories or not protein:
                print("Error: 食物、热量、蛋白质为必填参数")
                sys.exit(1)

            kwargs = _parse_kw_args(kw_args)
            diet.add_meal(
                food, calories, protein, carbs, fat, grams, note,
                target_date=kwargs.get('date'),
                target_time=kwargs.get('time'),
                meal_override=kwargs.get('meal'),
            )

        elif command == "delete":
            if len(sys.argv) < 3:
                print("Error: delete requires <id>")
                sys.exit(1)
            diet.delete_meal(sys.argv[2])

        elif command == "list":
            diet.list_meals()

        elif command == "summary":
            diet.get_daily_summary()

        elif command == "water":
            if len(sys.argv) < 3:
                print("Error: water requires <ml>")
                print("  用法: water <ml> [--date YYYY-MM-DD]")
                print("  示例: water 500")
                print("  示例: water 500 --date 2026-06-20")
                sys.exit(1)
            kwargs = _parse_kw_args(sys.argv[3:])
            water.add_water(sys.argv[2], target_date=kwargs.get('date'))

        elif command == "goal":
            if len(sys.argv) < 6:
                print("Error: goal 必须 4 个参数全传（v2.2 修改）")
                print("  用法: goal <热量> <蛋白> <碳水> <脂肪> [饮水ml]")
                print("  示例: goal 1850 150 200 50 2000")
                sys.exit(1)
            nutrition_goal.set_nutrition_goal(
                sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5],
                sys.argv[6] if len(sys.argv) > 6 else None,
            )

        elif command == "weight":
            if len(sys.argv) < 4:
                print("Error: weight requires <kg> <height_cm> [note]")
                print("  用法: weight <公斤> <身高cm> [备注]")
                print("  示例: weight 70 178")
                sys.exit(1)
            note = sys.argv[4] if len(sys.argv) > 4 else ''
            weight.log_weight(sys.argv[2], sys.argv[3], note)

        elif command == "weight-update":
            if len(sys.argv) < 3:
                print("Error: weight-update requires <id> [--weight <公斤>] [--height <身高cm>] [--note <备注>]")
                sys.exit(1)
            kwargs = _parse_kw_args(sys.argv[3:])
            weight.update_weight(
                sys.argv[2],
                weight_kg=kwargs.get('weight'),
                height_cm=kwargs.get('height'),
                note=kwargs.get('note'),
            )

        elif command == "weight-history":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            weight.get_weight_history(days)

        elif command == "weight-goal":
            if len(sys.argv) < 3:
                print("Error: weight-goal requires <kg> [deadline YYYY-MM-DD]")
                sys.exit(1)
            deadline = sys.argv[3] if len(sys.argv) > 3 else None
            weight_goal.set_weight_goal(sys.argv[2], deadline)

        elif command == "weight-goal-progress":
            weight_goal.print_goal_progress()

        elif command == "exercise-add":
            if len(sys.argv) < 4:
                print("Error: exercise-add requires <type> <calories> [--minutes N] [--reps N] [--note ...]")
                print("  示例: exercise-add 骑行 300 --minutes 40")
                sys.exit(1)
            kwargs = _parse_kw_args(sys.argv[4:])
            exercise.add_exercise(
                sys.argv[2], sys.argv[3],
                duration_minutes=kwargs.get('minutes'),
                reps=kwargs.get('reps'),
                note=kwargs.get('note', ''),
            )

        elif command == "exercise-summary":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
            exercise.print_exercise_summary(days)

        elif command == "history":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
            calorie_history.get_calorie_history(days)

        elif command == "add-product":
            if len(sys.argv) < 11:
                print("Error: add-product requires <name> <brand> <cal> <protein> <fat> <saturated_fat> <carbs> <sugar> <fiber> <sodium> [note]")
                sys.exit(1)
            note = sys.argv[12] if len(sys.argv) > 12 else ''
            product_library.add_product(
                sys.argv[2], sys.argv[3],
                float(sys.argv[4]), float(sys.argv[5]), float(sys.argv[6]),
                float(sys.argv[7]) or None,
                float(sys.argv[8]), float(sys.argv[9]) or None,
                float(sys.argv[10]) or None,
                float(sys.argv[11]),
                note,
            )

        elif command == "search-product":
            if len(sys.argv) < 3:
                print("Error: search-product requires <keyword>")
                sys.exit(1)
            product_library.search_products(sys.argv[2])

        elif command == "update-product":
            if len(sys.argv) < 3:
                print("Error: update-product requires <product_id> [--field value ...]")
                sys.exit(1)
            kwargs = _parse_kw_args(sys.argv[3:])
            product_library.update_product(sys.argv[2], **kwargs)

        elif command == "list-products":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
            product_library.list_products(limit)

        else:
            print(f"Error: Unknown command '{command}'")
            usage()
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()