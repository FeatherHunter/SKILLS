# 飞书开放平台 · 服务端事件订阅 · 长连接(WebSocket)协议调研草稿

> 目的：为 DeepSeek Harness 动态插件实现飞书长连接事件订阅提供**可直接照着写代码**的精确协议细节。
> 抓取时间：本会话；所有细节均标注来源 URL 与置信度。未确认/未找到的条目明确写出，不编造。

---

## 0. 结论速览（先看这里）

| 主题 | 结论 |
|---|---|
| 帧编码 | WebSocket **binary message**，内容为 proto2 protobuf（`pbbp2.proto` 的 `Frame`） |
| Frame 关键字段 | `SeqID(1)/LogID(2)/service(3)/method(4)/headers(5)/payload_encoding(6)/payload_type(7)/payload(8)/LogIDNew(9)` |
| `method` 枚举 | **只有两个值**：`0=control`（ping/pong）、`1=data`（event/card） |
| ⚠️ `client_register / client_register_resp / data / data_resp / server_ping / client_pong / server_ack` | **未找到**。现行官方协议（Go v3 / Python v2 / Rust 两个独立实现 / 官方 .proto）均无这些枚举，帧类型靠 header `type` 区分。详见 §2 |
| 握手 | `POST {base}/callback/ws/endpoint`，**没有 Authorization 头**，凭证在 JSON body（`AppID`/`AppSecret`/`ClientAssertion`） |
| 连接后先发什么 | **不发注册帧**。直接起收包循环 + ping 循环（首个 ping 立即发送，之后每 `PingInterval` 秒一次） |
| 事件 payload | DATA 帧的 `payload`（字段8）就是 **UTF-8 JSON 字符串**（事件体），不是 protobuf 子消息 |
| 分片重组 | header `sum`/`seq`/`message_id`；`sum>1` 时按 `message_id` 缓存拼包，5 秒超时 |
| ACK | 收到 data 帧后，把**同一帧原样回传**（字段+headers 不变，追加 header `biz_rt=<处理毫秒数>`），`payload` 换成 `{"code":200,"headers":null,"data":null}`；3 秒内必须回 |
| 心跳 | **客户端**发 ping（control 帧，header `type=ping`）；服务端回 pong（header `type=pong`），pong 的 payload 可携带新的 `ClientConfig` JSON（服务端可中途改配置） |
| 订阅配置 | 仅**企业自建应用**；后台「事件与回调 > 事件配置」选「使用长连接接收事件」；**必须先有在线客户端才能保存成功**；需添加事件并**发布应用版本**生效；单应用最多 50 连接；集群模式（多客户端随机一个收） |
| 鉴权/加解密 | 长连接内置加密鉴权，**无需**验签/解密 |

---

## 1. Frame protobuf 结构（pbbp2.proto）

### 1.1 权威定义（proto2）

官方 Go SDK 生成的代码（`ws/pbbp2.pb.go`，`github.com/larksuite/oapi-sdk-go` v3_main 分支）与独立 Rust 实现 `foxzool/openlark` 的 `crates/lark-websocket-protobuf/protos/pbbp2.proto` 完全一致：

```proto
syntax = "proto2";
package pbbp2;

message Header {
  required string key   = 1;
  required string value = 2;
}

// message frame
message Frame {
  required uint64 SeqID = 1;   // 拆包序号/帧序号
  required uint64 LogID = 2;   // 日志 ID
  required int32  service = 3; // 服务 ID（来自连接 URL query 的 service_id，回显）
  required int32  method  = 4; // 0=control, 1=data
  repeated Header headers = 5; // 键值对头
  optional string payload_encoding = 6; // http like content-encoding, eg: gzip or none
  optional string payload_type     = 7; // http like content-type
  optional bytes  payload          = 8; // http like body（事件/响应 JSON 就在这里）
  optional string LogIDNew         = 9;
}
```

### 1.2 字段明细表

