# Adobe Audition 2026：首轮全功能 API 盘点与集中开发验收

日期：2026-10-09
设备：Windows 11 / Audition 26.0.0.56 / WSL Debian FFmpeg 7.1.3
工程目录：D:\computer\Adobe\Audition

## 一、现有基础与项目保护

- 已继承原有 audition_controller.py，并保留既有 WaveDocument、Favorite、Multitrack、LUFS、Win32 辅助及 SESX 功能。
- 开始改动前完整备份原控制器与原始 7 份 JSX/说明至 backups/audition_pre_new_dev_20261009_210052.zip。
- 创建只含合成正弦波的测试素材；所有本轮原生写入保存在 tests/native_outputs。
- Audition 实机末态：26.0.0，0 个打开的文档。未覆盖用户素材。
- 脚本当前采用主控制器 AuditionController + controller_modules 模块化实现，避免单体巨大源码。

## 二、API 实地发现与边界

通过 Audition ExtendScript 动态反射，确认 11 类可观察对象/参数类型，详见 api/Audition_26_API_接口目录.md：
Application、WaveDocument、Transport、AudioFormat、AudioFileFormat、Metadata、Marker、
Preferences、DocumentOpenParameter、SampleTypeConvertParameters、WaveDocumentSaveAsParameters。

实际 Application 对象：8 个方法、10 个属性；WaveDocument：10 个方法、18 个属性；
Transport：7 个方法、7 个属性。
这些包括 app.invokeCommand、app.isCommandEnabled、app.openDocument、
WaveDocument.addMarker、applyFavorite、saveAsDocument、Transport.play/stop 等。

主要开发通道：
1. Audition ExtendScript（本机动态反射、真实调用）。
2. Audition CEP JavaScript / ExtendScript 面板（已写只读检查原型，未部署验收）。
3. Win32 原生命令辅助（保留此前已确认菜单 ID，不等同完整 GUI 自动化）。
4. SESX XML 文件变更（离线会话修改，必须经 Audition 重新打开才算原生验收）。
5. Audition AMIO C++ 文件/会话 SDK（官方支持，尚未获得本机 SDK 头文件和编译环境验收）。
6. Control Surface C++ SDK（需要相应 SDK、仿真环境或设备）。
7. Python SciPy / Debian FFmpeg 离线音频处理（不冒充 Audition 内置效果器）。

注意：本目录是已实例化 DOM 的完整反射列表，不意味着已获得全部未公开或需单独下载的 SDK 接口。
也没有在未打开原生多轨会话的情况下编造 MultitrackDocument 方法。

参考：
- https://developer.adobe.com/audition/
- https://helpx.adobe.com/uk/audition/desktop/applying-effects/enabling-cep-extensions.html
- https://github.com/Adobe-CEP/Samples/tree/master/Audition
- https://community.adobe.com/t5/audition-discussions/extendscript-for-audition-is-there-an-api-reference/td-p/12758550

## 三、267 项功能矩阵

- api/Audition_26_全功能开发矩阵.md：完整逐项表格。
- api/Audition_26_feature_ledger.json：机器可读 ID、路线和当前状态。
- api/Audition_26_runtime_api.json：11 类原生对象、35 个 Controller 方法、已知命令探测。

当前严格分布：
- 16 项：verified_native_live，本机 Audition 原生已操作成功。
- 42 项：verified_offline，独立 Python、DSP、FFmpeg 等路径下已验证。
- 20 项：existing_legacy_recheck，旧 Controller 已有实现，需要重新专项验收。
- 93 项：ui_or_media_pending，需要 GUI/特殊工程/真实效果回读。
- 72 项：not_verified，尚无完整实验收据。
- 12 项：cep_install_pending，面板、事件和宿主启动待验证。
- 12 项：sdk_or_hardware_required，AMIO、Control Surface 等外部开发前提。

这 267 项是用于自动化开发的细分功能清单，不应理解成“267 条官方 SDK 方法”。

## 四、本轮原生 Audition 实测

