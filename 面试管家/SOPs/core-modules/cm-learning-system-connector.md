# 学习系统交互模块

> 模块：cm-learning-system-connector  
> 用途：读写learning-system数据，严格遵循ls-data-structure.md  
> 依赖：ls-data-structure.md, LLM-WIKI skill

---

## 一、模块概述

本模块负责interview-system与learning-system之间的数据交互。

**核心原则**：
- 读取：直接读取learning-system的文件
- 写入：不修改learning-system任何文件，通过报告输出

---

## 二、读取接口

### 2.1 progress.json 读取

```json
读取路径：D:\2Study\StudyNotes\2026\learning-system\progress.json
```

| 需求 | 字段路径 | 返回值 |
|------|----------|--------|
| 知识点列表 | knowledge_progress | Object |
| 单知识点Level | knowledge_progress.{id}.current_level | number (0-7) |
| 基础流程状态 | knowledge_progress.{id}.foundation_path.status | string |
| 精通流程状态 | knowledge_progress.{id}.mastery_path.status | string |
| STAR案例路�� | knowledge_progress.{id}.interview_assets.star_case_path | string or null |
| 反面案例路径 | knowledge_progress.{id}.interview_assets.failure_case_path | string or null |
| ADR路径 | knowledge_progress.{id}.interview_assets.adr_path | string or null |

### 2.2 knowledge-list.json 读取

```json
读取路径：D:\2Study\StudyNotes\2026\learning-system\knowledge-list.json
```

| 需求 | 字段路径 | 返回值 |
|------|----------|--------|
| 知识点元数据 | knowledge.{id} | Object |
| 知识点标题 | knowledge.{id}.title | string |
| 语言 | knowledge.{id}.language | string |
| 分类 | knowledge.{id}.category | string |
| 依赖 | knowledge.{id}.metadata.dependencies | array |

### 2.3 LLM-WIKI 读取

```
读取方式：LLM-WIKI QUERY "{knowledge_id}"
返回：entity页完整内容，含frontmatter的related_to
读取路径：D:\2Study\StudyNotes\2026\learning-system\wiki\
```

---

## 三、Level计算规则

```python
def calculate_level(knowledge_id):
    progress = read_progress()
    kp = progress.knowledge_progress[knowledge_id]

    foundation = kp.foundation_path.status
    mastery = kp.mastery_path.status

    if foundation == "completed":
        base = 4
        if mastery == "completed":
            return 7
        elif mastery == "in_progress":
            current_stage = kp.mastery_path.current_stage
            return 4 + (current_stage - 5)  # stage5->5, stage6->6
        else:
            return 4
    elif foundation == "in_progress":
        current_stage = kp.foundation_path.current_stage
        return current_stage - 1  # stage1->1, stage2->2, stage3->3
    else:
        return 0
```

---

## 四、错误处理

| 场景 | 处理 |
|------|------|
| learning-system目录不存在 | 报错：learning-system未初始化 |
| progress.json不存在或为空 | 返回空对象，标记"无学习记录" |
| 知识点无数据 | 返回该知识点为level=0 |
| LLM-WIKI未找到 | **必须报错**，不要瞎走流程 |

---

## 五、数据写入规则

本模块**不写入**learning-system的任何文件。

补强建议通过报告输出：
- 输出位置：interview-system/reports/final-reports/
- 格式：JSON + Markdown
- 供learning-system解析读取

---

## 六、接口函数

### 6.1 get_knowledge_progress(knowledge_id)

返回知识点的学习进度

### 6.2 get_interview_assets(knowledge_id)

返回面试叙事素材路径

### 6.3 get_knowledge_metadata(knowledge_id)

返回知识点元数据

### 6.4 get_all_knowledge_ids()

返回所有已学习的知识点ID列表

### 6.5 check_readiness(knowledge_id)

检查知识点是否达到面试就绪标准（Level >= 4）

---

> 本模块由主流程SOP在Step 1调用