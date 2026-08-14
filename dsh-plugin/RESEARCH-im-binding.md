# DSH 椋炰功 IM 缁戝畾鎻掍欢 路 缁煎悎璋冪爺鎶ュ憡锛坴2锛?
> 璋冪爺浜猴細鐖朵細璇濓紙缁撳悎鏈湴 inspect 瀹炴祴锛? background subagent锛坈d9dd673锛屼簨瀹炵粏鑺傚畬鎴愶級
> 璋冪爺鏃ワ細2026-08-14
> v2 鏇存柊锛歴ubagent 瀹炶瘉棰犺浜嗘垜涔嬪墠鐨?4 涓垽鏂紝宸插交搴曟敼鍐欍€傝瑙?搂5銆?> 椤圭洰浣嶇疆锛歚D:\2Study\StudyNotes\SKILLS\dsh-plugin\`锛堝緟鏂板缓瀛愮洰褰?`dsh-feishu-link/`锛屽緟涓庣敤鎴峰榻愶級
> 鎶ュ憡璺緞锛歚dsh-plugin/RESEARCH-im-binding.md`锛堜綘鐪嬪埌鐨勫氨鏄繖浠斤級
> 閰嶅浜嬪疄妗ｆ锛坰ubagent 璇﹀敖鐗堬級锛歚dsh-plugin/RESEARCH-dsh-lark-bot.md`锛?58 琛岋級

---

## TL;DR锛?0 绉掕鐗?路 v2 鏇存鐗堬級

1. **鎶€鏈?*锛歁CODE 椋炰功缁戝畾 = 椋炰功 OAuth + WebSocket 闀胯繛鎺?+ DSH 宸ュ叿娉ㄥ唽锛屼笁娈电绾匡紱DSH 鐜版湁鑳藉姏锛坄credentials` 瀛?token銆乣webServer.registerUpgrade` 鎺?WebSocket銆乣harness.registerTool` 鏆撮湶缁欐ā鍨嬨€乣web` 鏈嶅姟鎷?OAuth锛?*鍏ㄩ儴灏辩华**锛?*闆舵柊鍩哄缓**銆?2. **瑕?1 涓彃浠讹紝涓嶈 2 涓?*锛欴SH 宸叉湁鍒涘缓 Agent 鐨勫簳灞?API锛岀己鐨勫彧鏄?UI銆侷M 缁戝畾 = Agent 鐨勬墿灞曞厓鏁版嵁锛屼笉璇ョ嫭绔嬫垚鎻掍欢銆?*鍗曟彃浠?* `dsh-feishu-link`锛堟殏鍚嶏級銆?3. **鈽呪槄鈽呪槄 subagent 棰犺鎬у彂鐜帮細寮€婧愬湀宸叉湁涓€涓珮搴﹁创鍚堢殑鍙傝€冨疄鐜?鈥?`limingboGitHub/dsh-feishu-connect`锛坣pm v1.2.4锛孧IT锛?*銆傚畠鍦?DSH 涓凡缁忓仛瀹屼簡銆岃缃〉 鈫?鑷姩鐢熶簩缁寸爜 鈫?椋炰功 App 鎵爜 鈫?鑷姩寤?PersonalAgent 搴旂敤 鈫?澶氭満鍣ㄤ汉 脳 澶?workspace 鈫?闀胯繛鎺ャ€嶅畬鏁存祦绋嬨€傛垜浠殑宸ヤ綔瀹屽叏鍙互**鍩轰簬杩欎釜 MIT 椤圭洰 fork 鎴栧弬鑰冭璁?*锛屼笉蹇呴噸鍙戞槑鍗忚灞傘€?4. **鎴戜箣鍓?4 澶勬帹鏂敊浜?*锛堝疄浜嬫眰鏄褰曞湪 搂5.1锛夛細
   - 閿欐妸"浜屾墜鍏抽敭鏉ユ簮 AdamPlatin123/research/dsh-feishu-bot.md"褰撴垚瀛樺湪鐨勯噸瑕佹枃浠?鈫?**璇ユ枃浠?404**
   - 閿欐妸 `dsh-feishu-connect` 褰撴垚 PlutoKeating 鐨勫濡瑰寘 鈫?**鐪熷疄浣滆€?lmber锛屼笌 PlutoKeating 鏃犲叧**
   - 閿欐妸 `@lc2panda/dsh-im-channels` 褰撴垚"channel 鎶借薄绫讳技鎴戜滑鐩爣" 鈫?**瀹冩槸琛ㄥ崟+閰嶅鐮侊紝涓嶆壂鐮?*
   - 閿欐妸 `dsh-lark-bot` 褰撴垚"涓€瀵逛竴 CLI 椋庢牸锛岃窡 MCODE 涓嶅悓鐗╃" 鈫?**瀹冪殑椋炰功鍗忚灞傝窡 MCODE 鍚屾瀯**锛圥ersonalAgent 璁惧娴?`oauth/v1/app/registration`锛?5. **鍏ㄦ柊娲炲療锛堟洿闇€鐢ㄦ埛纭锛?*锛氬叕寮€鑳芥煡鍒扮殑 MCODE 椋炰功鎺ュ叆锛圡CODE 鐨?OpenClaw 浣撶郴锛夎蛋鐨勬槸銆?*濉?AppID/Secret + pairing approve 閰嶅鐮?*銆嶁€斺€?*涓嶆槸** "鐐瑰浘鏍囨壂鐮?銆備絾浣犵粰鎴戠湅鐨?5 寮犲浘鎭板ソ灏辨槸"鐐瑰浘鏍囨壂鐮?锛屾墍浠ヤ綘 5 寮犲浘寰堝彲鑳?*涓嶆槸** MCODE 褰撳墠鐨勪富娴佹祦绋嬨€?*蹇呴』纭浣犺繖涓?UX 鏉ユ簮 鈫?瑙?搂6 寰呭洖绛旈棶棰?*銆?6. **鐪熸闅剧偣涓嶆槸鎶€鏈€佷笉鏄?UX**锛氭槸鎬庝箞 fork / 閫夊瀷銆丩icense 鍏煎锛圓GPL-3.0 浼犳煋 vs MIT 鍙嬪ソ锛夈€?
---

## 1. MCODE 5 寮犲浘 鈫?DSH 鐜版湁 Slot 钀界偣

| 鍥?| 鍏抽敭 UI | DSH slot 鍊欓€?| 鏄惁鍙 |
|---|---|---|---|
| 1 Agent 鍒楄〃 + 宸茬粦 Agent 鏈夝煋卞浘鏍囷紝鏈粦娌℃湁 | sidebar 琛岀骇闄勫姞鍏冪礌 | `sidebar.workspaces.directoryFlow`锛坅dditive hole锛?| 鈿狅笍 闇€ confirm |
| 2 鑱婂ぉ妗嗛《閮?杩炴帴 IM"鎸夐挳 | 鍗曚細璇濋《閮?| `conversation` 鏄?`single` + `shadows-shipped-ui` | 鉂?|
| 3 骞冲彴閫夐」寮圭獥锛堥涔?/ 寰俊锛?| 娴姩妯℃€?| `shell.overlay`锛坄list`锛宎dditive锛?| 鉁?|
| 4 鎵爜缁戝畾椋炰功鏈哄櫒浜?| 娴姩妯℃€?| `shell.overlay` | 鉁?|
| 5 缁戝畾鍚庡浘鏍囧彉鍖?| 鍚屾鏇存柊 sidebar 鍒楄〃 | 鍚屽浘 1 | 鈿狅笍 |

**缁撹**锛氬浘 3銆佸浘 4 鏄ǔ鐨勶紙`shell.overlay` 鏍囧噯鐢ㄦ硶锛夈€傚浘 1銆佸浘 5 鏆傛椂鍙兘鍙犲姞鍦?IM 涓績閲屽仛闀滃儚锛涘浘 2 鍦ㄥ綋鍓?slot 浣撶郴**娌℃湁鍚堥€傚嚭鍙?*锛岄渶瑕侀檷绾у埌浼氳瘽鍒囨崲鏃?IM 涓績鑱斿姩 + 椤堕儴鐘舵€佹潯鎻愮ず銆?
---