1. app.status、app.openDocument、app.closeDocument；WaveDocument 与 Application 对象反射。
2. WaveDocument.addMarker：成功新增 Native QA Cue，保存 WAV，再次打开仍读回 MARKERS=1、NAME=Native QA、START=48000。
3. Favorite Normalize to -3 dB：原生执行成功；峰值从约 -16.12 dBFS 变为 -3.01 dBFS。
4. WaveDocumentSaveAsParameters + SampleTypeConvertParameters：真实生成 44.1 kHz/24-bit WAV 与 96 kHz/24-bit WAV；独立 FFprobe 识别为 pcm_s24le，对应采样率正确。
5. 关闭所有测试文档后 Audition 文档数为 0，未触碰用户文件。
6. 应用只读命令状态探测：Select All、Copy、Insert Silence 等实际值留在 api/audition_26_object_reflection.json。

## 五、首轮新功能模块

- controller_modules/audio_dsp.py：重采样、增益、裁剪、淡入淡出、反转、Mono/Stereo、EQ IIR、工频陷波、去 DC、门限、压缩、限制、边声道增益；独立频谱分析与安全输出。
- controller_modules/native_safe.py：受保护的原生 Marker、Favorite、采样格式转换与只读命令接口。
- controller_modules/ffmpeg_audio.py：WSL Debian FFmpeg/FFprobe 与格式输出，原生编码回读及哈希。
- controller_modules/sesx_lab.py：离线 SESX 轨道、Clip、EQ、声像、时间点、Fades 等 9 类修改及结构检查。
- controller_modules/batch_lab.py：批量音频处理、输出 QA、输入哈希校验、活动区间检测。

全部由 audition_controller.AuditionController 统一暴露；目前可反射到 35 个公开方法。

## 六、本轮离线 DSP 与格式验收

- Python/SciPy：16 个核心音频模块单测通过；增益、转换、裁剪、滤波、峰值、淡入淡出、基础门限压缩、参数有效性及防覆盖均检查。
- 三条不同合成音频批量处理：3/3 成功，输入哈希前后相同。
- 16 kHz 测试音频生成成功，活动区间检测识别出两段活动波形。
- Debian FFmpeg 实际生成 FLAC、MP3、AAC/M4A、OGG Vorbis、Opus；FFprobe 验证 codec/sample rate/channel，均成功。
- 旧有 LUFS 程序基于 BS.1770 风格估算，本轮未做标准测试信号的 EBU R128 独立校准，不应误认等同于专业认证测量。

## 七、未能算作本轮原生成功的内容

- SESX：9 类离线 XML 修改与回读成功，但是从结构化模板创建，并未在 Audition 中原生重新打开。
- CEP：已在 cep/com.openai.audition.inspector/ 下制作只读面板样例；manifest.xml XML 检查和 panel.js Node 语法检查通过，未安装、加载或进行宿主实际交互。
- AMIO / Control Surface：本机尚无 SDK C++ 完整头文件、示例编译及宿主装载收据。
- MultitrackDocument：当前实际运行时没有原生多轨文档，未全量反射这一对象，仍是下一轮重点。
- GPU/高级降噪/频谱细选/复杂插件参数/自动配音等 GUI-only 功能，需具备对应界面自动化和独立质量验证，不能仅借助 DSP 假定等效。

## 八、验收与后续路线

本轮总验收：35/35 项 Python 单元测试，17/17 项证据门禁全部通过。

关键收据：
- tests/receipts/phase01_final_acceptance.json
- tests/receipts/phase01_audition_native_acceptance.json
- tests/receipts/phase01_native_marker_resample_verified.json
- tests/receipts/phase01_ffmpeg_acceptance.json
- tests/receipts/phase01_batch_dsp_acceptance.json
- tests/receipts/phase01_sesx_offline_acceptance.json

建议下一轮优先：
1. 安全生成真正的隔离 MultitrackDocument 并反射整个轨道/Clip/Bus API；
2. 部署并在 Audition 实际验收 Script Dictionary 与 CEP 宿主通信；
3. 区分并实现 GUI 效果链参数、音频修复与真实波形回读；
4. 验证真实 SESX 打开/保存/效果与 Clip 曲线；
5. 获取 AMIO 与 Control Surface SDK 并建立原生编译/加载清单。

注意：项目持续保留旧有 scripts/ 与旧 Controller 功能，本轮没有删除用户已有的配方或安装文件。
