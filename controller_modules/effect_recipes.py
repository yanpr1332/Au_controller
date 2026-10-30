"""Safe FFmpeg effect graphs for Audition production workflows (external DSP).

Only a typed whitelist of filter operations is accepted; arbitrary FFmpeg
filter expressions or user-supplied shell fragments are prohibited.
Input files must exist and are immutable. Output files must be new.
Native Audition effects are NOT claimed.
"""
from __future__ import annotations
from pathlib import Path
import math,hashlib,json,subprocess,tempfile,shutil

class AuditionEffectRecipes:
    @staticmethod
    def _num(spec,name,lo,hi,default=None):
        value=spec.get(name,default)
        if isinstance(value,bool) or not isinstance(value,(float,int)):
            raise ValueError(f'{name} requires numeric value')
        value=float(value)
        if not math.isfinite(value) or not lo<=value<=hi:
            raise ValueError(f'{name} outside [{lo},{hi}]')
        return value

    @classmethod
    def _effect_to_filter(cls,item):
        if not isinstance(item,dict) or not isinstance(item.get('effect'),str):
            raise ValueError('Each effect must be a dict with effect name')
        effect=item['effect']
        schema={
            'highpass':{'hz'},'lowpass':{'hz'},
            'bandpass':{'hz','bandwidth_hz'},'notch':{'hz','bandwidth_hz'},
            'equalizer':{'hz','db','width_octaves'},
            'declick':set(),'declip':set(),
            'fft_denoise':{'reduction_db'},'nlm_denoise':set(),
            'deesser':set(),
            'compressor':{'threshold_db','ratio','attack_ms','release_ms'},
            'gate':{'threshold_db','ratio','attack_ms','release_ms'},
            'limiter':{'ceiling_dbfs'},
            'hum_50':set(),'hum_60':set(),
            'volume':{'db'},
            'delay':{'ms','decay'},
            'chorus':set(),'flanger':set(),
            'tempo':{'multiplier'},'pitch':{'semitones'},
            'fade_in':{'seconds'},'fade_out':{'start_seconds','seconds'},
            'trim':{'start_seconds','duration_seconds'},
            'silence_trim':{'threshold_db','min_seconds'},
            'reverse':set(),
            'mono':set(),
            'dc_remove':set(),
            'dynaudnorm':set(),
        }
        if effect not in schema:raise ValueError('Unsupported effect '+effect)
        if set(item)-{'effect'}-schema[effect]:
            raise ValueError('Unrecognized effect parameter: '+str(set(item)-{'effect'}-schema[effect]))
        num=lambda n,a,b,d:cls._num(item,n,a,b,d)
        if effect=='highpass':
            return f'highpass=f={num("hz",20,10000,90):.4f}'
        if effect=='lowpass':
            return f'lowpass=f={num("hz",50,19000,12000):.4f}'
        if effect=='bandpass':
            return f'bandpass=f={num("hz",30,17000,1000):.4f}:width_type=h:width={num("bandwidth_hz",10,7000,400):.4f}'
        if effect=='notch':
            return f'bandreject=f={num("hz",30,17000,50):.4f}:width_type=h:width={num("bandwidth_hz",.5,200,3):.4f}'
        if effect=='equalizer':
            return f'equalizer=f={num("hz",30,17000,1200):.4f}:t=o:w={num("width_octaves",.15,4,1):.5f}:g={num("db",-12,12,0):.3f}'
        if effect=='declick':return 'adeclick'
        if effect=='declip':return 'adeclip'
        if effect=='fft_denoise':
            return f'afftdn=nr={num("reduction_db",.1,25,8):.3f}'
        if effect=='nlm_denoise':return 'anlmdn'
        if effect=='deesser':return 'deesser'
        if effect=='compressor':
            th=num('threshold_db',-50,-1,-22)
            ratio=num('ratio',1.1,12,3)
            att=num('attack_ms',1,200,20)
            rel=num('release_ms',20,1500,180)
            return f'acompressor=threshold={10**(th/20):.8f}:ratio={ratio:.4f}:attack={att:.3f}:release={rel:.3f}'
        if effect=='gate':
            th=num('threshold_db',-70,-5,-42)
            return f'agate=threshold={10**(th/20):.8f}:ratio={num("ratio",1.1,10,2.5):.4f}:attack={num("attack_ms",1,100,10):.3f}:release={num("release_ms",20,2000,150):.3f}'
        if effect=='limiter':
            limit=num('ceiling_dbfs',-12,-.1,-1.5)
            return f'alimiter=limit={10**(limit/20):.8f}:level=0'
        if effect in ('hum_50','hum_60'):
            freq=50 if effect=='hum_50' else 60
            # Three narrow notches at fundamental and first two harmonics.
            return ','.join(f'bandreject=f={freq*x}:width_type=h:width=3' for x in (1,2,3))
        if effect=='volume':
            return f'volume={10**(num("db",-48,12,0)/20):.8f}'
        if effect=='delay':
            t=num('ms',10,700,180);decay=num('decay',.02,.8,.25)
            return f'aecho=in_gain=0.8:out_gain=0.45:delays={t:.3f}:decays={decay:.4f}'
        if effect=='chorus':
            return 'chorus=0.6:0.75:40:0.25:0.25:2'
        if effect=='flanger':
            return 'flanger=delay=0:depth=2:regen=0:width=71:speed=0.4'
        if effect=='tempo':
            return f'atempo={num("multiplier",.5,2,1):.6f}'
        if effect=='pitch':
            # Native lib rubberband present in the current Debian FFmpeg build.
            semitones=num('semitones',-12,12,0)
            return f'rubberband=pitch={2**(semitones/12):.8f}'
        if effect=='fade_in':
            return f'afade=t=in:st=0:d={num("seconds",.005,60,1):.5f}'
        if effect=='fade_out':
            start=num('start_seconds',0,36000,0)
            dur=num('seconds',.005,60,1)
            return f'afade=t=out:st={start:.5f}:d={dur:.5f}'
        if effect=='trim':
            return f'atrim=start={num("start_seconds",0,36000,0):.5f}:duration={num("duration_seconds",.02,36000,1):.5f},asetpts=PTS-STARTPTS'
        if effect=='silence_trim':
            th=num('threshold_db',-80,-15,-45)
            dur=num('min_seconds',.02,3,.2)
            return (f'silenceremove=start_periods=1:start_duration={dur:.4f}:start_threshold={th:.2f}dB:'
                    f'stop_periods=-1:stop_duration={dur:.4f}:stop_threshold={th:.2f}dB')
        if effect=='reverse':return 'areverse'
        if effect=='mono':return 'aformat=channel_layouts=mono'
        if effect=='dc_remove':return 'highpass=f=20'
        if effect=='dynaudnorm':return 'dynaudnorm=f=250:g=9:p=0.85'
        raise ValueError('Unreachable effect')

    @classmethod
    def effects_recipe_validate(cls,effects,*,max_effects=16):
        if not isinstance(effects,list) or not 1<=len(effects)<=max_effects:
            raise ValueError('1..16 effect specifications required')
        graph=[]
        for item in effects:
            graph.append(cls._effect_to_filter(item))
        return {'effects':len(graph),'filters':graph,'graph':','.join(graph),
                'execution_backend':'WSL Debian FFmpeg','native_audition_effects':False}

    @classmethod
    def render_audio_effects(cls,source,destination,effects,*,sample_rate=48000,
                             final_ceiling_dbfs=-1.0,confirm=False):
        inp=cls._qa_input(source)
        out=cls._qa_output(inp,destination,suffixes=('.wav','.flac','.mp3','.m4a'))
        if type(sample_rate)!=int or sample_rate not in (16000,22050,32000,44100,48000,96000):
            raise ValueError('Invalid output sample rate')
        ceiling=cls._num({'ceiling_dbfs':final_ceiling_dbfs},'ceiling_dbfs',-9,-.1,-1.0)
        recipe=cls.effects_recipe_validate(effects)
        graph=recipe['graph']+f',aresample={sample_rate},alimiter=limit={10**(ceiling/20):.8f}:level=0'
        if not confirm:
            return {'dry_run':True,'source':str(inp),'output':str(out),'graph':graph,
                    'native_audition_effects':False}
        source_hash=hashlib.sha256(inp.read_bytes()).hexdigest()
        codec={'.wav':'pcm_f32le','.flac':'flac','.mp3':'libmp3lame','.m4a':'aac'}[out.suffix.lower()]
        args=['wsl.exe','-d','Debian','--exec','/usr/bin/ffmpeg','-nostdin','-hide_banner',
              '-loglevel','error','-n','-i',cls._wsl_path(inp),'-af',graph,
              '-ar',str(sample_rate),'-c:a',codec]
        if out.suffix.lower() in ('.mp3','.m4a'):
            args+=['-b:a','192k']
        args+=[cls._wsl_path(out)]
        try:
            cls._run(args,120)
            if not out.is_file() or out.stat().st_size<100:raise RuntimeError('No real output')
            probe=cls.ffprobe_media(out)
            stats=cls.audio_forensics(out) if out.suffix.lower()=='.wav' else None
            valid=hashlib.sha256(inp.read_bytes()).hexdigest()==source_hash
            if not valid:raise RuntimeError('Input source modified')
            if stats and (stats['peak_dbfs']>0.08 or stats['integer_or_float_clipping_samples']):
                raise RuntimeError('Audio output clipping QC failed')
            return {'passed':True,'output':str(out),'source':str(inp),
                    'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),
                    'source_sha256':source_hash,'input_unchanged':True,
                    'codec':probe['streams'][0]['codec_name'],
                    'channels':probe['streams'][0]['channels'],
                    'duration':float(probe['format']['duration']),
                    'sample_peak_dbfs':stats['peak_dbfs'] if stats else None,
                    'recipe':recipe,'final_ceiling_dbfs':ceiling,
                    'native_audition_effects':False}
        except Exception:
            if out.is_file():out.unlink()
            raise

    @classmethod
    def batch_effect_recipes(cls,jobs,*,confirm=False):
        """Run up to 24 typed jobs (reproducible effects) without overriding outputs."""
        if not isinstance(jobs,list) or not 1<=len(jobs)<=24:
            raise ValueError('1..24 jobs expected')
        planned=[]
        for job in jobs:
            if not isinstance(job,dict) or set(job)-{'source','destination','effects','sample_rate'}:
                raise ValueError('Unsupported job fields')
            source=cls._qa_input(job['source'])
            dst=cls._qa_output(source,job['destination'],suffixes=('.wav','.flac','.mp3','.m4a'))
            cls.effects_recipe_validate(job['effects'])
            planned.append((source,dst,job))
        destinations=[x[1] for x in planned]
        if len(set(destinations))!=len(destinations):raise ValueError('Duplicate output target in jobs')
        if set(destinations).intersection({x[0] for x in planned}):raise ValueError('Output collides with another input')
        if not confirm:
            return {'dry_run':True,'jobs':len(planned),'outputs':[str(x) for x in destinations]}
        outcomes=[]
        for source,dst,job in planned:
            try:
                result=cls.render_audio_effects(source,dst,job['effects'],
                  sample_rate=job.get('sample_rate',48000),confirm=True)
                outcomes.append(result)
            except Exception as exc:
                outcomes.append({'passed':False,'source':str(source),'output':str(dst),
                                 'error':str(exc)[:300]})
        return {'batch_size':len(planned),'passed_jobs':sum(bool(x['passed']) for x in outcomes),
                'results':outcomes,'backend':'Debian FFmpeg, not native Audition effects'}
