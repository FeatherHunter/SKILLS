#!/usr/bin/env python3
"""
作息管家 - 2026-06-28 16:30 ~ 2026-06-29 02:08 增量同步脚本
按活动切换点切割block，严格保证时间连续

游标：2026-06-28 14:52~16:30（最后活动：/作息管家 查询过去 15 天作息）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from schedule_db import add_record_full

# ============ Blocks 数据 ============
# 38 条消息，最少需要 8 个 block，按活动切换点切割

BLOCKS = [
    # ==================== 2026-06-28 ====================
    # Block 1: 16:30~17:21 - 通勤：购物结束回家（地铁+到家）
    {
        "date": "2026-06-28",
        "time_start": "16:30",
        "time_end": "17:21",
        "activity": "购物结束后地铁回家（一边逛街一边处理skill）",
        "category": "通勤",
        "source_contents": "[16:30] 可以扫一下\n[16:38] 现在在地铁呢😊 回家路上 刚才和你沟通属于一边逛街一边处理一些 skill\n[16:39] 不是办公是兴趣爱好\n[17:21] 我到家了",
        "source_timestamps": "2026-06-28 16:30:00,2026-06-28 16:38:00,2026-06-28 16:39:00,2026-06-28 17:21:00",
        "analysis_reasoning": "从游标位置16:30开始，用户仍在外面购物（扫码），16:38切换到地铁回家，途中与真哥沟通skill分类（明确说明'一边逛街一边处理一些 skill'，纠正'不是办公是兴趣爱好'）。17:21到家。整体属于通勤回家+顺手处理个人兴趣类问题，活动类型从游标的'工作查询'过渡到'通勤+兴趣'。"
    },
    # Block 2: 17:21~17:36 - 到家过渡
    {
        "date": "2026-06-28",
        "time_start": "17:21",
        "time_end": "17:36",
        "activity": "到家后短暂过渡",
        "category": "通勤",
        "source_contents": "[17:21] 我到家了（接续block1，此段无新消息，推断用户进门、换鞋、放下东西等过渡动作）",
        "source_timestamps": "2026-06-28 17:21:00",
        "analysis_reasoning": "17:21到家后，17:36才开始下一段电脑桌前工作，中间15分钟为到家过渡期（推断用户进门、稍作休息、走到电脑前）。时间间隔未达20分钟，但活动类型从'通勤途中'明确过渡到'到家休整'，单独切块。"
    },
    # Block 3: 17:36~18:15 - 工作：排查cron任务和fallback模型
    {
        "date": "2026-06-28",
        "time_start": "17:36",
        "time_end": "18:15",
        "activity": "电脑桌前排查cron任务和模型fallback配置",
        "category": "工作",
        "source_contents": "[17:36] 查看下 cron 任务早上是如何制定一天的计划作息的，此外描述如何制定计划作息是哪个技能定义的\n[17:39] 为什么连续13天都报错 不正常 先排查 error 原因\n[17:41] 用 m2.7来作为 fallback 此外 cron 需要提前几分钟生成吗？我怀疑八点 minimax 状态就有问题\n[17:45] 你理解错了，是主模型是不变的，将那个兜底的变成M2.7，我们不会再用小米的模型了。\n[17:51] 方案 a\n[17:59] 将整个系统中可能会 fallback 选到 mimo 的部分都改为 m2.7作为兜底方案，你先调查下\n[18:08] 现在是啥问题？你回答了一大段 内容\n[18:12] 动手吧",
        "source_timestamps": "2026-06-28 17:36:00,2026-06-28 17:39:00,2026-06-28 17:41:00,2026-06-28 17:45:00,2026-06-28 17:51:00,2026-06-28 17:59:00,2026-06-28 18:08:00,2026-06-28 18:12:00",
        "analysis_reasoning": "17:36起用户坐到电脑前开始排查cron任务报错问题，连续8条消息讨论fallback模型配置（minimax主模型、M2.7兜底、放弃mimo），18:12指示'动手吧'结束方案讨论。属典型连续技术工作session。"
    },
    # Block 4: 18:15~18:49 - 睡眠：打盹一小时
    {
        "date": "2026-06-28",
        "time_start": "18:15",
        "time_end": "18:49",
        "activity": "打盹睡觉一小时",
        "category": "睡眠",
        "source_contents": "[18:15] 睡觉了 打盹睡一小时\n[18:44] [Inter-session message] feathersdata-git-sync 完成通知（用户睡觉期间系统后台通知）",
        "source_timestamps": "2026-06-28 18:15:00,2026-06-28 18:44:00",
        "analysis_reasoning": "18:15用户明确说'打盹睡一小时'，18:44系统通知到达时用户仍在睡眠（无响应），属典型睡眠场景。"
    },
    # Block 5: 18:49~19:12 - 休闲：醒来+看系统通知
    {
        "date": "2026-06-28",
        "time_start": "18:49",
        "time_end": "19:12",
        "activity": "醒来+接收并查看git同步通知",
        "category": "休闲",
        "source_contents": "[18:49] 醒了\n[19:04] [Inter-session message] Git Sync - 记账本新增1条通讯支出记录（话费充值-49.53元）",
        "source_timestamps": "2026-06-28 18:49:00,2026-06-28 19:04:00",
        "analysis_reasoning": "18:49用户醒来，19:04系统通知到达，用户处于醒后短暂清醒查看通知状态（未主动发起新任务），属休闲/过渡期。"
    },
    # Block 6: 19:12~19:34 - 娱乐：电脑桌前准备开始游戏
    {
        "date": "2026-06-28",
        "time_start": "19:12",
        "time_end": "19:34",
        "activity": "电脑桌前准备开始玩游戏",
        "category": "娱乐",
        "source_contents": "[19:12] 电脑桌前 开始玩🤗\n[19:34] 准备开始玩金铲铲之战",
        "source_timestamps": "2026-06-28 19:12:00,2026-06-28 19:34:00",
        "analysis_reasoning": "19:12坐到电脑桌前宣布开始玩，19:34明确游戏目标（金铲铲之战）。从休闲过渡到娱乐准备阶段。"
    },
    # Block 7: 19:34~21:29 - 娱乐：玩金铲铲之战（两盘）
    {
        "date": "2026-06-28",
        "time_start": "19:34",
        "time_end": "21:29",
        "activity": "玩金铲铲之战（英雄联盟传奇模式团队排位两盘）",
        "category": "娱乐",
        "source_contents": "[19:34] 准备开始玩金铲铲之战\n[20:16] 玩了一盘 英雄联盟传奇模式的团队排位 拿了第一 😎 不打算玩咯\n[20:29] 再玩一盘\n[21:29] 玩好游戏了 打算录入一些东西",
        "source_timestamps": "2026-06-28 19:34:00,2026-06-28 20:16:00,2026-06-28 20:29:00,2026-06-28 21:29:00",
        "analysis_reasoning": "19:34开始游戏，20:16结束第一盘（拿第一，声称不玩），20:29又决定再玩一盘，21:29结束游戏。两次单局游戏在同一session内连续进行（用户改变主意），属同一娱乐活动。"
    },
    # Block 8: 21:29~22:13 - 餐饮：热粽子吃+操作备忘录
    {
        "date": "2026-06-28",
        "time_start": "21:29",
        "time_end": "22:13",
        "activity": "热粽子吃+操作备忘录删心愿",
        "category": "餐饮",
        "source_contents": "[21:29] 玩好游戏了 打算录入一些东西\n[21:41] 现在热粽子吃 有些饿了\n[21:48] 在等着吃呢 太烫了\n[21:49] /备忘录 心愿给猫换水那个可以删掉了 已经换过了",
        "source_timestamps": "2026-06-28 21:29:00,2026-06-28 21:41:00,2026-06-28 21:48:00,2026-06-28 21:49:00",
        "analysis_reasoning": "21:29结束游戏，21:41开始热粽子吃（晚餐），21:48等待粽子凉，21:49顺手用/备忘录技能删除已完成的心愿（给猫换水）。属晚餐+小操作混合场景，主活动是餐饮。"
    },
    # Block 9: 22:13~22:30 - 休闲：躺床上
    {
        "date": "2026-06-28",
        "time_start": "22:13",
        "time_end": "22:30",
        "activity": "躺床上休息",
        "category": "休闲",
        "source_contents": "[22:13] 现在躺在床上呢",
        "source_timestamps": "2026-06-28 22:13:00",
        "analysis_reasoning": "22:13用户明确表示已躺床上，处于位置切换（从餐桌/电脑前→床上）的过渡。22:30开始新的工作讨论（飞书插件），属明确活动类型切换。"
    },
    # Block 10: 22:30~23:11 - 工作：躺床上处理飞书插件兼容问题
    {
        "date": "2026-06-28",
        "time_start": "22:30",
        "time_end": "23:11",
        "activity": "躺床上处理openclaw飞书插件版本不兼容问题",
        "category": "工作",
        "source_contents": "[22:30] openclaw如何配置 飞书插件，现在飞书插件 因为版本问题不兼容 需要删除吗？\n[22:40] 按照你的方案 修复吧 我现在不知道如何给 openclaw通过飞书发消息\n[22:43] [Inter-session message] feathersdata-git-sync 完成通知（用户工作中后台系统通知）",
        "source_timestamps": "2026-06-28 22:30:00,2026-06-28 22:40:00,2026-06-28 22:43:00",
        "analysis_reasoning": "22:30开始讨论openclaw飞书插件版本兼容问题，22:40确认修复方案。中间22:43系统通知到达但未中断讨论。属连续工作session。"
    },
    # Block 11: 23:11~23:42 - 工作：飞书消息测试+询问重新绑定
    {
        "date": "2026-06-28",
        "time_start": "23:11",
        "time_end": "23:42",
        "activity": "测试飞书消息通道+询问重新绑定方案",
        "category": "工作",
        "source_contents": "[23:11] [feishu] 你好\n[23:11] 那我们有办法重新绑定 你和飞书机器人吗\n[23:12] [feishu] 你是谁\n[23:13] [feishu] ok",
        "source_timestamps": "2026-06-28 23:11:00,2026-06-28 23:11:00,2026-06-28 23:12:00,2026-06-28 23:13:00",
        "analysis_reasoning": "23:11收到feishu测试消息'你好'，用户立即询问能否重新绑定飞书机器人；23:12/23:13继续收到feishu自动回复。属飞书通道配置调试阶段。"
    },
    # Block 12: 23:42~23:59 - 睡眠：准备睡觉
    {
        "date": "2026-06-28",
        "time_start": "23:42",
        "time_end": "23:59",
        "activity": "准备睡觉（躺床上）",
        "category": "睡眠",
        "source_contents": "[23:42] 准备睡觉了\n[23:53] 躺床上啦",
        "source_timestamps": "2026-06-28 23:42:00,2026-06-28 23:53:00",
        "analysis_reasoning": "23:42用户明确宣布'准备睡觉了'，23:53已躺到床上。属入睡准备阶段，结束于23:59（6/28最后时间）。"
    },
    # ==================== 2026-06-29 ====================
    # Block 13: 00:00~00:17 - 睡眠：深夜躺床无消息
    {
        "date": "2026-06-29",
        "time_start": "00:00",
        "time_end": "00:17",
        "activity": "深夜躺床（入睡前/或未真正入睡）",
        "category": "睡眠",
        "source_contents": "[00:00~00:17] 用户未发送新消息（从23:53躺床上到00:17），推测处于入睡前阶段或浅睡眠",
        "source_timestamps": "2026-06-29 00:00:00",
        "analysis_reasoning": "日期切换至6/29，00:00~00:17无消息。结合上下文（23:53躺床上，准备睡觉），用户在深夜处于入睡准备或浅睡眠状态。"
    },
    # Block 14: 00:17~01:00 - 娱乐：躺床上看韩剧第十集
    {
        "date": "2026-06-29",
        "time_start": "00:17",
        "time_end": "01:00",
        "activity": "躺床上看韩剧（第十集）",
        "category": "娱乐",
        "source_contents": "[00:17] 还躺着呢 看看剧\n[00:17] 准备看昨天那个韩剧的第十集",
        "source_timestamps": "2026-06-29 00:17:00,2026-06-29 00:17:00",
        "analysis_reasoning": "00:17用户仍未入睡，决定改为看韩剧，躺在床上看剧消磨时间。"
    },
    # Block 15: 01:00~01:01 - 娱乐：看剧+收飞书消息
    {
        "date": "2026-06-29",
        "time_start": "01:00",
        "time_end": "01:01",
        "activity": "看剧+接收飞书消息",
        "category": "娱乐",
        "source_contents": "[01:00] [feishu] 哈哈哈\n[01:01] 我最近看的韩剧叫什么来着",
        "source_timestamps": "2026-06-29 01:00:00,2026-06-29 01:01:00",
        "analysis_reasoning": "01:00飞书自动消息'哈哈哈'到达，01:01用户询问韩剧名字（看剧中注意力分散/记忆模糊）。主活动仍是看剧。"
    },
    # Block 16: 01:01~02:08 - 未知：消息结束至今
    {
        "date": "2026-06-29",
        "time_start": "01:01",
        "time_end": "02:08",
        "activity": "深夜消息结束（推测继续看剧或入睡）",
        "category": "未知",
        "source_contents": "[消息结束] 01:01之后用户未发送新消息至当前时刻02:08。结合上下文（看韩剧中），推测用户继续看剧或已入睡。当前时间2026-06-29 02:08。",
        "source_timestamps": "2026-06-29 02:08:00",
        "analysis_reasoning": "01:01之后至当前cron时刻（02:08）无消息，属深夜无消息时段。推测用户继续看剧或自然入睡，无法明确判断具体活动，归为未知。"
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
        from datetime import timedelta
        delta += timedelta(days=1)
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
            print(f"✓ Block {i:2d} [{block['date']} {block['time_start']}~{block['time_end']}] {block['category']:6s} {block['activity'][:35]:35s} (id={record_id})")
            success_count += 1
        except Exception as e:
            print(f"✗ Block {i:2d} 失败: {e}")
            fail_count += 1
    
    print(f"\n汇总: 成功 {success_count} 条, 失败 {fail_count} 条")
    return success_count, fail_count

if __name__ == "__main__":
    main()