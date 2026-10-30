"""Audition 26 native SESX 1.9 multitrack clip arrangement recipes.

Safely CLONES QA clip elements into EMPTY existing audio tracks. Does not claim
a live application DOM file importer. Native Audition reopening/mixdown must be
independently performed to certify a generated session.
"""
from __future__ import annotations
from pathlib import Path
from lxml import etree as ET
import copy,hashlib,math

class AuditionArrangementLab:
    @classmethod
    def arrange_native_qa_clips(cls,source,destination,placements:list[dict],*,confirm=False):
        from audition_controller import ROOT
        safe=(ROOT/'tests').resolve()
        src,tree,root,tracks=cls._native_tree(source)
        dst=Path(destination).resolve()
        if src.suffix.lower()!='.sesx' or not src.name.startswith('ACCEPT_AU_') or safe not in src.parents:
            raise PermissionError('QA-only input SESX required')
        if (dst==src or dst.exists() or dst.suffix.lower()!='.sesx' or
            safe not in dst.parents or not dst.name.startswith('ACCEPT_AU_') or not dst.parent.is_dir()):
            raise ValueError('Only NEW QA SESX output in tests tree allowed')
        if not isinstance(placements,list) or not 1<=len(placements)<=24:
            raise ValueError('1..24 clip placements required')
        source_clips=[tr.findall('audioClip') for tr in tracks]
        old_ids={int(c.get('id')) for clips in source_clips for c in clips}
        next_id=max(old_ids,default=-1)+1
        targets=set()
        plans=[]
        for item in placements:
            if not isinstance(item,dict) or set(item)!={'source_track','source_clip','target_track','start_samples','gain_linear'}:
                raise ValueError('Placement needs exactly source_track, source_clip, target_track, start_samples, gain_linear')
            a,b,t,p,g=[item[k] for k in ('source_track','source_clip','target_track','start_samples','gain_linear')]
            if any(type(x)!=int for x in (a,b,t,p)) or a<0 or t<0 or a>=len(tracks) or t>=len(tracks):
                raise IndexError('Track index invalid')
            if b<0 or b>=len(source_clips[a]):raise IndexError('Source clip index invalid')
            if not 0<=p<=48_000_000:raise ValueError('Target clip time invalid')
            if isinstance(g,bool) or not isinstance(g,(int,float)) or not math.isfinite(float(g)) or not 0<=float(g)<=1:
                raise ValueError('QA arrangement gain must be 0..1 linear (no boost)')
            if t in targets or source_clips[t]:
                raise ValueError('Each destination must be a DISTINCT empty native audio track')
            targets.add(t)
            origin=source_clips[a][b]
            if not str(origin.get('name','')).startswith('accept_'):
                raise PermissionError('Clip source is not QA test fixture')
            if origin.get('offline')=='true' or origin.get('fileID') is None:
                # Media fileID '0' is valid; reject a real offline flag or missing ID.
                raise ValueError('Offline/unresolved source clip')
            clip=copy.deepcopy(origin)
            if next_id>2_000_000_000:raise ValueError('Clip IDs exhausted')
            clip.set('id',str(next_id))
            clip.set('name',str(origin.get('name'))+'_QAclone'+str(next_id))
            clip.set('select','false')
            clip.set('zOrder','0')
            duration=int(clip.get('endPoint'))-int(clip.get('startPoint'))
            if duration<=0:raise ValueError('Invalid source clip duration')
            clip.set('startPoint',str(p))
            clip.set('endPoint',str(p+duration))
            gain=next((x for x in clip.findall('component') if x.get('id')=='clipGain'),None)
            if gain is None:raise ValueError('Native clipGain component missing')
            for par in gain.findall('parameter'):
                if par.get('name') in ('static gain','volume'):
                    par.set('parameterValue',str(float(g)))
            plans.append({'target_track':t,'new_id':next_id,'start':p,'duration':duration,'gain':float(g),
                          'source_fileID':clip.get('fileID')})
            tracks[t].append(clip)
            next_id+=1
        if not confirm:return {'dry_run':True,'plan':plans,'output':str(dst)}
        old_hash=hashlib.sha256(src.read_bytes()).hexdigest()
        payload=ET.tostring(root,xml_declaration=True,encoding='utf8')
        ET.fromstring(payload)
        dst.write_bytes(payload)
        try:
            result=cls.inspect_native_sesx(dst)
            if result['clip_count']!=sum(map(len,source_clips))+len(plans):
                raise RuntimeError('Unexpected native clip count')
            if not result['all_media_present']:
                raise RuntimeError('Missing arranged audio media')
            if hashlib.sha256(src.read_bytes()).hexdigest()!=old_hash:
                raise RuntimeError('Input SESX changed')
        except Exception:
            dst.unlink(missing_ok=True)
            raise
        return {'source':str(src),'output':str(dst),'placements':plans,
                'all_media_present':True,'clip_count':result['clip_count'],
                'source_unchanged':True,'sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),
                'native_reopen_verified':False}
