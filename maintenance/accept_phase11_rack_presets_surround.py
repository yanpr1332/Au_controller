"""Native saved Rack presets and actual six-channel mixdown acceptance."""
from pathlib import Path
import sys,json
from datetime import datetime,timezone
import numpy as np
from scipy.io import wavfile
from lxml import etree as ET
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from audition_controller import AuditionController as C

if __name__=='__main__':
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    folder=ROOT/'tests/native_outputs'/('ACCEPT_AU_RackSurround_'+stamp);folder.mkdir()
    rack_source=ROOT/'tests/native_outputs/ACCEPT_AU_Rack_20261030T021617/ACCEPT_AU_Rack.sesx'
    c=C();result={};receipt=ROOT/'tests/receipts'/('phase11_rack_surround_'+stamp+'.json')
    try:
        edited=folder/'ACCEPT_AU_EditedRack.sesx'
        result['edit_rack']=C.edit_native_rack(rack_source,edited,track_id='10001',operations=[
            dict(action='copy_slot',template_session=str(rack_source),template_track_id='10001',template_slot=0,slot=1),
            dict(action='reorder',order=[1,0]),dict(action='power',slot=1,enabled=False)],confirm=True)
        preset=folder/'native_rack_preset.json';result['preset_export']=C.export_native_rack_preset(edited,preset,track_id='10001',confirm=True)
        applied=folder/'ACCEPT_AU_AppliedRack.sesx'
        result['preset_apply']=C.apply_native_rack_preset(rack_source,applied,preset,track_id='10001',confirm=True)
        result['preset_open']=c.open_document(str(applied))
        result['preset_render']=c.mixdown_production_session(applied,folder/'native_preset_mix.wav',confirm=True)
        sr,a=wavfile.read(result['preset_render']['output']);a=a.astype(float)
        if a.ndim>1:a=a.mean(axis=1)
        a=a[sr//2:sr*2];t=np.arange(len(a))/sr
        ratio=abs(np.dot(a,np.exp(-2j*np.pi*60*t)))/max(abs(np.dot(a,np.exp(-2j*np.pi*1000*t))),1e-20)
        result['preset_hum_to_tone_ratio']=float(ratio)
        manifest=folder/'ACCEPT_AU_Surround.auctl';native=folder/'ACCEPT_AU_Surround.sesx'
        C.create_native_sdk_session(dict(name='ACCEPT_AU_Surround',channels=6,tracks=[dict(source=str(ROOT/'tests/fixtures/accept_au_sine_48k_mono.wav'),name='QA Surround Source')]),manifest,confirm=True)
        result['surround_open_sdk']=c.open_document(str(manifest))
        result['surround_save']=c._run_jsx('var d=app.activeDocument;if(d.displayName!="ACCEPT_AU_Surround")throw "Wrong QA session";var r=d.saveAsDocument('+json.dumps(native.as_posix())+');for(var k in r)out(k,r[k]);','phase11_surround_save',35)
        result['surround_close']=c._run_jsx('var a='+json.dumps([manifest.as_posix(),native.as_posix()])+';for(var i=0;i<app.documents.length;i++){var d=app.documents[i],p=String(d.path).replace(/\\\\/g,"/");if(d.reflect.name=="MultitrackDocument"&&(p==a[0]||p==a[1])){if(d.dirty)throw "Save pending";d.activate();out("CLOSE",d.closeDocument());break;}}','phase11_surround_close',35)
        result['surround_open_native']=c.open_document(str(native))
        result['surround_render']=c.mixdown_production_session(native,folder/'native_surround_mix.wav',confirm=True)
        sr,a=wavfile.read(result['surround_render']['output'])
        result['surround_channels']=1 if a.ndim==1 else a.shape[1]
        result['surround_channel_rms']=np.sqrt(np.mean(a.astype(float)**2,axis=0)).tolist()
        result['passed']=bool(ratio<.05 and result['surround_channels']==6 and np.max(np.abs(a))>0)
    finally:
        receipt.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
        print(json.dumps(result,ensure_ascii=False,indent=2));print('RECEIPT',receipt)
