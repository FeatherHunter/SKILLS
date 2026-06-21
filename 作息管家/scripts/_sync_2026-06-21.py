#!/usr/bin/env python3
"""
2026-06-21 午间同步脚本
按活动切换点切割 block 写入数据库
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from schedule_db import add_record_full, DB_PATH

DATE = "2026-06-21"

# ============ Block 定义 ============
# 游标最后记录: 2026-06-21 02:10 [睡眠]
# 新消息6条:
#   07:00 醒了
#   07:01 睡了估计有七小时不到
#   08:33 看了90分钟手机 打算再睡觉
#   08:46 开始睡觉 不用闹钟
#   11:42 醒了 起床了
#   11:51 起来咯 开始做饭吃 哈哈

BLOCKS = [
    # Block 1: 02:10 ~ 07:00 - 凌晨睡眠延续到醒来
    {
        "time_start": "02:10",
        "time_end": "07:00",
        "duration_minutes": 290,
        "activity": "凌晨睡眠延续（接续02:10睡眠状态）",
        "category": "睡眠",
        "source_contents": "[07:00] 醒了",
        "source_timestamps": "2026-06-21 07:00:00",
        "analysis_reasoning": "游标最后记录02:10为睡眠状态，新消息第一条 [07:00] 醒了 是明确醒来信号，中间约5小时无消息应推断为持续睡眠。"
    },
    # Block 2: 07:00 ~ 07:01 - 醒来说话
    {
        "time_start": "07:00",
        "time_end": "07:01",
        "duration_minutes": 1,
        "activity": "醒来后报告睡眠时长",
        "category": "休闲",
        "source_contents": "[07:00] 醒了\n[07:01] 睡了估计有七小时不到",
        "source_timestamps": "2026-06-21 07:00:00,2026-06-21 07:01:00",
        "analysis_reasoning": "[07:00] 醒了 后 [07:01] 睡了估计有七小时不到 是醒来后立即回复睡眠时长的简短对话。下一条 [08:33] 看了90分钟手机 是切换到看手机活动，故切割。"
    },
    # Block 3: 07:01 ~ 08:33 - 看手机
    {
        "time_start": "07:01",
        "time_end": "08:33",
        "duration_minutes": 92,
        "activity": "躺在床上看手机",
        "category": "休闲",
        "source_contents": "[07:01] 睡了估计有七小时不到\n[08:33] 看了90分钟手机 打算再睡觉",
        "source_timestamps": "2026-06-21 07:01:00,2026-06-21 08:33:00",
        "analysis_reasoning": "[08:33] 看了90分钟手机 打算再睡觉 明确说明从7:01到8:33期间（约92分钟）主要在看手机。下一条 [08:46] 开始睡觉 是切换到睡眠活动，故切割。"
    },
    # Block 4: 08:33 ~ 08:46 - 决定再睡
    {
        "time_start": "08:33",
        "time_end": "08:46",
        "duration_minutes": 13,
        "activity": "决定继续睡觉（从看手机过渡到入睡）",
        "category": "休闲",
        "source_contents": "[08:33] 看了90分钟手机 打算再睡觉\n[08:46] 开始睡觉 不用闹钟",
        "source_timestamps": "2026-06-21 08:33:00,2026-06-21 08:46:00",
        "analysis_reasoning": "[08:33] 看了90分钟手机打算再睡觉 → [08:46] 开始睡觉不用闹钟 是从决定再睡到实际入睡的过渡阶段（约13分钟），与前后的睡眠/看手机活动不同（明确决策过程），单独成块。"
    },
    # Block 5: 08:46 ~ 11:42 - 上午睡觉
    {
        "time_start": "08:46",
        "time_end": "11:42",
        "duration_minutes": 176,
        "activity": "上午睡觉（无需闹钟）",
        "category": "睡眠",
        "source_contents": "[08:46] 开始睡觉 不用闹钟\n[11:42] 醒了 起床了",
        "source_timestamps": "2026-06-21 08:46:00,2026-06-21 11:42:00",
        "analysis_reasoning": "[08:46] 开始睡觉不用闹钟 是入睡信号，[11:42] 醒了起床了 是明确醒来信号，中间约176分钟无消息，应为持续睡眠。"
    },
    # Block 6: 11:42 ~ 11:51 - 起床
    {
        "time_start": "11:42",
        "time_end": "11:51",
        "duration_minutes": 9,
        "activity": "起床准备（从醒来到准备做饭）",
        "category": "休闲",
        "source_contents": "[11:42] 醒了 起床了\n[11:51] 起来咯 开始做饭吃 哈哈",
        "source_timestamps": "2026-06-21 11:42:00,2026-06-21 11:51:00",
        "analysis_reasoning": "[11:42] 醒了起床了 后 [11:51] 起来咯开始做饭吃 是起床后的过渡阶段（约9分钟），包含从醒来到准备开始做饭的过程。"
    },
    # Block 7: 11:51 ~ 11:51 - 开始做饭吃
    {
        "time_start": "11:51",
        "time_end": "11:51",
        "duration_minutes": 0,
        "activity": "开始做饭吃",
        "category": "餐饮",
        "source_contents": "[11:51] 起来咯 开始做饭吃 哈哈",
        "source_timestamps": "2026-06-21 11:51:00",
        "analysis_reasoning": "[11:51] 起来咯开始做饭吃哈哈 是明确开始做饭吃的活动起点信号（独立活动）。当前时刻12:21无后续消息，按规则末条消息之后不补齐，time_end为最后一条消息时间11:51。"
    },
]


def main():
    print(f"准备写入 {len(BLOCKS)} 个 block 到数据库 {DB_PATH}")
    print(f"日期: {DATE}")
    print()

    last_time_end = "02:10"
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
