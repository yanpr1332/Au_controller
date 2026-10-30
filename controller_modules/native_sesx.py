"""Native-schema Adobe Audition 26 SESX inspection, guarded patch, media validation.

Differs from the earlier schematic sesx_lab.py, which has no native schema claim.
Only writes NEW .sesx files, never source or referenced media.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
from lxml import etree as ET

class AuditionRealSession:
    @staticmethod
    def _native_tree(source):
        p=Path(source).resolve()
        if not p.is_file() or p.suffix.lower()!='.sesx':raise ValueError('Existing .sesx required')
        tree=ET.parse(p);r=tree.getroot()
        if r.tag!='sesx' or not (r.get('version') or '').startswith('1.'):
            raise ValueError('Expected Audition native SESX 1.x document')
        sess=r.find('session')
        if sess is None:raise ValueError('Missing native session')
        tracks=r.findall('.//audioTrack')
        return p,tree,r,tracks

    @classmethod
    def inspect_native_sesx(cls,source)->dict:
        p,tree,r,tracks=cls._native_tree(source)
        media=[]
        ids=set()
        for m in r.findall('./session/files/file')+r.findall('./files/file'):
            source_path=m.get('absolutePath')
            fid=m.get('id')
            if fid:ids.add(fid)
            media.append({'id':fid,'absolute_path':source_path,
                          'exists':Path(source_path).is_file() if source_path else False,
                          'media_handler':m.get('mediaHandler')})
        def param(track,cid,name):
            comp=next((c for c in track.findall('./trackAudioParameters/component') if c.get('id')==cid),None)
            if comp is None:return None
            par=next((q for q in comp.findall('parameter') if q.get('name')==name),None)
            return par.get('parameterValue') if par is not None else None
        data=[]
        broken_refs=[]
        for i,t in enumerate(tracks):
            clips=[]
            for clip in t.findall('audioClip'):
                fid=clip.get('fileID')
                if fid not in ids:broken_refs.append({'track':i,'fileID':fid})
                gain=next((c for c in clip.findall('component') if c.get('id')=='clipGain'),None)
                cv=next((x for x in gain.findall('parameter') if x.get('name')=='volume'),None) if gain is not None else None
                fades={n:dict(node.attrib) if (node:=clip.find(n)) is not None else None for n in ('fadeIn','fadeOut')}
                clips.append({'id':clip.get('id'),'name':clip.get('name'),'file_id':fid,
                  'start_samples':int(clip.get('startPoint','0')),
                  'end_samples':int(clip.get('endPoint','0')),
                  'source_in_samples':int(clip.get('sourceInPoint','0')),
                  'source_out_samples':int(clip.get('sourceOutPoint','0')),
                  'gain_linear':float(cv.get('parameterValue','1')) if cv is not None else None,
                  'fade':fades})
            au=t.find('trackAudioParameters')
            data.append({'index':i,'name':t.findtext('./trackParameters/name'),
             'id':t.get('id'),'clips':clips,'clip_count':len(clips),
             'solo':au.get('solo') if au is not None else None,
             'armed':au.get('recordArmed') if au is not None else None,
             'gain_linear':param(t,'trackFader','volume'),
             'pan':param(t,'trackPan','Pan'),
             'eq_powered':next((c.get('powered') for c in t.findall('./trackAudioParameters/component') if c.get('id')=='trackEQ'),None)})
        return {'path':str(p),'format_version':r.get('version'),'media':media,
         'all_media_present':all(x['exists'] for x in media) and not broken_refs,
         'broken_references':broken_refs,'tracks':data,'track_count':len(data),
         'clip_count':sum(len(x['clips']) for x in data),
         'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
         'native_application_reopen_verified':False}

    @staticmethod
    def _validfloat(value,low,high):
        if isinstance(value,bool) or not isinstance(value,(int,float)):raise ValueError('Numeric required')
        v=float(value)
        if not math.isfinite(v) or not low<=v<=high:raise ValueError('Value outside allowed range')
        return v

    @classmethod
    def patch_native_sesx(cls,source,destination,edits:list[dict],*,confirm:bool=False):
        src,t,r,tracks=cls._native_tree(source)
        dst=Path(destination).resolve()
        if dst==src or dst.suffix.lower()!='.sesx' or dst.exists() or not dst.parent.is_dir():
            raise ValueError('Output must be new SESX in existing directory; never overwrite')
        if not isinstance(edits,list) or not 1<=len(edits)<=64:
            raise ValueError('1-64 edits expected')
        allowed={'name','mute','solo','arm','track_gain','pan','eq_enabled',
                 'clip_gain','clip_start','fade_in_end','fade_out_start'}
        for e in edits:
            if not isinstance(e,dict) or e.get('action') not in allowed:
                raise ValueError('Unsupported operation')
            idx=e.get('track',0)
            if type(idx)!=int or not 0<=idx<len(tracks):raise IndexError('Unknown track')
            tr=tracks[idx];act=e['action'];value=e.get('value')
            def component(cid):
                obj=next((x for x in tr.findall('./trackAudioParameters/component') if x.get('id')==cid),None)
                if obj is None:raise ValueError('Native component missing: '+cid)
                return obj
            def valueparameter(comp,name):
                q=next((p for p in comp.findall('parameter') if p.get('name')==name),None)
                if q is None:raise ValueError('Native component parameter missing: '+name)
                return q
            if act=='name':
                nm=tr.find('./trackParameters/name')
                if nm is None or not isinstance(value,str) or not value.strip() or len(value)>96:
                    raise ValueError('Valid track name required')
                nm.text=value.strip()
            elif act in ('solo','arm'):
                if type(value)!=bool:raise ValueError('Boolean expected')
                ap=tr.find('trackAudioParameters')
                if ap is None:raise ValueError('Missing trackAudioParameters')
                ap.set('solo' if act=='solo' else 'recordArmed','true' if value else 'false')
            elif act=='mute':
                if type(value)!=bool:raise ValueError('Boolean expected')
                valueparameter(component('trackMute'),'mute').set('parameterValue','1' if value else '0')
            elif act in ('track_gain','pan'):
                v=cls._validfloat(value,0,10) if act=='track_gain' else cls._validfloat(value,-1,1)
                q=valueparameter(component('trackFader' if act=='track_gain' else 'trackPan'),
                          'volume' if act=='track_gain' else 'Pan')
                q.set('parameterValue',str(v))
            elif act=='eq_enabled':
                if type(value)!=bool:raise ValueError('Boolean expected')
                component('trackEQ').set('powered','true' if value else 'false')
            else:
                clip_idx=e.get('clip',0)
                clips=tr.findall('audioClip')
                if type(clip_idx)!=int or not 0<=clip_idx<len(clips):raise IndexError('Clip not found')
                cl=clips[clip_idx]
                if act=='clip_gain':
                    valueparameter(next((x for x in cl.findall('component') if x.get('id')=='clipGain'),None),'volume').set(
                       'parameterValue',str(cls._validfloat(value,0,10)))
                elif act=='clip_start':
                    if type(value)!=int or not 0<=value<=48_000_000:raise ValueError('Invalid sample position')
                    old_start=int(cl.get('startPoint','0'))
                    old_end=int(cl.get('endPoint','0'))
                    cl.set('startPoint',str(value))
                    cl.set('endPoint',str(value+(old_end-old_start)))
                elif act in ('fade_in_end','fade_out_start'):
                    if type(value)!=int or not 0<=value<=48_000_000:raise ValueError('Invalid fade sample position')
                    fade=cl.find('fadeIn' if act=='fade_in_end' else 'fadeOut')
                    if fade is None:raise ValueError('Missing native fade curve')
                    fade.set('endPoint' if act=='fade_in_end' else 'startPoint',str(value))
        if not confirm:return {'dry_run':True,'source':str(src),'destination':str(dst),'edit_count':len(edits)}
        before=hashlib.sha256(src.read_bytes()).hexdigest()
        # Audition embeds an XMP xpacket BOM as &#xFEFF; in its native SESX.
        # ElementTree expands that entity into a literal U+FEFF; serializing it
        # unescaped yields XML that Expat rejects inside the XMP packet text.
        payload=ET.tostring(r,encoding='utf8',xml_declaration=True)
        payload=payload.replace(b'\xef\xbb\xbf',b'&#xFEFF;')
        ET.fromstring(payload)  # Validate *before* creating the final output.
        dst.write_bytes(payload)
        after=hashlib.sha256(src.read_bytes()).hexdigest()
        if after!=before:raise RuntimeError('Source changed during edit')
        check=cls.inspect_native_sesx(dst)
        return {'output':str(dst),'source':str(src),'source_unchanged':True,
                'media_integrity':check['all_media_present'],'track_count':check['track_count'],
                'clip_count':check['clip_count'],'edit_count':len(edits),
                'source_sha256':before,'output_sha256':check['sha256'],
                'native_application_reopen_verified':False}
