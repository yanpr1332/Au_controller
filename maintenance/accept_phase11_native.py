"""Live-host acceptance on a unique owned QA session; never close other documents."""
from pathlib import Path
import sys
import json
import time
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from audition_controller import AuditionController as C

if __name__ == '__main__':
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    folder = ROOT/'tests/native_outputs'/('ACCEPT_AU_Phase11_'+stamp)
    folder.mkdir()
    c = C()
    evidence = dict(status='running', folder=str(folder))
    receipt = ROOT/'tests/receipts'/('phase11_native_'+stamp+'.json')
    def save():
        receipt.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')
    try:
        evidence['host_before'] = c.status(); save()
        if evidence['host_before'].get('DOCUMENTS') != '0':
            raise RuntimeError('Acceptance requires zero pre-existing user documents')
        template = ROOT/'tests/native_outputs/ACCEPT_AU_Phase06_multi_arrangement.sesx'
        source = ROOT/'tests/fixtures/accept_au_sine_48k_mono.wav'
        imported = folder/'ACCEPT_AU_Phase11_Imported.sesx'
        evidence['import'] = c.import_production_wavs(template,imported,[
            dict(source=str(source),track_id='10001',start_samples=160000),
            dict(source=str(source),new_track_name='QA Phase11 Imported',start_samples=32000)],confirm=True)
        save()
        evidence['open_import'] = c.open_document(str(imported)); save()
        evidence['native_import_snapshot'] = c._run_jsx('''
var d=app.activeDocument;if(!d||d.reflect.name!="MultitrackDocument")throw "Expected multitrack";
out("NAME",d.displayName);out("PATH",d.path);out("DIRTY",d.dirty);
var tracks=d.audioTracks.audioClipTracks;out("TRACKS",tracks.length);
for(var i=0;i<tracks.length;i++){
out("TRACK_"+i+"_NAME",tracks[i].name);out("TRACK_"+i+"_CLIPS",tracks[i].audioClips.length);
}
''','phase11_import_readback',40); save()
        evidence['native_mixdown'] = c.mixdown_production_session(imported,folder/'native_import_mix.wav',confirm=True)
        save()
        evidence['status'] = 'native_import_and_mixdown_completed'
    except Exception as exc:
        evidence.update(status='failed',error=repr(exc))
        raise
    finally:
        save()
        print('RECEIPT',receipt,flush=True)