| 字段 | 编号 | 类型 | 必填 | 语义 |
|---|---|---|---|---|
| `SeqID` | 1 | uint64 (varint) | 是 | 拆包序号；未拆包时 Go/Python SDK 发 ping 置 0 |
| `LogID` | 2 | uint64 (varint) | 是 | 日志 ID，用于链路追踪 |
| `service` | 3 | int32 (varint) | 是 | 服务 ID = 连接 URL query 里的 `service_id`（每个连接固定，ping/ack 都要回填） |
| `method` | 4 | int32 (varint) | 是 | `0`=control（ping/pong），`1`=data（event/card） |
| `headers` | 5 | repeated Header (len-delim) | 否 | 键值对；每个 Header 内部是 `{1:key, 2:value}` 两个 required string |
| `payload_encoding` | 6 | string | 否 | 类似 HTTP content-encoding（如 `gzip` / `none`），当前 SDK 未使用 |
| `payload_type` | 7 | string | 否 | 类似 HTTP content-type，当前 SDK 未使用 |
| `payload` | 8 | bytes | 否 | 类似 HTTP body：下行=事件 JSON；上行=ACK 响应 JSON |
| `LogIDNew` | 9 | string | 否 | 新版日志 ID，当前 SDK 未使用 |

> 解码时对未知字段/未知 wire type 要宽容跳过（Go SDK 的 gogo protobuf 自动处理；手工实现见 §7 伪代码）。

### 1.3 headers 常用键（官方常量，Go `ws/const.go` + Python `lark_oapi/ws/const.py`）

| header key | 说明 |
|---|---|
| `type` | 消息类型：`event` / `card`（下行 data 帧）、`ping` / `pong`（control 帧） |
| `message_id` | 消息 ID；拆包后各包继承同一 message_id |
| `sum` | 拆包总数，未拆包为 `1` |
| `seq` | 包序号，未拆包为 `0`（注意：header 里的 `seq`，与 Frame 字段 1 `SeqID` 是两回事） |
| `trace_id` | 链路 ID |
| `instance_id` | 下行来源/上行去向的机器实例地址（加密串），透传即可 |
| `timestamp` | 消息时间戳，单位 ms |
| `biz_rt` | 业务处理时长 ms，**上行 ACK 时由客户端追加** |
| `Handshake-Status` / `Handshake-Msg` / `Handshake-Autherrcode` | WS 升级握手失败时的 HTTP 响应头（见 §3.4） |

---

## 2. 帧类型枚举：⚠️ 用户预期的 `client_register` 等**未找到**

用户任务书里的枚举名（`client_register / client_register_resp / data / data_resp / server_ping / client_pong / server_ack`）**在现行官方协议中不存在**。逐一核对了：

- 官方 Go SDK v3（`larksuite/oapi-sdk-go` `ws/` 包）：只有 `FrameTypeControl=0`、`FrameTypeData=1` 两个 method 值；`MessageType` 只有 `event/card/ping/pong`（`ws/const.go`）。
- 官方 Python SDK v2（`larksuite/oapi-sdk-python` `lark_oapi/ws/`）：同上（`enum.py` 中的 `FrameType`/`MessageType`）。
- 官方 .proto（`ws/pbbp2.pb.go` 生成来源）：Frame 无 payload_type 枚举，`payload_type` 只是 optional string。
- Rust 实现 `aegis-agent-core/src/feishu_ws.rs`：`METHOD_CONTROL=0`、`METHOD_DATA=1`，header `type=ping/event`。
- Rust 实现 `foxzool/openlark`（openlark-protocol crate）：同上。

**结论**：注册不是靠「client_register 帧」，而是靠握手阶段 `POST /callback/ws/endpoint` 用 `AppID/AppSecret` 换连接 URL（URL 本身绑定身份，注册是隐式的）。这些枚举名很可能来自旧版内部协议或其它聊天平台的 socket-mode 风格协议（如 Slack/Discord），**按现行协议实现时不要使用**。

- 若你的插件要兼容「可能存在的旧协议」，**标注为：未找到权威来源，不确定，勿采用**。

---

## 3. 握手流程（获取连接 URL → WS 升级）

### 3.1 POST /callback/ws/endpoint（官方 Go `ws/client.go::getConnURL` + Python `_get_conn_url` 一致）

```
POST https://open.feishu.cn/callback/ws/endpoint
Headers:
  Content-Type: application/json
  locale: zh
  User-Agent: <SDK UA>（可选）
  （⚠️ 无 Authorization 头！凭证在 body 里）

Body:
{
  "AppID": "cli_xxxxxxxx",
  "AppSecret": "xxxxxxxxxxxxxxxx",
  "ClientAssertion": ""
}
```

