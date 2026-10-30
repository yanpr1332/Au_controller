"""Audition 26 native SESX bus topology tools.
Read/patch native XML of new session copies, never modify originals.
Route QA audio tracks into QA buses while retaining a valid master path.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from lxml import etree as ET

class AuditionBusRouting:
    @classmethod
    def inspect_session_routes(cls,source):
        p,tree,root,tracks=cls._native_tree(source)
        master=root.find('.//masterTrack')
        if master is None:raise ValueError('Native masterTrack missing')
        buslist=root.findall('.//busTrack')
        alltracks=tracks+buslist+[master]
        ids=[t.get('id') for t in alltracks]
        if len(set(ids))!=len(ids):raise ValueError('Duplicate session track ID')
        mappings=[]
        for tr in alltracks:
            out=tr.find('./trackAudioParameters/trackOutput')
            routes={'track_id':tr.get('id'),
                    'name':tr.findtext('./trackParameters/name'),
                    'type':tr.tag,
                    'output_id':out.get('outputID') if out is not None else None,
                    'routing_type':out.get('type') if out is not None else None}
            mappings.append(routes)
        graph={x['track_id']:x['output_id'] for x in mappings if x['routing_type']=='trackID'}
        loops=[]
        for source_id in graph:
            seen=set();current=source_id
            while current in graph:
                if current in seen:
                    loops.append(source_id);break
                seen.add(current);current=graph[current]
        dangling=[x for x in mappings if x['routing_type']=='trackID' and x['output_id'] not in ids]
        return {'session':str(p),'audio_tracks':len(tracks),'bus_tracks':len(buslist),
                'master_id':master.get('id'),'routes':mappings,
                'cycles':sorted(set(loops)),'dangling_routes':dangling,
                'valid_topology':not loops and not dangling}

    @classmethod
    def patch_session_bus_route(cls,source,destination,*,track_index=0,bus_index=0,
                                confirm=False):
        src,tree,root,tracks=cls._native_tree(source)
        dst=Path(destination).resolve()
        if dst==src or dst.exists() or dst.suffix.lower()!='.sesx' or not dst.parent.is_dir():
            raise ValueError('New SESX output required; overwrite forbidden')
        buses=root.findall('.//busTrack')
        if type(track_index)!=int or not 0<=track_index<len(tracks):
            raise IndexError('Track index out of bounds')
        if type(bus_index)!=int or not 0<=bus_index<len(buses):
            raise IndexError('Bus index out of bounds')
        tr=tracks[track_index];bus=buses[bus_index]
        if not (tr.findtext('./trackParameters/name') or '').startswith('QA '):
            raise PermissionError('Routing only QA labeled audio tracks')
        if not (bus.findtext('./trackParameters/name') or '').startswith('QA '):
            raise PermissionError('Routing only QA labeled bus tracks')
        target=bus.get('id')
        own=tr.get('id')
        if not target or target==own:raise ValueError('Invalid bus ID')
        out=tr.find('./trackAudioParameters/trackOutput')
        if out is None or out.get('type')!='trackID':
            raise ValueError('Unsupported track-output type')
        if not confirm:return {'dry_run':True,'track':track_index,'bus':bus_index,
                               'target_output_id':target}
        orig_hash=hashlib.sha256(src.read_bytes()).hexdigest()
        out.set('outputID',target)
        payload=ET.tostring(root,encoding='utf8',xml_declaration=True)
        ET.fromstring(payload)
        dst.write_bytes(payload)
        route=cls.inspect_session_routes(dst)
        if not route['valid_topology']:
            dst.unlink()
            raise RuntimeError('Refuse output with cyclic/dangling bus routes')
        if hashlib.sha256(src.read_bytes()).hexdigest()!=orig_hash:
            dst.unlink();raise RuntimeError('Source changed unexpectedly')
        return {'source':str(src),'destination':str(dst),
                'routed_track_id':own,'bus_id':target,
                'topology_valid':True,
                'sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),
                'native_reopen_verified':False}

    @classmethod
    def remove_unused_bus_sesx(cls,source,destination,*,bus_index:int,
                               expected_name:str,confirm:bool=False):
        """Conservatively remove only unused QA bus from new SESX copy.

        Audition 26 native audioBusTracks.remove returned "The object is invalid",
        so this route performs native-SESX file editing, NOT native DOM removal.
        It cannot remove a bus referenced by a track or another bus.
        """
        src,tree,root,tracks=cls._native_tree(source)
        target=Path(destination).resolve()
        if target==src or target.exists() or target.suffix.lower()!='.sesx' or not target.parent.is_dir():
            raise ValueError('New SESX file required, source and output must differ')
        buses=root.findall('.//busTrack')
        if type(bus_index)!=int or not 0<=bus_index<len(buses):raise IndexError('Invalid bus index')
        bus=buses[bus_index]
        name=bus.findtext('./trackParameters/name')
        if (not isinstance(expected_name,str) or name!=expected_name or
                not name.startswith('QA ')):
            raise PermissionError('Exact QA-only bus name required')
        bus_id=bus.get('id')
        if not bus_id or bus.findall('audioClip'):raise ValueError('Bus is not empty')
        nested=set(bus.iter())
        references=[]
        for element in root.iter():
            if element in nested:continue
            for key,value in element.attrib.items():
                if value==bus_id:
                    references.append({'tag':element.tag,'attr':key})
        if references:raise ValueError('Bus is referenced by other session objects: '+str(references[:5]))
        before=cls.inspect_session_routes(src)
        if not before['valid_topology']:raise ValueError('Invalid original session routing')
        if not confirm:return {'dry_run':True,'name':name,'bus_id':bus_id,
                               'existing_buses':len(buses)}
        parent=bus.getparent()
        if parent is None or parent.tag!='tracks':raise ValueError('Unsupported native bus parent')
        original_hash=hashlib.sha256(src.read_bytes()).hexdigest()
        parent.remove(bus)
        data=ET.tostring(root,encoding='utf8',xml_declaration=True)
        ET.fromstring(data)
        target.write_bytes(data)
        try:
            after=cls.inspect_session_routes(target)
            if not after['valid_topology'] or after['bus_tracks']!=before['bus_tracks']-1:
                raise ValueError('Output session topology invalid')
            if hashlib.sha256(src.read_bytes()).hexdigest()!=original_hash:
                raise RuntimeError('Original session changed')
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return {'source':str(src),'destination':str(target),'removed_name':name,
                'removed_id':bus_id,'bus_count_after':after['bus_tracks'],
                'source_intact':True,'destination_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
                'native_dom_delete':False,'native_reopen_verified':False}
