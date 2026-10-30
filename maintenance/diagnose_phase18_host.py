"""Read-only host document diagnostics; no closing or project mutation."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from audition_controller import AuditionController

if __name__=='__main__':
    body='''
var rows=[];
for(var i=0;i<app.documents.length;i++){
 var d=app.documents[i];rows.push({path:String(d.path),dirty:Boolean(d.dirty),name:String(d.displayName)});
 out("DOC_"+i+"_PATH",d.path);out("DOC_"+i+"_DIRTY",d.dirty);
}
out("DOCUMENTS",rows.length);
'''
    print(json.dumps(AuditionController()._run_jsx(body,'phase18_host_diag',30),indent=2))