## 2. DSH 鐜版湁鑳藉姏鐩樼偣锛堝凡瀹炴祴锛?
### Host Services
- `agentLoop.create / createAgent` 鈥斺€?**搴曞眰 API 宸叉敮鎸佸垱寤?Agent**
- `agentPresets.copy / mount / recompose / resolve / list / composeFrom / composedPreset` 鈥斺€?瀹屾暣 Agent preset 浣撶郴
- `agents.list / get / currentInitiator` 鈥斺€?璺熻釜 live agents
- **`credentials` 鏈嶅姟** 鈥斺€?IM 鍑瘉瀛樻斁鏍稿績锛坮esolve/set/unset/describe锛?- `webServer.registerRoute / registerUpgrade` 鈥斺€?**鑷畾涔?HTTP + WebSocket**
- `subprocess` 鈥斺€?璺?lark CLI / 闀胯繛鎺ュ畧鎶よ繘绋?- `web.fetch / search` 鈥斺€?宸插唴寤?fetch锛孫Auth 璧板畠
- `harness.handle` / `harness.registerTool` 鈥斺€?Host RPC + 妯″瀷宸ュ叿
- `approval` 鈥斺€?Agent 宸ュ叿鍐欐搷浣滃墠鐨勭敤鎴锋巿鏉冿紙涓嶉渶瑕佸湪 IM 涓績鐢級
- `sessionPersistence / sessionQuery` 鈥斺€?浼氳瘽鍘嗗彶
- `timer` 鈥斺€?蹇冭烦 / 杞

