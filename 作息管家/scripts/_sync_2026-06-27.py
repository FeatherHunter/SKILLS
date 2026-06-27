#!/usr/bin/env python3
"""
2026-06-27 午间同步脚本
按活动切换点切割 block 写入数据库

游标最后记录: 2026-06-26 23:59 睡前闲聊+准备睡觉
前10条上下文: 23:29 困了准备睡觉了 / 23:28 B / 22:14 b / 22:10 就我吃了两个菜包子 / 22:08 测试记录 直接删掉吧

新消息9条:
  10:49 醒了
  10:52 [Emoji: 坏笑]
  10:53 先修行一遍元母意程🙏 等我消息
  11:17 /备忘录 打卡 完成一次元母意程修行
  11:39 mmx 查下余额 以及账号有多少积分
  11:40 积分可以查询到吗
  11:41 比如 mmx 的 credtis
  11:49 起来看凡人修仙传咯
  11:50 /卡路里 记录体重 92.05kg
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from schedule_db import add_record_full, DB_PATH

DATE = "2026-06-27"

# ============ Block 定义 ============
BLOCKS = [
    # Block 1: 00:00 ~ 10:49 - 凌晨睡眠延续到醒来
    {
        "time_start": "00:00",
        "time_end": "10:49",
        "duration_minutes": 649,
        "activity": "睡眠（从昨晚困了准备睡觉到今早醒来）",
        "category": "睡眠",
        "source_contents": "前文[2026-06-26 23:29] 困了准备睡觉了 / [2026-06-27 10:49] 醒了（中间约11小时无消息，用前5后5判断为持续睡眠）",
        "source_timestamps": "2026-06-27 10:49:00",
        "analysis_reasoning": "游标最后记录为2026-06-26 23:59 '睡前闲聊+准备睡觉'，前一条[23:29]明确说'困了准备睡觉了'，后一条[10:49]明确'醒了'，中间约11小时无消息，应推断为持续睡眠。"
    },
    # Block 2: 10:49 ~ 10:53 - 刚醒、聊天
    {
        "time_start": "10:49",
        "time_end": "10:53",
        "duration_minutes": 4,
        "activity": "刚醒来、聊天打招呼",
        "category": "社交",
        "source_contents": "[10:49] 醒了\n[10:52] [Emoji: 坏笑]\n[10:53] 先修行一遍元母意程🙏 等我消息",
        "source_timestamps": "2026-06-27 10:49:00,2026-06-27 10:52:00,2026-06-27 10:53:00",
        "analysis_reasoning": "[10:49] 醒了是醒来信号，紧接着[10:52]坏笑表情、[10:53]宣布'先修行一遍元母意程'，三条消息均为起床后的简短聊天/表态（4分钟内），下一条[11:17]打卡表明修行已完成，活动已切换到修行阶段，故切割。"
    },
    # Block 3: 10:53 ~ 11:17 - 修行元母意程
    {
        "time_start": "10:53",
        "time_end": "11:17",
        "duration_minutes": 24,
        "activity": "修行元母意程",
        "category": "兴趣爱好",
        "source_contents": "[10:53] 先修行一遍元母意程🙏 等我消息\n[11:17] /备忘录 打卡 完成一次元母意程修行（中间无消息，约24分钟为修行时长）",
        "source_timestamps": "2026-06-27 10:53:00,2026-06-27 11:17:00",
        "analysis_reasoning": "[10:53] '先修行一遍元母意程等我消息'是明确的修行开始信号，[11:17] '/备忘录 打卡 完成一次元母意程修行'是明确的修行完成打卡，中间约24分钟无消息，应推断为持续修行元母意程活动。"
    },
    # Block 4: 11:17 ~ 11:39 - 修行结束后摸鱼/休息
    {
        "time_start": "11:17",
        "time_end": "11:39",
        "duration_minutes": 22,
        "activity": "打卡后休息/摸鱼",
        "category": "休闲",
        "source_contents": "[11:17] /备忘录 打卡 完成一次元母意程修行（中间约22分钟无消息，休息状态）",
        "source_timestamps": "2026-06-27 11:17:00",
        "analysis_reasoning": "[11:17]完成修行打卡后到[11:39]下一条消息之间约22分钟无消息，修行活动已结束，新活动尚未开始，应推断为打卡后的休息/摸鱼过渡阶段。"
    },
    # Block 5: 11:39 ~ 11:49 - 查询mmx余额和积分
    {
        "time_start": "11:39",
        "time_end": "11:49",
        "duration_minutes": 10,
        "activity": "查询mmx余额和积分",
        "category": "兴趣爱好",
        "source_contents": "[11:39] mmx 查下余额 以及账号有多少积分\n[11:40] 积分可以查询到吗\n[11:41] 比如 mmx 的 credtis",
        "source_timestamps": "2026-06-27 11:39:00,2026-06-27 11:40:00,2026-06-27 11:41:00",
        "analysis_reasoning": "[11:39] 'mmx 查下余额 以及账号有多少积分'是开始查询的指令，[11:40] '积分可以查询到吗'和[11:41] '比如 mmx 的 credtis'是连续的追问和澄清，三条消息均为查询mmx余额和积分的同一主题（约10分钟内）。下一条[11:49]切换到看凡人修仙传，故切割。"
    },
    # Block 6: 11:49 ~ 11:50 - 看凡人修仙传
    {
        "time_start": "11:49",
        "time_end": "11:50",
        "duration_minutes": 1,
        "activity": "开始看凡人修仙传",
        "category": "娱乐",
        "source_contents": "[11:49] 起来看凡人修仙传咯",
        "source_timestamps": "2026-06-27 11:49:00",
        "analysis_reasoning": "[11:49] '起来看凡人修仙传咯'是明确开始看剧的活动信号。下一条[11:50]切到记录体重，活动不同故切割。"
    },
    # Block 7: 11:50 ~ 11:50 - 记录体重
    {
        "time_start": "11:50",
        "time_end": "11:50",
        "duration_minutes": 0,
        "activity": "记录体重92.05kg",
        "category": "健康",
        "source_contents": "[11:50] /卡路里 记录体重 92.05kg",
        "source_timestamps": "2026-06-27 11:50:00",
        "analysis_reasoning": "[11:50] '/卡路里 记录体重 92.05kg'是明确的卡路里/健康记录动作（独立活动）。当前时刻12:20无后续消息，按规则末条消息之后不补齐，time_end为最后一条消息时间11:50。"
    },
]


def main():
    print(f"准备写入 {len(BLOCKS)} 个 block 到数据库 {DB_PATH}")
    print(f"日期: {DATE}")
    print()

    last_time_end = "00:00"
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