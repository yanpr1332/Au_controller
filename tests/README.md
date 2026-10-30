# Audition Controller 单元测试及 Native 实证

当前正式单元测试累计 **292 项**：

    python -B -m unittest discover -s D:\computer\Adobe\Audition\tests -q

最新第七轮：
- test_phase07_waveform_and_native_split.py：波形样本级编辑、Dither、Noise Shaping、FFT、Native Clip Split（26 项）。
- test_phase07_channels_and_coverage.py：左右声道零误差回组、Float-to-PCM16、4 步生产链、真实 MP3/FLAC 导入、P0 证据交叉验证（15 项）。

native_outputs/ 与 receipts/ 保存真实 Audition 及外部 DSP 成片/哈希证据，不是临时缓存。
正式发布检查：

    python -B maintenance\verify_workspace.py --sdk --full-tests
