# Audition 26 未完成与依赖清单（第九轮）

384 个审计条目中仍有 107 项未完整验证。
QA 通过不能自动证明录音硬件/自定义 CEP/AMIO/ASIO/视频往返能力。

| ID | 功能 | 当前状态 |
|---|---|---|
| AU009 | 事件订阅 | not_verified |
| AU017 | 新建空波形 | not_verified |
| AU019 | 原生 MP3 | not_verified |
| AU024 | 文件格式对象 | not_verified |
| AU027 | 全选 | not_verified |
| AU044 | 操作撤销 | not_verified |
| AU045 | 频谱显示 | ui_or_media_pending |
| AU046 | 频谱修复画笔 | ui_or_media_pending |
| AU047 | 套索频谱选择 | ui_or_media_pending |
| AU048 | 矩形频谱选择 | ui_or_media_pending |
| AU049 | 自动修复 | ui_or_media_pending |
| AU050 | 窄带噪声检测 | ui_or_media_pending |
| AU051 | 工频谱峰 | ui_or_media_pending |
| AU054 | 能量曲线 | ui_or_media_pending |
| AU056 | 频谱修复质检 | ui_or_media_pending |
| AU058 | DeReverb | existing_legacy_recheck |
| AU062 | 去爆破音 | ui_or_media_pending |
| AU063 | Click Repair | ui_or_media_pending |
| AU066 | 自适应降噪 | ui_or_media_pending |
| AU070 | 对白增强 | ui_or_media_pending |
| AU071 | 修复前后质检 | ui_or_media_pending |
| AU073 | Normalize | ui_or_media_pending |
| AU075 | 多段压缩 | ui_or_media_pending |
| AU076 | 扩展器 | ui_or_media_pending |
| AU081 | 去齿音 | ui_or_media_pending |
| AU083 | 动态 EQ | ui_or_media_pending |
| AU084 | 声音饱和 | ui_or_media_pending |
| AU085 | 峰值保护 | ui_or_media_pending |
| AU086 | Graphic EQ | ui_or_media_pending |
| AU089 | FIR Filter | ui_or_media_pending |
| AU090 | IIR Filter | ui_or_media_pending |
| AU095 | Convolution Reverb | ui_or_media_pending |
| AU096 | Studio Reverb | ui_or_media_pending |
| AU103 | Stereo Expand | ui_or_media_pending |
| AU104 | VST 插件 | ui_or_media_pending |
| AU105 | 新建多轨 | not_verified |
| AU107 | 保存 Session | not_verified |
| AU108 | 另存 Session | not_verified |
| AU115 | Track pan | existing_legacy_recheck |
| AU121 | Track effects | not_verified |
| AU122 | Track buses | partial_native_live |
| AU123 | 子混音 | not_verified |
| AU126 | 多轨信封 | not_verified |
| AU127 | 5.1 路由 | not_verified |
| AU131 | Record | ui_or_media_pending |
| AU134 | 预卷 | ui_or_media_pending |
| AU135 | 录音监测 | ui_or_media_pending |
| AU136 | 输入设备 | ui_or_media_pending |
| AU137 | 录音待命 | ui_or_media_pending |
| AU138 | ASIO | ui_or_media_pending |
| AU139 | 录音倒计时 | ui_or_media_pending |
| AU140 | 录音轨道映射 | ui_or_media_pending |
| AU152 | BWF 时间戳 | not_verified |
| AU153 | 音乐信息同步 | not_verified |
| AU155 | Favorite list | not_verified |
| AU156 | Favorite create | not_verified |
| AU173 | ATSC A85 | ui_or_media_pending |
| AU206 | Multispeaker EQ | ui_or_media_pending |
| AU209 | 降环境噪声 | ui_or_media_pending |
| AU210 | 口腔噪声 | ui_or_media_pending |
| AU211 | 语音压缩 | ui_or_media_pending |
| AU214 | 自动字幕 | ui_or_media_pending |
| AU215 | 转录音频 | ui_or_media_pending |
| AU216 | 自动角色分离 | ui_or_media_pending |
| AU217 | 视频音轨引用 | ui_or_media_pending |
| AU218 | Premiere 往返 | ui_or_media_pending |
| AU219 | Dynamic Link | ui_or_media_pending |
| AU220 | OMF Import | ui_or_media_pending |
| AU221 | OMF Export | ui_or_media_pending |
| AU222 | AAF Import | ui_or_media_pending |
| AU223 | AAF Export | ui_or_media_pending |
| AU224 | 时间码同步 | ui_or_media_pending |
| AU225 | 素材重链 | ui_or_media_pending |
| AU226 | 5.1 视频混音 | ui_or_media_pending |
| AU227 | 视频同步回放 | ui_or_media_pending |
| AU228 | 音画交付 | ui_or_media_pending |
| AU229 | Script Dictionary | cep_install_pending |
| AU230 | Application Commands | cep_install_pending |
| AU231 | Playhead Panel | cep_install_pending |
| AU232 | Transport Events | cep_install_pending |
| AU233 | CSInterface evalScript | cep_install_pending |
| AU234 | 自定义 CEP Panel | cep_install_pending |
| AU235 | 面板命令表 | cep_install_pending |
| AU236 | WebSocket bridge | cep_install_pending |
| AU237 | Web service | cep_install_pending |
| AU238 | 读写媒体元数据 | cep_install_pending |
| AU239 | CEP 插件安装 | cep_install_pending |
| AU240 | Panel 生命周期 | cep_install_pending |
| AU241 | 自定义媒体导入 | sdk_or_hardware_required |
| AU242 | 自定义媒体导出 | sdk_or_hardware_required |
| AU243 | 原生 Session 翻译 | sdk_or_hardware_required |
| AU244 | 自定义格式 | sdk_or_hardware_required |
| AU245 | Control Surface | sdk_or_hardware_required |
| AU246 | Fader 双向回读 | sdk_or_hardware_required |
| AU247 | 控制设备消息 | sdk_or_hardware_required |
| AU248 | 原生媒体 IO 插件 | sdk_or_hardware_required |
| AU249 | 第三方 VST3 | sdk_or_hardware_required |
| AU250 | C++ SDK 构建 | sdk_or_hardware_required |
| AU251 | 插件加载 | sdk_or_hardware_required |
| AU252 | 签名发布 | sdk_or_hardware_required |
| AU263 | 操作错误报告 | not_verified |
| AU272 | AudioBusTrackCollection remove | blocked_native_api |
| AU305 | CEP panel loaded inside Audition host | cep_install_pending |
| AU306 | Audition AMIO C++ SDK compile and deploy | sdk_or_hardware_required |
| AU331 | CEP Plugin host PlugPlugSetup internal error | blocked_host_runtime |
| AU332 | CEP live panel and evalScript callback | cep_install_pending |
| AU360 | PlugPlugSetup still failing after official CEP12 host correction | blocked_host_runtime |
