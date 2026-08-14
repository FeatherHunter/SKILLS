# npm-publish 坑位表（实测记录）

> 来自 2026-08-14 `dsh-opencode-tui-theme@1.0.0`（坑 1-7）与 `@1.1.0`（坑 8）实盘发布。每条含：现象 → 根因 → 解决。

## 坑 1：镜像源拦截登录/发布（CNPM 假象）

**现象**：
```
npm login → Public registration is not allowed
```
且 `npm config get registry` 显示 `https://registry.npmmirror.com`。

**根因**：
- 用户级 `~/.npmrc` 写了 `registry=https://registry.npmmirror.com`（淘宝镜像）；
- 更隐蔽的是**环境变量** `npm_config_registry=https://registry.npmmirror.com`（当前会话注入），
  其优先级高于 project `.npmrc` 和 user `.npmrc`；
- npmmirror 只做下载加速，**不支持登录/发布**——账号是 npmjs.org 的，请求却打到了镜像。

**排查**（三步定位来源）：
```powershell
npm config get registry                    # 当前生效值
npm config list                            # 看 "user" config / "project" config / "env" config 谁在覆盖
[Environment]::GetEnvironmentVariables('Machine').GetEnumerator() | Where-Object Key -match npm
[Environment]::GetEnvironmentVariables('User').GetEnumerator() | Where-Object Key -match npm
```

**解决**：命令行显式指定官方源（优先级最高，只影响单条命令，不动全局镜像下载加速）：
```powershell
npm login --registry=https://registry.npmjs.org
npm publish --registry=https://registry.npmjs.org
```
不要改全局/用户级 `.npmrc`（会破坏镜像下载加速）；project 级 `.npmrc` 可留作兜底但会被 env 覆盖。

## 坑 2：发布强制 2FA

**现象**：
```
npm error 403 Forbidden - PUT https://registry.npmjs.org/<包名>
Two-factor authentication or granular access token with bypass 2fa enabled is required to publish packages.
```

**根因**：npm 官方安全政策：发布必须 2FA。账号没开 2FA 或没传 OTP。

**解决**：
1. 开 2FA：`npm profile enable-2fa auth-and-writes --registry=https://registry.npmjs.org`
   （输密码 → 终端显示密钥/二维码 → 手机认证器 App 扫码或手输 → 回终端输 6 位码）
2. 发布带验证码：`npm publish --registry=https://registry.npmjs.org --otp=123456`

## 坑 3：2FA-bypass 令牌正在被 npm 淘汰（政策时间表）

**来源**：https://github.blog/changelog/2026-07-08-npm-install-time-security-and-gat-bypass2fa-deprecation/

| 时间 | 变更 | 影响 |
|---|---|---|
| 2026-08 初 | bypass-2FA 令牌**不能再做账户/包管理操作**（创建/删除令牌、改 2FA、管 maintainer 等） | 创建令牌本身都可能被拒 |
| 2027-01 左右 | bypass-2FA 令牌**不能再直接发布** | 只能"暂存发布 + 人工 2FA 批准" |

**结论**：个人发布者一律走**交互式 2FA（OTP）**；不要新建 bypass-2FA 令牌当长期方案。

## 坑 4：令牌泄露（本技能自己的教训）

**现象**：发布令牌被粘贴进聊天记录/日志/仓库文件。

**根因**：误以为"反正马上要用"。令牌 = 密码，任何出现过的场合都视为已泄露。

**解决**：
1. 立即到 https://www.npmjs.com/settings/<用户>/tokens → **Revoke**
2. 需要发布时用 2FA OTP（见坑 2），或重新生成令牌（新令牌**不再**发进聊天，直接写入本机 `.npmrc` 的 `//registry.npmjs.org/:_authToken=...` 行，注意别提交 git）
3. 发布命令的令牌参数只存在于单条命令，不留存文件

## 坑 5：包内容不干净

**现象**：`npm pack --dry-run` 发现 `.npmrc`、`node_modules`、测试文件被打进包。

**根因**：npm 默认打包规则宽（跟随 .gitignore 但不排除所有敏感文件）。

**解决**：`package.json` 的 `files` 白名单（如 `["lib"]`）；发布前必跑 `npm pack --dry-run` 核对 Tarball Contents。

## 坑 6：版本重复发布

**现象**：`npm publish` 报 `E403 cannot publish over previously published version` 或 E409。

**根因**：同名同版本已存在（含撤回过的版本，npm 保留历史）。

**解决**：升 `version` 再发；`npm view <包名> versions` 查已发版本。

## 坑 7：72 小时撤回窗口

**现象**：发布超过 72h 想删包，`npm unpublish` 被拒。

**根因**：npm 政策：超过 72h 只能 `npm deprecate`（标记废弃），不能删除。

**解决**：发布前想清楚；超期后 `npm deprecate <包名>@<版本> "reason"` 标记废弃。

## 坑 8：非交互环境发布必 EOTP · 交互终端走网页审批流（1.1.0 实盘）

**现象**：Agent/脚本代跑 `npm publish`（Start-Process 重定向、后台 job、无 TTY）时，
npm **不发任何授权 URL**，直接报：
```
npm error code EOTP
npm error This operation requires a one-time password from your authenticator.
```
而同一账号在**交互终端**手动跑 `npm publish`，npm 打印：
```
Authenticate your account at: https://www.npmjs.com/auth/cli/<uuid>
Press ENTER to open in the browser...
```
回车 → 浏览器完成登录 + 2FA 审批 → 回终端回车 → `+ <包名>@<版本>` 发布成功。

**根因**：npm CLI 检测到非交互（stdin 非 TTY / 输出被重定向）时跳过网页授权分支，直接走 OTP 通道；
隔空传 6 位 TOTP 码必被 30 秒轮换坑掉（本次实测连败 3 次 EOTP）。

**解决**：
1. **把命令交给用户在交互终端自己跑**（推荐，零时延）；
2. 账号没绑认证器 App 时，浏览器 2FA 输入框可填一个**没用过的恢复码**（npm_recovery_codes 文件）；
3. 网页审批完成后 npm 自动落 token，后续发布仍会要求 2FA 审批（每次都要走一遍）。

## 环境速查

```powershell
npm whoami                                   # 登录身份
npm config get registry                      # 当前源
npm view <包名>                              # 包信息（404=可用）
npm pack --dry-run                           # 发布内容预览
npm publish --registry=https://registry.npmjs.org --otp=123456
npm view <包名> version                      # 发布后验证
npm unpublish <包名>@<版本> --registry=https://registry.npmjs.org   # 72h 内撤回
```
