"""Read-only DOM snapshot of the GUI-imported QA OMF."""
import sys,json
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from audition_controller import AuditionController

if __name__=='__main__':
    result=AuditionController()._run_jsx('''
for(var n=0;n<app.documents.length;n++){
 var d=app.documents[n];if(d.reflect.name!="MultitrackDocument")continue;
 out("DOC_"+n+"_PATH",d.path);
 var tracks=d.audioTracks.audioClipTracks;out("DOC_"+n+"_TRACKS",tracks.length);
 for(var i=0;i<tracks.length;i++){
  out("DOC_"+n+"_TRACK_"+i+"_NAME",tracks[i].name);
  out("DOC_"+n+"_TRACK_"+i+"_CLIPS",tracks[i].audioClips.length);
  for(var j=0;j<tracks[i].audioClips.length;j++){
   var clip=tracks[i].audioClips[j];
   var prefix="DOC_"+n+"_TRACK_"+i+"_CLIP_"+j;
   var props=clip.reflect.properties;
   for(var k=0;k<props.length;k++){
    var key=props[k].name;
    if(/start|end|duration|length|name/i.test(key)){try{out(prefix+"_"+key,clip[key]);}catch(e){}}
   }
  }
 }
}''','omf_roundtrip_snapshot',30)
    target=ROOT/'tests/receipts'/('phase16_omf_snapshot_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'.json')
    with target.open('x',encoding='utf8') as f:json.dump(result,f,indent=2,ensure_ascii=False)
    print(json.dumps(result,indent=2,ensure_ascii=False));print(target)
