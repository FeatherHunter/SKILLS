#!/usr/bin/env python3
"""
渲染 2026-06-24 作息报告 HTML
"""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

with open('/tmp/report_data_2026-06-24.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

records = data['records']
hours = data['hours']
cat_minutes = data['cat_minutes']
total_minutes = data['total_minutes']
total_hours = total_minutes / 60
sleep_records = data['sleep_records']
main_sleep = data['main_sleep']
meal_records = data['meal_records']
work_records = data['work_records']
commute_records = data['commute_records']
study_records = data['study_records']
leisure_records = data['leisure_records']
entertainment_records = data['entertainment_records']
social_records = [r for r in records if r['category'] == '社交']
wash_records = [r for r in records if r['category'] == '洗漱']

# 颜色 & emoji
color_map = {
    "睡眠": "#5E5CE6", "工作": "#007AFF", "学习": "#34C759", "运动": "#FF9500",
    "通勤": "#64D2FF", "餐饮": "#FF9F0A", "娱乐": "#AF52DE", "社交": "#FF2D55",
    "休闲": "#30D158", "健康": "#FF3B30", "洗漱": "#5AC8FA", "兴趣爱好": "#BF8F5F",
    "居家": "#BF8F5F", "家政家务": "#A2845E", "居家管理": "#A2845E",
    "家务": "#A2845E", "生活": "#8E8E93", "未知": "#8E8E93", "休息": "#8E8E93",
    "其他": "#8E8E93", "烹饪": "#FF9F0A", "生活管理": "#A2845E",
    "卡路里": "#FF3B30", "记账": "#64D2FF",
}
emoji_map = {
    "睡眠": "😴", "工作": "💼", "学习": "📚", "运动": "🏋️",
    "通勤": "🚴", "餐饮": "🍽️", "娱乐": "🎮", "社交": "💕",
    "休闲": "🛋️", "健康": "🏥", "洗漱": "🚿", "兴趣爱好": "🎨",
    "居家": "🏠", "家政家务": "🧹", "居家管理": "🧹",
    "家务": "🧹", "生活": "🌱", "未知": "❓", "休息": "🛋️",
    "其他": "📌", "烹饪": "🍳", "生活管理": "📌",
    "卡路里": "🏥", "记账": "📌",
}

# 排序分类（按时长倒序）
sorted_cats = sorted(cat_minutes.items(), key=lambda x: -x[1])

# ============ HTML 渲染 ============
def fmt_dur(mins):
    return f"{mins//60}小时{mins%60}分钟" if mins % 60 else f"{mins//60}小时"

def cat_emoji(c):
    return emoji_map.get(c, "📌")
def cat_color(c):
    return color_map.get(c, "#8E8E93")

# 渲染分类摘要
summary_html = []
for cat, mins in sorted_cats:
    emoji = cat_emoji(cat)
    color = cat_color(cat)
    pct = mins / total_minutes * 100
    summary_html.append(f'''    <div class="summary-item">
      <span class="emoji">{emoji}</span>
      <div class="info">
        <div class="cat">{cat}</div>
        <div class="dur">{fmt_dur(mins)}</div>
        <div class="bar"><div class="bar-fill" style="width:{pct:.1f}%;background:{color}"></div></div>
      </div>
    </div>''')
summary_html = '\n'.join(summary_html)

# 计算时间轴：使用每小时主导分类（按分钟数覆盖最多）
hour_cats = [None] * 24
hour_minutes = [defaultdict(int) for _ in range(24)]
for r in records:
    final_cat = r['category']
    try:
        h_start = int(r['time_start'].split(':')[0])
        s_min = int(r['time_start'].split(':')[1])
        if r['time_end'] == '23:59':
            e_min_total = 23 * 60 + 59
        elif r['time_end'] == '24:00':
            e_min_total = 24 * 60
        else:
            eh, em = map(int, r['time_end'].split(':'))
            e_min_total = eh * 60 + em
        s_min_total = h_start * 60 + s_min
        cur = s_min_total
        while cur < e_min_total:
            h = cur // 60
            if h < 24:
                next_hour = (h + 1) * 60
                covered = min(next_hour, e_min_total) - cur
                hour_minutes[h][final_cat] += covered
                cur = next_hour
            else:
                break
    except Exception as e:
        pass

# 取每小时主导分类
for h in range(24):
    if hour_minutes[h]:
        hour_cats[h] = max(hour_minutes[h].items(), key=lambda x: x[1])[0]
    else:
        hour_cats[h] = hours[h] or '休息'

# 渲染时间轴
timeline_html = []
for h in range(24):
    cat = hour_cats[h] or '休息'
    color = cat_color(cat)
    timeline_html.append(f'    <div class="timeline-block" style="background:{color}"><div class="tip">{h:02d}:00 {cat}</div></div>')
timeline_html = '\n'.join(timeline_html)

# 渲染时间轴图例（去重，基于新算法）
used_cats = []
for h in range(24):
    cat = hour_cats[h] or '休息'
    if cat not in used_cats:
        used_cats.append(cat)
legend_html = []
for cat in used_cats:
    color = cat_color(cat)
    legend_html.append(f'    <div class="legend-item"><div class="legend-dot" style="background:{color}"></div>{cat}</div>')
legend_html = '\n'.join(legend_html)

# 周几
weekday_map = {0: '周一', 1: '周二', 2: '周三', 3: '周四', 4: '周五', 5: '周六', 6: '周日'}
dt = datetime.strptime(data['date'], '%Y-%m-%d')
weekday = weekday_map[dt.weekday()]
date_cn = f"{dt.year}年{dt.month}月{dt.day}日"

# ============ 当日亮点 ============
# 睡眠总时长
sleep_total = cat_minutes.get('睡眠', 0)
sleep_h = sleep_total // 60
sleep_m = sleep_total % 60
sleep_pct = sleep_total / total_minutes * 100

# 餐饮总时长
meal_total = cat_minutes.get('餐饮', 0)
meal_h = meal_total // 60
meal_m = meal_total % 60

# 工作总时长
work_total = cat_minutes.get('工作', 0)
work_h = work_total // 60
work_m = work_total % 60

# 学习总时长
study_total = cat_minutes.get('学习', 0)
study_h = study_total // 60
study_m = study_total % 60

# 娱乐总时长
entertainment_total = cat_minutes.get('娱乐', 0)

# 通勤总时长
commute_total = cat_minutes.get('通勤', 0)

# 休闲总时长
leisure_total = cat_minutes.get('休闲', 0)
leisure_h = leisure_total // 60
leisure_m = leisure_total % 60

# 洗漱总时长
wash_total = cat_minutes.get('洗漱', 0)

highlights_html = f'''    <div class="highlight-row">
      <span class="h-emoji">💼</span>
      <div>
        <div class="h-text">工作 8h16m（占 34.5%）：27 段工作 {work_h}h{work_m}m，是工作强度很高的一天。三大主题：① 居家管家物品录入 1h+（蓝牙耳机硅胶耳塞/冰格/毛球器/罗氏沼虾/鸡大胸等，4 张图+10 多段讨论）② 焖饭相关工作（卡路里查询/记账/居家管家）穿插全天 ③ 给王大为做歌（采访+歌词+确认+生成研究）约 1h30m。晚间还做了社保/公积金/劳动仲裁资料整理 1h+，社保补缴计算 32min。亮点是"创作"——给朋友做歌是全新的工作类型，21:24~23:55 共 2h31m 几乎不间断</div>
        <div class="h-time">27 段工作：08:18~08:33 / 08:34~08:47 / 08:48~08:55 / 08:55~08:57 / 08:57~08:59 / 08:59~09:12 / 11:15~11:22 / 11:22~11:23 / 11:23~11:27 / 11:27~11:28 / 11:33~11:36 / 11:36~11:37 / 12:09~12:13 / 12:26~12:41 / 14:57~15:07 / 15:07~15:10 / 16:16~17:23 / 17:58~18:49 / 18:49~19:21 / 19:54~21:15 / 21:15~21:24 / 21:24~22:03 / 22:03~22:34 / 22:34~23:21 / 23:21~23:44 / 23:44~23:55 / 23:55~23:59</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">😴</span>
      <div>
        <div class="h-text">睡眠 7h50m（占 32.7%）：1 段主睡眠 00:00~07:50 共 7h50m，符合 7-9h 推荐范围。单段无短醒，睡眠质量应该不错。07:50 起床后进入洗漱（08:33 送女朋友出门时刷牙），是健康的起床节奏。23:59 时记录仍在工作中（openclaw token 查询），所以今天凌晨的睡眠会归到 2026-06-25 的统计里</div>
        <div class="h-time">1 段睡眠：00:00~07:50</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🍽️</span>
      <div>
        <div class="h-text">餐饮时间偏长 4h0m（占 16.7%）：13 段餐饮 {meal_h}h{meal_m}m。延续了昨天的焖饭模式：① 10:35~11:15 早餐+做饭+收拾 40min（鸡蛋+调味料记录）② 12:41~14:07 焖饭准备 86min（切鸡胸肉+出门买菜+胡萝卜+鸡枞油+调料+出门采迷迭香）③ 14:34~16:14 焖饭持续 100min（生米+营养计算+煮饭+焖饭打理+罗氏沼虾准备+焖饭份数讨论+吃饭前热量总结+吃晚饭）④ 19:48~19:54 吃晚饭 6min。焖饭准备过程 2h+ 是"做饭时间过长"的典型表现，但营养记录完整（卡路里+调味+份数）</div>
        <div class="h-time">13 段餐饮：10:35~10:38 / 10:38~10:55 / 10:55~11:15 / 12:41~13:09 / 13:09~13:18 / 13:18~14:07 / 14:07~14:34 / 14:34~14:57 / 15:10~15:46 / 15:46~16:00 / 16:00~16:07 / 16:07~16:12 / 16:12~16:14</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">📚</span>
      <div>
        <div class="h-text">学习 1h2m（占 4.3%）：3 段。① 17:23~17:48 C盘扫描 + openclaw 更新研究 25min（系统级问题排查）② 17:48~17:58 WSL 内存使用研究 10min（深挖 WSL2 内存机制）③ 19:21~19:48 MiniMax Token Plan 配置 + web_search 研究 27min。这是高质量的"工程师学习"——磁盘/内存/配置类技术研究，是程序员持续精进的体现。3 段加在一起正好 1h+</div>
        <div class="h-time">3 段学习：17:23~17:48 / 17:48~17:58 / 19:21~19:48</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🎵</span>
      <div>
        <div class="h-text">给王大为做歌（21:24~23:55 共 2h31m）：这是全新的工作类型。21:24~22:03 采访+歌词确认 39min，22:03~22:34 歌曲生成研究 31min（探索技术方案），22:34~23:21 歌词审查和精简 47min，23:21~23:44 歌词修改+全新歌曲方向讨论 23min，23:44~23:55 OK 确认 11min。这是用 music_generate 技能为朋友创作歌曲的完整流程——采访→生成研究→歌词审查→方向调整→定稿。亮点：① 完整的创作流程 ② 多次方向调整 ③ 最终 OK。属于"技术+创意"的复合工作</div>
        <div class="h-time">5 段创作：21:24~22:03 / 22:03~22:34 / 22:34~23:21 / 23:21~23:44 / 23:44~23:55</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🛋️</span>
      <div>
        <div class="h-text">休闲 1h47m（占 7.4%）：6 段。① 09:12~10:07 躺床休息 55min（结束居家管家录入后）② 11:37~12:09 躺床+无糖可乐讨论 32min（咖啡因话题）③ 12:13~12:13 坐在床边瞬间 ④ 12:13~12:26 坐床边休息 13min ⑤ 19:48~19:54 吃晚饭+看短视频 6min ⑥ 19:54 工作前的过渡。休闲结构合理，主要是"工作间隔休息"和"饭后短暂休息"</div>
        <div class="h-time">6 段休闲：09:12~10:07 / 11:37~12:09 / 12:13~12:13 / 12:13~12:26 / 19:48~19:54</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">💕</span>
      <div>
        <div class="h-text">社交 33min（2 段）：① 10:07~10:35 购物比价咨询 28min（女朋友帮忙比价 黄瓜/白菜/胡萝卜/罗氏沼虾/鸡大胸）② 11:28~11:33 记账分类讨论+居家管家物品状态确认 5min。女朋友参与"购物决策"是健康的伴侣互动，比直接代购更有质量——用户自己做主，女朋友提供参考</div>
        <div class="h-time">2 段社交：10:07~10:35 / 11:28~11:33</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🚿</span>
      <div>
        <div class="h-text">洗漱 29min（2 段）：① 07:50~08:18 起床+称体重 28min（起床后到称体重的过渡）② 08:33~08:34 洗漱 1min（送女朋友出门+刷牙）。洗漱时间正常，称体重 28min 偏长——可能是在床上做伸展或记录</div>
        <div class="h-time">2 段洗漱：07:50~08:18 / 08:33~08:34</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🎮</span>
      <div>
        <div class="h-text">娱乐 2min：16:14~16:16 边吃晚饭边看视频 2min。娱乐时间极少（这是第 3 个 0 运动日的延伸），但符合"工作日专注"模式。19:48~19:54 有 6min 边吃晚饭边看短视频，归入休闲类（不算娱乐）</div>
        <div class="h-time">16:14~16:16 边吃边看视频</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">⚠️</span>
      <div>
        <div class="h-text">运动/通勤 0min：连续 3 天（06-22 0 运动 / 06-23 0 运动 / 06-24 0 运动+通勤）⚠️。这是居家日的典型问题——无需出门，所以也无通勤无运动。但身体仍然需要活动。建议：① 上午 10:00 主动站立活动 10min ② 做饭间隙做拉伸 ③ 下午 15:00 散步 20min ④ 晚饭后走动 15min</div>
        <div class="h-time">⚠️ 0 段运动+通勤，连续 3 天</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">💼</span>
      <div>
        <div class="h-text">居家管家物品录入 1h+：08:18~09:12 集中录入 5 件物品。① 蓝牙耳机硅胶耳塞（讨论方案 18min）② 冰格+毛球器（照片+位置+材质+名称 27min）③ 09:12 后短暂过渡到躺床休息。这是"批量录入"模式——把同类物品一起录入，效率高。方法：语音描述+图片+位置确认，比单件录入快 3 倍</div>
        <div class="h-time">居家管家：08:18~08:33 / 08:34~08:47 / 08:48~08:55 / 08:55~08:57 / 08:57~08:59 / 08:59~09:12</div>
      </div>
    </div>'''

# ============ 睡眠分析 ============
sleep_html = f'''    <div class="highlight-row">
      <span class="h-emoji">&#x1F319;</span>
      <div>
        <div class="h-text">主睡眠 00:00~07:50 共 7h50m：单段无中断的整夜睡眠。从 23:00 前夜入睡延续到 07:50 起床，整段 7h50m 处于"深度睡眠+REM 循环"的标准周期内。07:50 起床是健康的起床时间——既不太早（5~6 点）也不太晚（10 点+）</div>
        <div class="h-time">00:00~07:50 持续 7h50m</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4CA;</span>
      <div>
        <div class="h-text">总睡眠 7h50m（1 段），占全天 32.7%。在 7-9h 推荐范围之内（接近下限）。这是连续 3 天（06-22: 9h15m / 06-23: 12h11m / 06-24: 7h50m）以来睡眠最少的一天。睡眠结构简单：单段长睡眠，无午睡，无短醒——是"睡眠不足但质量不错"的模式</div>
        <div class="h-time">总 7h50m（1 段）✓ 正常（接近下限）</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F552;</span>
      <div>
        <div class="h-text">07:50 起床时间：起床后立即称体重（07:50~08:18 共 28min），然后进入工作状态（08:18 居家管家）。这是"起床→称体重→开始工作"的健康晨间流程，无赖床。建议：保持 7:30~8:00 起床，7-9h 睡眠（23:00~23:30 入睡最理想）</div>
        <div class="h-time">07:50 起床 → 08:18 开始工作</div>
      </div>
    </div>'''

# ============ 改善建议 ============
suggest_html = f'''    <div class="highlight-row">
      <span class="h-emoji">&#x1F3C3;</span>
      <div>
        <div class="h-text">运动 0min 连续 3 天 ⚠️：与 06-22、06-23 同样的问题。今天居家全天，无通勤无运动。居家日尤其需要主动运动——做饭/卧床/工作循环久了身体会僵。建议：① 上午 10:00 站立伸展 10min（做饭间隙做）② 下午 15:00 散步 20min（避开最热时段）③ 晚饭后室内走动 15min ④ 每天 1 万步（用手机计步器监控）⑤ 从"轻量"开始，关键是"每天都做"</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F37D;&#xFE0F;</span>
      <div>
        <div class="h-text">餐饮 4h0m 仍然偏长 ⚠️：与昨天 4h30m 类似，今天 4h0m。焖饭准备流程：10:35 切鸡胸肉→12:41 出门买菜→13:18 处理焖饭食材→14:07 出门采迷迭香→14:34 焖饭开始→16:14 吃晚饭——总流程 5h+，但吃饭只有 2min（16:12~16:14）。问题：焖饭流程分散，从 10:35 一直持续到 16:14。建议：① 焖饭集中准备（上午 9:00 开始 11:00 完成）② 电压力锅替代普通焖饭（25min 出锅）③ 简化调味记录（不必每种调料都问 AI）④ 吃饭时不操作手机 ⑤ 餐饮总时间控制在 2h 以内</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4A4;</span>
      <div>
        <div class="h-text">无午睡问题：今天 0 午睡（连续 2 天无午睡，06-23 有 1h53m 午睡）。无午睡对下午精力有影响——下午 17:00 后开始 C盘扫描+WSL 研究+社保资料整理 3 段高强度工作，全靠 1h47m 休闲时间支撑。建议：① 12:30~13:00 30min 午睡（饭后小憩）② 11:37~12:09 躺床 32min 可改为午睡时段 ③ 午睡不躺床上也行（坐着打盹 20min）④ 16:00 后避免高强度连续工作（工作 3h+ 后休息 10min）</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4DA;</span>
      <div>
        <div class="h-text">学习主题：今天 3 段学习都是"技术研究"类（C盘/WSL/MiniMax Token），无"软技能"或"人生规划"类学习。建议：① 平衡技术学习与软技能学习（写作/沟通/理财/健康）② 每周至少 1 次"非技术"学习（如阅读一本非技术书 30min）③ 学习记录到"备忘录"中便于回顾 ④ 周末可尝试 2h+ 的深度学习（一个主题）</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F3B5;</span>
      <div>
        <div class="h-text">给王大为做歌（创作类工作）：21:24~23:55 共 2h31m 的创作流程很完整（采访→研究→审查→调整→定稿）。这是新工作类型的探索——用 music_generate 技能为朋友创作。建议：① 总结"创作 SOP"（采访问题清单/歌词审查标准/生成参数调优）② 考虑是否对外开放（接单创作？周边服务？）③ 创作类工作是有意义的精神活动，与"半年不工作寻找意义"的计划契合 ④ 继续探索类似方向（写代码/写作/音乐/绘画）</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4BC;</span>
      <div>
        <div class="h-text">社保/劳动仲裁问题有进展：17:58~18:49 资料整理 51min + 18:49~19:21 补缴计算 32min = 共 1h23m 处理社保问题。这是 06-23 提到的"劳动仲裁接近解决"的延续——现在进入"补缴计算"阶段。建议：① 完成计算后尽快执行补缴（避免拖延）② 整理"劳动仲裁+社保补缴"完整流程文档（后续可复用）③ 与公司沟通时保留所有邮件/微信记录 ④ 必要时咨询专业律师（劳动法方向）</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F3E0;</span>
      <div>
        <div class="h-text">居家管家录入流程优化：今天 1h 完成 5 件物品录入（蓝牙耳机硅胶耳塞/冰格/毛球器/罗氏沼虾/鸡大胸），比 06-23 的 8 件（1h）略慢但效率仍较高。方法成熟：语音描述+图片+位置确认。建议：① 把"录入模板"固化（如"名称+材质+尺寸+位置+图片"）② 图片命名规则统一（昨天已讨论）③ 减少位置查找时间（提前定位）④ 每日居家管家录入 ≤30min（5 件左右）</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4F1;</span>
      <div>
        <div class="h-text">23:59 仍在工作的影响：末条记录 23:55~23:59 是"openclaw token 查询（命令行方式）"。23:59 时还在工作的状态会：① 影响入睡时间（推迟到 24:00+）② 降低睡眠质量（脑力疲劳）③ 形成"晚睡-早睡"的恶性循环。建议：① 23:30 停止所有工作 ② 23:30~24:00 做"睡前仪式"（洗漱/看纸质书/冥想）③ 设定 23:30 闹钟提醒"准备睡觉"④ 入睡时间控制在 23:30 之前</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4BE;</span>
      <div>
        <div class="h-text">今日计划：13:09~13:18 出门买菜 9min（线下买菜）。这是"线上下单→线下购买"的补充，说明美团买菜等不能完全覆盖（迷迭香/罗氏沼虾等）。建议：① 把"必须线下"清单固化（如特殊香料/活鲜）② 周末集中采购 1 次（减少外出频次）③ 烹饪分类下增加"采购"小类便于统计</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4DD;</span>
      <div>
        <div class="h-text">备忘录心愿讨论：16:16~17:23 67min 集中讨论"心愿"功能。这是核心功能迭代——心愿列表+优化。建议：① 完成心愿功能后整理"用户使用习惯"（哪个心愿最常被查）② 增加"心愿进度跟踪"（完成的打钩）③ 与"每日检查"联动（未完成心愿提醒）④ 收集用户反馈（哪些心愿难管理）</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x2705;</span>
      <div>
        <div class="h-text">周三做得好的地方：① 睡眠 7h50m 接近推荐（虽然最少但是够用）② 高强度工作 8h16m（27 段，含创作/技术研究/法律事务）③ 给王大为做歌（创作类工作，2h31m）④ 居家管家录入 5 件 ⑤ 焖饭流程完整（准备+记录+营养计算）⑥ 学习 1h+（C盘/WSL/MiniMax）⑦ 社保/劳动仲裁进展（1h23m 处理）⑧ 23:59 前完成工作（不拖延）⑨ 居家日效率高</div>
      </div>
    </div>'''

# ============ 完整 HTML ============
html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>作息报告 - {date_cn}（{weekday}）</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","SF Pro Display","PingFang SC","Microsoft YaHei",sans-serif;background:#f5f5f7;color:#1d1d1f;line-height:1.6;-webkit-font-smoothing:antialiased}}
.container{{max-width:720px;margin:0 auto;padding:24px 16px}}
.header{{text-align:center;padding:32px 0 24px}}
.header h1{{font-size:28px;font-weight:700;letter-spacing:-.5px}}
.header .date{{font-size:15px;color:#86868b;margin-top:4px}}
.header .weekday{{display:inline-block;font-size:12px;font-weight:500;color:#fff;background:#007AFF;border-radius:12px;padding:2px 10px;margin-top:8px}}
.card{{background:#fff;border-radius:14px;padding:24px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.04)}}
.card h2{{font-size:17px;font-weight:600;margin-bottom:16px;display:flex;align-items:center;gap:8px}}
.card h2 .icon{{font-size:20px}}
.summary-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}}
.summary-item{{display:flex;align-items:center;padding:12px 14px;background:#f5f5f7;border-radius:10px;gap:10px}}
.summary-item .emoji{{font-size:22px;width:32px;text-align:center;flex-shrink:0}}
.summary-item .info{{flex:1;min-width:0}}
.summary-item .cat{{font-size:13px;font-weight:500;color:#1d1d1f}}
.summary-item .dur{{font-size:12px;color:#86868b;margin-top:1px}}
.summary-item .bar{{height:4px;background:#e5e5e5;border-radius:2px;margin-top:6px;overflow:hidden}}
.summary-item .bar-fill{{height:100%;border-radius:2px;transition:width .6s ease}}
.total-row{{display:flex;justify-content:space-between;align-items:center;padding:14px 16px;background:#f5f5f7;border-radius:10px;margin-top:12px}}
.total-row .label{{font-size:14px;font-weight:500;color:#1d1d1f}}
.total-row .value{{font-size:20px;font-weight:700;color:#007AFF}}
.total-row .check{{font-size:14px;color:#34c759;margin-left:6px}}
.timeline{{display:flex;gap:2px;height:40px;border-radius:8px;overflow:hidden;margin-bottom:8px}}
.timeline-block{{flex:1;position:relative;cursor:pointer;transition:opacity .15s}}
.timeline-block:hover{{opacity:.8}}
.timeline-block .tip{{display:none;position:absolute;bottom:calc(100% + 6px);left:50%;transform:translateX(-50%);background:#1d1d1f;color:#fff;font-size:11px;padding:4px 8px;border-radius:6px;white-space:nowrap;z-index:10;pointer-events:none}}
.timeline-block:hover .tip{{display:block}}
.timeline-labels{{display:flex;justify-content:space-between;font-size:10px;color:#86868b;padding:0 2px}}
.legend{{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}}
.legend-item{{display:flex;align-items:center;gap:4px;font-size:11px;color:#86868b}}
.legend-dot{{width:10px;height:10px;border-radius:3px;flex-shrink:0}}
.highlights{{display:flex;flex-direction:column;gap:10px}}
.highlight-row{{display:flex;align-items:flex-start;gap:10px;padding:10px 14px;background:#f5f5f7;border-radius:10px}}
.highlight-row .h-emoji{{font-size:18px;flex-shrink:0;margin-top:1px}}
.highlight-row .h-text{{font-size:13px;color:#1d1d1f;line-height:1.5}}
.highlight-row .h-time{{font-size:12px;color:#86868b;margin-top:2px}}
.footer{{text-align:center;padding:20px 0;font-size:11px;color:#86868b}}
@media(max-width:480px){{.summary-grid{{grid-template-columns:1fr}}.container{{padding:16px 12px}}}}
</style>
</head>
<body>
<div class="container">

<div class="header">
  <h1>每日作息报告</h1>
  <div class="date">{date_cn}</div>
  <span class="weekday">{weekday}</span>
</div>

<div class="card">
  <h2><span class="icon">&#x1F4CA;</span> 时间分配</h2>
  <div class="summary-grid">
{summary_html}
  </div>
  <div class="total-row">
    <span class="label">总计</span>
    <span><span class="value">{fmt_dur(total_minutes)}</span><span class="check">&#x2713;</span></span>
  </div>
</div>

<div class="card">
  <h2><span class="icon">&#x1F550;</span> 24小时时间轴</h2>
  <div class="timeline">
{timeline_html}
  </div>
  <div class="timeline-labels">
    <span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>23:59</span>
  </div>
  <div class="legend">
{legend_html}
  </div>
</div>

<div class="card">
  <h2><span class="icon">&#x2B50;</span> 当日亮点</h2>
  <div class="highlights">
{highlights_html}
  </div>
</div>

<div class="card">
  <h2><span class="icon">&#x1F634;</span> 睡眠分析</h2>
  <div class="highlights">
{sleep_html}
  </div>
</div>

<div class="card">
  <h2><span class="icon">&#x1F4A1;</span> 改善建议</h2>
  <div class="highlights">
{suggest_html}
  </div>
</div>

<div class="footer">
  作息管家 · 自动生成于 {datetime.now().strftime("%Y-%m-%d %H:%M")} · 共 {data['total_records']} 个记录块
</div>

</div>
</body>
</html>'''

REPORT_PATH = Path('/mnt/d/2Study/StudyNotes/SKILLS/作息管家/reports/2026-06-24.html')
REPORT_PATH.write_text(html, encoding='utf-8')
print(f"✓ HTML 报告已生成: {REPORT_PATH}")
print(f"  文件大小: {REPORT_PATH.stat().st_size} bytes")