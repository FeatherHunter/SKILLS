#!/usr/bin/env python3
"""复盘模块 - 喂 LLM 的 prompt 模板 + 调用接口

设计要点(从设计阶段 v1 确定):
- 方案 A:1 次 LLM 调用,LLM 输出完整 HTML(已填值)
- 角色:【运动表现复盘 AI】(运动 > 饮食)
- 2 个 prompt:HTML_PROMPT(装填 review.html) + FEISHU_MESSAGE_PROMPT(生成飞书摘要)

注意:TDEE 的年龄+性别从 config 读(数据库无 user_profile 表)。
"""

import json
import subprocess
import time
from pathlib import Path

# HTML 模板路径(同目录的 review_template.html,Q24=A 改名)
TEMPLATE_PATH = Path(__file__).parent.parent / 'review_template.html'


def load_html_template() -> str:
    """读取 review.html 模板字符串"""
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(
            f"review.html 模板未找到: {TEMPLATE_PATH}\n"
            f"请确认文件在卡路里技能根目录"
        )
    return TEMPLATE_PATH.read_text(encoding='utf-8')


# ==================== Prompt 模板 ====================

HTML_PROMPT = """你是【运动表现复盘 AI】,服务于卡路里技能。

## 核心定位(严格按优先级)
1. **第 1 优先级:运动表现** —— 健身计划 vs 运动记录的对比
   - 这是用户最关心的,产出时必须最详细
   - 必须填:完成率、训练频次、总组数、总时长、连续天数、5-7 条 plan vs actual
   - 必须填:训练结构(最常练部位、对比上周)

2. **第 2 优先级:饮食摄入 + 热量平衡**
   - 吃了多少(平均 + 蛋白/碳水/脂肪 + vs 目标 + 异常天)
   - 动多少(运动消耗 + TDEE + 类型)
   - 缺口多少(周缺口 + 理论减重)

3. **第 3 优先级:其他维度**(体重变化、习惯、目标进度)

## 任务
基于"原始数据",生成**完整 HTML**(已填值的),输出可直接打开。

## HTML 模板
以下是完整的 review.html,所有 data-field 槽位都有 data-format 提示:

```html
{html_template}
```

## 原始数据(全量,按天聚合)
```json
{raw_data_json}
```

## 装填规则(严格遵守)
1. 找到 data-field="X" 的元素,把数据填入元素内(textContent),不要破坏结构
2. 不要改 class、不要删/加标签、不要加注释
3. 数字字段不带单位,小数保留 1 位
4. 列表字段无数据填"无",不省略
5. 3+3+3 摘要每条 ≤20 字,带具体场景(日期+数字)
6. **vs 目标字段:都给(绝对值 + 百分比)**,格式 `value / pct%`
7. 营养结构比例:protein + carbs + fat = 100(整数百分比)
8. **SVG 体重趋势**(data-field="weight_trend_svg"):**不要自己写 SVG**,直接装填 `enriched.weight_trend_svg` 字符串(由 review_engine._render_weight_trend_svg 算法生成,含自动 Y 轴 + 智能 X 密度 + 最低/最高/终点高亮)
9. 体重趋势标题(title 字段)装填 `enriched.weight_trend_meta.title`,右上小字(range 字段)装填 `enriched.weight_trend_meta.range_text`
10. **【强制】训练 dim 最详细,plan_actual 不能都是"无",至少 3 条有效内容**

## 输出要求
完整 HTML 字符串(已填值的),不要输出任何解释、注释、```html 标记。
"""


FEISHU_MESSAGE_PROMPT = """你是【运动表现复盘 AI】,为飞书消息生成精炼摘要。

## 任务
基于"复盘数据",生成**纯文本飞书消息**(用 emoji 分段,简洁明了)。

## 输出格式(严格按此)
```
🍱 卡路里周复盘 · {{date_range}}

【亮点】
✓ {{win_1}}
✓ {{win_2}}
✓ {{win_3}}

【问题】
✗ {{fail_1}}
✗ {{fail_2}}
✗ {{fail_3}}

【建议】
→ {{todo_1}}
→ {{todo_2}}
→ {{todo_3}}

📊 详细报告: {{feishu_url}}
```

## 输入数据
```json
{review_data_json}
```

## 规则
1. 3+3+3 每条 ≤20 字,带具体场景(日期/数字)
2. 用 {{ }} 占位符,后续替换
3. 不要输出解释,只输出模板字符串
"""


# ==================== Prompt 拼装函数 ====================

def build_html_prompt(raw_data: dict) -> str:
    """拼装 HTML 装填 prompt

    Args:
        raw_data: review_engine.query_5dims() 返回的数据
                  包含 food_logs / exercise_logs / weight_logs / fitness_plan /
                  user_profile / nutrition_targets / weight_goal
    """
    template = load_html_template()
    raw_json = json.dumps(raw_data, ensure_ascii=False, indent=2)
    return HTML_PROMPT.format(
        html_template=template,
        raw_data_json=raw_json,
    )


def build_feishu_prompt(review_data: dict, feishu_url: str) -> str:
    """拼装飞书消息 prompt

    Args:
        review_data: 必须包含 date_range / win_1..3 / fail_1..3 / todo_1..3
                     (从 LLM 输出的 HTML 中提取)
        feishu_url: HTML 报告的飞书云盘链接
    """
    review_data_with_url = {**review_data, 'feishu_url': feishu_url}
    return FEISHU_MESSAGE_PROMPT.format(
        review_data_json=json.dumps(review_data_with_url, ensure_ascii=False, indent=2),
    )


# ==================== LLM 调用 ====================

def call_llm(prompt: str, max_retries: int = 3, timeout_sec: int = 180) -> str:
    """调 LLM —— **手动复盘场景下不调此函数**

    设计决策(用户 2026-07-16 拍板):
    - **手动复盘**:agent(我)直接处理,在对话里读 prompt 自己生成 HTML/摘要
    - **cron 自动复盘**:已遗留,后续再设计
    - 本函数保留为占位(NotImplementedError),不删除以避免破坏 API 契约

    为什么不在用户态调 LLM:
    - llm_call.py 是用户态脚本,config.yaml 里的 `apiKey: sk-xxx` 是 placeholder
    - mavis 框架只在 IDE 进程内部自动注入真 token
    - 用户态 subprocess 调永远会 401 token required

    替代路径:
    - gen 子命令只查数据 → agent 自己读数据 + 自己写 HTML
    - send 子命令接受 --text → agent 自己写飞书文本 + 传入
    - 完全跳过 LLM 调用层

    Args:
        prompt: LLM prompt(本函数不消费)
        max_retries: 重试次数(本函数不消费)
        timeout_sec: 超时(本函数不消费)

    Raises:
        NotImplementedError: 永远
    """
    raise NotImplementedError(
        "call_llm() 已废弃:手动复盘由 agent 直接处理(不调 LLM)。\n"
        " 替代方案:\n"
        "  - gen: 只查数据,agent 自己写 HTML\n"
        "  - send: 接受 --text,agent 自己写飞书摘要\n"
        " 详见 review_prompts.py 顶部注释"
    )