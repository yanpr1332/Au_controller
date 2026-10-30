"""SESX automation/send models obtained from a real Au 26 SDK save."""
from lxml import etree as ET
import math
import uuid


class AuditionNativeAutomation:
    @classmethod
    def patch_native_pan_position(cls, source, destination, *, track_id, position, confirm=False):
        """Position -1..1 maps to native StereoPanner percentage -100..100.

        The legacy raw pan field uses serialized percentage units; +/-1 there
        is only a one-percent adjustment, as confirmed by native stereo renders.
        """
        if type(position) not in (int,float) or not math.isfinite(position) or not -1<=position<=1:
            raise ValueError('Finite pan position -1..1 required')
        src,tree,root,tracks=cls._native_tree(source);before=cls._hash_file(src)
        selected=[t for t in root.findall('.//audioTrack')+root.findall('.//busTrack') if t.get('id')==str(track_id)]
        if len(selected)!=1:raise ValueError('Unique track ID required')
        components=[c for c in selected[0].findall('./trackAudioParameters/component') if c.get('id')=='trackPan' and c.get('componentID')=='Audition.StereoPanner']
        if len(components)!=1:raise ValueError('Existing native StereoPanner required')
        params=[p for p in components[0].findall('parameter') if p.get('name')=='Pan']
        if len(params)!=1:raise ValueError('Unique Pan parameter required')
        if params[0].find('parameterKeyframes') is not None:raise ValueError('Pan already automated; edit its envelope explicitly')
        params[0].set('parameterValue',str(position*100))
        return cls._production_publish(src,destination,root,before,confirm,[dict(track_id=str(track_id),position=position,native_percent=position*100)])

    @classmethod
    def patch_native_track_envelope(cls, source, destination, *, track_id, points, component_id='trackFader', parameter_index=0, confirm=False):
        """Native normalized envelope values, not linear audio gain or dB."""
        src,tree,root,tracks=cls._native_tree(source);before=cls._hash_file(src)
        if component_id not in ('trackFader','trackPan') or type(parameter_index) is not int or parameter_index!=0:
            raise ValueError('Only native volume/pan parameter zero is currently supported')
        selected=[t for t in root.findall('.//audioTrack')+root.findall('.//busTrack')+root.findall('.//masterTrack') if t.get('id')==str(track_id)]
        if len(selected)!=1:raise ValueError('Unique track ID required')
        track=selected[0];ap=track.find('trackAudioParameters')
        matches=[c for c in ap.findall('component') if c.get('id')==component_id]
        if len(matches)!=1:raise ValueError('Unique existing native component required')
        params=[p for p in matches[0].findall('parameter') if p.get('index')=='0']
        if len(params)!=1:raise ValueError('Unique existing native parameter required')
        if not isinstance(points,list) or not 1<=len(points)<=4096:raise ValueError('1..4096 points required')
        duration=int(root.find('session').get('duration'));previous=-1
        keys=ET.Element('parameterKeyframes',enableSplines='false',readOnly='false')
        for point in points:
            if not isinstance(point,dict) or set(point)-{'sample','value','hold'} or 'sample' not in point or 'value' not in point:
                raise ValueError('Point requires sample/value and optional hold')
            sample,value=point['sample'],point['value'];hold=point.get('hold',False)
            if type(sample) is not int or not previous<sample<=duration or type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=1 or type(hold) is not bool:
                raise ValueError('Ordered in-range samples and normalized finite values required')
            ET.SubElement(keys,'parameterKeyframe',sampleOffset=str(sample),select='false',type='hold' if hold else 'linear',value=str(value))
            previous=sample
        parameter=params[0]
        for old in parameter.findall('parameterKeyframes'):parameter.remove(old)
        parameter.append(keys);ap.set('automationMode','1');track.set('automationLaneOpenState','true')
        return cls._production_publish(src,destination,root,before,confirm,[dict(track_id=str(track_id),component_id=component_id,points=points,units='native_normalized')])

    @classmethod
    def patch_native_send(cls, source, destination, *, track_id, bus_id, slot=0, level=0.25, pre_fader=False, enabled=True, confirm=False):
        src,tree,root,tracks=cls._native_tree(source);before=cls._hash_file(src)
        if type(slot) is not int or not 0<=slot<16 or type(level) not in (int,float) or not math.isfinite(level) or not 0<=level<=1 or type(pre_fader) is not bool or type(enabled) is not bool:
            raise ValueError('Invalid send slot/level/flags')
        tracks=root.findall('.//audioTrack')+root.findall('.//busTrack')+root.findall('.//masterTrack')
        mapping={t.get('id'):t for t in tracks}
        if len(mapping)!=len(tracks):raise ValueError('Duplicate native track IDs')
        owner=mapping.get(str(track_id));bus=mapping.get(str(bus_id))
        if owner is None or bus is None or bus.tag!='busTrack' or owner is bus:raise ValueError('Existing owner and distinct bus required')
        sends=owner.find('sendList')
        if sends is None:sends=ET.SubElement(owner,'sendList')
        matches=[s for s in sends.findall('sendSlot') if s.get('slotIndex')==str(slot)]
        if len(matches)>1:raise ValueError('Duplicate send slots')
        node=matches[0] if matches else ET.SubElement(sends,'sendSlot',slotIndex=str(slot))
        node.set('sendOutputID',str(bus_id));node.set('preFader',str(pre_fader).lower())
        components=[c for c in node.findall('component') if c.get('id')=='sendComponent']
        if len(components)>1:raise ValueError('Duplicate send components')
        component=components[0] if components else ET.SubElement(node,'component',componentGuid=str(uuid.uuid4()),componentID='Audition.Send',id='sendComponent',powered='true')
        component.set('powered',str(enabled).lower())
        for index,name,value in (('0','Power On/Off',int(enabled)),('1','Level',level)):
            params=[p for p in component.findall('parameter') if p.get('index')==index]
            if len(params)>1:raise ValueError('Duplicate send parameter')
            parameter=params[0] if params else ET.SubElement(component,'parameter',index=index,name=name)
            parameter.set('parameterValue',str(value))
        if not any(c.get('id')=='sendPan' for c in node.findall('component')):
            pan=ET.SubElement(node,'component',componentGuid=str(uuid.uuid4()),componentID='Audition.StereoPanner',id='sendPan',name='StereoPanner',powered='true')
            ET.SubElement(pan,'parameter',index='0',name='Pan',parameterValue='0')
        graph={key:[] for key in mapping}
        for key,track in mapping.items():
            output=track.find('./trackAudioParameters/trackOutput')
            if output is not None and output.get('type')=='trackID':graph[key].append(output.get('outputID'))
            graph[key].extend(s.get('sendOutputID') for s in track.findall('./sendList/sendSlot'))
        def visit(key,active,done):
            if key in active:raise ValueError('Send introduces routing feedback')
            if key in done:return
            if key not in graph:raise ValueError('Dangling native route')
            active.add(key)
            for target in graph[key]:visit(target,active,done)
            active.remove(key);done.add(key)
        done=set()
        for key in graph:visit(key,set(),done)
        return cls._production_publish(src,destination,root,before,confirm,[dict(track_id=str(track_id),bus_id=str(bus_id),slot=slot,level=level,pre_fader=pre_fader,enabled=enabled)])
