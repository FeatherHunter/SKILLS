#!/usr/bin/env python3
"""
渲染 2026-06-25 作息报告 HTML
"""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

with open('/tmp/report_data_2026-06-25.json', 'r', encoding='utf-8') as f:
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
exercise_records = [r for r in records if r['category'] == '运动']
home_records = [r for r in records if r['category'] == '家务']
hobby_records = [r for r in records if r['category'] == '兴趣爱好']

# 颜色 & emoji
color_map = {
    "睡眠": "#5E5CE6", "工作": "#007AFF", "学习": "#34C759", "运动": "#FF9500",
    "通勤": "#64D2FF", "餐饮": "#FF9F0A", "娱乐": "#AF52DE", "社交": "#FF2D55",
    "休闲": "#30D158", "健康": "#FF3B30", "洗漱": "#5AC8FA", "兴趣爱好": "#BF8F5F",
    "家务": "#A2845E", "未知": "#8E8E93", "休息": "#8E8E93",
}
emoji_map = {
    "睡眠": "😴", "工作": "💼", "学习": "📚", "运动": "🏋️",
    "通勤": "🚴", "餐饮": "🍽️", "娱乐": "🎮", "社交": "💕",
    "休闲": "🛋️", "健康": "🏥", "洗漱": "🚿", "兴趣爱好": "🎨",
    "家务": "🧹", "未知": "❓",
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

# ============ 关键数据 ============
sleep_total = cat_minutes.get('睡眠', 0)
sleep_h = sleep_total // 60
sleep_m = sleep_total % 60
sleep_pct = sleep_total / total_minutes * 100

meal_total = cat_minutes.get('餐饮', 0)
work_total = cat_minutes.get('工作', 0)
study_total = cat_minutes.get('学习', 0)
entertainment_total = cat_minutes.get('娱乐', 0)
commute_total = cat_minutes.get('通勤', 0)
leisure_total = cat_minutes.get('休闲', 0)
wash_total = cat_minutes.get('洗漱', 0)
social_total = cat_minutes.get('社交', 0)
exercise_total = cat_minutes.get('运动', 0)
home_total = cat_minutes.get('家务', 0)
hobby_total = cat_minutes.get('兴趣爱好', 0)

# 工作段（去掉14:04的0分钟重复）
real_work_records = [r for r in work_records if r['duration_minutes'] > 0]

# ============ 当日亮点 ============
highlights_html = f'''    <div class="highlight-row">
      <span class="h-emoji">😴</span>
      <div>
        <div class="h-text">睡眠 7h6m（占 29.6%）：1 段主睡眠 01:55~09:01 共 7h6m，凌晨 2 点入睡、早上 9 点起床。在推荐 7-9h 范围内（接近下限），但入睡时间过晚——01:55 入睡意味着 00:00 之后还活跃了 1h55m。9:01 起床后进入"起床后清醒/日常起居"阶段（88min），9 点起床配合 7h 睡眠也算合理。起床晚对应睡眠结构后移</div>
        <div class="h-time">1 段睡眠：01:55~09:01（426min）</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🏋️</span>
      <div>
        <div class="h-text">运动回归 1h12m（占 5.0%）：打破连续 4 天（06-21~06-24）0 运动的僵局 ✅。16:21~17:33 共 72min 健身 + 八段锦，其中八段锦 16:31~17:33 共 62min 是主要运动。00:00 后也提及"开始健身"，但 16:21 才真正开始。1h+ 运动是健康的标志——比前几天 0 运动好多了。建议保持每天 30min 主动运动</div>
        <div class="h-time">2 段运动：16:21~16:31（10min）开始健身 / 16:31~17:33（62min）八段锦</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">💕</span>
      <div>
        <div class="h-text">社交 3h41m（占 15.4%）：4 段社交，主要集中在 18:12~22:09 共 3h57m 与女朋友外出。① 18:12~19:02 去找女朋友 50min ② 19:27~20:05 出门逛街老门东 38min ③ 20:05~22:09 继续逛街 124min（推断无消息是游玩中）④ 22:09~22:47 打车回家。社交与女朋友相处的总时长 3h41m，关系维护很充分。老门东是南京著名景点，逛街 2h+ 是高质量的陪伴时光</div>
        <div class="h-time">4 段社交：18:12~19:02（50min）去找女朋友 / 19:27~20:05（38min）出门逛街老门东 / 20:05~22:09（124min）继续逛街 / 22:09~22:47 通勤回家</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🛋️</span>
      <div>
        <div class="h-text">休闲 4h50m（占 20.2%）：9 段休闲，是今天最显眼的"休息密集日"。结构：① 09:01~10:29 起床后清醒/日常起居 88min（最长）② 13:17~13:18 午餐结束小憩 1min ③ 14:32~14:57 头疼后躺下休息 25min ⚠️（下午工作 1h+ 后果断躺下，是好的恢复反应）④ 14:57~15:06 睡醒后清醒 9min ⑤ 15:33~16:21 在家休息 48min ⑥ 17:33~17:37 练完八段锦后打卡 4min ⑦ 17:53~18:11 吃完晚饭+铺床 18min ⑧ 19:02~19:27 在家吃饭洗碗 25min ⑨ 22:47~23:59 躺床上准备入睡 72min。休闲结构合理，14:32 的"头疼躺下"是身体发出的信号，正确的选择</div>
        <div class="h-time">9 段休闲：09:01~10:29 / 13:17~13:18 / 14:32~14:57 / 14:57~15:06 / 15:33~16:21 / 17:33~17:37 / 17:53~18:11 / 19:02~19:27 / 22:47~23:59</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">💼</span>
      <div>
        <div class="h-text">工作 1h31m（占 6.3%）：15 段工作（去掉 6 条 14:04 重复扫描的 0 分钟噪音）。主题：① 00:00~00:01 openclaw dashboard 查 token ② 00:43~00:49 环境变量查询 ③ 12:55~14:32 db 重复扫描清理 + 多 db 文件滚动设计 1h37m（核心工作）④ 14:05~14:15 定时任务验证 + 语音测试 + 数据查询 10min ⑤ 14:15~14:22 等待 AI 回复 7min ⑥ 14:22~14:32 继续查询 db 文件管理 + 删除 001.db 10min。今天工作主题是"录音机技能 db 文件管理"——从去重→多 db 设计→meta.db→删除测试库，是 1.5h 的高强度工作</div>
        <div class="h-time">15 段工作：00:00~00:01 / 00:43~00:49 / 12:55~12:58 / 13:10~13:16 / 13:16~13:17 / 13:18~13:21 / 13:21~13:32 / 13:32~13:42 / 13:42~13:49 / 13:49~14:04 / 14:04~14:04×6(0min) / 14:04~14:05 / 14:05~14:15 / 14:15~14:22 / 14:22~14:25 / 14:25~14:32</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🎮</span>
      <div>
        <div class="h-text">娱乐 1h40m（占 6.9%）：3 段娱乐。① 00:01~00:43 听歌曲评价 42min（评价给王大为做的歌）② 01:26~01:55 心愿加入 + 看短视频 + 准备睡觉 29min ③ 10:29~10:58 刷短视频（含生活提问）29min。娱乐以"听歌"和"刷短视频"为主，无游戏类娱乐。凌晨 00:01~00:43 听歌 + 01:26~01:55 看短视频是 1h+ 的睡前娱乐，这部分时间直接侵蚀了睡眠</div>
        <div class="h-time">3 段娱乐：00:01~00:43（42min）听歌曲评价 / 01:26~01:55（29min）看短视频+准备睡觉 / 10:29~10:58（29min）刷短视频</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🍽️</span>
      <div>
        <div class="h-text">餐饮 1h10m（占 4.9%）：5 段餐饮。① 12:13~12:21 吃午饭（罗氏沼虾）8min ② 12:21~12:45 继续吃午饭 24min ③ 12:45~12:55 吃完测量剩余 + 记录饮水 10min ④ 12:58~13:10 蒸新到的罗氏沼虾 + 查询蒸熟时间 12min ⑤ 17:37~17:53 准备吃虾（晚饭）16min。午饭时间偏长 42min+测量=52min（罗氏沼虾需要剥壳，剥壳时间也计入吃饭）。与女朋友的"在家吃饭洗碗"（19:02~19:27 25min）归到休闲类（社交+家务的复合）</div>
        <div class="h-time">5 段餐饮：12:13~12:21 / 12:21~12:45 / 12:45~12:55 / 12:58~13:10 / 17:37~17:53</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🧹</span>
      <div>
        <div class="h-text">家务 46min（占 3.2%）：4 段家务。① 10:58~11:33 洗衣服收尾/晾晒准备 35min ② 11:33~11:35 晒床单打卡 2min ③ 11:55~12:03 晒衣服 8min ④ 12:03~12:04 晒衣完成打卡 1min。集中处理了"洗衣服+晒衣服+晒床单"，全部在 10:58~12:04 的 1h6m 内完成。家务处理效率较高——分批次完成（先洗衣服再晒衣服再晒床单），符合家务动线</div>
        <div class="h-time">4 段家务：10:58~11:33（35min）洗衣服收尾 / 11:33~11:35（2min）晒床单 / 11:55~12:03（8min）晒衣服 / 12:03~12:04（1min）晒衣完成</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🚴</span>
      <div>
        <div class="h-text">通勤 44min（占 3.1%）：3 段通勤。① 15:06~15:11 出门倒垃圾 5min ② 18:11~18:12 出门倒垃圾 1min ③ 22:09~22:47 逛街结束打车回家 38min。今天通勤核心是晚上打车回家（22:09~22:47 38min），是体力消耗大的一天后的合理选择——22 点还在老门东，叫车回家是明智的。白天两次倒垃圾是家务的延伸</div>
        <div class="h-time">3 段通勤：15:06~15:11 / 18:11~18:12 / 22:09~22:47（38min）打车回家</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">📚</span>
      <div>
        <div class="h-text">学习 38min（占 2.6%）：5 段学习。① 00:49~01:00 元母意程修行 11min（凌晨学习）② 01:09~01:26 QQ 相册批量下载研究 17min ③ 11:35~11:36 查看同步报告 1min ④ 12:04~12:09 等待技术反馈 5min ⑤ 12:09~12:13 查看同步反馈 4min。学习集中在凌晨 + 等待技术反馈。QQ 相册批量下载是技术问题排查，元母意程修行是个人修炼。凌晨学习与晚睡关联，建议白天做技术研究</div>
        <div class="h-time">5 段学习：00:49~01:00 / 01:09~01:26 / 11:35~11:36 / 12:04~12:09 / 12:09~12:13</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🎨</span>
      <div>
        <div class="h-text">兴趣爱好 19min（占 1.3%）：2 段。① 11:36~11:54 修行元母意程 18min ② 11:54~11:55 完成修炼并打卡 1min。元母意程是个人修炼体系（与学习类不同），归到兴趣爱好。每天坚持 18min 修行是好的习惯延续</div>
        <div class="h-time">2 段兴趣：11:36~11:54（18min）修行元母意程 / 11:54~11:55 完成修炼打卡</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🚿</span>
      <div>
        <div class="h-text">洗漱 22min（占 1.5%）：1 段 15:11~15:33 回家刷牙后在家休息 22min。今天只有 1 段洗漱（在 15:11 倒垃圾回家后），早上起床后直接进入家务+吃饭，没有单独洗漱环节。洗漱是 22min 集中在下午，是"家务后的清洁"</div>
        <div class="h-time">1 段洗漱：15:11~15:33（22min）</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">⚠️</span>
      <div>
        <div class="h-text">14:04 重复扫描问题：14:04 这一分钟有 6 条 0 分钟的重复扫描记录 + 1 条 1 分钟的"文档冲突修复确认"= 总共 7 条 14:04 的记录。每条记录的 source_contents 都包含 5 条 14:04 的消息（重复扫描导致）。这是 daily_recorder 技能在 14:04 这一分钟被多次扫描同一文件导致重复录入的痕迹。问题在 14:05~14:15 通过删除 001.db + 检查活跃表得到部分解决，但根本问题（重复扫描）仍需修复（结合元母意程的"meta.db 滚动设计"讨论）</div>
        <div class="h-time">⚠️ 14:04 重复扫描：6 条 0 分钟记录（重复扫描 5 轮）</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">💕</span>
      <div>
        <div class="h-text">凌晨不睡觉问题：00:00~01:55 共 1h55m 各种活动：00:00~00:01 工作 + 00:01~00:43 听歌 + 00:43~00:49 工作 + 00:49~01:00 学习 + 01:00~01:09 沟通 + 01:09~01:26 学习 + 01:26~01:55 看短视频 + 01:55 入睡。1h55m 频繁切换活动（7 次切换），是"晚睡强迫症"的表现——刷手机/听歌/处理工作就是不想睡。结果：睡眠时间被压缩到 7h6m。建议：23:30 前关手机、停止所有屏幕活动、做"睡前仪式"（洗漱/冥想/看纸质书）</div>
        <div class="h-time">00:00~01:55 共 1h55m 频繁切换 7 次活动</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">✅</span>
      <div>
        <div class="h-text">周四做得好的地方：① 睡眠 7h6m 接近推荐 ② 运动回归 1h12m（八段锦 62min）打破 4 天僵局 ③ 社交 3h41m（与女朋友外出吃饭+逛街老门东）④ 家务 46min 集中处理洗衣服+晒衣服 ⑤ 工作 1h31m 解决 db 重复扫描问题 + 多 db 设计 ⑥ 餐饮 1h10m 健康（罗氏沼虾营养记录完整）⑦ 八段锦练习 62min 是好的精神活动 ⑧ 与女朋友的陪伴时间充足 ⑨ 22:47 回家准备入睡（不再熬夜）</div>
      </div>
    </div>'''

# ============ 睡眠分析 ============
sleep_html = f'''    <div class="highlight-row">
      <span class="h-emoji">&#x1F319;</span>
      <div>
        <div class="h-text">主睡眠 01:55~09:01 共 7h6m：单段无中断的整夜睡眠。从 01:55 入睡到 09:01 起床，7h6m 处于"深度睡眠+REM 循环"的标准周期内（4-5 个 90min 周期）。01:55 入睡不算太晚，但比 23:00 推荐入睡时间晚了 3h。9:01 起床后进入"起床后清醒/日常起居"（88min），是健康的起床节奏，无赖床</div>
        <div class="h-time">01:55~09:01 持续 7h6m</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4CA;</span>
      <div>
        <div class="h-text">总睡眠 7h6m（1 段），占全天 29.6%。在 7-9h 推荐范围之内（接近下限）。相比昨天（06-24: 7h50m）少 44min，相比前天（06-23: 12h11m）少 5h5m。睡眠结构简单：单段长睡眠，无午睡，无短醒——是"睡眠不足但质量不错"的模式。今日 1h55m 凌晨活动是导致睡眠不足的直接原因</div>
        <div class="h-time">总 7h6m（1 段）✓ 正常（接近下限）</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F552;</span>
      <div>
        <div class="h-text">09:01 起床时间：起床后进入 88min 的"起床后清醒/日常起居"（9:01~10:29），是健康的起床节奏——无赖床，有过渡。然后 10:29~10:58 刷短视频 29min，10:58 开始家务（洗衣服）。建议：保持 8:00~9:00 起床，7-9h 睡眠（23:00~23:30 入睡最理想）</div>
        <div class="h-time">09:01 起床 → 10:29 进入日常</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F634;</span>
      <div>
        <div class="h-text">凌晨不睡觉的代价：00:00~01:55 共 1h55m 切换 7 次活动（工作/听歌/工作/学习/沟通/学习/看短视频），这是"晚睡强迫症"——明知该睡了但不停切换活动刷存在感。结果：① 睡眠压缩到 7h6m（接近下限）② 9:01 起床时仍感疲劳 ③ 14:32 头疼躺下休息 25min（白天精力透支）④ 22:47 才回到床上（又是凌晨 1 点+ 才会困）。形成"晚睡→睡眠不足→白天累→继续熬"的恶性循环</div>
        <div class="h-time">00:00~01:55 共 1h55m 切换 7 次活动 ⚠️ 晚睡强迫症</div>
      </div>
    </div>'''

# ============ 改善建议 ============
suggest_html = f'''    <div class="highlight-row">
      <span class="h-emoji">&#x1F634;</span>
      <div>
        <div class="h-text">晚睡问题（最重要）⚠️：00:00~01:55 共 1h55m 切换 7 次活动，01:55 才入睡——这是连续多天的"凌晨 2 点入睡"模式。建议：① 23:00 停止所有屏幕活动（手机/电脑）② 23:00~23:30 做"睡前仪式"（洗漱/冥想/看纸质书/听白噪音）③ 设定 22:30 闹钟提醒"准备睡觉" ④ 把"不工作"作为入睡前的最后决策（不要让工作侵蚀睡眠）⑤ 入睡时间控制在 23:00~23:30 ⑥ 7-9h 睡眠是健康的核心，晚 1h 早 1h 都影响白天的精力</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F3C3;</span>
      <div>
        <div class="h-text">运动继续保持：今天 1h12m 运动（八段锦 62min + 健身 10min），打破 4 天僵局 ✅。但仍需加强。建议：① 每天 30min 主动运动（八段锦/散步/骑车/瑜伽）② 上午 10:00 站立伸展 10min（打破久坐）③ 下午 15:00 散步 20min（户外活动）④ 晚饭后 19:30 室内走动 15min ⑤ 每天 1 万步（用手机计步器监控）⑥ 运动是睡眠的最好保证（运动后入睡更快）</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4A4;</span>
      <div>
        <div class="h-text">14:32 头疼躺下问题：12:55~14:32 高强度工作 1h37m 后 14:32~14:57 头疼躺下休息 25min。这是身体的警告信号——工作强度过大或睡眠不足的累积反应。建议：① 工作 1h 休息 10min（番茄工作法）② 下午 14:00 后避免高强度工作（脑力疲劳）③ 头疼时立即躺下（14:32 的选择是对的）④ 增加白天的水分摄入（口渴会加剧头疼）⑤ 如果头疼频繁出现，建议体检（排查血压/颈椎问题）</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4BE;</span>
      <div>
        <div class="h-text">db 重复扫描问题 ⚠️：14:04 出现 6 条 0 分钟重复扫描记录，是 daily_recorder 技能在同一分钟被多次扫描同一文件导致。这影响 ① 数据准确性（重复录入）② 报告质量（噪音记录）③ 性能（重复扫描浪费资源）。建议：① 在 daily_recorder 加"扫描频率限制"（同一文件 5min 内不重复扫描）② 在 add_record 时加"内容去重"（基于 message_id 主键）③ meta.db 设计"扫描历史"表（避免重复扫描同一文件）④ 14:05~14:15 已删除 001.db 测试库，但根本问题需要修复</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4DA;</span>
      <div>
        <div class="h-text">学习时间：今天 38min 学习分散在凌晨（00:49~01:26 共 28min 元母意程 + QQ 相册批量下载）和中午（11:35~12:13 共 10min 等待技术反馈）。凌晨学习损伤大，建议把技术研究类学习移到白天。建议：① 22:00 后不学新知识（睡前学习影响入睡）② 上午 10:00~12:00 集中学习（精神最好）③ 晚上 20:00~21:00 复盘总结（一天所学）④ 学习内容记录到"备忘录"便于回顾</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F37D;&#xFE0F;</span>
      <div>
        <div class="h-text">餐饮 1h10m 健康：5 段餐饮集中处理（罗氏沼虾午饭 + 蒸虾 + 晚饭准备），与前几天的 4h+ 焖饭流程相比已经大幅缩短。罗氏沼虾需要剥壳，剥壳时间计入吃饭时间是合理的（这是吃饭的延续）。建议：① 继续罗氏沼虾作为优质蛋白来源 ② 蒸虾比炒虾更健康（少油） ③ 每天喝水量继续记录（今天记了 2000ml ✓） ④ 晚饭 17:37~17:53 16min 较快（与女朋友外出吃饭前）</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F3E0;</span>
      <div>
        <div class="h-text">家务 46min 集中处理：10:58~12:04 集中处理洗衣服+晒衣服+晒床单，全部在 1h6m 内完成。家务处理效率高——分批次完成（先洗衣服再晒衣服再晒床单），符合家务动线。建议：① 周末集中处理大件家务（深度清洁/换季衣物）② 每天小家务（收拾/倒垃圾/洗碗）≤15min ③ 晒衣服尽量上午（11:00 前晾晒，下午不易干） ④ 15:06 和 18:11 两次倒垃圾——可以在出门时顺便倒，不必专门下楼</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F495;</span>
      <div>
        <div class="h-text">社交 3h41m 是亮点：与女朋友的相处时间很充分（18:12~22:09 共 3h57m 外出）。这与"半年不工作寻找意义"的计划契合——在技术工作之外，有真实的情感连接。建议：① 继续保持每周 1-2 次外出约会 ② 22:09 打车回家是明智选择（不要因为省钱而步行很久）③ 回家后 22:47 准备入睡是好的节奏（不再熬夜）④ 周末可以尝试不同的活动（公园/展览/电影/演出）</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F3B5;</span>
      <div>
        <div class="h-text">给王大为做歌的后续：00:01~00:43 听歌曲评价 42min——这是昨天（06-24）做的歌的评价和反馈。说明用户对创作的成果有持续关注。建议：① 创作类工作的"反馈循环"很重要（做歌→评价→调整）② 创作流程可以继续优化（采访问题清单/歌词审查标准）③ 凌晨 0:01~0:43 听歌+评价 42min 持续了 1 天，这是"创作完成后的收尾" ④ 未来可以继续做类似的工作（朋友生日/纪念日/其他朋友）</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4F1;</span>
      <div>
        <div class="h-text">凌晨活动模式：00:00~01:55 共 1h55m 切换 7 次活动，9 个 block 块。这是"不想睡"的表现——明知 00:00 了但不停刷手机/听歌/工作。建议：① 23:00 关闭所有电子设备（包括手机）② 把手机放在客厅充电（物理隔离）③ 床头放一本书/白噪音机/冥想 App ④ 23:30 上床后不再起身（避免"再玩 5 分钟"） ⑤ 连续 7 天 23:30 入睡能形成新的生物钟</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4DD;</span>
      <div>
        <div class="h-text">心愿功能：01:26~01:55 心愿加入 29min（凌晨 1 点半还在玩心愿功能）。心愿功能的核心是"长期目标的可视化"，凌晨玩这个功能说明：① 用户在思考长期目标 ② 习惯性地把心愿记录到系统中 ③ 但凌晨玩可能影响入睡。建议：① 心愿添加在白天 9:00~21:00 ② 心愿回顾每周 1 次（周日晚上）③ 心愿进度跟踪（完成的打钩）④ 心愿与每日检查联动（未完成心愿提醒）</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F3AF;</span>
      <div>
        <div class="h-text">今日改进优先级：① 23:30 前入睡（最优先）② 每天 30min 运动（维持 1h12m 的水平）③ 工作 1h 休息 10min（避免下午头疼）④ db 重复扫描修复（影响所有报告）⑤ 减少凌晨切换活动（23:00 关机）⑥ 晚饭后不再工作（22:00 后进入"放松模式"）⑦ 元母意程修行保持每天 18min</div>
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

REPORT_PATH = Path('/mnt/d/2Study/StudyNotes/SKILLS/作息管家/reports/2026-06-25.html')
REPORT_PATH.write_text(html, encoding='utf-8')
print(f"✓ HTML 报告已生成: {REPORT_PATH}")
print(f"  文件大小: {REPORT_PATH.stat().st_size} bytes")
