Status: ready-for-agent

# 05 — ADR-0001 expand: render pipeline 加 rename step

**What to build:** `render_help_center.py` 渲染成功后,自动把最新 `卡路里_HELP_<TS>.html` 复制为 `卡路里.html`(根目录)。旧 `卡路里.html` 备份一次(可放 `.scratch/card-html-redesign/` 或 archive 路径)。

依据:ADR-0001 expand 阶段。

**Blocked by:** None — can start immediately

- [ ] `render_help_center.py` 在生成 `<TS>.html` 后追加 rename/copy 步骤(自动检测最新一份)
- [ ] 命令行加 `--no-mirror` flag 显式跳过(给调试用)
- [ ] rename 步骤写日志:打印 mirror 源路径与目标路径
- [ ] 旧 `卡路里.html`(101 KB SKILL.md 镜像)备份到 `.scratch/card-html-redesign/archive/卡路里_SKILL镜像_<date>.html` 后才覆盖
- [ ] `pytest tests/test_redesign.py` 加 test:运行 render 后 `<SKILL_DIR>/卡路里.html` 字节相同于最新 `<TS>.html`(允许压缩空白差)