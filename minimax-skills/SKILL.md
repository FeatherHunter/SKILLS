https://github.com/MiniMax-AI/skills/tree/main/skills
激活其中的 minimax-multimodal-toolkit,vision-analysis,minimax-docx,minimax-music-gen,minimax-pdf,minimax-xlsx

向我询问拿到 API KEY
然后完成所有配置直至全部可以使用




请帮我接入 MiniMax CLI（https://github.com/MiniMax-AI/cli），按以下三步完成安装与配置：

1. 全局安装 CLI：执行 `npm install -g mmx-cli`，完成后用 `mmx --version` 验证
2. 登录并配置 API Key：执行 `mmx auth login --api-key sk-xxxxx`；
3. 安装官方 SKILL：执行 `npx skills add MiniMax-AI/cli -y -g`

完成后请执行 `mmx quota` 查看我的 Token Plan 余额，确认整体配置生效。


文本	mmx text chat	多轮对话、流式输出、系统提示词、JSON 输出
图像	mmx image generate	文生图，支持宽高比与批量生成
视频	mmx video generate	异步视频生成，支持任务查询与下载
语音	mmx speech synthesize	文字转语音（TTS），支持多音色与流式输出
音乐	mmx music generate	文生音乐，支持歌词模式与纯音乐模式
视觉	mmx vision describe	图像理解，支持本地文件、URL、文件 ID
搜索	mmx search query	内置网络检索


mmx auth status / refresh / logout	查看登录身份 / 刷新凭据 / 登出	mmx auth status
mmx config show / set	查看与修改配置（region、默认模型等）	mmx config set --key region --value cn
mmx quota	查看 Token Plan 用量与剩余额度	mmx quota
mmx update / mmx update latest	检查更新 / 升级到最新版	mmx update latest