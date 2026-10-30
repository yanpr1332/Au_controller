# 第十八轮：三类问题的区分诊断

## 结论与修复范围

本轮证明 CEP 的宿主桥接实际已工作，但视觉呈现尚未恢复；Premiere 可以进入主页、新建隔离项目、导入视频并保存，但随后仍退出，因此没有证明稳定性修复。频谱拖拽问题在 Premiere 也复现，疑点转向 Computer Use 的拖拽输入环节，尚不能确定工具实现缺陷或应用输入兼容性。

## CEP 白屏

1. 安装目录中的 HTML、JS、manifest 均存在，CEP 命令行指向正确页面。排除页面未安装或错误 MainPath 的简单原因。
2. 单纯关闭/重新打开面板不重新解析 manifest。原参数 e30= 代表空对象；正常退出 Au 并单次重开后，详细日志参数才实际生效。因此前面的无日志不证明渲染引擎没运行。
3. 已保存 tests/receipts/phase18_cep_layout.log：记录 index.html、panel.js 的 FileURLLoader，以及 status/dictionary/commands/result 元素的实际布局。说明页面与脚本进入渲染流程。
4. tests/receipts/phase18_cep_handshake.txt 是本轮真实 CEP evalScript 在宿主内写出的握手：HOST=Audition，VERSION=26.0.0，DOCUMENTS=0，REFLECT_CLASS=Application。因此不能再称 CEP 宿主加载或 evalScript 全部不可用。
5. 页面布局和宿主回调已成功，但 Computer Use 截图仍白屏。候选原因包括宿主嵌入窗口呈现/合成、DPI 和捕获兼容性；尚需用户肉眼确认真实面板是否白屏，才能排除截图路径问题。
6. 对自有面板测试 --disable-gpu，并核对新进程参数 WyItLWRpc2FibGUtZ3B1Il0= 确已生效；仍白屏，故单独禁用GPU不是有效修复。已从工程及安装 manifest 撤回此参数与详细日志参数；当前测试进程可在正常关闭面板后结束，后续正常启动使用恢复后的清单。未更改系统GPU、安全或隐私设置。
7. 零文档 activeDocument 防护已在上一轮部署，属于真实代码修复，但与当前白屏没有已证明的因果关系。

参考 Adobe CEP 官方调试说明：https://github.com/Adobe-CEP/CEP-Resources/blob/master/CEP_12.x/Documentation/Debugging%20Handbook.md

## 频谱选择

通过 Edit > Tools 的圆点标记确认 Marquee Selection 已选中。频谱中大范围拖拽仅把时间光标移到拖拽起点，选区长度仍为零；不是仅因选区过小或工具未选中。
此前中文输入法会截获字母快捷键，切换英文后这个干扰消失，但拖拽未因此恢复。
在已恢复编辑器的 Premiere 中，把项目素材拖入空时间线也未建立序列。相同工具的点击、文本输入、导入、保存都成功，拖拽异常并非只发生在 Au。
结论为输入层/兼容性疑点，不是已证明 Au 功能缺失。当前 sky API 没有公开拖拽持续时间、分段路径或鼠标按住状态选项；本轮未调用自制鼠标注入绕过正式工具。未执行画笔修复或更改源媒体。

## Premiere 退出

观察到启动有时能出现主页，但进入编辑器后黑屏退出。捕获成功的新建项目对话框说明它不是始终无法启动。
最新 UXP 主页日志记录 getUserAccessTokenSync is not a function、SAM init timed out、CCXProcess 初始化超时；这是主页/宿主接口或配置不一致的线索，并不证明它们导致原生进程退出。
Windows 8小时范围检索找到 RADAR_PRE_LEAK_64，不是应用崩溃模块记录；没有据此断言内存泄漏就是原因。插件加载末尾没有明确第三方插件崩溃记录。

隔离测试：Au测试目录创建 ACCEPT_AU_Phase18_PR_Diagnostic.prproj。原布局 UserWorkspace.xml、WorkspaceConfig.xml 暂移到 backups/phase18_pr_layouts 后，项目成功进入完整编辑器，导入 delivery_verified.mp4 并保存。项目从5453字节变为7586字节，解压项目内容确认包含媒体引用。随后持续性检查发现 Premiere 再次退出，因此不能把布局重置标为最终修复。
原布局已还原；备份仍保留，同时生成的测试布局保存为 .generated 文件。未删除用户偏好、媒体缓存、插件或工程；未重装/更新驱动，也未触及账户或许可设置。
相关外部 Python/Node/PowerShell 进程按 Pr_controller/Premiere/native-smoke 关键字查询未发现匹配常驻控制进程；这不能彻底排除其他外部干预。

参考 Adobe 启动隔离说明：https://helpx.adobe.com/premiere/desktop/troubleshooting/preferences-and-settings-issues/reset-preferences-at-launch.html

## 验证与交付

- 验证收据 tests/receipts/phase18_diagnostics_20261030T111706441008.json 证明保存项目的媒体引用、旧布局备份和CEP握手；不包含后来持续性检查的成功声明。
- Python诊断脚本语法、manifest XML解析及 panel.js 的 node --check 通过。本轮未更改核心131个公开接口，不重复扩大384/384历史回归范围。
- maintenance/diagnose_phase18_host.py 最终仅保留只读诊断；删除未成功验证的关闭文档实验分支。
- maintenance/phase18_workspace_probe.ps1 支持隔离和恢复，恢复保留备份。
- all_requested_development_complete=false。仍未解决：CEP视觉呈现、拖拽输入、Premiere持续退出与完整音画往返。
