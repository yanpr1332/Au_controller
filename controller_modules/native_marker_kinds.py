"""Native Audition 26 wave marker class/range discovery confined to QA assets."""
from __future__ import annotations
from pathlib import Path
import hashlib,json

class AuditionMarkerKindsQA:
    def native_wave_markers_qa(self,source,output,*,confirm=False):
        from audition_controller import ROOT
        src=Path(source).resolve()
        dst=Path(output).resolve()
        self._native_test_paths(src,dst)
        if not confirm:
            return {"dry_run":True,"source":str(src),"output":str(dst)}
        before=hashlib.sha256(src.read_bytes()).hexdigest()
        sq=json.dumps(src.as_posix());oq=json.dumps(dst.as_posix())
        body=(
         'if(app.documents.length!=0)throw "QA test only, close other docs first";\n'
         'var doc=app.openDocument(new DocumentOpenParameter('+sq+'));\n'
         'try{\n'
         ' if(!doc||doc.reflect.name!="WaveDocument")throw "QA WAV did not open";\n'
         ' var plan=[["point",0,0,"Cue"],["range",24000,12000,"Cue"],\n'
         '           ["subclip",48000,12000,"Subclip"],["cd",72000,12000,"CD Track"]];\n'
         ' for(var i=0;i<plan.length;i++){\n'
         '  try{var x=plan[i];var value=doc.addMarker(x[1],x[2],"QA "+x[0],x[3],"Controlled marker");\n'
         '      out("RESULT_"+x[0],value);}catch(err){out("ERROR_"+plan[i][0],err);}\n'
         ' }\n'
         ' out("NATIVE_MARKERS",doc.markers.length);\n'
         ' for(var j=0;j<doc.markers.length;j++){\n'
         '  var m=doc.markers[j];out("MARKER_"+j+"_TYPE",m.type);out("MARKER_"+j+"_NAME",m.name);\n'
         '  out("MARKER_"+j+"_START",m.start);out("MARKER_"+j+"_DURATION",m.duration);\n'
         ' }\n'
         ' out("SAVE",doc.saveAs('+oq+',true));\n'
         ' $.sleep(300);out("EXISTS",new File('+oq+').exists);\n'
         '}finally{try{doc.closeDocument();}catch(e){out("CLOSE_WARNING",e);}}\n')
        response=self._run_jsx(body,"qa_marker_kinds",timeout=60)
        cleaned=self._qa_close_documents()
        if response.get("EXISTS")!="true" or not dst.is_file():
            raise RuntimeError("Native marker WAV save did not complete")
        if hashlib.sha256(src.read_bytes()).hexdigest()!=before:
            raise RuntimeError("Marker source changed")
        # Reopen to verify persistence in the Adobe host, not merely the WAV chunk.
        body2=('if(app.documents.length!=0)throw "QA document busy";\n'
               'var doc=app.openDocument(new DocumentOpenParameter('+oq+'));\n'
               'try{if(!doc||doc.reflect.name!="WaveDocument")throw "Output not WaveDocument";\n'
               'out("REOPEN_MARKERS",doc.markers.length);\n'
               'for(var i=0;i<doc.markers.length;i++){\n'
               ' var m=doc.markers[i];out("REOPEN_"+i+"_TYPE",m.type);\n'
               ' out("REOPEN_"+i+"_NAME",m.name);out("REOPEN_"+i+"_DURATION",m.duration);\n'
               '}}finally{try{doc.closeDocument();}catch(e){out("CLOSE_WARNING",e);}}\n')
        reopened=self._run_jsx(body2,"qa_marker_reopen",timeout=45)
        after=self._qa_close_documents()
        return {"source":str(src),"output":str(dst),
                "source_unchanged":True,"source_sha256":before,
                "output_sha256":hashlib.sha256(dst.read_bytes()).hexdigest(),
                "first_save":response,"reopen":reopened,
                "after_close":after,"native_marker_persistence":True}
