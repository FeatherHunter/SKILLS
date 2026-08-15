# UNINSTALL · dsh-feishu-link 卸载指南

> 完整卸载：插件 + 所有状态 + 所有 side-effect

## 一次性卸载命令

```bash
# 1. 卸载包
npx --yes @deepseek-ai/dsh plugin --profile web remove dsh-feishu-link
```

`scripts/install-patch.cjs` 的对称操作 `uninstall-patch.cjs`（v0.2.0-pre 提供）会自动：
- 从 `~/.dsh/profiles/web/cordis.patch.yml` 移除 `dsh-feishu-link` block
- 不动其他插件的注册条目（幂等）

## 手动清理（如果自动卸载不彻底）

按下面 5 步，从上到下逐项做：

### 步骤 1 · 解除绑定

在 DSH 会话里调：
```
host.call('im.unbind', { agentId: '<每个 agent>' })  // 逐个 agent 调
host.call('im.health', {})                            // 确认 helper 已停
```

或用 IM 中心 overlay 里点每个「● 已绑」agent 行的「解绑」按钮。

### 步骤 2 · 删除 metadata

```bash
# 删除所有 Agent 的绑定元数据
rm -rf ~/.dsh/im-bindings/
# Windows (PowerShell)：
Remove-Item -Recurse -Force "$env:USERPROFILE\.dsh\im-bindings"
```

### 步骤 3 · 删除 credentials

DSH 进程内的 `credentials` 服务缓存了每个 agent 的 appId/appSecret。需要：

```
# 在 DSH 会话内调（如果你有 im.clearCredentials RPC；v0.2.0 加入）
host.call('im.clearCredentials', {})  // 清所有 ns='im-lark' 凭证

# 或者重启 DSH（凭证服务通常只在内存，重启即清）
```

### 步骤 4 · 停 helper 子进程

helper 子进程由 host 进程 spawn。如果 DSH 重启了，子进程会自然消失。否则：

```
# Windows Task Manager 杀掉名为 'helper.mjs' 或 dsh-feishu-link 的 Node 进程
```

或在 DSH 会话里最后一次 unbind 后，helper 应该已经停掉（unbind → stopBot → close WSClient）。

### 步骤 5 · 删除 patch 注册

```bash
# 手动从 cordis.patch.yml 删除 ds-feishu-link 段
# ~/.dsh/profiles/web/cordis.patch.yml
# 找到包含 'dsh-feishu-link' 的 - insert: 块，删除
```

或运行 uninstall-patch.cjs（v0.2.0-pre 提供）：
```bash
node scripts/uninstall-patch.cjs
```

### 步骤 6 · 删除 npm 缓存（可选）

```bash
rm -rf ~/.dsh/profiles/web/node_modules/dsh-feishu-link
npm cache clean --force  # 可选
```

## 完整清空 helper 凭据（v0.2.0+）

helper 子进程在内存里持有 appSecret，但**只在 broadcastList 喂入后**使用。如果你不希望 helper 持有：
- 解绑后 helper 自然不再使用
- DSH 重启 helper 子进程也会被父进程释放

## helper 子进程没正常退？

如果解绑后 helper 还在：
1. 看 DSH 帮助 → 列出 helper pid
2. `kill <pid>` 强制杀
3. 重新加载插件（重启 DSH 或 `cordis_run` 重启）

## 你需要做的最多 6 步

| # | 行动 | 时间 |
|---|---|---|
| 1 | `npx ... plugin remove` | < 5s |
| 2 | 解绑所有 agent | < 10s/agent |
| 3 | `rm -rf ~/.dsh/im-bindings/` | < 1s |
| 4 | 重启 DSH（清 credentials）| 30s |
| 5 | 删 patch 段 | < 5s |
| 6 | 删 npm 缓存（可选） | < 5s |

总计 **< 2 分钟** 完成完整卸载。

## 应急：DSH 起不来？

如果插件导致 DSH 启动失败：
1. 删除 `~/.dsh/profiles/web/cordis.patch.yml` 里 `dsh-feishu-link` 那段
2. 删除 `~/.dsh/profiles/web/node_modules/dsh-feishu-link`
3. 重启 DSH

## 保留 to upgrade

如果你**不卸载**，只是想升级版本：

```bash
# v0.1.0 → v0.2.0
npx --yes @deepseek-ai/dsh plugin --profile web update dsh-feishu-link
```

metadata / credentials / IM 中心列表**全部保留**（向后兼容）。
