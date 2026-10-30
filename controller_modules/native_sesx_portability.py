"""QA-only self-contained native Audition SESX package with copied media and relink.

Creates NEW directory with sesx, media, manifest. Real Audition reopen required
before caller labels package as native verified. Never alters original session or media.
"""
from __future__ import annotations
import hashlib,json,re,shutil,tempfile
from pathlib import Path
from lxml import etree as ET

class AuditionSessionPortability:
    @staticmethod
    def _sha(path):
        h=hashlib.sha256()
        with Path(path).open('rb') as stream:
            for chunk in iter(lambda:stream.read(2**20),b''):h.update(chunk)
        return h.hexdigest()

    @classmethod
    def create_qa_session_package(cls,source,destination,*,confirm=False):
        from audition_controller import ROOT
        qa=(ROOT/'tests').resolve()
        src=Path(source).resolve()
        output=Path(destination).resolve()
        if qa not in src.parents or src.suffix.lower()!='.sesx' or not src.name.startswith('ACCEPT_AU_'):
            raise PermissionError('QA-only Audition source session required')
        if qa not in output.parents or output.exists() or not output.parent.is_dir():
            raise PermissionError('Output must be a new directory under QA tests')
        if not output.name.startswith('ACCEPT_AU_'):
            raise ValueError('Package directory must begin ACCEPT_AU_')
        tree=ET.parse(str(src));root=tree.getroot()
        if root.tag!='sesx':raise ValueError('Invalid Audition SESX document')
        files=root.findall('./files/file')
        if not 1<=len(files)<=32:raise ValueError('1..32 native SESX media references required')
        records=[];seen=set()
        for f in files:
            media_path=f.get('absolutePath')
            if not media_path:raise ValueError('Missing native absolutePath')
            p=Path(media_path).resolve()
            if qa not in p.parents or not p.is_file() or p.suffix.lower() not in ('.wav','.mp3','.flac'):
                raise PermissionError('QA-only existing audio media required')
            fid=f.get('id','')
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,20}',fid) or fid in seen:
                raise ValueError('Invalid/duplicate native media file ID')
            seen.add(fid)
            target_name=fid+'_'+p.name
            records.append({'id':fid,'source':str(p),'name':target_name,
                            'source_sha256':cls._sha(p),'source_size':p.stat().st_size})
        if not confirm:return {'dry_run':True,'media_count':len(records),
                               'output':str(output),'source':str(src)}
        original=cls._sha(src)
        with tempfile.TemporaryDirectory(prefix='.au_pack_',dir=output.parent) as temp:
            staging=Path(temp)/output.name
            staging.mkdir()
            media=staging/'media';media.mkdir()
            for node,record in zip(files,records):
                dest=media/record['name']
                shutil.copy2(record['source'],dest)
                if cls._sha(dest)!=record['source_sha256']:
                    raise RuntimeError('Media copy checksum mismatch')
                node.set('absolutePath',str((output/'media'/record['name']).resolve()))
                node.set('relativePath','media/'+record['name'])
            sesx=staging/(output.name+'.sesx')
            payload=ET.tostring(root,xml_declaration=True,encoding='utf-8')
            ET.fromstring(payload)
            sesx.write_bytes(payload)
            manifest={'session':sesx.name,'source_session':str(src),
                      'original_sha256':original,
                      'media':records,'session_sha256':cls._sha(sesx),
                      'native_reopen_verified':False}
            (staging/'MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
            if cls._sha(src)!=original:raise RuntimeError('Source modified unexpectedly')
            staging.rename(output)
        return {'package_dir':str(output),'session':str(output/(output.name+'.sesx')),
                'media_count':len(records),'source_intact':True,
                'manifest':str(output/'MANIFEST.json'),
                'native_reopen_verified':False}

    @classmethod
    def verify_qa_session_package(cls,directory):
        package=Path(directory).resolve()
        manifest=json.loads((package/'MANIFEST.json').read_text(encoding='utf8'))
        session=package/manifest['session']
        if not session.is_file() or cls._sha(session)!=manifest['session_sha256']:
            raise ValueError('Packaged session checksum mismatch')
        r=ET.parse(str(session)).getroot()
        files={x.get('id'):x for x in r.findall('./files/file')}
        checks=[]
        for entry in manifest['media']:
            name=entry['name']
            dest=package/'media'/name
            if not dest.is_file() or cls._sha(dest)!=entry['source_sha256']:
                checks.append(False);continue
            f=files.get(entry['id'])
            checks.append(bool(f is not None and f.get('relativePath')=='media/'+name and
                               Path(f.get('absolutePath','')).resolve()==dest))
        return {'package':str(package),'session':str(session),
                'file_count':len(checks),'file_checks':checks,'all_present':bool(checks) and all(checks),
                'native_reopen_verified':bool(manifest.get('native_reopen_verified'))}
