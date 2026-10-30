"""Archive stale startup recovery pointers without deleting recovery payloads."""
from pathlib import Path
import os
import sys
import csv
import json
import hashlib
import shutil
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda:handle.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

if __name__=='__main__':
    rows=list(csv.reader(subprocess.run(['tasklist','/FI','IMAGENAME eq Adobe Audition.exe','/FO','CSV','/NH'],capture_output=True,text=True,errors='replace',check=True).stdout.splitlines()))
    if any(row and row[0].lower()=='adobe audition.exe' for row in rows):
        raise RuntimeError('Close Audition normally before archiving startup recovery')
    base=(Path(os.environ['APPDATA'])/'Adobe/Audition/26.0').resolve()
    pointers=[base/name for name in ('Audition26Recovery.xml','Audition26Recovery1.xml') if (base/name).is_file()]
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    archive=ROOT/'backups'/('recovery_archive_'+stamp)
    manifest=dict(created_utc=stamp,source=str(base),pointers=[],copied_files=[],missing_references=[],original_payloads_retained=True)
    if '--confirm' not in sys.argv:
        print(json.dumps(dict(dry_run=True,pointers=[str(p) for p in pointers],archive=str(archive)),ensure_ascii=False));sys.exit(0)
    archive.mkdir()
    folders=set();references=set()
    for pointer in pointers:
        entry=dict(name=pointer.name,sha256=digest(pointer));manifest['pointers'].append(entry)
        shutil.copy2(pointer,archive/pointer.name)
        for node in ET.parse(pointer).iter('ustring'):
            folder=Path(node.text or '').resolve()
            if folder.parent!=base:raise ValueError('Unexpected recovery directory; pointers retained')
            if folder.is_dir():folders.add(folder)
            else:manifest['missing_references'].append(str(folder))
    for folder in folders:
        for path in folder.rglob('*'):
            if not path.is_file():continue
            if folder not in path.resolve().parents:raise ValueError('Recovery symlink escaped folder')
            target=archive/'payloads'/folder.name/path.relative_to(folder)
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
            if digest(path)!=digest(target):raise RuntimeError('Recovery payload backup mismatch')
            manifest['copied_files'].append(dict(source=str(path),backup=str(target.relative_to(archive)),sha256=digest(target)))
            if path.suffix.lower()=='.xml':
                try:
                    for node in ET.parse(path).iter('ustring'):
                        text=node.text or ''
                        if len(text)>3 and text[1:3]==':\\':references.add(Path(text))
                except ET.ParseError:pass
    for index,path in enumerate(sorted(references)):
        if path.is_file():
            target=archive/'referenced_files'/(str(index)+'_'+path.name)
            target.parent.mkdir(exist_ok=True);shutil.copy2(path,target)
            if digest(path)!=digest(target):raise RuntimeError('Referenced recovery backup mismatch')
            manifest['copied_files'].append(dict(source=str(path),backup=str(target.relative_to(archive)),sha256=digest(target)))
        else:manifest['missing_references'].append(str(path))
    manifest_path=archive/'manifest.json'
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    # Remove only the two exact pointer files, after backup and hash verification.
    # Original recovery folders, raw audio and user projects are never removed.
    for pointer in pointers:
        if pointer.resolve().parent!=base or pointer.name not in ('Audition26Recovery.xml','Audition26Recovery1.xml'):
            raise ValueError('Unexpected pointer target')
        record=next(row for row in manifest['pointers'] if row['name']==pointer.name)
        if digest(pointer)!=record['sha256'] or digest(archive/pointer.name)!=record['sha256']:
            raise RuntimeError('Pointer changed; do not remove')
    for pointer in pointers:pointer.unlink()
    print(json.dumps(dict(archive=str(archive),pointers_archived=len(pointers),payload_files_copied=len(manifest['copied_files']),original_payloads_retained=True),ensure_ascii=False,indent=2))
