"""Completed read-only host/evidence capabilities from phases 15–19.

These inspect real state or saved artifacts, never imply successful GUI actions.
"""
import gzip
import hashlib
import json
from pathlib import Path


class AuditionCompletedDiagnostics:
    def native_document_snapshot(self):
        """Read document paths, dirty state and multitrack clip timing in samples."""
        return self._run_jsx('''
out("DOCUMENTS",app.documents.length);
for(var n=0;n<app.documents.length;n++){
 var d=app.documents[n],p="DOC_"+n;
 out(p+"_PATH",d.path);out(p+"_DIRTY",d.dirty);out(p+"_CLASS",d.reflect.name);
 if(d.reflect.name!="MultitrackDocument")continue;
 var tracks=d.audioTracks.audioClipTracks;out(p+"_TRACKS",tracks.length);
 for(var i=0;i<tracks.length;i++){
  var t=p+"_TRACK_"+i;out(t+"_NAME",tracks[i].name);out(t+"_CLIPS",tracks[i].audioClips.length);
  for(var j=0;j<tracks[i].audioClips.length;j++){
   var c=tracks[i].audioClips[j],k=t+"_CLIP_"+j;
   out(k+"_NAME",c.name);out(k+"_START",c.startTime);out(k+"_DURATION",c.duration);
  }
 }
}''', 'document_snapshot', 30)

    def inspect_native_omf(self, path):
        """Hash an existing OMF and ask the live host whether it can see it.

        Does not export/import; GUI file opening is a separate workflow.
        """
        p=Path(path).resolve()
        if p.suffix.lower()!='.omf' or not p.is_file():
            raise ValueError('Existing OMF required')
        digest=hashlib.sha256()
        with p.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
        host=self._run_jsx('var f=new File('+json.dumps(p.as_posix())+');'
            'out("EXISTS",f.exists);out("SIZE",f.length);','omf_visibility',15)
        return dict(path=str(p),bytes=p.stat().st_size,sha256=digest.hexdigest(),
                    host_file_visibility=host,roundtrip_verified=False)

    @staticmethod
    def inspect_cep_receipt(path):
        """Read a bounded CEP handshake or page-health JSON receipt, offline."""
        p=Path(path)
        if p.suffix.lower() not in ('.json','.txt') or p.stat().st_size>65536:
            raise ValueError('Small JSON or text CEP receipt required')
        text=p.read_text(encoding='utf-8-sig')
        if p.suffix.lower()=='.json':
            data=json.loads(text)
            if not isinstance(data,dict) or data.get('stage') not in (
                'dom-ready','loaded','repaint-requested','after-content-resize','resize-error','resized','error'):
                raise ValueError('Invalid CEP page receipt')
            dimensions=[data.get('width'),data.get('height')]
            if any(type(v) not in (int,float) or not 0<=v<=100000 for v in dimensions):
                raise ValueError('Invalid CEP dimensions')
            return dict(kind='page',data=data,zero_viewport=0 in dimensions,
                        visual_rendering_verified=False,live_probe_executed=False)
        data=dict(line.split('=',1) for line in text.splitlines() if '=' in line)
        if data.get('HOST')!='Audition' or data.get('REFLECT_CLASS')!='Application':
            raise ValueError('Invalid Audition CEP handshake')
        return dict(kind='handshake',data=data,host_callback_recorded=True,
                    visual_rendering_verified=False,live_probe_executed=False)

    @staticmethod
    def inspect_premiere_project_reference(path, media_name):
        """Check a saved PR project reference; not playback or Au/Pr roundtrip."""
        p=Path(path)
        if p.suffix.lower()!='.prproj' or not isinstance(media_name,str) or not media_name or len(media_name)>1024:
            raise ValueError('PR project and media reference required')
        limit=64*1024*1024
        if p.stat().st_size>limit:raise ValueError('Project exceeds inspection limit')
        raw=p.read_bytes()
        if raw[:2]==b'\x1f\x8b':
            with gzip.open(p,'rb') as stream:xml=stream.read(limit+1)
        else:xml=raw
        if len(xml)>limit:raise ValueError('Expanded project exceeds inspection limit')
        return dict(path=str(p.resolve()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
                    media_reference_present=media_name.encode('utf8') in xml,
                    premiere_roundtrip_verified=False,playback_verified=False)
