"""Stage our built SDK plugin and restart only a clean QA-only Audition host."""
from pathlib import Path
import sys
import json
import time
import shutil
import ctypes
import ctypes.wintypes as wt
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from audition_controller import AuditionController as C

if __name__ == '__main__':
    c=C()
    binary=ROOT/'sdk/session_bridge/build/ControllerSessionBridge.ases'
    target=c.audition_exe.parent/'PlugIns/Session/ControllerSessionBridge.ases'
    if not binary.is_file(): raise RuntimeError('Build the SDK plugin first')
    # Preflight *every* document before closing even one owned QA document.
    print(c._run_jsx('''
for(var i=0;i<app.documents.length;i++){
var d=app.documents[i],p=String(d.path).replace(/\\\\/g,"/").toLowerCase();
if(p.indexOf("d:/computer/adobe/audition/au_controller/tests/")!=0||d.dirty)throw "Non-QA or unsaved document present; no restart";
}out("SAFE",true);
''','phase11_restart_preflight',30),flush=True)
    for i in range(30):
        response=c._run_jsx('''
if(app.documents.length){var d=app.documents[app.documents.length-1],p=String(d.path).replace(/\\\\/g,"/").toLowerCase();
if(p.indexOf("d:/computer/adobe/audition/au_controller/tests/")!=0||d.dirty)throw "Unexpected document; stop";
d.activate();out("CLOSE",d.closeDocument());}else out("EMPTY",true);
''','phase11_restart_close',30)
        if response.get('EMPTY')=='true':break
    else:raise RuntimeError('Owned QA documents did not close')
    # Keep a handle to the exact original process; never assume a fixed delay
    # means it exited, and never invoke status() as an implicit relaunch.
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wt.DWORD,wt.BOOL,wt.DWORD]
    kernel.OpenProcess.restype=wt.HANDLE
    kernel.WaitForSingleObject.argtypes=[wt.HANDLE,wt.DWORD]
    kernel.CloseHandle.argtypes=[wt.HANDLE]
    handle=kernel.OpenProcess(0x00100000,False,c._audition_pid())
    if not handle: raise ctypes.WinError(ctypes.get_last_error())
    try:
        print(c._run_jsx('if(app.documents.length)throw "Documents present";out("QUIT",true);app.quit();','phase11_clean_restart',20),flush=True)
        if kernel.WaitForSingleObject(handle,30000)!=0:
            raise RuntimeError('Original Audition process did not exit; no replacement launched')
    finally:
        kernel.CloseHandle(handle)
    if target.exists() and c._hash_file(target)!=c._hash_file(binary):
        if b'E316D202-94AD-4ED3-9B47-9EA00EB8B645' not in target.read_bytes():
            raise RuntimeError('Existing plugin ownership cannot be verified; preserved')
        backups=ROOT/'sdk/session_bridge/previous_builds';backups.mkdir(exist_ok=True)
        backup=backups/(c._hash_file(target)+'.ases')
        if not backup.exists(): shutil.copy2(target,backup)
        pending=target.with_suffix('.ases.pending')
        if pending.exists(): raise FileExistsError(pending)
        shutil.copy2(binary,pending)
        pending.replace(target)
    elif not target.exists():
        with target.open('xb') as out,binary.open('rb') as source:shutil.copyfileobj(source,out)
    print('PLUGIN_STAGED_AND_HOST_EXITED: launch Audition once and finish startup before requesting status',flush=True)
    print('PLUGIN',target,'SHA256',c._hash_file(target),flush=True)
