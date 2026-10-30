"""Close saved QA documents, then independently verify the host is empty."""
from pathlib import Path
import sys,json
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from audition_controller import AuditionController as C

if __name__=='__main__':
    c=C();evidence={'before':c.status(),'closed':[]}
    preflight=c._run_jsx('''
for(var i=0;i<app.documents.length;i++){var d=app.documents[i],p=String(d.path).replace(/\\\\/g,"/").toLowerCase();
if((p.indexOf("d:/computer/adobe/audition/tests/")!=0&&p.indexOf("d:/computer/adobe/audition/_runtime/")!=0)||d.dirty)throw "Non-QA or unsaved document; preserve all documents";
}out("SAFE",true);
''','phase11_final_preflight',30)
    for attempt in range(100):
        result=c._run_jsx('''
var selected=null;
for(var i=0;i<app.documents.length;i++){var d=app.documents[i],p=String(d.path).replace(/\\\\/g,"/").toLowerCase();
if((p.indexOf("d:/computer/adobe/audition/tests/")!=0&&p.indexOf("d:/computer/adobe/audition/_runtime/")!=0)||d.dirty)throw "Unexpected document; stop";
if(!selected||d.reflect.name=="MultitrackDocument")selected=d;
}
if(selected){out("PATH",selected.path);selected.activate();out("CLOSED",selected.closeDocument());}else out("EMPTY",true);
''','phase11_final_close',30)
        evidence['closed'].append(result)
        if result.get('EMPTY')=='true':break
    evidence['after']=c.status();evidence['passed']=evidence['after'].get('DOCUMENTS')=='0'
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    receipt=ROOT/'tests/receipts'/('phase11_cleanup_'+stamp+'.json');receipt.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')
    print('CLEAN_HOST',evidence['passed'],'RECEIPT',receipt)
