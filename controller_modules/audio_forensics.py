"""Audition offline signal forensics: objective sample statistics + labeled heuristics.

This is NOT Adobe Audition native analysis and NOT a certified EBU R128 meter.
Reads sources without mutation; supports PCM/float WAV already covered by AudioLab.
"""
from __future__ import annotations
import json
import math
import hashlib
from pathlib import Path
import numpy as np
from scipy import signal

class AuditionAudioForensics:
    @staticmethod
    def _db(value):
        return float(20*np.log10(max(float(value),1e-12)))

    @classmethod
    def audio_forensics(cls,source,*,window_ms=100,true_peak_factor=4):
        if type(window_ms)!=int or not 10<=window_ms<=500:
            raise ValueError('window_ms must be 10..500')
        if type(true_peak_factor)!=int or true_peak_factor not in (1,2,4):
            raise ValueError('true_peak_factor must be 1/2/4')
        sr,x,meta=cls._read_wav(source)
        size=max(1,round(sr*window_ms/1000))
        samples=len(x)
        n=math.ceil(samples/size)
        rms=np.zeros(n,dtype=float)
        pk=np.zeros(n,dtype=float)
        for k in range(n):
            chunk=x[k*size:(k+1)*size]
            rms[k]=np.sqrt(np.mean(chunk*chunk))
            pk[k]=np.max(np.abs(chunk))
        frame_db=np.asarray([cls._db(v) for v in rms])
        silences=[]
        start=None
        # Frames below -55 dBFS RMS are "near-silence", not speech detection.
        active=frame_db>-55
        for i,val in enumerate(active):
            if not val and start is None:start=i
            elif val and start is not None:
                if i-start>=2:silences.append([round(start*size/sr,3),round(min(i*size/sr,samples/sr),3)])
                start=None
        if start is not None and n-start>=2:silences.append([round(start*size/sr,3),round(samples/sr,3)])
        peak=float(np.max(np.abs(x)))
        # Bound memory: upsample in blocks, each padded to reduce boundary error;
        # approx. true peak per ITU P.1826, NOT an independently certified TP meter.
        truepeak=peak
        if true_peak_factor>1:
            block=max(sr,32768)
            for pos in range(0,len(x),block):
                raw=x[max(0,pos-24):min(len(x),pos+block+24)]
                up=signal.resample_poly(raw,true_peak_factor,1,axis=0)
                truepeak=max(truepeak,float(np.max(np.abs(up))))
        rms_full=float(np.sqrt(np.mean(x*x)))
        # Derivative spike heuristic rejects truly silent clips; no generic digital-clipping claim.
        delta=np.max(np.abs(np.diff(x,axis=0)),axis=1) if len(x)>1 else np.array([])
        near=np.maximum(np.max(np.abs(x[:-1]),axis=1),np.max(np.abs(x[1:]),axis=1)) if len(x)>1 else np.array([])
        spike_idx=np.flatnonzero((delta>0.55)&(near>0.20))
        # collapse sequential spikes into events
        ticks=[]
        for idx in spike_idx:
            if not ticks or idx-ticks[-1]>int(sr*.008):ticks.append(int(idx))
        # Generate spectral power diagnostics, no human-speech classification claims.
        mono=np.mean(x,axis=1)
        freqs,psd=signal.welch(mono,fs=sr,nperseg=min(8192,len(mono)))
        def band(lo,hi):
            mask=(freqs>=lo)&(freqs<hi)
            return float(np.sum(psd[mask]))
        power=float(np.sum(psd))
        low=band(5,min(80,sr*.48))/max(power,1e-30)
        presence=band(300,min(3400,sr*.48))/max(power,1e-30)
        hi=band(8000,min(20000,sr*.48))/max(power,1e-30) if sr>16000 else 0
        hum={}
        for hz in (50,60):
            j=int(np.argmin(np.abs(freqs-hz)))
            lo=max(1,j-6);hi=min(len(psd),j+7)
            neighbors=np.r_[psd[lo:max(lo,j-1)],psd[min(hi,j+2):hi]]
            contrast=float(10*np.log10((psd[j]+1e-30)/(np.median(neighbors)+1e-30))) if len(neighbors) else 0
            hum[str(hz)]={'contrast_db':round(contrast,3),
                           'suspected':bool(contrast>16 and psd[j]>power*0.002)}
        stereo=None
        if x.shape[1]==2:
            L,R=x[:,0],x[:,1]
            mean=(L+R)*.5
            side=(L-R)*.5
            lc=np.std(L);rc=np.std(R)
            corr=float(np.corrcoef(L,R)[0,1]) if lc>1e-8 and rc>1e-8 else None
            stereo={'correlation':corr,
                'mid_dbfs':cls._db(np.sqrt(np.mean(mean*mean))),
                'side_dbfs':cls._db(np.sqrt(np.mean(side*side))),
                'left_peak_dbfs':cls._db(np.max(np.abs(L))),
                'right_peak_dbfs':cls._db(np.max(np.abs(R))),
                'mono_fold_down_peak_dbfs':cls._db(np.max(np.abs(mean))),
                'anti_phase_warning':bool(corr is not None and corr<-.2)}
        outputs={'source':str(source),'sha256':hashlib.sha256(Path(source).read_bytes()).hexdigest(),
          'sample_rate':sr,'channels':meta['channels'],'frames':samples,
          'duration_seconds':round(samples/sr,6),'window_ms':window_ms,
          'peak_dbfs':round(cls._db(peak),3),'rms_dbfs':round(cls._db(rms_full),3),
          'crest_db':round(cls._db(peak/max(rms_full,1e-12)),3),
          'approx_true_peak_dbtp':round(cls._db(truepeak),3),
          'true_peak_factor':true_peak_factor,
          'integer_or_float_clipping_samples':int(np.sum(np.abs(x)>=.99999)),
          'near_silence_regions_seconds':silences,
          'near_silence_fraction':round(float(np.mean(~active)),4),
          'transient_spike_candidates_seconds':[round(t/sr,5) for t in ticks[:200]],
          'candidate_spike_count':len(ticks),
          'low_band_energy_share':round(low,5),
          'speech_presence_band_share':round(presence,5),
          'high_band_energy_share':round(hi,5),
          'hum':hum,'stereo':stereo,
          'limitations':['Spike/hum flags are heuristics, not proof of defects',
                         'Approximate true peak is not certified BS.1770/EBU R128',
                         'Window RMS silence is not speech recognition or diarization'],
          'backend':'SciPy offline signal forensics'}
        return outputs

    @classmethod
    def qc_audio_profile(cls,source,profile='podcast',*,profile_override=None):
        standard={
          'podcast':{'max_sample_peak_dbfs':-1.0,'max_dc':.015,'maximum_silence_fraction':.95,
                     'max_candidate_spikes':30,'min_duration':.1},
          'broadcast':{'max_sample_peak_dbfs':-1.0,'max_dc':.01,'maximum_silence_fraction':.95,
                       'max_candidate_spikes':10,'min_duration':.1},
          'music':{'max_sample_peak_dbfs':-.1,'max_dc':.02,'maximum_silence_fraction':.98,
                   'max_candidate_spikes':40,'min_duration':.1}}
        if profile not in standard:raise ValueError('Profile must be podcast/broadcast/music')
        limits=dict(standard[profile])
        if profile_override:
            if not isinstance(profile_override,dict) or not set(profile_override).issubset(limits):
                raise ValueError('Invalid profile overrides')
            for key,value in profile_override.items():
                if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(float(value)):
                    raise ValueError('Numeric profile overrides only')
                limits[key]=value
        analysis=cls.audio_forensics(source)
        dc=cls.audio_signal_report(source)['dc_offset']
        checks={
          'sample_peak_headroom':analysis['peak_dbfs']<=limits['max_sample_peak_dbfs']+.03,
          'dc_offset':max(abs(z) for z in dc)<=limits['max_dc'],
          'no_digital_clipping':analysis['integer_or_float_clipping_samples']==0,
          'not_nearly_silent':analysis['near_silence_fraction']<=limits['maximum_silence_fraction'],
          'transient_spikes':analysis['candidate_spike_count']<=limits['max_candidate_spikes'],
          'minimum_duration':analysis['duration_seconds']>=limits['min_duration']}
        return {'profile':profile,'limits':limits,'passed':all(checks.values()),
                'checks':checks,'analysis':analysis,
                'broadcast_loudness_verified':False,
                'note':'Sample-based QC only: use measure_r128_ffmpeg separately for LUFS and dBTP.'}

    @classmethod
    def export_audio_qc_report(cls,source,destination,*,profile='podcast',confirm=False):
        out=Path(destination).resolve()
        if out.exists() or out.suffix.lower()!='.json' or not out.parent.is_dir():
            raise ValueError('QC destination must be a new JSON file')
        if not confirm:return {'dry_run':True,'output':str(out),'profile':profile}
        r=cls.qc_audio_profile(source,profile=profile)
        out.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf8')
        return {'path':str(out),'passed':r['passed'],
                'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'profile':profile}
