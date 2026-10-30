"""Native Audition 26 SESX track EQ controls in normalized 0..1 units.

These are SESX serialized PARAMETER values; they are NOT documented dB or Hz
and must not be labeled as such. Only new QA SESX files can be edited.
"""
from __future__ import annotations
import hashlib,math,re
from pathlib import Path
from lxml import etree as ET

class AuditionNativeEQ:
    @classmethod
    def inspect_native_eq(cls,session,*,track=0,kind='audioTrack'):
        src,tree,r,_=cls._native_tree(session)
        if kind not in ('audioTrack','busTrack'):raise ValueError('Only audio/bus track')
        nodes=r.findall('.//'+kind)
        if type(track)!=int or not 0<=track<len(nodes):raise IndexError('Track out of range')
        t=nodes[track]
        comp=next((x for x in t.findall('./trackAudioParameters/component') if x.get('id')=='trackEQ'),None)
        if comp is None:raise ValueError('Track EQ unavailable')
        return {'session':str(src),'kind':kind,'track_index':track,
                'track_name':t.findtext('./trackParameters/name'),
                'powered':comp.get('powered'),
                'parameters':{x.get('name'):float(x.get('parameterValue')) for x in comp.findall('parameter')},
                'parameter_units':'Audition proprietary normalized 0..1, NOT Hz/dB'}

    @classmethod
    def patch_native_eq_normalized(cls,source,destination,settings:dict,*,track=0,
                                   kind='audioTrack',enabled=True,confirm=False):
        src,tree,r,_=cls._native_tree(source)
        dst=Path(destination).resolve()
        if (not src.name.startswith('ACCEPT_AU_') or dst==src or dst.exists() or
                dst.suffix.lower()!='.sesx' or not dst.parent.is_dir() or not dst.name.startswith('ACCEPT_AU_')):
            raise ValueError('Only new QA Audition SESX copy may be changed')
        if kind not in ('audioTrack','busTrack'):raise ValueError('Unsupported track kind')
        nodes=r.findall('.//'+kind)
        if type(track)!=int or not 0<=track<len(nodes):raise IndexError('Track not found')
        target=nodes[track]
        label=target.findtext('./trackParameters/name') or ''
        if not label.startswith('QA '):raise PermissionError('Track must have QA label')
        if type(enabled)!=bool:raise ValueError('enabled boolean required')
        if not isinstance(settings,dict) or not 1<=len(settings)<=32:
            raise ValueError('1..32 EQ parameter assignments required')
        component=next((x for x in target.findall('./trackAudioParameters/component') if x.get('id')=='trackEQ'),None)
        if component is None:raise ValueError('No serialized track EQ component')
        names={x.get('name'):x for x in component.findall('parameter')}
        pattern=re.compile(r'^(?:EQ Band [1-5] (?:Gain|Center Frequency|Q|Enable|Bandwidth)|'
                           r'Low Shelf (?:Frequency|Gain|Enable)|High Shelf (?:Frequency|Gain|Enable)|'
                           r'High-Pass (?:Filter Enable|Cutoff Frequency|Slope)|'
                           r'Low-Pass (?:Filter Enable|Cutoff Frequency|Slope))$')
        for name,value in settings.items():
            if not isinstance(name,str) or not pattern.fullmatch(name) or name not in names:
                raise ValueError('Unknown/unsafe EQ parameter: '+str(name))
            if 'Enable' in name:
                if type(value)!=bool:raise ValueError('Enable must be boolean')
                val=1. if value else 0.
            else:
                if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(float(value)):
                    raise ValueError('Normalized 0..1 numerical value required')
                val=float(value)
                if not 0<=val<=1:raise ValueError('EQ value outside normalized range')
                # Actual Audition 26 render showed that 0.95 on normalized
                # EQ Band 3 Gain produced +26.4 dBFS FLOAT audio. Until the
                # proprietary mapping is calibrated, permit only tiny safe
                # offsets from neutral 0.5, not arbitrary gain values.
                if name.endswith(' Gain') and not 0.49<=val<=0.51:
                    raise ValueError('Uncalibrated native EQ gain outside conservative 0.49..0.51 range')
            names[name].set('parameterValue',str(val))
        component.set('powered','true' if enabled else 'false')
        if not confirm:return {'dry_run':True,'settings':settings,'output':str(dst),'units':'normalized'}
        before=hashlib.sha256(src.read_bytes()).hexdigest()
        raw=ET.tostring(r,encoding='utf8',xml_declaration=True)
        ET.fromstring(raw)
        dst.write_bytes(raw)
        if hashlib.sha256(src.read_bytes()).hexdigest()!=before:
            dst.unlink(missing_ok=True);raise RuntimeError('Original SESX changed')
        proof=cls.inspect_native_eq(dst,track=track,kind=kind)
        if (proof['powered']=='true')!=enabled:raise RuntimeError('Power state readback failed')
        for name,value in settings.items():
            if abs(proof['parameters'][name]-(float(value)))>1e-6:
                raise RuntimeError('EQ parameter readback failed: '+name)
        return {'source':str(src),'output':str(dst),'settings':settings,
                'verified_native_schema':True,'units':'normalized, not dB/Hz',
                'source_unmodified':True,'native_reopened':False,
                'sha256':hashlib.sha256(dst.read_bytes()).hexdigest()}
