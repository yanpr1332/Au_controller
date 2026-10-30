# 第十一轮开发及本地 Au 实机验收

日期：2026-10-30。本机 Adobe Audition 26.0.0。当前123个公开接口，原96个接口名称保留。第九轮384条功能台账和107项未完整验收是历史冻结数据，没有把本轮新增接口数量冒充全功能完成率。

## 已实现并取得本地 Au 证据

| 能力 | 实际验证 | 收据（tests/receipts 下） |
|---|---|---|
| 批量 WAV 导入、创建轨道 | Au 回读7条轨道，新轨1个片段，原轨2个片段；原生混音48kHz、275200帧 | phase11_native_20261030T015310.json |
| 原生音量包络 | 使用 Au SDK 保存的 parameterKeyframes 模型；原生渲染后段 RMS 0.08326、前段0.00748 | phase11_automation_20261030T020936.json |
| Pan 校准 | 新接口把-1..1位置映射为原生-100..100百分比；全左/全右的另一声道均为零 | 同上 |
| 发送总线 | 原生 Send Slot、前后推子标志和反馈环校验；测试发送使 RMS 从0.06963升到0.08704 | 同上 |
| 原生效果架 | 使用本机真实 DeHummer 预设；保存并重开后，60Hz/1kHz幅度比由0.6降至0.000580 | phase11_rack_20261030T021617.json |
| Rack 顺序、旁通与预设 | 复制原生Slot、重排两槽、旁通一槽、导出JSON预设并重新应用；Au原生渲染仍取得相同工频抑制 | phase11_rack_surround_20261030T022213.json |
| 原生5.1 | SDK创建6声道会话，保存SESX、关闭重开，原生WAV输出6声道；中心有信号，其余五路为零 | 同上 |
| 工程包迁移 | 旧绝对路径暂时不可用时，移动后的工程依靠相对路径在 Au 重开并成功混音 | phase11_relocation_20261030T021109.json |
| 生产 Favorite 副本处理 | 对私有输入副本执行 Au Normalize；新输出峰值-3.011dBFS，原始输入哈希不变 | phase11_native_favorite_ACCEPT_AU_Favorite_20261030T022612.json |
| 默认麦克风真实录音 | 经用户明确授权，约1秒采集窗口实际保存0.64秒、48000Hz、30720帧float32音频；录音已停止、Arm已解除 | phase11_microphone_20261030T023932.json |

效果器可能带来尾音，不能假定处理后帧数与输入完全相同。5.1测试证明软件渲染与基础路由，不证明六扬声器回放或5.1视频往返。

## SDK真实构建与部署

从Adobe官方提供的 AMIO/Session SDK 8.1x160 下载包构建，不是同名占位接口。

- 下载包SHA256：67271d6d67b48bccbff9c45f943a225aec86604dcd9587c967820e556c344bee。
- 官方AMIO APE示例已在本机MSVC v145编译成功，产物位于 sdk/AMIO_8.1x160/Amio/Windows Sample/AmioApe/Release/64/AmioApe.dll。修复旧示例标准头文件和资源头依赖；不把厂商随附 Sample Binary 当作本次构建产物。
- 自有 Session SDK 桥：sdk/session_bridge/bridge.cpp，产物 ControllerSessionBridge.ases，已安装到本机Au PlugIns/Session，并在宿主 SessionPlugInInfoCache 中发现。
- .auctl清单经过Python验证，原生SDK负责创建真实轨道、关键帧、Send、Rack和会话布局。不能把它描述为无依赖的JSON/XML模拟Au。
- 旧插件版本保存在 sdk/session_bridge/previous_builds。尚未进行证书签名和对外分发。

官方来源：[Adobe SDK说明及下载入口](https://community.adobe.com/questions-544/welcome-to-the-audition-developer-and-sdk-forum-159958)。SDK较旧，本轮兼容范围由上述Au26实测限定。

## 其他已实现的软件能力

- search_session_media：限定目录和扫描数量，按名称和可选SHA256找候选；保留歧义，绝不自动选错素材。
- import_production_wavs：按采样率和轨道布局检查WAV，支持现有轨道或新建轨道；当前要求存在相同布局的原生模板，不宣称所有编码均可导入。
- run_resumable_production：与原生产链共用执行器，逐步保存中间产物、配方和输入哈希；中断后验证缓存再跳过已完成步骤，损坏缓存或输入变化会拒绝恢复。异常回滚发布结果；不宣称进程在多文件发布过程中被强杀仍可完全自动恢复。
- 原始输入和工程采用输出副本策略。复制片段/轨道时生成新的组件GUID。
- CLI已补齐import-wavs、native-edit、sdk-session、resume-production、media-search、native-favorite、rack-export和record-qa。

## 反复弹窗的处理

恢复提示的旧索引已在Au正常退出后备份并移走；原恢复目录和临时数据未删除。备份：backups/recovery_archive_20261030T020158605824。重启后Au正常响应，后续真实SDK测试已成功执行。

重启逻辑不再固定等待两秒，改为持有原进程句柄等待其真正退出。更新插件后只允许显式单次启动。Controller的脚本请求现在要求Au已经运行，不会在宿主缺失时通过-r隐式启动，从代码层面防止反复拉起新实例。

零文档时不再读取无效activeDocument对象。原生混音使用saveAs(..., false)，等待保存并显式激活、关闭自己的暂存结果，再解码发布；不会把异步保存返回true当作文件已可读。

## 仍未完成：不能标为全量交付

- CEP宿主日志仍有User profile empty。扩展已被发现不等于面板、evalScript回调、WebSocket生命周期完成实测。
- 频谱修复画笔、套索和明确区域选择的GUI控制尚未完成。整段Auto Heal实测使误差扩大，收据 phase11_autoheal_20261030T022449.json 保留为失败证据；生产Favorite接口已禁止这种整段调用。
- OMF的saveAsDocument和exportDocument均返回invalidFilenameExt=true。Au官方确有GUI导出OMF，但当前这两条脚本路径不支持，不能声称已完成OMF往返。
- Premiere/视频同步回放与完整音画往返尚未完成。AAF不属于已证明可用的Au原生导出路径，不能仅添加AAF方法名冒充实现。
- 未发现ASIO驱动或MIDI输入设备。ASIO切换/端口映射、控制台双向消息与推子回读尚未实现和验收。默认Realtek录音成功不能替代这些能力。
- 对外证书签名与发布未完成。

桌面控制工具曾在初始化时返回 failed to prepare MXC sandbox: permission path cannot be represented losslessly。核心原生脚本和SDK已绕开对此工具的依赖，但上述GUI交互仍缺少可用的控制路径。

官方交换格式说明：[保存与导出](https://helpx.adobe.com/nl/audition/desktop/saving-and-exporting/saving-exporting-files1.html)。不要把转码结果称作Au原生OMF/AAF或Premiere往返。

## 复验

```powershell
python -B maintenance/verify_workspace.py --sdk --full-tests
```

以最新 phase11_verification_*.json 为准。检查通过的含义是软件回归与表中明确范围通过，不表示上面的剩余项已经完成。全接口签名见 api/Audition_26_phase11_api.json。

录音文件仅保存在隔离测试目录；未播放、转录或上传。实际录音接口默认只规划，执行必须有明确采集授权并传confirm=True。
