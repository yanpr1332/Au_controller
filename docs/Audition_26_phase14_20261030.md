# 第十四轮：桌面工具排查与频谱坐标准备

## 桌面控制现状

本轮重新调用 Computer Use，仍在初始化阶段失败：`failed to prepare MXC sandbox: permission path cannot be represented losslessly`。错误发生于访问任何 Au 窗口之前。此前重置并重试也出现同一错误；不能据此断言问题来自 Au。

当前聊天所在项目根为 `D:\`。将聊天项目改为具体目录 `D:\computer\Adobe\Audition` 后重试是一个排查假设；尚未得到对照结果，不能断言盘符根目录就是原因。Remote Desktop Commander 此时显示设备离线，且其已提供工具不包含截图和鼠标操作。

故本轮没有调用其他 Windows UI 自动化途径绕过桌面工具，也没有操作 Au 用户界面。对话框控件树、频谱显示、画笔和套索均未实机验证。

## 频谱坐标规划

`plan_spectral_selection` 是纯计算接口：根据调用方提供的当前窗口内绘图区边界、时间范围和线性或对数频率刻度，将明确的时间/频率点转换为窗口相对像素坐标。它拒绝窗口外、非有限数值、非法对数刻度以及错误的点数。

该方法不截屏、不识别坐标轴、不控制鼠标，也不代表实际频谱选择或修复已经完成。由于 Au 的缩放、刻度和窗口位置会变化，坐标参数必须来自当前实际截图/界面状态的独立校准。

新增加5项单元测试，覆盖线性/对数坐标、边界和非法参数。用户界面验收仍需 Computer Use 工作后执行。实际完整回归以 `tests/receipts/phase11_verification_*.json` 的最新记录为准。

本轮完整软件回归379/379通过，130个公开方法；收据 `tests/receipts/phase11_verification_20261030T041357067102.json`。此回归没有本轮Au GUI实测。

## UI Automation 只读检查准备

已从官方 Python 包索引将 pywinauto 0.6.9、comtypes 1.4.17、pywin32 312 和 six 1.17.0 安装在项目 `_vendor/gui`，没有修改全局 Python；版本清单见 `requirements-uia.txt`。库导入已验证。

`inspect_audition_controls` 和 `uia-inspect` CLI 使用独立进程只读收集 Au 进程所属的窗口和控件，限制遍历数量、深度和执行时长；不点击、输入或保存工程。测试使用模拟 UIA 响应检查进程边界和超时。该接口没有在真实 Au 窗口运行，不能视为 OMF 对话框或频谱界面已验收。

用户已将 App Dev 项目路径改为 `D:\computer\Adobe\Audition`；项目列表可见，但当前聊天运行目录在本次运行中仍回读为 `D:\`，Computer Use 重试仍失败。项目归属调整不自动证明当前执行目录已改变，下一步需在该项目的新运行上下文中验证。

最新完整软件回归 384/384 通过，131 个公开方法，收据 `tests/receipts/phase11_verification_20261030T042311044047.json`。GUI 未实测，`all_requested_development_complete=false`。
