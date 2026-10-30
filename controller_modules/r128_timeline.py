"""FFmpeg ebur128 timeline and practical policy gates; separate from Audition native API."""
from __future__ import annotations
import json,re,hashlib,math
from pathlib import Path

class AuditionR128Timeline:
    @classmethod
    def r128_loudness_timeline(cls,source,*,max_points=4000,timeout_seconds=100):
        src=cls._qa_input(source)
        if type(max_points)!=int or not 10<=max_points<=50000:
            raise ValueError('max_points must be 10..50000')
        if type(timeout_seconds)!=int or not 5<=timeout_seconds<=240:
            raise ValueError('timeout_seconds must be 5..240')
        # 100ms windows and gating are calculated by FFmpeg's ebur128 filter,
        # not approximated by naive frame RMS.
        args=['wsl.exe','-d','Debian','--exec','/usr/bin/ffmpeg','-nostdin',
              '-hide_banner','-loglevel','verbose','-i',cls._wsl_path(src),
              '-af','ebur128=peak=true:framelog=verbose','-vn','-f','null','-']
        output=cls._run(args,timeout_seconds).stderr
        patt=re.compile(r'\bt:\s*([0-9.]+)\s+TARGET:\s*[-0-9.]+\s*LUFS\s+M:\s*([-0-9.]+)\s+S:\s*([-0-9.]+)\s+I:\s*([-0-9.]+)\s*LUFS\s+LRA:\s*([0-9.]+)',re.I)
        readings=[]
        for match in patt.finditer(output):
            readings.append({'seconds':float(match.group(1)),
                             'momentary_lufs':float(match.group(2)),
                             'short_term_lufs':float(match.group(3)),
                             'integrated_so_far_lufs':float(match.group(4)),
                             'loudness_range_so_far_lu':float(match.group(5))})
        if not readings:raise RuntimeError('Unable to parse FFmpeg ebur128 time series')
        stride=max(1,math.ceil(len(readings)/max_points))
        reported=readings[::stride]
        long=cls.measure_r128_ffmpeg(src)
        return {'source':str(src),'backend':'Debian FFmpeg ebur128, ITU-R BS.1770 style',
                'not_native_audition_meter':True,
                'resolution_approx_seconds':.1,'readings_total':len(readings),
                'readings_returned':len(reported),'downsample_stride':stride,
                'time_series':reported,'integrated_summary':long,
                'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest()}

    @classmethod
    def loudness_delivery_gate(cls,source,*,profile='podcast_stereo'):
        presets={
          'podcast_stereo':{'lufs_target':-16,'tolerance':1,'true_peak_max':-1.0},
          'podcast_mono':{'lufs_target':-19,'tolerance':1,'true_peak_max':-1.0},
          'broadcast_ebu':{'lufs_target':-23,'tolerance':1,'true_peak_max':-1.0},
          'online_video':{'lufs_target':-14,'tolerance':1,'true_peak_max':-1.0},
        }
        if profile not in presets:raise ValueError('Unknown delivery profile')
        sample=cls.measure_r128_ffmpeg(source)
        ref=presets[profile]
        integr=sample['integrated_lufs'];peak=sample['true_peak_dbtp']
        checks={'integrated_lufs_within_tolerance':
                 integr is not None and math.isfinite(integr) and abs(integr-ref['lufs_target'])<=ref['tolerance'],
                'true_peak_below_ceiling':
                 peak is not None and math.isfinite(peak) and peak<=ref['true_peak_max']}
        return {'profile':profile,'policy':ref,'checks':checks,
                'passed':all(checks.values()),
                'measured_integrated_lufs':integr,'measured_true_peak_dbtp':peak,
                'note':'Practical delivery thresholds; not a broadcaster compliance certification.'}

    @classmethod
    def export_r128_timeline(cls,source,destination,*,confirm=False,max_points=4000):
        output=Path(destination).resolve()
        if output.suffix.lower()!='.json' or output.exists() or not output.parent.is_dir():
            raise ValueError('Output must be new JSON in existing directory')
        if not confirm:return {'dry_run':True,'output':str(output)}
        report=cls.r128_loudness_timeline(source,max_points=max_points)
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
        return {'output':str(output),'points':report['readings_returned'],
                'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
                'input_sha256':report['source_sha256']}
