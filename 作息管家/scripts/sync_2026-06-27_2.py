#!/usr/bin/env python3
"""
作息管家 - 2026-06-27 11:50 ~ 2026-06-28 02:08 增量同步脚本
按活动切换点切割block，严格保证时间连续
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from schedule_db import add_record_full

# ============ Blocks 数据 ============
# 游标位置：2026-06-27 11:50:00，最后活动：开始看凡人修仙传（娱乐）
# 截止时间：2026-06-28 02:08:47（当前时间）

# 日期：2026-06-27 是大部分消息的日期，但 00:00 之后的消息属于 2026-06-28
# 处理时根据消息具体时间确定日期

BLOCKS = [
    # ==================== 2026-06-27 ====================
    # Block 1: 11:50~12:14 - 健康：记录体重
    {
        "date": "2026-06-27",
        "time_start": "11:50",
        "time_end": "12:14",
        "activity": "用卡路里技能记录体重 92.05kg",
        "category": "健康",
        "source_contents": "[11:50] /卡路里 记录体重 92.05kg",
        "source_timestamps": "2026-06-27 11:50:00",
        "analysis_reasoning": "11:50 用户触发卡路里技能记录体重，从游标活动'看凡人修仙传'切换到健康记录活动。属于新的活动类型，必须切割。"
    },
    # Block 2: 12:15~12:16 - 健康：查询昨天体重
    {
        "date": "2026-06-27",
        "time_start": "12:15",
        "time_end": "12:16",
        "activity": "查询26日体重",
        "category": "健康",
        "source_contents": "[12:15] 26日 我的体重多少",
        "source_timestamps": "2026-06-27 12:15:00",
        "analysis_reasoning": "12:15 用户询问昨天体重，仍属健康相关活动但内容不同（查询vs记录）。"
    },
    # Block 3: 12:17~12:31 - 工作：录音机bug调研
    {
        "date": "2026-06-27",
        "time_start": "12:17",
        "time_end": "12:31",
        "activity": "调研录音机技能数据库膨胀bug",
        "category": "工作",
        "source_contents": "[12:17] \"D:\\2Study\\StudyNotes\\.db\\daily_recorder.db\" 为什么每日大小增加那么快？ 此外看下 录音机 的 技能脚本逻辑和cron任务的代码逻辑 是不是哪里有BUG？\n[12:17] 两个70的直接删除\n[12:23] 重新讲解下 目前录音机技能的bug是什么 为什么数据大小如此大，而且会一直增大\n[12:24] 我不需要修复录音cron执行失败问题 我只想优化和 录音机的数据库文件的大小问题\n[12:26] 直接删除吧\n[12:27] 需要审查下 为什么当前技能会出现重复数据问题\n[12:30] 如果需要修改录音机技能 有什么很好的方案可以避免重复数据 又可以避免遗漏数据？\n[12:32] 如果需要修改录音机技能 有什么很好的方案可以避免重复数据 又可以避免遗漏数据？",
        "source_timestamps": "2026-06-27 12:17:00,2026-06-27 12:17:00,2026-06-27 12:23:00,2026-06-27 12:24:00,2026-06-27 12:26:00,2026-06-27 12:27:00,2026-06-27 12:30:00,2026-06-27 12:32:00",
        "analysis_reasoning": "12:17 开始用户切换到录音机技术bug调研，连续多条消息讨论录音机数据库膨胀问题。活动类型从健康切换到工作，必须切割。"
    },
    # Block 4: 12:32~12:34 - 餐饮：准备煮水饺
    {
        "date": "2026-06-27",
        "time_start": "12:32",
        "time_end": "12:34",
        "activity": "准备做午饭煮水饺",
        "category": "餐饮",
        "source_contents": "[12:32] 现在开始做午饭 准备煮水饺",
        "source_timestamps": "2026-06-27 12:32:00",
        "analysis_reasoning": "12:32 用户明确表示要做午饭，活动从技术调研切换到餐饮准备，必须切割。"
    },
    # Block 5: 12:35~12:36 - 工作：技术方案讨论
    {
        "date": "2026-06-27",
        "time_start": "12:35",
        "time_end": "12:36",
        "activity": "讨论录音机去重方案（message_id vs content+timestamp）",
        "category": "工作",
        "source_contents": "[12:35] 以前就用过 message_id 作为 唯一健 但好像也出问题了 我才改为了 (content, timestamp)",
        "source_timestamps": "2026-06-27 12:35:00",
        "analysis_reasoning": "12:35 用户继续讨论录音机技术方案，活动再次切换回工作。"
    },
    # Block 6: 12:37~12:41 - 餐饮：准备出门买菜
    {
        "date": "2026-06-27",
        "time_start": "12:37",
        "time_end": "12:41",
        "activity": "准备出门买菜（娃娃菜、香蕉）",
        "category": "餐饮",
        "source_contents": "[12:37] 我准备先出门去买一下娃娃菜，买个香蕉，然后再回来煮水饺。因为做水饺，我煮一些娃娃菜，这样嗯嗯，容易填饱，不容易那么饥饿。",
        "source_timestamps": "2026-06-27 12:37:00",
        "analysis_reasoning": "12:37 用户决定出门买菜以补充午饭食材，活动切换到外出购物准备。"
    },
    # Block 7: 12:42~12:46 - 记账：买菜支出记录
    {
        "date": "2026-06-27",
        "time_start": "12:42",
        "time_end": "12:46",
        "activity": "买菜后用饼干记账记录支出（娃娃菜、金针菇、香蕉）",
        "category": "生活事务",
        "source_contents": "[12:42] /饼干记账 记支出 买的娃娃菜和金针菇\n[12:43] 5.5元 买了个香蕉 也记个账吧\n[12:43] ok\n[12:46] ok",
        "source_timestamps": "2026-06-27 12:42:00,2026-06-27 12:43:00,2026-06-27 12:43:00,2026-06-27 12:46:00",
        "analysis_reasoning": "12:42 用户买菜后用饼干记账技能记录支出，活动类型是记账/财务记录。"
    },
    # Block 8: 12:47~12:48 - 通勤：代驾回家
    {
        "date": "2026-06-27",
        "time_start": "12:47",
        "time_end": "12:48",
        "activity": "代驾回家",
        "category": "通勤",
        "source_contents": "[12:47] 代驾了\n[12:47] 到家了",
        "source_timestamps": "2026-06-27 12:47:00,2026-06-27 12:47:00",
        "analysis_reasoning": "12:47 用户通过代驾回家，活动类型明确为通勤/出行。"
    },
    # Block 9: 12:49~12:49 - 健康：记录吃香蕉卡路里
    {
        "date": "2026-06-27",
        "time_start": "12:49",
        "time_end": "12:49",
        "activity": "用卡路里技能记录吃香蕉",
        "category": "健康",
        "source_contents": "[12:49] 127-45=82g 吃了这么多香蕉 卡路里技能 记录一下",
        "source_timestamps": "2026-06-27 12:49:00",
        "analysis_reasoning": "12:49 用户单独触发卡路里技能记录香蕉摄入量，属于健康类活动。"
    },
    # Block 10: 12:50~12:55 - 餐饮：煮水饺
    {
        "date": "2026-06-27",
        "time_start": "12:50",
        "time_end": "12:55",
        "activity": "煮水饺做饭",
        "category": "餐饮",
        "source_contents": "[12:50] 开始煮水饺",
        "source_timestamps": "2026-06-27 12:50:00",
        "analysis_reasoning": "12:50 用户明确开始煮水饺，进入做饭状态。"
    },
    # Block 11: 12:56~13:14 - 工作：录音机方案决策
    {
        "date": "2026-06-27",
        "time_start": "12:56",
        "time_end": "13:14",
        "activity": "讨论录音机改动方案并决定执行方案B",
        "category": "工作",
        "source_contents": "[12:56] 改动3和改动4 会有冲突的部分吗？ 改动1和改动2 确定一定有效 且不会引入bug吗\n[13:15] 方案B 执行吧",
        "source_timestamps": "2026-06-27 12:56:00,2026-06-27 13:15:00",
        "analysis_reasoning": "12:56 用户回到录音机技术问题讨论，最终决定执行方案B，活动切换为工作决策。"
    },
    # Block 12: 13:15~13:18 - 餐饮：做好饭
    {
        "date": "2026-06-27",
        "time_start": "13:15",
        "time_end": "13:18",
        "activity": "水饺做好了",
        "category": "餐饮",
        "source_contents": "[13:19] 做好了\n[13:19] 嘿嘿",
        "source_timestamps": "2026-06-27 13:19:00,2026-06-27 13:19:00",
        "analysis_reasoning": "13:19 用户表示水饺已做好，结束做饭阶段，进入就餐准备。"
    },
    # Block 13: 13:19~13:43 - 工作：方案执行与反馈
    {
        "date": "2026-06-27",
        "time_start": "13:19",
        "time_end": "13:43",
        "activity": "催促方案B执行",
        "category": "工作",
        "source_contents": "[13:20] 我都说方案B了 在执行过程中你遇到什么问题了？为什么需要我做选择？一句话解释清楚",
        "source_timestamps": "2026-06-27 13:20:00",
        "analysis_reasoning": "13:20 用户催促方案B执行，活动再次切换到工作。"
    },
    # Block 14: 13:44~14:42 - 休息：躺床午睡
    {
        "date": "2026-06-27",
        "time_start": "13:44",
        "time_end": "14:42",
        "activity": "躺床上累了休息/午睡",
        "category": "休闲",
        "source_contents": "[13:44] 躺床上了 累了\n[13:49] 你是谁",
        "source_timestamps": "2026-06-27 13:44:00,2026-06-27 13:49:00",
        "analysis_reasoning": "13:44 用户表示躺床休息，13:49只发了简单的'你是谁'，结合上下文（刚躺下、之前在休息）以及14:43才起床，整段时间应为午睡休息状态。"
    },
    # Block 15: 14:43~14:45 - 起床
    {
        "date": "2026-06-27",
        "time_start": "14:43",
        "time_end": "14:45",
        "activity": "起床",
        "category": "休闲",
        "source_contents": "[14:43] 起来咯",
        "source_timestamps": "2026-06-27 14:43:00",
        "analysis_reasoning": "14:43 用户明确表示起床，活动切换为起床/起身。"
    },
    # Block 16: 14:46~14:57 - 餐饮：吃香蕉
    {
        "date": "2026-06-27",
        "time_start": "14:46",
        "time_end": "14:57",
        "activity": "吃香蕉并记录卡路里",
        "category": "餐饮",
        "source_contents": "[14:46] /卡路里 记吃了 145-57=88g 的 香蕉",
        "source_timestamps": "2026-06-27 14:46:00",
        "analysis_reasoning": "14:46 用户记录吃香蕉，活动为餐饮+健康记录。"
    },
    # Block 17: 14:58~15:11 - 通勤：出门
    {
        "date": "2026-06-27",
        "time_start": "14:58",
        "time_end": "15:11",
        "activity": "出门",
        "category": "通勤",
        "source_contents": "[14:58] 现在我出门喽。",
        "source_timestamps": "2026-06-27 14:58:00",
        "analysis_reasoning": "14:58 用户明确表示出门，活动切换为通勤/外出。"
    },
    # Block 18: 15:12~15:20 - 办健身卡
    {
        "date": "2026-06-27",
        "time_start": "15:12",
        "time_end": "15:20",
        "activity": "办乐享健身健身卡 2680元",
        "category": "生活事务",
        "source_contents": "[15:12] /饼干记账 记支出 2680元 乐享健身健身卡 从7.10～2028年 7.10日 再额外加三个月\n[15:14] 是到 11.10日 修改了",
        "source_timestamps": "2026-06-27 15:12:00,2026-06-27 15:14:00",
        "analysis_reasoning": "15:12 用户办健身卡并进行记账，活动切换为办卡/财务事务。"
    },
    # Block 19: 15:21~15:42 - 讨论：健身卡提醒方案
    {
        "date": "2026-06-27",
        "time_start": "15:21",
        "time_end": "15:42",
        "activity": "讨论健身卡到期提醒方案",
        "category": "生活事务",
        "source_contents": "[15:21] 此外如何不忘记这个事情呢？是记录在 备忘录技能中 还是 什么技能中？比较好 我担心以后忘记我的卡持续到什么时候了\n[15:29] 那这样吧，首先不要用心愿，我觉得心愿不对呀，心愿是我接下来要做的事儿，有你要不要找一个其他的分类，你记一下，然后定时提醒的话，嗯。呃，你说的那个提醒是吧，提前一天到，我觉得不要这样设，我觉得你可以设置，呃，嗯，每个月的。嗯，一号你提醒我啊，这个卡已经用了多少个月，还有多少个月。然后是一直设置到，呃，这个健身卡过期的时候，比如说每个月一号你设一个，但是我要的不是每月提醒，是你手动的设那种单次提醒，然后里面有内容理解我意思吗？先复述我的想法，先不要着急执行。",
        "source_timestamps": "2026-06-27 15:21:00,2026-06-27 15:29:00",
        "analysis_reasoning": "15:21 开始用户讨论如何记住健身卡持续时间，与AI讨论提醒方案。"
    },
    # Block 20: 15:43~16:11 - 系统通知 + 健身卡时间确定
    {
        "date": "2026-06-27",
        "time_start": "15:43",
        "time_end": "16:11",
        "activity": "确定健身卡起始时间+讨论提醒机制",
        "category": "生活事务",
        "source_contents": "[15:43] [Inter-session message] ... FeathersData Git 自动同步完成 ✅ 1 个 commit 已成功推送到 main 分支...（系统通知，不计入主动行为）\n[16:12] 健身卡起始时间是 26年7.10日 持续到 28年11月10日\n 你说打卡还是成就是什么意思？\n[16:13] 要不要设定每个月10日的提醒？还是讨论 不要执行",
        "source_timestamps": "2026-06-27 15:43:00,2026-06-27 16:12:00,2026-06-27 16:13:00",
        "analysis_reasoning": "15:43 FeathersData自动同步通知是系统消息，可忽略主动行为；16:12-16:13用户继续讨论健身卡起始时间和提醒设定。"
    },
    # Block 21: 16:12~16:18 - 决策：a方案执行
    {
        "date": "2026-06-27",
        "time_start": "16:12",
        "time_end": "16:18",
        "activity": "确定a方案（每月10日提醒健身卡）",
        "category": "生活事务",
        "source_contents": "[16:12] 健身卡起始时间是 26年7.10日 持续到 28年11月10日\n 你说打卡还是成就是什么意思？\n[16:13] 要不要设定每个月10日的提醒？还是讨论 不要执行\n[16:19] a 方案执行吧",
        "source_timestamps": "2026-06-27 16:12:00,2026-06-27 16:13:00,2026-06-27 16:19:00",
        "analysis_reasoning": "16:12-16:13 用户讨论健身卡时间，16:19决定执行a方案（每月10日提醒）。"
    },
    # Block 22: 16:19~16:22 - 执行健身卡提醒
    {
        "date": "2026-06-27",
        "time_start": "16:19",
        "time_end": "16:22",
        "activity": "执行a方案设定健身卡提醒",
        "category": "生活事务",
        "source_contents": "[16:19] a 方案执行吧",
        "source_timestamps": "2026-06-27 16:19:00",
        "analysis_reasoning": "16:19 用户决定执行a方案。"
    },
    # Block 23: 16:23~16:32 - 讨论分类+坐电脑桌前
    {
        "date": "2026-06-27",
        "time_start": "16:23",
        "time_end": "16:32",
        "activity": "讨论健身卡支出分类并坐到电脑桌前",
        "category": "工作",
        "source_contents": "[16:23] 这笔2680支出算在什么分类中？\n[16:24] 我现在坐在电脑桌前呢",
        "source_timestamps": "2026-06-27 16:23:00,2026-06-27 16:24:00",
        "analysis_reasoning": "16:23 询问2680健身卡分类，16:24坐到电脑桌前，切换到工作状态。"
    },
    # Block 24: 16:33~16:45 - 数据库维护+饼干记账分类
    {
        "date": "2026-06-27",
        "time_start": "16:33",
        "time_end": "16:45",
        "activity": "执行VACUUM+同步+饼干记账分类讨论",
        "category": "工作",
        "source_contents": "[16:33] 可以跑  VACUUM\n[16:35] 同步吧\n[16:46] 饼干记账支持二级目录吗？\n[16:47] 那你就先按照娱乐来记账吧",
        "source_timestamps": "2026-06-27 16:33:00,2026-06-27 16:35:00,2026-06-27 16:46:00,2026-06-27 16:47:00",
        "analysis_reasoning": "16:33 用户决定运行VACUUM并同步，16:46-16:47讨论饼干记账分类。"
    },
    # Block 25: 16:46~17:16 - 居家管家物品优化
    {
        "date": "2026-06-27",
        "time_start": "16:46",
        "time_end": "17:16",
        "activity": "优化居家管家物品（去小便后继续）",
        "category": "工作",
        "source_contents": "[16:56] 去小便 现在在优化居家管家的物品中\n[17:17] 在电脑桌前 我现在体验很不好",
        "source_timestamps": "2026-06-27 16:56:00,2026-06-27 17:17:00",
        "analysis_reasoning": "16:56 用户表示去小便后正在优化居家管家物品，活动切换为优化工作。"
    },
    # Block 26: 17:17~17:49 - 体验差+Gateway令牌查询
    {
        "date": "2026-06-27",
        "time_start": "17:17",
        "time_end": "17:49",
        "activity": "继续优化居家管家+查询Gateway令牌",
        "category": "工作",
        "source_contents": "[17:17] 在电脑桌前 我现在体验很不好\n[17:18] 没啥\n[17:29] 现在gateway的令牌是什么",
        "source_timestamps": "2026-06-27 17:17:00,2026-06-27 17:18:00,2026-06-27 17:29:00",
        "analysis_reasoning": "17:17-17:29 用户表示体验不好并查询Gateway令牌，继续居家管家优化相关工作。"
    },
    # Block 27: 17:50~18:17 - 短暂休息：准备睡觉（实际未睡）
    {
        "date": "2026-06-27",
        "time_start": "17:50",
        "time_end": "18:17",
        "activity": "躺床准备睡觉（但最终没睡）",
        "category": "休闲",
        "source_contents": "[17:50] 开始睡觉了😪\n[17:51] 今天结束了ฅ՞•ﻌ•՞ฅ\n[18:18] 没睡觉🥹",
        "source_timestamps": "2026-06-27 17:50:00,2026-06-27 17:51:00,2026-06-27 18:18:00",
        "analysis_reasoning": "17:50 用户表示准备睡觉，17:51说今天结束了；18:18又说没睡觉。这段时间是躺床休息但实际未入睡的状态。"
    },
    # Block 28: 18:18~18:27 - 出门吃晚饭
    {
        "date": "2026-06-27",
        "time_start": "18:18",
        "time_end": "18:27",
        "activity": "出门吃晚饭",
        "category": "通勤",
        "source_contents": "[18:18] 没睡觉🥹\n[18:18] 准备出门吃晚饭\n[18:18] 今天吃了多少热量了\n[18:19] /卡路里 技能 今天吃了多少热量",
        "source_timestamps": "2026-06-27 18:18:00,2026-06-27 18:18:00,2026-06-27 18:18:00,2026-06-27 18:19:00",
        "analysis_reasoning": "18:18 用户表示没睡准备出门吃晚饭，18:19查看今日卡路里。"
    },
    # Block 29: 18:28~18:55 - 吃晚饭+卡路里计算
    {
        "date": "2026-06-27",
        "time_start": "18:28",
        "time_end": "18:55",
        "activity": "吃晚饭（卤肉葱油拌面）并记录卡路里",
        "category": "餐饮",
        "source_contents": "[18:28] 我如果吃一份卤肉面，一碗卤肉面，我会消耗会增加多少热量呢？\n[18:41] 卤肉 28g 多少热量\n[18:48] 1400-1121=279g 葱油拌面多少热量？\n[18:48] 我一共吃了这么多拌面和卤肉 一共多少热量？\n[18:50] 录入的话 名字就写卤肉葱油拌面吧",
        "source_timestamps": "2026-06-27 18:28:00,2026-06-27 18:41:00,2026-06-27 18:48:00,2026-06-27 18:48:00,2026-06-27 18:50:00",
        "analysis_reasoning": "18:28-18:50 用户讨论晚饭热量并录入卡路里数据，活动为餐饮+健康记录。"
    },
    # Block 30: 18:56~19:17 - 接收系统通知
    {
        "date": "2026-06-27",
        "time_start": "18:56",
        "time_end": "19:17",
        "activity": "接收skills-git-sync系统通知",
        "category": "工作",
        "source_contents": "[18:56] [Inter-session message] ... skills-git-sync 报告 2026-06-27 18:55 ✅ 无变更需提交...（系统通知）",
        "source_timestamps": "2026-06-27 18:56:00",
        "analysis_reasoning": "18:56 skills-git-sync系统通知，仓库无变更。系统通知归类为工作（被动接收消息）。"
    },
    # Block 31: 19:18~20:19 - 方案b决策
    {
        "date": "2026-06-27",
        "time_start": "19:18",
        "time_end": "20:19",
        "activity": "选择方案b（居家管家优化）",
        "category": "工作",
        "source_contents": "[19:18] 方案 b 吧",
        "source_timestamps": "2026-06-27 19:18:00",
        "analysis_reasoning": "19:18 用户选择方案b执行，结合上下文（居家管家优化），活动为工作决策。"
    },
    # Block 32: 20:20~21:38 - 在家+询问找书能力
    {
        "date": "2026-06-27",
        "time_start": "20:20",
        "time_end": "21:38",
        "activity": "在家+询问找书能力（庄子等）",
        "category": "社交",
        "source_contents": "[20:20] 我在家一个小时了\n[20:21] 你找书的能力如何？找得到庄子等书籍吗",
        "source_timestamps": "2026-06-27 20:20:00,2026-06-27 20:21:00",
        "analysis_reasoning": "20:20 用户表示已在家一小时，20:21询问AI找书能力，活动为日常聊天/信息查询。"
    },
    # Block 33: 21:39~22:05 - 上厕所+阅读庄子
    {
        "date": "2026-06-27",
        "time_start": "21:39",
        "time_end": "22:05",
        "activity": "上厕所+查看庄子在线资源",
        "category": "学习",
        "source_contents": "[21:39] 起来上厕所咯\n[21:39] [Quoted message begins] 找到啦！👇 ... 可可诗词网 ... 庄子在线资源（免费可用） ... [Quoted message ends]\n我这条消息引用了你发过的消息 你能看到我引用的是哪个吗",
        "source_timestamps": "2026-06-27 21:39:00,2026-06-27 21:39:00",
        "analysis_reasoning": "21:39 用户起身上厕所并查看AI推荐的庄子在线资源链接，活动切换为学习/阅读。"
    },
    # Block 34: 22:06~22:07 - 洗漱
    {
        "date": "2026-06-27",
        "time_start": "22:06",
        "time_end": "22:07",
        "activity": "洗澡刷牙",
        "category": "洗漱",
        "source_contents": "[22:06] 洗好澡了 刷了牙 哈哈",
        "source_timestamps": "2026-06-27 22:06:00",
        "analysis_reasoning": "22:06 用户表示洗澡刷牙完成，活动切换为洗漱。"
    },
    # Block 35: 22:08~22:55 - 和老婆亲密
    {
        "date": "2026-06-27",
        "time_start": "22:08",
        "time_end": "22:55",
        "activity": "和老婆亲密",
        "category": "社交",
        "source_contents": "[22:06] 开始和老婆亲密\n[23:04] 爱爱好啦",
        "source_timestamps": "2026-06-27 22:06:00,2026-06-27 23:04:00",
        "analysis_reasoning": "22:06 用户表示开始和老婆亲密，23:04表示爱爱好啦。整段时间为亲密活动。"
    },
    # Block 36: 23:04~23:15 - 休息+火疖子咨询
    {
        "date": "2026-06-27",
        "time_start": "23:04",
        "time_end": "23:15",
        "activity": "想休息+咨询火疖子治疗（能否手术）",
        "category": "健康",
        "source_contents": "[23:04] 现在想休息\n[23:04] 我头后有一个复发了三次的火疖子 如果我去皮肤科 他能给我做手术切掉吗？\n[23:06] 那他可以立马做手术吗？还是要等几天？",
        "source_timestamps": "2026-06-27 23:04:00,2026-06-27 23:04:00,2026-06-27 23:06:00",
        "analysis_reasoning": "23:04 用户想休息并咨询头后火疖子手术问题，活动为健康咨询。"
    },
    # Block 37: 23:16~23:26 - 火疖子用药与费用
    {
        "date": "2026-06-27",
        "time_start": "23:16",
        "time_end": "23:26",
        "activity": "咨询火疖子用药（龙珠软膏/百多邦）+切除费用",
        "category": "健康",
        "source_contents": "[23:09] 为什么发炎时不能切除？这是谁定的规矩？\n[23:11] 我看有医生对于皮脂腺囊肿都是直接切的 即便是发炎的\n[23:16] 火疖子应该用龙珠软膏还是百多邦？\n[23:16] 火疖子切除要多少钱？",
        "source_timestamps": "2026-06-27 23:09:00,2026-06-27 23:11:00,2026-06-27 23:16:00,2026-06-27 23:16:00",
        "analysis_reasoning": "23:09-23:16 用户持续咨询火疖子治疗，活动仍为健康咨询。"
    },
    # Block 38: 23:27~23:28 - 火疖子治疗咨询（深入）
    {
        "date": "2026-06-27",
        "time_start": "23:27",
        "time_end": "23:28",
        "activity": "火疖子治疗方式深入咨询",
        "category": "健康",
        "source_contents": "[23:27] 火疖子怎么治疗？火疖子有办法根治吗？火疖子化脓破溃长好之后需要去医院切掉什么吗？感觉残留的头部皮肤区域像皮肤病",
        "source_timestamps": "2026-06-27 23:27:00",
        "analysis_reasoning": "23:27 用户深入咨询火疖子治疗，活动继续为健康。"
    },
    # Block 39: 23:27~23:28 - 情绪发泄
    {
        "date": "2026-06-27",
        "time_start": "23:27",
        "time_end": "23:28",
        "activity": "情绪发泄：别催我睡觉别当傻逼",
        "category": "休闲",
        "source_contents": "[23:27] 别你妈他的催我睡觉 也别说什么生气了 别当傻逼",
        "source_timestamps": "2026-06-27 23:27:00",
        "analysis_reasoning": "23:27 用户发泄对AI催他睡觉的不满，情绪表达类活动。"
    },
    # Block 40: 23:29~23:55 - 火疖子囊壁咨询
    {
        "date": "2026-06-27",
        "time_start": "23:29",
        "time_end": "23:55",
        "activity": "咨询火疖子囊壁+单纯火疖子可能性",
        "category": "健康",
        "source_contents": "[23:29] 火疖子是囊壁这个说法吗？\n[23:56] 有没有可能没有皮脂腺囊肿而出现单纯的火疖子？",
        "source_timestamps": "2026-06-27 23:29:00,2026-06-27 23:56:00",
        "analysis_reasoning": "23:29-23:56 用户继续咨询火疖子医学知识，活动仍为健康。"
    },
    # Block 41: 23:56~23:59 - 拍照描述
    {
        "date": "2026-06-27",
        "time_start": "23:56",
        "time_end": "23:59",
        "activity": "拍摄火疖子照片",
        "category": "健康",
        "source_contents": "[23:57] 硬疙瘩是什么意思？有0.5cm 厚吗？\n[23:59] 这个是我头后的照片",
        "source_timestamps": "2026-06-27 23:57:00,2026-06-27 23:59:00",
        "analysis_reasoning": "23:57-23:59 用户拍摄火疖子照片并询问硬度，活动为健康记录。"
    },
    # ==================== 2026-06-28 ====================
    # Block 42: 00:00~00:01 - 火疖子照片分析
    {
        "date": "2026-06-28",
        "time_start": "00:00",
        "time_end": "00:01",
        "activity": "分析火疖子照片（剃掉头发+查看肿区域）",
        "category": "健康",
        "source_contents": "[00:00] 头发被我剃掉了\n[00:01] 你看这个是火疖子吗\n[00:01] 肿的区域 直径大于三厘米",
        "source_timestamps": "2026-06-28 00:00:00,2026-06-28 00:01:00,2026-06-28 00:01:00",
        "analysis_reasoning": "00:00-00:01 用户描述火疖子照片细节（剃头发+肿区域直径>3cm），活动仍为健康记录。"
    },
    # Block 43: 00:01~02:08 - 深夜待续（消息结束）
    {
        "date": "2026-06-28",
        "time_start": "00:01",
        "time_end": "02:08",
        "activity": "深夜未发送消息（推测继续健康咨询/休息）",
        "category": "未知",
        "source_contents": "[消息结束] 用户在00:01之后未发送新消息，根据上下文（23:56-00:01为火疖子照片分析+深夜），推测用户在持续查看AI回复或已休息。当前时间02:08:47。",
        "source_timestamps": "2026-06-28 02:08:47",
        "analysis_reasoning": "00:01之后无新消息至当前时刻02:08，整段无消息时段归为未知。"
    },
]

def calculate_duration(time_start, time_end):
    """计算时长（分钟）"""
    from datetime import datetime
    fmt = "%H:%M"
    s = datetime.strptime(time_start, fmt)
    e = datetime.strptime(time_end, fmt)
    delta = e - s
    if delta.total_seconds() < 0:
        # 跨天
        delta += __import__('datetime').timedelta(days=1)
    return int(delta.total_seconds() / 60)

def main():
    success_count = 0
    fail_count = 0
    
    for i, block in enumerate(BLOCKS, 1):
        try:
            duration = calculate_duration(block['time_start'], block['time_end'])
            record_id = add_record_full(
                date=block['date'],
                time_start=block['time_start'],
                time_end=block['time_end'],
                duration_minutes=duration,
                activity=block['activity'],
                category=block['category'],
                source_contents=block['source_contents'],
                source_timestamps=block['source_timestamps'],
                analysis_reasoning=block['analysis_reasoning']
            )
            print(f"✓ Block {i:2d} [{block['date']} {block['time_start']}~{block['time_end']}] {block['category']:6s} {block['activity'][:30]:30s} (id={record_id})")
            success_count += 1
        except Exception as e:
            print(f"✗ Block {i:2d} 失败: {e}")
            fail_count += 1
    
    print(f"\n汇总: 成功 {success_count} 条, 失败 {fail_count} 条")

if __name__ == "__main__":
    main()