# AGENTS · MuseSparkInit

本技能封装 Muse Spark 1.2 在 DSH 的一键初始化，含地区封锁自检与 Clash 代理穿透。

## 文件清单

| 文件 | 角色 |
|---|---|
| `SKILL.md` | 主读本（触发词/前置自检/权威模板/代理分支/流程） |
| `AGENTS.md` | 本文件 |

## 与 configure-third-party-llm 的边界

- 本技能是其 **预设化封装**：`route id=opencode-go-muse` `api=openai-responses` `baseURL=https://opencode.ai/zen/go/v1` `contextWindow=1048576` `maxTokens=13272` 已固化，不再让 AI 猜
- 通用第三方 LLM 配置仍走 `configure-third-party-llm`，Muse Spark 专用走本技能

## 部署

- 源在 `D:\2Study\StudyNotes\SKILLS\MuseSparkInit\`
- DSH 通过 `mklink /J` 挂到 `C:\Users\辰辰洋洋\.dsh\skills\MuseSparkInit`
```powershell
cmd /c rmdir "C:\Users\辰辰洋洋\.dsh\skills\MuseSparkInit" 2>nul
cmd /c mklink /J "C:\Users\辰辰洋洋\.dsh\skills\MuseSparkInit" "D:\2Study\StudyNotes\SKILLS\MuseSparkInit"
```

## 改动前 3 问

1. 只改 `~/.dsh/settings.yaml` `opencode-go-muse` 与 `verge.yaml` TUN 开关，不动 `credentials.yaml` 裸值
2. 无数据迁移
3. 回滚：`settings.yaml.bak.<ts>` 覆盖 + `verge.yaml:enable_tun_mode:null`
