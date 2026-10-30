"""Portable Audition SESX analysis and cautious offline copies.

This manipulates XML only. Audition must actually re-open a session before it
is counted as an Audition-native session acceptance.
"""
from __future__ import annotations
import json
import xml.etree.ElementTree as ET
from pathlib import Path

class AuditionSessionLab:
    _OPS={'track_name','track_volume','track_pan','eq_enabled','eq_band3_gain',
          'clip_gain','fade_in_samples','fade_out_start_samples','clip_start_samples'}

    @staticmethod
    def inspect_sesx(path:str|Path)->dict:
        p=Path(path)
        if not p.is_file() or p.suffix.lower()!='.sesx':raise ValueError('Existing SESX session required')
        tree=ET.parse(p);root=tree.getroot()
        if root.tag.lower() not in ('sesx','session'):raise ValueError('Unrecognized SESX root tag')
        tracks=[]
        for i,tr in enumerate(root.findall('.//audioTrack')):
            comps={}
            for c in tr.findall('./trackAudioParameters/component'):
                cid=c.get('id','')
                comps[cid]={'powered':c.get('powered'),
                            'params':{v.get('name',''):v.get('parameterValue') for v in c.findall('parameter')}}
            clips=[]
            for cl in tr.findall('./audioClip'):
                fadein=cl.find('fadeIn');fadeout=cl.find('fadeOut')
                clips.append({'attrib':dict(cl.attrib),
                              'gain_components':len(cl.findall('./component')),
                              'fade_in':dict(fadein.attrib) if fadein is not None else None,
                              'fade_out':dict(fadeout.attrib) if fadeout is not None else None})
            tracks.append({'index':i,'name':tr.get('name'),'attrib':dict(tr.attrib),
                           'components':comps,'clip_count':len(clips),'clips':clips})
        paths=[]
        for node in root.iter():
            if node.tag.lower() in ('file','media') and ('path' in node.attrib or 'relativePath' in node.attrib):
                paths.append({'element':node.tag,'path':node.get('path') or node.get('relativePath')})
        return {'source':str(p),'root':root.tag,'xml_version':root.get('version'),
                'track_count':len(tracks),'tracks':tracks,'source_refs':paths,
                'native_open_tested':False}

    @classmethod
    def patch_sesx(cls,source:str|Path,dest:str|Path,changes:list[dict],*,confirm=False)->dict:
        src=Path(source).resolve();out=Path(dest).resolve()
        if not src.is_file() or src.suffix.lower()!='.sesx':
            raise FileNotFoundError('SESX source not found')
        if out==src or out.exists() or out.suffix.lower()!='.sesx' or not out.parent.is_dir():
            raise ValueError('Must write into a new SESX filename in an existing directory')
        if not isinstance(changes,list) or not 1<=len(changes)<=32:
            raise ValueError('1..32 session edits required')
        tree=ET.parse(src)
        root=tree.getroot();tracks=root.findall('.//audioTrack')
        if not tracks:raise ValueError('No SESX audio tracks')
        def numeric(v,lower,upper):
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not lower<=v<=upper:
                raise ValueError('Invalid numeric SESX value')
            return str(float(v))
        for edit in changes:
            if not isinstance(edit,dict) or edit.get('action') not in cls._OPS:
                raise ValueError('Unsupported SESX edit')
            idx=edit.get('track',0)
            if type(idx)!=int or not 0<=idx<len(tracks):raise IndexError('Track index out of range')
            tr=tracks[idx];name=edit['action'];value=edit.get('value')
            if name=='track_name':
                if not isinstance(value,str) or len(value)>100 or not value:raise ValueError('Invalid track name')
                tr.set('name',value)
                continue
            clipidx=edit.get('clip',0)
            if name.startswith('clip_') or name.startswith('fade_'):
                clips=tr.findall('./audioClip')
                if type(clipidx)!=int or not 0<=clipidx<len(clips):raise IndexError('Clip index out of range')
                clip=clips[clipidx]
                if name=='clip_start_samples':
                    clip.set('startTime',str(int(float(numeric(value,0,48_000_000)))))
                elif name in ('fade_in_samples','fade_out_start_samples'):
                    fade=clip.find('fadeIn' if name=='fade_in_samples' else 'fadeOut')
                    if fade is None:fade=ET.SubElement(clip,'fadeIn' if name=='fade_in_samples' else 'fadeOut')
                    fade.set('endPoint' if name=='fade_in_samples' else 'startPoint',str(int(float(numeric(value,0,48_000_000)))))
                else:
                    comp=next((c for c in clip.findall('./component') if c.get('id')=='clipGain'),None)
                    if comp is None:raise ValueError('Clip gain component missing')
                    param=next((q for q in comp.findall('./parameter') if q.get('name')=='volume'),None)
                    if param is None:raise ValueError('Clip gain parameter missing')
                    param.set('parameterValue',numeric(value,0,20))
                continue
            component_name='trackFader' if name=='track_volume' else 'trackPan' if name=='track_pan' else 'trackEQ'
            comp=next((c for c in tr.findall('./trackAudioParameters/component') if c.get('id')==component_name),None)
            if comp is None:raise ValueError('Required track component missing: '+component_name)
            if name=='eq_enabled':
                if type(value)!=bool:raise ValueError('eq_enabled requires bool')
                comp.set('powered','true' if value else 'false')
                continue
            paramname='volume' if name=='track_volume' else 'Pan' if name=='track_pan' else 'EQ Band 3 Gain'
            para=next((x for x in comp.findall('./parameter') if x.get('name')==paramname),None)
            if para is None:raise ValueError('Required parameter missing: '+paramname)
            low,high=(0,20) if name=='track_volume' else (-1,1) if name=='track_pan' else (-24,24)
            para.set('parameterValue',numeric(value,low,high))
        if not confirm:return {'dry_run':True,'source':str(src),'destination':str(out),'changes':len(changes)}
        tree.write(out,encoding='utf8',xml_declaration=True)
        inspect=cls.inspect_sesx(out)
        return {'source':str(src),'destination':str(out),'changes':len(changes),
                'track_count':inspect['track_count'],'clip_count':sum(x['clip_count'] for x in inspect['tracks']),
                'native_audition_session_opened':False}
