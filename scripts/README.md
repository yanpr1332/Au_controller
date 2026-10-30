# Adobe Audition 2026 Automation

正式控制器：

`D:\computer\Adobe\Audition\audition_controller.py`

Audition 版本：26.0.0。

## 架构

控制器分三层：

1. **ExtendScript DOM**
   - WaveDocument
   - MultitrackDocument 基础轨道/clip 编排
   - Favorite
   - Marker
   - Transport
   - Wave 保存与采样格式转换
   - Batch

2. **Win32 UI helper**
   - 新建 Multitrack Session 对话框
   - Multitrack Mixdown
   - Match Loudness 面板
   - Spectral Frequency Display
   - Spot Healing Brush

3. **离线 .sesx XML**
   - Track volume
   - Pan
   - Clip gain
   - Fade in/out
   - Track EQ 参数

## 已验证能力

### 1. Waveform 选区 / 编辑

- `Edit.SelectAll`：可用
- `Edit.Cut / Copy / Delete / InsertSilence`：命令存在
- 实测 `SelectAll -> Delete` 令 240000 samples 变为 0
- WaveDocument DOM 没有任意 start/end 时间选区 setter，因此任意范围选择需要 UI-assisted

### 2. 效果器

- `applyFavorite()` 可无人值守
- Normalize / DeNoise / DeReverb / Remove 60 Hz Hum / Repair DC Offset 已验证
- Effects 参数窗口可通过命令/菜单打开
- 任意实时效果参数没有公开 WaveDocument DOM
- Multitrack EQ 可通过 .sesx XML 精确修改

### 3. Multitrack

DOM 已验证：
- Track rename / mute / solo / armed / visible
- AudioClip startTime
- Session 保存

.sesx 已验证：
- Track volume
- Pan
- Clip gain
- Fade in/out
- EQ enable / parameter values

### 4. Mixdown

Audition 原生菜单命令：
- 35169 = Multitrack > Mixdown Session to New File > Entire Session

已实测生成新的 WaveDocument，并成功另存 WAV。

### 5. 格式 / 采样转换

稳定：
- WAV
- MP3（文件头 ID3，真实 MP3）
- SampleTypeConvertParameters
- 44.1 kHz / 24-bit WAV 已实测

不应直接使用简单 saveAs：
- FLAC
- AAC
- M4A

这些扩展名在测试中仍写出 RIFF/WAVE 数据。

### 6. Batch

3 个不同电平 WAV 批量执行 Normalize to -3 dB：
- 3/3 成功
- 输出峰值均约 -3.011 dBFS

### 7. Loudness

Audition 提供 Match Loudness UI：
- EBU R128
- ITU-R BS.1770-3
- ATSC A/85
- True Peak

但目标 LUFS / tolerance 没有公开 ExtendScript 参数对象。
Controller 可通过原生菜单 ID 35419 打开 Match Loudness；精确面板参数需 UI-assisted。

正式 controller 已加入外部 fallback：
- measure_lufs(path)
- normalize_lufs_fallback(input, output, target_lufs, true_peak_limit)
- BS.1770-style K-weighting / gating
- 4x oversampled true-peak estimation
- True Peak 上限优先；若线性增益无法同时满足 LUFS 与 dBTP，则避免削波而保守低于目标 LUFS

测试：原始约 -20.57 LUFS / -3.03 dBTP；请求 -16 LUFS / -1 dBTP 后，
True Peak 被限制在约 -1.00 dBTP，最终 Integrated Loudness 约 -18.54 LUFS。

### 8. Audio cleanup

实测数据变化：
- De-Noise：有效
- De-Reverb：有效
- Remove 60 Hz Hum：60 Hz 约 -35.27 dB -> -96.13 dB
- Repair DC Offset：DC mean 约 0.0175 -> -0.0007

### 9. Spectral

Audition 原生命令存在：
- 35361 = Toggle Spectral Frequency Display
- 35250 = Spot Healing Brush
- 35467 = Auto Heal Selection

ExtendScript command registry 中不可稳定调用，因此属于 UI-assisted。
频谱范围选择没有公开 DOM 坐标接口。

### 10. Controller

核心文件：
- `audition_controller.py`

Helper：
- `waveform.jsx`
- `favorites.jsx`
- `multitrack.jsx`
- `export.jsx`
- `batch.jsx`
- `loudness.jsx`
- `spectral.jsx`

控制器是模块化工具箱，不是固定流水线；每次只调用需要的能力。
