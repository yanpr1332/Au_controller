"""Offline, backed-up removal of the drive-root grant from this chat only."""
import datetime
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

THREAD = '01a18b0c-b0b4-79e2-9747-5163cf06c499'
BASE = Path(r'C:\Users\LENOVO\.codex')
RECEIPT = Path(r'D:\computer\Adobe\Audition\_runtime\session_root_repair.json')

def narrow(profile):
    entries = profile.get('file_system', {}).get('entries', profile.get('entries', []))
    old = len(entries)
    entries[:] = [e for e in entries if not (e.get('access') == 'write' and e.get('path', {}).get('path', '').rstrip('\\/').lower() == 'd:')]
    return old - len(entries)

def main():
    stamp = datetime.datetime.now().strftime('%Y%m%dT%H%M%S')
    backup = BASE / ('au-session-root-backup-' + stamp)
    backup.mkdir()
    conn = sqlite3.connect(BASE / 'state_5.sqlite', timeout=15)
    row = conn.execute('SELECT rollout_path,sandbox_policy FROM threads WHERE id=?', (THREAD,)).fetchone()
    if not row:
        raise RuntimeError('Target thread missing')
    rollout = Path(row[0])
    shutil.copy2(rollout, backup / rollout.name)
    (backup / 'sandbox_policy.json').write_text(row[1], encoding='utf8')
    lines = rollout.read_text(encoding='utf8').splitlines(keepends=True)
    runtime_roots_removed = 0
    for meta_index, line in enumerate(lines):
        meta = json.loads(line)
        if meta.get('type') == 'session_meta' and 'runtime_workspace_roots' in meta.get('payload', {}):
            roots = meta['payload']['runtime_workspace_roots']
            clean = [p for p in roots if p.rstrip('\\/').lower() != 'd:']
            runtime_roots_removed += len(roots) - len(clean)
            meta['payload']['runtime_workspace_roots'] = clean
            lines[meta_index] = json.dumps(meta, ensure_ascii=False, separators=(',', ':')) + '\n'
    index = next(i for i in range(len(lines)-1, -1, -1) if json.loads(lines[i]).get('type') == 'turn_context')
    context = json.loads(lines[index])
    payload = context['payload']
    changes = {}
    for key in ('permission_profile', 'file_system_sandbox_policy'):
        if key in payload:
            changes[key] = narrow(payload[key])
    policy = payload.get('sandbox_policy', {})
    if 'writable_roots' in policy:
        policy['writable_roots'] = [p for p in policy['writable_roots'] if p.rstrip('\\/').lower() != 'd:']
    lines[index] = json.dumps(context, ensure_ascii=False, separators=(',', ':')) + '\n'
    tmp = rollout.with_suffix('.au-repair.tmp')
    tmp.write_text(''.join(lines), encoding='utf8', newline='')
    saved = json.loads(row[1])
    db_removed = narrow(saved)
    conn.execute('BEGIN IMMEDIATE')
    try:
        conn.execute('UPDATE threads SET sandbox_policy=? WHERE id=? AND sandbox_policy=?', (json.dumps(saved, separators=(',', ':')), THREAD, row[1]))
        if conn.total_changes != 1:
            raise RuntimeError('Thread changed during repair')
        os.replace(tmp, rollout)
        conn.commit()
    except Exception:
        conn.rollback()
        shutil.copy2(backup / rollout.name, rollout)
        raise
    finally:
        conn.close()
    RECEIPT.write_text(json.dumps({'status':'applied','thread_id':THREAD,'backup':str(backup),'runtime_roots_removed':runtime_roots_removed,'context_changes':changes,'db_removed':db_removed,'timestamp':stamp}, indent=2),encoding='utf8')

if __name__ == '__main__':
    if '--self-test' in sys.argv:
        with tempfile.TemporaryDirectory(dir=r'D:\computer\Adobe\Audition\_runtime') as folder:
            BASE = Path(folder)
            RECEIPT = BASE / 'receipt.json'
            entry = lambda p: {'path':{'type':'path','path':p},'access':'write'}
            profile = {'type':'managed','file_system':{'type':'restricted','entries':[entry('D:\\'),entry(r'D:\computer\Adobe\Audition')]},'network':'restricted'}
            context = {'type':'turn_context','payload':{'permission_profile':profile,'sandbox_policy':{'writable_roots':['D:\\',r'D:\computer\Adobe\Audition']}}}
            rollout = BASE / 'fixture.jsonl'
            sentinel = json.dumps({'type':'response_item','payload':{'content':'preserve this message'}})+'\n'
            meta = {'type':'session_meta','payload':{'runtime_workspace_roots':['D:\\',r'D:\computer\Adobe\Audition']}}
            rollout.write_text(json.dumps(meta)+'\n'+sentinel+json.dumps(context)+'\n',encoding='utf8')
            c = sqlite3.connect(BASE/'state_5.sqlite')
            c.execute('CREATE TABLE threads(id TEXT PRIMARY KEY,rollout_path TEXT,sandbox_policy TEXT)')
            c.execute('INSERT INTO threads VALUES(?,?,?)',(THREAD,str(rollout),json.dumps(profile)))
            c.commit(); c.close()
            main()
            assert rollout.read_text(encoding='utf8').splitlines(keepends=True)[1] == sentinel
            assert json.loads(rollout.read_text(encoding='utf8').splitlines()[0])['payload']['runtime_workspace_roots'] == [r'D:\computer\Adobe\Audition']
            updated = json.loads(rollout.read_text(encoding='utf8').splitlines()[-1])
            assert len(updated['payload']['permission_profile']['file_system']['entries']) == 1
            assert updated['payload']['sandbox_policy']['writable_roots'] == [r'D:\computer\Adobe\Audition']
            c = sqlite3.connect(BASE/'state_5.sqlite')
            assert len(json.loads(c.execute('SELECT sandbox_policy FROM threads').fetchone()[0])['file_system']['entries']) == 1
            c.close()
            assert json.loads(RECEIPT.read_text())['status'] == 'applied'
            print('OFFLINE_SESSION_REPAIR_TEST_PASSED')
        sys.exit(0)
    try:
        main()
    except Exception as error:
        RECEIPT.write_text(json.dumps({'status':'failed','error':str(error)},indent=2),encoding='utf8')
        raise
