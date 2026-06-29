#!/usr/bin/env python3
"""
作息管家 - 2026-06-28 严格重做脚本
按"最严格标准"重新生成 6/28 作息表

执行模式：
  默认（dry-run）：只备份 + 打印新 blocks，不写入数据库
  --apply：备份 + 清空 6/28 旧记录 + 写入 26 个新 block
                          ※ 清空操作需用户破例授权（违反"禁止 DELETE"规则，仅此一次）

设计依据：
  - 67 条用户消息（74 条原始 - 7 条 inter-session）
  - messages_per_block=5，最少 14 个 block（ceil(67/5)）
  - 本次设计 26 个 block（满足粒度最大化原则）
  - 时间严格连续 00:00 ~ 23:59
"""
import sys
import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from schedule_db import get_connection, get_records_by_date, add_record_full
from block_count import validate_record_count, get_required_block_count

# ============ 26 个 Block 数据（最严格标准）============

BLOCKS = [
    # ==================== 2026-06-28 ====================
    # Block 1: 00:00~00:32 - 健康：剃头+查看火疖子
    {
        "date": "2026-06-28",
        "time_start": "00:00",
        "time_end": "00:32",
        "activity": "凌晨剃掉头发并查看火疖子照片（直径>3cm）",
        "category": "健康",
        "source_contents": "[00:00:13] 头发被我剃掉了\n[00:01:02] 你看这个是火疖子吗\n[00:01:15] 肿的区域 直径大于三厘米",
        "source_timestamps": "2026-06-28 00:00:13,2026-06-28 00:01:02,2026-06-28 00:01:15",
        "analysis_reasoning": "00:00 用户主动告知剃掉头发，00:01 连续两条消息咨询火疖子（肿区域直径 >3cm），属健康咨询场景。无 inter-session 干扰。3 条消息聚类在同一活动主题，合并为 1 个 block。"
    },
    # Block 2: 00:32~00:39 - 工作：查硬汉健身 skill
    {
        "date": "2026-06-28",
        "time_start": "00:32",
        "time_end": "00:39",
        "activity": "查询健身相关技能（硬汉健身）",
        "category": "工作",
        "source_contents": "[00:32:39] 硬汉健身 有这个相关的 skill 吗？",
        "source_timestamps": "2026-06-28 00:32:39",
        "analysis_reasoning": "00:32 用户突然切换话题查询技能（健身类），属工作/技能配置类。单独成 block，因活动主题与前段健康咨询不同（用户从'自我健康'转向'查 skill 帮忙健身'，性质变化）。"
    },
    # Block 3: 00:39~01:18 - 休闲：躺床上但没睡
    {
        "date": "2026-06-28",
        "time_start": "00:39",
        "time_end": "01:18",
        "activity": "躺床上但尚未入睡（持续清醒）",
        "category": "休闲",
        "source_contents": "[00:39:36] 准备睡觉咯\n[00:40:11] 我先躺床上\n[00:41:11] 刚才抹了一个药膏 叫什么 复方多粘菌素b软膏 感觉头后的疖子 不怎么疼了\n[01:17:56] 还没睡觉",
        "source_timestamps": "2026-06-28 00:39:36,2026-06-28 00:40:11,2026-06-28 00:41:11,2026-06-28 01:17:56",
        "analysis_reasoning": "00:39 准备睡觉，00:40 躺到床上，00:41 反馈抹药效果（疖子不疼），01:17 明确'还没睡觉'。用户躺床后长时间清醒，最终未入睡。属休闲/睡前过渡期，4 条消息同主题（从准备到抹药到确认未睡），合并为一个 block。"
    },
    # Block 4: 01:18~02:08 - 娱乐：看新进职员姜会长第九集
    {
        "date": "2026-06-28",
        "time_start": "01:18",
        "time_end": "02:08",
        "activity": "躺在床上看韩剧《新进职员姜会长》第九集",
        "category": "娱乐",
        "source_contents": "[01:18:20] 准备看会儿 剧\n[01:50:08] 在看新进职员姜会长第九集",
        "source_timestamps": "2026-06-28 01:18:20,2026-06-28 01:50:08",
        "analysis_reasoning": "01:18 决定看剧消磨时间，01:50 通报在看《新进职员姜会长》第九集。2 条消息同主题（看剧），且与前段躺床未睡的活动类型从'休闲'过渡到'娱乐'（明确选择剧目+看剧行为），切分为新 block。"
    },
    # Block 5: 02:08~08:52 - 睡眠：看完剧入睡至次日醒
    {
        "date": "2026-06-28",
        "time_start": "02:08",
        "time_end": "08:52",
        "activity": "看完剧后入睡（持续睡眠，含早晨系统自动同步）",
        "category": "睡眠",
        "source_contents": "[02:08 之后至 08:52] 用户未发送任何消息。期间 06:04-08:09 系统有 6 条 inter-session 自动同步（feathersdata-git-sync / SKILLS Git / workhorse 报告），与用户活动无关。08:52 用户主动发'醒咯'，确认此前处于睡眠状态。",
        "source_timestamps": "2026-06-28 08:52:17",
        "analysis_reasoning": "02:08 是用户最后一条消息（'在看新进职员姜会长第九集'）后 1h18m 的时间锚点——按规范推断用户看完第九集后入睡（第九集单集时长约 1h10m-1h20m）。08:52 用户主动发'醒咯'，确认入睡结束。中间 6h44m 全部归为睡眠，inter-session 消息严格过滤（不计入作息时间线）。source_timestamps 仅记录用户最后消息后的锚点 08:52:17（用户醒来信号）。"
    },
    # Block 6: 08:52~09:51 - 休闲：醒了但一直没起来
    {
        "date": "2026-06-28",
        "time_start": "08:52",
        "time_end": "09:51",
        "activity": "醒了但一直在床上（未起身）",
        "category": "休闲",
        "source_contents": "[08:52:17] 醒咯\n[08:59:32] 还想睡会儿🥱\n[09:27:58] [Emoji: 坏笑]\n[09:51:31] 汗 一直没睡",
        "source_timestamps": "2026-06-28 08:52:17,2026-06-28 08:59:32,2026-06-28 09:27:58,2026-06-28 09:51:31",
        "analysis_reasoning": "08:52 醒咯，08:59 还想睡，09:27 坏笑表情，09:51 反馈'一直没睡'（实际是'一直没起来'，延续在床上状态）。4 条消息全部是躺着状态下的碎片反馈，合并为一个 block。Emoji 单条消息保留为有效信号（用户活跃证据）。"
    },
    # Block 7: 09:51~10:01 - 工作：修行元母意程查询
    {
        "date": "2026-06-28",
        "time_start": "09:51",
        "time_end": "10:01",
        "activity": "查询修行/冥想类应用（元母意程）",
        "category": "工作",
        "source_contents": "[09:52:55] 打算修行元母意程",
        "source_timestamps": "2026-06-28 09:52:55",
        "analysis_reasoning": "09:52 用户突然发起新话题——修行/冥想类应用查询。属技能/信息查询类活动。单独成 block（活动主题与前段'赖床'和后段'健康记录'均不同）。"
    },
    # Block 8: 10:01~10:35 - 健康：记录体重+报身高
    {
        "date": "2026-06-28",
        "time_start": "10:01",
        "time_end": "10:35",
        "activity": "通过 /卡路里 记录体重 91.45kg 并报身高 177cm",
        "category": "健康",
        "source_contents": "[10:01:15] /卡路里 记录体重 91.45kg\n[10:35:24] 177cm",
        "source_timestamps": "2026-06-28 10:01:15,2026-06-28 10:35:24",
        "analysis_reasoning": "10:01 主动调用 /卡路里 记录体重 91.45kg（属健康监测），10:35 补充报身高 177cm（卡路里计算需要的身高参数）。两条消息同主题（个人健康数据登记），合并为一个 block。注：'我现在起来了 等女朋友出发' 出现在 10:35:24 同一条消息里，但其属于'准备出门'的状态描述，归入下个 block（社交）作为时间锚点。"
    },
    # Block 9: 10:35~10:56 - 社交：起床+等女朋友出发
    {
        "date": "2026-06-28",
        "time_start": "10:35",
        "time_end": "10:56",
        "activity": "起床并等女朋友准备出门约会",
        "category": "社交",
        "source_contents": "[10:35:24] 我现在起来了 等女朋友出发☺️",
        "source_timestamps": "2026-06-28 10:35:24",
        "analysis_reasoning": "10:35:24 消息后半段'我现在起来了 等女朋友出发'——起床+准备社交约会。属社交/准备出门场景。注意 10:01-10:35 期间用户已主动起床（10:01 主动记体重），到 10:35 处于'等女朋友'的等待状态。1 条消息但内容明确指示活动类型，单独成 block。"
    },
    # Block 10: 10:56~11:06 - 工作：查居家管家药物（细胞生长因子）
    {
        "date": "2026-06-28",
        "time_start": "10:56",
        "time_end": "11:06",
        "activity": "查询居家管家是否有'细胞生长因子'药物（附火疖子图片）",
        "category": "工作",
        "source_contents": "[10:55:13] [附件: image/jpeg] 火疖子药品照片\n[10:56:02] 居家管家系统中有这个药物吗\n[10:57:09] 你看到图片内容是什么了吗\n[10:57:40] 是不是还有一个生长因子\n[10:58:41] 细胞生长因子 有这个药吗\n[10:59:17] 你搜下",
        "source_timestamps": "2026-06-28 10:55:13,2026-06-28 10:56:02,2026-06-28 10:57:09,2026-06-28 10:57:40,2026-06-28 10:58:41,2026-06-28 10:59:17",
        "analysis_reasoning": "10:55 上传药品照片，10:56-10:59 连续 5 条消息询问居家管家系统中是否有'细胞生长因子'药物——属技能操作类（查询/录入药品）。5+1 附件 = 6 条记录，同主题（查询+讨论药品），合并为一个 block。注：'查询居家管家' 属系统操作类工作，非纯娱乐。"
    },
    # Block 11: 11:06~11:33 - 通勤：出发去新街口
    {
        "date": "2026-06-28",
        "time_start": "11:06",
        "time_end": "11:33",
        "activity": "出发去新街口（移动途中+讨论生长因子对痘痘效果）",
        "category": "通勤",
        "source_contents": "[11:06:29] 出发咯~(¯▽¯~)~\n[11:07:17] 生长因子对痘痘有帮助吗",
        "source_timestamps": "2026-06-28 11:06:29,2026-06-28 11:07:17",
        "analysis_reasoning": "11:06 出发去新街口（地铁/打车），11:07 在路上继续讨论生长因子。2 条消息，物理位置从'家'转向'移动中'，归为通勤。注：消息内容虽是健康话题，但发生场景是'通勤路上'，按发生场景而非主题分类。"
    },
    # Block 12: 11:33~12:17 - 通勤：到新街口+讨论图片解析规范
    {
        "date": "2026-06-28",
        "time_start": "11:33",
        "time_end": "12:17",
        "activity": "到新街口+讨论 AI 图片解析规范+等叫号",
        "category": "通勤",
        "source_contents": "[11:33:36] 即将到新街口\n[11:34:58] 你的记忆中哪里写了不需要你解析图片？\n[12:08:25] 不额外解析 此外也不是直接用用户随后发的文本描述录入，因为我们肯定是需要讨论的\n[12:17:25] 我现在已经到这个点了 叫号了 估计十五分钟就可以进去吃了",
        "source_timestamps": "2026-06-28 11:33:36,2026-06-28 11:34:58,2026-06-28 12:08:25,2026-06-28 12:17:25",
        "analysis_reasoning": "11:33 即将到新街口，11:34-12:08 讨论 AI 图片解析规范（属技能配置对话），12:17 到达餐厅叫号。4 条消息，前段通勤+后段到达后等位，物理位置从'移动中'过渡到'餐厅门口等位'。按发生场景归为'通勤'（含到达后短暂等位）。同主题延续性合并。"
    },
    # Block 13: 12:17~14:41 - 餐饮：吃羊肉串（中午饭）+逛街
    {
        "date": "2026-06-28",
        "time_start": "12:17",
        "time_end": "14:41",
        "activity": "中午饭：羊肉串（新街口很久以前）+ 饭后逛街",
        "category": "餐饮",
        "source_contents": "[12:17:06] [附件: image/jpeg] 餐厅照片\n[12:17:25] 我现在已经到这个点了 叫号了 估计十五分钟就可以进去吃了\n[14:41:56] 13点多吃完了 逛街到现在 哈哈",
        "source_timestamps": "2026-06-28 12:17:06,2026-06-28 12:17:25,2026-06-28 14:41:56",
        "analysis_reasoning": "12:17 餐厅门口叫号（上传餐厅照片），约 13:00 吃完（按 14:41 用户回溯'13点多吃完'），14:41 反馈'逛街到现在'。整段约 2h24m，主活动是午餐+饭后逛街合并场景，按'餐饮'归类（吃饭是主活动，逛街是饭后延续）。2 条用户消息+1 附件，时间跨度大但活动连续，合并为一个 block。"
    },
    # Block 14: 14:41~14:52 - 休闲：茶颜悦色排队
    {
        "date": "2026-06-28",
        "time_start": "14:41",
        "time_end": "14:52",
        "activity": "茶颜悦色门口排队等女朋友点单",
        "category": "休闲",
        "source_contents": "[14:41:56] 13点多吃完了 逛街到现在 哈哈\n[14:42:08] 在 茶颜悦色门口 女朋友点了喝的在排队",
        "source_timestamps": "2026-06-28 14:41:56,2026-06-28 14:42:08",
        "analysis_reasoning": "14:41 反馈吃完了在逛街，14:42 立即说明在茶颜悦色门口排队。2 条消息同主题（逛街+等单），属休闲/约会场景。单独成 block，因活动类型从'餐饮（吃饭）'明确切到'休闲（逛街+排队）'。"
    },
    # Block 15: 14:52~16:30 - 工作：补 6-14 作息+严格按规范
    {
        "date": "2026-06-28",
        "time_start": "14:52",
        "time_end": "16:30",
        "activity": "在茶颜悦色排队/逛街途中补充 6-14 作息记录（严格按规范重做）",
        "category": "工作",
        "source_contents": "[14:52:53] /作息管家 我看下过去15天的作息每天覆盖了23h59m 吗\n[15:05:29] 补充6-14 那天缺的东西吧\n[15:06:30] [语音: 15秒] 你按照作息，你按照作息管家技能的要求，你从那天的录音机的技能里面去看，呃，缺的那些时间段，你在做什么呀？你理解我意思吗？\n[15:50:33] 严格按照作息管家的要求来",
        "source_timestamps": "2026-06-28 14:52:53,2026-06-28 15:05:29,2026-06-28 15:06:30,2026-06-28 15:50:33",
        "analysis_reasoning": "14:52 发起 /作息管家 查询+讨论补全 6-14 数据，15:05 确认补充 6-14，15:06 语音详细说明需求（按作息管家规范从录音机补查），15:50 强调'严格按照作息管家的要求来'。4 条记录（含 1 语音）同主题（补全历史作息），属技能维护工作。时间段长（38 分钟）但用户处于'一边逛街一边处理 skill'状态（后续 16:38 明确说明），工作活动与社交场景重叠，按工作内容归类。"
    },
    # Block 16: 16:30~17:21 - 通勤：地铁回家（一遍处理 skill）
    {
        "date": "2026-06-28",
        "time_start": "16:30",
        "time_end": "17:21",
        "activity": "地铁回家途中（继续讨论 skill 分类：兴趣 vs 办公）",
        "category": "通勤",
        "source_contents": "[16:30:40] 可以扫一下\n[16:38:58] 现在在地铁呢😊 回家路上 刚才和你沟通属于一边逛街一边处理一些 skill\n[16:39:32] 不是办公是兴趣爱好",
        "source_timestamps": "2026-06-28 16:30:40,2026-06-28 16:38:58,2026-06-28 16:39:32",
        "analysis_reasoning": "16:30 准备扫码（推断支付/乘车码），16:38 明确在地铁回家+继续沟通 skill，16:39 强调'不是办公是兴趣爱好'。3 条消息同主题（通勤+兴趣讨论），按发生场景归为'通勤'。注：消息内容是工作类讨论，但用户明确否定'办公'属性，按用户定性+发生场景归类。"
    },
    # Block 17: 17:21~17:36 - 通勤：到家过渡
    {
        "date": "2026-06-28",
        "time_start": "17:21",
        "time_end": "17:36",
        "activity": "到家后短暂过渡（15 分钟）",
        "category": "通勤",
        "source_contents": "[17:21:17] 我到家了",
        "source_timestamps": "2026-06-28 17:21:17",
        "analysis_reasoning": "17:21 到家，至 17:36 开始电脑桌前排查工作，中间 15 分钟为到家过渡期（推断换鞋/放东西/走到电脑前）。单独成 block，因活动类型从'通勤途中'过渡到'到家休整'。注：按 SKILL.md 规范，到家过渡属通勤活动延续。"
    },
    # Block 18: 17:36~18:15 - 工作：cron 任务+fallback 模型配置
    {
        "date": "2026-06-28",
        "time_start": "17:36",
        "time_end": "18:15",
        "activity": "电脑桌前排查 cron 任务报错+模型 fallback 配置（minimax主+ M2.7 兜底）",
        "category": "工作",
        "source_contents": "[17:36:47] 查看下 cron 任务早上是如何制定一天的计划作息的，此外描述如何制定计划作息是哪个技能定义的\n[17:39:07] 为什么连续13天都报错 不正常 先排查 error 原因\n[17:41:23] 用 m2.7来作为 fallback 此外 cron 需要提前几分钟生成吗？我怀疑八点 minimax 状态就有问题\n[17:45:34] [语音: 30秒] 你理解错了，是主模型是不变的，将那个兜底的变成M2.7，我们不会再用小米的模型了。\n[17:51:31] 方案 a\n[17:59:34] 将整个系统中可能会 fallback 选到 mimo 的部分都改为 m2.7作为兜底方案，你先调查下\n[18:08:39] 现在是啥问题？你回答了一大段 内容\n[18:12:54] 动手吧",
        "source_timestamps": "2026-06-28 17:36:47,2026-06-28 17:39:07,2026-06-28 17:41:23,2026-06-28 17:45:34,2026-06-28 17:51:31,2026-06-28 17:59:34,2026-06-28 18:08:39,2026-06-28 18:12:54",
        "analysis_reasoning": "17:36-18:12 连续 8 条消息（含 1 语音）讨论 cron 任务排查+模型 fallback 配置调整（minimax 主模型保持不变，兜底从 mimo 改为 M2.7），18:12 '动手吧'结束方案讨论。8 条消息全为同一主题（连续技术 session），按 SKILL.md'同主题可合并'规范合并为一个 block。注：本 block 消息数 8 > 5，但属同一连续工作 session，符合规范。"
    },
    # Block 19: 18:15~18:49 - 睡眠：打盹一小时
    {
        "date": "2026-06-28",
        "time_start": "18:15",
        "time_end": "18:49",
        "activity": "打盹睡觉一小时（用户主动告知）",
        "category": "睡眠",
        "source_contents": "[18:15:58] 睡觉了 打盹睡一小时\n[18:44:29] [Inter-session message] feathersdata-git-sync 完成通知（用户睡眠期间系统后台通知）",
        "source_timestamps": "2026-06-28 18:15:58,2026-06-28 18:44:29",
        "analysis_reasoning": "18:15 用户明确'睡觉了 打盹睡一小时'，18:44 系统 inter-session 通知到达时用户未响应。属典型短时打盹。inter-session 通知保留在 source_contents 标注为'系统通知，与用户活动无关'。"
    },
    # Block 20: 18:49~19:12 - 休闲：醒来+看系统通知
    {
        "date": "2026-06-28",
        "time_start": "18:49",
        "time_end": "19:12",
        "activity": "醒来+接收并查看 git 同步通知（话费充值记账）",
        "category": "休闲",
        "source_contents": "[18:49:03] 醒了\n[19:04:18] [Inter-session message] Git Sync - 记账本新增1条通讯支出记录（话费充值-49.53元）",
        "source_timestamps": "2026-06-28 18:49:03,2026-06-28 19:04:18",
        "analysis_reasoning": "18:49 用户醒来，19:04 系统通知到达（记账同步），用户处于醒后短暂清醒查看通知状态。属休闲/过渡期。1 条用户消息 + 1 inter-session，合并为 1 个 block。"
    },
    # Block 21: 19:12~21:29 - 娱乐：玩金铲铲之战（两盘）
    {
        "date": "2026-06-28",
        "time_start": "19:12",
        "time_end": "21:29",
        "activity": "玩金铲铲之战（英雄联盟传奇模式团队排位两盘）",
        "category": "娱乐",
        "source_contents": "[19:12:11] 电脑桌前 开始玩🤗\n[19:34:22] 准备开始玩金铲铲之战\n[20:16:37] 玩了一盘 英雄联盟传奇模式的团队排位 拿了第一 😎 不打算玩咯\n[20:29:16] 再玩一盘\n[21:29:20] 玩好游戏了 打算录入一些东西",
        "source_timestamps": "2026-06-28 19:12:11,2026-06-28 19:34:22,2026-06-28 20:16:37,2026-06-28 20:29:16,2026-06-28 21:29:20",
        "analysis_reasoning": "19:12 坐到电脑桌前准备玩，19:34 明确游戏目标（金铲铲），20:16 第一盘结束拿第一（声称不玩），20:29 又决定再玩一盘，21:29 结束游戏。5 条消息同主题（游戏 session），合并为一个 block。两次单局在同一 session 内连续进行（用户改变主意），属同一娱乐活动不切分。"
    },
    # Block 22: 21:29~22:13 - 餐饮：热粽子吃+操作备忘录
    {
        "date": "2026-06-28",
        "time_start": "21:29",
        "time_end": "22:13",
        "activity": "热粽子吃晚餐+操作 /备忘录 删除已完成心愿（给猫换水）",
        "category": "餐饮",
        "source_contents": "[21:29:20] 玩好游戏了 打算录入一些东西\n[21:41:50] 现在热粽子吃 有些饿了\n[21:48:35] 在等着吃呢 太烫了\n[21:49:28] /备忘录 心愿给猫换水那个可以删掉了 已经换过了",
        "source_timestamps": "2026-06-28 21:29:20,2026-06-28 21:41:50,2026-06-28 21:48:35,2026-06-28 21:49:28",
        "analysis_reasoning": "21:29 结束游戏，21:41 开始热粽子吃晚餐，21:48 等凉，21:49 顺手用 /备忘录 删除已完成的心愿（给猫换水）。4 条消息，主活动是晚餐，删心愿是吃饭等待期间的小操作，按主活动归为'餐饮'。同主题合并为一个 block。"
    },
    # Block 23: 22:13~22:30 - 休闲：躺床上休息
    {
        "date": "2026-06-28",
        "time_start": "22:13",
        "time_end": "22:30",
        "activity": "躺床上休息（睡前过渡）",
        "category": "休闲",
        "source_contents": "[22:13:26] 现在躺在床上呢",
        "source_timestamps": "2026-06-28 22:13:26",
        "analysis_reasoning": "22:13 用户明确表示已躺床上，处于从餐桌→床的位置切换过渡期。22:30 开始新的工作讨论（飞书插件），单独成 block 因活动类型从'餐饮收尾'切到'休闲（躺床）'再到'工作'。"
    },
    # Block 24: 22:30~23:11 - 工作：躺床上处理飞书插件兼容问题
    {
        "date": "2026-06-28",
        "time_start": "22:30",
        "time_end": "23:11",
        "activity": "躺床上处理 openclaw 飞书插件版本不兼容问题（修复方案确认）",
        "category": "工作",
        "source_contents": "[22:30:41] openclaw如何配置 飞书插件，现在飞书插件 因为版本问题不兼容 需要删除吗？\n[22:40:55] 按照你的方案 修复吧 我现在不知道如何给 openclaw通过飞书发消息\n[22:43:20] [Inter-session message] feathersdata-git-sync 完成通知（用户工作中后台系统通知）",
        "source_timestamps": "2026-06-28 22:30:41,2026-06-28 22:40:55,2026-06-28 22:43:20",
        "analysis_reasoning": "22:30 开始讨论飞书插件版本兼容问题，22:40 确认修复方案。中间 22:43 系统通知到达未中断讨论。3 条消息同主题（飞书插件修复），合并为一个 block。"
    },
    # Block 25: 23:11~23:42 - 工作：飞书消息测试+询问重新绑定
    {
        "date": "2026-06-28",
        "time_start": "23:11",
        "time_end": "23:42",
        "activity": "飞书消息通道测试+询问真哥与飞书机器人重新绑定方案",
        "category": "工作",
        "source_contents": "[23:11:34] [feishu] 你好\n[23:11:58] 那我们有办法重新绑定 你和飞书机器人吗\n[23:12:22] [feishu] 你是谁\n[23:13:49] [feishu] ok",
        "source_timestamps": "2026-06-28 23:11:34,2026-06-28 23:11:58,2026-06-28 23:12:22,2026-06-28 23:13:49",
        "analysis_reasoning": "23:11 收到 feishu 测试消息'你好'，用户立即（同一分钟）询问能否重新绑定飞书机器人；23:12/23:13 继续收到 feishu 自动回复'你是谁'/'ok'。属飞书通道配置调试阶段，4 条消息（2 条用户+2 条 feishu 回执）同主题合并为一个 block。"
    },
    # Block 26: 23:42~23:59 - 睡眠：准备睡觉
    {
        "date": "2026-06-28",
        "time_start": "23:42",
        "time_end": "23:59",
        "activity": "宣布准备睡觉并躺到床上",
        "category": "睡眠",
        "source_contents": "[23:42:37] 准备睡觉了\n[23:53:22] 躺床上啦",
        "source_timestamps": "2026-06-28 23:42:37,2026-06-28 23:53:22",
        "analysis_reasoning": "23:42 用户明确'准备睡觉了'，23:53 已躺到床上。属入睡准备阶段，至 23:59（6/28 最后时间点）结束。注：00:00 之后 6/29 凌晨的数据由 sync_2026-06-28_2.py 已处理（Block 13-16），不在本次重建范围。"
    },
]


