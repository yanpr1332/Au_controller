"""Safe, auditable WAV operations for Audition workflows.

These run in Python/SciPy, NOT Audition ExtendScript. They complement native commands
and never overwrite source files or silently claim native effect processing.
"""
from __future__ import annotations
import math
from pathlib import Path
from typing import Any

import numpy as np
from scipy import signal
from scipy.io import wavfile

class AuditionAudioLab:
    MAX_SECONDS=600
    MAX_SAMPLES=48_000*600*8

    @staticmethod
    def _read_wav(source: str | Path) -> tuple[int,np.ndarray,dict]:
        p=Path(source)
        if not p.is_file() or p.suffix.lower()!='.wav':raise ValueError('Existing WAV input required')
        sr,a=wavfile.read(p,mmap=False)
        if a.ndim not in (1,2):raise ValueError('1 or 2-channel WAV required')
        channels=1 if a.ndim==1 else a.shape[1]
        if channels not in (1,2):raise ValueError('Only mono or stereo PCM/float WAV supported')
        if len(a)>AuditionAudioLab.MAX_SECONDS*sr or a.size>AuditionAudioLab.MAX_SAMPLES:
            raise ValueError('Input exceeds bounded duration or sample budget')
        if a.dtype.kind=='f':x=a.astype(np.float64)
        elif a.dtype.kind=='u':
            offset=2**(a.dtype.itemsize*8-1)
            x=(a.astype(np.float64)-offset)/offset
        elif a.dtype.kind=='i':
            scale=2**(a.dtype.itemsize*8-1)
            x=a.astype(np.float64)/scale
        else:raise TypeError('Unsupported PCM type')
        if not np.all(np.isfinite(x)):raise ValueError('WAV contains nonfinite samples')
        if x.ndim==1:x=x[:,None]
        return int(sr),x,{'source':str(p),'channels':channels,'frames':len(a),'sample_format':str(a.dtype)}

    @staticmethod
    def _numeric(value:Any,name:str,low:float,high:float)->float:
        if isinstance(value,bool) or not isinstance(value,(int,float)):raise ValueError(name+' must be numeric')
        f=float(value)
        if not math.isfinite(f) or not low<=f<=high:raise ValueError(name+f' must be in [{low},{high}]')
        return f

    @classmethod
    def audio_signal_report(cls,source:str|Path,*,fft_window:int=4096)->dict:
        sr,x,info=cls._read_wav(source)
        peak=float(np.max(np.abs(x))) if x.size else 0.
        rms=float(np.sqrt(np.mean(np.square(x)))) if x.size else 0.
        mono=np.mean(x,axis=1)
        if mono.size>=8:
            f,p=signal.welch(mono,sr,nperseg=min(int(fft_window),len(mono)))
            idx=int(np.argmax(p[1:])+1) if len(p)>1 else 0
            dominant=float(f[idx])
            centroid=float(np.sum(f*p)/max(np.sum(p),1e-20))
        else:dominant=centroid=0.
        corr=None
        if x.shape[1]==2:
            if np.std(x[:,0])>1e-10 and np.std(x[:,1])>1e-10:
                corr=float(np.corrcoef(x.T)[0,1])
        dif=np.abs(np.diff(x,axis=0))
        result=dict(info,seconds=len(x)/sr,sample_rate=sr,
                    peak_dbfs=float(20*math.log10(max(peak,1e-12))),
                    rms_dbfs=float(20*math.log10(max(rms,1e-12))),
                    clipped_samples=int(np.sum(np.abs(x)>=.99999)),
                    dc_offset=[float(z) for z in np.mean(x,axis=0)],
                    dominant_hz=dominant,spectral_centroid_hz=centroid,
                    stereo_correlation=corr,
                    peak_step=float(np.max(dif)) if dif.size else 0.)
        return result

    @classmethod
    def process_wav(cls,source:str|Path,destination:str|Path,operations:list[dict],*,
                    confirm:bool=False,output_format:str='pcm16')->dict:
        src=Path(source).resolve()
        dst=Path(destination).resolve()
        if not src.is_file() or dst==src or dst.exists() or not dst.parent.is_dir() or dst.suffix.lower()!='.wav':
            raise ValueError('Input must exist; output must be new .wav in an existing directory')
        if output_format not in ('pcm16','float32'):raise ValueError('Output pcm16 or float32')
        if not isinstance(operations,list) or not 1<=len(operations)<=24 or any(not isinstance(v,dict) for v in operations):
            raise ValueError('1..24 DSP operation objects required')
        # Preflight all operations, including if dry-run; processing only after confirmed.
        actions={'gain_db','peak_normalize','trim','fade','reverse','mono','stereo',
                 'resample','highpass','lowpass','notch','dc_remove','gate','compress',
                 'limit','pad_silence','channel_balance'}
        for op in operations:
            if op.get('type') not in actions:raise ValueError('Unsupported DSP operation '+str(op.get('type')))
        if not confirm:return {'dry_run':True,'source':str(src),'destination':str(dst),'operations':operations}
        sr,x,old=cls._read_wav(src)
        for op in operations:
            name=op['type']
            if name=='gain_db':
                db=cls._numeric(op.get('db'),'gain dB',-120,60)
                x*=10**(db/20)
            elif name=='peak_normalize':
                target=cls._numeric(op.get('target_dbfs',-3),'target dBFS',-50,0)
                p=float(np.max(np.abs(x))) if x.size else 0.
                if p>1e-12:x*=10**(target/20)/p
            elif name=='trim':
                a=cls._numeric(op.get('start',0),'start',0,cls.MAX_SECONDS)
                b=cls._numeric(op.get('end'),'end',0,cls.MAX_SECONDS)
                ia,ib=round(a*sr),round(b*sr)
                if not 0<=ia<ib<=len(x):raise ValueError('Trim must select non-empty range within audio')
                x=x[ia:ib].copy()
            elif name=='fade':
                edge=op.get('edge','in')
                if edge not in ('in','out'):raise ValueError('edge must be in or out')
                seconds=cls._numeric(op.get('seconds'),'fade seconds',0.001,cls.MAX_SECONDS)
                n=round(seconds*sr)
                if n<2 or n>len(x):raise ValueError('Fade exceeds signal length')
                w=np.linspace(0,1,n)
                if edge=='in':x[:n]*=w[:,None]
                else:x[-n:]*=w[::-1,None]
            elif name=='reverse':x=x[::-1].copy()
            elif name=='mono':x=np.mean(x,axis=1,keepdims=True)
            elif name=='stereo':
                if x.shape[1]==1:x=np.repeat(x,2,axis=1)
            elif name=='resample':
                target=int(cls._numeric(op.get('rate'),'sample rate',8000,192000))
                import math as _math
                g=_math.gcd(sr,target)
                x=signal.resample_poly(x,target//g,sr//g,axis=0)
                sr=target
            elif name in ('highpass','lowpass','notch'):
                hz=cls._numeric(op.get('hz'),'frequency Hz',5,sr*.49)
                if len(x)<32:raise ValueError('Insufficient audio for IIR filtering')
                if name=='notch':
                    q=cls._numeric(op.get('q',30),'notch Q',1,200)
                    b,a=signal.iirnotch(hz,q,fs=sr)
                    sos=signal.tf2sos(b,a)
                else:sos=signal.butter(4,hz,fs=sr,btype='highpass' if name=='highpass' else 'lowpass',output='sos')
                x=signal.sosfilt(sos,x,axis=0)
            elif name=='dc_remove':x-=np.mean(x,axis=0)
            elif name=='gate':
                threshold=cls._numeric(op.get('threshold_dbfs',-45),'gate threshold',-100,0)
                p=np.max(np.abs(x),axis=1)
                # Smooth gate to reduce boundary clicks.
                mask=(p>=10**(threshold/20)).astype(float)
                win=max(1,int(sr*.005))
                if win>1:mask=np.convolve(mask,np.ones(win)/win,mode='same')
                x*=mask[:,None]
            elif name=='compress':
                threshold=cls._numeric(op.get('threshold_dbfs',-18),'compress threshold',-80,0)
                ratio=cls._numeric(op.get('ratio',3),'compression ratio',1,30)
                envelope=np.maximum(np.max(np.abs(x),axis=1),1e-12)
                over=np.maximum(20*np.log10(envelope)-threshold,0)
                gain_db=-(1-1/ratio)*over
                # apply simple static shared gain to all channels, not dynamic attack/release
                x*=np.power(10,gain_db/20)[:,None]
            elif name=='limit':
                cap=10**(cls._numeric(op.get('ceiling_dbfs',-1),'ceiling',-30,0)/20)
                x=np.clip(x,-cap,cap)
            elif name=='pad_silence':
                seconds=cls._numeric(op.get('seconds'),'pad seconds',0.001,30)
                side=op.get('side','end')
                if side not in ('start','end'):raise ValueError('side must be start or end')
                z=np.zeros((round(seconds*sr),x.shape[1]),dtype=float)
                x=np.vstack((z,x)) if side=='start' else np.vstack((x,z))
            elif name=='channel_balance':
                if x.shape[1]!=2:raise ValueError('channel_balance requires stereo')
                left=cls._numeric(op.get('left_db',0),'left gain',-60,24)
                right=cls._numeric(op.get('right_db',0),'right gain',-60,24)
                x*=np.array([10**(left/20),10**(right/20)])[None,:]
            if x.size>cls.MAX_SAMPLES or len(x)>sr*cls.MAX_SECONDS:
                raise ValueError('Output exceeds bounded sample budget')
        # Avoid corrupting the final destination if a calculation raises.
        if not np.all(np.isfinite(x)):raise ValueError('Processing generated nonfinite samples')
        if output_format=='pcm16':
            # Never silently saturate signal; caller explicitly requests limiter.
            if float(np.max(np.abs(x)))>1.00001:
                raise ValueError('Output would clip; add peak_normalize or limit operation')
            data=(np.clip(x,-1,1)*32767).round().astype(np.int16)
        else:data=x.astype(np.float32)
        if data.shape[1]==1:data=data[:,0]
        wavfile.write(dst,sr,data)
        info=cls.audio_signal_report(dst)
        info.update({'output':str(dst),'source':str(src),'operations':operations,'backend':'SciPy offline DSP',
                     'native_audition_effect':False,'output_format':output_format})
        return info
