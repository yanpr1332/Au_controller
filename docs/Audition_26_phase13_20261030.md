# 第十三轮开发记录

Remote Desktop Commander 已连接设备 LAPTOP-ND3M1731。其可用工具覆盖文件、搜索和进程，但没有桌面截图、鼠标或对话框控制接口。它不能替代此前未能启动的桌面控制工具；不将连接成功计作 GUI 功能验收。

新增 `mux_video_audio`，将视频画面流与指定音频用本机 WSL Debian FFmpeg 合成到新的 MP4/MOV，支持音频偏移、独占发布、输入哈希和音视频流及时间戳检查。默认只规划，实际执行需 `confirm=True`。CLI：

```powershell
python -B audition_controller.py mux-video video.mp4 audio.wav output.mp4 --offset 0.25
```

末尾添加 `--confirm` 才实际写入。此功能是离线交付，不是 Audition 或 Premiere 原生往返。音频编码为 AAC，编码器延迟会影响实际起点；代码以0.06秒容差校验并报告实际起点，不宣称样本精度同步。

使用合成 H.264 视频和合成 WAV 实测：指定偏移0.25秒，输出相对起点0.228秒，视频H.264、音频AAC、输入哈希不变。收据 `tests/receipts/phase13_video_20261030T030239.json`。

最终复验：374/374自动化测试通过，Au 26.0.0响应且零文档，原96个接口保留；共129个公开方法。收据 `tests/receipts/phase11_verification_20261030T030445699427.json`。该复验保留第十一轮已存原生实证，并不把视频离线合成认作 Premiere 往返。

尚未完成：CEP宿主面板、频谱画笔/套索及局部修复、原生OMF导出和Premiere往返、AAF转换、ASIO设备切换与硬件验收、HUI/Mackie控制台协议及真实设备双向同步、证书签名发布。此前检测无ASIO驱动及MIDI输入设备。
