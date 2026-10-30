"""Precisely targeted live export. Requires independent real-host acceptance."""
from pathlib import Path
import json
import time
import uuid
import hashlib
import shutil
from scipy.io import wavfile
from controller_modules.host_lock import audition_host_lock


class AuditionProductionNative:
    def mixdown_production_session(self, session_path, output, *, timeout=120, confirm=False):
        from audition_controller import ROOT, CMD_MIXDOWN_NEW_FILE_ENTIRE
        source, destination = Path(session_path).resolve(), Path(output).resolve()
        if not source.is_file() or source.suffix.lower() != '.sesx':
            raise ValueError('Existing saved SESX required')
        if destination.exists() or destination.suffix.lower() != '.wav' or not destination.parent.is_dir():
            raise ValueError('New WAV destination required')
        if type(timeout) not in (int, float) or not 1 <= timeout <= 600 or type(confirm) is not bool:
            raise ValueError('Invalid timeout/confirmation')
        if not confirm:
            return dict(dry_run=True, session=str(source), output=str(destination))
        target = json.dumps(str(source))
        stage = destination.parent / ('.au_mix_' + uuid.uuid4().hex + '.wav')
        before_code = '''
function key(d){return String(d.path)+"|"+String(d.displayName);}
var mt=null,count=0;
for(var i=0;i<app.documents.length;i++){
 var d=app.documents[i];
 if(d.reflect.name=="MultitrackDocument" && new File(String(d.path)).fsName.toLowerCase()==new File(TARGET).fsName.toLowerCase()){mt=d;count++;}
 out("DOC_"+i,key(d));
}
if(count!=1)throw "Exactly one matching open session required";
if(mt.dirty)throw "Save source session before exporting";
if(app.transport.isPlaying||app.transport.isRecording)throw "Transport in use";
mt.activate();out("READY",true);
'''.replace('TARGET', target)
        start = time.monotonic()
        with audition_host_lock(ROOT / '_runtime' / 'locks', timeout):
            before = self._run_jsx_unlocked(before_code, 'production_mix_before', timeout)
            known = [v for k, v in before.items() if k.startswith('DOC_')]
            self.send_menu_command(CMD_MIXDOWN_NEW_FILE_ENTIRE)
            while time.monotonic()-start < timeout:
                code = '''
var known=KNOWN,candidates=[];
for(var i=0;i<app.documents.length;i++){
 var d=app.documents[i],key=String(d.path)+"|"+String(d.displayName),old=false;
 for(var j=0;j<known.length;j++)if(known[j]==key)old=true;
 if(!old&&d.reflect.name=="WaveDocument")candidates.push(d);
}
if(candidates.length>1)throw "Multiple new wave documents; export target ambiguous";
if(candidates.length==1&&!candidates[0].isBusy){
 var wave=candidates[0];out("SAVE",wave.saveAs(OUTPUT,false));out("DURATION",wave.duration);
}else out("WAIT",true);
'''.replace('KNOWN', json.dumps(known)).replace('OUTPUT', json.dumps(stage.as_posix()))
                result = self._run_jsx_unlocked(code, 'production_mix_poll', max(.1, timeout-(time.monotonic()-start)))
                if result.get('SAVE') == 'true':
                    # saveAs may return while Au still holds the output for writing.
                    # Close only our uniquely named staged result, using a fresh DOM
                    # request; never enumerate-close other user documents.
                    while time.monotonic()-start < timeout:
                        drain = '''
var owned=null;
for(var i=0;i<app.documents.length;i++){
 var d=app.documents[i];
 if(d.reflect.name=="WaveDocument" && new File(String(d.path)).fsName.toLowerCase()==new File(OUTPUT).fsName.toLowerCase())owned=d;
}
if(!owned)out("CLOSED",true);
else if(owned.isBusy)out("WAIT",true);
else {try{owned.activate();out("CLOSED",owned.closeDocument());}catch(e){out("CLOSE_PENDING",String(e));}}
'''.replace('OUTPUT', json.dumps(stage.as_posix()))
                        closed = self._run_jsx_unlocked(drain, 'production_mix_flush', max(.1,timeout-(time.monotonic()-start)))
                        if closed.get('CLOSED') == 'true': break
                        time.sleep(.1)
                    else:
                        raise TimeoutError('Owned mixdown save did not finish; staged output retained')
                    break
                time.sleep(.1)
            else:
                raise TimeoutError('Mixdown completion not observed; inspect host before retry')
        # User documents remain open; only the owned staged mixdown was closed.
        try:
            rate, audio = wavfile.read(stage)
            if len(audio) == 0:
                raise RuntimeError('Empty native mixdown')
            digest = hashlib.sha256(stage.read_bytes()).hexdigest()
            created = False
            try:
                with destination.open('xb') as out:
                    created = True
                    with stage.open('rb') as inp:
                        shutil.copyfileobj(inp, out)
                if hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
                    raise RuntimeError('Published mixdown hash mismatch')
            except Exception:
                if created: destination.unlink(missing_ok=True)
                raise
            return dict(output=str(destination), sha256=digest, sample_rate=int(rate), frames=len(audio),
                        native_audition_export=True, host_response=result)
        finally:
            try:
                stage.unlink(missing_ok=True)
            except OSError:
                pass  # Preserve a still-owned host file; never mask the original error.
