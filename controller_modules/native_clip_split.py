"""Split a QA audioClip in native SESX, creating a separate output only."""
from pathlib import Path
from copy import deepcopy
from lxml import etree as ET
import hashlib

class AuditionNativeClipSplit:
    @classmethod
    def split_native_qa_clip(cls,source,destination,*,track=0,clip=0,offset_samples=0,confirm=False):
        from audition_controller import ROOT
        safe=(ROOT/'tests').resolve()
        src,tree,root,tracks=cls._native_tree(source)
        dst=Path(destination).resolve()
        if safe not in src.parents or not src.name.startswith('ACCEPT_AU_'):
            raise PermissionError('QA source only')
        if dst==src or dst.exists() or safe not in dst.parents or dst.suffix.lower()!='.sesx' or not dst.name.startswith('ACCEPT_AU_'):
            raise ValueError('New QA output required')
        if any(type(v)!=int for v in (track,clip,offset_samples)) or not 0<=track<len(tracks):
            raise ValueError('Integer track/clip/offset required')
        clips=tracks[track].findall('audioClip')
        if not 0<=clip<len(clips):raise IndexError('Missing clip')
        left=clips[clip]
        if not str(left.get('name','')).startswith('accept_') or left.get('looped')=='true':
            raise PermissionError('Only unlooped QA media')
        t0=int(left.get('startPoint'));t1=int(left.get('endPoint'))
        s0=int(left.get('sourceInPoint'));s1=int(left.get('sourceOutPoint'))
        if t1-t0!=s1-s0 or not 1<=offset_samples<t1-t0:
            raise ValueError('Invalid source/timeline split')
        ids=[int(x.get('id')) for x in root.findall('.//audioClip')]
        if len(ids)!=len(set(ids)):raise ValueError('Existing duplicate clip IDs')
        new_id=max(ids)+1
        cut=s0+offset_samples
        right=deepcopy(left)
        left.set('endPoint',str(t0+offset_samples))
        left.set('sourceOutPoint',str(cut))
        right.set('id',str(new_id))
        right.set('name',left.get('name')+'_splitQA')
        right.set('startPoint',str(t0+offset_samples))
        right.set('sourceInPoint',str(cut))
        right.set('select','false')
        for item,tag in ((left,'fadeOut'),(right,'fadeIn')):
            fade=item.find(tag)
            if fade is not None:
                fade.set('startPoint',str(cut));fade.set('endPoint',str(cut))
        node=tracks[track]
        node.insert(list(node).index(left)+1,right)
        result={'source':str(src),'output':str(dst),'original_duration':t1-t0,
                'left_duration':offset_samples,'right_duration':t1-t0-offset_samples,
                'right_clip_id':new_id}
        if not confirm:return {'dry_run':True,**result}
        before=hashlib.sha256(src.read_bytes()).hexdigest()
        content=ET.tostring(root,xml_declaration=True,encoding='utf8')
        content=content.replace(b'\xef\xbb\xbf',b'&#xFEFF;')
        ET.fromstring(content)
        dst.write_bytes(content)
        try:
            verified=cls.inspect_native_sesx(dst)
            if verified['clip_count']!=len(ids)+1 or not verified['all_media_present']:
                raise RuntimeError('Invalid split result')
            if hashlib.sha256(src.read_bytes()).hexdigest()!=before:
                raise RuntimeError('Original SESX changed')
        except Exception:
            dst.unlink(missing_ok=True)
            raise
        return {'dry_run':False,**result,'source_unchanged':True,
                'native_reopen_verified':False,'new_clip_count':verified['clip_count'],
                'output_sha256':verified['sha256']}
