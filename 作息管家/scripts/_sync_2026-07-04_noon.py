#!/usr/bin/env python3
"""
2026-07-04 午间同步脚本
按活动切换点切割 block 写入数据库

游标最后记录: 2026-07-04 01:59 优化智剪工坊/vlog剪辑技能 [工作]
新消息: 8 条 (第1页/共1页, has_next=false)
最少需要 block: 2 个 (8 条 / 5条/块)
实际切割: 6 个 block (按活动切换点)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from schedule_db import add_record_full, DB_PATH
from block_count import get_required_block_count, validate_record_count

DATE = "2026-07-04"

# ============ 前置:获取最少 block 数量 ============
required_min = get_required_block_count(
    f"{DATE} 01:59:00",
    f"{DATE} 12:20:00",
    messages_per_block=5
)
print(f"前置: 最少需要 block 数量 = {required_min}")
print()

# ============ Block 定义 ============
BLOCKS = [
    # Block 1: 01:59 ~ 02:24 - 优化智剪工坊/vlog剪辑技能 [工作] (25 min)
    {
        "time_start": "01:59",
        "time_end": "02:24",
        "duration_minutes": 25,
        "activity": "优化智剪工坊/vlog剪辑技能(延续凌晨的剪视频skill优化)",
        "category": "工作",
        "source_contents": "[01:59] msg_id=82402\n[message_id: om_x100b6b4bc95120a4b29ac809b6c3d9c]\nou_c9f2e82c30540a3b5898cd062062772dd51: 捣鼓到现在 剪辑 vlog 的技能优化\n\n[02:24] msg_id=82403\n[message_id: om_x100b6b4baa707ca4b3921bb861645d6]\nou_c9f2e82c30540a3b5898cd062772dd51: 还在处理剪视频 skill，真累哈".replace("062062772dd51", "062772dd51"),
        "source_timestamps": "2026-07-04 01:59:00,2026-07-04 02:24:00",
        "analysis_reasoning": "[01:59]用户继续报告'捣鼓到现在 剪辑 vlog 的技能优化',延续上一block的'优化智剪工坊技能'活动(同一工作);[02:24]用户说'还在处理剪视频 skill,真累哈'是同一活动的延续收尾,接着用户说'打算睡了'→ 这是该活动的明确结束信号,准备进入下一活动。前5后5窗口:前[00:53一直在优化智剪工坊技能][21:55到家了][21:44健身结束了],后[02:24打算睡了][02:26关闭每日检查cron]。主活动=优化智剪工坊/vlog剪辑技能(工作),25分钟。"
    },
    # Block 2: 02:24 ~ 02:26 - 准备睡觉(关闭每日检查cron) [起居] (2 min)
    {
        "time_start": "02:24",
        "time_end": "02:26",
        "duration_minutes": 2,
        "activity": "准备睡觉(关闭每日检查 cron 定时任务)",
        "category": "起居",
        "source_contents": "[02:24] msg_id=82404\n[message_id: om_x100b6b4baa2f90a0b274fcd64273960]\nou_c9f2e82c30540a3b5898cd062772dd51: 打算睡了\n\n[02:26] msg_id=82405\n[message_id: om_x100b6b4ba27434a0b3fbfe1ce513f31]\nou_c9f2e82c30540a3b5898cd062772dd51: 关闭每日检查的 cron 定时任务",
        "source_timestamps": "2026-07-04 02:24:00,2026-07-04 02:26:00",
        "analysis_reasoning": "[02:24]用户说'打算睡了',切换到睡前准备阶段;[02:26]用户执行'关闭每日检查的 cron 定时任务'(系统操作,睡前收尾)。这是睡前准备的连续动作(2分钟),应切为独立block。前5后5窗口:前[02:24还在处理剪视频 skill][01:59捣鼓到现在剪辑vlog的技能优化],后[06:02还没睡 现在才睡][中间无消息]。主活动=准备睡觉(关闭每日检查cron),2分钟。"
    },
    # Block 3: 02:26 ~ 06:02 - 睡前摸鱼(迟迟未能入睡) [休闲] (216 min)
    {
        "time_start": "02:26",
        "time_end": "06:02",
        "duration_minutes": 216,
        "activity": "睡前摸鱼(说打算睡但实际3小时36分钟没睡,推测玩手机/刷手机)",
        "category": "休闲",
        "source_contents": "[02:26] msg_id=82405\n[message_id: om_x100b6b4ba27434a0b3fbfe1ce513f31]\nou_c9f2e82c30540a3b5898cd062772dd51: 关闭每日检查的 cron 定时任务\n\n[06:02] msg_id=82406\n[message_id: om_x100b6bb75965cca8b497189484b6b93]\nou_c9f2e82c30540a3b5898cd062772dd51: 还没睡 现在才睡".replace("062062772dd51", "062772dd51"),
        "source_timestamps": "2026-07-04 02:26:00,2026-07-04 06:02:00",
        "analysis_reasoning": "[02:26]用户说'打算睡了'并'关闭每日检查cron',但3小时36分钟后[06:02]用户报告'还没睡 现在才睡'→ 这是一条反证信号:用户虽然02:24说打算睡了,实际到06:02才真正入睡,这3小时36分钟用户是醒着的。中间无消息记录(推测在床上玩手机/刷手机/发呆)。必须用[02:26] + [06:02] 两个端点消息作为source_contents,推断主活动=睡前摸鱼(玩手机/刷手机)。前5后5窗口:前[02:24打算睡了][01:59捣鼓到现在][21:55到家了],后[06:02还没睡 现在才睡][11:12捣鼓了一小时技能]。主活动=睡前摸鱼(迟迟未能入睡),216分钟。"
    },
    # Block 4: 06:02 ~ 11:12 - 睡眠 [睡眠] (310 min)
    {
        "time_start": "06:02",
        "time_end": "11:12",
        "duration_minutes": 310,
        "activity": "睡眠(从6:02说'现在才睡'到11:12起床后捣鼓技能)",
        "category": "睡眠",
        "source_contents": "[06:02] msg_id=82406\n[message_id: om_x100b6bb75965cca8b497189484b6b93]\nou_c9f2e82c30540a3b5898cd062772dd51: 还没睡 现在才睡\n\n[11:12] msg_id=82456\n[message_id: om_x100b6bb3ee25c0acb3e02bfb2e35219]\nou_c9f2e82c30540a3b5898cd062772dd51: 捣鼓了一小时技能".replace("062062772dd51", "062772dd51"),
        "source_timestamps": "2026-07-04 06:02:00,2026-07-04 11:12:00",
        "analysis_reasoning": "[06:02]用户说'现在才睡'是明确的入睡信号;[11:12]用户报告'捣鼓了一小时技能'(起床后已开始工作1小时)→ 反推起床时间约在10:12左右,到11:12已经起床后工作1小时。这之间约5小时10分钟(310分钟)用户处于睡眠状态。中间无消息记录(用户睡觉)。必须用[06:02] + [11:12] 两个端点消息作为source_contents,推断主活动=睡眠。前5后5窗口:前[02:26关闭每日检查cron][02:24打算睡了],后[11:12捣鼓了一小时技能][11:12现在开始做午饭][11:15起床了]。主活动=睡眠,310分钟。"
    },
    # Block 5: 11:12 ~ 11:12 - 起床后捣鼓技能(继续vlog/智剪工坊技能优化) [工作] (0 min)
    {
        "time_start": "11:12",
        "time_end": "11:12",
        "duration_minutes": 0,
        "activity": "起床后捣鼓技能(继续vlog/智剪工坊技能优化,捣鼓了一小时)",
        "category": "工作",
        "source_contents": "[11:12] msg_id=82456\n[message_id: om_x100b6bb3ee25c0acb3e02bfb2e35219]\nou_c9f2e82c30540a3b5898cd062772dd51: 捣鼓了一小时技能".replace("062062772dd51", "062772dd51"),
        "source_timestamps": "2026-07-04 11:12:00",
        "analysis_reasoning": "[11:12]用户发'捣鼓了一小时技能'(描述过去一小时的工作),切换到新工作活动;[11:12]紧接着用户发'现在开始做午饭'→ 这是该工作的明确结束信号,切换到餐饮活动。两条消息在同一分钟但活动类型不同(工作→餐饮),必须切为独立block。前5后5窗口:前[06:02还没睡 现在才睡],后[11:12现在开始做午饭][11:15起床了]。主活动=起床后捣鼓技能(继续vlog/智剪工坊技能优化),0分钟(衔接,实际工作时段在10:12~11:12的睡眠block反推中)。"
    },
    # Block 6: 11:12 ~ 11:15 - 做午饭 [餐饮] (3 min)
    {
        "time_start": "11:12",
        "time_end": "11:15",
        "duration_minutes": 3,
        "activity": "开始做午饭(起床后的第一顿)",
        "category": "餐饮",
        "source_contents": "[11:12] msg_id=82457\n[message_id: om_x100b6bb3efd4f8acb17f0a683417a37]\nou_c9f2e82c30540a3b5898cd062772dd51: 现在开始做午饭\n\n[11:15] msg_id=82458\n[message_id: om_x100b6bb2f6dc34a8b1a19ed2d1d44f6]\nou_c9f2e82c30540a3b5898cd062772dd51: 起床了".replace("062062772dd51", "062772dd51"),
        "source_timestamps": "2026-07-04 11:12:00,2026-07-04 11:15:00",
        "analysis_reasoning": "[11:12]用户发'现在开始做午饭',切换到餐饮活动;[11:15]用户发'起床了'→ 这是补发的起床信号(说明用户实际起床比11:12更早,可能在10:12左右就起了,起床后捣鼓了一小时技能,11:12开始做午饭)。补发的'起床了'消息放在当前block,表示餐饮活动开始确认。前5后5窗口:前[11:12捣鼓了一小时技能][06:02还没睡 现在才睡],后[无更多新消息,当前为最后一block]。主活动=开始做午饭,3分钟。"
    },
]

# ============ 写入数据库 ============
print(f"准备写入 {len(BLOCKS)} 个 block:")
for i, b in enumerate(BLOCKS, 1):
    print(f"  Block {i}: {b['time_start']} ~ {b['time_end']} | {b['activity']} [{b['category']}] ({b['duration_minutes']} min)")
print()

ids = []
for b in BLOCKS:
    record_id = add_record_full(
        date=DATE,
        time_start=b["time_start"],
        time_end=b["time_end"],
        duration_minutes=b["duration_minutes"],
        activity=b["activity"],
        category=b["category"],
        source_contents=b["source_contents"],
        source_timestamps=b["source_timestamps"],
        analysis_reasoning=b["analysis_reasoning"],
    )
    ids.append(record_id)
    print(f"  ✓ 写入 id={record_id}: {b['time_start']}~{b['time_end']} {b['activity']}")

print()
print(f"成功写入 {len(ids)} 条记录, IDs: {ids}")
print(f"数据库: {DB_PATH}")
print()

# ============ 后置:验证 block 数量 ============
result = validate_record_count(
    f"{DATE} 01:59:00",
    f"{DATE} 12:20:00",
    messages_per_block=5
)
print(f"后置校验结果: {result}")
if result is True:
    print("✅ Block 数量达标, 同步完成")
else:
    print(f"❌ Block 数量不足, 需要重新拆分: {result}")