# Audition 26 Controller API（第二十轮已完成功能整合）

当前135个公开方法；接口存在不代表所有宿主、插件或硬件组合已验收。

第二十轮新增四个只读入口：

| 方法 | 签名 | 边界 |
|---|---|---|
| native_document_snapshot | `(self)` | 实时文档与轨道片段名称、起点和长度；不保存或关闭文档 |
| inspect_native_omf | `(self, path)` | 已存在 OMF 的 SHA256、长度及 Au 可见性；不执行导入导出 |
| inspect_cep_receipt | `(path)` | 离线解析握手/页面诊断收据；不证明当前画面正常 |
| inspect_premiere_project_reference | `(path, media_name)` | 有限大小解压及媒体引用检查；不证明播放或往返 |

本轮边界见 docs/Audition_26_phase14_20261030.md，完整签名见 Audition_26_phase14_api.json。

| 方法 | 签名 |
|---|---|
| activity_regions | `(path: 'str / Path', *, threshold_dbfs: 'float' = -35.0, window_ms: 'int' = 20, min_active_ms: 'int' = 80) -> 'dict'` |
| add_marker | `(self, start_samples: 'int', duration_samples: 'int' = 0, name: 'str' = '', marker_type: 'str' = 'Cue', description: 'str' = '') -> 'dict[str, str]'` |
| apply_favorite | `(self, name: 'str', output_path: 'str / None' = None, timeout: 'float' = 30.0) -> 'dict[str, str]'` |
| apply_native_rack_preset | `(source, destination, preset, *, track_id, confirm=False)` |
| arrange_native_qa_clips | `(source, destination, placements: 'list[dict]', *, confirm=False)` |
| audio_forensics | `(source, *, window_ms=100, true_peak_factor=4)` |
| audio_quality_gate | `(path: 'str / Path', *, max_peak_dbfs: 'float' = 0.0, max_dc: 'float' = 0.01, allow_clips: 'int' = 0) -> 'dict'` |
| audio_signal_report | `(source: 'str / Path', *, fft_window: 'int' = 4096) -> 'dict'` |
| audit_native_session | `(session, *, reject_hot_eq=True)` |
| audition_command_probe | `(self, commands: 'list[str]') -> 'dict'` |
| audition_native_favorite_export | `(self, source: 'str / Path', output: 'str / Path', *, favorite: 'str', confirm: 'bool' = False) -> 'dict'` |
| audition_native_marker_export | `(self, source: 'str / Path', output: 'str / Path', *, start_samples: 'int', duration_samples: 'int' = 0, name: 'str' = 'QA Marker', confirm: 'bool' = False) -> 'dict'` |
| audition_native_resample_export | `(self, source: 'str / Path', output: 'str / Path', *, sample_rate: 'int' = 44100, bit_depth: 'int' = 24, confirm: 'bool' = False) -> 'dict'` |
| audition_reflect | `(self, object_name: 'str' = 'application') -> 'dict'` |
| batch_dsp | `(sources: 'list[str / Path]', output_folder: 'str / Path', operations: 'list[dict]', *, confirm: 'bool' = False) -> 'dict'` |
| batch_effect_recipes | `(jobs, *, confirm=False)` |
| batch_favorite | `(self, paths: 'list[str]', favorite: 'str', output_dir: 'str', suffix: 'str' = '_processed') -> 'dict[str, str]'` |
| batch_loudness_master | `(sources, output_folder, *, target_lufs=-16.0, ceiling_dbtp=-1.5, rate=48000, suffix='_loudness', confirm=False, stop_on_error=False)` |
| batch_transcode_audio | `(sources: 'list[str / Path]', output_dir: 'str / Path', *, fmt: 'str' = 'flac', suffix: 'str' = '_deliver', rate: 'int' = 48000, channels: 'int' = 2, bitrate_kbps: 'int' = 192, stop_on_error: 'bool' = False, confirm: 'bool' = False) -> 'dict'` |
| combine_mono_to_stereo | `(left, right, destination, *, confirm=False)` |
| control_surface_devices | `()` |
| create_multitrack_from_current | `(self, session_name: 'str', timeout: 'float' = 10.0) -> 'None'` |
| create_native_sdk_session | `(spec, destination, *, confirm=False)` |
| create_qa_session_package | `(source, destination, *, confirm=False)` |
| decode_midi_message | `(packed)` |
| deliver_audio_batch | `(sources: 'list[str / Path]', directory, *, preset='podcast_16', formats=('wav', 'mp3'), denoise=False, confirm=False)` |
| duck_music_under_dialogue | `(dialogue, background, destination, *, music_gain_db=-9.0, voice_gain_db=0.0, threshold=0.025, ratio=8.0, attack_ms=15, release_ms=300, confirm=False)` |
| edit_native_rack | `(source, destination, *, track_id, operations, confirm=False)` |
| edit_production_session | `(source, destination, operations, *, confirm=False)` |
| edit_sesx | `(session_path: 'str', *, output_path: 'str / None' = None, track_index: 'int' = 0, track_volume: 'float / None' = None, pan: 'float / None' = None, clip_index: 'int' = 0, clip_gain: 'float / None' = None, fade_in_samples: 'int / None' = None, fade_out_start_samples: 'int / None' = None, eq_band3_gain: 'float / None' = None, enable_eq: 'bool / None' = None) -> 'str'` |
| edit_wav_timeline | `(source, destination, operations, *, format='float32', dither='none', seed=19, confirm=False)` |
| effects_recipe_validate | `(effects, *, max_effects=16)` |
| enqueue_production_job | `(database, spec, output_dir)` |
| export_audio_qc_report | `(source, destination, *, profile='podcast', confirm=False)` |
| export_fft_spectrum | `(source, destination, *, window=4096, confirm=False)` |
| export_native_marker_chapters | `(session, rendered_audio, directory, *, fade_ms=5, confirm=False)` |
| export_native_rack_preset | `(source, destination, *, track_id, confirm=False)` |
| export_r128_timeline | `(source, destination, *, confirm=False, max_points=4000)` |
| ffmpeg_environment | `() -> 'dict'` |
| ffprobe_media | `(path: 'str / Path') -> 'dict'` |
| import_production_wavs | `(source, destination, placements, *, confirm=False)` |
| inspect_audition_controls | `(self, *, title_contains='', max_controls=200, max_depth=5, timeout=15)` |
| inspect_native_clips_advanced | `(source)` |
| inspect_native_eq | `(session, *, track=0, kind='audioTrack')` |
| inspect_native_sesx | `(source) -> 'dict'` |
| inspect_session_routes | `(source)` |
| inspect_sesx | `(path: 'str / Path') -> 'dict'` |
| listen_midi_controls | `(device_id, *, seconds=1.0, confirm=False)` |
| lookup_native_menu | `(self, keyword: 'str', *, max_results: 'int' = 50)` |
| loudness_delivery_gate | `(source, *, profile='podcast_stereo')` |
| mark_production_job_interrupted | `(database, job_id, *, confirm=False)` |
| master_loudness | `(source, destination, *, target_lufs=-16.0, ceiling_dbtp=-1.5, rate=48000, confirm=False)` |
| measure_lufs | `(path: 'str') -> 'dict[str, float / int]'` |
| measure_r128_ffmpeg | `(source, *, timeout=45)` |
| midi_control_message | `(channel, controller, value)` |
| mix_audio_stems | `(stems: 'list[dict]', destination, *, rate=48000, output_ceiling=0.9, confirm=False)` |
| mixdown_production_session | `(self, session_path, output, *, timeout=120, confirm=False)` |
| mixdown_to_wave | `(self, output_path: 'str', wait_seconds: 'float' = 1.2) -> 'dict[str, str]'` |
| multitrack_track_edit | `(self, track_index: 'int' = 0, *, name: 'str / None' = None, mute: 'bool / None' = None, solo: 'bool / None' = None, armed: 'bool / None' = None, visible: 'bool / None' = None, clip_index: 'int / None' = None, clip_start_samples: 'int / None' = None, session_path: 'str / None' = None, save: 'bool' = False) -> 'dict[str, str]'` |
| mux_video_audio | `(video, audio, destination, *, offset_seconds=0.0, bitrate_kbps=192, shortest=True, confirm=False)` |
| native_add_track_qa | `(self, session_name: 'str', *, label: 'str' = 'QA Added Track', confirm: 'bool' = False)` |
| native_apply_favorite_copy | `(self, source, destination, *, favorite, timeout=120, confirm=False)` |
| native_batch_open_qa | `(self, sources, *, confirm=False)` |
| native_batch_process_qa | `(self, sources, output_folder, *, task='favorite', favorite='Normalize to -3 dB', rate=44100, bit_depth=24, suffix='_phase09_native', stop_on_error=False, confirm=False)` |
| native_favorite_inventory | `()` |
| native_menu_catalog | `(self)` |
| native_move_clip_qa | `(self, session_name: 'str', from_track: 'int', to_track: 'int', *, clip_index: 'int' = 0, start_samples: 'int / None' = None, confirm: 'bool' = False)` |
| native_multitrack_add_bus_qa | `(self, session_name: 'str', bus_name: 'str', *, confirm: 'bool' = False)` |
| native_multitrack_bus_marker_inventory | `(self, session_name: 'str')` |
| native_multitrack_edit_qa | `(self, session_name: 'str', track_index: 'int', *, name: 'str / None' = None, mute: 'bool / None' = None, solo: 'bool / None' = None, clip_index: 'int / None' = None, clip_start_samples: 'int / None' = None, confirm: 'bool' = False) -> 'dict'` |
| native_multitrack_marker_qa | `(self, session_name: 'str', *, start_samples: 'int', duration_samples: 'int' = 0, label: 'str' = 'QA Marker', description: 'str' = 'Audition QA', confirm: 'bool' = False)` |
| native_multitrack_mixdown_qa | `(self, session_name: 'str', output: 'str / Path', *, confirm: 'bool' = False, poll_seconds: 'float' = 3.0)` |
| native_multitrack_remove_bus_qa | `(self, session_name: 'str', bus_index: 'int', *, confirm: 'bool' = False)` |
| native_multitrack_snapshot | `(self, session_name: 'str')` |
| native_qa_transport_accept | `(self, session_name, *, seek_samples=0, play_ms=150, test_pause=True, confirm=False)` |
| native_record_input_qa | `(self, destination, *, seconds=1.0, confirm=False)` |
| native_remove_empty_track_qa | `(self, session_name: 'str', track_index: 'int', *, confirm: 'bool' = False)` |
| native_sesx_markers_xmp | `(session)` |
| native_track_state_roundtrip_qa | `(self, source, *, track_index=0, armed=True, visible=False, confirm=False)` |
| native_transport_snapshot | `(self)` |
| native_wave_markers_qa | `(self, source, output, *, confirm=False)` |
| normalize_lufs_fallback | `(input_path: 'str', output_path: 'str', target_lufs: 'float' = -16.0, true_peak_limit: 'float' = -1.0) -> 'dict[str, float / str]'` |
| open_document | `(self, path: 'str') -> 'dict[str, str]'` |
| open_match_loudness_panel | `(self) -> 'None'` |
| package_production_session | `(source, destination, *, confirm=False)` |
| patch_native_clip_advanced | `(source, destination, edits: 'list[dict]', *, confirm=False)` |
| patch_native_eq_normalized | `(source, destination, settings: 'dict', *, track=0, kind='audioTrack', enabled=True, confirm=False)` |
| patch_native_pan_position | `(source, destination, *, track_id, position, confirm=False)` |
| patch_native_send | `(source, destination, *, track_id, bus_id, slot=0, level=0.25, pre_fader=False, enabled=True, confirm=False)` |
| patch_native_sesx | `(source, destination, edits: 'list[dict]', *, confirm: 'bool' = False)` |
| patch_native_track_envelope | `(source, destination, *, track_id, points, component_id='trackFader', parameter_index=0, confirm=False)` |
| patch_native_xmp_markers | `(source, destination, operations, *, confirm=False)` |
| patch_production_component | `(source, destination, *, track_id, component_id, powered=None, normalized_parameters=None, confirm=False)` |
| patch_session_bus_route | `(source, destination, *, track_index=0, bus_index=0, confirm=False)` |
| patch_sesx | `(source: 'str / Path', dest: 'str / Path', changes: 'list[dict]', *, confirm=False) -> 'dict'` |
| plan_spectral_selection | `(*, viewport, points, tool='lasso')` |
| podcast_sidechain_delivery | `(dialogue, music, destination, *, target_lufs=-16, ceiling_dbtp=-1.5, confirm=False)` |
| process_wav | `(source: 'str / Path', destination: 'str / Path', operations: 'list[dict]', *, confirm: 'bool' = False, output_format: 'str' = 'pcm16') -> 'dict'` |
| production_component_inventory | `(source)` |
| production_job_plan | `(spec, output_dir)` |
| production_queue_status | `(database)` |
| qc_audio_profile | `(source, profile='podcast', *, profile_override=None)` |
| r128_loudness_timeline | `(source, *, max_points=4000, timeout_seconds=100)` |
| relink_production_session | `(source, destination, replacements, *, confirm=False)` |
| remove_unused_bus_sesx | `(source, destination, *, bus_index: 'int', expected_name: 'str', confirm: 'bool' = False)` |
| render_audio_effects | `(source, destination, effects, *, sample_rate=48000, final_ceiling_dbfs=-1.0, confirm=False)` |
| render_gain_pan_envelope | `(source, destination, points, *, confirm=False)` |
| repair_review_bundle | `(source, destination, operations, *, confirm=False)` |
| retry_production_job | `(database, job_id, *, confirm=False)` |
| run_next_production_job | `(database, *, confirm=False)` |
| run_production_jobs | `(spec, output_dir, *, confirm=False)` |
| run_resumable_production | `(spec, output_dir, checkpoint_dir, *, confirm=False)` |
| save_as | `(self, path: 'str') -> 'dict[str, str]'` |
| save_wave_converted | `(self, path: 'str', sample_rate: 'int / None' = None, bit_depth: 'int / None' = None, dither: 'bool' = True, resample_quality: 'int' = 100) -> 'dict[str, str]'` |
| search_session_media | `(source, roots, *, expected_hashes=None, max_files=20000)` |
| select_spot_healing_brush | `(self) -> 'None'` |
| send_menu_command | `(self, command_id: 'int') -> 'None'` |
| send_midi_control | `(device_id, *, channel, controller, value, confirm=False)` |
| session_overlap_report | `(source)` |
| set_playhead | `(self, samples: 'int') -> 'dict[str, str]'` |
| speech_cleanup | `(source, destination, *, highpass_hz=85.0, denoise_db=9.0, threshold_db=-22.0, ratio=2.5, confirm=False)` |
| split_native_qa_clip | `(source, destination, *, track=0, clip=0, offset_samples=0, confirm=False)` |
| split_stereo_to_mono | `(source, left_output, right_output, *, confirm=False)` |
| status | `(self) -> 'dict[str, str]'` |
| tag_delivery_audio | `(source, destination, tags: 'dict', *, bwf=False, confirm=False)` |
| toggle_spectral_display | `(self) -> 'None'` |
| transcode_audio | `(source: 'str / Path', destination: 'str / Path', *, rate: 'int' = 48000, channels: 'int' = 2, bitrate_kbps: 'int' = 192, confirm: 'bool' = False) -> 'dict'` |
| transport | `(self, action: 'str') -> 'dict[str, str]'` |
| verify_qa_session_package | `(directory)` |
| wav_stats | `(path: 'str') -> 'dict[str, float / int / str]'` |
| write_native_session_audit | `(session, destination, *, confirm=False)` |
