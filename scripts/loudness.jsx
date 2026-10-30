#target audition
// Audition 26 exposes Match Loudness primarily as a UI panel, not as a
// parameterized ExtendScript DOM object.
//
// Python controller support:
// - AuditionController.measure_lufs(path)
// - AuditionController.normalize_lufs_fallback(input, output, target_lufs, true_peak_limit)
//
// The fallback implements BS.1770-style K-weighting / gating and 4x
// oversampled true-peak estimation. True-peak protection takes priority;
// if simple gain cannot reach both LUFS and dBTP targets simultaneously,
// the result stays below the requested LUFS instead of clipping.
//
// Native UI helper:
// CMD_MATCH_LOUDNESS = 35419
function AuCtl_normalizeMinus3(){
    return AuCtl_applyFavoriteAndWait("Normalize to -3 dB",30000);
}
