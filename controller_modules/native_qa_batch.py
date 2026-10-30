"""Audition 26 live QA-only track-state and multi-file import probes.

These commands mutate only a new ACCEPT_AU_ test-session copy, never a user
project. The controlled test closes its own documents and never starts Record.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import json


class AuditionNativeQABatch:
    @staticmethod
    def _qa_project(path):
        from audition_controller import ROOT
        p=Path(path).resolve()
        allowed=(ROOT/"tests"/"native_outputs").resolve()
        if (allowed not in p.parents or not p.name.startswith("ACCEPT_AU_")
            or p.suffix.lower()!=".sesx" or not p.is_file()):
            raise PermissionError("Only an existing tests/native_outputs/ACCEPT_AU_*.sesx")
        return p

    def _qa_close_documents(self):
        from audition_controller import ROOT
        allowed=json.dumps((ROOT/"tests").resolve().as_posix().lower()+"/")
        body=('var allowed='+allowed+';\n'
              'for(var i=0;i<app.documents.length;i++){\n'
              ' var p=String(app.documents[i].path).replace(/\\\\/g,"/").toLowerCase();\n'
              ' if(p.indexOf(allowed)!=0)throw "Refuse to close non-QA document";\n'
              '}\n'
              'for(var j=app.documents.length-1;j>=0;j--){\n'
              ' try{app.documents[j].closeDocument();}catch(e){out("CLOSE_ERROR_"+j,e);}\n'
              '}out("AFTER",app.documents.length);\n')
        result=self._run_jsx(body,"qa_doc_cleanup",timeout=35)
        if result.get("AFTER")!="0":
            raise RuntimeError("QA documents remain open")
        return result

    def native_track_state_roundtrip_qa(self, source, *, track_index=0,
                                        armed=True, visible=False, confirm=False):
        src=self._qa_project(source)
        if type(track_index)!=int or not 0<=track_index<32:
            raise ValueError("QA track index must be 0..31")
        if type(armed)!=bool or type(visible)!=bool:
            raise ValueError("QA state must be Boolean")
        if not confirm:
            return {"dry_run":True,"session":str(src),"track":track_index}
        before=hashlib.sha256(src.read_bytes()).hexdigest()
        q=json.dumps(src.as_posix())
        body=(
          'if(app.documents.length!=0)throw "Open documents present; QA only";\n'
          'var doc=app.openDocument(new DocumentOpenParameter('+q+'));\n'
          'try{\n'
          ' if(!doc||doc.reflect.name!="MultitrackDocument")throw "QA session did not open";\n'
          ' if(String(doc.path).replace(/\\\\/g,"/")!='+q+')throw "Session path mismatch";\n'
          ' var tracks=doc.audioTracks.audioClipTracks;\n'
          ' if(tracks.length<='+str(track_index)+')throw "Track absent";\n'
          ' var tr=tracks['+str(track_index)+'];\n'
          ' out("TRACK",tr.name);out("ARMED_BEFORE",tr.armed);out("VISIBLE_BEFORE",tr.visible);\n'
          ' try{tr.armed='+str(armed).lower()+';out("ARMED_CHANGED",tr.armed);}catch(e){out("ARMED_ERROR",e);}\n'
          ' try{tr.visible='+str(visible).lower()+';out("VISIBLE_CHANGED",tr.visible);}catch(e){out("VISIBLE_ERROR",e);}\n'
          ' try{tr.armed=false;out("ARMED_RESTORED",tr.armed);}catch(e){out("ARMED_RESTORE_ERROR",e);}\n'
          ' try{tr.visible=true;out("VISIBLE_RESTORED",tr.visible);}catch(e){out("VISIBLE_RESTORE_ERROR",e);}\n'
          ' out("SAVE",doc.saveDocument());\n'
          '}finally{\n'
          ' var qaRoot="d:/computer/adobe/audition/tests/";\n'
          ' for(var j=0;j<app.documents.length;j++){\n'
          '  var current=String(app.documents[j].path).replace(/\\\\/g,"/").toLowerCase();\n'
          '  if(current.indexOf(qaRoot)!=0)throw "Refusing close of non-QA file";\n'
          ' }\n'
          ' for(var k=app.documents.length-1;k>=0;k--){\n'
          '  try{app.documents[k].closeDocument();}catch(closeErr){out("CLOSE_WARNING_"+k,closeErr);}\n'
          ' }\n'
          '}\n'
          'out("DOCUMENTS_AFTER",app.documents.length);\n')
        result=self._run_jsx(body,"qa_track_state",timeout=65)
        cleaned=self._qa_close_documents()
        # A separate native request permits asynchronous close to settle.
        return {"cleanup":cleaned,"source":str(src),"source_sha256_before":before,
                "source_sha256_after":hashlib.sha256(src.read_bytes()).hexdigest(),
                "result":result,"native_dom_readback":True,
                "no_audio_recorded":True}

    def native_batch_open_qa(self, sources, *,confirm=False):
        from audition_controller import ROOT
        allowed=(ROOT/"tests"/"fixtures").resolve()
        if not isinstance(sources,list) or not 1<=len(sources)<=12:
            raise ValueError("1..12 QA media paths required")
        paths=[Path(p).resolve() for p in sources]
        if len(set(paths))!=len(paths) or any(
            allowed not in p.parents or p.suffix.lower() not in (".wav",".mp3",".flac")
            or not p.is_file() for p in paths):
            raise PermissionError("Only distinct existing QA media in tests/fixtures")
        if not confirm:return {"dry_run":True,"count":len(paths)}
        hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        body=('if(app.documents.length!=0)throw "Open documents present; QA only";\n'
              'var files='+json.dumps([p.as_posix() for p in paths])+';\n'
              'var done=0;for(var i=0;i<files.length;i++){\n'
              ' var wave=app.openDocument(new DocumentOpenParameter(files[i]));\n'
              ' try{if(!wave||wave.reflect.name!="WaveDocument")throw "Open not WaveDocument";\n'
              ' out("FILE_"+i+"_NAME",wave.displayName);\n'
              ' out("FILE_"+i+"_DURATION",wave.duration);done++;\n'
              ' }finally{if(wave)wave.closeDocument();}\n'
              '}out("IMPORTED",done);out("DOCUMENTS_AFTER",app.documents.length);\n')
        result=self._run_jsx(body,"qa_batch_open",timeout=85)
        cleaned=self._qa_close_documents()
        if result.get("IMPORTED")!=str(len(paths)):
            raise RuntimeError("Native QA batch readback incomplete")
        if any(hashlib.sha256(p.read_bytes()).hexdigest()!=hashes[str(p)] for p in paths):
            raise RuntimeError("QA input modified by batch open")
        return {"count":len(paths),"source_sha256":hashes,
                "result":result,"native_audition_import":True,"sources_unchanged":True}
