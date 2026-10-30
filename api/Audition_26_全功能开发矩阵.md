# Audition 26 全功能开发矩阵（第九轮）

上一轮冻结基线：api/Audition_26_phase08_baseline_379.json。
本轮旧问题仅依证据升级，故障未解决的 CEP/Bus/SDK 状态保留。

| 状态 | 数量 |
|---|---:|
| blocked_host_runtime | 2 |
| blocked_native_api | 1 |
| cep_install_pending | 14 |
| existing_legacy_recheck | 2 |
| not_verified | 18 |
| partial_native_live | 1 |
| sdk_or_hardware_required | 13 |
| ui_or_media_pending | 56 |
| verified_hybrid_sesx_reopened | 27 |
| verified_installed_not_loaded | 1 |
| verified_native_live | 59 |
| verified_offline | 126 |
| verified_offline_ffmpeg | 52 |
| verified_offline_heuristic | 5 |
| verified_readonly_host | 4 |
| verified_static_only | 3 |

| ID | 功能 | 状态 | 证据 |
|---|---|---|---|
| AU001 | 启动状态 | verified_native_live |  |
| AU002 | 版本及构建号 | verified_native_live |  |
| AU003 | 活跃文档 | verified_native_live |  |
| AU004 | 已打开文档 | verified_native_live |  |
| AU005 | DOM 对象反射 | verified_native_live |  |
| AU006 | 只读命令枚举 | verified_readonly_host | api\Audition_26_native_menu_registry.json |
| AU007 | 命令状态 | verified_native_live |  |
| AU008 | 原生命令调用 | verified_native_live | tests\receipts\phase07_native_mp3_flac_open.json |
| AU009 | 事件订阅 | not_verified |  |
| AU010 | 停止播放 | verified_native_live | tests\receipts\phase06_native_transport_acceptance.json |
| AU011 | 未保存检测 | verified_native_live | tests\receipts\phase07_native_mp3_flac_open.json |
| AU012 | 安全任务超时 | verified_offline | tests\receipts\phase08_transport_faults.json |
| AU013 | WAV 打开 | verified_native_live |  |
| AU014 | MP3 打开 | verified_native_live | tests\receipts\phase07_native_mp3_flac_open.json |
| AU015 | FLAC 打开 | verified_native_live | tests\receipts\phase07_native_mp3_flac_open.json |
| AU016 | 多文档 | verified_native_live | tests\receipts\phase07_native_mp3_flac_open.json |
| AU017 | 新建空波形 | not_verified |  |
| AU018 | 另存 WAV | verified_native_live |  |
| AU019 | 原生 MP3 | not_verified |  |
| AU020 | 重采样导出 | verified_native_live |  |
| AU021 | 位深转换 | verified_offline | tests\receipts\phase07_float_to_pcm16.json |
| AU022 | Dither | verified_offline | tests\receipts\phase07_float_to_pcm16.json |
| AU023 | Noise Shaping | verified_offline | tests\receipts\phase07_float_to_pcm16.json |
| AU024 | 文件格式对象 | not_verified |  |
| AU025 | 元数据保留 | verified_offline_ffmpeg | tests/receipts/phase06_tag_delivery.json |
| AU026 | 关闭文档 | verified_native_live |  |
| AU027 | 全选 | not_verified |  |
| AU028 | 复制 | verified_offline | tests\receipts\phase07_waveform_timeline_acceptance.json |
| AU029 | 剪切 | verified_offline | tests\receipts\phase07_waveform_timeline_acceptance.json |
| AU030 | 粘贴 | verified_offline | tests\receipts\phase07_waveform_timeline_acceptance.json |
| AU031 | 删除 | verified_offline | tests\receipts\phase07_waveform_timeline_acceptance.json |
| AU032 | 插入静音 | verified_offline | tests\receipts\phase07_waveform_timeline_acceptance.json |
| AU033 | 样本级裁剪 | verified_offline |  |
| AU034 | 片段反转 | verified_offline |  |
| AU035 | 淡入淡出 | verified_offline |  |
| AU036 | 增益 | verified_offline |  |
| AU037 | 峰值标准化 | verified_offline |  |
| AU038 | 声道分离 | verified_offline | tests\receipts\phase07_channel_split_roundtrip.json |
| AU039 | 单声道合并 | verified_offline |  |
| AU040 | 立体声混合 | verified_offline |  |
| AU041 | 通道平衡 | verified_offline |  |
| AU042 | 播放头位置 | verified_native_live | tests\receipts\phase06_native_transport_acceptance.json |
| AU043 | 分段静音 | verified_offline |  |
| AU044 | 操作撤销 | not_verified |  |
| AU045 | 频谱显示 | ui_or_media_pending |  |
| AU046 | 频谱修复画笔 | ui_or_media_pending |  |
| AU047 | 套索频谱选择 | ui_or_media_pending |  |
| AU048 | 矩形频谱选择 | ui_or_media_pending |  |
| AU049 | 自动修复 | ui_or_media_pending |  |
| AU050 | 窄带噪声检测 | ui_or_media_pending |  |
| AU051 | 工频谱峰 | ui_or_media_pending |  |
| AU052 | 主频分析 | verified_offline |  |
| AU053 | 谱重心 | verified_offline |  |
| AU054 | 能量曲线 | ui_or_media_pending |  |
| AU055 | 谱图导出 | verified_offline | tests\receipts\phase07_waveform_timeline_acceptance.json |
| AU056 | 频谱修复质检 | ui_or_media_pending |  |
| AU057 | DeNoise | verified_offline_ffmpeg | tests/receipts/phase06_effects_batch.json;phase05_ducking_and_mastering.json |
| AU058 | DeReverb | existing_legacy_recheck |  |
| AU059 | 去 50Hz Hum | verified_offline_ffmpeg | tests/receipts/phase06_effects_batch.json;phase06_effects_second_batch.json |
| AU060 | 去 60Hz Hum | verified_offline_ffmpeg | tests/receipts/phase06_effects_batch.json;phase06_effects_second_batch.json |
| AU061 | 去 DC Offset | verified_offline |  |
| AU062 | 去爆破音 | ui_or_media_pending |  |
| AU063 | Click Repair | ui_or_media_pending |  |
| AU064 | DeClick | verified_offline_ffmpeg | tests/receipts/phase06_effects_batch.json;phase06_effects_second_batch.json |
| AU065 | DeClip | verified_offline_ffmpeg | tests/receipts/phase06_effects_batch.json;phase06_effects_second_batch.json |
| AU066 | 自适应降噪 | ui_or_media_pending |  |
| AU067 | Noise Gate | verified_offline |  |
| AU068 | High Pass | verified_offline |  |
| AU069 | Notch | verified_offline |  |
| AU070 | 对白增强 | ui_or_media_pending |  |
| AU071 | 修复前后质检 | ui_or_media_pending |  |
| AU072 | Amplify | verified_offline_ffmpeg | tests/receipts/phase06_effects_batch.json;phase06_effects_second_batch.json |
| AU073 | Normalize | ui_or_media_pending |  |
| AU074 | 压缩器 | verified_offline |  |
| AU075 | 多段压缩 | ui_or_media_pending |  |
| AU076 | 扩展器 | ui_or_media_pending |  |
| AU077 | 限制器 | verified_offline |  |
| AU078 | True Peak Limit | verified_offline_ffmpeg | tests/receipts/phase06_effects_batch.json;phase05_ducking_and_mastering.json |
| AU079 | 自动电平 | verified_offline_ffmpeg | tests/receipts/phase06_effects_batch.json;phase06_effects_second_batch.json |
| AU080 | 门限 | verified_offline_ffmpeg | tests/receipts/phase06_effects_batch.json;phase06_effects_second_batch.json |
| AU081 | 去齿音 | ui_or_media_pending |  |
| AU082 | 侧链压缩 | verified_offline_ffmpeg | tests/receipts/phase06_effects_batch.json;phase06_effects_second_batch.json |
| AU083 | 动态 EQ | ui_or_media_pending |  |
| AU084 | 声音饱和 | ui_or_media_pending |  |
| AU085 | 峰值保护 | ui_or_media_pending |  |
| AU086 | Graphic EQ | ui_or_media_pending |  |
| AU087 | Parametric EQ | verified_offline_ffmpeg | tests/receipts/phase06_effects_batch.json;phase06_effects_second_batch.json |
| AU088 | Track EQ | verified_hybrid_sesx_reopened | tests\receipts\phase04_real_eq_render.json |
| AU089 | FIR Filter | ui_or_media_pending |  |
| AU090 | IIR Filter | ui_or_media_pending |  |
| AU091 | High Pass | verified_offline |  |
| AU092 | Low Pass | verified_offline |  |
| AU093 | Band Pass | verified_offline_ffmpeg | tests/receipts/phase06_effects_batch.json;phase06_effects_second_batch.json |
| AU094 | Notch Filter | verified_offline_ffmpeg | tests/receipts/phase06_effects_batch.json;phase06_effects_second_batch.json |
| AU095 | Convolution Reverb | ui_or_media_pending |  |
| AU096 | Studio Reverb | ui_or_media_pending |  |
| AU097 | Delay | verified_offline_ffmpeg | tests/receipts/phase06_effects_batch.json;phase06_effects_second_batch.json |
| AU098 | Echo | verified_offline_ffmpeg | tests/receipts/phase06_effects_batch.json;phase06_effects_second_batch.json |
| AU099 | Chorus | verified_offline_ffmpeg | tests/receipts/phase06_effects_batch.json;phase06_effects_second_batch.json |
| AU100 | Flanger | verified_offline_ffmpeg | tests/receipts/phase06_effects_batch.json;phase06_effects_second_batch.json |
| AU101 | Pitch Shift | verified_offline_ffmpeg | tests/receipts/phase06_effects_batch.json;phase06_effects_second_batch.json |
| AU102 | Time Stretch | verified_offline_ffmpeg | tests/receipts/phase06_effects_batch.json;phase06_effects_second_batch.json |
| AU103 | Stereo Expand | ui_or_media_pending |  |
| AU104 | VST 插件 | ui_or_media_pending |  |
| AU105 | 新建多轨 | not_verified |  |
| AU106 | 打开 SESX | verified_native_live | tests\receipts\phase07_native_split_acceptance.json |
| AU107 | 保存 Session | not_verified |  |
| AU108 | 另存 Session | not_verified |  |
| AU109 | Track rename | verified_native_live | tests/receipts/phase02-phase04 |
| AU110 | Track mute | verified_native_live | tests/receipts/phase02-phase04 |
| AU111 | Track solo | verified_native_live | tests/receipts/phase02-phase04 |
| AU112 | Track arm | verified_native_live | tests/receipts/phase09_native_acceptance.json |
| AU113 | Track visibility | verified_native_live | tests/receipts/phase09_native_acceptance.json |
| AU114 | Track fader | verified_hybrid_sesx_reopened | tests\receipts\phase07_native_track_controls.json |
| AU115 | Track pan | existing_legacy_recheck |  |
| AU116 | Clip move | verified_native_live | tests/receipts/phase02-phase04 |
| AU117 | Clip gain | verified_hybrid_sesx_reopened | tests\receipts\phase06_native_arrangement_acceptance.json |
| AU118 | Clip fade in | verified_hybrid_sesx_reopened | tests\receipts\phase05_native_clip_trim_fade_acceptance.json |
| AU119 | Clip fade out | verified_hybrid_sesx_reopened | tests\receipts\phase05_native_clip_trim_fade_acceptance.json |
| AU120 | Track EQ | verified_hybrid_sesx_reopened | tests/receipts/phase02-phase04 |
| AU121 | Track effects | not_verified |  |
| AU122 | Track buses | partial_native_live | tests/receipts/phase02-phase04 |
| AU123 | 子混音 | not_verified |  |
| AU124 | 剪辑插入 | verified_hybrid_sesx_reopened | tests\receipts\phase07_native_split_acceptance.json |
| AU125 | 剪辑拆分 | verified_hybrid_sesx_reopened | tests\receipts\phase07_native_split_acceptance.json |
| AU126 | 多轨信封 | not_verified |  |
| AU127 | 5.1 路由 | not_verified |  |
| AU128 | Play | verified_native_live | tests/receipts/phase06_native_transport_acceptance.json |
| AU129 | Pause | verified_native_live | tests/receipts/phase06_native_transport_acceptance.json |
| AU130 | Stop | verified_native_live | tests/receipts/phase06_native_transport_acceptance.json |
| AU131 | Record | ui_or_media_pending |  |
| AU132 | Loop | verified_native_live | tests/receipts/phase06_native_transport_acceptance.json |
| AU133 | Seek | verified_native_live | tests/receipts/phase06_native_transport_acceptance.json |
| AU134 | 预卷 | ui_or_media_pending |  |
| AU135 | 录音监测 | ui_or_media_pending |  |
| AU136 | 输入设备 | ui_or_media_pending |  |
| AU137 | 录音待命 | ui_or_media_pending |  |
| AU138 | ASIO | ui_or_media_pending |  |
| AU139 | 录音倒计时 | ui_or_media_pending |  |
| AU140 | 录音轨道映射 | ui_or_media_pending |  |
| AU141 | Marker add | verified_native_live |  |
| AU142 | Marker range | verified_native_live | tests/receipts/phase02-phase04 |
| AU143 | Marker name | verified_native_live |  |
| AU144 | Marker description | verified_native_live | tests/receipts/phase02-phase04 |
| AU145 | Marker type | verified_native_live | tests/receipts/phase09_native_markers.json |
| AU146 | Marker readback | verified_native_live | tests/receipts/phase02-phase04 |
| AU147 | Marker export | verified_offline | tests/receipts/phase05_xmp_chapter_acceptance.json |
| AU148 | 批量标记 | verified_hybrid_sesx_reopened | tests\receipts\phase06_native_xmp_edit_acceptance.json |
| AU149 | XMP 读 | verified_offline | tests/receipts/phase05_xmp_chapter_acceptance.json |
| AU150 | XMP 写 | verified_hybrid_sesx_reopened | tests/receipts/phase06_native_xmp_edit_acceptance.json |
| AU151 | ID3 标签 | verified_offline_ffmpeg | tests/receipts/phase06_tag_delivery.json |
| AU152 | BWF 时间戳 | not_verified |  |
| AU153 | 音乐信息同步 | not_verified |  |
| AU154 | Favorite apply | verified_native_live |  |
| AU155 | Favorite list | not_verified |  |
| AU156 | Favorite create | not_verified |  |
| AU157 | Favorite batch | verified_native_live | tests/receipts/phase09_native_batch_acceptance.json |
| AU158 | 文件批量打开 | verified_native_live | tests/receipts/phase09_native_acceptance.json |
| AU159 | 批量 WAV | verified_offline |  |
| AU160 | 批量 MP3 | verified_offline | tests/receipts/phase09_offline_batch_acceptance.json |
| AU161 | 批量 FLAC | verified_offline | tests/receipts/phase08_real_delivery.json |
| AU162 | 批量重采样 | verified_native_live | tests/receipts/phase09_native_batch_acceptance.json |
| AU163 | 批量命名 | verified_offline | tests/receipts/phase09_native_batch_acceptance.json |
| AU164 | 任务回滚 | verified_offline | tests\receipts\phase06_production_bundle_acceptance.json |
| AU165 | 结果清单 | verified_offline |  |
| AU166 | 失败隔离 | verified_offline | tests/receipts/phase08_real_delivery.json |
| AU167 | 批量响度 | verified_offline | tests/receipts/phase09_offline_batch_acceptance.json |
| AU168 | Integrated LUFS | verified_offline_ffmpeg | tests/receipts/phase02-phase04 |
| AU169 | Short-term LUFS | verified_offline_ffmpeg | tests/receipts/phase06_r128_timeline.json |
| AU170 | Momentary LUFS | verified_offline_ffmpeg | tests/receipts/phase06_r128_timeline.json |
| AU171 | ITU BS1770 | verified_offline_ffmpeg | tests/receipts/phase06_r128_timeline.json |
| AU172 | EBU R128 | verified_offline_ffmpeg | tests/receipts/phase06_r128_timeline.json |
| AU173 | ATSC A85 | ui_or_media_pending |  |
| AU174 | True Peak | verified_offline_ffmpeg | tests/receipts/phase02-phase04 |
| AU175 | Sample Peak | verified_offline |  |
| AU176 | RMS | verified_offline |  |
| AU177 | DC Offset | verified_offline |  |
| AU178 | Clipping count | verified_offline |  |
| AU179 | Silence detection | verified_offline | tests/receipts/phase05_session_preflight.json;phase06_r128_timeline.json |
| AU180 | Click detection | verified_offline_heuristic | tests/receipts/phase03_forensics_delivery_acceptance.json |
| AU181 | Crest Factor | verified_offline | tests/receipts/phase05_session_preflight.json;phase06_r128_timeline.json |
| AU182 | Stereo correlation | verified_offline |  |
| AU183 | Frequency centroid | verified_offline |  |
| AU184 | Loudness batch | verified_offline_ffmpeg | tests/receipts/phase05_ducking_and_mastering.json;phase06_production_bundle_acceptance.json |
| AU185 | JSON 报告 | verified_offline | tests/receipts/phase05_session_preflight.json;phase06_r128_timeline.json |
| AU186 | PCM16 WAV | verified_offline |  |
| AU187 | Float32 WAV | verified_offline |  |
| AU188 | PCM24 WAV | verified_native_live |  |
| AU189 | MP3 | verified_offline |  |
| AU190 | FLAC | verified_offline |  |
| AU191 | AAC M4A | verified_offline |  |
| AU192 | Vorbis OGG | verified_offline |  |
| AU193 | Opus | verified_offline |  |
| AU194 | 16k speech WAV | verified_offline |  |
| AU195 | 44.1k WAV | verified_native_live |  |
| AU196 | 48k WAV | verified_offline |  |
| AU197 | 96k WAV | verified_native_live |  |
| AU198 | Mono | verified_offline |  |
| AU199 | Stereo | verified_offline |  |
| AU200 | Codec validation | verified_offline |  |
| AU201 | File hash | verified_offline |  |
| AU202 | Batch export | verified_offline | tests/receipts/phase02-phase04 |
| AU203 | Overwrite guard | verified_offline |  |
| AU204 | Dialogue leveling | verified_offline_ffmpeg | tests/receipts/phase05_ducking_and_mastering.json;phase06_production_bundle_acceptance.json |
| AU205 | Music ducking | verified_offline_ffmpeg | tests/receipts/phase05_ducking_and_mastering.json;phase06_production_bundle_acceptance.json |
| AU206 | Multispeaker EQ | ui_or_media_pending |  |
| AU207 | Podcast mastering | verified_offline_ffmpeg | tests/receipts/phase05_ducking_and_mastering.json;phase06_production_bundle_acceptance.json |
| AU208 | 片头片尾处理 | verified_offline_ffmpeg | tests/receipts/phase05_ducking_and_mastering.json;phase06_production_bundle_acceptance.json |
| AU209 | 降环境噪声 | ui_or_media_pending |  |
| AU210 | 口腔噪声 | ui_or_media_pending |  |
| AU211 | 语音压缩 | ui_or_media_pending |  |
| AU212 | LUFS -16 | verified_offline_ffmpeg | tests/receipts/phase05_ducking_and_mastering.json;phase06_production_bundle_acceptance.json |
| AU213 | 广播 -23 | verified_offline_ffmpeg | tests/receipts/phase05_ducking_and_mastering.json;phase06_production_bundle_acceptance.json |
| AU214 | 自动字幕 | ui_or_media_pending |  |
| AU215 | 转录音频 | ui_or_media_pending |  |
| AU216 | 自动角色分离 | ui_or_media_pending |  |
| AU217 | 视频音轨引用 | ui_or_media_pending |  |
| AU218 | Premiere 往返 | ui_or_media_pending |  |
| AU219 | Dynamic Link | ui_or_media_pending |  |
| AU220 | OMF Import | ui_or_media_pending |  |
| AU221 | OMF Export | ui_or_media_pending |  |
| AU222 | AAF Import | ui_or_media_pending |  |
| AU223 | AAF Export | ui_or_media_pending |  |
| AU224 | 时间码同步 | ui_or_media_pending |  |
| AU225 | 素材重链 | ui_or_media_pending |  |
| AU226 | 5.1 视频混音 | ui_or_media_pending |  |
| AU227 | 视频同步回放 | ui_or_media_pending |  |
| AU228 | 音画交付 | ui_or_media_pending |  |
| AU229 | Script Dictionary | cep_install_pending |  |
| AU230 | Application Commands | cep_install_pending |  |
| AU231 | Playhead Panel | cep_install_pending |  |
| AU232 | Transport Events | cep_install_pending |  |
| AU233 | CSInterface evalScript | cep_install_pending |  |
| AU234 | 自定义 CEP Panel | cep_install_pending |  |
| AU235 | 面板命令表 | cep_install_pending |  |
| AU236 | WebSocket bridge | cep_install_pending |  |
| AU237 | Web service | cep_install_pending |  |
| AU238 | 读写媒体元数据 | cep_install_pending |  |
| AU239 | CEP 插件安装 | cep_install_pending |  |
| AU240 | Panel 生命周期 | cep_install_pending |  |
| AU241 | 自定义媒体导入 | sdk_or_hardware_required |  |
| AU242 | 自定义媒体导出 | sdk_or_hardware_required |  |
| AU243 | 原生 Session 翻译 | sdk_or_hardware_required |  |
| AU244 | 自定义格式 | sdk_or_hardware_required |  |
| AU245 | Control Surface | sdk_or_hardware_required |  |
| AU246 | Fader 双向回读 | sdk_or_hardware_required |  |
| AU247 | 控制设备消息 | sdk_or_hardware_required |  |
| AU248 | 原生媒体 IO 插件 | sdk_or_hardware_required |  |
| AU249 | 第三方 VST3 | sdk_or_hardware_required |  |
| AU250 | C++ SDK 构建 | sdk_or_hardware_required |  |
| AU251 | 插件加载 | sdk_or_hardware_required |  |
| AU252 | 签名发布 | sdk_or_hardware_required |  |
| AU253 | 安全工作区 | verified_offline | tests\receipts\phase07_waveform_timeline_acceptance.json |
| AU254 | 备份 | verified_offline | tests\receipts\phase07_waveform_pipeline_acceptance.json |
| AU255 | 源文件只读 | verified_offline | tests\receipts\phase07_waveform_timeline_acceptance.json |
| AU256 | 拒绝覆盖 | verified_offline | tests\receipts\phase07_waveform_timeline_acceptance.json |
| AU257 | 路径预检 | verified_offline | tests\receipts\phase07_waveform_timeline_acceptance.json |
| AU258 | 超时处理 | verified_offline | tests\receipts\phase08_transport_faults.json |
| AU259 | 文件 SHA256 | verified_offline | tests\receipts\phase07_waveform_timeline_acceptance.json |
| AU260 | 输出后解码 | verified_offline | tests\receipts\phase07_channel_split_roundtrip.json |
| AU261 | 固定测试波形 | verified_offline | tests\receipts\phase07_waveform_timeline_acceptance.json |
| AU262 | 日志清单 | verified_offline | tests\receipts\phase07_waveform_timeline_acceptance.json |
| AU263 | 操作错误报告 | not_verified |  |
| AU264 | 自动回归 | verified_offline | tests\receipts\phase07_waveform_pipeline_acceptance.json |
| AU265 | 恢复说明 | verified_offline | tests\receipts\phase07_waveform_pipeline_acceptance.json |
| AU266 | 使用文档 | verified_offline | tests\receipts\phase07_waveform_pipeline_acceptance.json |
| AU267 | API 动态发现 | verified_readonly_host | api\Audition_26_native_menu_registry.json |
| AU268 | MultitrackDocument live reflection | verified_native_live |  |
| AU269 | AudioTrackCollection add and remove | verified_native_live |  |
| AU270 | AudioClipCollection move preserving time | verified_native_live |  |
| AU271 | AudioBusTrackCollection add | verified_native_live |  |
| AU272 | AudioBusTrackCollection remove | blocked_native_api |  |
| AU273 | MultitrackDocument addMarker | verified_native_live |  |
| AU274 | Native SESX save and reopen | verified_native_live |  |
| AU275 | Native marker save and DOM readback | verified_native_live |  |
| AU276 | Audition multitrack Mixdown to Float WAV | verified_native_live |  |
| AU277 | 474 real menu commands discovered | verified_readonly_host |  |
| AU278 | 473 distinct native menu command IDs | verified_readonly_host |  |
| AU279 | Track to Bus routing and reimport | verified_hybrid_sesx_reopened |  |
| AU280 | Native Mixdown through bus | verified_hybrid_sesx_reopened |  |
| AU281 | Cycles and dangling bus routes detection | verified_offline |  |
| AU282 | Remove unused QA Bus and native reopen | verified_hybrid_sesx_reopened |  |
| AU283 | Reject referenced Bus deletion | verified_offline |  |
| AU284 | Self contained native session media packaging | verified_hybrid_sesx_reopened |  |
| AU285 | Native reopen and mix packaged session | verified_hybrid_sesx_reopened |  |
| AU286 | Media hash verification and relink | verified_offline |  |
| AU287 | Native EQ serialized parameters roundtrip | verified_hybrid_sesx_reopened |  |
| AU288 | Native EQ audible rendered output | verified_hybrid_sesx_reopened |  |
| AU289 | Reject dangerous EQ gain values | verified_offline |  |
| AU290 | EQ processing tail length check | verified_hybrid_sesx_reopened |  |
| AU291 | Approximate oversampled true peak | verified_offline_heuristic |  |
| AU292 | RMS silence region identification | verified_offline_heuristic |  |
| AU293 | Click candidate detection | verified_offline_heuristic |  |
| AU294 | 50Hz and 60Hz hum candidates | verified_offline_heuristic |  |
| AU295 | Stereo anti-phase and mono fold-down | verified_offline |  |
| AU296 | Crest factor frequency band analysis | verified_offline |  |
| AU297 | Podcast broadcast music QC presets | verified_offline |  |
| AU298 | JSON and SHA256 QA reporting | verified_offline |  |
| AU299 | Two-pass FFmpeg R128 loudnorm | verified_offline_ffmpeg |  |
| AU300 | Podcast 16 LUFS WAV MP3 actual export | verified_offline_ffmpeg |  |
| AU301 | Broadcast 23 LUFS FLAC actual export | verified_offline_ffmpeg |  |
| AU302 | Batch delivery immutable source guard | verified_offline |  |
| AU303 | Static validation of Audition panel manifest | verified_static_only |  |
| AU304 | User-level CEP panel staged and hash checked | verified_installed_not_loaded |  |
| AU305 | CEP panel loaded inside Audition host | cep_install_pending |  |
| AU306 | Audition AMIO C++ SDK compile and deploy | sdk_or_hardware_required |  |
| AU307 | Native clip source trim with sample-accurate bounds | verified_hybrid_sesx_reopened | Phase05 tests and tests/receipts/phase05_*.json; for blocked statuses see CEP12-AUDT.log |
| AU308 | Native clip position after trim readback | verified_hybrid_sesx_reopened | Phase05 tests and tests/receipts/phase05_*.json; for blocked statuses see CEP12-AUDT.log |
| AU309 | Native clip fade-in/out duration editing | verified_hybrid_sesx_reopened | Phase05 tests and tests/receipts/phase05_*.json; for blocked statuses see CEP12-AUDT.log |
| AU310 | Native session lock clip flag readback | verified_offline | Phase05 tests and tests/receipts/phase05_*.json; for blocked statuses see CEP12-AUDT.log |
| AU311 | Native clip mute flag serialized and guarded | verified_offline | Phase05 tests and tests/receipts/phase05_*.json; for blocked statuses see CEP12-AUDT.log |
| AU312 | Native clip loop flag serialized and guarded | verified_offline | Phase05 tests and tests/receipts/phase05_*.json; for blocked statuses see CEP12-AUDT.log |
| AU313 | Native clip editing produced non-clipped real Mixdown | verified_hybrid_sesx_reopened | Phase05 tests and tests/receipts/phase05_*.json; for blocked statuses see CEP12-AUDT.log |
| AU314 | Immutable source and no overwrite clip recipe | verified_offline | Phase05 tests and tests/receipts/phase05_*.json; for blocked statuses see CEP12-AUDT.log |
| AU315 | FFmpeg voice sidechain-compression mix | verified_offline_ffmpeg | Phase05 tests and tests/receipts/phase05_*.json; for blocked statuses see CEP12-AUDT.log |
| AU316 | Measured 220Hz background ducking suppression | verified_offline_ffmpeg | Phase05 tests and tests/receipts/phase05_*.json; for blocked statuses see CEP12-AUDT.log |
| AU317 | Background music restoration after dialogue | verified_offline_ffmpeg | Phase05 tests and tests/receipts/phase05_*.json; for blocked statuses see CEP12-AUDT.log |
| AU318 | Ducked podcast 16 LUFS target mastering | verified_offline_ffmpeg | Phase05 tests and tests/receipts/phase05_*.json; for blocked statuses see CEP12-AUDT.log |
| AU319 | Voice/music source hash unchanged after mixing | verified_offline | Phase05 tests and tests/receipts/phase05_*.json; for blocked statuses see CEP12-AUDT.log |
| AU320 | Parse real Audition XMP Cue markers | verified_offline | Phase05 tests and tests/receipts/phase05_*.json; for blocked statuses see CEP12-AUDT.log |
| AU321 | Read 48 kHz marker frameRate and region duration | verified_offline | Phase05 tests and tests/receipts/phase05_*.json; for blocked statuses see CEP12-AUDT.log |
| AU322 | Export 2 sample-accurate chapters from native markers | verified_offline | Phase05 tests and tests/receipts/phase05_*.json; for blocked statuses see CEP12-AUDT.log |
| AU323 | Chapter fades and WAV readback | verified_offline | Phase05 tests and tests/receipts/phase05_*.json; for blocked statuses see CEP12-AUDT.log |
| AU324 | Non-destructive chapter no-overwrite guard | verified_offline | Phase05 tests and tests/receipts/phase05_*.json; for blocked statuses see CEP12-AUDT.log |
| AU325 | Session audit missing media and unresolved file ID | verified_offline | Phase05 tests and tests/receipts/phase05_*.json; for blocked statuses see CEP12-AUDT.log |
| AU326 | Session audit clip/fade range consistency | verified_offline | Phase05 tests and tests/receipts/phase05_*.json; for blocked statuses see CEP12-AUDT.log |
| AU327 | Session audit Bus cycles and dangling routes | verified_offline | Phase05 tests and tests/receipts/phase05_*.json; for blocked statuses see CEP12-AUDT.log |
| AU328 | Session audit high gain EQ safety gate | verified_offline | Phase05 tests and tests/receipts/phase05_*.json; for blocked statuses see CEP12-AUDT.log |
| AU329 | Write JSON session QA structural report | verified_offline | Phase05 tests and tests/receipts/phase05_*.json; for blocked statuses see CEP12-AUDT.log |
| AU330 | CEP Manifest AUDT host v11 and CSXS v6 corrected | verified_static_only | Phase05 tests and tests/receipts/phase05_*.json; for blocked statuses see CEP12-AUDT.log |
| AU331 | CEP Plugin host PlugPlugSetup internal error | blocked_host_runtime | Phase05 tests and tests/receipts/phase05_*.json; for blocked statuses see CEP12-AUDT.log |
| AU332 | CEP live panel and evalScript callback | cep_install_pending | Phase05 tests and tests/receipts/phase05_*.json; for blocked statuses see CEP12-AUDT.log |
| AU333 | Four-track clip duplication recognized by Audition | verified_hybrid_sesx_reopened | tests/receipts/phase06_native_arrangement_acceptance.json |
| AU334 | Native arrangement gains and sample-accurate offsets | verified_hybrid_sesx_reopened | tests/receipts/phase06_native_arrangement_acceptance.json |
| AU335 | Audition native 4-track Mixdown 199200 frames | verified_native_live | tests/receipts/phase06_native_arrangement_acceptance.json |
| AU336 | Clone clip ID uniqueness and fixture safety guards | verified_offline | tests/receipts/phase06_native_arrangement_acceptance.json |
| AU337 | Offline media refusal and non-overwrite arrangement | verified_offline | tests/receipts/phase06_native_arrangement_acceptance.json |
| AU338 | Safe restoration and closure of QA Audition documents | verified_native_live | tests/receipts/phase06_arrangement_closed.json |
| AU339 | XMP cue add move rename delete and native reopen | verified_hybrid_sesx_reopened | tests/receipts/phase06_native_xmp_edit_acceptance.json |
| AU340 | Audition transport play pause stop seek loop restoration | verified_native_live | tests/receipts/phase06_native_transport_acceptance.json |
| AU341 | Typed whitelist of 29 offline audio effect types | verified_offline | tests/receipts/phase06_effects_batch.json |
| AU342 | 17 independent FFmpeg audio effect renders | verified_offline_ffmpeg | tests/receipts/phase06_effects_batch.json;phase06_effects_second_batch.json |
| AU343 | Denoise declick declip chained repair audio | verified_offline_ffmpeg | tests/receipts/phase06_effects_batch.json |
| AU344 | Independent pitch and tempo output verification | verified_offline_ffmpeg | tests/receipts/phase06_effects_batch.json |
| AU345 | Gate and silence trim actual audio evidence | verified_offline_ffmpeg | tests/receipts/phase06_effects_second_batch.json |
| AU346 | FFmpeg EBU R128 momentary short term timeline | verified_offline_ffmpeg | tests/receipts/phase06_r128_timeline.json |
| AU347 | Integrated LUFS and true peak profile gate | verified_offline_ffmpeg | tests/receipts/phase06_r128_timeline.json |
| AU348 | BWF audio tags with description field roundtrip | verified_offline_ffmpeg | tests/receipts/phase06_tag_delivery.json |
| AU349 | MP3 ID3v2.3 tags with metadata roundtrip | verified_offline_ffmpeg | tests/receipts/phase06_tag_delivery.json |
| AU350 | Metadata codec copy and source hash preservation | verified_offline_ffmpeg | tests/receipts/phase06_tag_delivery.json |
| AU351 | End to end 10-step declarative audio production | verified_offline_ffmpeg | tests/receipts/phase06_production_bundle_acceptance.json |
| AU352 | Staged publication and failure rollback | verified_offline | tests/receipts/phase06_production_bundle_acceptance.json |
| AU353 | Input source hashes and output manifest integrity | verified_offline | tests/receipts/phase06_production_bundle_acceptance.json |
| AU354 | Dependency planning and forward reference guard | verified_offline | tests/receipts/phase06_production_bundle_acceptance.json |
| AU355 | Mastering metadata ducking R128 QC integration | verified_offline_ffmpeg | tests/receipts/phase06_production_bundle_acceptance.json |
| AU356 | Production plan/run through explicit confirmation | verified_offline | tests/receipts/phase06_production_bundle_acceptance.json |
| AU357 | Native QA arrangement command with dry run | verified_offline | tests/receipts/phase06_native_arrangement_acceptance.json |
| AU358 | Audition SESX audit and effects command routes | verified_offline | tests/receipts/phase06_production_bundle_acceptance.json |
| AU359 | CEP12 manifest AUDT25+ runtime CSXS12 schema validated | verified_static_only | tests/receipts/phase06_cep12_manifest_corrected.json |
| AU360 | PlugPlugSetup still failing after official CEP12 host correction | blocked_host_runtime | tests/receipts/phase06_cep12_relaunch_diagnostic.json |
| AU361 | Sample-accurate cut/delete and silence insertion | verified_offline | tests\receipts\phase07_waveform_timeline_acceptance.json |
| AU362 | Copy/paste original sample region at arbitrary frame | verified_offline | tests\receipts\phase07_waveform_timeline_acceptance.json |
| AU363 | Regional gain and fade editing | verified_offline | tests\receipts\phase07_waveform_timeline_acceptance.json |
| AU364 | Deterministic TPDF 16-bit dithering with seed | verified_offline | tests\receipts\phase07_float_to_pcm16.json |
| AU365 | First-order error-feedback noise shaping (non-Audition preset) | verified_offline | tests\receipts\phase07_float_to_pcm16.json |
| AU366 | Native Float32-to-PCM16 file readback | verified_offline | tests\receipts\phase07_float_to_pcm16.json |
| AU367 | Welch FFT 4096 window JSON frequency spectrum | verified_offline | tests\receipts\phase07_waveform_timeline_acceptance.json |
| AU368 | Sample-accurate Native SESX QA clip split and reimport | verified_hybrid_sesx_reopened | tests\receipts\phase07_native_split_acceptance.json |
| AU369 | Native Mixdown after clip split matches original samples | verified_native_live | tests\receipts\phase07_native_split_acceptance.json |
| AU370 | Native Track Fader gain change and peak readback | verified_hybrid_sesx_reopened | tests\receipts\phase07_native_track_controls.json |
| AU371 | MP3 and FLAC native WaveDocument open and close | verified_native_live | tests\receipts\phase07_native_mp3_flac_open.json |
| AU372 | Stereo split into L/R mono and zero-error rejoin | verified_offline | tests\receipts\phase07_channel_split_roundtrip.json |
| AU373 | Waveform Edit and FFT JSON pipeline actions | verified_offline | tests\receipts\phase07_waveform_pipeline_acceptance.json |
| AU374 | Four-step PCM editing FFT mastering and QC bundle | verified_offline | tests\receipts\phase07_waveform_pipeline_acceptance.json |
| AU375 | Thirty-one P0 items individually cross-referenced | verified_offline | tests\receipts\phase07_waveform_pipeline_acceptance.json |
| AU376 | Unique request nonce and cleanup for JSX transport | verified_offline | tests\receipts\phase08_transport_faults.json |
| AU377 | JSX error propagation and controlled timeout fault injection | verified_offline | tests\receipts\phase08_transport_faults.json |
| AU378 | FLAC and MP3 batches with isolated failures | verified_offline | tests\receipts\phase08_real_delivery.json |
| AU379 | Staged exclusive publish with codec, SHA256 and source immutability | verified_offline | tests\receipts\phase08_real_delivery.json |
| AU380 | Track arm and visibility native live toggle, restore and QA-only cleanup | verified_native_live | tests/receipts/phase09_native_acceptance.json |
| AU381 | Three-item QA native Favorites batch with output validation | verified_native_live | tests/receipts/phase09_native_batch_acceptance.json |
| AU382 | Three-item QA native sample-rate/bit-depth batch | verified_native_live | tests/receipts/phase09_native_batch_acceptance.json |
| AU383 | Cue and Subclip point/range native WAV persisted-reopen | verified_native_live | tests/receipts/phase09_native_markers.json |
| AU384 | Two-pass normalized LUFS batch with independent failure isolation | verified_offline | tests/receipts/phase09_offline_batch_acceptance.json |
