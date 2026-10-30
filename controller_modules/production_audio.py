"""Offline sample automation and reviewable repair bundles; never native Au Fx."""
from pathlib import Path
import hashlib
import json
import tempfile
import shutil
import math
import numpy as np
from scipy.io import wavfile


class AuditionProductionAudio:
    @classmethod
    def render_gain_pan_envelope(cls, source, destination, points, *, confirm=False):
        """Linear interpolation of dB gain and pan at explicit sample positions.

        Mono uses equal-power panning into stereo; stereo uses attenuation balance.
        This renders a new audio file, not native SESX automation keyframes.
        """
        src, dst = Path(source).resolve(), Path(destination).resolve()
        if src == dst or dst.exists() or dst.suffix.lower() != '.wav' or not dst.parent.is_dir():
            raise ValueError('New WAV destination required')
        rate, audio, meta = cls._read_wav(src)
        if not isinstance(points, list) or not 1 <= len(points) <= 4096 or not len(audio):
            raise ValueError('1..4096 envelope points and nonempty audio required')
        previous = -1
        for p in points:
            if not isinstance(p, dict) or set(p) != {'sample', 'gain_db', 'pan'}:
                raise ValueError('Each point requires sample, gain_db, pan')
            if type(p['sample']) is not int or not previous < p['sample'] < len(audio):
                raise ValueError('Points must increase within audio duration')
            for key, low, high in (('gain_db', -96, 0), ('pan', -1, 1)):
                if type(p[key]) not in (int, float) or not math.isfinite(p[key]) or not low <= p[key] <= high:
                    raise ValueError('Invalid envelope '+key)
            previous = p['sample']
        if points[0]['sample'] != 0 or type(confirm) is not bool:
            raise ValueError('Envelope must start at sample zero; Boolean confirm required')
        if not confirm:
            return dict(dry_run=True, output=str(dst), points=points, native_audition_automation=False)
        original = hashlib.sha256(src.read_bytes()).hexdigest()
        positions = np.arange(len(audio))
        times = [p['sample'] for p in points]
        gain = 10 ** (np.interp(positions, times, [p['gain_db'] for p in points])/20)
        pan = np.interp(positions, times, [p['pan'] for p in points])
        if audio.shape[1] == 1:
            angle = (pan+1)*np.pi/4
            result = np.column_stack((audio[:,0]*np.cos(angle), audio[:,0]*np.sin(angle)))
        else:
            result = audio.copy()
            result[:,0] *= np.cos(np.maximum(pan, 0)*np.pi/2)
            result[:,1] *= np.cos(np.maximum(-pan, 0)*np.pi/2)
        result *= gain[:,None]
        if not np.all(np.isfinite(result)) or np.max(np.abs(result)) > 1:
            raise ValueError('Rendered automation would clip')
        if hashlib.sha256(src.read_bytes()).hexdigest() != original:
            raise RuntimeError('Source changed')
        created = False
        try:
            with dst.open('xb') as handle:
                created = True
                wavfile.write(handle, rate, result.astype(np.float32))
            sr, decoded = wavfile.read(dst)
            if sr != rate or len(decoded) != len(audio):
                raise RuntimeError('Envelope output readback failed')
        except Exception:
            if created: dst.unlink(missing_ok=True)
            raise
        return dict(output=str(dst), sample_rate=rate, frames=len(audio), channels=2,
                    sha256=hashlib.sha256(dst.read_bytes()).hexdigest(), source_sha256=original,
                    native_audition_automation=False)

    @classmethod
    def repair_review_bundle(cls, source, destination, operations, *, confirm=False):
        """Explicit WAV edits plus before/after audio, diagnostics and review markers.

        Heuristic transient flags are review candidates, never automatic diagnoses.
        """
        src, dst = Path(source).resolve(), Path(destination).resolve()
        if dst.exists() or not dst.parent.is_dir():
            raise ValueError('New review directory required')
        # Validate exact typed waveform operations even in dry-run.
        cls._wb_config(src, dst.parent / (dst.name+'_preview.wav'), operations, 'float32', 'none', 19)
        before = cls.audio_forensics(src)
        if type(confirm) is not bool:
            raise ValueError('Boolean confirm required')
        if not confirm:
            return dict(dry_run=True, output=str(dst), operations=operations, diagnostics=before)
        with tempfile.TemporaryDirectory(prefix='.au_review_', dir=dst.parent) as temp:
            package = Path(temp) / dst.name
            package.mkdir()
            original = package / 'before.wav'
            shutil.copy2(src, original)
            edited = package / 'after.wav'
            result = cls.edit_wav_timeline(original, edited, operations, confirm=True)
            after = cls.audio_forensics(edited)
            before['source'] = 'before.wav'
            after['source'] = 'after.wav'
            with (package/'review_markers.csv').open('x', encoding='utf8', newline='') as handle:
                handle.write('seconds,label\n')
                for second in before['transient_spike_candidates_seconds']:
                    handle.write(str(second)+',Review transient candidate\n')
            if hashlib.sha256(src.read_bytes()).hexdigest() != before['sha256']:
                raise RuntimeError('Source changed during review')
            report = dict(backend='offline Python/SciPy', operations=operations,
                          before=before, after=after, listening_review_required=True,
                          native_spectral_repair_verified=False)
            (package/'review.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
            package.rename(dst)
        return dict(output=str(dst), before=str(dst/'before.wav'), after=str(dst/'after.wav'),
                    report=str(dst/'review.json'), listening_review_required=True)
