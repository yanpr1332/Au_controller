# 第十五轮：恢复桌面接管与 OMF GUI 导出

当前运行目录为 D:\computer\Adobe\Audition，权限未包含 D 盘根目录。
直接启动已安装的 Adobe Audition.exe 成功；Computer Use 的 launch_app 返回 accessibility window-opened handler did not become ready，因此后续采用直接启动、Computer Use 接管的方式。

Computer Use 已实测截图、激活、菜单点击和 OMF Export 对话框输入。启动恢复提示选择 Later，恢复数据未删除。

## OMF

打开既有 ACCEPT_AU_Phase06_multi_arrangement.sesx，通过 File > Export > OMF 原生导出，观察到转换进度后回到工作区。
输出 tests/native_outputs/ACCEPT_AU_Phase06_multi_arrangement.omf，383112 字节，SHA256 ad973f3ff5704da34efd0194cddd49c4a8281f421ace61f5f2229734589a4630。
Au 内部 File.exists=true，File.length=383112。证据见 tests/receipts/phase15_omf_inspection_20261030T063819555603.json。
对话框明确警告总线轨道、轨道 EQ 被忽略，空轨道跳过。
open_document 对 OMF 返回 File does not exist，但同一宿主 File 对象确认存在。尚未完成 GUI 重新导入和片段/时间位置核验，因此 roundtrip_verified=false。

## 频谱

合成 QA WAV 在 Au 中显示真实频谱，包含约 440Hz 和 880Hz 明亮谱线。矩形工具点击、拖拽未产生可确认的选区；工具快捷键曾被中文输入法截获，切到英文后仍未取得选区成功证据。未执行画笔修复或保存源音频。
频谱显示已观察；矩形、套索、画笔和音质改善仍未验收。

## 控制器运行环境

普通受限执行环境不能发现桌面 Au，导致 _audition_pid 报未运行。桌面访问权限下 status 正确回读 Audition 26.0.0，原生 open_document 成功。不能把受限环境中的进程不可见解释为宿主未运行。

本轮新增只读证据脚本 maintenance/inspect_phase15_omf.py；未增加公开接口，未重跑完整回归，不改变既有 131 接口和 384/384 的历史验证范围。
CEP、Premiere 往返、硬件依赖项目及发布签名均未完成；all_requested_development_complete=false。
