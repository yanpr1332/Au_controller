"""Repeatable audio QC and batched DSP pipelines with immutable inputs."""
from __future__ import annotations
from pathlib import Path
import math,hashlib,json
import numpy as np
from scipy.io import wavfile

class AuditionBatchLab:
    @classmethod
    def audio_quality_gate(cls,path:str|Path,*,max_peak_dbfs:float=0.0,
                           max_dc:float=.01,allow_clips:int=0)->dict:
        a=cls.audio_signal_report(path)
        checks={'peak_below_limit':a['peak_dbfs']<=max_peak_dbfs+0.02,
                'dc_offset':max(abs(v) for v in a['dc_offset'])<=max_dc,
                'no_clipped_samples':a['clipped_samples']<=allow_clips}
        return {'passed':all(checks.values()),'checks':checks,'analysis':a}

    @classmethod
    def activity_regions(cls,path:str|Path,*,threshold_dbfs:float=-35.0,
                         window_ms:int=20,min_active_ms:int=80)->dict:
        sr,a,info=cls._read_wav(path)
        if not (-100<=threshold_dbfs<=0) or type(window_ms)!=int or not 5<=window_ms<=200:
            raise ValueError('Invalid activity threshold/window')
        if type(min_active_ms)!=int or not 5<=min_active_ms<=5000:
            raise ValueError('Invalid activity minimum')
        size=max(1,round(sr*window_ms/1000))
        count=len(a)//size
        if count==0:return {'regions':[],'total_active_seconds':0,'threshold_dbfs':threshold_dbfs}
        windows=a[:count*size].reshape(count,size,a.shape[1])
        rms=np.sqrt(np.mean(windows**2,axis=(1,2)))
        active=rms>10**(threshold_dbfs/20)
        regs=[];start=None
        for i,v in enumerate(active):
            if v and start is None:start=i
            if not v and start is not None:
                if (i-start)*window_ms>=min_active_ms:
                    regs.append({'start_seconds':round(start*size/sr,4),
                                 'end_seconds':round(i*size/sr,4)})
                start=None
        if start is not None and (len(active)-start)*window_ms>=min_active_ms:
            regs.append({'start_seconds':round(start*size/sr,4),
                         'end_seconds':round(len(active)*size/sr,4)})
        return {'source':str(path),'backend':'window RMS activity detector',
                'not_speech_recognition':True,'threshold_dbfs':threshold_dbfs,
                'regions':regs,'total_active_seconds':round(sum(x['end_seconds']-x['start_seconds'] for x in regs),4)}

    @classmethod
    def batch_dsp(cls,sources:list[str|Path],output_folder:str|Path,operations:list[dict],*,
                  confirm:bool=False)->dict:
        folder=Path(output_folder).resolve()
        if not folder.is_dir():raise ValueError('Existing output directory required')
        if not isinstance(sources,list) or not 1<=len(sources)<=100:
            raise ValueError('Batch size must be 1..100')
        srcs=[Path(x).resolve() for x in sources]
        if len(set(srcs))!=len(srcs) or any(not x.is_file() or x.suffix.lower()!='.wav' for x in srcs):
            raise ValueError('Unique existing source WAVs required')
        outputs=[folder/(x.stem+'_audition_processed.wav') for x in srcs]
        if len(set(outputs))!=len(outputs) or any(x.exists() or x==y for x,y in zip(outputs,srcs)):
            raise FileExistsError('Output collision or overwrite risk')
        if not confirm:return {'dry_run':True,'job_count':len(srcs),'outputs':[str(x) for x in outputs]}
        results=[]
        for src,out in zip(srcs,outputs):
            row={'source':str(src),'destination':str(out)}
            try:
                original_sha=hashlib.sha256(src.read_bytes()).hexdigest()
                row['processing']=cls.process_wav(src,out,operations,confirm=True)
                row['quality']=cls.audio_quality_gate(out)
                row['source_intact']=hashlib.sha256(src.read_bytes()).hexdigest()==original_sha
                row['passed']=row['source_intact'] and row['quality']['passed']
            except Exception as e:
                row['error']=repr(e);row['passed']=False
            results.append(row)
        return {'total':len(srcs),'success':sum(x['passed'] for x in results),
                'results':results,'native_audition_operation':False}
