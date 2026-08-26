# 马里 注册要点

> last_verified: 2026-08-26（AI 联网初版；官方注册手册下载未成功，原文待补）
> 状态: 已开发市场

## 1. 概况

- 监管机构: **DPM（Direction de la Pharmacie et du Médicament，药事与药品管理局）**，隶属卫生与社会发展部；注册决策链条: DPM 内部评估 + 外部专家（经费受限不定期）→ **国家药品委员会（Commission Nationale du Médicament）**审议 → 卫生部长签发 → DPM 局长通知申请人。质量检验归国家卫生实验室（LNS），场所检查归卫生监察（ISP）（2026-08-26 AI 联网 NEPAD/WHO 国别档案，待确认）
- 官网: https://www.dirpharma.ml/ （联系 info@dirpharma.ml, +223 20 22 24 63）；新上线数字化门户「Guichet du Médicament」: https://amm-mali.eregistrations.org/ （AI 联网，待确认）
- 官方语言: 法语——**注册 dossier 须 CTD 格式且用法语**（2026-08-26 用户确认 CTD，已核实；法语要求 AI 联网 AREMA 印证，待确认）
- 主要法规: 马里为 **UEMOA + ECOWAS 双成员国**——适用 UEMOA 条例（同科特迪瓦框架，见 `sources/uemoa/`）+ ECOWAS/WAHO 统一注册指南（CTD 格式）；国家层面有 Decree 04-557/P-RM 等文本（AI 联网，待确认）

## 2. 注册路径

- 申报类型: 上市许可 AMM；申请分类为新申请/续期/变更三类（用户确认 CTD 口径下的常规路径；AI 联网，待确认）
- 本地代理要求: 需本地授权代表（AI 联网，待确认）
- 流程步骤（AI 联网 NEPAD 档案，待确认）: **纸质 dossier + 两张光盘**递交至 DPM 局长 → 分配至相关处室 → 注册官评估 → 国家药品委员会审议 → 部长批准发证
- 简化通道: 经严格监管机构（SRA）评估或 WHO PQ 的产品可交**简缩摘要文件**；其余产品（含被忽视热带病用药）须全套文件（AI 联网 ECOWAS 指南口径，待确认）

## 3. 文件要求

- Dossier 格式: **CTD 格式**（2026-08-26 用户确认，已核实）；按 ECOWAS CTD 指南（2018 年 6 月版）组织
- 申请规则（ECOWAS 指南口径，AI 联网，待确认）:
  - 一个产品一份申请；同一 API+规格+生产商+生产地+质量标准+剂型、仅包装/装量不同的可合并一份
  - 同 API 但盐型/规格/剂型/商品名不同 → 分别申请
- 新申请随附（AI 联网，待确认）:
  - 样品: 一个批次商业包装 + 批 COA（数量按 WAHO/NMRA schedule）
  - **CPP**: 原产国主管当局按 WHO 格式出具，放 CTD Module 1
  - **Site Master File**: 放 Module 3
  - 药物警戒计划: NCE/创新药须提交（Module 1.2.8 PSUR 相关）
- GMP: 法规要求注册材料中含 **GMP 检查报告和/或证书**（NEPAD 档案，待确认）；WAHO 或所在国 NMRA 可开展检查，报告互认避免重复
- 必须生产商提供的文件: CPP、SMF、样品批 COA 等（按惯例全部来自生产商，待确认）

## 4. 样品要求

- 数量: 按 WAHO/DPM schedule 执行，公开来源未见固定数字表（待录入；实操前问客户/代理）
- 是否需要原料药样品: 未查到明确要求（待录入）
- 样品 COA: 需要——样品批 COA 随样提交（AI 联网 ECOWAS 口径，待确认）；马里对注册前样品进行实验室检验（NEPAD 档案，待确认）

## 5. Artwork 要求

- 语言: 法语（推断自 dossier 法语要求，待确认）
- 注册号标注 / 警示语细节: 待录入

## 6. 时间与费用

- 审评周期（AI 联网 ECOWAS 指南口径，待确认）: 完整新申请 ≤ **12 个月**；优先药品/本地产/变更/续期 ≤ 90 个工作日
- 注册有效期: **5 年**（AI 联网多方一致含 ECOWAS 指南与 UEMOA 条例第 16 条，已核实条例层面）
- 再注册周期: 到期前**至少 3 个月**启动续期；续期材料: 申请表 + **递交前 6 个月内实际生产的 BMR** + PSUR + 仿制药互换性证明 + 样品批 COA + SMF（AI 联网 ECOWAS 口径，待确认）
- 问询答复: **6 个月内未答复视为撤回**；第二次答复仍不合格则拒签、须重新申请（AI 联网，待确认）
- 申诉: 决定通知后 **2 个月**内书面申诉（AI 联网，待确认）
- 注册费用: 按 NMRA/WAHO 费率表，进口 vs ECOWAS 本地生产不同档，金额待录入

## 7. 常见坑

- **法语 CTD 是硬门槛**: 与科特迪瓦同属 UEMOA 圈，但科特迪瓦允许技术文件用英语（申请信+RCP 法语即可），马里口径是整个 dossier 用法语——翻译工作量提前算（AI 联网 AREMA 口径 vs 科特迪瓦官方程序对照，待确认）
- 问询 6 个月死线与利比里亚相同，补料响应机制要建好（AI 联网，待确认）
- 续期要附**近 6 个月内生产的 BMR**——工厂要留好最近批次记录（AI 联网，待确认）
- 数字化刚起步（Guichet du Médicament 上线中），实操可能纸质与线上并行，递交前与代理确认渠道（AI 联网，待确认）

> 详细来源: dirpharma.ml 官方《Manuel de procédures pour l'enregistrement des médicaments à usage humain au Mali》（PDF 约 8MB，服务器限速两次下载均截断损坏，原件待补——URL 已记录）；ECOWAS CTD Guidance June 2018；NEPAD AMRH Mali 国别档案；AREMA Mali 页
