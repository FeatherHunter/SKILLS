# DSH 插件包的 package.json 清单（npm-publish 附录）

> 发布 **DSH 插件包**时 `package.json` 的最小骨架。
> 实测通过：`dsh-opencode-tui-theme@1.0.0`（完整源码见 `dsh-plugin/dsh-opencode-tui-theme/package/`）。

## 骨架

```json
{
  "name": "dsh-<插件名>",
  "version": "1.0.0",
  "description": "一句话说明（npm 主页展示）",
  "type": "module",
  "main": "lib/index.js",
  "exports": {
    ".": "./lib/index.js",
    "./client": "./lib/client.js",
    "./package.json": "./package.json"
  },
  "files": ["lib"],
  "dsh": {
    "client": {
      "platform": "web",
      "immediately": true,
      "inject": ["@deepseek-ai/dsh-client-ui-theme"]
    }
  },
  "license": "MIT"
}
```

## 关键字段说明

| 字段 | 作用 | 坑 |
|---|---|---|
| `exports["./client"]` | 浏览器 bundle 入口，DSH `dsh-client-modules` 靠它找到插件代码并伺服为 `/plugins/<id>/client.js` | 缺失 → 启动扫描报 `declares dsh.client but exports no "./client" bundle` |
| `dsh.client.platform` | 必须 `"web"`（浏览器端插件） | 其他值不生效 |
| `dsh.client.immediately` | `true` = 开机立即加载 | 主题类插件应设 true |
| `dsh.client.inject` | 依赖的**包名**列表，保证这些包先于本插件进 boot 图 | 主题插件依赖 `@deepseek-ai/dsh-client-ui-theme`（它 provide `theme` 服务） |
| `files` | 发布白名单 | 只含 `lib`，`client.js` 之外的杂项不进包 |

## 目录结构

```
<包>/
├── package.json
└── lib/
    ├── index.js     ← 宿主半（no-op 也行，保证 loader 条目可挂载）
    └── client.js    ← 浏览器半：window.__ModuleLoader__.load({id, factory}) 注册格式
```

## 浏览器半（client.js）格式要点

```js
window.__ModuleLoader__.load({
  id: '<包名>',
  factory: (require) => {
    var module = { exports: {} }
    var exports = module.exports
    Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' })
    // …插件代码…
    exports.inject = ['theme']           // 依赖的服务名（不是包名）
    exports.apply = function (ctx) { … }
    return module.exports
  },
})
```

- 导出形状与官方 client 包一致：named exports `{ inject, apply }`（参考 `dsh-client-ui-theme/lib/client.js` 结尾）
- 静态插件**没有** `styles.insert` builtin（那是动态 runner 的）——注入 CSS 用手动 `<style data-plugin="…">` 标签，卸载时 `ctx.effect` 清理
- `theme.overrideTokens(source, tokens)` 覆盖 13 个注册 token，返回 disposer

## 本机安装（发布前自测用）

```powershell
# 方式一：手动复制（本次实测）
Copy-Item <包目录>\* "C:\Users\<用户>\.dsh\profiles\node_modules\<包名>\" -Recurse -Force
# 方式二：npm 安装（发布后）
npm install <包名> --registry=https://registry.npmjs.org
```

DSH profile 的 `cordis.patch.yml` 注册行：

```yaml
- insert:
    - id: <插件行id>
      name: '<包名>'
```

配置热加载，刷新浏览器页面即生效，无需重启 DSH。
