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
- body_photo_tracker.py
"""

import sys
from datetime import date, datetime
from pathlib import Path

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

# 复盘模块(Q16=B 多子命令:review --gen / --send / --archive / --full)
import review_engine
import review_prompts
import review_feishu


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
  update-meal <id> [--grams <克数>] [--food <食物名>] [--note <备注>]
                                   更新饮食记录（克数/食物名/备注）
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
                    # 同时把 value 也加入 kw_args（如果下一个不是 --flag）
                    if i + 1 < len(args) and not args[i+1].startswith('--'):
                        kw_args.append(args[i+1])
                        i += 2
                    else:
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
                food, calories, protein, carbs, fat, grams,
                kwargs.get('note') or note,
                target_date=kwargs.get('date'),
                target_time=kwargs.get('time'),
                meal_override=kwargs.get('meal'),
            )

        elif command == "delete":
            if len(sys.argv) < 3:
                print("Error: delete requires <id>")
                sys.exit(1)
            diet.delete_meal(sys.argv[2])

        elif command == "update-meal":
            if len(sys.argv) < 3:
                print("Error: update-meal requires <id> [--grams <克数>] [--food <食物名>] [--note <备注>]")
                sys.exit(1)
            kwargs = _parse_kw_args(sys.argv[3:])
            diet.update_meal(
                sys.argv[2],
                grams=kwargs.get('grams'),
                food_name=kwargs.get('food'),
                note=kwargs.get('note'),
            )

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

        elif command == "review":
            # 复盘子命令(Q16=B 多子命令)
            #   review --gen [--range X:Y] [--type day|week|month|year]
            #       → 生成 HTML(LLM 装填 review.html 模板)
            #   review --send --html-path <path>
            #       → 从 HTML 提取 3+3+3,LLM 生成飞书消息,发送
            #   review --archive --html-path <path>
            #       → 上传 HTML 到飞书云盘,返回 URL
            #   review --full [--range X:Y] [--type ...]  # 默认行为
            #       → gen + archive + send 全跑

            if len(sys.argv) < 3:
                print("Error: review 需要子命令 --gen / --send / --archive / --full")
                print("  用法:")
                print("    review --full [--range 2026-07-08:2026-07-14] [--type week]")
                print("    review --gen  [--range X:Y] [--type day|week|month|year]")
                print("    review --archive --html-path <path>")
                print("    review --send --html-path <path>")
                sys.exit(1)

            sub = sys.argv[2]
            kw = _parse_kw_args(sys.argv[3:])

            if sub == '--gen':
                _review_gen(kw)
            elif sub == '--archive':
                _review_archive(kw)
            elif sub == '--send':
                _review_send(kw)
            elif sub == '--full':
                # 全跑:gen → archive → send
                html_path = _review_gen(kw)
                url = _review_archive({'html-path': str(html_path)})
                _review_send({'html-path': str(html_path), 'feishu-url': url})
            else:
                print(f"Error: review 子命令 '{sub}' 未知")
                sys.exit(1)

        else:
            print(f"Error: Unknown command '{command}'")
            usage()
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


# ==================== 复盘子命令实现 ====================

def _review_gen(kw: dict) -> Path:
    """生成复盘 HTML(LLM 装填 review.html 模板)

    Args:
        kw: 包含 --range / --type

    Returns:
        Path: 生成的 HTML 文件路径(系统 temp 目录)
    """
    import tempfile

    # 1. 解析时间范围
    range_arg = kw.get('range')
    range_type = kw.get('type', 'week')
    start, end = review_engine.parse_range(range_arg, range_type)
    print(f"→ 时间范围: {start} 至 {end}")

    # 2. 查询 5 维原始数据
    skill_dir = Path(__file__).parent.parent
    raw_data = review_engine.query_5dims(start, end, skill_dir)
    print(f"→ 数据查询完毕: {len(raw_data['daily_intake'])} 天摄入, "
          f"{len(raw_data['daily_burn'])} 天运动, "
          f"{len(raw_data['weight_logs'])} 条体重")

    # 3. 衍生计算
    enriched = review_engine.derive(raw_data)
    print(f"→ 衍生计算: TDEE={enriched['tdee']}, "
          f"周缺口={enriched['weekly_deficit']}, "
          f"理论减重={enriched['theoretical_weight_loss']}kg")

    # 4. 拼 prompt + 调 LLM
    prompt = review_prompts.build_html_prompt(enriched)
    print("→ 调 LLM 装填 review.html...")
    html_output = review_prompts.call_llm(prompt)

    # 5. 保存到系统 temp 目录(Q17=C)
    temp_dir = Path(tempfile.gettempdir()) / 'calorie_reviews'
    temp_dir.mkdir(parents=True, exist_ok=True)
    html_path = temp_dir / f'review_{start}_{end}.html'
    html_path.write_text(html_output, encoding='utf-8')
    print(f"✓ HTML 已生成: {html_path}")

    return html_path


def _review_archive(kw: dict) -> str:
    """上传 HTML 到飞书云盘

    Args:
        kw: 包含 --html-path

    Returns:
        str: 飞书云盘链接
    """
    html_path = kw.get('html-path')
    if not html_path:
        print("Error: --archive 需要 --html-path 参数")
        sys.exit(1)

    print(f"→ 上传 {html_path} 到飞书云盘...")
    url = review_feishu.upload_to_feishu_drive(html_path)
    print(f"✓ 飞书链接: {url}")
    return url


def _review_send(kw: dict) -> None:
    """从 HTML 提取摘要,LLM 生成飞书消息,发送

    Args:
        kw: 包含 --html-path 和 --feishu-url
    """
    html_path = kw.get('html-path')
    feishu_url = kw.get('feishu-url', '')
    if not html_path:
        print("Error: --send 需要 --html-path 参数")
        sys.exit(1)

    html_path = Path(html_path)
    if not html_path.exists():
        print(f"Error: HTML 文件不存在: {html_path}")
        sys.exit(1)

    # 1. 提取摘要
    html_output = html_path.read_text(encoding='utf-8')
    summary = review_engine.extract_summary(html_output)
    print(f"→ 摘要提取: {summary['date_range']}")

    # 2. LLM 生成飞书消息
    feishu_prompt = review_prompts.build_feishu_prompt(summary, feishu_url)
    print("→ 调 LLM 生成飞书消息...")
    feishu_text = review_prompts.call_llm(feishu_prompt)

    # 3. 替换模板里的占位符
    # LLM 输出格式: 完整模板字符串,占位符仍是 {{xxx}}
    # 直接用 fill_template 函数替换
    final_text = _fill_feishu_template(feishu_text, summary, feishu_url)

    # 4. 发送
    print("→ 发送飞书...")
    success = review_feishu.send_feishu(final_text)
    if success:
        print("✓ 飞书消息发送成功")
    else:
        print("✗ 飞书消息发送失败")
        sys.exit(1)


def _fill_feishu_template(template: str, summary: dict, feishu_url: str) -> str:
    """把 {{xxx}} 占位符替换为实际值"""
    result = template
    for key, value in summary.items():
        result = result.replace('{{' + key + '}}', str(value))
    result = result.replace('{{feishu_url}}', feishu_url)
    return result


if __name__ == "__main__":
    main()