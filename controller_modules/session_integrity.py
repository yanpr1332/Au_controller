"""Read-only Audition SESX preflight and risk report for advanced controller operations.
Only reliable structural checks are blockers; unverified heuristics are warnings.
"""
from __future__ import annotations
from pathlib import Path
from collections import defaultdict
import hashlib,json,math

class AuditionSessionIntegrity:
    @classmethod
    def audit_native_session(cls,session,*,reject_hot_eq=True):
        src,tree,r,tracks=cls._native_tree(session)
        routes=cls.inspect_session_routes(src)
        clips=cls.inspect_native_clips_advanced(src)
        markers=cls.native_sesx_markers_xmp(src)
        media=r.findall('./files/file')
        file_ids=[x.get('id') for x in media]
        errors=[];warnings=[]
        if len(file_ids)!=len(set(file_ids)):
            errors.append('Duplicate native media IDs')
        media_map={x.get('id'):x for x in media}
        for x in media:
            path=x.get('absolutePath')
            if not path or not Path(path).is_file():
                errors.append('Missing media '+str(x.get('id')))
        if not routes['valid_topology']:
            errors.append('Bus routing cycles/dangling destinations')
        allclips=defaultdict(list)
        for ti,tr in enumerate(tracks):
            name=tr.findtext('./trackParameters/name') or ''
            eq=next((node for node in tr.findall('./trackAudioParameters/component') if node.get('id')=='trackEQ'),None)
            if eq is not None and eq.get('powered')=='true':
                for par in eq.findall('parameter'):
                    key=par.get('name','')
                    if key.endswith(' Gain'):
                        try:gain=float(par.get('parameterValue'))
                        except Exception:errors.append('Malformed EQ gain on '+name);continue
                        if not math.isfinite(gain):
                            errors.append('Non-finite EQ gain '+name)
                        elif not .49<=gain<=.51:
                            txt='Uncalibrated EQ gain on '+name+' ('+key+')'
                            if reject_hot_eq:errors.append(txt)
                            else:warnings.append(txt)
            for cl in tr.findall('audioClip'):
                fname=cl.get('name','')
                fid=cl.get('fileID')
                if fid not in media_map:errors.append('Unresolved fileID '+str(fid))
                try:
                    st=int(cl.get('startPoint'));en=int(cl.get('endPoint'))
                    sin=int(cl.get('sourceInPoint'));sout=int(cl.get('sourceOutPoint'))
                except Exception:
                    errors.append('Bad clip timestamps '+fname);continue
                if min(st,sin)<0 or st>=en or sin>=sout:
                    errors.append('Invalid range '+fname)
                elif en-st!=sout-sin and cl.get('looped')!='true':
                    errors.append('Clip source/play duration mismatch '+fname)
                allclips[ti].append((st,en,fname))
                for fade_tag in ('fadeIn','fadeOut'):
                    fade=cl.find(fade_tag)
                    if fade is None:continue
                    lo=int(fade.get('startPoint'));hi=int(fade.get('endPoint'))
                    if not sin<=lo<=hi<=sout:
                        errors.append('Invalid '+fade_tag+' range on '+fname)
        for ti,entries in allclips.items():
            entries.sort()
            for a,b in zip(entries,entries[1:]):
                if b[0]<a[1]:
                    warnings.append('Overlapping clips on track '+str(ti))
        rate=markers.get('sample_rate')
        session_el=r.find('session')
        sess_samples=int(session_el.get('duration','0')) if session_el is not None else 0
        for m in markers.get('markers',[]):
            if m['start_samples']>max(sess_samples,max([c['end'] for c in clips['clips']],default=0)):
                warnings.append('Marker outside session timeline '+m['name'])
        return {'source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),
            'passed':not errors,'error_count':len(errors),'warning_count':len(warnings),
            'errors':errors,'warnings':warnings,
            'checks':{'track_count':len(tracks),'clip_count':clips['clip_count'],
                'bus_count':routes['bus_tracks'],'native_markers':markers['count'],
                'file_count':len(media),'routes_valid':routes['valid_topology'],
                'project_sample_rate':rate},
            'native_audition_app_opened':False,
            'note':'Structural preflight only. Success does not imply third-party VSTs, audio content, or external media are correct.'}
    @classmethod
    def write_native_session_audit(cls,session,destination,*,confirm=False):
        out=Path(destination).resolve()
        if not out.parent.is_dir() or out.exists() or out.suffix.lower()!='.json':
            raise ValueError('New JSON report required')
        if not confirm:return {'dry_run':True,'destination':str(out)}
        report=cls.audit_native_session(session)
        out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
        return {'path':str(out),'passed':report['passed'],
                'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),
                'error_count':report['error_count']}
