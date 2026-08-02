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

import subprocess
import sys
from datetime import date, datetime, timedelta
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
import profile
import review_cli




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


def _parse_render_path(stdout_text):
    """从 render_*.py 脚本 stdout 中解析出 HTML 输出路径

    render 脚本固定输出首行为 `✅ <path>`,本函数提取该路径;
    找不到则返回 None,调用方走 fallback 纯文本。
    """
    if not stdout_text:
        return None
    for line in stdout_text.splitlines():
        line = line.strip()
        if line.startswith('✅ '):
            # ✅ D:/.db/calorie_html/今日饮食_20260726_123000.html
            return Path(line[2:].strip())
    return None


def usage():
    """Print usage information"""
    print("""
卡路里 - 用法

命令：
  add <食物> <卡路里> <蛋白质> [碳水] [脂肪] [克数] [备注]
                                   添加食物记录（可用 --date / --time / --meal 补录历史）
  copy-meals [--from D] [--to D]   复制某日饮食到另一日(默认昨天→今天)
  add-meal-batch --input <json>    批量补记饮食(一次录多餐)
  delete <id>                       删除记录
  update-meal <id> [--grams <克数>] [--food <食物名>] [--note <备注>]
                                   更新饮食记录（克数/食物名/备注）
  update-meals-by-date <date> [--field value ...]
                                   按日期批量改某日饮食
  delete-meal-by-type <date> <餐别> 删一餐(早餐/午餐/下午茶/晚餐/夜宵/加餐)
  delete-meals-by-date <date>       删某日饮食(一整天清空)
  delete-meals-by-range <start> <end>
                                   按日期范围批量删饮食
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
  deprecate-product <id>            下架食品(标废弃,查询不再出现)
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


def _sub_help(args: list[str], usage_text: str) -> None:
    """subcommand 级别 --help / -h 检测(Phase 3b · ticket 04 ticket 09 增量)

    若 args 含 --help / -h,print usage + exit 0。
    所有走 CLI 的子命令开头都用一下,实现"全 CLI 支持 --help"。
    """
    if "--help" in args or "-h" in args:
        print(usage_text)
        sys.exit(0)


def main():
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    command = sys.argv[1]

    # ADR-0004 · ticket 04: 顶层 --help / -h 立即返回 usage
    if command in ("--help", "-h", "help"):
        usage()
        sys.exit(0)

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
            # v2.4.16 改:符合 V1.0 §02 第②特性"回执 = ID + 时间戳 + 影响行数"
            receipt = diet.add_meal(
                food, calories, protein, carbs, fat, grams,
                kwargs.get('note') or note,
                target_date=kwargs.get('date'),
                target_time=kwargs.get('time'),
                meal_override=kwargs.get('meal'),
            )
            if receipt is None:
                sys.exit(1)
            print(f"✓ 饮食已记录 (id={receipt['id']}, 影响 {receipt['rows_affected']} 行)")
            print(f"  日期: {receipt['date']} {receipt['time']} | 餐次: {receipt['meal']}")
            print(f"  {receipt['food_name']} ({receipt['calories']}卡, {receipt['protein']}蛋白, {receipt['grams']}克)")
            if receipt['cal_goal']:
                rem = receipt['remaining_cal'] or 0
                marker = '剩余' if rem > 0 else '超标'
                print(f"  {receipt['date_label']}: {receipt['today_total_cal']}/{receipt['cal_goal']}卡 | {marker} {abs(rem):.0f}卡")

        elif command == "delete":
            if len(sys.argv) < 3:
                print("Error: delete requires <id>")
                sys.exit(1)
            diet.delete_meal(sys.argv[2])

        elif command == "update-meal":
            if len(sys.argv) < 3:
                print("Error: update-meal requires <id> [+可选字段]")
                print("  支持(至少传 1 个):")
                print("    --grams N           克数")
                print("    --food NAME         食物名")
                print("    --calories N        热量(卡)")
                print("    --protein N         蛋白(克)")
                print("    --carbs N           碳水(克)")
                print("    --fat N             脂肪(克)")
                print("    --date YYYY-MM-DD   日期")
                print("    --time HH:MM        时间")
                print("    --note X            备注")
                print("  (餐次 meal_type 从 time 自动推断,不需传)")
                print("  示例:")
                print("    update-meal 5 --calories 180")
                print("    update-meal 5 --calories 180 --protein 15 --carbs 30 --fat 8")
                print("    update-meal 5 --date 2026-07-20 --time 18:30")
                sys.exit(1)
            parsed = _parse_kw_args(sys.argv[3:])
            field_map = {
                'grams': 'grams',
                'food': 'food_name',
                'calories': 'calories',
                'protein': 'protein',
                'carbs': 'carbs',
                'fat': 'fat',
                'date': 'date',
                'time': 'time',
                'note': 'note',
            }
            # 检测非法 CLI 参数 → 明确报错(v2.2.0 改进)
            unknown = set(parsed) - set(field_map)
            if unknown:
                print(f"Error: 不识别的字段: {sorted(unknown)}")
                print(f"  支持: {sorted(field_map)}")
                sys.exit(1)
            kwargs = {field_map[k]: v for k, v in parsed.items() if k in field_map}
            result = diet.update_meal(sys.argv[2], **kwargs)
            if not result["ok"]:
                print(f"Error: {result['error']}")
                sys.exit(1)

        elif command == "list":
            # v2.4.6:接通 render_today_meals.py(V1.3 §04 协议 — 有 HTML 模板必走 HTML)
            # v2.4.8:不传 --output,由 render 走 html_path() 新规范(中文 + 时间戳)
            # 默认 list 是"查今天吃" → 生成 HTML;render 失败 fallback 纯文本
            render_proc = subprocess.run(
                [sys.executable, 'scripts/render_today_meals.py'],
                capture_output=True, text=True, encoding='utf-8', timeout=15,
            )
            tmp = _parse_render_path(render_proc.stdout) if render_proc.returncode == 0 else None
            if tmp and tmp.exists():
                print(f"\n✅ HTML 已生成(查今天吃): {tmp}")
                print(f"⚠️ ACTION=SEND_TO_USER | HTML={tmp.absolute()}")
            else:
                print(f"⚠️ render 失败,回退纯文本(fallback):")
                if render_proc.stderr:
                    print(f"  stderr: {render_proc.stderr.strip()[:200]}")
            diet.list_meals()  # 始终 print 纯文本(向后兼容)

        elif command == "summary":
            # v2.4.6:接通 render_today_diet.py(查今日摘要)
            # v2.4.8:不传 --output,由 render 走 html_path() 新规范
            render_proc = subprocess.run(
                [sys.executable, 'scripts/render_today_diet.py'],
                capture_output=True, text=True, encoding='utf-8', timeout=15,
            )
            tmp = _parse_render_path(render_proc.stdout) if render_proc.returncode == 0 else None
            if tmp and tmp.exists():
                print(f"\n✅ HTML 已生成(查今日摘要): {tmp}")
                print(f"⚠️ ACTION=SEND_TO_USER | HTML={tmp.absolute()}")
            else:
                print(f"⚠️ render 失败,回退纯文本(fallback):")
                if render_proc.stderr:
                    print(f"  stderr: {render_proc.stderr.strip()[:200]}")
            diet.get_daily_summary()  # fallback 纯文本

        elif command == "water":
            if len(sys.argv) < 3:
                print("Error: water requires <ml>")
                print("  用法: water <ml> [--date YYYY-MM-DD]")
                print("  示例: water 500")
                print("  示例: water 500 --date 2026-06-20")
                sys.exit(1)
            kwargs = _parse_kw_args(sys.argv[3:])
            # v2.4.16 改:符合 V1.0 §02 第②特性"回执 = ID + 时间戳 + 影响行数"
            receipt = water.add_water(sys.argv[2], target_date=kwargs.get('date'))
            if receipt is None:
                sys.exit(1)
            print(f"✓ 饮水已记录 (id={receipt['id']}, 影响 {receipt['rows_affected']} 行)")
            print(f"  日期: {receipt['date']} {receipt['time']}")
            print(f"  本次: {receipt['ml']} ml")
            date_label = '今日' if not kwargs.get('date') else receipt['date']
            print(f"  {date_label}累计: {receipt['today_total_ml']}/{receipt['water_goal_ml']} ml | 剩余 {receipt['remaining_ml']:+} ml")

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

        elif command == "get-goal":
            # ticket 06 · P0 空挂修复:业务函数已有,CLI 层接通(get-goal 之前不存在)
            goal = nutrition_goal.get_nutrition_goal()
            if goal is None:
                print("⚠️ 未设置营养目标(请先执行 goal <热量> <蛋白> <碳水> <脂肪> [饮水ml])")
                sys.exit(0)
            cols = ['id', 'calorie_goal', 'protein_goal', 'carbs_goal', 'fat_goal',
                    'weight_goal', 'goal_deadline', 'water_goal', 'updated_at']
            print("✓ 当前目标:")
            for name, val in zip(cols, goal):
                if name == 'id':
                    continue
                label = {'calorie_goal': '热量', 'protein_goal': '蛋白', 'carbs_goal': '碳水',
                         'fat_goal': '脂肪', 'water_goal': '饮水', 'weight_goal': '体重目标',
                         'goal_deadline': '截止', 'updated_at': '更新时间'}.get(name, name)
                unit = ' 卡' if name == 'calorie_goal' else (' g' if name in ('protein_goal', 'carbs_goal', 'fat_goal') else (' ml' if name == 'water_goal' else ' kg' if name == 'weight_goal' else ''))
                print(f"  {label}: {val if val is not None else '未设'}{unit if val is not None else ''}")

        elif command == "weight":
            # 2026-07-20 改:身高从 user_profile 读,note 用 --note 标志(强制)
            if len(sys.argv) < 3:
                print("Error: weight requires <kg> [--note '<备注>']")
                print("  2026-07-20 改:身高不再 CLI 传")
                print("  note 必须用 --note 标志(不接受位置参数)")
                print("  用法:")
                print("    calorie_tracker.py weight 70")
                print("    calorie_tracker.py weight 70 --note '我今天吃饱了'")
                sys.exit(1)
            args = sys.argv[3:]
            # 解析 --note 标志(必须成对出现)
            note = ''
            consumed = []
            i = 0
            while i < len(args):
                if args[i] == '--note':
                    if i + 1 >= len(args):
                        print("Error: --note 标志后必须跟备注内容")
                        sys.exit(1)
                    note = args[i + 1]
                    consumed.extend([i, i + 1])
                    i += 2
                else:
                    i += 1
            # 任何未被消费的参数都是非法的
            extra = [a for idx, a in enumerate(args) if idx not in consumed]
            if extra:
                print(f"Error: 未知参数: {extra}")
                print("  2026-07-20 改:note 必须用 --note 标志")
                print(f"  旧用法 'weight 70 178' / 'weight 70 我今天吃饱了' 不再支持")
                print(f"  请改:calorie_tracker.py weight 70 --note '<备注>'")
                sys.exit(1)
            # v2.4.14 改:符合 V1.0 §02 第②特性 "回执 = ID + 时间戳 + 影响行数"
            receipt = weight.log_weight(sys.argv[2], note=note)
            if receipt is None:
                sys.exit(1)
            print(f"✓ 体重已记录 (id={receipt['id']}, 影响 {receipt['rows_affected']} 行)")
            print(f"  日期: {receipt['date']} {receipt['time']}")
            print(f"  体重: {receipt['kg']} 公斤 / BMI: {receipt['bmi']}")
            if receipt['note']:
                print(f"  备注: {receipt['note']}")

        elif command == "weight-update":
            # 2026-07-20 改:--height 参数已删除
            if len(sys.argv) < 3:
                print("Error: weight-update requires <id> [--weight <kg>] [--note <备注>]")
                sys.exit(1)
            kwargs = _parse_kw_args(sys.argv[3:])
            if 'height' in kwargs:
                print("Error: --height 参数已删除(2026-07-20)")
                print("  身高从 user_profile 读,请用:profile set 30 male --height <cm>")
                sys.exit(1)
            # v2.4.18a 改:符合 V1.0 §02 第②特性"回执 = ID + 时间戳 + 影响行数"
            receipt = weight.update_weight(
                sys.argv[2],
                weight_kg=kwargs.get('weight'),
                note=kwargs.get('note'),
            )
            if receipt is None:
                sys.exit(1)
            print(f"✓ 体重记录已更新 (id={receipt['id']}, 影响 {receipt['rows_affected']} 行)")
            print(f"  日期: {receipt['date']} {receipt['time']}")
            print(f"  体重: {receipt['old_weight']} → {receipt['new_weight']} kg | BMI: {receipt['bmi']}")
            if receipt['note']:
                print(f"  备注: {receipt['note']}")

        elif command == "weight-history":
            _sub_help(sys.argv[2:],
                "用法: weight-history [天数] | --days N\n"
                "默认: 30 天体重历史(HTML)\n"
                "示例: weight-history 7  /  weight-history --days 90")
            # v2.4.6:接通 render_weight_history.py(V1.3 §04 协议 — 有 HTML 模板必走 HTML)
            # v2.4.8:不传 --output,由 render 走 html_path() 新规范(中文 + 时间戳)
            # Phase 3e 修:支持 [天数] 与 --days N,加 try/except 防 int() 崩溃(ADR-0004)
            days = 30
            argv_rest = sys.argv[2:]
            i = 0
            while i < len(argv_rest):
                arg = argv_rest[i]
                if arg == "--days":
                    if i + 1 >= len(argv_rest):
                        print("Error: --days 需要数字", file=sys.stderr)
                        sys.exit(2)
                    try:
                        days = int(argv_rest[i + 1])
                    except ValueError:
                        print(f"Error: --days 需要数字,实得 '{argv_rest[i + 1]}'", file=sys.stderr)
                        sys.exit(2)
                    i += 2
                elif arg.lstrip("-").isdigit():
                    # 兼容旧接口: weight-history 7
                    days = int(arg)
                    i += 1
                else:
                    print(f"Error: 未知参数 '{arg}'", file=sys.stderr)
                    sys.exit(2)
            render_proc = subprocess.run(
                [sys.executable, 'scripts/render_weight_history.py', '--days', str(days)],
                capture_output=True, text=True, encoding='utf-8', timeout=15,
            )
            tmp = _parse_render_path(render_proc.stdout) if render_proc.returncode == 0 else None
            if tmp and tmp.exists():
                print(f"\n✅ HTML 已生成(体重历史): {tmp}")
                print(f"⚠️ ACTION=SEND_TO_USER | HTML={tmp.absolute()}")
            else:
                print(f"⚠️ render 失败,回退纯文本(fallback):")
                if render_proc.stderr:
                    print(f"  stderr: {render_proc.stderr.strip()[:200]}")
            weight.get_weight_history(days)  # fallback 纯文本

        elif command == "weight-goal":
            # ADR-0004 v2.5.5 · ticket 10: --weight-goal --deadline 标志位
            # v2.5.5 起不存 deprecation 库存:positional 参数立即拒绝,无 --legacy-positional 逃生口
            if "--help" in sys.argv[2:] or "-h" in sys.argv[2:]:
                print("用法: weight-goal --weight-goal <kg> [--deadline <YYYY-MM-DD>]")
                print("示例: weight-goal --weight-goal 73 --deadline 2026-12-31")
                sys.exit(0)
            kg = None
            deadline = None
            i = 2
            while i < len(sys.argv):
                arg = sys.argv[i]
                if arg == "--weight-goal" and i + 1 < len(sys.argv):
                    try:
                        kg = float(sys.argv[i + 1])
                    except ValueError:
                        print(f"Error: --weight-goal 需要数字,实得 '{sys.argv[i + 1]}'", file=sys.stderr)
                        sys.exit(2)
                    i += 2
                elif arg == "--deadline" and i + 1 < len(sys.argv):
                    deadline = sys.argv[i + 1]
                    i += 2
                elif not arg.startswith("--"):
                    # v2.5.5 起,positional 立即拒绝(无 deprecation 库存)
                    print(
                        f"Error: 拒绝 positional 参数 '{arg}'。"
                        f"请用 --weight-goal <kg> [--deadline <date>]"
                        f"(v2.5.5 起不存 deprecation 库存,见 ADR-0004)。",
                        file=sys.stderr,
                    )
                    sys.exit(2)
                else:
                    print(f"Error: 未知参数 '{arg}'", file=sys.stderr)
                    sys.exit(2)
            if kg is None:
                print(f"Error: 缺少 --weight-goal <kg>", file=sys.stderr)
                sys.exit(1)
            # SKILL §⚠️ #6 写库回执契约
            receipt = weight_goal.set_weight_goal(kg, deadline)
            print(f"✓ 体重目标已设定:{receipt['weight_goal']} kg"
                  + (f" | 目标日期:{receipt['deadline']}" if receipt['deadline'] else ""))
            print(f"id={receipt['id']} | 日期 {receipt['updated_at']} | 影响 {receipt['rows_affected']} 行")

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
            _sub_help(sys.argv[2:],
                "用法: exercise-summary [天数] | --days N\n默认: 7 天运动汇总")
            # Phase 3e 修:支持 [天数] 与 --days N,加 try/except 防 int() 崩溃
            days = 7
            argv_rest = sys.argv[2:]
            i = 0
            while i < len(argv_rest):
                arg = argv_rest[i]
                if arg == "--days":
                    if i + 1 >= len(argv_rest):
                        print("Error: --days 需要数字", file=sys.stderr)
                        sys.exit(2)
                    try:
                        days = int(argv_rest[i + 1])
                    except ValueError:
                        print(f"Error: --days 需要数字,实得 '{argv_rest[i + 1]}'", file=sys.stderr)
                        sys.exit(2)
                    i += 2
                elif arg.lstrip("-").isdigit():
                    days = int(arg)
                    i += 1
                else:
                    print(f"Error: 未知参数 '{arg}'", file=sys.stderr)
                    sys.exit(2)
            exercise.print_exercise_summary(days)

        elif command == "history":
            _sub_help(sys.argv[2:],
                "用法: history [天数] | --days N\n默认: 7 天热量历史")
            # Phase 3e 修:同上,加 try/except
            days = 7
            argv_rest = sys.argv[2:]
            i = 0
            while i < len(argv_rest):
                arg = argv_rest[i]
                if arg == "--days":
                    if i + 1 >= len(argv_rest):
                        print("Error: --days 需要数字", file=sys.stderr)
                        sys.exit(2)
                    try:
                        days = int(argv_rest[i + 1])
                    except ValueError:
                        print(f"Error: --days 需要数字,实得 '{argv_rest[i + 1]}'", file=sys.stderr)
                        sys.exit(2)
                    i += 2
                elif arg.lstrip("-").isdigit():
                    days = int(arg)
                    i += 1
                else:
                    print(f"Error: 未知参数 '{arg}'", file=sys.stderr)
                    sys.exit(2)
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
            # ADR-0005 · ticket 04 + ticket 07: 默认 200 + --all 显式全量 + --text escape hatch
            if "--help" in sys.argv[2:] or "-h" in sys.argv[2:]:
                print("用法: list-products [--all | --limit <N>] [--text]")
                print("默认: 前 200 行(按 id 升序)")
                print("--all: 全部行(无 LIMIT)")
                print("--limit N: 自定义行数")
                print("--text: 纯文本输出(供 pipeline 用,如 ... | grep)")
                sys.exit(0)
            limit = 200
            text_mode = False  # ticket 07 M4: --text 真 flag
            i = 2
            while i < len(sys.argv):
                arg = sys.argv[i]
                if arg == "--all":
                    limit = None
                    i += 1
                elif arg == "--text":
                    text_mode = True  # 标记,当前实现下与默认行为一致,未来若切 HTML 渲染则用
                    i += 1
                elif arg == "--limit" and i + 1 < len(sys.argv):
                    try:
                        limit = int(sys.argv[i + 1])
                    except ValueError:
                        print(f"Error: --limit 需要数字,实得 '{sys.argv[i + 1]}'", file=sys.stderr)
                        sys.exit(2)
                    i += 2
                else:
                    print(f"Error: 未知参数 '{arg}'(list-products 只接受 --all / --limit N / --text)", file=sys.stderr)
                    sys.exit(2)
            # None (=--all) 转成 999999 防 SQLite LIMIT NULL 报错
            actual_limit = limit if limit is not None else 999999
            # M4: --text 让输出明确为 plain text(给 pipeline 用);无 --text 保留现有行为
            if text_mode:
                # 在 stdout 顶部声明 pipeline 模式,方便 pipe 工具识别
                print("# MODE=text · 适用: ... | grep / awk / wc-l 等 pipeline")
            product_library.list_products(actual_limit)

        elif command == "copy-meals":
            # 复制昨日饮食(D1.8 · ticket #3)
            _sub_help(sys.argv[2:],
                "用法: copy-meals [--from YYYY-MM-DD] [--to YYYY-MM-DD]\n"
                "默认: 从昨天复制到今天(可显式指定)\n"
                "示例: copy-meals / copy-meals --from 2026-08-01 --to 2026-08-02")
            kwargs = _parse_kw_args(sys.argv[2:])
            from_date = kwargs.get('from')
            to_date = kwargs.get('to')
            if not from_date:
                from_date = (date.today() - timedelta(days=1)).isoformat()
            result = diet.copy_meals(from_date, to_date)
            print(f"✓ 已复制饮食 (影响 {result['copied']} 行,跳过 {result['skipped']} 行)")
            print(f"  {result['from_date']} → {result['to_date']}")
            print(f"id=n/a | 日期 {date.today().isoformat()} | 影响 {result['copied']} 行")

        elif command == "add-meal-batch":
            # 批量补记饮食(D1.4 · ticket #3):一次录多餐
            _sub_help(sys.argv[2:],
                "用法: add-meal-batch --input <json>\n"
                "JSON = 数组,每项 {date?, time?, food_name, grams?, calories, protein, carbs?, fat?, note?}\n"
                "示例: add-meal-batch --input /tmp/batch.json")
            kwargs = _parse_kw_args(sys.argv[2:])
            input_path = kwargs.get('input')
            if not input_path:
                print("Error: add-meal-batch 需要 --input <json>", file=sys.stderr)
                sys.exit(1)
            import json as _json
            from pathlib import Path as _Path
            p = _Path(input_path)
            if not p.exists():
                print(f"Error: 输入文件不存在: {p}", file=sys.stderr)
                sys.exit(1)
            entries = _json.loads(p.read_text(encoding='utf-8'))
            if not isinstance(entries, list):
                print("Error: JSON 顶层必须是数组(每项一餐)", file=sys.stderr)
                sys.exit(1)
            result = diet.add_meals_batch(entries)
            print(f"✓ 批量补记完成 (写入 {result['added']} 行 / 跳过 {result['skipped']} / 失败 {result['failed']})")
            for idx, reason in result['failures']:
                print(f"  ✗ 第 {idx + 1} 条跳过: {reason}")
            print(f"id=n/a | 日期 {date.today().isoformat()} | 影响 {result['added']} 行")

        elif command == "update-meals-by-date":
            # 改某日饮食(D2.2 · ticket #3):按日期定位批量改
            _sub_help(sys.argv[2:],
                "用法: update-meals-by-date <date> [--field value ...]\n"
                "支持字段同 update-meal(至少 1 个): --grams/--food/--calories/--protein/--carbs/--fat/--date/--time/--note\n"
                "示例: update-meals-by-date 2026-08-01 --note 修正")
            if len(sys.argv) < 3:
                print("Error: update-meals-by-date 需要 <date>", file=sys.stderr)
                sys.exit(1)
            parsed = _parse_kw_args(sys.argv[3:])
            field_map = {
                'grams': 'grams', 'food': 'food_name', 'calories': 'calories',
                'protein': 'protein', 'carbs': 'carbs', 'fat': 'fat',
                'date': 'date', 'time': 'time', 'note': 'note',
            }
            unknown = set(parsed) - set(field_map)
            if unknown:
                print(f"Error: 不识别的字段: {sorted(unknown)}", file=sys.stderr)
                sys.exit(1)
            kwargs = {field_map[k]: v for k, v in parsed.items() if k in field_map}
            result = diet.update_meals_by_date(sys.argv[2], **kwargs)
            if not result["ok"]:
                print(f"Error: {result['error']}", file=sys.stderr)
                sys.exit(1)
            print(f"✓ 命中 {result['matched']} 条,已更新 {result['updated']} 条")
            print(f"  改动字段: {result['changed_fields']}")

        elif command == "delete-meal-by-type":
            # 删一餐(D2.4 · ticket #3):按餐别删
            _sub_help(sys.argv[2:],
                "用法: delete-meal-by-type <date> <餐别>\n"
                "餐别: 早餐 / 午餐 / 下午茶 / 晚餐 / 夜宵 / 加餐(=下午茶+夜宵)\n"
                "示例: delete-meal-by-type 2026-08-01 早餐")
            if len(sys.argv) < 4:
                print("Error: delete-meal-by-type 需要 <date> <餐别>", file=sys.stderr)
                sys.exit(1)
            result = diet.delete_meals_by_type(sys.argv[2], sys.argv[3])
            if not result["ok"]:
                print(f"Error: {result['error']}", file=sys.stderr)
                sys.exit(1)
            print(f"✓ 已删除 {result['deleted']} 条 ({result['date']} {result['meal']})")
            print(f"id=n/a | 日期 {result['date']} | 影响 {result['deleted']} 行")

        elif command == "delete-meals-by-date":
            # 删某日饮食(D2.5 · ticket #3):一整天清空
            _sub_help(sys.argv[2:],
                "用法: delete-meals-by-date <date>\n"
                "示例: delete-meals-by-date 2026-08-01")
            if len(sys.argv) < 3:
                print("Error: delete-meals-by-date 需要 <date>", file=sys.stderr)
                sys.exit(1)
            result = diet.delete_meals_by_date(sys.argv[2])
            print(f"✓ 已删除 {result['deleted']} 条 ({result['date']})")
            print(f"id=n/a | 日期 {result['date']} | 影响 {result['deleted']} 行")

        elif command == "delete-meals-by-range":
            # 批量删饮食(D2.6 · ticket #3):按日期范围删
            _sub_help(sys.argv[2:],
                "用法: delete-meals-by-range <start> <end>\n"
                "示例: delete-meals-by-range 2026-07-01 2026-07-14")
            if len(sys.argv) < 4:
                print("Error: delete-meals-by-range 需要 <start> <end>", file=sys.stderr)
                sys.exit(1)
            result = diet.delete_meals_by_range(sys.argv[2], sys.argv[3])
            print(f"✓ 已删除 {result['deleted']} 条 ({result['start']} ~ {result['end']})")
            print(f"id=n/a | 日期 {result['start']} | 影响 {result['deleted']} 行")

        elif command == "deprecate-product":
            # 下架食品(D4.5 · ticket #3):标废弃
            _sub_help(sys.argv[2:],
                "用法: deprecate-product <product_id>\n"
                "示例: deprecate-product 3")
            if len(sys.argv) < 3:
                print("Error: deprecate-product 需要 <product_id>", file=sys.stderr)
                sys.exit(1)
            result = product_library.deprecate_product(sys.argv[2])
            if not result['ok']:
                print(f"Error: {result['error']}", file=sys.stderr)
                sys.exit(1)
            print(f"✓ 已下架「{result['name']}」 (id={result['id']}, 影响 1 行)")
            print(f"  提示: 该食品已标记下架,查询/搜索/导入去重不再出现")

        elif command == "profile":
            # profile 子命令
            #   profile set <age> <gender> [--height <cm>] [--note <text>] [--activity <level>]
            #   profile get
            #   profile show
            #   profile activity <level>
            #   profile update --field <X> --value <Y>
            # (2026-07-20 删:profile sync-height)
            if len(sys.argv) < 3:
                print("用法:")
                print("  profile set <age> <gender> [--height <cm>] [--note <text>] [--activity <level>]")
                print("    示例:profile set 30 male --height 177 --activity moderate")
                print("  profile get")
                print("  profile show")
                print("  profile activity <level>")
                print("    示例:profile activity active")
                print("  profile update --field <height|age|gender|activity|note> --value <新值>")
                print("    示例:profile update --field height --value 180")
                sys.exit(1)

            sub = sys.argv[2]
            try:
                if sub == "set":
                    if len(sys.argv) < 5:
                        print("Error: profile set 需要 <age> <gender>")
                        print("  示例:profile set 30 male --height 177 --activity moderate")
                        sys.exit(1)
                    age = int(sys.argv[3])
                    gender = sys.argv[4]
                    kwargs = _parse_kw_args(sys.argv[5:])
                    profile.set_profile(
                        age=age,
                        gender=gender,
                        height_cm=float(kwargs["height"]) if "height" in kwargs else None,
                        note=kwargs.get("note"),
                        activity_level=kwargs.get("activity"),
                    )
                    print("✓ 档案已更新")
                    profile.print_profile()
                elif sub == "get":
                    import json
                    p = profile.get_profile()
                    print(json.dumps(p, ensure_ascii=False, indent=2))
                elif sub == "show":
                    profile.print_profile()
                elif sub == "activity":
                    # profile activity <level> — 设活动量(单独,无需重传其他字段 · #22C)
                    if len(sys.argv) < 4:
                        print("Error: profile activity 需要 <level>")
                        print("  示例:profile activity active")
                        print(f"  可选: {profile.VALID_ACTIVITY_LEVELS}")
                        sys.exit(1)
                    result = profile.set_activity_level(sys.argv[3])
                    print(f"✓ 活动量已设置 (id=1, 影响 1 行)")
                    print(f"  等级: {result['activity_level']} ({result['activity_label']})")
                    print(f"  系数: {result['old_factor']} → {result['activity_factor']}")
                elif sub == "update":
                    # profile update --field <X> --value <Y> — 单字段更新(改档案 · #22C)
                    kwargs = _parse_kw_args(sys.argv[3:])
                    field = kwargs.get("field")
                    value = kwargs.get("value")
                    if not field or value is None:
                        print("Error: profile update 需要 --field 与 --value")
                        print("  示例:profile update --field height --value 180")
                        sys.exit(1)
                    result = profile.update_profile_field(field, value)
                    print(f"✓ {result['label']}已更新 (id=1, 影响 1 行)")
                    print(f"  改前: {result['old_value']}")
                    print(f"  改后: {result['new_value']}")
                    if result['impact']:
                        print(f"  影响: {result['impact']}")
                # 2026-07-20 删:profile sync-height 子命令
                else:
                    print(f"Error: profile 子命令 \"{sub}\" 未知")
                    sys.exit(1)
            except profile.InvalidAgeError as e:
                print(f"Error: {e}")
                sys.exit(1)
            except profile.InvalidGenderError as e:
                print(f"Error: {e}")
                sys.exit(1)
            except profile.InvalidActivityLevelError as e:
                print(f"Error: {e}")
                sys.exit(1)
            except profile.InvalidFieldError as e:
                print(f"Error: {e}")
                sys.exit(1)
            except profile.ProfileError as e:
                print(f"Error: {e}")
                sys.exit(1)

        elif command == "review":
            # 复盘子命令(Q23=A):委托给独立 review_cli.py(符合 5 层契约层)
            # 推荐直接用 review_cli.py:python scripts/review_cli.py --help

            if len(sys.argv) < 3:
                print("Error: review 需要子命令 --gen / --send / --archive / --full")
                print("  推荐:python scripts/review_cli.py --help")
                sys.exit(1)

            # 委托:用 subprocess 列表传参(避免 PowerShell 中文乱码)
            cli_path = Path(__file__).parent / 'review_cli.py'
            sub_arg_map = {
                '--gen': 'gen',
                '--send': 'send',
                '--archive': 'archive',
                '--full': 'full',
            }
            sub = sys.argv[2]
            subcommand = sub_arg_map.get(sub)
            if not subcommand:
                print(f"Error: review 子命令 '{sub}' 未知")
                sys.exit(1)

            forwarded_args = [subcommand] + sys.argv[3:]

            try:
                result = subprocess.run(
                    ['python', str(cli_path)] + forwarded_args,
                    capture_output=True, text=True, encoding='utf-8',
                    timeout=600,
                )
            except subprocess.TimeoutExpired:
                print("Error: review_cli.py 调用超时 (600s)")
                sys.exit(1)
            except FileNotFoundError:
                print(f"Error: 找不到 review_cli.py, 路径:{cli_path}")
                sys.exit(1)

            if result.stdout:
                print(result.stdout)
            if result.returncode != 0:
                print(f"Error: review_cli.py 退出码 {result.returncode}", file=sys.stderr)
                if result.stderr:
                    print(result.stderr, file=sys.stderr)
                sys.exit(result.returncode)

        else:
            print(f"Error: Unknown command '{command}'")
            usage()
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