- `ClientAssertion` 是新鉴权方式（client assertion），可留空；若使用 client assertion，则 `AppSecret` 置空串 `""`。
- 请求体字段名是**大写驼峰**：`AppID` / `AppSecret` / `ClientAssertion`。

### 3.2 响应结构

```json
{
  "code": 0,
  "msg": "",
  "data": {
    "URL": "wss://xxx.feishu.cn/ws?device_id=dev-xxx&service_id=100",
    "ClientConfig": {
      "ReconnectCount": -1,
      "ReconnectInterval": 120,
      "ReconnectNonce": 30,
      "PingInterval": 90
    }
  }
}
```

- `data.URL` 为 WebSocket 连接地址，**query 里带 `device_id` 与 `service_id`**（`service_id` 之后要回填到每个 Frame 的 `service` 字段）。
- `data.ClientConfig`：`PingInterval`（心跳间隔秒，**未下发时 SDK 默认 120s**）、`ReconnectCount`（-1=无限重连）、`ReconnectInterval`（秒）、`ReconnectNonce`（首次重连随机抖动秒）。Rust aegis 实现与 Go 一致：`PingInterval` 缺失时默认 `120`。
- `code` 错误码（官方常量）：`0` OK / `1` SystemBusy / `403` Forbidden（封禁）/ `514` AuthFailed / `1000040343` InternalError / `1000040344` NoCredential（Python 独有）/ `1000040350` ExceedConnLimit（连接数超限）。

### 3.3 连接后

- 直接 `ws.Dial(URL)`（Go `ws.DefaultDialer.Dial`，Python `websockets.connect`），**无需额外认证头**。
- **不发任何注册帧**。启动 receive loop + ping loop；ping loop 首个循环**立即**发一个 ping，之后每 `PingInterval` 秒一次。
- 只收/只发 **WS binary message**（Go SDK 忽略非 binary；Python 直接 `recv()` bytes）。

### 3.4 升级握手失败时的错误头

WS 升级返回非 101 时，错误信息在 HTTP 响应头：

| 头 | 值 |
|---|---|
| `Handshake-Status` | `514`（AuthFailed）/ `403`（Forbidden）等 |
| `Handshake-Msg` | 错误描述 |
| `Handshake-Autherrcode` | `1000040350` 表示连接数超限（ExceedConnLimit） |

（Go `parseErr` + Python `_parse_ws_conn_exception` 一致；头名大小写不敏感。）

---

## 4. Ping / Pong 与 ACK 规则

### 4.1 客户端 Ping（主动心跳，官方 SDK 构造示例）

```text
method = 0 (control)
service = <连接 URL 里的 service_id>
headers = [ {key:"type", value:"ping"} ]
SeqID = 0, LogID = 0, payload 为空
```

（Go `NewPingFrame`、Python `_new_ping_frame`、Rust `build_ping_frame` 三者一致。）

### 4.2 服务端 Pong

- 服务端收到 ping 后回 control 帧，header `type=pong`。
- **pong 的 payload 若非空**，是 `ClientConfig` JSON（键同上 §3.2），客户端据此更新 `PingInterval`/重连参数——即服务端可以**在会话中途动态下发配置**，实现时务必解析。
- 客户端**收到 ping 不回**（Python `_handle_control_frame` 对 `type=ping` 直接 `return`；Go 同理只处理 pong）。

### 4.3 DATA 帧 ACK（关键）

收到 `method=1` 的 data 帧后（官方 Go `handleDataFrame` / Python `_handle_data_frame` / Rust `build_ack_frame` 一致）：

1. 读取 headers：`type`、`message_id`、`sum`、`seq`、`trace_id`。
2. 若 `sum > 1`：按 `message_id` 缓存分包（5 秒过期），等所有 `seq ∈ [0, sum)` 到齐后按序拼接 payload；未齐则**本次不回 ACK**（等后续包）。
3. `type=event` → 把拼接后的 payload（JSON 字节）交给事件 handler；`type=card` → 当前 SDK **直接 return，不回 ACK**（旧版卡片回传不支持长连接，见 §6）。
4. 计算处理耗时 `biz_rt`（毫秒）。
5. 构造响应 JSON：成功 `{"code":200,"headers":null,"data":null}`；handler 出错 `{"code":500,...}`。（Go `Response` 结构 `{code, headers, data}` 无 omitempty，序列化即为上面形态；Python 同键名。）
6. **把入站帧原样回传**：`SeqID/LogID/service/method` 不变，`headers` 复制入站全部 header **并追加** `{key:"biz_rt", value:"<毫秒数>"}`，`payload` 替换为响应 JSON。
7. 以 WS binary 发回。

