"""Read-only, PID-scoped Windows UIA diagnostics; no GUI actions."""
from pathlib import Path
import json
import math
import subprocess
import sys
from .completed_diagnostics import AuditionCompletedDiagnostics


class AuditionUIAInspection(AuditionCompletedDiagnostics):
    def inspect_audition_controls(self,*,title_contains='',max_controls=200,max_depth=5,timeout=15):
        if not isinstance(title_contains,str) or len(title_contains)>128 or any(x in title_contains for x in '\r\n\0'):
            raise ValueError('Invalid window title filter')
        if type(max_controls) is not int or not 1<=max_controls<=500 or type(max_depth) is not int or not 0<=max_depth<=8:
            raise ValueError('Invalid UIA traversal limits')
        if type(timeout) not in (int,float) or not math.isfinite(timeout) or not 1<=timeout<=30:
            raise ValueError('Invalid UIA timeout')
        root=Path(__file__).resolve().parents[1]
        worker=root/'controller_modules'/'uia_worker.py'
        if not (root/'_vendor'/'gui'/'pywinauto').is_dir():
            raise RuntimeError('Install pywinauto in the project-local _vendor/gui directory')
        pid=self._audition_pid()
        try:
            process=subprocess.run([sys.executable,'-B',str(worker),str(pid),str(max_controls),str(max_depth),title_contains],
                capture_output=True,text=True,encoding='utf8',errors='replace',timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError('Read-only UIA inspection timed out; Au was not terminated') from exc
        if process.returncode:
            raise RuntimeError('Read-only UIA inspection failed: '+process.stderr[-1200:])
        result=json.loads(process.stdout)
        if result.get('pid')!=pid or result.get('actions_performed') is not False or not isinstance(result.get('windows'),list):
            raise RuntimeError('Unexpected UIA inspection result')
        result['audition_gui_workflow_verified']=False
        return result
