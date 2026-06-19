#!/usr/bin/env python3
"""
2026-06-19 午间同步脚本
按活动切换点切割 block 写入数据库
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from schedule_db import add_record_full, DB_PATH

DATE = "2026-06-19"

# ============ Block 定义 ============
# 每个 block 包含: time_start, time_end, duration_minutes, activity, category,
#                  source_contents, source_timestamps, analysis_reasoning

BLOCKS = [
    # Block 1: 02:08 ~ 08:05 - 持续睡眠到醒来
    {
        "time_start": "02:08",
        "time_end": "08:05",
        "duration_minutes": 357,
        "activity": "凌晨睡眠（接续00:53晚安入睡）",
        "category": "睡眠",
        "source_contents": "[08:05] 醒咯",
        "source_timestamps": "2026-06-19 08:05:00",
        "analysis_reasoning": "游标时间 02:08 为睡眠状态（前置 prev_message [00:53] 晚安哈 已确认入睡）。新消息第一条 [08:05] 醒咯 是明确醒来信号，确认该时段为持续睡眠。"
    },
    # Block 2: 08:05 ~ 09:00 - 起床后短暂清醒活动
    {
        "time_start": "08:05",
        "time_end": "09:00",
        "duration_minutes": 55,
        "activity": "起床后在家短暂清醒",
        "category": "休闲",
        "source_contents": "[08:05] 醒咯\n[10:51] 九点继续睡 ，睡到了 现在 10:50 哈哈",
        "source_timestamps": "2026-06-19 08:05:00,2026-06-19 10:51:00",
        "analysis_reasoning": "前5后5窗口：08:05 醒咯是起床信号，结合后5条消息中的 [10:51] 九点继续睡 ，睡到了现在10:50，明确说明 8:05 起床后到9点又睡了，故 08:05~09:00 为起床后短暂清醒活动。"
    },
    # Block 3: 09:00 ~ 10:51 - 9点继续睡懒觉到10:50
    {
        "time_start": "09:00",
        "time_end": "10:51",
        "duration_minutes": 111,
        "activity": "9点继续睡懒觉到10:50",
        "category": "睡眠",
        "source_contents": "[10:51] 九点继续睡 ，睡到了 现在 10:50 哈哈",
        "source_timestamps": "2026-06-19 10:51:00",
        "analysis_reasoning": "窗口消息 [10:51] 九点继续睡 ，睡到了现在10:50 哈哈 明确表明9点再次入睡、10:50起床，故 09:00~10:51 为继续睡懒觉的睡眠时段。"
    },
    # Block 4: 10:51 ~ 12:03 - 起床后休息，准备做饭
    {
        "time_start": "10:51",
        "time_end": "12:03",
        "duration_minutes": 72,
        "activity": "起床后在家休息，准备做午饭",
        "category": "休闲",
        "source_contents": "[10:51] 九点继续睡 ，睡到了 现在 10:50 哈哈\n[12:03] 给你一个新的物品，位置放在客厅的健身箱中：\n明白了，如果盖子没有任何机械结构，是直接拿起来的，那重新解析如下：\n物品名： 复古撞色扣盖收纳盒（或金属翻盖收纳盒）\n特点：\n1. 极简扣盖结构：盖子与盒身没有任何铰链或弹簧，纯靠边缘贴合或轻微卡扣固定。取用时只需捏住盖子，直接向上提起即可，非常原始和方便。\n2. 造型上的\"伪装提手\"：顶部金色盖子上那两道横向凸起，以及中间的方形凹块，并非机械开关，而是纯粹的装饰性设计。同时，这两条凸起也充当了\"提手\"，方便手指捏住发力，轻松把盖子拔开。\n3. 强烈撞色与金属质感：鲜艳的亮橙色盒身，搭配高抛光亮金色的顶盖，色彩反差极大，视觉上非常吸睛。金色部分无明显的划痕或氧化，保留了复古又崭新的工业感。\n4. 方正硬朗的几何风：盒身呈规整长方体，边缘折角硬朗。这种设计风格很像微缩版的复古工具箱或油桶，携带十分便携，适合放在口袋或包里。\n5. 用途：内部为一个简单的空腔，非常适合用来装小药片、薄荷糖、耳钉/戒指、U盘、卡针这类随手需要用的小零碎物件。盖子厚实，也能提供很好的防压保护。",
        "source_timestamps": "2026-06-19 10:51:00,2026-06-19 12:03:00",
        "analysis_reasoning": "10:51 起床后到12:03 中间无消息。结合后续 [12:04] 在蒸包子 快好了 推断该时段主要为起床后休息、准备做饭（蒸包子）的阶段；[12:03] 是居家管家对之前图片的物品识别响应，与居家管家系统交互。"
    },
    # Block 5: 12:03 ~ 12:04 - 居家管家物品识别响应
    {
        "time_start": "12:03",
        "time_end": "12:04",
        "duration_minutes": 1,
        "activity": "居家管家物品识别响应（复古撞色扣盖收纳盒）",
        "category": "居家管家交互",
        "source_contents": "[12:03] 给你一个新的物品，位置放在客厅的健身箱中：\n明白了，如果盖子没有任何机械结构，是直接拿起来的，那重新解析如下：\n物品名： 复古撞色扣盖收纳盒（或金属翻盖收纳盒）\n特点：\n1. 极简扣盖结构：盖子与盒身没有任何铰链或弹簧，纯靠边缘贴合或轻微卡扣固定。取用时只需捏住盖子，直接向上提起即可，非常原始和方便。\n2. 造型上的\"伪装提手\"：顶部金色盖子上那两道横向凸起，以及中间的方形凹块，并非机械开关，而是纯粹的装饰性设计。同时，这两条凸起也充当了\"提手\"，方便手指捏住发力，轻松把盖子拔开。\n3. 强烈撞色与金属质感：鲜艳的亮橙色盒身，搭配高抛光亮金色的顶盖，色彩反差极大，视觉上非常吸睛。金色部分无明显的划痕或氧化，保留了复古又崭新的工业感。\n4. 方正硬朗的几何风：盒身呈规整长方体，边缘折角硬朗。这种设计风格很像微缩版的复古工具箱或油桶，携带十分便携，适合放在口袋或包里。\n5. 用途：内部为一个简单的空腔，非常适合用来装小药片、薄荷糖、耳钉/戒指、U盘、卡针这类随手需要用的小零碎物件。盖子厚实，也能提供很好的防压保护。",
        "source_timestamps": "2026-06-19 12:03:00",
        "analysis_reasoning": "消息 [12:03] 是居家管家对用户之前发送的物品图片的识别响应（复古撞色扣盖收纳盒，位置客厅健身箱），属于居家管家交互。下一条 [12:04] 在蒸包子快好了 是活动切换（蒸包子准备），故单独成块。"
    },
    # Block 6: 12:04 ~ 12:09 - 在家蒸包子
    {
        "time_start": "12:04",
        "time_end": "12:09",
        "duration_minutes": 5,
        "activity": "在家蒸包子（快好了）",
        "category": "餐饮",
        "source_contents": "[12:04] 在蒸包子 快好了",
        "source_timestamps": "2026-06-19 12:04:00",
        "analysis_reasoning": "[12:04] 在蒸包子 快好了 是明确餐饮准备活动（蒸包子即将完成）。下一条 [12:09] /卡路里 记录体重 是切换到健康记录，活动变化故切割。"
    },
    # Block 7: 12:09 ~ 12:11 - 记录体重
    {
        "time_start": "12:09",
        "time_end": "12:11",
        "duration_minutes": 2,
        "activity": "记录体重92.5kg到卡路里系统",
        "category": "健康",
        "source_contents": "[12:09] /卡路里 记录体重 92.5kg",
        "source_timestamps": "2026-06-19 12:09:00",
        "analysis_reasoning": "[12:09] /卡路里 记录体重 92.5kg 是用户调用卡路里技能记录体重数据，明确的健康管理活动。下一条 [12:11] 发图（无文字）为拍照/分享，活动变化故切割。"
    },
    # Block 8: 12:11 ~ 12:14 - 发图片（拍包子）
    {
        "time_start": "12:11",
        "time_end": "12:14",
        "duration_minutes": 3,
        "activity": "拍包子图片发送",
        "category": "休闲",
        "source_contents": "[12:11] [User sent media without caption]",
        "source_timestamps": "2026-06-19 12:11:00",
        "analysis_reasoning": "[12:11] 是用户发送的图片（无文字），结合上下文 [12:04] 在蒸包子、[12:14] 蒸好包子了开始吃饭，推断为拍摄蒸好的包子图片分享。"
    },
    # Block 9: 12:14 ~ 12:15 - 开始吃饭
    {
        "time_start": "12:14",
        "time_end": "12:15",
        "duration_minutes": 1,
        "activity": "开始吃午饭（蒸好的包子）",
        "category": "餐饮",
        "source_contents": "[12:14] 蒸好包子了 开始吃饭",
        "source_timestamps": "2026-06-19 12:14:00",
        "analysis_reasoning": "[12:14] 蒸好包子了 开始吃饭 是明确的就餐活动（开始吃饭）。下一条 [12:15] /居家管家 我有哪些物品在快递中 是切换到居家管家交互，活动变化故切割。"
    },
    # Block 10: 12:15 ~ 12:17 - 询问居家管家物品快递
    {
        "time_start": "12:15",
        "time_end": "12:17",
        "duration_minutes": 2,
        "activity": "询问居家管家快递中物品",
        "category": "居家管家交互",
        "source_contents": "[12:15] /居家管家 我有哪些物品在 快递中？快递/山姆的有吗\n[12:17] 怎么样了",
        "source_timestamps": "2026-06-19 12:15:00,2026-06-19 12:17:00",
        "analysis_reasoning": "[12:15] /居家管家 我有哪些物品在快递中？ 是查询居家管家系统中快递状态（含山姆），[12:17] 怎么样了 是跟进询问响应。两条都是同一主题（向居家管家询问快递物品），连续消息合并为一个 block。"
    },
    # Block 11: 12:17 ~ 12:19 - 给居家管家下指令移动物品
    {
        "time_start": "12:17",
        "time_end": "12:19",
        "duration_minutes": 2,
        "activity": "给居家管家下指令（移动健身箱物品到17件位置）",
        "category": "居家管家交互",
        "source_contents": "[12:18] 客厅/健身箱 中的物品 都移到 那17件所在的位置，这次新的也录入进去。",
        "source_timestamps": "2026-06-19 12:18:00",
        "analysis_reasoning": "[12:18] 是给居家管家的物品位置移动指令（客厅/健身箱中的物品移到17件所在位置+新物品录入）。这是新的指令意图，与之前的查询快递不同。下一条 [12:19] 甜甜圈吃完了 是切换到物品状态更新。"
    },
    # Block 12: 12:19 ~ 12:21 - 更新居家管家物品状态+询问
    {
        "time_start": "12:19",
        "time_end": "12:21",
        "duration_minutes": 2,
        "activity": "更新居家管家物品状态（甜甜圈消耗）+ 询问山姆菜包",
        "category": "居家管家交互",
        "source_contents": "[12:19] 甜甜圈吃完了 数量为0\n[12:21] 居家管家中有 山姆的菜包吗？",
        "source_timestamps": "2026-06-19 12:19:00,2026-06-19 12:21:00",
        "analysis_reasoning": "[12:19] 甜甜圈吃完了数量为0 是物品状态更新（消耗完），[12:21] 居家管家中有山姆的菜包吗 是新查询。两条都是向居家管家系统汇报/询问物品状态，连续同主题对话合并。"
    },
    # Block 13: 12:21 ~ 12:22 - 居家管家物品位置记录
    {
        "time_start": "12:21",
        "time_end": "12:22",
        "duration_minutes": 1,
        "activity": "记录物品位置（白砂糖、水饺、黑猪肉包）到居家管家",
        "category": "居家管家交互",
        "source_contents": "[12:22] 白砂糖 位置在厨房 和 香叶那些东西在一个位置\n水饺和黑猪肉包都在 客厅冰箱的下层（从已有位置去找）",
        "source_timestamps": "2026-06-19 12:22:00",
        "analysis_reasoning": "[12:22] 是给居家管家的物品位置记录指令（白砂糖在厨房香叶位置、水饺和黑猪肉包在客厅冰箱下层）。这是新的指令意图（位置录入），与前面消耗/查询不同。time_end 为最后一条消息时间 12:22，当前时刻12:26不补齐。"
    },
]


def main():
    print(f"准备写入 {len(BLOCKS)} 个 block 到数据库 {DB_PATH}")
    print(f"日期: {DATE}")
    print()

    last_time_end = "02:08"
    for i, block in enumerate(BLOCKS, 1):
        # 校验时间连续性
        if block["time_start"] != last_time_end:
            print(f"❌ Block {i} 时间不连续: 上一条 time_end={last_time_end}, 当前 time_start={block['time_start']}")
            return

        try:
            record_id = add_record_full(
                date=DATE,
                time_start=block["time_start"],
                time_end=block["time_end"],
                duration_minutes=block["duration_minutes"],
                activity=block["activity"],
                category=block["category"],
                source_contents=block["source_contents"],
                source_timestamps=block["source_timestamps"],
                analysis_reasoning=block["analysis_reasoning"],
            )
            print(f"✓ Block {i}: {block['time_start']}~{block['time_end']} [{block['category']}] {block['activity'][:30]}... (id={record_id})")
            last_time_end = block["time_end"]
        except Exception as e:
            print(f"❌ Block {i} 写入失败: {e}")
            return

    print()
    print(f"✓ 全部 {len(BLOCKS)} 个 block 写入成功")


if __name__ == "__main__":
    main()