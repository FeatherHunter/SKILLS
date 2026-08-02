# 0007 备忘录 HELP HTML 重构为 4 级分类架构

HELP HTML 从 2 级(模块 + 场景)重构为 4 级(分类 → 子功能 → 场景 → 详情),并新增「首次使用/初始化」模块。

## 背景

用户首次使用技能时卡在 Python 安装,无新手引导入口。原 HELP HTML 为 2 级 details 结构,分组逻辑硬编码在 JS(`groups={...}` 按 wake_word 字符串分类),「批量类 / 跨Skill / 子唤醒词」是内部实现概念,用户不可理解。

## 决策(#31 8 决策 + #32/#33/#34/#35 落地)

1. **wake_word 单值**:每个场景一个主唤醒词(HELP 唯一展示名),**别名只在 SKILL.md 匹配层**,不进 scenarios.yaml(禁字段守卫)
2. **categories 列表**:顶层 `categories`(key/name/icon 有序数组)声明分组,场景 `category` 字段引用 key,渲染只读
3. **subfunction 可选**:空 →「基础」兜底组;单组分类(打卡/情绪/同步/初始化)不留子功能
4. **无 order 字段**:组内序 = scenarios.yaml 书写序(单文件 YAML 天然保序,避免双份顺序真相)
5. **7 必填字段保留** + category 必填(白名单校验)+ subfunction 可选
6. **不建反向索引**:29 场景全表扫描足够
7. **共享校验模块** `script/validate_scenarios.py`:测试 + 渲染前双触发(单一真相,坏数据不进 HTML)
8. **Init 展示名「首次使用」**:scenario_id = memo_init_setup;别名「初始化/新手」进 SKILL.md 触发层
9. **dependencies 可选字段**(#32):多行文本,Init 场景的环境依赖清单,渲染为圆点列表
10. **8 分类**(#33 第一性原理:对象 + 查找分离):备忘📝 / 查找🔍 / 提醒⏰ / 心愿🎯 / 打卡✅ / 情绪💭 / 同步🔄 / 初始化🚀;29 场景全映射(28 唯一唤醒词,备忘改分类 单条+批量 共用)
11. **4 级 details 渲染**(#34):Level 1 分类 → Level 2 子功能 → Level 3 场景卡(复制按钮总可见)→ Level 4 详情子折叠(dimensions/prompt/result + dependencies 块);JS 数据驱动,payload.categories 注入

## 后果

- scenarios.yaml 与 SKILL.md 镜像约束调整(version 1.2.0)
- Init 模块作为新顶层 category「初始化类」;「首次使用」触发后 AI 直接诊断环境(复用现有命令,不新增 check-env)
- wake_word 允许多对一(备忘改分类 单条+批量),唯一性只在 scenario_id
- HELP HTML 渲染即切换,无灰度期;旧 2 级结构不再保留

## 替代方案

| 方案 | 说明 | 结论 |
|------|------|------|
| A 双源 | scenarios 平铺 + categories 树双份存储 | ❌ 双源漂移风险,需一致性测试 |
| B 卡路里式(选中) | 平铺 + category/subfunction 字段,渲染时分组 | ✅ 与卡路里同型,单一真相 |
| C 嵌套 + 索引 | 完整嵌套树 + 顶层 wake_word 索引 | ❌ YAML 变长,索引冗余 |

3 级 vs 4 级:卡路里 3 级(详情为场景内子块),本技能选 4 级(详情独立折叠,用户按需展开维度/prompt/结果)。

## Status

accepted · 2026-08-02 · wayfinder #30 map · #31-#36 tickets

## 何时复议

若场景数 > 100(需反向索引)或出现跨文件存储(需 order 字段),复议本 ADR。

## 与既有 ADR 关系

- ADR-0003(commit 全中文 · Tested-By):本 ADR 涉及 commit,遵循该约定
- ADR-0004(A.4 .scratch 5 文件范式):本次 spec/决策落 `.scratch/memo-help-4level-init-map/`
- ADR-0006(templates 静态扫描):4 级渲染脚本仍由 template_lint 守护

## Related

- map: issue #30(wayfinder:map · 已关)
- tickets: #31(schema)/ #32(Init 内容)/ #33(归类)/ #34(渲染)/ #35(测试)/ #36(本 ADR)
- spec: `.scratch/memo-help-4level-init-map/`
