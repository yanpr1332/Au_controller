"""Read-only Audition UIA snapshot worker; invoked in a bounded subprocess."""
from pathlib import Path
import json
import os
import sys


def main():
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    pid,limit,depth,needle=int(sys.argv[1]),int(sys.argv[2]),int(sys.argv[3]),sys.argv[4]
    root=Path(__file__).resolve().parents[1]
    vendor=root/'_vendor'/'gui'
    if not (vendor/'pywinauto').is_dir():raise RuntimeError('Project-local pywinauto is not installed')
    sys.path[:0]=[str(vendor),str(vendor/'win32'),str(vendor/'win32'/'lib'),str(vendor/'pythonwin')]
    dll_handle=os.add_dll_directory(str(vendor/'pywin32_system32'))
    from pywinauto import Desktop
    windows=Desktop(backend='uia').windows(process=pid,visible_only=True)
    result=[];count=0;truncated=False
    def visit(control,level):
        nonlocal count,truncated
        if count>=limit:
            truncated=True;return None
        info=control.element_info
        if info.process_id!=pid:return None
        rect=info.rectangle
        node=dict(name=str(info.name or '')[:256],control_type=str(info.control_type or ''),
                  automation_id=str(info.automation_id or '')[:256],
                  bounds=dict(left=rect.left,top=rect.top,right=rect.right,bottom=rect.bottom),children=[])
        count+=1
        if level<depth:
            for child in control.children():
                if count>=limit:truncated=True;break
                item=visit(child,level+1)
                if item is not None:node['children'].append(item)
        return node
    for window in windows:
        if needle and needle.casefold() not in str(window.element_info.name or '').casefold():continue
        item=visit(window,0)
        if item is not None:result.append(item)
        if count>=limit:truncated=True;break
    print(json.dumps(dict(pid=pid,backend='Windows UI Automation',windows=result,control_count=count,truncated=truncated,
                          screenshots_captured=False,actions_performed=False),ensure_ascii=False))
    # Keep the DLL search handle alive until imports and UIA queries complete.
    dll_handle.close()


if __name__=='__main__':main()
