"""Declarative Audition production jobs: bounded, atomic, auditable offline pipelines.

Uses validated Controller operations with no arbitrary shell/code execution.
All input media are read-only; destination must exist and outputs must not.
Jobs run in a private staging directory, and are published using atomic
same-volume hard links only when every step and integrity check passes.
"""
from __future__ import annotations
import hashlib,json,os,re,tempfile
from pathlib import Path

class AuditionProductionJobs:
    _actions={
        'effects':({'effects','sample_rate'},('.wav','.flac','.mp3','.m4a')),
        'master':({'target_lufs','ceiling_dbtp','rate'},('.wav','.flac','.mp3','.m4a')),
        'transcode':({'rate','channels','bitrate_kbps'},('.wav','.flac','.mp3','.m4a','.ogg','.opus')),
        'metadata':({'tags','bwf'},('.wav','.flac','.mp3','.m4a')),
        'duck':({'background','music_gain_db','voice_gain_db','threshold','ratio','attack_ms','release_ms'},('.wav',)),
        'qc':({'profile'},('.json',)),
        'r128':({'max_points'},('.json',)),
        'session_audit':(set(),('.json',)),
        'wave_edit':({'operations','format','dither','seed'},('.wav',)),
        'fft':({'window'},('.json',)),
    }
    @staticmethod
    def _hash_file(path):
        h=hashlib.sha256()
        with Path(path).open('rb') as handle:
            for chunk in iter(lambda:handle.read(1024*1024),b''):
                h.update(chunk)
        return h.hexdigest()

    @classmethod
    def _production_plan(cls,spec,output_dir):
        folder=Path(output_dir).resolve()
        if not folder.is_dir():raise ValueError('Existing output directory is required')
        if not isinstance(spec,dict) or set(spec)!={'inputs','steps'}:
            raise ValueError('Production spec requires exactly inputs and steps')
        inputs=spec['inputs'];steps=spec['steps']
        if not isinstance(inputs,dict) or not 1<=len(inputs)<=12 or not isinstance(steps,list) or not 1<=len(steps)<=24:
            raise ValueError('1..12 input aliases and 1..24 steps required')
        alias_re=re.compile(r'^[a-zA-Z][a-zA-Z0-9_]{0,30}$')
        resolved={}
        for name,path in inputs.items():
            if not isinstance(name,str) or not alias_re.fullmatch(name):
                raise ValueError('Invalid input alias')
            if not isinstance(path,str):raise ValueError('File input paths must be strings')
            p=Path(path).resolve()
            if not p.is_file():raise FileNotFoundError('Missing production input: '+str(p))
            if p.suffix.lower() not in ('.wav','.flac','.mp3','.m4a','.ogg','.opus','.sesx'):
                raise ValueError('Unsupported input format')
            resolved[name]=p
        known=dict(resolved);seen=set();plan=[]
        for row in steps:
            if not isinstance(row,dict) or set(row)!={'id','kind','source','format','params'}:
                raise ValueError('Step needs id, kind, source, format and params')
            ident,kind,src,fmt,params=[row[k] for k in ('id','kind','source','format','params')]
            if not isinstance(ident,str) or not alias_re.fullmatch(ident) or ident in seen or ident in known:
                raise ValueError('Duplicate or invalid step id')
            if kind not in cls._actions:raise ValueError('Unknown step action')
            allowed,extensions=cls._actions[kind]
            if not isinstance(fmt,str) or ('.'+fmt) not in extensions:raise ValueError('Unsupported format for action')
            if not isinstance(params,dict) or not set(params).issubset(allowed):
                raise ValueError('Unexpected parameters for '+kind)
            if not isinstance(src,str):raise ValueError('Step source must be named')
            ref=src[1:] if src.startswith('@') else src
            if ref not in known:raise ValueError('Missing / forward step reference '+ref)
            if ref not in resolved and not src.startswith('@'):
                raise ValueError('Produced step references require @ prefix: '+ref)
            if src.startswith('@') and ref in resolved:
                raise ValueError('@ prefix reserved for produced step IDs')
            # Keep text metadata/params JSON compatible: no functions, NaN or custom objects.
            json.dumps(params,allow_nan=False)
            origin=known[ref]
            if kind=='session_audit':
                if origin.suffix.lower()!='.sesx':raise ValueError('Session audit needs SESX')
            else:
                if origin.suffix.lower()=='.sesx':raise ValueError('Audio action cannot read SESX')
            if kind in ('wave_edit','fft') and origin.suffix.lower()!='.wav':
                raise ValueError('Waveform timeline/FFT requires a WAV source')
            if kind=='wave_edit':
                ops=params.get('operations')
                if not isinstance(ops,list) or not 1<=len(ops)<=32:
                    raise ValueError('Waveform step needs 1..32 typed edits')
            if kind=='metadata' and origin.suffix.lower()!='.'+fmt:
                raise ValueError('Metadata muxing cannot change codec/container')
            extra=None
            if kind=='duck':
                voice=params.get('background')
                if not isinstance(voice,str):raise ValueError('Ducking needs background alias')
                back=voice[1:] if voice.startswith('@') else voice
                if back not in known:raise ValueError('Unknown background reference')
                if back not in resolved and not voice.startswith('@'):
                    raise ValueError('Produced background references require @ prefix')
                if back in resolved and voice.startswith('@'):
                    raise ValueError('@ prefix reserved for produced step IDs')
                extra=known[back]
                if extra.suffix.lower()=='.sesx':raise ValueError('Background must be audio')
            if kind=='effects':
                cls.effects_recipe_validate(params.get('effects'))
            file=folder/(ident+'.'+fmt)
            if file.is_file() or file.exists():raise FileExistsError('Output already exists: '+str(file))
            if file in resolved.values():raise ValueError('Destination overlaps input')
            plan.append({'id':ident,'kind':kind,'source':src,
                         'format':fmt,'params':params,'output':str(file),
                         'background':str(extra) if extra else None})
            # Path is final destination for display, actual execution uses staging.
            known[ident]=file
            seen.add(ident)
        manifest=folder/'audition_production_receipt.json'
        if manifest.exists():raise FileExistsError('Existing production receipt not overwritten')
        return folder,resolved,plan

    @classmethod
    def production_job_plan(cls,spec,output_dir):
        folder,inputs,steps=cls._production_plan(spec,output_dir)
        return {'dry_run':True,'destination':str(folder),
                'inputs':{k:str(v) for k,v in inputs.items()},
                'steps':steps,'publish_policy':'all-or-nothing, no file overwrite'}

    @classmethod
    def _execute_production_step(cls,step,inputs,staged_outputs,stage):
        ident,kind,params=step['id'],step['kind'],step['params']
        src=step['source']
        path=staged_outputs[src[1:]] if src.startswith('@') else inputs[src]
        target=stage/(ident+'.'+step['format'])
        if kind=='wave_edit':
            result=cls.edit_wav_timeline(path,target,params['operations'],
                format=params.get('format','float32'),
                dither=params.get('dither','none'),seed=params.get('seed',19),confirm=True)
        elif kind=='fft':
            result=cls.export_fft_spectrum(path,target,
                window=params.get('window',4096),confirm=True)
        elif kind=='effects':
            result=cls.render_audio_effects(path,target,params['effects'],
                  sample_rate=params.get('sample_rate',48000),confirm=True)
        elif kind=='master':
            result=cls.master_loudness(path,target,
                  target_lufs=params.get('target_lufs',-16),
                  ceiling_dbtp=params.get('ceiling_dbtp',-1.5),
                  rate=params.get('rate',48000),confirm=True)
            if not result['qa_passed']:raise RuntimeError('Master loudness failed '+ident)
        elif kind=='transcode':
            result=cls.transcode_audio(path,target,
                  rate=params.get('rate',48000),channels=params.get('channels',2),
                  bitrate_kbps=params.get('bitrate_kbps',192),confirm=True)
        elif kind=='metadata':
            result=cls.tag_delivery_audio(path,target,params['tags'],
                                          bwf=params.get('bwf',False),confirm=True)
        elif kind=='duck':
            b=params['background']
            background=staged_outputs[b[1:]] if b.startswith('@') else inputs[b]
            kw={k:v for k,v in params.items() if k!='background'}
            result=cls.duck_music_under_dialogue(path,background,target,confirm=True,**kw)
            if not result['audio_quality_ok']:raise RuntimeError('Ducked output quality failed')
        elif kind=='qc':
            result=cls.export_audio_qc_report(path,target,profile=params.get('profile','podcast'),confirm=True)
            if not result['passed']:raise RuntimeError('QC profile failed '+ident)
        elif kind=='r128':
            result=cls.export_r128_timeline(path,target,max_points=params.get('max_points',4000),confirm=True)
        elif kind=='session_audit':
            result=cls.write_native_session_audit(path,target,confirm=True)
            if not result['passed']:raise RuntimeError('SESX preflight failed')
        else:raise RuntimeError('Unsupported action')
        return target,result

    @classmethod
    def run_production_jobs(cls,spec,output_dir,*,confirm=False):
        folder,inputs,plan=cls._production_plan(spec,output_dir)
        if not confirm:return cls.production_job_plan(spec,output_dir)
        original={name:cls._hash_file(path) for name,path in inputs.items()}
        staged_outputs={}
        rec=[]
        created=[]
        with tempfile.TemporaryDirectory(prefix='.audition_job_stage_',dir=folder) as temp:
            stage=Path(temp)
            for step in plan:
                ident,kind=step['id'],step['kind']
                target,result=cls._execute_production_step(step,inputs,staged_outputs,stage)
                if not target.is_file() or target.stat().st_size==0:
                    raise RuntimeError('No output from step '+ident)
                digest=cls._hash_file(target)
                staged_outputs[ident]=target
                rec.append({'id':ident,'kind':kind,'output':Path(step['output']).name,
                            'sha256':digest,'bytes':target.stat().st_size,
                            'backend':'Audition Controller, native SESX only for session audits',
                            'evidence':{'passed':True,'codec':result.get('codec'),
                                'lufs':result.get('measured_after',{}).get('integrated_lufs'),
                                'r128_points':result.get('points')}})
            if any(cls._hash_file(path)!=original[name] for name,path in inputs.items()):
                raise RuntimeError('Input changed during production; nothing published')
            manifest={'version':1,'status':'complete',
                'backend':'Audition Controller Python + WSL Debian FFmpeg/SciPy',
                'native_audition_gui_automated':False,
                'inputs':{name:{'path':str(path),'sha256':original[name]} for name,path in inputs.items()},
                'steps':rec,'step_count':len(rec),
                'format':'SHA256 verified, atomic hard-link publication'}
            receipt=stage/'audition_production_receipt.json'
            receipt.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
            output_paths=[folder/x['output'] for x in rec]
            output_paths.append(folder/receipt.name)
            for src,dst in zip(list(staged_outputs.values())+[receipt],output_paths):
                if dst.exists():raise FileExistsError('Output appeared during rendering: '+str(dst))
            # Link each staging file to its final name, never replacing existing files.
            try:
                for staged,dest in zip(list(staged_outputs.values())+[receipt],output_paths):
                    os.link(staged,dest)
                    created.append(dest)
                for x,dest in zip(rec,output_paths):
                    if cls._hash_file(dest)!=x['sha256']:
                        raise RuntimeError('Published output hash mismatch '+x['id'])
            except Exception:
                for file in created:file.unlink(missing_ok=True)
                raise
        return {'passed':True,'steps':len(rec),
                'receipt':str(folder/'audition_production_receipt.json'),
                'outputs':[str(folder/x['output']) for x in rec],
                'inputs_unchanged':True,
                'publish_atomic_per_file':True,'all_or_nothing_with_rollback':True,
                'native_audition_gui_automated':False}
