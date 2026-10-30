# Audition 第七轮 P0 历史能力证据映射

原审计 P0 31 项，其中 22 项依据限定范围的证据升级。
注意：某些仅证明存在安全边界或静态只读操作，并不代表全部 GUI 功能。

| 原 ID | 功能 | 旧状态 | 当前状态 | 证据 |
|---|---|---|---|---|
| AU006 | 只读命令枚举 | not_verified | verified_readonly_host | api\Audition_26_native_menu_registry.json |
| AU008 | 原生命令调用 | not_verified | verified_native_live | tests\receipts\phase07_native_mp3_flac_open.json |
| AU009 | 事件订阅 | not_verified | not_verified | 仍待专项验证 |
| AU010 | 停止播放 | not_verified | verified_native_live | tests\receipts\phase06_native_transport_acceptance.json |
| AU011 | 未保存检测 | not_verified | verified_native_live | tests\receipts\phase07_native_mp3_flac_open.json |
| AU012 | 安全任务超时 | not_verified | not_verified | 仍待专项验证 |
| AU058 | DeReverb | existing_legacy_recheck | existing_legacy_recheck | 仍待专项验证 |
| AU088 | Track EQ | existing_legacy_recheck | verified_hybrid_sesx_reopened | tests\receipts\phase04_real_eq_render.json |
| AU112 | Track arm | existing_legacy_recheck | existing_legacy_recheck | 仍待专项验证 |
| AU113 | Track visibility | existing_legacy_recheck | existing_legacy_recheck | 仍待专项验证 |
| AU114 | Track fader | existing_legacy_recheck | verified_hybrid_sesx_reopened | tests\receipts\phase07_native_track_controls.json |
| AU115 | Track pan | existing_legacy_recheck | existing_legacy_recheck | 仍待专项验证 |
| AU117 | Clip gain | existing_legacy_recheck | verified_hybrid_sesx_reopened | tests\receipts\phase06_native_arrangement_acceptance.json |
| AU118 | Clip fade in | existing_legacy_recheck | verified_hybrid_sesx_reopened | tests\receipts\phase05_native_clip_trim_fade_acceptance.json |
| AU119 | Clip fade out | existing_legacy_recheck | verified_hybrid_sesx_reopened | tests\receipts\phase05_native_clip_trim_fade_acceptance.json |
| AU157 | Favorite batch | existing_legacy_recheck | existing_legacy_recheck | 仍待专项验证 |
| AU253 | 安全工作区 | not_verified | verified_offline | tests\receipts\phase07_waveform_timeline_acceptance.json |
| AU254 | 备份 | not_verified | verified_offline | tests\receipts\phase07_waveform_pipeline_acceptance.json |
| AU255 | 源文件只读 | not_verified | verified_offline | tests\receipts\phase07_waveform_timeline_acceptance.json |
| AU256 | 拒绝覆盖 | not_verified | verified_offline | tests\receipts\phase07_waveform_timeline_acceptance.json |
| AU257 | 路径预检 | not_verified | verified_offline | tests\receipts\phase07_waveform_timeline_acceptance.json |
| AU258 | 超时处理 | not_verified | not_verified | 仍待专项验证 |
| AU259 | 文件 SHA256 | not_verified | verified_offline | tests\receipts\phase07_waveform_timeline_acceptance.json |
| AU260 | 输出后解码 | not_verified | verified_offline | tests\receipts\phase07_channel_split_roundtrip.json |
| AU261 | 固定测试波形 | not_verified | verified_offline | tests\receipts\phase07_waveform_timeline_acceptance.json |
| AU262 | 日志清单 | not_verified | verified_offline | tests\receipts\phase07_waveform_timeline_acceptance.json |
| AU263 | 操作错误报告 | not_verified | not_verified | 仍待专项验证 |
| AU264 | 自动回归 | not_verified | verified_offline | tests\receipts\phase07_waveform_pipeline_acceptance.json |
| AU265 | 恢复说明 | not_verified | verified_offline | tests\receipts\phase07_waveform_pipeline_acceptance.json |
| AU266 | 使用文档 | not_verified | verified_offline | tests\receipts\phase07_waveform_pipeline_acceptance.json |
| AU267 | API 动态发现 | not_verified | verified_readonly_host | api\Audition_26_native_menu_registry.json |