### Client Slots
- `shell.overlay`锛坄list`锛夆€斺€?鉁?IM 涓績銆佹壂鐮?modal銆佸钩鍙伴€夋嫨
- `sidebar.footer.action`锛坄list`锛夆€斺€?鉁?渚ф爮鍏ュ彛
- `sidebar.settings` 鍐呯殑 `settings.section` / `settings.plugins.tab` / `settings.plugin.item` 鈥斺€?鉁?閰嶇疆椤?- `conversation.input.dock` 鈥斺€?鉁?杈撳叆妗嗛檮鍔犲尯
- `details`锛坄single`锛屽凡琚?waystation 鐢?`priority: -1` 鏇挎崲涓哄彸鏍忓仠闈狅級鈥斺€?鉁?鑱斿姩鍙敤
- `sidebar.workspaces` / `conversation` 鈥斺€?鈿?閮芥槸 `single`锛堟敞鍐屼細鏇挎崲鍘?UI锛夛紝涓嶅缓璁敤

### 宸插弬鑰冪殑鍏勫紵鎻掍欢
- **`dsh-waystation/`**锛坴25/v26锛?026-08-14 鏈€鏂帮級鈥斺€?**鍏ㄦ爤 IM 涓績鍚屽舰鎬佹彃浠剁殑鏈€浣冲弬鑰?*锛歴hell.overlay 涓夎鍥?+ sidebar.footer.action + conversation.input.dock 鐘舵€佹潯 + settings.plugins.tab 閰嶇疆椤?+ details 鍙虫爮鍋滈潬銆?*鐩存帴鎶勫畠鐨勭洰褰曢鏋?+ RPC 妯″紡**銆?- **`dsh-opencode-tui-theme/`** 鈥斺€?Client-only 涓婚鎻掍欢锛宻ettings.plugins.tab 鍗?tab 娉ㄥ唽鑼冧緥 + postinstall 鑷姩娉ㄥ唽 cordis.patch.yml

### 鎻掍欢鍙屽舰鎬?1. **鍔ㄦ€佺増**锛歚cordis_define` + `cordis_run`锛坔ost.js + client.js 涓や釜鏂囦欢锛岄浂瀹夎锛?2. **姝ｅ紡瀹夎鐗?*锛歯pm 鍖?`name=<name>`锛宍dsh.client: { platform: 'web' }`锛岃鍒?`~/.dsh/profiles/web/node_modules`锛屽啓 `~/.dsh/profiles/web/cordis.patch.yml`锛屽紑鏈鸿嚜鍚?
---

## 3. 鍏ㄥ娴佺▼鐨勬妧鏈疄鐜帮紙涓夋绠＄嚎锛?
### 3.1 鎺堟潈娈碉紙涓€娆℃€т氦浜掞紝鍥?4 鎵爜鎺堟潈鏃讹級
- Host 璧锋湰鍦颁复鏃?HTTP server锛坄webServer.registerRoute('/im/callback', ...)`锛夛紝鍖归厤椋炰功 OAuth redirect URL
- Host 鎷夐涔?OAuth URL锛堝惈 `client_id / redirect_uri / scope / state`锛夛紝`web.fetch` 鍗冲彲
- Client 鍦?`shell.overlay` 娓叉煋 QR Code锛堟寚鍚?OAuth URL 鎴?device flow 鐨?user_code URL锛?- 鐢ㄦ埛鎵嬫満鎵爜 鈫?椋炰功骞冲彴銆屽垱寤洪涔︽満鍣ㄤ汉搴旂敤銆嶆祦绋?鈫?鍥炶皟鍒版湰鍦?HTTP server 鈫?鍏戞崲 `user_access_token` + `refresh_token`
- **`credentials.set(ref, access_token)`** 鎸佷箙鍖?
### 3.2 闀胯繛鎺ユ锛堟寔涔咃級
- Host 椋炰功 larksuite OpenClaw SDK锛坄@larksuiteoapi/node-sdk`锛夊缓绔?WSS 闀胯繛鎺?- 涓ょ璺戞硶锛?  - **X**锛欴SH `webServer.registerUpgrade('/im/lark/:agentId', handler)` 璧?WSS endpoint
  - **Y**锛堟帹鑽愶級锛歴pawn 甯搁┗瀛愯繘绋嬭窇 lark 闀胯繛鎺ワ紝涓昏繘绋嬬粡 `webServer` 鎴?socket 涓庡瓙杩涚▼娑堟伅浜掗€?- 闀胯繛鎺ユ敹鍒版秷鎭?鈫?瑙ｆ瀽 sender / chat_id / message 鈫?璺敱鍒板搴?Agent

### 3.3 鍛戒护鍥炴祦娈碉紙姣忔 IM 娑堟伅锛?- 闀胯繛鎺ユ敹鍒版秷鎭?鈫?`harness.registerTool` 鏆撮湶 `im_relay`锛堟垨 `im_offer`锛夋妸娑堟伅鐏屽叆瀵瑰簲 Agent 瀵硅瘽
- 鎴栫洿鎺ヨ皟 `agents.currentInitiator()` / `sessionReferenceResolver.prepare(...)`

### 3.4 鎬昏鍥?```
[鍥?4 鎵爜] 鈫?[椋炰功 OAuth] 鈫?[token 杩?credentials]
                                       鈫?[鍥?3 閫夊钩鍙癩                         闀胯繛鎺ュ缓绔?鈫愨攢鈹€鈹€鈹€鈹€鈹?[鍥?1/5 鍥炬爣鐘舵€乚 鈫愨攢鈹€ 鐘舵€佽疆璇?鈹€鈹€鈹€鈫?   鈹?        鈹?                                       鈹?        鈹?[鐢ㄦ埛鎵嬫満鍙戞秷鎭痌 鈹€鈫?椋炰功 WSS 鈹€鈫?闀胯繛鎺ユ敹鍒?                                  鈹?                                  鈫?                        璺敱鍒?Agent N
                                  鈹?                                  鈫?                sessionReferenceResolver.prepare
                                  鈹?                                  鈫?                  Agent N 鏀跺埌 user turn銆?..銆?浠庢墜鏈烘潵鐨?
                                  鈹?                                  鈫?                Agent N 瀹屾垚鎬濊€?鈫?鍙嶅悜宸ュ叿璋冪敤鍙戠粰鎵嬫満
```

**鎵€鏈夌敤鍒扮殑 DSH 鑳藉姏閮界幇鎴?*锛?*鏃犻渶浠讳綍鏂板熀寤?*銆?
---

## 4. 鎻掍欢鍒嗘媶鏂规

**鍗曟彃浠?`dsh-feishu-link`**锛堟殏鍚嶏紝寰?搂5 澶氭柟瀵硅瘉鍚庡畾锛夛細
- Agent 鍒涘缓 + Agent 鍒楄〃 + IM 缁戝畾缁熶竴鍦ㄤ竴涓?IM 涓績閲?- 鍐呴儴妯″潡鍖栵細
  - `agents-manager` 鈥斺€?Agent CRUD UI + 鐘舵€佹満
  - `im-link` 鈥斺€?IM 骞冲彴閫夋嫨 + 鎵爜缁?+ token 绠＄悊 + 闀胯繛鎺?+ 娑堟伅璺敱
  - `im-center`锛堣鍥惧眰锛夆€斺€?shell.overlay + sidebar.footer.action + settings.plugins.tab
- 鏂囦欢娓呭崟锛堝榻?waystation 鑼冨紡锛夛細
  ```
  dsh-feishu-link/
  鈹溾攢鈹€ host.js                鈫?Agent CRUD + IM token + 闀胯繛鎺?+ RPC
  鈹溾攢鈹€ client.js              鈫?shell.overlay IM 涓績 + sidebar.footer 鍏ュ彛 + settings tab
  鈹溾攢鈹€ DESIGN.md              鈫?璁捐鏂囨。锛堜豢 dsh-waystation/DESIGN.md锛?  鈹溾攢鈹€ ACCEPTANCE.md          鈫?楠屾敹娓呭崟
  鈹斺攢鈹€ package/               鈫?npm 鍙戝竷鐗堬紙鍔ㄦ€佺増鈫掗潤鎬佺増鍚屾锛?  ```

**鏄惁闇€瑕佹敮鎸佸垱寤?Agent 鎻掍欢锛?* 鈫?瑕侊紙灏佽 UI锛夛紝浣嗗簳灞?API 宸插瓨鍦紝绾?UI 宸ヤ綔銆?**鏄惁闇€瑕佸崟鐙?IM 缁戝畾鎻掍欢锛?* 鈫?涓嶉渶瑕侊紝鍚堝苟銆?**鏄惁鍙锛?* 鈫?鉁?DSH 鐜版湁鑳藉姏 100% 瑕嗙洊
**鎶€鏈鐐?*锛?- 鉁?鍏ㄩ儴鎶€鏈爤鐜版垚
- 鈿?UX 椋庨櫓锛氬浘 1/2/5 鍦?DSH 褰撳墠 slot 浣撶郴涓嬪仛涓嶅埌 1:1
- 鈿?椋炰功搴旂敤瀹℃壒锛氱敤鎴烽娆＄敤瑕佸幓椋炰功寮€鍙戣€呭悗鍙板缓 App锛坰ettings 寮圭獥鎻愮ず锛?- 鈿?闀胯繛鎺ュ穿婧冩仮澶嶏細鑷姩閲嶈繛 + 鐘舵€佷笂鎶ュ埌 IM 涓績
- 鈿?澶?Agent 璺敱锛氱兢鑱?@ 涓嶅悓鍚嶅瓧鎬庝箞璺敱锛岃鍦?IM 涓績鍋氭槧灏勯厤缃?
---

## 5. 鈽?璋冪爺鐪熺浉锛坰ubagent 瀹炶瘉鏀瑰啓锛?
### 5.1 鎴戜箣鍓?4 澶勬牳蹇冭鍒?
#### 璇垽 1锛氫互涓?`AdamPlatin123/awesome-dsh-plugins/research/dsh-feishu-bot.md` 瀛樺湪
- **鐪熺浉**锛氳鏂囦欢 404銆俙awesome-dsh-plugins/main` 鐩綍鏍戞牴鏈棤 `research/`銆佹棤 `dsh-feishu-bot.md`锛岄€掑綊鎼?feishu/lark/research 闆跺懡涓?- **鏁欒**锛歸eb_search 鍛戒腑涓?= 鏂囦欢瀛樺湪锛涗笅娆¤ `curl -I` 楠岃瘉 raw 鏂囦欢

#### 璇垽 2锛氫互涓?`dsh-feishu-connect` 鏄?PlutoKeating 鐨勫濡瑰寘
- **鐪熺浉**锛氱湡瀹?`dsh-feishu-connect`锛坣pm 1.2.4锛変綔鑰?`lmber`锛屼粨搴?`https://github.com/limingboGitHub/dsh-feishu-connect`锛?*涓?PlutoKeating 鏃犲叧**
- **鏁欒**锛氫笉鑳戒粠 npm 鍖呭悕鍚屽墠缂€鎺ㄦ柇鍚屼綔鑰?
#### 璇垽 3锛氫互涓?`@lc2panda/dsh-im-channels` 鏄?channel 鎶借薄鏈€璐磋繎鎴戜滑鐩爣"
- **鐪熺浉**锛氬畠鐢ㄣ€岃〃鍗?CLI 濉?App ID/Secret + `tenant_access_token` 鏍￠獙 + 閰嶅鐮侊紙pairing code锛夈€嶏紝**涓嶆槸鎵爜寤哄簲鐢?*锛汫itHub main 鏄┖浠撳簱锛屽疄浣撳湪 npm
- **鏁欒**锛歱lugin 鍚嶅瓧甯?`im-channels` 涓嶇瓑浜庤蛋"鎵爜 IM 棰戦亾"璺嚎锛涘姟蹇呰鍏?host 瀹炵幇

#### 璇垽 4锛氫互涓?`dsh-lark-bot` 鏄?涓€瀵逛竴 CLI 椋庢牸锛岃窡 MCODE 涓嶅悓鐗╃"
- **鐪熺浉**锛?*dsh-lark-bot 鐨勯涔﹀崗璁眰璺?MCODE 鍚屾瀯**鈥斺€旂敤 `@larksuite/channel` 鐨?`registerApp` 灏佽椋炰功瀹樻柟 `oauth/v1/app/registration` 璁惧娴侊紙`archetype: 'PersonalAgent'`锛夛紝`begin`鈫掕繑鍥?`device_code`+`verification_uri_complete`锛圦R 閾炬帴锛夛紝`poll`鈫掕繑鍥?`client_id`/`client_secret`锛堟湭鎵繑鍥?`authorization_pending`锛夈€傚畠缂虹殑鍙槸銆孉gent 鍥炬爣+鑱婂ぉ妗嗚繛鎺ユ寜閽?骞冲彴閫夋嫨椤点€嶈繖浜?*Web 鍐呭祵 GUI 澶栧３**锛屼笉鏄粦瀹氬崗璁?- **鏁欒**锛氬彧璇?README + 鍖呭悕灏卞垎绫?鐗╃"鏄嵄闄╃殑锛涜璇?`src/onboard/registration.ts` 杩欑鏍稿績瀹炵幇鎵嶈兘纭

### 5.2 涓変釜寮€婧愰」鐩殑绮剧粏瀹氫綅锛坰ubagent 浜嬪疄鐗堬級

| 缁村害 | dsh-lark-bot锛圥lutoKeating锛?| dsh-feishu-connect锛坙imingboGitHub锛?| @lc2panda/dsh-im-channels | MCODE锛堝叕寮€鍙煡锛?|
|---|---|---|---|---|
| License | **AGPL-3.0** | **MIT** | MIT | 鈥?|
| 缁戝畾鏂瑰紡 | PersonalAgent 璁惧娴佹壂鐮侊紙缁堢 qrcode-terminal锛?| PersonalAgent 璁惧娴佹壂鐮侊紙**璁剧疆椤靛鎴风鐢熸垚浜岀淮鐮?*锛?| 琛ㄥ崟濉?AppID/Secret + 閰嶅鐮?| OpenClaw锛氳〃鍗?AppID/Secret + pairing approve |
| 缁戝畾 API | `oauth/v1/app/registration` init鈫抌egin鈫抪oll | `accounts.feishu.cn/oauth/v1/app/registration`锛堝悓鍗忚锛?| `auth/v3/tenant_access_token/internal` | 缁忛涔﹀畼鏂规彃浠?|
| 闀胯繛鎺?| WebSocket | WebSocket锛坔elper.cjs锛?| WebSocket锛園larksuiteoapi锛?| WebSocket |
| UI 澶栧３ | **缁堢 CLI** | **Cordis bundle Web 绔紙璁剧疆椤?`/feishu/admin/*`锛?* | **Cordis bundle Web 绔?+ 琛ㄥ崟** | 锛堟帹鏂級**浜у搧鍐呭祵** |
| 澶氭満鍣ㄤ汉 | 鍗?bot 鍗?profile | **澶?bot 姣?bot 缁?workspace** | 寰俊+椋炰功缁熶竴棰戦亾 | 鈥?|
| **璺?MCODE "鐐瑰浘鏍囨壂鐮?** | 鍗忚鍚屾瀯锛屽澹虫槸 CLI | **鏈€鎺ヨ繎**锛堣缃〉鎵爜鑷姩寤?PersonalAgent + 鑷姩 ownerOpenId 鍗曡亰锛?| 宸窛鏈€澶э紙鏃犳壂鐮佸缓搴旂敤锛?| 鈥?|

### 5.3 鍏抽敭娲炲療

- **dsh-feishu-connect = 鐜扮姸涓嬫垜浠渶楂?ROI 鐨勫弬鑰?*锛歁IT 鍙嬪ソ + Cordis bundle 宸叉垚鍨?+ PersonalAgent 璁惧娴?+ 璁剧疆椤靛氨鏄?鍥?3+4"鐨?Web 鐗堬紙铏界劧**涓嶆槸鐐瑰浘鏍囪Е鍙?*锛岃€屾槸璁剧疆椤佃Е鍙戯級
- **dsh-lark-bot = 鍗忚澶囬€?*锛氬崗璁浣?AGPL-3.0 浼犳煋鎬?license + CLI 澶栧３锛岄渶閲嶅仛 UI锛涘彲浣滀负**鍗忚瀹炵幇鍙傝€?*鑰岄潪渚濊禆
- **@lc2panda = 鍙嶅悜鍙傝€?*锛氬畠鐨勫疄鐜板彲鑳?*鍙嶈€屾洿鎺ヨ繎 MCODE 鍏紑鍋氭硶**锛圓ppID/Secret 鍑嵁娉曡€岄潪鎵爜锛夆€斺€?鍗?*鐢ㄦ埛 5 寮犲浘 鈮?MCODE 鍏紑鏍囧噯**锛堣 搂6锛?
### 5.4 鎴戜滑鑳藉惁 fork / 渚濊禆锛?- 鉁?**`limingboGitHub/dsh-feishu-connect`锛圡IT锛?*锛氬彲鐩存帴 fork / `npm install` / 寮曠敤鈥斺€旀渶寮哄弬鑰?- 鈿?**`PlutoKeating/dsh-lark-bot`锛圓GPL-3.0锛?*锛氬彲璇绘簮鐮佸鍗忚锛屼絾**涓嶈兘鐩存帴 npm install 鍚庣敤浜庡澶栧垎鍙?*锛堜紶鏌擄級锛涜嫢绾鏈?fork 娌￠棶棰橈紝浣嗕綘杩欎釜椤圭洰鍚?`dsh-feishu-link` 鏄剧劧鏄瀵瑰寮€婧愮殑
- 鉂?**`@lc2panda/dsh-im-channels`锛圡IT 浣嗚蛋涓嶅悓璺嚎锛?*锛氫笉浣滀负杩欎釜椤圭洰鐨勪緷璧栵紱瀹冮€傚悎"鎴戝凡缁忔湁 AppID/Secret 鍑嵁"鐨勫満鏅紝涓庝綘 5 寮犲浘鎵爜缁戣矾绾夸笉绗?
**缁撹锛氭垜浠簲浼樺厛閲囩敤 `limingboGitHub/dsh-feishu-connect` 鐨勮璁?*锛堝悓鍗忚 + MIT + 宸茬粡鍋氫簡 Cordis UI锛変綔涓哄熀纭€ + 鎶?DSH 杩欎竴渚х殑 IM 涓績銆丄gent 鍒楄〃銆丼idebar 鍥炬爣琛ュ厖濂姐€?
---

## 6. 鍏抽敭鏂版礊瀵燂細浣?5 寮犲浘 鈮?MCODE 鍏紑鐨勫畼鏂规祦绋?
**subagent 鍦?搂4.2 瀹炶瘉**锛?
> 鍏紑鑳芥煡鍒?MCODE/MaxClaw锛圤penClaw 鍙樹綋锛夌殑椋炰功鎺ュ叆鏄?OpenClaw 浣撶郴 + 瀹樻柟椋炰功鎻掍欢锛屾牳蹇冩祦绋嬫槸锛?> 1. `openclaw plugins enable minimax-portal-auth` + `openclaw onboard --auth-choice minimax-portal`锛圤Auth 鎺堟潈锛?> 2. **杈撳叆椋炰功骞冲彴鑾峰彇鐨?App ID / App Secret**锛?*涓嶆槸鎵爜**锛?> 3. `openclaw pairing approve feishu [閰嶅鐮乚` 閰嶅鏀捐
>
> 褰撳墠 web_search **鏈繑鍥?*浠讳綍"MCODE 鐐瑰浘鏍囨壂鐮?鐨勫畼鏂逛竴鎵嬫枃妗?
鈫?浣犵湅鐨?5 寮犲浘鍙兘鏄細
- (a) **MCODE 鐨勫疄楠屾€у姛鑳?*锛堟柊鐗?/ 鍐呴儴棰勮锛夆€斺€?杩樻湭鏉ュ緱鍙婁笂绾垮叕寮€鏂囨。
- (b) **鍙︿竴涓骇鍝佹埅鍥?*锛堜笉鏄?MCODE锛屽彲鑳芥槸 MiniMax 鍒殑浜у搧鎴栬€呯珵鍝侊級
- (c) **浣犳兂璞?璁捐鐨?*鐩爣 UX
- (d) **MCODE 鍦ㄤ腑鍥藉競鍦虹壒渚涚増**锛堝叕寮€鏂囨。涓绘帹 OpenClaw 鑼冨紡锛屼絾涓浗鐗堢敤鎵爜璁惧娴侊級

**杩欎欢浜嬪繀椤荤‘璁?*鈥斺€斿喅瀹氭垜浠殑鍗忚灞傝蛋"鎵爜 + PersonalAgent"锛堜綘宸茬粡鐪嬭繃鐨勫紑婧愬疄鐜帮級杩樻槸"AppID/Secret + 閰嶅鐮?锛圡CODE 鍏紑鍋氭硶锛夈€?
---

## 7. 閲嶆柊鍥炵瓟浣犵殑"鍏ㄥ姛鑳芥墦閫?

### 7.1 鎷嗗垎涓夊眰璇勪及锛堝熀浜?v2锛?
| 灞傜骇 | 鍚箟 | 璺嚎 A + 鍙傝€?limingboGitHub 瀹為檯鑳藉仛鍒?|
|---|---|---|
| **L1 路 椋炰功缁戝畾** | 5 寮犲浘娴佺▼ | 鉁?**100%**锛坙imingboGitHub 宸插疄鐜板畬鏁存祦绋?+ MIT 鍙嬪ソ锛?|
| **L2 路 涓€鐩村疄鏃舵矡閫?* | 鍙屽悜娑堟伅銆佹柇绾块噸杩炪€乼oken 闈欓粯鎹㈠彂 | 鉁?**~95%**锛堟妧鏈畬鏁达紝鍏抽敭鍦ㄨˉ寮虹ǔ瀹氭€?+ Electron 杩涚▼閲嶅惎鍏滃簳锛?|
| **L3 路 MCODE 鍏ㄥ** | 鍥?1/2/5 + 澶氬钩鍙?+ 瀵屾枃鏈崱鐗?+ Agent 浜掑彂 + 涓诲姩鎺ㄩ€?| 鈿?**~80%**锛圲I 鍙楅檺浜?DSH slot 浣撶郴锛涗絾缁戙€佸疄鏃躲€佸瘜鏂囨湰閮借兘鍒颁綅锛?|

### 7.2 瀹為檯宸ヤ綔閲忥紙淇璇勪及锛?
鎸?fork + 浜屽紑 limingboGitHub/dsh-feishu-connect"璺嚎锛?
| 闃舵 | 鑼冨洿 | 浼拌浠ｇ爜 |
|---|---|---|
| **P0 路 MVP 楠岃瘉** | 鍗曢涔?+ 鍗?Agent + 鎵爜 + 闀胯繛鎺?+ 鍙屽悜鏀跺彂 + 鏈€绠€ IM 涓績锛堣缃〉鑱氬悎锛?| 50 琛?host锛堟敞鍏ュ苟绮剧畝 dsh-feishu-connect锛? 400 琛?client |
| **P1 路 澶?Agent 鍖?* | 鎶?limingbo 鐨?澶氭満鍣ㄤ汉"閲嶅仛鎴?澶?DSH Agent"锛屽姞 Agent 鍒楄〃瑙嗗浘銆佸姞璺敱琛ㄣ€佸姞鐘舵€佸績璺?| +400 琛?|
| **P2 路 澶氬钩鍙伴鏋?* | 寰俊 / 閽夐拤 浣滀负鍙彃鎷?channel adapter | +500 琛?|
| **P3 路 浣撻獙琛ュ叏** | 鐘舵€佹潯鑱斿姩 / 浼氳瘽鍒囨崲鏃惰仈鍔?/ 閰嶇疆椤垫ā鏉跨紪杈?| +300 琛?|
| **P4 路 鍐呭祵 GUI** | 绛?DSH 绔紑鍙ｈˉ sidebar.workspaces 琛岀骇鍥炬爣銆乧onversation.toolbar 鎸夐挳 | 鐪?DSH 鍐冲畾 |

**鎬昏 ~1500 琛屼唬鐮?* 鈥斺€?鈽?v3 淇锛氬疄闄?**~1900 琛?*锛堣瑙?搂10 鍋ュ悍妫€鏌ラ拤姝荤粨璁衡€斺€擿limingboGitHub/dsh-feishu-connect` 涓嶈兘鐩存帴 npm install 鐢紝鍗忚灞傞渶绾嚜鐮旓紱澶氬嚭鏉ョ殑 400 琛屽湪鑷啓 fetch 4 鍑芥暟 + WSS 瀛愯繘绋嬬簿绠€鑷啓锛?
### 7.3 鍏抽敭椋庨櫓鐐癸紙v3 淇鐗堬級

| 椋庨櫓 | 绛夌骇 | 缂撹В |
|---|---|---|
| ~~浣?5 寮犲浘鐨?UX 鏄笉鏄叕寮€鏂囨。閲岀殑鐪熷疄 MCODE锛焴~ | 鉁?宸茶В鍐?| 鐢ㄦ埛鎺堟潈銆屾寜 5 寮犲浘涓虹洰鏍?UX 鑷爺銆嶁€斺€?璧版壂鐮佺粦璺嚎 |
| ~~`limingboGitHub/dsh-feishu-connect` 瀹為檯缁存姢鐘舵€亊~ | 鉁?宸茶В鍐?| sub-agent 鍋ュ悍妫€鏌ュ畬鎴愶紙瑙?搂10锛?|
| 闀胯繛鎺ュ湪 Electron 妗岄潰绔殑鐢熷懡鍛ㄦ湡锛圖SH 閲嶅惎=闀胯繛鎺ヤ涪锛?| 馃煛 涓?| UI 蹇呴』鏄庣ず + P1 webhook event 妯″紡闄嶇骇 |
| 澶?Agent 璺敱琛ㄨ璁★紙@璋佺粰璋侊級 | 馃煛 涓?| P1 鑼冨洿锛汸0 鍙仛鍗?Agent 鍗曢涔?|
| **渚濊禆绋冲畾鎬?*锛坣pm + 鍗忚鑷啓锛?| 馃煝 浣?| 鍗忚灞傚畬鍏ㄨ嚜鐮?+ 浠呬緷璧?`@larksuiteoapi/node-sdk`锛坣pm 鍏紑涓荤嚎锛?+ `qrcode` |
| AGPL-3.0 浼犳煋闄烽槺 | 馃煝 浣?| 涓ュ畧鍙敤 MIT / 鍏紑 npm 椤圭洰鍋氫緷璧栵紱涓嶅鐢?PlutoKeating/dsh-lark-bot 鐨勪唬鐮?|
| **DSH `useSession` 鍒?agentId 鏄犲皠锛堟棤鐜版垚 metadata 瀛楁锛?* | 馃敶 楂?| 蹇呴』 P0 鏃╂湡楠岃瘉锛涘閫夛細鎷?SessionHeader + agentPresets.resolve 鍙嶆帹 |

---

## 8. 寰呬綘鍥炵瓟锛?*5 鏉￠兘宸茬敱浣犳巿鏉冭В鍐?*锛?
### 8.1 馃敶 蹇呯瓟 路 鍐冲畾鍗忚灞傝蛋娉?**Q-A**锛氫綘閭?5 寮犲浘绌剁珶鏄摢涓骇鍝佺殑鎴浘锛熸槸涓嶆槸 MCODE 褰撳墠**宸插叕寮€**鐨勫畼鏂规祦绋嬶紵杩樻槸鏂扮増棰勮 / 瀹為獙鍔熻兘锛?- **A1**锛? 寮犲浘灏辨槸 MCODE 鍏紑鐨?鈫?鎴戜滑璧?*鎵爜缁?*锛坒ork limingboGitHub锛?- **A2**锛? 寮犲浘鏄柊鐗?/ 瀹為獙 / 涓嶆槸 MCODE 鏍囧噯 鈫?鎴戜滑閲嶆柊鍐冲畾锛氭壂鐮?OR AppID/Secret
- **A3**锛? 寮犲浘鏄彟涓€涓骇鍝侊紙姣斿 MCODE 涓浗鐗堛€丮axClaw銆乵ini-agent 绛夛級鈫?浣犲憡璇夋垜浜у搧鍚?
### 8.2 馃敶 蹇呯瓟 路 鍐冲畾 UX 褰㈡€?**Q-B**锛歎I 璺嚎锛堣繖鏄笂娆?Q-A锛屼絾 搂1/搂7 鍚庡啀娆￠渶瑕佷綘纭锛?- **A**锛氱嫭绔?IM 涓績锛坄shell.overlay`锛? 璁剧疆椤?鈫?**褰撳墠 DSH slot 鍞竴鑳藉畬鏁磋窇閫?*鐨勫舰鎬?- **B**锛氱瓑 DSH 绔紑鍙?鈫?褰撳墠鍛ㄦ湡鍐呭彧鍋?P0/P1

### 8.3 馃敶 蹇呯瓟 路 鍐冲畾渚濊禆绛栫暐
**Q-C**锛氬弬鑰冨紑婧?vs 鍏ㄩ儴鑷爺
- **A**锛歠ork `limingboGitHub/dsh-feishu-connect`锛圡IT锛夊仛鍩虹 + 鍔?DSH UI 澧為噺 鈫?**鐪?30% 宸ヤ綔閲?*
- **B**锛氱函鑷爺锛堝弬鐓ф€濊矾涓嶄緷璧栦唬鐮侊級 鈫?瀹屽叏鍙帶

### 8.4 鈴?娆¤
**Q-D**锛氭彃浠跺悕锛堝€欓€?`dsh-feishu-link` / `dsh-lark-link` / `dsh-im-bridge` / `dsh-agent-hub`锛?
### 8.5 鈴?娆¤
**Q-E**锛歅0 鑼冨洿 = 浠呴涔?/ 杩樻槸鍖呭惈寰俊 / 閽夐拤锛?
---

## 9. 涓嬩竴姝ュ缓璁?
**绛変綘鍥炵瓟 Q-A + Q-B + Q-C 鍚庢垜绔嬪埢鎺ㄨ繘**锛?
1. **绔嬪埢**锛氭寜浣犳媿鏉跨殑璺嚎寮€涓€寮?wayfinder map锛?*`[dsh-feishu-link] v1 瀹炴柦鍦板浘`** + 5鈥? 寮犲瓙绁?2. **骞惰**锛氭淳 sub-agent 鍋?fork 鍋ュ悍妫€鏌ワ紙`limingboGitHub/dsh-feishu-connect` 浠撳簱娲昏穬搴︺€乮ssue 鍙嶉銆丳R 鑺傚銆佹祴璇曡鐩栵級
3. **鍚屾**锛氭牴鎹綘鐨?UX 閫夋嫨锛屾洿鏂?MCODE 5 寮犲浘 鈫?鎴戜滑鐨?slot 鏄犲皠琛?4. **P0 瀹炴柦**锛氭寜 waystation 鐨?鍙屽舰鎬?妯″紡寮€鍙戯紙鍔ㄦ€?+ npm 姝ｅ紡鐗堬級

---

## 10. 鈽?鍋ュ悍妫€鏌ラ拤姝荤粨璁猴紙sub-agent `cf5d128c` 瀹炴祴 路 2026-08-14锛?
### 10.1 涓€鍙ヨ瘽
**鈿狅笍 璋ㄦ厧閫夋嫨锛氫笉鐩存帴 `npm install` 澶嶇敤 `limingboGitHub/dsh-feishu-connect`**锛堟繁搴︾粦瀹?DSH 绉佸煙銆佺増鏈己鍙ｃ€佹棤 LICENSE 鏂囦欢銆? star銆佸崟浣滆€咃級锛屼絾**鍗忚瀹炵幇鎬濊矾闈炲父鍊煎緱鍊熼壌**鈥斺€旈噰绾?4 涓函 fetch 鍑芥暟 + 鐢ㄥ畼鏂?WSClient 鑷啓闀胯繛鎺?+ 澶氭満鍣ㄤ汉鏋舵瀯鍋氬弬鑰冿紝per-chat Agent 浼氳瘽 + 璁剧疆椤靛畬鍏ㄥ彟璧枫€?
### 10.2 鍐冲畾鎬ц瘉鎹?- **鑷村懡缁戝畾**锛歱eerDep `@deepseek-ai/dsh-tools` + `inject` 鍏ㄥ DSH 瀹夸富鏈嶅姟锛坄agents/shell/webServer/agentPresets`锛夆€斺€旀棤娉曡劚绂?DSH 鐙珛褰撳崗璁?SDK
- **鐗堟湰缂哄彛**锛歱eerDep `@deepseek-ai/dsh-tools ^0.1.0-rc.5` 浣?npm 浠呮湁 rc.2 / rc.3 / rc.6 鈥斺€?涓庡涓诲己鑰﹀悎
- **鏃?LICENSE 鏂囦欢**锛氫粨搴?`license: null`锛屼粎 package.json `"license":"MIT"` 瀛楁涓嶆瀯鎴愭硶寰嬪０鏄?鈫?fork 鎺堟潈涓嶆槑纭?- **闆剁ぞ鍖哄弽棣?*锛? star / 0 fork / 0 issue / 鏃?release / 鍗曚綔鑰呴闄?
### 10.3 鍗忚灞傚彲澶嶇敤鎬х煩闃碉紙閽夋鐗堬級

| 鍏冪礌 | 鏉ユ簮 | 琛屽彿 | 鎴戜滑澶勭悊鏂瑰紡 |
|---|---|---|---|
| `tenantAccessToken` cache | `index.js` L124-137 | 鉁?鍙洿鎺ュ鍒伙紙绾?fetch锛屾棤 DSH 渚濊禆锛?|
| `sendAppMessage` 涓夌骇鐩爣瑙ｆ瀽锛坈hat_id鈫抣astChatId鈫抩wnerOpenId锛?| `index.js` L142-172 | 鉁?鍙洿鎺ュ鍒?|
| 璁惧娴佹壂鐮?init/begin/poll + QR 娓叉煋锛坄accounts.feishu.cn/oauth/v1/app/registration`锛?| `index.js` L912-1008 | 鉁?鍙洿鎺ュ鍒?|
| `addReaction/removeReaction` 澶勭悊涓〃鎯?| `index.js` L178-196 | 鉁?鍙洿鎺ュ鍒?|
| WSS 闀胯繛鎺?helper锛?6 琛?+ EventDispatcher + stdout 骞挎挱 + 10s 蹇冭烦锛?| `helper.cjs` | 馃攣 **鍊熼壌鎬濊矾鑷疄鐜?*锛氬畼鏂?WSClient + timer.interval 蹇冭烦 + 瀛愯繘绋?IPC |
| 澶氭満鍣ㄤ汉绠＄悊锛坆ots[]/鐙珛 helper/state-appId/10s 閰嶇疆閲嶈浇/宕╂簝鑷姩閲嶅惎锛?| `index.js` 澶氬 | 馃攣 **鏋舵瀯鍊熼壌 + 鏇挎崲 DSH 绉佸煙鎺ュ彛**涓?`subprocess` + 鏈湴 child_process |
| per-chat Agent 浼氳瘽姹狅紙resolveActiveAgent/createDedicated/resumeDedicated锛?| 锛堟繁搴﹁€﹀悎 ctx.agents锛?| 鉂?**瀹屽叏涓嶈兘鐢?*锛氭繁搴﹁€﹀悎 ctx.agents/agentPresets锛屽叏鍙﹁捣 |
| Client 璁剧疆椤?+ admin RPC锛坰lots.inject + /feishu/admin/*锛?| `client.js` | 鉂?**瀹屽叏涓嶈兘鐢?*锛氬叏缁戝畾 DSH 瀹夸富 |
| `@deepseek-ai/dsh-tools` | peerDep | 鉂?**涓嶅彲渚濊禆**锛氬唴閮ㄥ寘 |

### 10.4 鎴戜滑鐪熸鐨勪緷璧栨爲

```json
{
  "dependencies": {
    "@larksuiteoapi/node-sdk": "^1.73.0",   // 椋炰功瀹樻柟 SDK锛坣pm 涓荤嚎锛? WSClient
    "qrcode": "^1.5.4",                       // 浜岀淮鐮佹覆鏌擄紙Client UI 鐢級
    "commander": "^12",                       // helper 瀛愯繘绋嬪懡浠よ瑙ｆ瀽锛堝彲閫夛級
    "ws": "^8"                                // 鐩存帴浣跨敤 ws锛堥伩鍏?SDK 榛戠锛?  }
}
```

**浠呬緷璧栭涔﹀畼鏂?SDK 涓庨€氱敤 npm 鍖?*锛屼笉寮曞叆浠讳綍 DSH 绉佸煙鍖呫€傝繖鏍锋湭鏉?DSH 鍗囩骇涓嶆帀閾俱€?
### 10.5 P0 宸ヤ綔閲忔渶缁堟牳瀹氾紙v3锛?
| 妯″潡 | 浼扮畻 | 澧為噺鍘熷洜锛坴2 鈫?v3锛?|
|---|---|---|
| host.js 鎬?| **~900 琛?*锛坴2: 700锛?| +200 琛岋紙鑷爺 tenantAccessToken cache + sendAppMessage 瑙ｆ瀽 + 璁惧娴?3 鍑芥暟 + 琛ㄦ儏澶勭悊锛?|
| client.js 鎬?| ~700 琛?| 涓嶅彉 |
| helper 瀛愯繘绋?| **~150 琛?* | 鏂板鏂囦欢锛坄helper.mjs`锛歐SClient + EventDispatcher + IPC锛?|
| 鍏变韩 fetch utility | ~80 琛?| 鍖呰椋炰功 API |
| 娴嬭瘯锛坔ost 閫昏緫灞傦級 | **~500 琛?* | 浠?waystation 鑼冨紡锛坴erify-bind.js / verify-poll.js / verify-ws.js锛?|
| **鎬昏** | **~2300 琛?*锛坴2: 1700锛?| 鍑€澧?600 琛岋紙鐨嗗洜鍗忚灞傚畬鍏ㄨ嚜鐮?+ 娴嬭瘯锛?|

### 10.6 椤圭洰鐩綍鏈€缁堢粨鏋勶紙v3锛?
```
dsh-plugin/dsh-feishu-link/
鈹溾攢鈹€ README.md
鈹溾攢鈹€ DESIGN.md                鈫?鏈姤鍛?+ DESIGN-concept.md 鍚堝苟瀹氱
鈹溾攢鈹€ ACCEPTANCE.md             鈫?P0 楠屾敹娓呭崟
鈹溾攢鈹€ RESEARCH-NOTES.md         鈫?鏈璋冪爺 3 涓。妗堟眹鎬荤储寮?鈹溾攢鈹€ host.js                   鈫?cordis_define 鐨?code.host
鈹溾攢鈹€ client.js                 鈫?cordis_define 鐨?code.client
鈹溾攢鈹€ lib/
鈹?  鈹溾攢鈹€ fetch.mjs            鈫?4 涓函 fetch 鍑芥暟锛坱enantToken / sendAppMsg / beginBind / pollBind锛?鈹?  鈹斺攢鈹€ ipc.mjs              鈫?涓昏繘绋?鈫?helper 瀛愯繘绋嬬殑 IPC 鍗忚
鈹溾攢鈹€ helper.mjs                鈫?WSS 闀胯繛鎺ュ瓙杩涚▼锛坰pawn 璧锋潵璺戦涔?WSClient锛?鈹溾攢鈹€ tests/
鈹?  鈹溾攢鈹€ verify-bind.js       鈫?璁惧娴佸崟鍏冩祴璇?鈹?  鈹溾攢鈹€ verify-poll.js       鈫?杞鍗曞厓娴嬭瘯
鈹?  鈹溾攢鈹€ verify-ws.js         鈫?WSS 闀胯繛鎺ュ崟鍏冩祴璇?鈹?  鈹斺攢鈹€ verify-fetch.js      鈫?fetch 宸ュ叿鍑芥暟鍗曞厓娴嬭瘯
鈹斺攢鈹€ package/                  鈫?npm 鍙戝竷鐗堬紙鍔ㄦ€佺増鈫掗潤鎬佺増鍚屾锛?    鈹溾攢鈹€ package.json
    鈹溾攢鈹€ lib/index.js          鈫?host 鍗婏紙闈欐€佹彃浠跺崗璁?export const name + apply锛?    鈹溾攢鈹€ lib/client.js         鈫?browser bundle锛坵indow.__ModuleLoader__.load锛?    鈹斺攢鈹€ scripts/install-patch.cjs
```

### 10.7 鍏抽敭瀹炵幇瑕佺偣锛堥拤姝荤増锛?
#### A. 椋炰功璁惧娴侊紙4 涓?fetch 鍑芥暟锛屽弬鑰?dsh-feishu-connect 琛屽彿 1:1 澶嶅埢锛?```javascript
// lib/fetch.mjs 鈥斺€?4 涓函 fetch锛屼笉渚濊禆浠讳綍 DSH 绉佹湁鏈嶅姟
const FEISHU_BASE = 'https://accounts.feishu.cn'

export async function beginBind({ auth_method = 'client_secret', request_user_info = 'open_id', source }) {
  const form = new URLSearchParams({ action: 'begin', auth_method, request_user_info, source })
  const res = await fetch(FEISHU_BASE + '/oauth/v1/app/registration', { method: 'POST', body: form })
  if (!res.ok) throw new Error('feishu begin failed: ' + res.status)
  const j = await res.json()
  if (j.code !== 0) throw new Error('feishu begin error: ' + j.message)
  return j.data   // { device_code, verification_uri_complete, expires_in, interval }
}

export async function pollBind({ device_code }) {
  const form = new URLSearchParams({ action: 'poll', device_code })
  const res = await fetch(FEISHU_BASE + '/oauth/v1/app/registration', { method: 'POST', body: form })
  if (!res.ok) throw new Error('feishu poll failed: ' + res.status)
  const j = await res.json()
  if (j.code === 0) return { status: 'success', appId: j.data.client_id, appSecret: j.data.client_secret, operatorOpenId: j.data.user_info?.open_id }
  if (j.error === 'authorization_pending') return { status: 'pending' }
  throw new Error('feishu poll error: ' + j.message + ' (code ' + j.code + ')')
}

export async function getTenantAccessToken({ appId, appSecret }) {
  const res = await fetch('https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ app_id: appId, app_secret: appSecret }),
  })
  const j = await res.json()
  if (j.code !== 0) throw new Error('feishu token error: ' + j.msg)
  return { accessToken: j.tenant_access_token, expiresAt: Date.now() + (j.expire - 60) * 1000 }
}

export async function sendAppMessage({ accessToken, receiveId, msgType = 'text', content, receiveIdType = 'chat_id' }) {
  const res = await fetch(`https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=${receiveIdType}`, {
    method: 'POST',
    headers: { 'Authorization': 'Bearer ' + accessToken, 'content-type': 'application/json' },
    body: JSON.stringify({ receive_id: receiveId, msg_type: msgType, content: JSON.stringify(content) }),
  })
  return await res.json()
}
```

#### B. WSS 闀胯繛鎺ュ瓙杩涚▼锛坔elper.mjs锛?```javascript
// helper.mjs 鈥斺€?spawn 璧锋潵璺戦涔?WSClient锛屼富杩涚▼閫氳繃 stdio JSON RPC 閫氳
import { WSClient, EventDispatcher, Domain } from '@larksuiteoapi/node-sdk'
import { createInterface } from 'readline'

let bots = []   // [{ agentId, appId, appSecret, wsClient }]

function send(msg) { process.stdout.write(JSON.stringify(msg) + '\n') }

async function startBot(agent) {
  const ws = new WSClient({ appId: agent.appId, appSecret: agent.appSecret, domain: Domain.Feishu })
  const disp = new EventDispatcher({}).register({
    'im.message.receive_v1': (data) => {
      send({ type: 'message', agentId: agent.agentId, data })
    },
  })
  await ws.start({ eventDispatcher: disp })
  bots.push({ ...agent, wsClient: ws })
  send({ type: 'botStarted', agentId: agent.agentId })
}

// 浠?stdio 璇讳富杩涚▼鍛戒护
const rl = createInterface({ input: process.stdin })
rl.on('line', async (line) => {
  const cmd = JSON.parse(line)
  if (cmd.cmd === 'startBot') await startBot(cmd.payload)
  if (cmd.cmd === 'stopBot') {/* ... */}
  if (cmd.cmd === 'shutdown') process.exit(0)
})

process.on('SIGTERM', () => process.exit(0))
send({ type: 'ready' })
```

#### C. Host 涓昏繘绋?IPC锛坙ib/ipc.mjs + host.js锛?```javascript
// host.js 浼唬鐮佺墖娈?import { spawn } from 'child_process'

let helperProc = null
function ensureHelper() {
  if (helperProc) return helperProc
  helperProc = spawn(process.execPath, ['dsh-feishu-link/helper.mjs'], { stdio: ['pipe', 'pipe', 'inherit'] })
  helperProc.stdout.on('data', (chunk) => onHelperStdout(chunk.toString()))
  helperProc.on('exit', (code) => { helperProc = null; timer.setTimeout(ensureHelper, 2000, 'restart-helper') })
  return helperProc
}

function onHelperStdout(text) {
  for (const line of text.split('\n')) {
    if (!line.trim()) continue
    const msg = JSON.parse(line)
    if (msg.type === 'message') {
      // 鈫?璺敱鍒板搴?Agent锛坉sh-im-stations/harness/agents锛?    }
    if (msg.type === 'ready') {
      // 鍚姩鏃舵妸宸茬粦瀹氱殑 bot 鍠傜粰瀹?      const bots = listAllBots()
      bots.forEach(b => helperProc.stdin.write(JSON.stringify({ cmd: 'startBot', payload: b }) + '\n'))
    }
  }
}
```

---

## 11. 涓嬩竴姝ワ紙鎸?v3 缁堢 路 绔嬪嵆鎺ㄨ繘锛?
1. 鉁?涓绘姤鍛?v3 = 鏈枃妗ｏ紙鍚?搂10 鍋ュ悍妫€鏌ラ拤姝荤粨璁猴級
2. 鉁?姒傚康璁捐 v2 = `DESIGN-concept.md`
3. 馃敎 **涓嬩竴姝?*锛氭寜 wayfinder 瑙勮寖寮€涓€寮?GitHub 瀹炴柦 map
   - map 鏍囬锛歚[dsh-feishu-link] v1 瀹炴柦 map 路 5 寮犲浘 IM 缁戝畾锛堟寜鐢ㄦ埛鎺堟潈鑷爺锛塦
   - 鏍囩锛歚dsh:plugin:feishu-link` + `wayfinder:map`
   - 5鈥? 寮犲瓙绁紙research / task / grilling锛夛細
     - **T1 research**锛氭牳瀵?`accounts.feishu.cn/oauth/v1/app/registration` 璁惧娴佹渶鏂扮鐐?+ 椋炰功 WSClient 鍦?DSH Electron 杩涚▼鐨勫吋瀹规€?     - **T2 task**锛歨ost 鍗忚灞傦紙lib/fetch.mjs 4 涓函 fetch + lib/ipc.mjs helper 閫氳 + 7 涓?RPC + 妯″瀷宸ュ叿娉ㄥ唽锛?     - **T3 task**锛歐SS 闀胯繛鎺ュ瓙杩涚▼锛坔elper.mjs 56 琛屾€濊矾鑷爺 + EventDispatcher + 蹇冭烦 + 閲嶅惎绛栫暐锛?     - **T4 task**锛欳lient UI锛? 涓粍浠?shell.overlay / settings.plugins.tab / conversation.input.dock + CSS锛?     - **T5 task**锛氳缃〉 + 妯℃澘缂栬緫鍣?+ 涓嫳鍙岃锛堜豢 waystation v25 T2a/T2b锛?     - **T6 grilling**锛歎X 缁嗚妭鎷嶆澘锛堟彁绀烘潯瑙﹀彂鏃舵満 / 鑷姩灞曞紑 IM 涓績瑙勫垯 / 涓婚瀹夊叏鑹茬粏鑺?/ 鐘舵€佸窘鏍囬鑹诧級
     - **T7 task**锛歅0 楠屾敹锛堜豢 waystation ACCEPTANCE.md锛?   - 闃诲鍏崇郴锛堝師鐢燂級锛歍2/T3/T4/T5 闃诲 T7锛汿2/T3 闃诲 T4锛汿6 闃诲 T7
4. 馃敎 **骞惰**锛氭淳 1 涓?sub-agent 璺?T1锛堟牳瀹為涔﹀崗璁鐐癸級
5. 馃敎 鐢ㄦ埛瀹?map 鍚庡紑 P0 瀹炴柦

---

## 闄勫綍 A 路 鍏抽敭閾炬帴锛堟寜閲嶈鎬ф帓搴忥級

### 鎴戜滑搴旇浣滀负鍩虹渚濊禆鐨勶紙MIT + 鏈€璐磋繎锛?- `https://github.com/limingboGitHub/dsh-feishu-connect` 鈥斺€?MIT锛孋ordis bundle锛孋ordis 娉ㄥ唽灞?`index.js` / `client.js` / `helper.cjs`
- `https://www.npmjs.com/package/dsh-feishu-connect` 鈥斺€?v1.2.4

### 鍗忚灞傚悓鏋勩€乴icense 涓ユ牸锛堝彧璇讳笉鐩存帴 fork锛?- `https://github.com/PlutoKeating/dsh-lark-bot` 鈥斺€?AGPL-3.0锛孋LI 褰㈡€?- `https://www.npmjs.com/package/dsh-lark-bot` / `dsh-feishu-bot` 鈥斺€?v0.5.1 鍙屽寘
- `https://raw.githubusercontent.com/PlutoKeating/dsh-lark-bot/main/src/onboard/registration.ts` 鈥斺€?鍗忚鍏抽敭浠ｇ爜

### 璺緞鐩稿弽锛圓ppID/Secret + 閰嶅鐮佸舰鎬侊級
- `https://github.com/lc2panda/dsh-im-channels` 鈥斺€?main 绌猴紝npm 0.3.1
- `https://github.com/omdsh-dev/dsh-lark` / `https://github.com/imetn/dsh-lark-bridge` 鈥斺€?鍏朵粬椋炰功娓犻亾椤圭洰

### 琛屼笟鑴夌粶
- `https://github.com/like-study1/Oh-My-DSH/blob/main/PLUGINS.md` 鈥斺€?DSH 鎻掍欢鐢熸€佹竻鍗曪紙dsh-lark-bot 鏀跺綍浜庛€岎煋?娑堟伅閫氳銆嶏級
- `https://github.com/AdamPlatin123/awesome-dsh-plugins/blob/main/PLUGINS.md` 鈥斺€?鍚屾牱鏀跺綍锛堜絾鍏?`research/dsh-feishu-bot.md` 涓嶅瓨鍦級
- `https://www.cnblogs.com/vivekgd/articles/19667044` 鈥斺€?OpenClaw + MiniMax + 椋炰功鏈哄櫒浜洪€氱敤閰嶇疆娴佺▼
- `https://platform.minimaxi.com/docs/solutions/openclaw` 鈥斺€?MiniMax OpenClaw 瀹樻柟鏂囨。

### 椤圭洰璺緞閫熻
- 宸ヤ綔鏍癸細`D:\2Study\StudyNotes\SKILLS\`
- DSH 鎻掍欢宸ヤ綔鍖猴細`D:\2Study\StudyNotes\SKILLS\dsh-plugin\`
- 涓绘姤鍛婏細`D:\2Study\StudyNotes\SKILLS\dsh-plugin\RESEARCH-im-binding.md`锛堟湰鏂囦欢锛?- 閰嶅浜嬪疄妗ｏ細`D:\2Study\StudyNotes\SKILLS\dsh-plugin\RESEARCH-dsh-lark-bot.md`锛?58 琛屽師鏂囨憳褰曪級
- 鍏勫紵鎻掍欢锛堝弬鑰冩ā鏉匡級锛?  - `D:\2Study\StudyNotes\SKILLS\dsh-plugin\dsh-waystation\`锛坴25/v26 鍏ㄦ爤鑼冧緥锛?  - `D:\2Study\StudyNotes\SKILLS\dsh-plugin\dsh-opencode-tui-theme\`锛圕lient 涓婚鑼冧緥锛?- 寰呮柊寤猴紙Q-D 瀹氬悕鍚庯級锛歚D:\2Study\StudyNotes\SKILLS\dsh-plugin\<鏂版彃浠跺悕>\`

### issue tracker 绾﹀畾
- GitHub Issues + `gh` CLI锛堣矾寰?`D:\0Tools\GitHubCLI\gh.exe`锛?- 鏍囩 `dsh:plugin:<鍚?`锛堟部鐢?`dsh:plugin:waystation` 鍛藉悕绌洪棿锛?- 鐖?issue 鏍囬鍓嶇紑 `[dsh-feishu-link]` 鎴栧榻愬埌 Q-D 鍛藉悕

### 瀛?agent 鍋ュ悍妫€鏌ヨ剼鏈紙寰?搂9 fork 鍋ュ悍妫€鏌ラ樁娈典娇鐢級
- `https://api.github.com/repos/limingboGitHub/dsh-feishu-connect` 鈥斺€?浠撳簱鍏冩暟鎹?- `https://api.github.com/repos/limingboGitHub/dsh-feishu-connect/issues?state=all&per_page=50` 鈥斺€?issue 鍙嶉
- `https://api.github.com/repos/limingboGitHub/dsh-feishu-connect/commits?per_page=20` 鈥斺€?缁存姢娲昏穬搴?