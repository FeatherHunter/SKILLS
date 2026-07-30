# 03 — archive superpowers:`docs/superpowers/` → `_archive/superpowers/`

**What to build:**
执行 D5 决策(已沉淀但未落地):用 `git mv` 把 `docs/superpowers/` 整体移到 `_archive/superpowers/`。完成后,任何人打开仓库都不会再误以为 `docs/superpowers/specs/` 是当前 spec。

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

### 验收标准

- [ ] 执行 `git mv docs/superpowers _archive/superpowers`(在智剪工坊目录下)
- [ ] 验证 `ls docs/superpowers` 输出 "目录不存在"(404)
- [ ] 验证 `ls _archive/superpowers` 显示原有内容(plans/ specs/ 等子目录)
- [ ] 验证 `git status` 显示 "renamed: docs/superpowers -> _archive/superpowers"(不是 delete + add)
- [ ] 验证 git history 连续:`git log --follow _archive/superpowers/specs/2026-07-25-video-time-segment-model.html | head -20` 显示历史 commit
- [ ] git commit,信息格式: `[智剪工坊] 03-archive-superpowers: D5 落地`
- [ ] 跑现有所有测试套件全过(无回归):
  - `references/tests/test_intent_v3_schema.py`
  - `lib/tests/test_intent_v3_validator.py`
  - `lib/tests/test_video_processing.py`
  - `scripts/_internal/tests/test_stage1_checklist.py`
  - `智剪工坊-意图编辑-tests/test_html_v3_structure.py`
  - `scripts/ai/cover_compose/tests/test_cover_compose.py`

### 实现细节(供 agent 参考)

**执行命令**(在 `D:\2Study\StudyNotes\SKILLS\智剪工坊\` 目录下):
```bash
git mv docs/superpowers _archive/superpowers
git status  # 应该显示 renamed: ... -> _archive/superpowers
git log --follow _archive/superpowers/specs/2026-07-25-video-time-segment-model.html | head -5
# 跑测试套件确认无回归
# 然后 commit
```

**README 占位**(可选):
如果 `_archive/` 目录已存在但没有 README,加 1 个 `_archive/README.md` 说明这是历史归档目录,**只读语义**。

### 已知事实(避免 agent 误判)

- **`docs/superpowers/` 历史内容完整保留** —— git mv 是 rename,不是删除
- **`.scratch/intent-v3-refactor/` 不动** —— 这是 active spec/issues,不是历史
- **`.scratch/v3-cleanup-tickets/` 不动** —— 这是本批 ticket 的活跃目录
- **`docs/adr/` 不动** —— 由 ticket 02 创建
- **`_archive/` 目录不存在**(2026-07-29 验证过),git mv 会自动创建

### 为什么这条 ticket 独立

- git mv 是原子操作,5 秒完成
- 不依赖其他 ticket 的产出
- 是 D5 决策的最后落地步骤(D5 已沉淀但忘了执行)

如果跳过本工单:**仓库仍有 `docs/superpowers/specs/` 误导性目录** —— 违反 D11("任何小 bug 必须修复")。

### 风险

- **零代码风险**:纯目录移动
- **git history 风险**:极低,git mv 是 rename,history 保留
- **回滚成本**:1 个 git revert 命令即可