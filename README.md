# Adobe Audition 26 自动化 Controller

Copyright © 2026 Yan Pengrui · MIT License（自有源码；第三方 Adobe SDK 与依赖保留其原有许可，不包含在本仓库的 MIT 授权中）。

## 目录迁移与公开源码

当前 Controller 根目录为 `D:\computer\Adobe\Audition\Au_controller`；Audition 程序位于同级 `Adobe Audition 2026` 目录。可用环境变量 `AUDITION_EXE` 指定其他安装位置。

公开仓库不包含本地运行输出、原始录音、验收媒体、备份、下载的 Adobe SDK 或依赖二进制。这些本地文件已随工程迁移但不上传；依赖它们的历史全量验收不适用于全新克隆。历史文档中的旧绝对路径是当时证据，不代表当前工作区路径。

> 第二十轮整合：135个公开方法，新增文档/片段时间快照、OMF可见性、CEP收据和Premiere媒体引用四项只读API及CLI。详见 `docs/Audition_26_phase20_integration.md`。本轮不做新的GUI尝试。

> 2026-10-30 第十一轮：当前123个公开接口，已取得本地Au轨道导入、原生混音、包络、Pan、Send、Rack、预设、5.1及经授权麦克风录音证据。完整范围和未完成项见 `docs/Audition_26_phase11_20261030.md`；统一复验：`python -B maintenance/verify_workspace.py --sdk --full-tests`。

> 第十二轮新增MIDI和ASIO设备发现及原始MIDI消息层，当前128个公开接口；具体验证与仍未完成范围见 `docs/Audition_26_phase12_20261030.md`。

> 第十三轮新增离线音画交付及时间戳核验，当前129个公开方法；实测及剩余范围见 `docs/Audition_26_phase13_20261030.md`。

> 第十四轮正在排查桌面工具启动问题；新增频谱坐标规划，不包含GUI操作。当前131个公开方法，详见 `docs/Audition_26_phase14_20261030.md`。

**工作区** `D:\computer\Adobe\Audition\Au_controller`  
**宿主** Audition 26.0.0 / Windows 11；外部音频服务为 WSL Debian FFmpeg 7.1.3。

## 第九轮历史验收（冻结基线）

- **384 个功能审计条目**，**96 个公开 Controller 方法**。
- **326/326 项自动化测试通过**，**25/25 项综合检查通过**（包含实机 Audition 零文档状态）。
- **107 项功能尚未完整验收**；相关实机条件、限制及依赖见 `api/Audition_26_未完成与依赖清单.md`。
- 第八轮 379 项台账冻结在 `api/Audition_26_phase08_baseline_379.json`。
- 所有外部 SciPy/FFmpeg 处理结果明确标记为离线，不冒充 Audition 原生 Fx、GUI 或 SDK。

## 目录

| 路径 | 作用 |
|---|---|
| `audition_controller.py` | 统一 Controller Python API、CLI 入口 |
| `controller_modules/` | 各功能的实际模块化实现；无需从外部单独导入 |
| `api/Audition_26_API_接口目录.md` | 全部 96 个方法签名 |
| `api/Audition_26_全功能开发矩阵.md` | 384 项审计条目、验证等级和凭据 |
| `api/Audition_26_未完成与依赖清单.md` | 尚未完整验证的 107 项 |
| `docs/Audition_26_第九轮集中开发与实机验收_20261010.md` | 本轮正式报告 |
| `tests/fixtures/` | 受控、不得覆写的 QA 合成媒体 |
| `tests/native_outputs/` | Native Au、FFmpeg、SciPy 的验收结果 |
| `tests/receipts/` | JSON 证据、真实输出哈希和发布验收记录 |
| `maintenance/` | 当前重建与验收脚本、受控 QA 工具 |
| `archives/`、`backups/` | 历史脚本归档、不可覆盖的恢复点 |
| `_runtime/` | Audition JSX 运行中的瞬时文件，结束后自动清理 |

## 第九轮新增公开方法

`native_track_state_roundtrip_qa` — 仅对 `ACCEPT_AU_` 隔离 SESX 会话进行 Track Arm / Visibility 变更、恢复、真实回读，**不会执行录音**。

`native_batch_open_qa` — 原生逐项导入 1–12 个 QA WAV/MP3/FLAC，检查源媒体哈希，结束后关闭 QA 文档。

`native_batch_process_qa` — 真实 Audition Favorite 或 SaveAsDocument 受控批量处理，逐文件保留响应、SHA256、输出解码证据。

`native_wave_markers_qa` — Cue 点/范围、Subclip 类型的创建与原生保存重开核验；本机不支持以 `CD Track` 为输入类型的该接口调用。

`batch_loudness_master` — 批量双遍 FFmpeg Loudnorm、响度/真峰值验收、独占文件发布、错误隔离；**非原生 Match Loudness GUI**。

上述操作除特别说明外均支持 `confirm=False` 只规划，实际执行需要 `confirm=True`，并拒绝覆盖现有文件。

## 复验

```powershell
cd D:\computer\Adobe\Audition\Au_controller
python -B maintenance\verify_workspace.py --sdk --full-tests
```

第九轮重建脚本属于历史工具，当前版本禁止回写旧台账。下列命令仅供历史环境参考：

```powershell
python -B maintenance\rebuild_phase09_catalog.py
```

历史第七、第八轮重建程序已有版本防降级保护，不能误写覆盖当前第九轮台账。

## 当前真实阻塞

Audition CEP PlugPlugSetup 宿主装载、Native Bus.remove、复杂原生 Rack / 发送 / Automation、完整 Spectral 修复 GUI、真实音频采集和 ASIO、AMIO C++ SDK、Control Surface、Premiere/AAF/OMF、5.1 等仍未达到完整验收。详见正式报告和未完成清单。
