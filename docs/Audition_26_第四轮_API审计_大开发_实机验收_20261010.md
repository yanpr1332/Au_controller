# Audition 2026：第四轮大开发、API 全量核查与实机验收

日期：2026-10-10
工程目录：D:\computer\Adobe\Audition
宿主版本：Adobe Audition 26.0.0.56
控制器：audition_controller.py

## 本轮结论

第三轮结束时：103 项正式测试、原生 Bus 删除受阻、功能基线 267 项。
第四轮完成时：**125/125 测试通过，18/18 实证门禁通过**。

- 接口和功能审计已扩展为 **306 个细分功能点**，其中包含尚未验证的项目，绝非 306 项功能全部完成。
- AuditionController 当前 **64 个公开方法**，统一挂载到唯一入口，模块内部按功能职责拆分。
- Win32 原生命令目录真实枚举 **474 个条目、473 个不同命令 ID**。
- 本轮新增真实 SESX Bus 删除替代方案、会话自包含打包、Native EQ 保守修改、原生命令发现和配套 API。
- 最终 Audition：0 个打开文档；全部 QA 使用测试素材，源文件没有被覆盖。

## 1. 原生菜单 API 自动发现

- controller_modules/native_menu_registry.py
- api/Audition_26_native_menu_registry.json
- api/Audition_26_原生菜单命令目录.md

读取实际 Win32 Menu，包含 File、Edit、Multitrack、Clip、Effects、Favorites、View、Window、Help 的命令 ID。
菜单条目只是“存在”，不等于有独立的 ExtendScript 接口，更不代表该命令已通过端到端效果测试。

## 2. 原生 Bus 删除问题与替代方案

真实 Audition 26 原生 audioBusTracks.add 可以创建 Bus；audioBusTracks.remove(BusObject) 对本机测试 Bus 返回：
Error: The object is invalid。

新增 remove_unused_bus_sesx：
- 只操作新的、独立的 SESX 副本；
- 必须匹配完整的 QA Bus 名称；
- 若 Bus 被任何其他会话节点的 ID 引用，拒绝删除；
- 若包含剪辑，拒绝删除；
- 删除后检测音轨路由是否循环或失效；
- 原始源文件哈希不变。

**真实验收**：Audition 重新打开删去无用 Bus 的工程，读回 6 条音轨、1 条 Bus、2 条标记。详见 tests/receipts/phase04_native_bus_prune_reopen.json。

注意：这是一种 **SESX 安全替代方案**，不是原生 audioBusTracks.remove 现已修复。

## 3. 多轨工程自包含打包

新增 controller_modules/native_sesx_portability.py：
- create_qa_session_package
- verify_qa_session_package

自动复制 SESX 引用的媒体到 media/，重写绝对路径及相对路径，生成 MANIFEST.json 与逐文件 SHA-256。
拒绝用户媒体路径和覆盖已有目录；默认仅在独立 QA 目录执行。

**实机证明**：打包的多轨会话在 Audition 中成功打开，重新链接的音频可用，原生 Mixdown 产出 48 kHz / 32-bit Float、139200 帧的非静音 WAV。

证据：tests/receipts/phase04_native_portable_bundle_acceptance.json。

该验证说明包在当前目录可用，尚未跨电脑或跨磁盘验证随意搬迁的相对路径回退；不能超范围声称完全可移植。

## 4. 原生轨道 EQ 参数与成片

新增 controller_modules/native_eq.py：
- inspect_native_eq
- patch_native_eq_normalized

从真实 SESX 1.9 trackEQ 组件读取支持的 Band 1–5、Shelf、高低通等序列化字段。
需要注意：**这些值是 Audition 内部归一化参数，不是直接以 dB 或 Hz 为单位的数值**。

第一次 QA 测试用 Band 3 Gain=0.95，实际浮点音频峰值约 **+26.43 dBFS**，存在严重超范围风险。
已立刻关闭测试会话、删除这些异常测试音频及会话副本，并保存异常原因收据。
因此代码禁止未校准的 Gain 远离中性 0.5（现临时限制在 0.49 到 0.51）。

