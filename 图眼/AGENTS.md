# 图眼 · AGENTS.md

本技能目录的 AI 协作入口。根级仓库约定见 `SKILLS/AGENTS.md`。

## 本技能范围

- `scripts/eye.py` 是唯一 CLI 入口(子命令:look / scan / ocr / ask / audit)
- `references/prompts.md` 是软规则(prompt 模板库 + 场景分级 + 心法)
- 无数据库、无持久状态;临时文件走系统 tempfile

## Agent 使用本技能的标准动作

1. 用户表达「看图/精扫/读图/问图/审图」意图 → 读本 `SKILL.md` 路由表
2. 根据场景分级选档:粗看 `look` / 精扫 `scan` / OCR `ocr` / 问答 `ask` / 审问 `audit`
3. 带 `--output json` 拿结构化结果;落盘文档用 `<media type="file">` 主动发用户
4. 问图/审图默认 `--brain mmx`(零配置);用户要接 deepseek 时提醒设 `DEEPSEEK_API_KEY`

## 开发与测试

- 测试:`cd 图眼 && python -m pytest tests/ -v`(15 项,不碰网络/DB)
- 切片逻辑在 `scripts/eye.py` 的 `slice_image`;测试在 `tests/test_slice.py`
- CLI 契约测试在 `tests/test_eye_cli.py`
- 真实调用验证(消耗 token)手动执行,不在 pytest 里

## 数据库隔离红线(根级继承)

本技能**不读写任何数据库**——无需 DB 路径隔离;但跑测试/自测时遵守根级 AGENTS.md 红线:
不触碰任何生产 DB 文件。图眼自身无 DB,天然隔离。

## Git 提交规范(根级继承)

- 全中文 commit:`[图眼] <主题> · <细节>`,含 `Tested-By:` 行末
- 提交用 `git commit --only <path>` 只提交图眼/ 下文件,不碰并行 agent 的暂存
- push 由用户自己负责(2026-08-11 用户声明)
