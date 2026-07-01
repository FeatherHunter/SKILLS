#!/usr/bin/env python3
"""
2026-07-01 午间同步脚本
按活动切换点切割 block 写入数据库

游标最后记录: 2026-07-01 01:13 躺上床+准备睡觉说晚安 [睡眠]
新消息: 20 条 (第1页/共1页, has_next=false)
最少需要 block: 4 个 (20 条 / 5条/块)
实际切割: 10 个 block (按活动切换点)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from schedule_db import add_record_full, DB_PATH
from block_count import get_required_block_count, validate_record_count

DATE = "2026-07-01"

# ============ 前置:获取最少 block 数量 ============
required_min = get_required_block_count(
    f"{DATE} 01:13:00",
    f"{DATE} 12:21:00",
    messages_per_block=5
)
print(f"前置: 最少需要 block 数量 = {required_min}")
print()

# ============ Block 定义 ============
BLOCKS = [
    # Block 1: 01:13 ~ 09:52 - 睡眠
    {
        "time_start": "01:13",
        "time_end": "09:52",
        "duration_minutes": 519,
        "activity": "睡眠(从说晚安到次日9:52醒来)",
        "category": "睡眠",
        "source_contents": "[01:13] msg_id=76051\n讨论的差不多了，我准备睡觉了。现在是7月1号凌晨1:12，我准备睡觉了，晚安",
        "source_timestamps": "2026-07-01 01:13:00",
        "analysis_reasoning": "[01:13]用户明确说'准备睡觉了，晚安'，是入睡信号;中间无任何用户消息(8小时39分钟);[09:52]用户醒来(由10:47消息'9:52的时候醒了'佐证)。前5后5窗口：前[00:51~01:13]准备躺下说晚安，后[10:47]9:52醒来报告。主活动=睡眠(从说晚安到9:52醒来),519分钟。"
    },
    # Block 2: 09:52 ~ 10:17 - 起床+起居
    {
        "time_start": "09:52",
        "time_end": "10:17",
        "duration_minutes": 25,
        "activity": "起床+起居(从9:52醒来到10:17开始微信电话)",
        "category": "起居",
        "source_contents": "[10:47] msg_id=76052\n9:52的时候醒了",
        "source_timestamps": "2026-07-01 10:47:00",
        "analysis_reasoning": "用户[10:47]报告'9:52的时候醒了'(注:消息时间戳10:47为报告时刻,实际醒来时间是9:52)。起床后到[10:17]开始与同事微信电话，中间25分钟是起床+起居事务。前5后5窗口：前[01:13~09:52]睡眠，后[10:17~10:47]微信电话讨论劳动纠纷。主活动=起床+起居,25分钟。"
    },
    # Block 3: 10:17 ~ 10:47 - 微信电话和同事讨论劳动纠纷
    {
        "time_start": "10:17",
        "time_end": "10:47",
        "duration_minutes": 30,
        "activity": "微信电话和同事讨论劳动纠纷维权细节(半小时)",
        "category": "社交",
        "source_contents": "[10:47] msg_id=76053\n和遇到劳动纠纷的同事交流了半小时微信电话 教了一下他关于需要维权的细节",
        "source_timestamps": "2026-07-01 10:47:00",
        "analysis_reasoning": "用户[10:47]报告'和遇到劳动纠纷的同事交流了半小时微信电话 教了一下他关于需要维权的细节'(注:消息时间戳10:47为报告时刻,实际通话时间是10:17~10:47半小时)。前5后5窗口：前[09:52~10:17]起床+起居，后[10:47]9:52醒来的报告(同一时间戳的另一条)。主活动=微信电话讨论劳动纠纷(社交支持),30分钟。"
    },
    # Block 4: 10:47 ~ 11:10 - 收衣服+挂衣服
    {
        "time_start": "10:47",
        "time_end": "11:10",
        "duration_minutes": 23,
        "activity": "收衣服+挂衣服(早间家务)",
        "category": "家务",
        "source_contents": "[11:09] msg_id=76054\n在吗\n\n[11:10] msg_id=76058\n刚才到现在把衣服给收了晒了",
        "source_timestamps": "2026-07-01 11:09:00,2026-07-01 11:10:00",
        "analysis_reasoning": "用户[10:47]报告了起床和微信电话(均为过去活动)后,继续做家务。[11:09]'在吗'是用户尝试与AI沟通(收衣服活动临近结束),[11:10]'刚才到现在把衣服给收了晒了'是用户报告10:47~11:10期间(23分钟)在做收衣服+晒衣服家务。前5后5窗口：前[10:17~10:47]微信电话,后[11:11]查询今日计划(新活动)。主活动=收衣服+挂衣服,23分钟。"
    },
    # Block 5: 11:10 ~ 11:17 - 查询今日计划+重复报告收衣服
    {
        "time_start": "11:10",
        "time_end": "11:17",
        "duration_minutes": 7,
        "activity": "查询今日计划(尝试唤醒AI查询计划)+再次报告收衣服",
        "category": "工作",
        "source_contents": "[11:11] msg_id=76055\n查询今日计划\n\n[11:12] msg_id=76056\n刚才到现在把衣服给收了晒了\n\n[11:14] msg_id=76057\n查询计划作息表",
        "source_timestamps": "2026-07-01 11:11:00,2026-07-01 11:12:00,2026-07-01 11:14:00",
        "analysis_reasoning": "[11:11]用户唤醒'查询今日计划';[11:12]用户再次报告'刚才到现在把衣服给收了晒了'(11:10已报告过,可能是用户觉得AI没看到);[11:14]用户换种说法'查询计划作息表'。3条消息7分钟内,主题=查询今日计划(可能AI响应不符合预期导致用户重试)。前5后5窗口：前[10:47~11:10]收衣服,后[11:17]用户禁止AI设置计划(切换为禁止操作)。主活动=查询今日计划+重复报告,7分钟。"
    },
    # Block 6: 11:17 ~ 11:25 - 怒骂AI+禁止设置计划+要求SQL清理
    {
        "time_start": "11:17",
        "time_end": "11:25",
        "duration_minutes": 8,
        "activity": "怒骂AI+禁止AI设置计划+要求SQL清理(用户对AI擅自操作不满)",
        "category": "工作",
        "source_contents": "[11:17] msg_id=76158\n禁止你设置我的计划作息表\n\n[11:18] msg_id=76159\n你查到作息计划来源于哪个文件？\n\n[11:19] msg_id=76160\n你是傻逼\n\n[11:19] msg_id=76161\n禁止在不确定时设置我的作息计划表\n\n[11:20] msg_id=76162\n全部硬删除\n\n[11:21] msg_id=76163\n直接 sql 清理 因为你是傻逼破坏了我的数据",
        "source_timestamps": "2026-07-01 11:17:00,2026-07-01 11:18:00,2026-07-01 11:19:00,2026-07-01 11:19:00,2026-07-01 11:20:00,2026-07-01 11:21:00",
        "analysis_reasoning": "用户对AI擅自设置/操作计划作息表表示强烈不满。[11:17]明确禁止AI设置计划;[11:18]质问AI数据来源;[11:19]怒骂'你是傻逼'+再次禁止;[11:20]命令'全部硬删除';[11:21]要求'直接 sql 清理'。6条消息8分钟内密集表达愤怒和清理指令。前5后5窗口：前[11:11~11:14]查询今日计划(用户触发),后[11:25]要求修正 skill 桥接(用户平复后)。主活动=用户怒骂AI+禁止操作+要求清理,8分钟。"
    },
    # Block 7: 11:25 ~ 11:34 - 修正 skill 桥接文件
    {
        "time_start": "11:25",
        "time_end": "11:34",
        "duration_minutes": 9,
        "activity": "修正作息管家skill桥接文件(要求openclaw桥接与skill本体同步)",
        "category": "工作",
        "source_contents": "[11:25] msg_id=76148\n/作息管家 在 openclaw 的 桥接文件的唤醒词内容需要和 skill 本体技能同步下\n\n[11:31] msg_id=76149\n好的",
        "source_timestamps": "2026-07-01 11:25:00,2026-07-01 11:31:00",
        "analysis_reasoning": "用户平复后,切换到新活动——修正作息管家skill桥接文件。[11:25]用户用'/作息管家'触发并要求'在 openclaw 的 桥接文件的唤醒词内容需要和 skill 本体技能同步下'(因为之前查询计划时AI表现混乱,可能是桥接文件与本体不同步);[11:31]'好的'是用户对AI响应的确认。2条消息9分钟内,主题=修正skill桥接。前5后5窗口：前[11:17~11:21]怒骂AI+要求清理,后[11:34]查询今日计划(新查询)。主活动=修正skill桥接,9分钟。"
    },
    # Block 8: 11:34 ~ 11:37 - 查询今日计划(详细SQL指令)
    {
        "time_start": "11:34",
        "time_end": "11:37",
        "duration_minutes": 3,
        "activity": "查询今日计划(用户发详细SQL指令要求AI查DB)",
        "category": "工作",
        "source_contents": "[11:34] msg_id=76150\n请帮我查询「作息管家」技能在 2026-07-01 这一天的全天计划。\n## 数据源(任选其一,DB 是 source of truth,飞书是镜像)\n### A. 本地 SQLite(权威,推荐)\n- DB 路径:D:\\2Study\\StudyNotes\\.db\\schedule_data.db\n- 表:schedule_plans\n- 字段:date(YYYY-MM-DD)/ time_start(HH:MM)/ time_end(HH:MM)/ title / notes / category / is_active(1=活跃)\n- 查 7/1 全部活跃事件:\n import sqlite3\n conn = sqlite3.connect(r'D:\\2Study\\StudyNotes\\.db\\schedule_data.db')\n rows = conn.execute(\"\"\"\n SELECT time_start, time_end, title, notes, category\n FROM schedule_plans\n WHERE date='2026-07-01' AND is_active=1\n ORDER BY time_start\n \"\"\").fetchall()\n for r in rows: print(r)",
        "source_timestamps": "2026-07-01 11:34:00",
        "analysis_reasoning": "用户[11:34]发出详细查询指令,要求AI按指定DB路径和SQL查询2026-07-01的schedule_plans全部活跃事件(因为之前AI查询出错,用户直接给AI写好查询脚本)。前5后5窗口：前[11:25~11:31]修正skill桥接,后[11:37]用户说'现在出门洗车去'(切换到新活动)。主活动=用户向AI发出详细SQL查询指令,3分钟(等待AI响应期间用户决定出门)。"
    },
    # Block 9: 11:37 ~ 11:56 - 出门洗车
    {
        "time_start": "11:37",
        "time_end": "11:56",
        "duration_minutes": 19,
        "activity": "出门洗车(去洗车点把车洗干净)",
        "category": "家务",
        "source_contents": "[11:37] msg_id=76151\n现在出门洗车去",
        "source_timestamps": "2026-07-01 11:37:00",
        "analysis_reasoning": "[11:37]用户明确说'现在出门洗车去',切换到出门洗车活动;中间约19分钟无消息(用户在外洗车);[11:56]用户发'我把车给洗了擦了...'(下一活动开始,标记洗车结束)。前5后5窗口：前[11:34]查询今日计划,后[11:56]洗车结束+回家。主活动=出门洗车,19分钟。"
    },
    # Block 10: 11:56 ~ 12:21 - 回家洗工具+套车套+再次报告收衣服
    {
        "time_start": "11:56",
        "time_end": "12:21",
        "duration_minutes": 25,
        "activity": "回家洗工具+套车套+再次报告收衣服(家务收尾)",
        "category": "家务",
        "source_contents": "[11:56] msg_id=76164\n我把车给洗了擦了，还算是干净的。\n我现在去回家：\n1. 把这个用于打扫汽车的工具给洗干净\n2. 把汽车的车套拿过来，把车给盖上\n\n[12:05] msg_id=76165\n刚才到现在把衣服给收了晒了",
        "source_timestamps": "2026-07-01 11:56:00,2026-07-01 12:05:00",
        "analysis_reasoning": "[11:56]用户告知洗车完成+准备回家做两件事(洗工具+套车套);[12:05]用户再次报告'刚才到现在把衣服给收了晒了'(本次是第3次报告,可能是回家途中/到家后又看到衣服需要收)。当前时间12:21,time_end不能超过当前时刻。前5后5窗口：前[11:37~11:56]出门洗车,后无更多用户消息(当前时刻12:21)。主活动=回家洗工具+套车套+收衣服(家务收尾),25分钟(到当前时刻)。"
    },
]


def main():
    print(f"准备写入 {len(BLOCKS)} 个 block 到数据库 {DB_PATH}")
    print(f"日期: {DATE}")
    print(f"最少需要: {required_min} 个 block (20 条/5)")
    print()

    last_time_end = "01:13"  # 上游标最后记录 time_end
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
            print(f"✓ Block {i:2d}: {block['time_start']}~{block['time_end']} ({block['duration_minutes']:3d}min) [{block['category']}] {block['activity'][:30]}... (id={record_id})")
            last_time_end = block["time_end"]
        except Exception as e:
            print(f"❌ Block {i} 写入失败: {e}")
            return

    print()
    print(f"✓ 全部 {len(BLOCKS)} 个 block 写入成功")
    print()

    # 后置校验
    print("=" * 60)
    print("后置: 调用 validate_record_count() 校验 block 数量是否达标")
    print("=" * 60)
    result = validate_record_count(
        f"{DATE} 01:13:00",
        f"{DATE} 12:21:00",
        messages_per_block=5
    )
    print(f"校验结果: {result}")
    print()

    if result is True:
        print("✅ 校验通过!")
    else:
        print(f"❌ 校验失败: {result}")
        print("需要根据提示重新拆分 block")


if __name__ == "__main__":
    main()