def calculate_duration(time_start: str, time_end: str) -> int:
    """计算时长（分钟）"""
    fmt = "%H:%M"
    s = datetime.strptime(time_start, fmt)
    e = datetime.strptime(time_end, fmt)
    delta = e - s
    if delta.total_seconds() < 0:
        from datetime import timedelta
        delta += timedelta(days=1)
    return int(delta.total_seconds() / 60)


def check_time_continuity(blocks):
    """校验时间严格连续"""
    for i in range(len(blocks) - 1):
        cur_end = blocks[i]["time_end"]
        next_start = blocks[i + 1]["time_start"]
        if cur_end != next_start:
            return False, f"Block {i+1} 结束 {cur_end} != Block {i+2} 开始 {next_start}"
    return True, "OK"


def backup_6_28_data(backup_dir: Path) -> Path:
    """备份 6/28 全部记录到 JSON"""
    backup_dir.mkdir(parents=True, exist_ok=True)
    records = get_records_by_date("2026-06-28")
    backup_data = {
        "backup_time": datetime.now().isoformat(),
        "date": "2026-06-28",
        "record_count": len(records),
        "records": records,
    }
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"schedule_records_2026-06-28_backup_{timestamp}.json"
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=2, default=str)
    return backup_path


def apply_changes(blocks):
    """清空 6/28 旧记录并写入新 block（破例 DELETE 一次）"""
    conn = get_connection()
    c = conn.cursor()
    
    # 清空旧记录（破例 DELETE，仅此一次）
    c.execute("DELETE FROM schedule_records WHERE date = ?", ("2026-06-28",))
    deleted = c.rowcount
    conn.commit()
    conn.close()
    
    # 写入新 block
    success = 0
    for i, block in enumerate(blocks, 1):
        duration = calculate_duration(block["time_start"], block["time_end"])
        rid = add_record_full(
            date=block["date"],
            time_start=block["time_start"],
            time_end=block["time_end"],
            duration_minutes=duration,
            activity=block["activity"],
            category=block["category"],
            source_contents=block["source_contents"],
            source_timestamps=block["source_timestamps"],
            analysis_reasoning=block["analysis_reasoning"],
        )
        print(f"  ✓ Block {i:2d} [{block['time_start']}~{block['time_end']}] {block['category']:4s} | {block['activity'][:40]:40s} (id={rid})")
        success += 1
    
    return deleted, success


