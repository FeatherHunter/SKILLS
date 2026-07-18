---
name: gaode-map
description: |
  Use this skill when the user asks for 高德地图查询、POI 搜索、附近搜索、路径规划、地理编码、经纬度查地址、查距离、查天气。触发场景:用户说"搜美食/找酒店/天安门在哪/西直门周边/规划路线/北京一日游/查距离/查天气/经纬度/地址解析/坐标查地址"。
  通过高德开放平台 Web Service API(AMAP_WEBSERVICE_KEY)完成中国境内 POI 搜索 / 周边搜索 / 路径规划(步行·驾车·公交·骑行)/ 地理编码(地址→经纬度)/ 逆地理编码(经纬度→地址)/ 距离测量 / 天气查询。
  Do NOT use for 百度地图/腾讯地图/Google Maps;不用于需要海外服务或离线场景。
descriptions:
  zh-Hans: "高德地图本地 skill —— POI/路径/地理编码/天气查询,通过 Web Service API 直连。"
displayNames:
  zh-Hans: "高德地图"
---

# 高德地图

## Inputs to collect

调用前确认:

- **API Key**: 已通过 `setx AMAP_WEBSERVICE_KEY "..."` 持久化到 User 环境变量(注册表 `[Environment]::GetEnvironmentVariable("AMAP_WEBSERVICE_KEY", "User")` 可验证)。当前会话若未生效,用 `$env:AMAP_WEBSERVICE_KEY="..."` 临时注入。**子代理场景**(OpenClaw Sonnet 等沙箱)可能剥掉 env,**必须用 `--key=<key>` 命令行传参**,不要依赖 env。
- **操作类型**:POI 搜索 / 路径规划 / 地理编码 / 逆地理编码 / 距离测量 / 天气查询(每个对应一个 script)。
- **查询参数**:keywords / city / location / origin / destination / type 等。

未明确时,主动问用户。

## Procedure

1. **确认 Key 已设置**:`echo $env:AMAP_WEBSERVICE_KEY`(PowerShell)或 `echo $AMAP_WEBSERVICE_KEY`(bash)。空字符串 → 提示用户去 `https://lbs.amap.com/api/webservice/create-project-and-key` 申请 Key,平台勾选 **Web Service JS API**。
2. **选脚本**:按操作类型挑对应 `scripts/*.js`:
   - `poi-search.js` — 关键字搜索 POI
   - `around-search.js` — 中心点周边搜索
   - `route-planning.js` — 路径规划
   - `geocode.js` — 地理编码(地址→坐标)
   - `regeocode.js` — 逆地理编码(坐标→地址)
   - `distance.js` — 距离测量
   - `weather.js` — 天气查询
3. **跑命令**:每个脚本支持 `--help` 看参数自检。
4. **解析输出**:脚本统一输出 JSON 到 stdout;再由 AI 提炼成人话回复。
5. **失败处理**:见下文。

每个脚本封装路径、参数构造、错误码翻译,直接调高德 REST API,无中间层。

## Output contract

- **stdout**: 完整高德 API JSON 响应(原始,含 status/info/pois/paths 等)
- **stderr**: 错误信息(高德错误码 + 翻译后的原因)
- **exit code**: 0 = 成功(status:"1"),1 = 网络/解析错误,2 = 高德业务错误(status:"0")
- **AI 提炼**:把 JSON 翻译成中文要点列表(名称、地址、坐标、电话、营业时间等);不要把整段 JSON 甩给用户。

## Failure handling

| 现象 | 原因 | 处理 |
|---|---|---|
| `INVALID_USER_KEY` (10001) | Key 不存在或被删 | 提示重新申请 |
| `INVALID_USER_SIGN` / `USER_DAILY_QUERY_OVER_LIMIT` | 签名错或日配额耗尽 | 换 Key 或升级到企业版 |
| `SERVICE_NOT_AVAILABLE` (10002) | 该 Key 未开通对应平台 | 申请 Key 时勾选 **Web Service JS API** |
| `USER_IP_RECORDED_ERROR` | 服务器 IP 不在白名单 | 申请 Key 时 IP 留空或加白名单 |
| `CUQPS_HAS_EXCEEDED_THE_LIMIT` (10014) | QPS 超限 | 降低调用频率或申请扩容 |
| 网络超时 / `ENOTFOUND` | 网络问题 | 重试或检查代理 |
| 脚本执行报 `Key not set` | 环境变量未注入到子进程 | **PowerShell 子进程不继承父进程 `$env:` 临时变量**;setx 只对新 shell 生效。当前命令必须显式传 key,或在 `node` 前一行写 `$env:AMAP_WEBSERVICE_KEY="..."; node ...` 一起跑 |

## Examples

**Input**: "北京西直门周边 1km 内的咖啡店"

**Run**(两步走 —— 先 geocode 拿坐标,再 around-search):
```powershell
# 第 1 步:地址 → 坐标
node D:\2Study\StudyNotes\skills\gaode-map\scripts\geocode.js --address=西直门 --city=北京

# 第 2 步:坐标 → 周边 POI(把第 1 步返回的 location 字段填到这里)
node D:\2Study\StudyNotes\skills\gaode-map\scripts\around-search.js --location=<lng,lat> --keywords=咖啡 --radius=1000
```

如果用户**已经给了坐标**,跳过第 1 步直接跑第 2 步。

**AI 提炼**:把返回的 POI 列表按 distance 排序,挑前 5 条地址+名称+距离报给用户。

**Input**: "从天安门到首都机场怎么走"

**Run**:
```powershell
node D:\2Study\StudyNotes\skills\gaode-map\scripts\route-planning.js --origin=116.397,39.909 --destination=116.609,40.080 --mode=driving
```

**AI 提炼**:取出路径方案 distance/duration/cost/策略,生成"打车 32 公里约 50 分钟 / 打车费约 110 元"这类人话。

## Windows (win32) platform notes

- 所有 `setx AMAP_WEBSERVICE_KEY "..."` 永久生效;`$env:AMAP_WEBSERVICE_KEY="..."` 仅当前会话。
- 高德 API HTTPS 直连无需额外代理配置。
- `node scripts/*.js` 在 PowerShell 下路径用反斜杠或 `Join-Path`。
- 验证命令:`node D:\2Study\StudyNotes\skills\gaode-map\scripts\poi-search.js --keywords=肯德基 --city=北京`
- 输出统一用 UTF-8 中文,JSON 内含中文 Key/Value 不需要额外 `chcp 65001`(Node.js 默认 UTF-8)。