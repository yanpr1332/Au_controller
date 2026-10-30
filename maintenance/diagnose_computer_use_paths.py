"""Read-only command probes using the installed Codex sandbox launcher."""
import json
import subprocess
from pathlib import Path

ROLLOUT = Path(r'C:\Users\LENOVO\.codex\sessions\2026\10\30\rollout-2026-10-30T12-23-47-01a18b0c-b0b4-79e2-9747-5163cf06c499.jsonl')
EXE = r'C:\Users\LENOVO\AppData\Local\OpenAI\Codex\bin\22cfb1d302613eae\codex.exe'

def main():
    context = None
    for line in ROLLOUT.read_text(encoding='utf8').splitlines():
        row = json.loads(line)
        if row.get('type') == 'turn_context':
            context = row['payload']
    profile = context['permission_profile']
    entries = profile['file_system']['entries']
    probes = {
        'without_drive_root': [e for e in entries if not (e['path'].get('path') == 'D:\\' and e['access']=='write')],
        'without_drive_and_slash_tmp': [e for e in entries if not (e['path'].get('path') == 'D:\\' and e['access']=='write') and e['path'].get('value',{}).get('kind')!='slash_tmp'],
    }
    for label, selected in probes.items():
        candidate = json.loads(json.dumps(profile))
        candidate['file_system']['entries'] = selected
        state = {'permissionProfile': candidate, 'sandboxCwd': 'file:///D:/computer/Adobe/Audition'}
        result = subprocess.run([EXE, 'sandbox', '--sandbox-state-json', json.dumps(state), 'cmd.exe', '/c', 'ver'], capture_output=True, timeout=45)
        print(json.dumps({'probe':label, 'exit_code':result.returncode, 'stdout':result.stdout.decode('utf8','replace'), 'stderr':result.stderr.decode('utf8','replace')},ensure_ascii=True),flush=True)
    for path in ['D:\\', 'D:\\\\', r'\\?\C:\Users\LENOVO\AppData\Local\OpenAI\Codex\runtimes\cua_node\5c41f77a7900391c\bin']:
        toml = 'permissions.path_probe={filesystem={\":root\"=\"read\",' + json.dumps(path) + '=\"read\"},network={enabled=false}}'
        result = subprocess.run([EXE,'sandbox','-c','default_permissions="path_probe"','-c',toml,'cmd.exe','/c','ver'],capture_output=True,timeout=45)
        print(json.dumps({'path':path,'exit_code':result.returncode,'stderr':result.stderr.decode('utf8','replace')},ensure_ascii=True),flush=True)
    selected = probes['without_drive_root']
    mapping = {}
    for entry in selected:
        path = entry['path']
        key = path.get('path') or ':' + path['value']['kind']
        mapping[key] = entry['access']
    toml = 'permissions.path_probe={filesystem={' + ','.join(json.dumps(k)+'='+json.dumps(v) for k,v in mapping.items()) + '},network={enabled=false}}'
    result = subprocess.run([EXE,'sandbox','-c','default_permissions="path_probe"','-c',toml,'cmd.exe','/c','ver'],capture_output=True,timeout=45)
    print(json.dumps({'probe':'node_config_format_without_drive_root','exit_code':result.returncode,'stderr':result.stderr.decode('utf8','replace')},ensure_ascii=True),flush=True)

if __name__ == '__main__':
    main()