第二次保守测试用 Gain=0.51：Audition 原生导出后峰值约 -15.28 dBFS，较未开启 EQ 的基线增加 **0.84 dB**，且无高于 -1 dBFS 的风险。
开启原生 EQ 还导致约 8192 帧的额外尾长，已写入验收规则。

证据：
- tests/receipts/phase04_real_eq_render.json
- tests/receipts/phase04_eq_unsafe_gain_rejected.json
- tests/receipts/phase04_eq_final_clean.json

## 5. CEP 宿主验证

官方 Adobe Audition 确认支持 CEP HTML/JS 面板。
已完成：
- 只读 CEP Inspector 的 CSXS manifest、HTML/JS；
- Node JS 语法与 XML 解析检查；
- 将面板复制到 C:\Users\LENOVO\AppData\Roaming\Adobe\CEP\extensions\com.openai.audition.inspector；
- 对比源和用户级扩展目录中的每个文件哈希；
- HKCU 已有 CSXS.11、CSXS.12、CSXS.13 的 PlayerDebugMode=1，未额外更改；
- 当 Audition 为 0 个打开文档时正常退出并启动，重新扫描扩展。

**当前未通过**：没有 phase04_cep_host_loaded.txt 宿主握手回执；读取的 Window → Extensions 子菜单目前为空。
CEP12-AUDT.log 提示 PlugPlugSetup / AddEventListener 内部错误，尚不能确定是清单、宿主初始条件还是其他扩展问题。CEP 的“插件已部署”不算“面板在宿主里已运行”。
保留面板源码及已安装目录以供下轮排查。

参考：
https://helpx.adobe.com/audition/desktop/applying-effects/enabling-cep-extensions.html
https://github.com/Adobe-CEP/CEP-Resources

## 6. API 清单和验收分级

- api/Audition_26_API_接口目录.md：基础和 Multitrack 实际反射对象、Controller 全部公开方法。
- api/Audition_26_原生菜单命令目录.md：474 条原生命令 ID。
- api/Audition_26_全功能开发矩阵.md：306 项细分功能、真实验收状态及路径。
- api/Audition_26_runtime_api.json：机器可读的 API 对象和方法。
- api/Audition_26_feature_ledger.json：机器可读的完整功能清单。
- api/Audition_26_phase01_baseline_267.json：冻结的最初 267 项功能基线，便于精确重建。

其中 Native DOM、SESX 经实机重新打开、FFmpeg 离线、GUI/CEP 待验收、C++ SDK 依赖均使用独立状态。
不要把“所有常见功能都已列出”理解为“Adobe 公开了全部 C++ API”或“所有功能全部开发完成”。

## 7. 工程结构与命令

统一入口：audition_controller.py
功能源码：controller_modules/ 
正式单元测试：tests/test_*.py
真实素材、音频成片、SESX 与 JSON 证据：tests/
CEP Inspector：cep/
完整接口目录：api/
开发报告：docs/
源代码快照：backups/
历史探测脚本压缩包：archives/
维护入口：maintenance/rebuild_phase04_catalog.py 与 maintenance/verify_workspace.py

PowerShell:
    cd D:\computer\Adobe\Audition
    python -B maintenance\verify_workspace.py --sdk --full-tests
    python -B maintenance\rebuild_phase04_catalog.py

## 8. 后续开发的主要瓶颈

1. CEP 12/AUDT 宿主面板的菜单注册与实际打开问题。
2. AMIO C++ SDK、Control Surface SDK 的头文件及原生编译/装载。
3. 高级音频效果器的真实参数—单位映射和完整效果器运行时回读（尤其不能未经校准直接放宽 Gain）。
4. SESX 自包含包跨机器/跨盘移动验证，进一步补齐复杂媒体格式和轨道发送关系。
5. 高质量播客动态 Ducking、多轨轨道效果机架与视频参考同步的 GUI 或原生控制。

本轮对用户既有工程未做删除和覆盖。所有实测写入均为 ACCEPT_AU_ 隔离测试对象。
