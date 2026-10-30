"""Close only currently open Audition QA files under the project tests tree."""
from __future__ import annotations
import sys,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R))
from audition_controller import AuditionController as C
root=(R/"tests").resolve().as_posix().lower()
q=json.dumps(root)
body=('var allowed='+q+';var files=[];\n'
      'for(var i=0;i<app.documents.length;i++){\n'
      ' var p=String(app.documents[i].path).replace(/\\\\/g,"/").toLowerCase();\n'
      ' files.push(p);out("OPEN_"+i,p);\n'
      ' if(p.indexOf(allowed+"/")!=0)throw "Non-QA document is open: "+p;\n'
      '}\n'
      'for(var j=app.documents.length-1;j>=0;j--){\n'
      ' try{app.documents[j].closeDocument();}catch(e){out("CLOSE_ERROR_"+j,e);}\n'
      '}out("AFTER",app.documents.length);\n')
if __name__=="__main__":
    print(json.dumps(C()._run_jsx(body,"qa_only_close",timeout=35),ensure_ascii=False),flush=True)
