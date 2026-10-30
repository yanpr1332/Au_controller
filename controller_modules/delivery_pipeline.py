"""One-call audio delivery: safe per-source speech cleanup, two-pass loudness
mastering, codec readback, source integrity and JSON job receipt.

This is an EXTERNAL Debian FFmpeg pipeline, not native Audition effects.
"""
from __future__ import annotations
import hashlib,json,tempfile
from pathlib import Path

class AuditionDeliveryPipeline:
    PRESETS={
     'podcast_16':{'target_lufs':-16.,'ceiling_dbtp':-1.5},
     'broadcast_23':{'target_lufs':-23.,'ceiling_dbtp':-1.},
     'voiceover_19':{'target_lufs':-19.,'ceiling_dbtp':-2.}
    }
    @classmethod
    def deliver_audio_batch(cls,sources:list[str|Path],directory,*,preset='podcast_16',
                            formats=('wav','mp3'),denoise=False,confirm=False):
        if preset not in cls.PRESETS:raise ValueError('Supported preset required')
        if not isinstance(sources,list) or not 1<=len(sources)<=20:
            raise ValueError('1..20 distinct audio sources required')
        srcs=[cls._qa_input(p) for p in sources]
        if len(set(srcs))!=len(srcs):raise ValueError('Duplicate sources')
        folder=Path(directory).resolve()
        if not folder.is_dir():raise ValueError('Existing destination directory required')
        if not isinstance(formats,(list,tuple)) or not 1<=len(formats)<=4 or any(f not in ('wav','flac','mp3','m4a') for f in formats):
            raise ValueError('Output format must be wav/flac/mp3/m4a')
        if len(set(formats))!=len(formats):raise ValueError('Duplicate output formats')
        if type(denoise)!=bool:raise ValueError('denoise must be boolean')
        destinations=[]
        for source in srcs:
            if source.parent==folder:raise ValueError('Use separate delivery folder')
            base=source.stem
            for ext in formats:
                destinations.append(folder/(base+'_'+preset+'.'+ext))
        if len(set(destinations))!=len(destinations) or any(x.exists() for x in destinations):
            raise FileExistsError('Batch destination collides with existing files')
        jobs=[{'source':str(p),'files':[str(folder/(p.stem+'_'+preset+'.'+e)) for e in formats]} for p in srcs]
        if not confirm:return {'dry_run':True,'jobs':jobs,
                               'pipeline':'Optional speech cleanup then FFmpeg two-pass loudnorm'}
        results=[]
        settings=cls.PRESETS[preset]
        for src in srcs:
            orig=hashlib.sha256(src.read_bytes()).hexdigest()
            item={'source':str(src),'source_sha256':orig,'outputs':[],'passed':False}
            with tempfile.TemporaryDirectory(prefix='audition_processing_',dir=str(folder)) as work:
                working=src
                try:
                    if denoise:
                        temp=Path(work)/'speech_clean.wav'
                        clean=cls.speech_cleanup(src,temp,confirm=True)
                        item['cleanup']={'codec':clean['codec'],'duration':clean['duration'],
                                         'filters':clean['filters']}
                        working=temp
                    for fmt in formats:
                        dst=folder/(src.stem+'_'+preset+'.'+fmt)
                        master=cls.master_loudness(working,dst,confirm=True,**settings)
                        final=cls.ffprobe_media(dst)
                        check=cls.audio_quality_gate(dst) if fmt=='wav' else None
                        item['outputs'].append({
                         'path':str(dst),'format':fmt,'sha256':master['sha256'],
                         'duration':float(final['format']['duration']),
                         'codec':final['streams'][0]['codec_name'],
                         'measured_lufs':master['measured_after']['integrated_lufs'],
                         'measured_dbtp':master['measured_after']['true_peak_dbtp'],
                         'loudness_qa':master['qa_passed'],
                         'sample_qa':check['passed'] if check else None
                        })
                    item['source_unchanged']=hashlib.sha256(src.read_bytes()).hexdigest()==orig
                    item['passed']=item['source_unchanged'] and len(item['outputs'])==len(formats) and all(
                        x['loudness_qa'] and x['sample_qa'] is not False for x in item['outputs'])
                except Exception as exc:
                    item['error']=str(exc)[:300]
                    # Only remove exact outputs which this job just created, never user sources.
                    for ext in formats:
                        dst=folder/(src.stem+'_'+preset+'.'+ext)
                        if dst.is_file() and dst!=src:
                            dst.unlink()
                    item['outputs']=[]
                results.append(item)
        return {'preset':preset,'backend':'WSL Debian FFmpeg, not native Audition',
                'job_count':len(srcs),'output_formats':list(formats),
                'passed_jobs':sum(x['passed'] for x in results),'results':results}
