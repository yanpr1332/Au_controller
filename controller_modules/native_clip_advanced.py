"""Native Audition SESX clip safe operations with source-bound guards and roundtrip receipts.

Native file edits only: do not call this a native live DOM binding. Only ACCEPT_AU
test files in user's QA folder, write-new only. Parameters modeled on saved 26.0 SESX.
"""
from __future__ import annotations
from pathlib import Path
import hashlib,math
from lxml import etree as ET

class AuditionClipAdvanced:
    @classmethod
    def inspect_native_clips_advanced(cls,source):
        src,tree,root,tracks=cls._native_tree(source)
        ret=[]
        for ti,track in enumerate(tracks):
            for ci,clip in enumerate(track.findall('audioClip')):
                components={n.get('id'):n for n in clip.findall('component')}
                mute=components.get('clipMute')
                mutepara=next((p for p in mute.findall('parameter') if p.get('name')=='mute'),None) if mute is not None else None
                ret.append({'track':ti,'clip':ci,'id':clip.get('id'),
                    'name':clip.get('name'),'start':int(clip.get('startPoint')),
                    'end':int(clip.get('endPoint')),
                    'source_in':int(clip.get('sourceInPoint')),
                    'source_out':int(clip.get('sourceOutPoint')),
                    'locked_in_time':clip.get('lockedInTime')=='true',
                    'looped':clip.get('looped')=='true',
                    'muted':float(mutepara.get('parameterValue'))>=.5 if mutepara is not None else None,
                    'fade_in':dict(clip.find('fadeIn').attrib) if clip.find('fadeIn') is not None else None,
                    'fade_out':dict(clip.find('fadeOut').attrib) if clip.find('fadeOut') is not None else None})
        return {'source':str(src),'clip_count':len(ret),'clips':ret,
                'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest()}

    @classmethod
    def patch_native_clip_advanced(cls,source,destination,edits:list[dict],*,confirm=False):
        from audition_controller import ROOT
        safe=(ROOT/'tests').resolve()
        src,tree,root,tracks=cls._native_tree(source)
        dst=Path(destination).resolve()
        if not src.name.startswith('ACCEPT_AU_') or safe not in src.parents:
            raise PermissionError('Only QA native SESX sources permitted')
        if dst==src or dst.exists() or safe not in dst.parents or not dst.name.startswith('ACCEPT_AU_') or dst.suffix.lower()!='.sesx' or not dst.parent.is_dir():
            raise ValueError('Only brand new QA SESX file allowed')
        if not isinstance(edits,list) or not 1<=len(edits)<=48:raise ValueError('1..48 clip edits')
        allowed={'mute','lock','loop','move','trim_source','fade'}
        for e in edits:
            if not isinstance(e,dict) or e.get('action') not in allowed:raise ValueError('Unsupported clip edit')
            track=e.get('track')
            clipindex=e.get('clip')
            if type(track)!=int or type(clipindex)!=int or not 0<=track<len(tracks):
                raise IndexError('Invalid track or clip index')
            clips=tracks[track].findall('audioClip')
            if not 0<=clipindex<len(clips):raise IndexError('Clip index out of range')
            clip=clips[clipindex]
            if not str(clip.get('name','')).startswith('accept_'):
                raise PermissionError('Must use synthetic accept_ audio clip only')
            action=e['action'];v=e.get('value')
            start=int(clip.get('startPoint'));end=int(clip.get('endPoint'))
            sourcein=int(clip.get('sourceInPoint'));sourceout=int(clip.get('sourceOutPoint'))
            if end<=start or sourceout<=sourcein:raise ValueError('Invalid source clip')
            if action in ('mute','lock','loop'):
                if type(v)!=bool:raise ValueError('Expected boolean for '+action)
                if action=='mute':
                    comp=next((x for x in clip.findall('component') if x.get('id')=='clipMute'),None)
                    if comp is None:raise ValueError('Clip mute component missing')
                    p=next((x for x in comp.findall('parameter') if x.get('name')=='mute'),None)
                    if p is None:raise ValueError('Clip mute parameter missing')
                    p.set('parameterValue','1' if v else '0')
                else:
                    clip.set('lockedInTime' if action=='lock' else 'looped','true' if v else 'false')
            elif action=='move':
                if type(v)!=int or not 0<=v<=48_000_000:raise ValueError('Invalid move sample position')
                clip.set('startPoint',str(v));clip.set('endPoint',str(v+(end-start)))
            elif action=='trim_source':
                if not isinstance(v,dict) or set(v)!={'in_samples','out_samples'}:
                    raise ValueError('Trimming requires in_samples and out_samples')
                begin=v['in_samples'];finish=v['out_samples']
                if type(begin)!=int or type(finish)!=int or not sourcein<=begin<finish<=sourceout:
                    raise ValueError('Only inward, sample-aligned trims permitted')
                delta=finish-begin
                # Native saved clip endPoint models startPoint + audible duration.
                clip.set('sourceInPoint',str(begin))
                clip.set('sourceOutPoint',str(finish))
                clip.set('endPoint',str(start+delta))
                # Convert existing source-local fades into zero duration at new cut boundaries
                # unless they remain fully within the new media span.
                for fade_tag,boundary in (('fadeIn',begin),('fadeOut',finish)):
                    fade=clip.find(fade_tag)
                    if fade is not None:
                        lo=int(fade.get('startPoint','0'));hi=int(fade.get('endPoint','0'))
                        if lo<begin or hi>finish:
                            fade.set('startPoint',str(boundary));fade.set('endPoint',str(boundary))
            elif action=='fade':
                if not isinstance(v,dict) or set(v)!={'edge','length_samples'}:
                    raise ValueError('fade requires edge and length_samples')
                edge=v['edge'];length=v['length_samples']
                if edge not in ('in','out') or type(length)!=int or length<0 or length>sourceout-sourcein:
                    raise ValueError('Fade edge/length invalid')
                fade=clip.find('fadeIn' if edge=='in' else 'fadeOut')
                if fade is None:raise ValueError('Native fade unavailable')
                if edge=='in':
                    fade.set('startPoint',str(sourcein))
                    fade.set('endPoint',str(sourcein+length))
                else:
                    fade.set('startPoint',str(sourceout-length))
                    fade.set('endPoint',str(sourceout))
            else:
                raise ValueError('Not permitted')
        if not confirm:return {'dry_run':True,'count':len(edits),'destination':str(dst)}
        prior=hashlib.sha256(src.read_bytes()).hexdigest()
        payload=ET.tostring(root,xml_declaration=True,encoding='utf-8')
        ET.fromstring(payload)
        dst.write_bytes(payload)
        post=cls.inspect_native_clips_advanced(dst)
        if hashlib.sha256(src.read_bytes()).hexdigest()!=prior:
            dst.unlink(missing_ok=True);raise RuntimeError('Source changed')
        return {'output':str(dst),'edits':len(edits),'clips':post['clips'],
                'source_unchanged':True,'source_sha256':prior,
                'output_sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),
                'native_audition_reopen_verified':False}
