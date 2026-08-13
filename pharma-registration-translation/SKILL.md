---
name: pharma-registration-translation
description: Use ONLY when translating Chinese pharmaceutical registration dossiers (药品注册资料 / 药品注册申报资料) into English for overseas NMRA submissions. Covers Certificate of Analysis (COA / 检验报告 / 检验报告书), Drug Product specifications, raw material specifications, CMC documents, and regulatory filings. Front-load trigger keywords: 药品注册, COA, 检验报告, 注册资料, 注册申报, 翻译, 翻译件, Specifications, Assay, Related Substances, Ciprofloxacin, 环丙沙星, 马达加斯加, Madagascar, FP, DP.
---

# International Pharmaceutical Registration — English Translation Database

Hard rules. Apply verbatim. Do not improvise alternatives.

## 1. Compliance phrases (highest priority — user-corrected)

| Chinese (中文)          | Correct English              | DO NOT USE (已被禁用)           |
|-------------------------|------------------------------|---------------------------------|
| 符合规定                | Complies                     | conform, conforms, pass         |
| 应符合规定              | Should be comply             | Should conform, should pass     |
| 不符合规定              | Does not comply              | Does not conform, fail          |
| 符合/不符合 限度要求    | Meets / Does not meet the limit | conform to / fail the limit   |

These four rows are the authoritative fix for prior translation errors. Every other translation in this skill is built on top of them.

## 2. 验证 vs 确认 — project-wide convention (user-corrected, supersedes prior rule)

For this project, both 验证 and 确认 are rendered in English as **validation / validate** (verb forms included). Do NOT distinguish the two Chinese terms in the English output.

| Chinese            | Part of speech | Correct English (project rule) | DO NOT USE |
|--------------------|----------------|--------------------------------|------------|
| 验证 (noun)        | noun           | validation                     | verification, verify |
| 验证 (verb)        | verb           | validate / validated / validating | verify, verified |
| 确认 (noun)        | noun           | validation                     | verification, verify |
| 确认 (verb)        | verb           | validate / validated / validating | verify, verified |

Concrete lexical swaps the user has approved (apply uniformly):

| Chinese phrase                            | Correct English                              |
|-------------------------------------------|----------------------------------------------|
| 验证方案 / 确认方案 / 验证计划 / 确认计划 | validation protocol / validation plan        |
| 验证证书 / 确认证书 / 验证报告 / 确认报告 | validation certificate / validation report   |
| 验证小组 / 确认小组 / 验证总负责人 / 确认总负责人 | validation team / overall validation lead |
| 验证管理 / 确认管理 / 验证管理部门 / 确认管理部门 | validation management / validation management department |
| 验证专员 / 确认专员                        | validation specialist                        |
| 验证小组长 / 确认小组长 / 验证小组人员     | validation team leader / validation team members |
| 验证（verb）/ 确认（verb）                  | validate / validated / validating            |
| 验证结果 / 确认结果 / 验证记录 / 确认记录 | validation result / validation record        |

Rationale: the company's English output treats 验证 and 确认 as interchangeable terms for a single in-house activity, and uses "validation" as the umbrella English term.

## 3. Document structural rule — Table of Contents

- **Delete the entire Table of Contents block** (the "目录" heading line and every TOC entry, including the auto-generated TOC field, hyperlinks, PAGEREF fields, and the dotted leader tabs).
- Detect the TOC block by paragraph text "目录" (and obvious variants like "目  录", "目     录"). Delete that heading paragraph and every contiguous TOC-style paragraph (`toc 1` / `toc 2` / `toc 3` style) that follows it, up to the next non-TOC paragraph.
- Body headings (Heading 1 / Heading 2 / Heading 3 / Title styles) ARE still translated; only the generated TOC is removed.
- Do not attempt to regenerate the TOC. The translated document is shipped without one.

## 4. COA header fields (Certificate of Analysis / 检验报告)

| 中文           | English                          |
|----------------|----------------------------------|
| 检验报告       | Certificate of Analysis (COA)    |
| 产品名称       | Product Name                     |
| 批号           | Batch No.                        |
| 规格           | Specification                    |
| 包装规格       | Package Specification            |
| 数量           | Quantity                         |
| 生产日期       | Date of Manufacture              |
| 有效期至       | Expiry Date                      |
| 报告日期       | Report Date                      |
| 检验依据       | Test Basis                       |
| 来源           | Source                           |
| 检验项目       | Test Item                        |
| 检验标准       | Acceptance Criteria              |
| 检验结果       | Test Result                      |
| 结论           | Conclusion                       |

## 5. COA test items

