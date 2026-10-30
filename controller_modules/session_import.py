"""WAV import using observed native SESX clip/track templates, write-new only."""
from pathlib import Path
from copy import deepcopy
import os
import uuid
from lxml import etree as ET


class AuditionSessionImport:
    @classmethod
    def import_production_wavs(cls, source, destination, placements, *, confirm=False):
        src, tree, root, tracks = cls._native_tree(source)
        before = cls._hash_file(src)
        session = root.find('session')
        rate = int(session.get('sampleRate'))
        if not isinstance(placements, list) or not 1 <= len(placements) <= 100:
            raise ValueError('1..100 WAV placements required')
        trackmap = {t.get('id'): t for t in tracks}
        if len(trackmap) != len(tracks):
            raise ValueError('Duplicate track IDs')
        files = root.find('files')
        if files is None: files = session.find('files')
        if files is None: raise ValueError('Native files collection required')
        wav_template = next((f for f in files.findall('file') if f.get('mediaHandler') == 'AmioWav'), None)
        if wav_template is None: raise ValueError('Native AmioWav file template required')
        clip_templates = {}
        for track in tracks:
            clip = track.find('audioClip')
            if clip is not None and clip.get('looped') != 'true':
                channel_type = track.find('trackAudioParameters').get('audioChannelType')
                clip_templates.setdefault(channel_type, (track, clip))
        ids = [c.get('id') for c in root.findall('.//audioClip')]
        if len(ids) != len(set(ids)): raise ValueError('Duplicate clip IDs')
        next_clip = max((int(x) for x in ids), default=0)+1
        all_tracks = session.find('tracks')
        next_track = max(int(t.get('id')) for t in all_tracks if t.get('id'))+1
        next_index = max(int(t.get('index', '0')) for t in all_tracks if t.tag != 'masterTrack')+1
        fids = [f.get('id') for f in files.findall('file')]
        if len(fids) != len(set(fids)): raise ValueError('Duplicate media IDs')
        next_file = max((int(x) for x in fids), default=-1)+1
        changes, source_hashes = [], {}
        for item in placements:
            if not isinstance(item, dict) or set(item)-{'source','start_samples','track_id','new_track_name'}:
                raise ValueError('Unknown placement fields')
            if ('track_id' in item) == ('new_track_name' in item):
                raise ValueError('Specify exactly one track_id or new_track_name')
            path = Path(item['source']).resolve()
            sr, audio, meta = cls._read_wav(path)
            if sr != rate or not len(audio):
                raise ValueError('WAV must be nonempty and match session sample rate')
            pos = item.get('start_samples', 0)
            if type(pos) is not int or not 0 <= pos <= 2**53-len(audio):
                raise ValueError('Invalid sample position')
            layout = 'mono' if audio.shape[1] == 1 else 'stereo'
            if layout not in clip_templates:
                raise ValueError('A native unlooped '+layout+' clip template is required')
            template_track, template_clip = clip_templates[layout]
            if 'new_track_name' in item:
                name = item['new_track_name']
                if not isinstance(name, str) or not name.strip() or len(name) > 96:
                    raise ValueError('Valid new track name required')
                target = deepcopy(template_track)
                for component in target.iter('component'):
                    if component.get('componentGuid'): component.set('componentGuid',str(uuid.uuid4()))
                for clip in target.findall('audioClip'): target.remove(clip)
                # Do not clone automation or effects from a user's source track.
                for child in list(target):
                    if child.tag not in ('trackParameters','trackAudioParameters','editParameter'):
                        target.remove(child)
                audio_params = target.find('trackAudioParameters')
                for child in list(audio_params):
                    if child.tag == 'component' and child.get('id') in ('trackFader','trackMute','trackPan','trackEQ'):
                        for parameter in child.findall('parameter'):
                            for automation in list(parameter): parameter.remove(automation)
                        if child.get('id') == 'trackEQ': child.set('powered','false')
                        for parameter in child.findall('parameter'):
                            if child.get('id') == 'trackFader': parameter.set('parameterValue','1')
                            elif child.get('id') in ('trackMute','trackPan'): parameter.set('parameterValue','0')
                    elif child.tag != 'trackOutput':
                        audio_params.remove(child)
                audio_params.set('recordArmed','false'); audio_params.set('solo','false'); audio_params.set('monitoring','false')
                target.find('./trackParameters/name').text = name.strip()
                target.set('id',str(next_track)); target.set('index',str(next_index))
                next_track += 1; next_index += 1
                master = all_tracks.find('masterTrack')
                if master is not None:
                    master.set('index',str(next_index))
                    all_tracks.insert(list(all_tracks).index(master),target)
                else: all_tracks.append(target)
                trackmap[target.get('id')] = target
            else:
                target = trackmap.get(str(item['track_id']))
                if target is None or target.find('trackAudioParameters').get('audioChannelType') != layout:
                    raise ValueError('Destination track must exist and match WAV channels')
            digest = cls._hash_file(path); source_hashes[str(path)] = digest
            file_node = deepcopy(wav_template)
            file_node.set('id', str(next_file)); file_node.set('absolutePath', str(path))
            file_node.attrib.pop('importerPrivateSettings', None)
            try: file_node.set('relativePath', os.path.relpath(path, Path(destination).resolve().parent).replace('\\','/'))
            except ValueError: file_node.attrib.pop('relativePath', None)
            files.append(file_node)
            clip = deepcopy(template_clip)
            for component in clip.iter('component'):
                if component.get('componentGuid'): component.set('componentGuid',str(uuid.uuid4()))
            for child in list(clip):
                if child.tag not in ('component','fadeIn','fadeOut','channelMap','editParameter'): clip.remove(child)
                elif child.tag == 'component':
                    if child.get('id') not in ('clipGain','clipMute','clipPan'):
                        clip.remove(child); continue
                    for parameter in child.findall('parameter'):
                        for automation in list(parameter): parameter.remove(automation)
                        parameter.set('parameterValue','1' if child.get('id') == 'clipGain' else '0')
            for key,value in dict(id=next_clip,fileID=next_file,name=path.stem,startPoint=pos,endPoint=pos+len(audio),sourceInPoint=0,sourceOutPoint=len(audio),offline='false',select='false',lockedInTime='false',looped='false',crossFadeHeadClipID=-1,crossFadeTailClipID=-1).items():
                clip.set(key,str(value))
            for tag,point in (('fadeIn',0),('fadeOut',len(audio))):
                fade = clip.find(tag)
                if fade is not None:
                    fade.set('startPoint',str(point)); fade.set('endPoint',str(point))
            target.append(clip)
            changes.append(dict(track_id=target.get('id'),clip_id=str(next_clip),file_id=str(next_file),source=str(path),sha256=digest))
            next_clip += 1; next_file += 1
            session.set('duration',str(max(int(session.get('duration','0')),pos+len(audio))))
        if any(cls._hash_file(path) != digest for path,digest in source_hashes.items()):
            raise RuntimeError('Input WAV changed during import')
        return cls._production_publish(src,destination,root,before,confirm,changes)
