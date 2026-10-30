# Audition 26 第五轮集中开发与实机验收

日期：2026-10-10  
工程：D:\computer\Adobe\Audition  
版本：Adobe Audition 26.0.0.56

## 验收总览

| 项目 | 第四轮 | 第五轮 |
|---|---:|---:|
| 细分功能清单 | 306 | 332 |
| Controller 公开方法 | 64 | 72 |
| 正式单元测试通过 | 125 | 166 |
| 综合验收检查通过 | 18 | 26 |

最终 Audition 为 **0 个打开文档**。项目全程只写入独立 ACCEPT_AU_ 实验会话及合成音频输出，没有覆盖用户原始素材。

332 项是逐项开发／验收清单，并非 332 项都已完成。GUI、CEP、C++ SDK 和若干未实测能力仍有明确待验收状态。

## 一、原生剪辑高级操作与成片

模块：controller_modules/native_clip_advanced.py

方法：inspect_native_clips_advanced、patch_native_clip_advanced。

支持 clipMute、lockedInTime、looped、startPoint/endPoint、sourceInPoint/sourceOutPoint、Fade In/Out 的原生 SESX 修改，并具备安全输入校验、输出防覆盖、源文件 SHA-256 保持不变。

实际将源剪辑裁剪到 2000–80000 samples，移动至 48000 samples，设置 4000 samples 淡入、6000 samples 淡出。
Audition 原生重新打开后，读到开始 48000、时长 78000 samples；原生 Mixdown 输出 48000 Hz、126000 frames、2.625 秒无削波 WAV。

Clip Loop/Mute 等额外标志具备序列化修改与单元测试，但尚未对所有开关单独完成 Audition 输出行为验收。

证据：tests/receipts/phase05_native_clip_trim_fade_acceptance.json。

## 二、背景音乐自动压低与播客母带

模块：controller_modules/podcast_automation.py

方法：duck_music_under_dialogue、podcast_sidechain_delivery。

使用 **Debian FFmpeg** sidechaincompress、amix、alimiter 处理语音与音乐，实际输出 float WAV，并可进行两遍响度母带。
合成测试中，220Hz 背景音乐在旁白期间下降约 **12.93 dB**，结束后恢复；成品实测 **−15.96 LUFS**，目标 −16 LUFS。
输入合成媒体哈希保持不变，输出通过采样峰值与格式检查。

这是可复用的外部音频生产能力，不等于 Audition 内建实时侧链效果或 VST 插件控制。

证据：tests/receipts/phase05_ducking_and_mastering.json。

## 三、Audition 原生 XMP 章节标记提取与精确切割

模块：controller_modules/chapter_lab.py

方法：native_sesx_markers_xmp、export_native_marker_chapters。

Audition 原生多轨 Cue Marker 实际位于 /sesx/session/xmpMetadata 中的内嵌 xmpDM:Tracks XML，包含 frameRate、startTime、duration、name 和 guid，而不是普通 marker 标签。

实测两个 QA Marker：起点 48000 / 时长 48000 samples，以及起点 95000 / 时长 10000 samples。基于 Audition 已导出的 Native Mixdown，通过 SciPy 精确导出 48000 帧和 10000 帧的两份独立 WAV，并验证源哈希、Fade、输出格式和帧数。

证据：tests/receipts/phase05_xmp_chapter_acceptance.json。

## 四、Native SESX 结构化预检

模块：controller_modules/session_integrity.py

方法：audit_native_session、write_native_session_audit。

检查媒体存在性、fileID 唯一性与 Clip 引用、Bus 环路与失效输出、Clip 可播放时长和源时长一致性、Fade 越界、潜在危险的私有 EQ Gain、轨道重叠和 XMP Marker 时间有效性。

通过合成的媒体丢失、错误 fileID、时长不一致、Fade 越界、Bus 循环及异常 Gain 场景验证均能标记异常。
正常第五轮工程通过检查，生成 JSON 审计收据。

注意：它是结构预检，并不能保证第三方 VST、声音主观质量或视频同步都正确。

证据：tests/receipts/phase05_session_preflight.json。

## 五、CEP 加载故障的兼容性修复与未解决项

经比较本机 Audition 2026 自带 Portal / Onboarding CEP 清单，发现官方内部使用 AUDT 11.0 和 CSXS 6.0，而我们先前使用了不匹配的 AUDT 26.x 宿主范围。

已备份旧 CEP 清单，并更新自定义扩展为 AUDT Version=11.0、CSXS Version=6.0、Manifest Version=6.0；用户级安装副本与源文件哈希一致。

确认 0 个文档后正常重启 Audition，重新检查 Window → Extensions 和 CEP12-AUDT.log。重启后仍出现 PlugPlugSetup/PlugPlugAddEventListener internalError，且 Inspector 不显示，因此 **CEP 宿主加载仍未通过**。不能把清单修复认作插件运行成功。

证据：tests/receipts/phase05_cep_manifest_correction.json 和 phase05_cep_host_diagnostic.json。

## 六、回归与工程管理

- 本轮新增 test_phase05_clips_duck_xmp.py：30 项。
- 新增 test_phase05_session_integrity.py：11 项。
- 全部累计：**166/166 项通过**。
- 综合检查：**26/26 项通过**。
- API：72 个 Controller 公共方法、332 个功能条目。
- 原生菜单命令保持第四轮真实发现的 474 条快照，不因最近打开的文件列表变化而虚增 SDK 数目。
- 原生 Bus 删除仍存在接口报错，已保留经实机验证的 SESX 安全替代方案。

文件路径：
- audition_controller.py：唯一 Controller 入口。
- controller_modules/：功能模块，不作为用户直接调用入口。
- api/：API 方法、原生命令清单、完整覆盖矩阵与第四轮冻结基线。
- tests/fixtures、tests/native_outputs、tests/receipts：隔离素材、真实成品与哈希收据。
- docs/：本报告。
- backups/：源码和修复前 CEP Manifest 备份。
- archives/：一次性探测脚本压缩归档。
- maintenance/：可重建目录与最终验收的长期维护脚本。

日常命令：

    cd D:\computer\Adobe\Audition
    python -B maintenance\rebuild_phase05_catalog.py
    python -B maintenance\verify_workspace.py --sdk --full-tests

## 仍需要的条件

原生 Bus 删除方法、CEP PlugPlug 宿主、复杂实时 VST/效果机架、AMIO/Control Surface C++ SDK 编译与装载，均没有被本轮虚报成已验收。后续应优先解决宿主接口阻塞及实际 GUI/硬件验收。
