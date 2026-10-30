"""Non-destructive stereo split/join for Audition external-media workflows."""
from __future__ import annotations
from pathlib import Path
import hashlib,os,tempfile
import numpy as np
from scipy.io import wavfile

class AuditionChannelTools:
    @classmethod
    def split_stereo_to_mono(cls,source,left_output,right_output,*,confirm=False):
        src=Path(source).resolve()
        a=Path(left_output).resolve();b=Path(right_output).resolve()
        if not src.is_file() or src.suffix.lower()!='.wav':
            raise ValueError('Existing WAV required')
        if len({a,b,src})!=3 or any(p.exists() or p.suffix.lower()!='.wav' or not p.parent.is_dir() for p in (a,b)):
            raise ValueError('Require two new distinct WAV output names')
        if not confirm:return {'dry_run':True,'source':str(src),'outputs':[str(a),str(b)]}
        digest=cls._sha_wb(src)
        sr,x,info=cls._read_wav(src)
        if x.shape[1]!=2:raise ValueError('Two-channel source required')
        staged=[]
        published=[]
        try:
            for i,dst in enumerate((a,b)):
                fd,temp=tempfile.mkstemp(suffix='.wav',prefix='.audition_channel_',dir=str(dst.parent))
                os.close(fd);p=Path(temp);staged.append((p,dst))
                wavfile.write(p,sr,x[:,i].astype(np.float32))
                r,z=wavfile.read(p)
                if r!=sr or len(z)!=len(x):raise RuntimeError('Channel readback failed')
            if cls._sha_wb(src)!=digest:raise RuntimeError('Source mutated')
            for source_file,target in staged:
                os.link(source_file,target)
                published.append(target)
            return {'passed':True,'source':str(src),'left':str(a),'right':str(b),
                    'sample_rate':sr,'frames':len(x),'source_sha256':digest,
                    'left_sha256':cls._sha_wb(a),'right_sha256':cls._sha_wb(b),
                    'native_audition_effect':False}
        except Exception:
            for p in published:p.unlink(missing_ok=True)
            raise
        finally:
            for p,d in staged:p.unlink(missing_ok=True)

    @classmethod
    def combine_mono_to_stereo(cls,left,right,destination,*,confirm=False):
        lp=Path(left).resolve();rp=Path(right).resolve();dst=Path(destination).resolve()
        if not lp.is_file() or not rp.is_file() or len({lp,rp,dst})!=3 or dst.exists() or dst.suffix.lower()!='.wav' or not dst.parent.is_dir():
            raise ValueError('Distinct source files and new WAV output required')
        if not confirm:return {'dry_run':True,'left':str(lp),'right':str(rp),'destination':str(dst)}
        old=(cls._sha_wb(lp),cls._sha_wb(rp))
        rate,l,li=cls._read_wav(lp)
        rate2,r,ri=cls._read_wav(rp)
        if l.shape[1]!=1 or r.shape[1]!=1 or rate!=rate2 or len(l)!=len(r):
            raise ValueError('Mono files with identical duration and sample rate required')
        stereo=np.column_stack((l[:,0],r[:,0])).astype(np.float32)
        fd,temp=tempfile.mkstemp(suffix='.wav',prefix='.audition_stereo_',dir=str(dst.parent))
        os.close(fd);stage=Path(temp)
        try:
            wavfile.write(stage,rate,stereo)
            read_rate,arr=wavfile.read(stage)
            if read_rate!=rate or arr.shape!=stereo.shape:raise RuntimeError('Stereo readback failed')
            if (cls._sha_wb(lp),cls._sha_wb(rp))!=old:raise RuntimeError('Source changed')
            os.link(stage,dst)
        finally:
            stage.unlink(missing_ok=True)
        return {'passed':True,'output':str(dst),'frames':len(stereo),'channels':2,
                'sample_rate':rate,'output_sha256':cls._sha_wb(dst),
                'sources_unchanged':True,'backend':'SciPy independent WAV channel processing'}