> 回传必须是**同一个帧**（echo 语义）：`SeqID/LogID` 不重编号。未 ACK 的事件会被重推（见 §6）。

---

## 5. 事件 payload 如何解出（分片重组 + JSON）

- DATA 帧 `payload`（字段 8）= **UTF-8 JSON 字符串**（事件体），不是 protobuf 子消息；`payload_encoding`/`payload_type`（字段 6/7）当前官方 SDK 不解析。
- 事件类型在 header `type`（`event`）；具体事件类型在 JSON 里（v1.0 用 `event.type`，v2.0 用 `header.event_type`）。
- 分片规则（Go `combine` / Python `_combine` / Rust `Reassembler` 三方一致）：
  - `sum` = 总包数，`seq` = 当前包序号（0 起），`message_id` 相同即为同一事件的分片。
  - 未拆包：`sum=1, seq=0`。
  - 缓冲 key = `message_id`，TTL **5 秒**；全部到齐后按 `seq` 升序拼接字节。
- 事件 JSON 结构（官方「事件概述」文档）：
  - **v1.0**：顶层 `{ "ts", "uuid", "token", "type":"event_callback", "event":{...,"type":"p2p_chat_create"} }`。
  - **v2.0**：顶层 `{ "schema":"2.0", "header":{ "event_id","token","create_time","event_type","tenant_key","app_id" }, "event":{...} }`。

---

## 6. 订阅配置要求（官方文档）

