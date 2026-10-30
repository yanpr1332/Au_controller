"""Write-new production SESX edits. File editing is not live host acceptance."""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import math
import tempfile
import shutil
import uuid
from lxml import etree as ET


class AuditionProductionSession:
    @classmethod
    def package_production_session(cls, source, destination, *, confirm=False):
        """Copy all explicitly resolved media and SESX into a new directory.

        Relative paths are written for relocation; host reopening elsewhere still
        requires independent acceptance. Missing media is never silently skipped.
        """
        src, tree, root, tracks = cls._native_tree(source)
        dst = Path(destination).resolve()
        if dst.exists() or not dst.parent.is_dir() or type(confirm) is not bool:
            raise ValueError('New package directory and Boolean confirm required')
        files = root.findall('./files/file') + root.findall('./session/files/file')
        if not files:
            raise ValueError('No native media references found')
        records = []
        ids = set()
        for index, node in enumerate(files):
            fid = node.get('id')
            if not fid or fid in ids:
                raise ValueError('Missing or duplicate media file ID')
            ids.add(fid)
            absolute = node.get('absolutePath')
            media = Path(absolute) if absolute else Path('missing')
            if not media.is_file():
                relative = node.get('relativePath')
                media = src.parent / relative if relative else media
            media = media.resolve()
            if not media.is_file():
                raise FileNotFoundError('Unresolved media ID '+fid)
            name = str(index)+'_'+media.name
            records.append(dict(file_id=fid, source=str(media), name=name, sha256=cls._hash_file(media)))
            node.set('relativePath', 'media/'+name)
            node.set('absolutePath', str(dst/'media'/name))
        before = cls._hash_file(src)
        if not confirm:
            return dict(dry_run=True, output=str(dst), media=records)
        with tempfile.TemporaryDirectory(prefix='.au_package_', dir=dst.parent) as temp:
            package = Path(temp)/'package'
            (package/'media').mkdir(parents=True)
            for record in records:
                target = package/'media'/record['name']
                shutil.copy2(record['source'], target)
                if cls._hash_file(target) != record['sha256']:
                    raise RuntimeError('Copied media checksum mismatch')
            session = package/'session.sesx'
            session.write_bytes(ET.tostring(root, encoding='utf8', xml_declaration=True))
            manifest = dict(source=str(src), source_sha256=before, session='session.sesx',
                            session_sha256=cls._hash_file(session), media=records,
                            native_reopen_verified=False)
            (package/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf8')
            if cls._hash_file(src) != before or any(cls._hash_file(r['source']) != r['sha256'] for r in records):
                raise RuntimeError('Source changed during packaging')
            package.rename(dst)
        return dict(output=str(dst), session=str(dst/'session.sesx'), media_count=len(records), native_reopen_verified=False)

    @staticmethod
    def _production_publish(source, destination, root, before, confirm, changes):
        src, dst = Path(source).resolve(), Path(destination).resolve()
        if dst == src or dst.exists() or dst.suffix.lower() != '.sesx' or not dst.parent.is_dir():
            raise ValueError('New SESX destination in existing directory required')
        payload = ET.tostring(root, encoding='utf8', xml_declaration=True)
        ET.fromstring(payload)
        if type(confirm) is not bool:
            raise ValueError('confirm must be Boolean')
        result = dict(dry_run=not confirm, changes=changes, output=str(dst),
                      native_reopen_verified=False, source_sha256=before)
        if confirm:
            if hashlib.sha256(src.read_bytes()).hexdigest() != before:
                raise RuntimeError('Source changed during planning')
            created = False
            try:
                with dst.open('xb') as handle:
                    created = True
                    handle.write(payload)
            except Exception:
                if created:
                    dst.unlink(missing_ok=True)
                raise
            result['output_sha256'] = hashlib.sha256(payload).hexdigest()
        return result

    @classmethod
    def edit_production_session(cls, source, destination, operations, *, confirm=False):
        """Edit by stable track_id/clip_id; all positions are project samples.

        Unknown time-stretched/looped clip layouts are rejected for split/trim.
        Preserves unknown XML, effects and automation; never edits source files.
        """
        src, tree, root, tracks = cls._native_tree(source)
        before = hashlib.sha256(src.read_bytes()).hexdigest()
        if not isinstance(operations, list) or not 1 <= len(operations) <= 256:
            raise ValueError('1..256 operations required')
        trackmap = {t.get('id'): t for t in tracks}
        if len(trackmap) != len(tracks):
            raise ValueError('Duplicate track IDs')
        ids = [c.get('id') for c in root.findall('.//audioClip')]
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate clip IDs')
        next_id = max((int(x) for x in ids), default=0) + 1
        changes = []
        def integer(value):
            if type(value) is not int or value < 0:
                raise ValueError('Nonnegative integer sample position required')
            return value
        for op in operations:
            if not isinstance(op, dict):
                raise ValueError('Operation must be an object')
            action = op.get('action')
            allowed = {'move', 'copy', 'delete', 'ripple_delete', 'split', 'trim', 'fade', 'crossfade', 'rename_track'}
            if action not in allowed:
                raise ValueError('Unknown production operation')
            fields = {'move': {'target_track_id', 'start_samples'},
                      'copy': {'target_track_id', 'start_samples'},
                      'delete': set(), 'ripple_delete': set(),
                      'split': {'offset_samples'}, 'trim': {'source_in', 'source_out'},
                      'fade': {'edge', 'length_samples'}, 'crossfade': {'right_clip_id'}, 'rename_track': {'name'}}
            if set(op) - ({'action', 'track_id', 'clip_id'} | fields[action]):
                raise ValueError('Unexpected operation fields')
            track = trackmap.get(str(op.get('track_id')))
            if track is None:
                raise ValueError('Unknown track ID')
            if action == 'rename_track':
                name = op.get('name')
                node = track.find('./trackParameters/name')
                if node is None or not isinstance(name, str) or not name.strip() or len(name) > 96:
                    raise ValueError('Track name required')
                node.text = name.strip()
            else:
                found = [c for c in track.findall('audioClip') if c.get('id') == str(op.get('clip_id'))]
                if len(found) != 1:
                    raise ValueError('Unique clip ID required on selected track')
                clip = found[0]
                if clip.get('lockedInTime') == 'true':
                    raise ValueError('Unlock the clip explicitly in Audition before editing')
                start, end = int(clip.get('startPoint')), int(clip.get('endPoint'))
                si, so = int(clip.get('sourceInPoint')), int(clip.get('sourceOutPoint'))
                if end <= start or so <= si:
                    raise ValueError('Invalid clip duration')
                if action in ('move', 'copy'):
                    target = trackmap.get(str(op.get('target_track_id', op.get('track_id'))))
                    if target is None:
                        raise ValueError('Unknown destination track ID')
                    pos = integer(op.get('start_samples'))
                    if action == 'copy':
                        clip = deepcopy(clip)
                        for component in clip.iter('component'):
                            if component.get('componentGuid'): component.set('componentGuid',str(uuid.uuid4()))
                        clip.set('id', str(next_id)); next_id += 1
                    else:
                        track.remove(clip)
                    clip.set('startPoint', str(pos)); clip.set('endPoint', str(pos + end - start))
                    target.append(clip)
                elif action in ('delete', 'ripple_delete'):
                    others = [c for c in track.findall('audioClip') if c is not clip]
                    if action == 'ripple_delete':
                        if any(int(c.get('startPoint')) < end and int(c.get('endPoint')) > start for c in others):
                            raise ValueError('Ripple deletion intersects another clip')
                        for c in others:
                            if int(c.get('startPoint')) >= end:
                                for key in ('startPoint', 'endPoint'):
                                    c.set(key, str(int(c.get(key)) - (end - start)))
                    track.remove(clip)
                elif action == 'crossfade':
                    matches = [c for c in track.findall('audioClip') if c.get('id') == str(op.get('right_clip_id'))]
                    if len(matches) != 1 or matches[0] is clip:
                        raise ValueError('Distinct right clip required')
                    right = matches[0]
                    rs, re = int(right.get('startPoint')), int(right.get('endPoint'))
                    ri, ro = int(right.get('sourceInPoint')), int(right.get('sourceOutPoint'))
                    if not start <= rs < end <= re or end-start != so-si or re-rs != ro-ri:
                        raise ValueError('Crossfade requires overlapping, unstretched clips')
                    if right.get('lockedInTime') == 'true' or any(c.get('looped') == 'true' for c in (clip, right)):
                        raise ValueError('Crossfade requires unlocked, unlooped clips')
                    outfade, infade = clip.find('fadeOut'), right.find('fadeIn')
                    if outfade is None or infade is None:
                        raise ValueError('Existing native fade templates required')
                    length = end-rs
                    outfade.set('startPoint', str(so-length)); outfade.set('endPoint', str(so))
                    infade.set('startPoint', str(ri)); infade.set('endPoint', str(ri+length))
                elif action in ('split', 'trim'):
                    if clip.get('looped') == 'true' or end-start != so-si:
                        raise ValueError('Split/trim requires unlooped, unstretched clip')
                    if action == 'split':
                        offset = integer(op.get('offset_samples'))
                        if not 0 < offset < end-start:
                            raise ValueError('Split must be inside clip')
                        right = deepcopy(clip)
                        right.set('id', str(next_id)); next_id += 1
                        right.set('startPoint', str(start+offset)); right.set('sourceInPoint', str(si+offset))
                        clip.set('endPoint', str(start+offset)); clip.set('sourceOutPoint', str(si+offset))
                        track.append(right)
                        pieces = [clip, right]
                    else:
                        begin, finish = integer(op.get('source_in')), integer(op.get('source_out'))
                        if not si <= begin < finish <= so:
                            raise ValueError('Trim must stay within current source range')
                        clip.set('sourceInPoint', str(begin)); clip.set('sourceOutPoint', str(finish))
                        clip.set('endPoint', str(start+finish-begin)); pieces = [clip]
                    for piece in pieces:
                        lo, hi = int(piece.get('sourceInPoint')), int(piece.get('sourceOutPoint'))
                        for tag, boundary in (('fadeIn', lo), ('fadeOut', hi)):
                            fade = piece.find(tag)
                            if fade is not None and (int(fade.get('startPoint')) < lo or int(fade.get('endPoint')) > hi):
                                fade.set('startPoint', str(boundary)); fade.set('endPoint', str(boundary))
                elif action == 'fade':
                    edge, length = op.get('edge'), integer(op.get('length_samples'))
                    if edge not in ('in', 'out') or length > so-si:
                        raise ValueError('Invalid fade')
                    fade = clip.find('fadeIn' if edge == 'in' else 'fadeOut')
                    if fade is None:
                        raise ValueError('Native fade template unavailable')
                    fade.set('startPoint', str(si if edge == 'in' else so-length))
                    fade.set('endPoint', str(si+length if edge == 'in' else so))
            changes.append(dict(op))
        return cls._production_publish(src, destination, root, before, confirm, changes)

    @classmethod
    def relink_production_session(cls, source, destination, replacements, *, confirm=False):
        """Explicit file-ID mapping, with optional expected SHA256; no fuzzy relinking."""
        src, tree, root, tracks = cls._native_tree(source)
        before = hashlib.sha256(src.read_bytes()).hexdigest()
        if not isinstance(replacements, dict) or not replacements:
            raise ValueError('Nonempty media file-ID mapping required')
        files = root.findall('./files/file') + root.findall('./session/files/file')
        changes = []
        for fid, entry in replacements.items():
            nodes = [f for f in files if f.get('id') == str(fid)]
            if len(nodes) != 1 or not isinstance(entry, dict):
                raise ValueError('Unique media file ID required')
            path = Path(entry['path']).resolve()
            if not path.is_file():
                raise FileNotFoundError(path)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if entry.get('sha256', digest) != digest:
                raise ValueError('Replacement media hash mismatch')
            node = nodes[0]
            changes.append(dict(file_id=str(fid), old_path=node.get('absolutePath'), path=str(path), sha256=digest))
            node.set('absolutePath', str(path))
            # Avoid retaining a stale relative path pointing at different media.
            node.attrib.pop('relativePath', None)
        return cls._production_publish(src, destination, root, before, confirm, changes)

    @classmethod
    def session_overlap_report(cls, source):
        src, tree, root, tracks = cls._native_tree(source)
        overlaps = []
        for track in tracks:
            clips = sorted(track.findall('audioClip'), key=lambda c: int(c.get('startPoint')))
            for i, left in enumerate(clips):
                for right in clips[i+1:]:
                    start = int(right.get('startPoint')); end = min(int(left.get('endPoint')), int(right.get('endPoint')))
                    if start >= int(left.get('endPoint')): break
                    if end > start:
                        overlaps.append(dict(track_id=track.get('id'), left=left.get('id'), right=right.get('id'), start=start, end=end))
        return dict(source=str(src), overlaps=overlaps, native_reopen_verified=False)

    @classmethod
    def production_component_inventory(cls, source):
        """Inspect serialized components without asserting plugin availability."""
        src, tree, root, tracks = cls._native_tree(source)
        components = []
        for track in root.findall('.//audioTrack') + root.findall('.//busTrack') + root.findall('.//masterTrack'):
            for component in track.findall('./trackAudioParameters/component'):
                components.append(dict(track_id=track.get('id'), attributes=dict(component.attrib),
                    parameters=[dict(p.attrib) for p in component.findall('parameter')]))
        return dict(source=str(src), components=components, native_plugins_verified=False)

    @classmethod
    def patch_production_component(cls, source, destination, *, track_id, component_id,
                                   powered=None, normalized_parameters=None, confirm=False):
        """Update existing serialized component by ID; never invent Rack/Send schemas.

        Parameter values here are explicitly normalized 0..1, not Hz/dB.
        Caller must supply a real component/parameter from inventory.
        """
        src, tree, root, tracks = cls._native_tree(source)
        before = hashlib.sha256(src.read_bytes()).hexdigest()
        nodes = [t for t in root.findall('.//audioTrack') + root.findall('.//busTrack') + root.findall('.//masterTrack') if t.get('id') == str(track_id)]
        if len(nodes) != 1:
            raise ValueError('Unique track ID required')
        components = [c for c in nodes[0].findall('./trackAudioParameters/component') if c.get('id') == component_id]
        if len(components) != 1:
            raise ValueError('Unique existing component ID required')
        component = components[0]
        if powered is not None:
            if type(powered) is not bool or 'powered' not in component.attrib:
                raise ValueError('Existing powered flag and Boolean required')
            component.set('powered', 'true' if powered else 'false')
        if normalized_parameters is not None:
            if not isinstance(normalized_parameters, dict):
                raise ValueError('Parameter name mapping required')
            for name, value in normalized_parameters.items():
                if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
                    raise ValueError('Normalized parameter must be finite, 0..1')
                matches = [p for p in component.findall('parameter') if p.get('name') == name]
                if len(matches) != 1:
                    raise ValueError('Unique existing parameter name required')
                matches[0].set('parameterValue', str(value))
        if powered is None and not normalized_parameters:
            raise ValueError('At least one component change required')
        return cls._production_publish(src, destination, root, before, confirm,
            [dict(track_id=str(track_id), component_id=component_id, powered=powered, parameters=normalized_parameters)])
