"""Waveform timeline editing and reproducible PCM16 TPDF quantization.

Offline Python/SciPy, not native Audition Edit-menu actions.
No overwrites, external commands, or live Audition document mutations.
"""
from __future__ import annotations
from pathlib import Path
import hashlib,math,os,tempfile
import numpy as np
from scipy.io import wavfile

class AuditionWaveformWorkbench:
    @staticmethod
    def _sha_wb(file):
        h=hashlib.sha256()
        with Path(file).open('rb') as f:
            for part in iter(lambda:f.read(1<<20),b''):h.update(part)
        return h.hexdigest()

    @classmethod
    def _wb_config(cls,source,destination,operations,format,dither,seed):
        src=Path(source).resolve();dst=Path(destination).resolve()
        if not src.is_file() or src.suffix.lower()!='.wav':
            raise ValueError('Existing WAV source required')
        if dst.exists() or dst==src or dst.suffix.lower()!='.wav' or not dst.parent.is_dir():
            raise ValueError('New WAV destination required; no overwrite')
        if format not in ('float32','pcm16'):raise ValueError('Output float32 or pcm16 only')
        if dither not in ('none','tpdf','tpdf_feedback'):raise ValueError('Dither mode invalid')
        if format!='pcm16' and dither!='none':raise ValueError('Dither only meaningful on PCM16')
        if type(seed)!=int or not 0<=seed<=2**32-1:raise ValueError('Invalid deterministic seed')
        if not isinstance(operations,list) or not 1<=len(operations)<=32:
            raise ValueError('1..32 edits required')
        names={'cut':{'start','end'},'delete':{'start','end'},'silence':{'start','end'},
               'insert_silence':{'at','frames'},'copy_insert':{'at','from_start','from_end'},
               'gain_region':{'start','end','db'},'fade_region':{'start','end','edge'}}
        for e in operations:
            if not isinstance(e,dict) or e.get('action') not in names:raise ValueError('Unsupported action')
            action=e['action']
            required=names[action]
            if set(e)!={'action'}|required:raise ValueError('Exact typed fields required')
            for key in required-{'edge','db'}:
                if type(e[key])!=int or e[key]<0 or e[key]>60_000_000:
                    raise ValueError('Expected nonnegative integer frame position: '+key)
            if action=='gain_region':
                db=e['db']
                if isinstance(db,bool) or not isinstance(db,(int,float)) or not math.isfinite(db) or not -100<=db<=18:
                    raise ValueError('Gain must be -100..18 dB')
            if action=='fade_region' and e['edge'] not in ('in','out'):
                raise ValueError('Fade edge must be in or out')
        return src,dst

    @staticmethod
    def _pcm16_quantize(x,dither,seed):
        if not len(x):raise ValueError('Audio cannot be empty')
        if float(np.max(np.abs(x)))>1.000001:
            raise ValueError('Input exceeds 0 dBFS; explicit limiter/normalization required')
        y=x*32768
        if dither=='none':
            return np.clip(np.rint(y),-32768,32767).astype(np.int16)
        rng=np.random.default_rng(seed)
        if dither=='tpdf':
            noise=rng.random(y.shape)-rng.random(y.shape)
            return np.clip(np.rint(y+noise),-32768,32767).astype(np.int16)
        # Bounded first-order error feedback, per channel.
        # This is a practical first-order shaping heuristic, NOT a proprietary
        # Audition noise-shaping preset.
        z=np.empty(y.shape,dtype=np.int16)
        error=np.zeros(y.shape[1],dtype=float)
        for i in range(len(y)):
            noisy=y[i]+.75*error+rng.random(y.shape[1])-rng.random(y.shape[1])
            q=np.clip(np.rint(noisy),-32768,32767)
            z[i]=q.astype(np.int16)
            error=np.clip((y[i]+.75*error)-q,-2,2)
        return z

    @classmethod
    def edit_wav_timeline(cls,source,destination,operations,*,format='float32',
                          dither='none',seed=19,confirm=False):
        src,dst=cls._wb_config(source,destination,operations,format,dither,seed)
        if not confirm:
            return {'dry_run':True,'input':str(src),'output':str(dst),
                    'operations':len(operations),'format':format,'dither':dither}
        prior=cls._sha_wb(src)
        sr,x,metadata=cls._read_wav(src)
        original=x.copy()
        for e in operations:
            name=e['action']
            if name=='copy_insert':
                a,b,at=e['from_start'],e['from_end'],e['at']
                if not 0<=a<b<=len(original) or not 0<=at<=len(x):
                    raise ValueError('Copy segment/source position exceeds sample length')
                x=np.concatenate((x[:at],original[a:b],x[at:]),axis=0)
            elif name=='insert_silence':
                at,n=e['at'],e['frames']
                if at>len(x) or n<1:raise ValueError('Silence insertion invalid')
                x=np.concatenate((x[:at],np.zeros((n,x.shape[1])),x[at:]),axis=0)
            else:
                a,b=e['start'],e['end']
                if not 0<=a<b<=len(x):raise ValueError('Region outside waveform')
                if name in ('cut','delete'):
                    x=np.concatenate((x[:a],x[b:]),axis=0)
                elif name=='silence':x[a:b]=0
                elif name=='gain_region':x[a:b]*=10**(float(e['db'])/20)
                elif name=='fade_region':
                    curve=np.linspace(0,1,b-a)
                    if e['edge']=='out':curve=curve[::-1]
                    x[a:b]*=curve[:,None]
            if not 0<len(x)<=sr*cls.MAX_SECONDS or x.size>cls.MAX_SAMPLES:
                raise ValueError('Bounded output duration/sample budget exceeded')
        if not np.all(np.isfinite(x)):raise ValueError('Nonfinite DSP result')
        if float(np.max(np.abs(x)))>1.000001:raise ValueError('Output would clip')
        arr=cls._pcm16_quantize(x,dither,seed) if format=='pcm16' else x.astype(np.float32)
        if arr.shape[1]==1:arr=arr[:,0]
        # Stage with a unique extension to keep final destination untouched until success.
        fd,temp=tempfile.mkstemp(prefix='.audition_wav_stage_',suffix='.wav',dir=str(dst.parent))
        os.close(fd)
        stage=Path(temp)
        try:
            wavfile.write(stage,sr,arr)
            rate,readback=wavfile.read(stage)
            if rate!=sr or len(readback)!=len(x):raise RuntimeError('WAV frame readback failed')
            if cls._sha_wb(src)!=prior:raise RuntimeError('Source changed during edit')
            os.link(stage,dst)  # hard-link publish without overwriting existing output
        finally:
            stage.unlink(missing_ok=True)
        report=cls.audio_signal_report(dst)
        return {'passed':True,'source':str(src),'output':str(dst),'source_unchanged':True,
                'source_sha256':prior,'output_sha256':cls._sha_wb(dst),
                'format':format,'dither':dither,'seed':seed,'operations':len(operations),
                'sample_rate':sr,'original_frames':metadata['frames'],
                'output_frames':len(x),'channels':metadata['channels'],
                'peak_dbfs':report['peak_dbfs'],
                'backend':'SciPy timeline + deterministic PCM quantization; not native Audition'}

    @classmethod
    def export_fft_spectrum(cls,source,destination,*,window=4096,confirm=False):
        import json
        from scipy import signal
        src=Path(source).resolve();dst=Path(destination).resolve()
        if not src.is_file() or src.suffix.lower()!='.wav' or dst.exists() or dst.suffix.lower()!='.json' or not dst.parent.is_dir():
            raise ValueError('Existing WAV, brand new JSON output')
        if type(window)!=int or not 512<=window<=16384 or window&(window-1):
            raise ValueError('FFT window must be power of two 512..16384')
        if not confirm:return {'dry_run':True,'source':str(src),'destination':str(dst),'fft_window':window}
        sr,x,metadata=cls._read_wav(src)
        if len(x)<window:raise ValueError('WAV shorter than FFT window')
        bins,power=signal.welch(x.mean(axis=1),sr,nperseg=window)
        db=10*np.log10(np.maximum(power,1e-20))
        k=int(np.argmax(power[1:])+1)
        report={'source':str(src),'source_sha256':cls._sha_wb(src),'sample_rate':sr,
                'fft_size':window,'frequencies_hz':[float(v) for v in bins],
                'power_db':[float(v) for v in db],
                'dominant_frequency_hz':float(bins[k]),'backend':'SciPy Welch, not Audition spectral view'}
        blob=json.dumps(report,ensure_ascii=False,indent=2)
        # exclusive create prevents races/overwrites
        with dst.open('x',encoding='utf8') as f:f.write(blob)
        return {'output':str(dst),'sha256':cls._sha_wb(dst),'dominant_frequency_hz':float(bins[k]),
                'bins':len(bins),'source_sha256':report['source_sha256']}