来源：[事件概述](https://open.feishu.cn/document/ukTMukTMukTM/uUTNz4SN1MjL1UzM) + [使用长连接接收事件](https://open.feishu.cn/document/ukTMukTMukTM/uYDNxYjL2QTM24iN0EjN/event-subscription-configure-/request-url-configuration-case)

- **仅支持企业自建应用**；应用商店应用只能用 Webhook 模式。
- 开启方式：开发者后台 → 应用 → **事件与回调 > 事件配置** → 订阅方式选「**使用长连接接收事件**」→ 保存。**保存时必须已有长连接客户端在线**，否则报错（如「无在线长连接」）。
- 添加所需事件并**发布应用版本**使配置生效（「事件概述」：添加事件后需发布）。
- 每个应用最多 **50 个连接**（每初始化一个 client 算一个连接）。
- 消息推送为**集群模式**，非广播：同一应用多个客户端只有**随机一个**收到某条消息。
- 收到事件后需在 **3 秒内**处理完成且不抛异常（长连接场景下「处理成功」= 3 秒内处理且在 SDK handler 中不抛异常，即视为成功；TCP 建联超时 2 秒，整体 3 秒）；否则按 **15秒、5分钟、1小时、6小时** 间隔重推，**最多重试 4 次**。
- 全链路**至少一次投递**，可能重复；幂等判断：v1.0 用 `uuid`，v2.0 用 `header.event_id`。部分事件为**有序事件**（前一事件消费成功才推下一件）。
- 长连接内置通信加密与鉴权，**无需额外解密/验签**、无需防火墙白名单。
- 支持的事件：飞书绝大多数业务事件（消息、审批、云文档、通讯录等），完整列表见[事件列表](https://open.feishu.cn/document/ukTMukTMukTM/uYDNxYjL2QTM24iN0EjN/event-list)。⚠️ 旧版卡片回调（card.action.trigger）长连接不支持，需 Webhook（当前 Go/Python SDK 对 `type=card` 帧不回 ACK）。

---

## 7. 帧编解码伪代码（可直接照写）

### 7.1 varint / tag 基础

```text
put_varint(v):        // LEB128，低 7 位一组，高位续传
  while v >= 0x80: out << (v & 0x7f | 0x80); v >>= 7
  out << v

read_varint(data, pos):  // 返回 u64，越界返回 None
  result=0; shift=0
  loop: b=data[pos++]; result |= (b&0x7f)<<shift
        if b&0x80==0: return result
        shift+=7; if shift>=64: return None

tag(field, wire) = varint(field<<3 | wire)
  wire 0 = varint, wire 2 = length-delimited
```

### 7.2 Frame encode（proto2，required 字段 1–4 必写）

```text
encode_frame(f):
  put_varint( tag(1,0) ); put_varint(f.SeqID)     // required uint64
  put_varint( tag(2,0) ); put_varint(f.LogID)     // required uint64
  put_varint( tag(3,0) ); put_varint(f.service)   // required int32（负数按 u64 编码）
  put_varint( tag(4,0) ); put_varint(f.method)    // required int32
  for (k,v) in f.headers:
    put_varint( tag(5,2) ); put_len_delim( encode_header(k,v) )
  if f.payload非空:
    put_varint( tag(8,2) ); put_len_delim(f.payload)
  // 字段 6/7/9 通常不需要发

encode_header(k,v):
  put_varint(tag(1,2)); put_len_delim(k)
  put_varint(tag(2,2)); put_len_delim(v)
```

### 7.3 Frame decode（宽容跳过未知字段）

```text
decode_frame(bytes):
  f = empty; pos=0
  while pos < len:
    tag = read_varint; field = tag>>3; wire = tag&7
    if wire==0:  v = read_varint
                 field 1→f.SeqID, 2→f.LogID, 3→f.service, 4→f.method
    elif wire==2:
                 len = read_varint; bytes = data[pos..pos+len]; pos+=len
                 field 5→push decode_header(bytes) 到 f.headers
                 field 8→f.payload = bytes
                 field 6/7/9→忽略
    else: 跳过未知 wire（或报错）
  return f
```

### 7.4 关键帧构造

```text
# Ping（客户端心跳）
frame = { SeqID:0, LogID:0, service:<service_id>, method:0,
          headers:[{type:"ping"}], payload:空 }
send(binary_encode(frame))

# ACK（收到 data 帧后）
frame = 入站帧原样拷贝
frame.headers += {biz_rt: <处理毫秒数>}
frame.payload = '{"code":200,"headers":null,"data":null}'   # 出错则 code:500
send(binary_encode(frame))
```

### 7.5 分片重组

```text
cache: dict[message_id] = {parts: [None]*sum, inserted: now}

on_data_frame(frame):
  sum = header_int("sum"); seq = header_int("seq"); mid = header("message_id")
  if sum > 1:
    buf = cache.get(mid)
    if buf is None: buf = {parts:[None]*sum, inserted:now}; cache[mid]=buf
    if len(buf.parts)!=sum: 重置 buf.parts=[None]*sum
    buf.parts[seq] = frame.payload
    if 有任何 part 为空: return None        # 等后续包，本次不回 ACK
    payload = concat(buf.parts)            # 按 seq 升序
    del cache[mid]
  else:
    payload = frame.payload                # sum==1，直接用
  # 清理 5 秒前的缓存条目
```

---

## 8. 来源清单（每条标注 URL 与置信度）

| # | 内容 | 来源 | 置信度 |
|---|---|---|---|
| 1 | Frame/Header protobuf 定义、method 0/1、headers 键、ping/ack/分片逻辑、endpoint 握手 | 官方 Go SDK `larksuite/oapi-sdk-go`（v3_main）`ws/pbbp2.pb.go`、`ws/const.go`、`ws/model.go`、`ws/client.go` — [GitHub 目录](https://github.com/larksuite/oapi-sdk-go/tree/v3_main/ws)（raw: `https://raw.githubusercontent.com/larksuite/oapi-sdk-go/v3_main/ws/client.go` 等） | 高（官方实现，一手） |
| 2 | 同上协议的 Python 版交叉验证（含 `handshake-status` 头、`NO_CREDENTIAL=1000040344`） | 官方 Python SDK `larksuite/oapi-sdk-python`（v2_main）`lark_oapi/ws/client.py`、`const.py`、`model.py` — [GitHub](https://github.com/larksuite/oapi-sdk-python/tree/v2_main/lark_oapi/ws) | 高（官方实现，一手） |
| 3 | `.proto` 原文（含字段 6/7 注释） | `foxzool/openlark` `crates/lark-websocket-protobuf/protos/pbbp2.proto` — [GitHub](https://github.com/foxzool/openlark/blob/main/crates/lark-websocket-protobuf/protos/pbbp2.proto)；发布版 [docs.rs openlark-protocol](https://docs.rs/crate/openlark-protocol/latest) | 高（第三方独立实现，与官方逐字段一致） |
| 4 | 纯协议层 Rust 实现（Frame codec、endpoint 解析、分片重组、`{"code":200,"headers":null,"data":null}` ACK） | [docs.rs aegis-agent-core 源码页](https://docs.rs/crate/aegis-agent-core/latest/source/src/feishu_ws.rs)（本会话已抓取全文；模块页 [aegis_core/feishu_ws](https://docs.rs/aegis-agent-core/latest/aegis_core/feishu_ws/)） | 高（第三方独立实现，与官方一致） |
| 5 | 事件订阅整体概念、两种订阅方式、v1.0/v2.0 事件结构、重试间隔（15s/5min/1h/6h 最多 4 次）、至少一次投递、幂等键、发布应用使配置生效 | 官方文档《事件概述》— [open.feishu.cn](https://open.feishu.cn/document/ukTMukTMukTM/uUTNz4SN1MjL1UzM)（本会话以 `.md` 后缀抓取全文） | 高（官方文档，一手） |
| 6 | 长连接模式配置细节：仅自建应用、50 连接上限、集群模式、3 秒处理、后台选「使用长连接接收事件」且需客户端在线、各语言 SDK 示例 | 官方文档《使用长连接接收事件》— [open.feishu.cn](https://open.feishu.cn/document/ukTMukTMukTM/uYDNxYjL2QTM24iN0EjN/event-subscription-configure-/request-url-configuration-case)（本会话以 `.md` 后缀抓取全文） | 高（官方文档，一手） |
| 7 | 支持事件完整列表入口 | 官方《事件列表》— [open.feishu.cn](https://open.feishu.cn/document/ukTMukTMukTM/uYDNxYjL2QTM24iN0EjN/event-list)（未抓取全文，页面为交互式） | 中（链接来自官方文档内引用） |
| 8 | 入门向实战博文（佐证 50 连接上限、自建应用限定、先起客户端再保存配置、30s 心跳经验值） | [cnblogs《飞书机器人长连接（WebSocket）完整接入实战指南》](https://www.cnblogs.com/wyx-114514/p/20546882)（本会话已抓取；其中部分 API 示例与官方 SDK 不符，仅作佐证） | 低（第三方博文，勿照抄其代码） |
| 9 | ⚠️ `client_register/client_register_resp/data/data_resp/server_ping/client_pong/server_ack` 帧枚举 | **未找到**任何现行官方/可信来源；web 搜索与 4 个 SDK 实现均无此枚举 | 未找到（勿采用；现行协议用 `method` 0/1 + header `type`） |

---

## 9. 对实现者的额外提醒

1. **别被旧教程带偏**：网上不少教程让客户端发心跳「每 30 秒一次」，但官方 SDK 以服务端下发的 `PingInterval` 为准（默认 120s）；实现时应跟随服务端配置并响应 pong 里下发的 `ClientConfig`。
2. **WS 消息全是 binary**：忽略 text 帧（Go SDK 明确只处理 binary）。
3. **ACK 必须 echo 原帧**：SeqID/LogID/service/method 与入站一致，只改 payload、追加 `biz_rt` 头。
4. **断线重连**：官方 SDK 默认无限重连（`ReconnectCount=-1`），间隔 `ReconnectInterval`（默认 120s），首次带随机抖动（`ReconnectNonce`，默认 30s）；重连前需重新调 `POST /callback/ws/endpoint` 拿新 URL。
5. **幂等**：消息可能重复，用 `uuid`（v1.0）/`header.event_id`（v2.0）去重。
6. 本报告草稿阶段抓取的原始文件（Rust 源码、.proto、官方文档 markdown、SDK 源码）保存在仓库根目录 `*.rs` / `gosdk_*` / `pysdk_*` / `feishu_*.md` 等临时文件中，供后续核对；正式方案定稿后可清理。