def main():
    parser = argparse.ArgumentParser(
        description="作息管家 - 2026-06-28 严格重做脚本（破例 DELETE 需 --apply）"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="实际写入数据库（默认 dry-run：只备份+打印新 block）",
    )
    args = parser.parse_args()
    
    skill_dir = Path(__file__).parent.parent
    backup_dir = skill_dir / ".db" / "backup"
    
    # === 步骤 1：校验时间连续性 ===
    print("=" * 70)
    print("📋 步骤 1：校验时间连续性")
    print("=" * 70)
    ok, msg = check_time_continuity(BLOCKS)
    if not ok:
        print(f"❌ 连续性校验失败：{msg}")
        sys.exit(1)
    print(f"✓ 26 个 block 时间严格连续：{BLOCKS[0]['time_start']} ~ {BLOCKS[-1]['time_end']}")
    
    # === 步骤 2：统计 ===
    print()
    print("=" * 70)
    print("📊 步骤 2：统计信息")
    print("=" * 70)
    total_duration = sum(
        calculate_duration(b["time_start"], b["time_end"]) for b in BLOCKS
    )
    print(f"  Block 数：{len(BLOCKS)}（最少要求 {get_required_block_count('2026-06-28 00:00:00', '2026-06-28 23:59:00', 5)}）")
    print(f"  总时长：{total_duration} 分钟 = {total_duration // 60}h{total_duration % 60}m")
    print(f"  区间：{BLOCKS[0]['time_start']} ~ {BLOCKS[-1]['time_end']}")
    
    # === 步骤 3：备份旧数据 ===
    print()
    print("=" * 70)
    print("💾 步骤 3：备份 6/28 现有数据")
    print("=" * 70)
    backup_path = backup_6_28_data(backup_dir)
    print(f"✓ 已备份到：{backup_path}")
    
    # === 步骤 4：显示新 block 列表 ===
    print()
    print("=" * 70)
    print("📝 步骤 4：26 个新 block 预览")
    print("=" * 70)
    for i, b in enumerate(BLOCKS, 1):
        duration = calculate_duration(b["time_start"], b["time_end"])
        print(f"  {i:2d}. [{b['time_start']}~{b['time_end']}] ({duration:3d}m) {b['category']:4s} | {b['activity'][:45]}")
    
    # === 步骤 5：执行写入（仅 --apply）===
    print()
    print("=" * 70)
    print("🚀 步骤 5：执行写入")
    print("=" * 70)
    if not args.apply:
        print("⚠️  当前为 dry-run 模式，未实际写入数据库")
        print("    如确认要执行重建，请使用 --apply 参数：")
        print(f"    python3 {Path(__file__).name} --apply")
        print()
        print("    --apply 模式将：")
        print("    1) 清空 6/28 全部旧记录（破例 DELETE，仅此一次）")
        print("    2) 写入 26 个新 block")
        print("    3) 调用 validate_record_count 校验")
    else:
        print("⚠️  --apply 模式已启用，开始执行重建...")
        deleted, success = apply_changes(BLOCKS)
        print(f"\n✓ 已清空 6/28 旧记录 {deleted} 条")
        print(f"✓ 已写入新 block {success} 条")
        
        # 后置校验
        print()
        print("=" * 70)
        print("✅ 步骤 6：后置校验")
        print("=" * 70)
        result = validate_record_count(
            "2026-06-28 00:00:00", "2026-06-28 23:59:00", 5
        )
        if result is True:
            print("✓ validate_record_count 校验通过！")
        else:
            print(f"❌ 校验失败：{result}")
        
        # 显示新 6/28 报告
        print()
        print("=" * 70)
        print("📊 新 6/28 作息报告")
        print("=" * 70)
        records = get_records_by_date("2026-06-28")
        for r in records:
            print(f"  [{r['time_start']}~{r['time_end']}] {r['category']:4s} | {r['activity']}")


if __name__ == "__main__":
    main()
