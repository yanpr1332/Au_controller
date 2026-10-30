"""Bounded Adobe Audition companion: EBU BS.1770 metering, two-pass loudnorm,
noise cleanup and stem mixdown using verified Debian FFmpeg/FFprobe.

Every operation creates NEW files and reports that it is not native Audition.
"""
from __future__ import annotations
import hashlib,json,math,re,subprocess
from pathlib import Path

class AuditionMasteringLab:
    @classmethod
    def _qa_input(cls,source):
        p=Path(source).resolve()
        if not p.is_file() or p.suffix.lower() not in ('.wav','.flac','.mp3','.m4a','.ogg','.opus'):
            raise ValueError('Supported existing audio input required')
        return p
    @classmethod
    def _qa_output(cls,source,target,*,suffixes=('.wav','.flac','.mp3','.m4a')):
        out=Path(target).resolve()
        if out==Path(source).resolve() or out.exists() or not out.parent.is_dir() or out.suffix.lower() not in suffixes:
            raise ValueError('Must supply NEW output audio file in existing directory')
        return out
    @staticmethod
    def _f(value,lo,hi,label):
        if isinstance(value,bool) or not isinstance(value,(int,float)):
            raise ValueError(label+' numeric required')
        v=float(value)
        if not math.isfinite(v) or not lo<=v<=hi:raise ValueError(label+' out of range')
        return v
    @staticmethod
    def _run(args,seconds=90):
        r=subprocess.run(args,capture_output=True,text=True,errors='replace',timeout=seconds)
        if r.returncode:raise RuntimeError('Debian FFmpeg failed: '+r.stderr[-600:])
        return r
    @classmethod
    def measure_r128_ffmpeg(cls,source,*,timeout=45):
        p=cls._qa_input(source)
        cmd=['wsl.exe','-d','Debian','--exec','/usr/bin/ffmpeg','-hide_banner','-nostdin',
             '-i',cls._wsl_path(p),'-af','loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json',
             '-vn','-f','null','-']
        out=cls._run(cmd,timeout)
        # json printed to STDERR after filtering; the last loudnorm JSON object wins.
        objs=re.findall(r'\{\s*"input_i".*?\}',out.stderr,flags=re.DOTALL)
        if not objs:raise RuntimeError('Unable to parse FFmpeg loudnorm measurement')
        d=json.loads(objs[-1])
        fields=('input_i','input_tp','input_lra','input_thresh','target_offset')
        measured={}
        for field in fields:
            try:measured[field]=float(d[field])
            except (ValueError,KeyError,TypeError):measured[field]=None
        return {'backend':'Debian FFmpeg loudnorm','source':str(p),
                'integrated_lufs':measured['input_i'],
                'true_peak_dbtp':measured['input_tp'],
                'loudness_range_lu':measured['input_lra'],
                'absolute_threshold_lufs':measured['input_thresh'],
                'parameters':measured,
                'calibration':'FFmpeg loudnorm analysis, not Audition Match Loudness'}

    @classmethod
    def master_loudness(cls,source,destination,*,target_lufs=-16.0,
                        ceiling_dbtp=-1.5,rate=48000,confirm=False):
        src=cls._qa_input(source)
        dst=cls._qa_output(src,destination)
        loud=cls._f(target_lufs,-36,-8,'target LUFS')
        ceiling=cls._f(ceiling_dbtp,-9,-.1,'true peak ceiling')
        if type(rate)!=int or rate not in (16000,32000,44100,48000,96000):
            raise ValueError('Unsupported rate')
        if not confirm:return {'dry_run':True,'source':str(src),'output':str(dst),'target_lufs':loud}
        analysis=cls.measure_r128_ffmpeg(src)
        p=analysis['parameters']
        if any(p[k] is None or not math.isfinite(p[k]) for k in ('input_i','input_tp','input_lra','input_thresh','target_offset')):
            raise RuntimeError('Cannot loudnorm an invalid or silent measurement')
        args=[f'I={loud}',f'TP={ceiling}','LRA=11',
            f'measured_I={p["input_i"]}',f'measured_TP={p["input_tp"]}',
            f'measured_LRA={p["input_lra"]}',f'measured_thresh={p["input_thresh"]}',
            f'offset={p["target_offset"]}','linear=true','print_format=json']
        af='loudnorm='+':'.join(args)
        fmt=dst.suffix.lower()
        codec={'.wav':'pcm_s24le','.flac':'flac','.mp3':'libmp3lame','.m4a':'aac'}[fmt]
        cmd=['wsl.exe','-d','Debian','--exec','/usr/bin/ffmpeg','-nostdin','-hide_banner',
             '-loglevel','error','-n','-i',cls._wsl_path(src),
             '-af',af,'-ar',str(rate),'-c:a',codec]
        if fmt in ('.mp3','.m4a'):cmd+=['-b:a','192k']
        cmd.append(cls._wsl_path(dst))
        cls._run(cmd,120)
        if not dst.is_file() or dst.stat().st_size<100:raise RuntimeError('No output after mastering')
        proof=cls.ffprobe_media(dst)
        measure=cls.measure_r128_ffmpeg(dst)
        accepted=(measure['integrated_lufs'] is not None and
                  abs(measure['integrated_lufs']-loud)<1.2 and
                  measure['true_peak_dbtp'] is not None and
                  measure['true_peak_dbtp']<=ceiling+.45)
        return {'source':str(src),'output':str(dst),'sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),
                'codec':proof.get('streams',[{}])[0].get('codec_name'),
                'target_lufs':loud,'target_true_peak_dbtp':ceiling,
                'measured_before':analysis,'measured_after':measure,
                'qa_passed':accepted,'backend':'Debian FFmpeg two-pass loudnorm',
                'native_audition_effect':False}

    @classmethod
    def speech_cleanup(cls,source,destination,*,highpass_hz=85.0,
                       denoise_db=9.0,threshold_db=-22.0,ratio=2.5,
                       confirm=False):
        src=cls._qa_input(source);dst=cls._qa_output(src,destination,suffixes=('.wav',))
        hp=cls._f(highpass_hz,20,500,'highpass')
        reduction=cls._f(denoise_db,0,25,'denoise')
        thresh=cls._f(threshold_db,-45,-8,'threshold')
        comp=cls._f(ratio,1,10,'ratio')
        filters=[f'highpass=f={hp:g}']
        if reduction>.01:filters.append(f'afftdn=nr={reduction:g}')
        filters.append(f'acompressor=threshold={10**(thresh/20):.6f}:ratio={comp:g}:attack=20:release=180')
        filters.append('alimiter=limit=0.90:level=0')
        if not confirm:return {'dry_run':True,'filters':filters,'destination':str(dst)}
        cmd=['wsl.exe','-d','Debian','--exec','/usr/bin/ffmpeg','-nostdin','-hide_banner',
             '-loglevel','error','-n','-i',cls._wsl_path(src),'-af',','.join(filters),
             '-c:a','pcm_f32le',cls._wsl_path(dst)]
        cls._run(cmd,100)
        p=cls.ffprobe_media(dst)
        return {'source':str(src),'output':str(dst),'filters':filters,
                'codec':p['streams'][0]['codec_name'],
                'duration':float(p['format']['duration']),
                'sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),
                'native_audition_effect':False}

    @classmethod
    def mix_audio_stems(cls,stems:list[dict],destination,*,rate=48000,
                        output_ceiling=.90,confirm=False):
        if not isinstance(stems,list) or not 2<=len(stems)<=8:
            raise ValueError('2 to 8 stem specifications required')
        if type(rate)!=int or rate not in (44100,48000,96000):
            raise ValueError('Unsupported output rate')
        cap=cls._f(output_ceiling,.5,.99,'output ceiling')
        sources=[];gains=[];delays=[]
        for entry in stems:
            if not isinstance(entry,dict):raise ValueError('Stem dict expected')
            src=cls._qa_input(entry.get('source'))
            gain=cls._f(entry.get('gain_db',0),-60,12,'stem gain')
            delay=cls._f(entry.get('delay_seconds',0),0,60,'stem delay')
            sources.append(src);gains.append(gain);delays.append(delay)
        if len(set(sources))!=len(sources):raise ValueError('Inputs must be unique files')
        dst=cls._qa_output(sources[0],destination,suffixes=('.wav',))
        if dst in sources:raise ValueError('Cannot overwrite any input stem')
        if not confirm:return {'dry_run':True,'sources':[str(x) for x in sources],'destination':str(dst)}
        filters=[]
        for i,(db,delay) in enumerate(zip(gains,delays)):
            milli=int(round(delay*1000))
            filters.append(f'[{i}:a]aresample={rate},aformat=channel_layouts=stereo,'
                           f'volume={10**(db/20):.8f},adelay={milli}:all=1[s{i}]')
        pads=''.join(f'[s{i}]' for i in range(len(stems)))
        filters.append(pads+f'amix=inputs={len(stems)}:duration=longest:dropout_transition=0,'
                       f'alimiter=limit={cap}:level=0[out]')
        args=['wsl.exe','-d','Debian','--exec','/usr/bin/ffmpeg',
              '-nostdin','-hide_banner','-loglevel','error','-n']
        for src in sources:args+=['-i',cls._wsl_path(src)]
        args+=['-filter_complex',';'.join(filters),'-map','[out]','-ar',str(rate),
               '-c:a','pcm_f32le',cls._wsl_path(dst)]
        cls._run(args,120)
        check=cls.ffprobe_media(dst)
        return {'backend':'Debian FFmpeg complex amix','native_audition_mixdown':False,
                'stems':len(stems),'output':str(dst),'codec':check['streams'][0]['codec_name'],
                'channels':check['streams'][0]['channels'],
                'duration':float(check['format']['duration']),
                'sha256':hashlib.sha256(dst.read_bytes()).hexdigest()}
