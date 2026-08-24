# npm-publish 坑位表（通用）

> 每条含：现象 → 根因 → 解决。覆盖官方源发布链路上的高频失败，与包类型/框架无关。

## 坑 1：镜像源拦截登录/发布

**现象**：
```
npm login → Public registration is not allowed
```
且 `npm config get registry` 显示 `https://registry.npmmirror.com` 或其他镜像。

**根因**：
- 用户级 `~/.npmrc` 写了 `registry=https://registry.npmmirror.com`；
- 更隐蔽的是环境变量 `npm_config_registry`（优先级高于所有 `.npmrc`）被设为镜像；
- 镜像只做下载加速，**不支持登录/发布**。

**排查**（三步定位来源，选你当前 shell 的写法）：

```bash
npm config get registry          # 当前生效值
npm config list                  # 看 user / project / env 哪一层在覆盖
```

```bash
# bash / zsh
env | grep -i npm
echo $npm_config_registry
```

```powershell
# PowerShell
npm config list
Get-ChildItem Env: | Where-Object Name -match npm
[Environment]::GetEnvironmentVariable("npm_config_registry","User")
[Environment]::GetEnvironmentVariable("npm_config_registry","Machine")
```

**解决**：单条命令显式指定官方源（优先级最高，不动全局镜像加速）：

```bash
npm login --registry=https://registry.npmjs.org
npm publish --registry=https://registry.npmjs.org
npm view <包名> --registry=https://registry.npmjs.org
```

不要改全局 `.npmrc` 去掉镜像（会损失下载加速）；`--registry` 参数只影响单条命令。

## 坑 2：发布强制 2FA

**现象**：
```
npm error 403 Forbidden - PUT https://registry.npmjs.org/<包名>
Two-factor authentication ... is required to publish packages.
```

**根因**：npm 安全策略要求发布必须 2FA；账号未开 2FA 或未传 OTP。

**解决**：
1. 开 2FA：`npm profile enable-2fa auth-and-writes --registry=https://registry.npmjs.org`（按提示输密码 → 终端显示密钥/二维码 → 认证器 App 扫码 → 输 6 位码确认）
2. 发布时走网页审批流（§4）或带码：`npm publish --registry=https://registry.npmjs.org --otp=123456`

## 坑 3：bypass-2FA 令牌正被淘汰

**来源**：https://github.blog/changelog/ 搜索 `bypass 2FA`（npm 已公告逐步收紧）

- 2026 年起：bypass-2FA 令牌不能再做账户/包管理操作
- 后续：bypass-2FA 令牌不能再直接发布（改为暂存 + 人工 2FA 批准）

**结论**：个人发布一律走**交互式 2FA（OTP / 网页审批）**，不要新建 bypass-2FA 令牌当长期方案。

## 坑 4：令牌泄露

**现象**：发布令牌出现在聊天记录/日志/仓库文件/命令行历史。

**根因**：误以为“马上要用没关系”。令牌 = 密码，任何出现过的场合都视为已泄露。

**解决**：
1. 立即到 https://www.npmjs.com/settings/<用户>/tokens → **Revoke**
2. 之后发布改走 2FA（见坑 2），或重新生成令牌后**直接写入本机** `~/.npmrc` 的 `//registry.npmjs.org/:_authToken=...` 行（注意别提交 git），绝不经过聊天
3. 令牌只存在于单条命令或本地文件，不留存于仓库/日志

## 坑 5：包内容不干净

**现象**：`npm pack --dry-run` 发现 `.npmrc`、`node_modules`、测试、`.env` 被打进包。

**根因**：npm 默认打包规则较宽，跟随 `.gitignore` 但不排除所有敏感文件。

**解决**：`package.json` 的 `files` 白名单（如 `["dist"]`）；发布前必跑 `npm pack --dry-run` 核对 Tarball Contents。见 `package-checklist.md`。

## 坑 6：版本重复发布

**现象**：`npm publish` 报 `E403 cannot publish over previously published version` 或 `E409`。

**根因**：同名同版本已存在（含撤回过的版本，npm 保留历史不可覆盖）。

**解决**：升 `version` 再发；`npm view <包名> versions --registry=https://registry.npmjs.org` 查已发版本。

## 坑 7：72 小时撤回窗口

**现象**：发布超过 72h 想删包，`npm unpublish` 被拒。

**根因**：npm 策略：超 72h 只能 `npm deprecate` 标记废弃，不能删除。

**解决**：发布前想清楚；超期后：
```bash
npm deprecate <包名>@<版本> "reason" --registry=https://registry.npmjs.org
```

## 坑 8：非交互环境发布必 EOTP · 交互终端走网页审批流

**现象**：在无 TTY 环境（后台 job、输出重定向、CI 无人工、Agent 代跑）执行 `npm publish`，npm **不发任何授权 URL**，直接报：

```
npm error code EOTP
npm error This operation requires a one-time password from your authenticator.
```

而在**交互终端**手跑同一条 `npm publish`，npm 打印：

```
Authenticate your account at: https://www.npmjs.com/auth/cli/<uuid>
Press ENTER to open in the browser...
```

回车 → 浏览器完成登录 + 2FA 审批 → 回终端回车 → `+ <包名>@<版本>` 发布成功。

**根因**：npm 检测到非交互（stdin 非 TTY / stdout 被重定向）时跳过网页授权分支，直接走 OTP 通道；隔空传 6 位 TOTP 码会因 30 秒轮换而过期。

**解决**：
1. **把命令交给人在交互终端自己执行**（推荐，零时延）；
2. 未绑定认证器 App 时，浏览器 2FA 输入框可填一个未用过的恢复码；
3. 发布命令**不要重定向输出**（`> file` 会触发 EOTP）；
4. 验证查询时显式 `--registry=https://registry.npmjs.org --prefer-online`，避免镜像同步延迟误判。

**Agent 铁律**：不要在后台代跑 `npm publish` 并等待用户发 OTP；应让用户在可见终端执行，Agent 负责前后检查与验证。

## 环境速查

```bash
npm whoami --registry=https://registry.npmjs.org   # 登录身份
npm config get registry                              # 当前源
npm view <包名> --registry=https://registry.npmjs.org  # 包信息（404=可用）
npm pack --dry-run                                   # 发布内容预览
npm publish --registry=https://registry.npmjs.org --otp=123456
npm view <包名> version --registry=https://registry.npmjs.org --prefer-online  # 发布后验证
npm unpublish <包名>@<版本> --registry=https://registry.npmjs.org   # 72h 内撤回
```
