# 第十六轮实测

## OMF 原生导出后重新导入

将第十五轮导出的 OMF 通过已安装 Au 的文件打开入口交给宿主，成功进入封装媒体解包对话框。Computer Use 指定新目录 tests/native_outputs/ACCEPT_AU_Phase16_OMF_Extract 后，Au 成功打开多轨 OMF。

只读 DOM 证据：tests/receipts/phase16_omf_snapshot_20261030T104926652222.json。

四条非空音频轨道的名称、片段数量、起点及长度保留：起点分别为 24000、48000、84000、0 样本；每片段长度 115200 样本。源中两条空音频轨被跳过；总线不属于保留范围。四个片段显示名称均合并为同一 QAclone3 名称，不能称元数据无损。尚未进行导入后混音音频差分，不声称完整音频等价。

脚本 openDocument 路径仍报 File does not exist，而文件入口能正确导入，故错误限定于脚本路径，不能当作 Au 不支持 OMF。

## CEP

真实 GUI 中 Window > Extensions 已出现 Audition API Inspector，点击后创建面板，但持续白屏。两个新生成的 Inspector 日志无可读错误文本。本轮只修复工程源码 panel.js 的零文档 activeDocument 访问；尚未部署这个修改到用户扩展目录，未取得宿主 evalScript 成功证据。

## 回归

受限执行的完整回归因历史包、Favorites.xml 访问及音频服务调用失败；桌面用户权限下重跑 384/384 通过，131 个公开方法、14 个历史输出哈希有效。收据 tests/receipts/phase11_verification_20261030T104923576048.json。

本轮未录音，未修改源媒体。频谱画笔/套索、CEP 运行时、Premiere 音画往返、硬件驱动与签名发布仍未完成。all_requested_development_complete=false。
