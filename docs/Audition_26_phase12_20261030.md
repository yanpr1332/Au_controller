# 第十二轮：控制设备软件层与剩余阻塞

本轮实现 WinMM MIDI 输入/输出设备枚举、ASIO 注册驱动枚举、MIDI 通道消息编解码、限时输入监听和控制消息发送。发送和监听默认只规划；实际访问设备需显式 confirm=True。接口位于 controller_modules/control_surface.py。

运行 `python -B audition_controller.py control-devices` 查看设备。ASIO 名单来自 Windows 注册信息，只表明驱动注册，不表示 Audition 已选用或成功打开。

本次本机检测：MIDI 输入0个，MIDI输出为 Microsoft GS Wavetable Synth，ASIO驱动0个。未向合成器发送消息；未完成HUI/Mackie协议、设备与Au的状态同步、推子回读、ASIO切换/录音验收。新增5项测试覆盖消息编解码、参数范围、干运行不打开设备及无输入设备的错误；无实物设备不应视为硬件验收通过。

重新尝试桌面控制后，工具仍在初始化阶段返回 `failed to prepare MXC sandbox: permission path cannot be represented losslessly`。因此 CEP 面板交互、频谱画笔/套索、OMF导出对话框和 Premiere 界面往返仍未完成。CEP调试开关已是启用状态，扩展文件存在；不能据此宣称面板加载成功。

AAF转换、完整Premiere往返、ASIO宿主设备设置、HUI/Mackie双向控制、第三方签名与对外发布均未实现或验收。不得把原始MIDI CC发送称为已完成硬件控制台协议。

本轮全量软件回归371/371通过，收据 tests/receipts/phase11_verification_20261030T025433111918.json。此收据复用第十一轮原生Au证据，没有在本轮重新实测Au或Premiere。此前真实麦克风录音已停止，未再次采集。