| 中文                  | English                                              |
|-----------------------|------------------------------------------------------|
| 性状                  | Description                                          |
| 鉴别                  | Identification                                       |
| 检查                  | Tests                                                |
| pH 值                 | pH Value                                             |
| 吸光度                | Absorbance                                           |
| 有关物质              | Related Substances                                   |
| 杂质 A / B / C / D / E | Impurity A / B / C / D / E                          |
| 单个杂质峰            | Any single impurity                                  |
| 各杂质校正后峰面积的和 | Total of corrected peak areas of all impurities      |
| 不溶性微粒            | Particulate Matter (insoluble particles)             |
| Φ≥10μm 的微粒         | Particles ≥10 μm                                     |
| Φ≥25μm 的微粒         | Particles ≥25 μm                                     |
| 重金属                | Heavy Metals                                         |
| 渗透压摩尔浓度        | Osmolarity                                           |
| 渗透压摩尔浓度比      | Osmolarity ratio                                     |
| 细菌内毒素            | Bacterial Endotoxins                                 |
| 无菌                  | Sterility                                            |
| 应无菌生长            | Should be sterile (no growth)                        |
| 装量                  | Volume / Fill Volume                                 |
| 可见异物              | Visible Particulates                                 |
| 含量测定              | Assay                                                |
| 标示量                | Labeled amount / labelled amount                     |

### Phrase patterns inside the Acceptance Criteria column

- 应为 X~Y → Should be X–Y
- 应不得过/大于/小于 X → Should not be more than X / Should not be greater than X / Should not be less than X
- 应不得检出 → Should not be detected
- 应无 … → Should be free from … / Should show no …
- 应呈正反应 → Should give a positive reaction
- 供试品溶液主峰的保留时间应与对照品溶液主峰的保留时间一致 → The retention time of the principal peak in the test solution should correspond to that of the reference solution
- 按外标法以峰面积计算 → Calculated by the external standard method based on peak area
- 按校正后的峰面积计算（乘以校正因子 X） → Calculated on the corrected peak area (multiplying by the correction factor X)
- 不得大于对照液主峰面积的 X 倍 → Should not be greater than X times the area of the principal peak of the reference solution
- 每 1ml 中含 X 的量应小于 Y → The amount of X per 1 ml should be less than Y

## 6. Signature block

- QC 主任 → QC Director
- 复核员 → Reviewer
- 报告员 → Reporter

Chinese signature names are to be transliterated into Hanyu Pinyin (no tones, capitalize surname). Examples seen in this project:

| 中文 | Pinyin |
|------|--------|
| 吴利花 | Wu Lihua |
| 邓诗容 | Deng Shirong |
| 邓诗文 | Deng Shiwen |
| 丁才艳 | Ding Caiyan |

When a name is illegible, ask the user instead of guessing.

## 7. Drug substance / product names

| 中文                | English                                       | Notes |
|---------------------|-----------------------------------------------|-------|
| 乳酸环丙沙星        | Ciprofloxacin Lactate                         | INN use "Ciprofloxacin" alone is acceptable in running text; salt form is "Ciprofloxacin Lactate" |
| 乳酸环丙沙星氯化钠注射液 | Ciprofloxacin Lactate and Sodium Chloride Injection | USP title |
| 氯化钠              | Sodium Chloride                              | |
| 环丙沙星            | Ciprofloxacin                                | |
| 分子式 C₁₇H₁₈FN₃O₃ | Molecular formula: C₁₇H₁₈FN₃O₃               | preserve subscript digits |
| NaCl                | NaCl                                          | |

## 8. Regulatory authority references

- 国家食品药品监督管理局 (旧称，COA 仍在使用) → State Food and Drug Administration (SFDA), Approval No. YBH02572016
- 国家药品监督管理局 (现行) → National Medical Products Administration (NMPA)
- Keep the original 标准 YBH02572016 / YBH02572016 verbatim; do not invent an FDA/NMPA number.

## 9. Layout rules when generating a translated COA in DOCX

- Preserve the original table grid (same row count, same merged regions).
- Column 1 = Test Item, Column 2 = Acceptance Criteria, Column 3 = Test Result.
- Keep WM-QC-REC-015 form code unchanged.
- The red round company seal stays as-is — do not attempt to redraw or move it.
- Page margins, header logo placement, and footer signatures must match the source layout.

### Typography (applies to every translated document, not only COA)

- **Font family: Times New Roman — always.** No Calibri, no Arial, no mixed fonts.
- **Title font size: 四号 = 14 pt** (company name, "Certificate of Analysis", and any top-level document title).
- **Body / content font size: 小四 = 12 pt** (table cells, acceptance criteria, test results, conclusion, signature block, form code, paragraphs).
- Bold is allowed for table column headers and labels (Product Name, Batch No., Test Item, etc.) but font size stays at 小四 / 12 pt.
- `eastAsia` font hint in `w:rFonts` is still set to Times New Roman to keep Word from falling back to a Chinese font when the cell contains rare characters.
- Do not mix scripts in a single cell unless the source did so (e.g. `WM-QC-REC-015`, `YBH02572016`, `NaCl`, `C₁₇H₁₈FN₃O₃`).

## 10. Workflow

1. Confirm the target document path with the user.
2. For each page/COA: extract every field, verify batch-specific numbers (Batch No., Date of Manufacture, Expiry Date, Quantity, Report Date, pH, Particulate Matter counts, Assay %) against the image before writing.
3. Apply the mappings above; never use a synonym outside this skill.
4. Save to the requested path; show the user the absolute path and a 2-line summary of what was written.
5. If any field is ambiguous or unreadable, stop and ask — do not guess.