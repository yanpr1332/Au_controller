"""Read Audition native SESX 1.9 XMP cue markers and export frame-accurate chapters.

XMP metadata is an embedded XML text packet, not plain SESX <marker> nodes.
Chapter output uses SciPy WAV splitting, NOT Audition's native export command.
"""
from __future__ import annotations
from pathlib import Path
import hashlib,json,math,re
import numpy as np
from scipy.io import wavfile
from lxml import etree as ET

class AuditionChapterLab:
    @classmethod
    def native_sesx_markers_xmp(cls,session):
        src,tree,root,tracks=cls._native_tree(session)
        metadata=root.find('./session/xmpMetadata')
        if metadata is None or not metadata.text:
            return {'session':str(src),'sample_rate':int(root.find('session').get('sampleRate')),
                    'markers':[],'count':0,'format':'SESX XMP'}
        raw=metadata.text
        match=re.search(r'<x:xmpmeta\b[\s\S]*?</x:xmpmeta>',raw)
        if match is None:raise ValueError('No valid XMP metadata packet')
        xmp=ET.fromstring(match.group(0).encode('utf8'))
        ns={'xmpDM':'http://ns.adobe.com/xmp/1.0/DynamicMedia/',
            'rdf':'http://www.w3.org/1999/02/22-rdf-syntax-ns#'}
        out=[]
        rates=set()
        for track in xmp.xpath('//xmpDM:Tracks/rdf:Bag/rdf:li',namespaces=ns):
            title=track.findtext('xmpDM:trackName',namespaces=ns)
            rate=track.findtext('xmpDM:frameRate',namespaces=ns)
            if rate and re.fullmatch(r'f\d+',rate):rates.add(int(rate[1:]))
            for marker in track.xpath('./xmpDM:markers/rdf:Seq/rdf:li',namespaces=ns):
                def f(t):return marker.findtext('xmpDM:'+t,namespaces=ns)
                start=int(f('startTime') or 0)
                dur=int(f('duration') or 0)
                if start<0 or dur<0:raise ValueError('Invalid XMP marker timestamp')
                out.append({'track_name':title,'name':f('name') or '',
                            'comment':f('comment') or '',
                            'start_samples':start,'duration_samples':dur,
                            'guid':f('guid')})
        session_rate=int(root.find('session').get('sampleRate'))
        if rates and rates!={session_rate}:raise ValueError('Native XMP marker frame rate differs from session')
        out.sort(key=lambda x:(x['start_samples'],x['name']))
        return {'session':str(src),'sample_rate':session_rate,'markers':out,
                'count':len(out),'format':'SESX native embedded XMP'}

    @classmethod
    def export_native_marker_chapters(cls,session,rendered_audio,directory,*,
                                      fade_ms=5,confirm=False):
        from audition_controller import ROOT
        src=Path(rendered_audio).resolve()
        out=Path(directory).resolve()
        safe=(ROOT/'tests').resolve()
        if safe not in src.parents or safe not in out.parents or not out.is_dir():
            raise PermissionError('Only QA source WAV and QA output directory permitted')
        if not src.is_file() or src.suffix.lower()!='.wav':raise ValueError('QA WAV required')
        if type(fade_ms)!=int or not 0<=fade_ms<=50:raise ValueError('Fade length must be 0..50 ms')
        mapping=cls.native_sesx_markers_xmp(session)
        markers=mapping['markers']
        if not markers:raise ValueError('No native XMP markers found')
        rate,samples=wavfile.read(src)
        if rate!=mapping['sample_rate']:raise ValueError('WAV rate and SESX marker rate differ')
        if samples.dtype not in (np.dtype('float32'),np.dtype('int16'),np.dtype('int32')):
            raise ValueError('Unsupported WAV sample type')
        sections=[]
        for i,marker in enumerate(markers):
            start=marker['start_samples']
            duration=marker['duration_samples']
            if duration==0:
                duration=(markers[i+1]['start_samples']-start) if i+1<len(markers) else len(samples)-start
            stop=start+duration
            if not 0<=start<stop<=len(samples):raise ValueError('Marker region outside waveform bounds')
            title=re.sub(r'[^A-Za-z0-9_]+','_',marker['name']).strip('_')[:48] or 'chapter'
            dest=out/(f'QA_CHAPTER_{i+1:02d}_{title}.wav')
            if dest.exists():raise FileExistsError('Refusing to overwrite chapter '+str(dest))
            sections.append((marker,start,stop,dest))
        if not confirm:return {'dry_run':True,'regions':[
             {'name':m['name'],'start':a,'end':b,'destination':str(d)} for m,a,b,d in sections]}
        originals=hashlib.sha256(src.read_bytes()).hexdigest()
        result=[]
        created=[]
        try:
            for mark,start,stop,dest in sections:
                clip=samples[start:stop].copy()
                nf=min(round(rate*fade_ms/1000),len(clip)//4)
                if nf>0:
                    fade=np.linspace(0,1,nf,endpoint=True)
                    if clip.ndim>1:fade=fade[:,None]
                    amp=np.asarray(clip,dtype=np.float64)
                    amp[:nf]*=fade;amp[-nf:]*=fade[::-1]
                    clip=amp.astype(samples.dtype)
                wavfile.write(dest,rate,clip)
                created.append(dest)
                reopened_rate,got=wavfile.read(dest)
                if reopened_rate!=rate or len(got)!=(stop-start):
                    raise RuntimeError('Chapter WAV readback mismatch')
                result.append({'name':mark['name'],'start_sample':start,
                               'end_sample':stop,'duration_s':round((stop-start)/rate,6),
                               'path':str(dest),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),
                               'frames':len(got),'sample_rate':rate})
            if hashlib.sha256(src.read_bytes()).hexdigest()!=originals:
                raise RuntimeError('Original mix waveform changed')
        except Exception:
            for f in created:f.unlink(missing_ok=True)
            raise
        return {'backend':'SciPy marker-aligned WAV chapter export',
                'native_audition_export':False,'markers_from':'Audition SESX XMP',
                'count':len(result),'source_unchanged':True,'chapters':result}
