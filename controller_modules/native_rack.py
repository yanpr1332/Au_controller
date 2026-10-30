"""Native effects Rack editing using Au-saved slot/preset data."""
from pathlib import Path
from copy import deepcopy
import json
import uuid
import hashlib
from lxml import etree as ET


class AuditionNativeRack:
    @staticmethod
    def _rack_track(root,track_id):
        tracks=[t for t in root.findall('.//audioTrack')+root.findall('.//busTrack')+root.findall('.//masterTrack') if t.get('id')==str(track_id)]
        if len(tracks)!=1:raise ValueError('Unique native track ID required')
        return tracks[0]

    @staticmethod
    def _rack_refresh_guids(rack):
        for component in rack.iter('component'):
            if component.get('componentGuid'):component.set('componentGuid',str(uuid.uuid4()))

    @classmethod
    def edit_native_rack(cls,source,destination,*,track_id,operations,confirm=False):
        src,tree,root,tracks=cls._native_tree(source);before=cls._hash_file(src)
        owner=cls._rack_track(root,track_id);rack=owner.find('effectsRack')
        if not isinstance(operations,list) or not 1<=len(operations)<=64:raise ValueError('1..64 Rack operations required')
        for op in operations:
            if not isinstance(op,dict):raise ValueError('Rack operation object required')
            action=op.get('action')
            if action=='copy_slot':
                if set(op)!={'action','template_session','template_track_id','template_slot','slot'}:raise ValueError('Exact copy_slot fields required')
                template_src,_,template_root,_=cls._native_tree(op['template_session'])
                template_owner=cls._rack_track(template_root,op['template_track_id']);template_rack=template_owner.find('effectsRack')
                if template_rack is None:raise ValueError('Template Rack missing')
                if owner.find('trackAudioParameters').get('audioChannelType')!=template_owner.find('trackAudioParameters').get('audioChannelType'):
                    raise ValueError('Template Rack channel layout mismatch')
                if any(type(op[k]) is not int or not 0<=op[k]<16 for k in ('slot','template_slot')):raise ValueError('Rack slots must be 0..15')
                slots=[s for s in template_rack.findall('slot') if s.get('slotIndex')==str(op['template_slot'])]
                if len(slots)!=1:raise ValueError('Unique template slot required')
                if rack is None:
                    rack=deepcopy(template_rack)
                    for slot in rack.findall('slot'):rack.remove(slot)
                    cls._rack_refresh_guids(rack)
                    ap=owner.find('trackAudioParameters');owner.insert(list(owner).index(ap)+1,rack)
                if any(s.get('slotIndex')==str(op['slot']) for s in rack.findall('slot')):raise ValueError('Destination slot occupied')
                slot=deepcopy(slots[0]);slot.set('slotIndex',str(op['slot']));cls._rack_refresh_guids(slot);rack.append(slot)
            elif rack is None:raise ValueError('Native Rack missing')
            elif action=='reorder':
                if set(op)!={'action','order'}:raise ValueError('Exact reorder fields required')
                slots=rack.findall('slot');mapping={int(s.get('slotIndex')):s for s in slots};order=op['order']
                if len(mapping)!=len(slots) or not isinstance(order,list) or any(type(i) is not int for i in order) or len(order)!=len(slots) or len(set(order))!=len(order) or set(order)!=set(mapping):
                    raise ValueError('Order must contain every existing slot exactly once')
                for slot in slots:rack.remove(slot)
                for index,old in enumerate(order):
                    mapping[old].set('slotIndex',str(index));rack.append(mapping[old])
            elif action in ('power','remove'):
                allowed={'action','slot','enabled'} if action=='power' else {'action','slot'}
                if set(op)!=allowed or type(op['slot']) is not int:raise ValueError('Exact slot operation fields required')
                slots=[s for s in rack.findall('slot') if s.get('slotIndex')==str(op['slot'])]
                if len(slots)!=1:raise ValueError('Unique slot required')
                if action=='remove':rack.remove(slots[0])
                else:
                    if type(op['enabled']) is not bool:raise ValueError('Boolean slot power required')
                    slots[0].set('powered',str(op['enabled']).lower())
            elif action=='pre_fader':
                if set(op)!={'action','enabled'} or type(op['enabled']) is not bool:raise ValueError('Boolean pre_fader required')
                rack.set('preFader',str(op['enabled']).lower())
            else:raise ValueError('Unsupported Rack action')
        return cls._production_publish(src,destination,root,before,confirm,operations)

    @classmethod
    def export_native_rack_preset(cls,source,destination,*,track_id,confirm=False):
        src,tree,root,tracks=cls._native_tree(source);owner=cls._rack_track(root,track_id)
        rack=owner.find('effectsRack');dst=Path(destination).resolve()
        if rack is None:raise ValueError('Native Rack missing')
        if dst.exists() or dst.suffix.lower()!='.json' or not dst.parent.is_dir() or type(confirm) is not bool:raise ValueError('New preset JSON required')
        payload=ET.tostring(rack,encoding='utf-8').decode('utf8')
        preset=dict(schema='audition-native-rack-v1',channel_layout=owner.find('trackAudioParameters').get('audioChannelType'),rack_xml=payload,sha256=hashlib.sha256(payload.encode()).hexdigest())
        if confirm:
            with dst.open('x',encoding='utf8') as handle:json.dump(preset,handle,ensure_ascii=False,indent=2)
        return dict(dry_run=not confirm,output=str(dst),slots=len(rack.findall('slot')),native_plugins_verified=False)

    @classmethod
    def apply_native_rack_preset(cls,source,destination,preset,*,track_id,confirm=False):
        src,tree,root,tracks=cls._native_tree(source);before=cls._hash_file(src)
        data=json.loads(Path(preset).read_text(encoding='utf8'))
        if set(data)!={'schema','channel_layout','rack_xml','sha256'} or data['schema']!='audition-native-rack-v1' or not isinstance(data['rack_xml'],str):raise ValueError('Unknown Rack preset schema')
        payload=data['rack_xml'].encode('utf8')
        if len(payload)>16*1024*1024 or hashlib.sha256(payload).hexdigest()!=data['sha256']:raise ValueError('Rack preset checksum mismatch or oversized')
        if b'<!DOCTYPE' in payload.upper() or b'<!ENTITY' in payload.upper():raise ValueError('DTD/entities are not permitted in presets')
        rack=ET.fromstring(payload,parser=ET.XMLParser(resolve_entities=False,no_network=True))
        if rack.tag!='effectsRack' or len(rack.findall('slot'))>16:raise ValueError('Invalid native Rack')
        indices=[s.get('slotIndex') for s in rack.findall('slot')]
        if len(indices)!=len(set(indices)) or any(not i or not i.isdigit() or not 0<=int(i)<16 for i in indices):raise ValueError('Invalid Rack slot indices')
        owner=cls._rack_track(root,track_id)
        if owner.find('trackAudioParameters').get('audioChannelType')!=data['channel_layout']:raise ValueError('Preset channel layout mismatch')
        cls._rack_refresh_guids(rack)
        old=owner.find('effectsRack')
        if old is not None:index=list(owner).index(old);owner.remove(old)
        else:index=list(owner).index(owner.find('trackAudioParameters'))+1
        owner.insert(index,rack)
        return cls._production_publish(src,destination,root,before,confirm,[dict(action='apply_rack_preset',preset=str(Path(preset).resolve()),track_id=str(track_id))])
