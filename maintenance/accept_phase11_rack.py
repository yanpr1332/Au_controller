"""Native Rack acceptance using the installed Remove 60 Hz Hum preset."""
from pathlib import Path
import sys,json
import xml.etree.ElementTree as E
from datetime import datetime,timezone
import numpy as np
from scipy.io import wavfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from audition_controller import AuditionController as C

if __name__=='__main__':
    import os
    favorites=E.parse(Path(os.environ['APPDATA'])/'Adobe/Audition/26.0/Favorites.xml').getroot()
    favorite=next(p for p in favorites.findall('.//prop.pair') if p.findtext('key')=='Remove 60 Hz Hum')
    def value(parent,key):
        if parent.tag=='prop.pair':parent=parent.find('prop.list')
        row=next(p for p in parent.findall('prop.pair') if p.findtext('key')==key)
        return next(n for n in row if n.tag!='key')
    settings=value(value(favorite,'Settings'),'ActionSettings')
    component=value(settings,'ID').text
    chunk=value(value(settings,'Settings'),'ChunkData').text
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    folder=ROOT/'tests/native_outputs'/('ACCEPT_AU_Rack_'+stamp);folder.mkdir()
    rate=48000;t=np.arange(115200)/rate
    source=folder/'accept_hum_and_tone.wav';wavfile.write(source,rate,(.03*np.sin(2*np.pi*60*t)+.05*np.sin(2*np.pi*1000*t)).astype(np.float32))
    spec=dict(name='ACCEPT_AU_Native_Rack',tracks=[dict(source=str(source),name='QA Native Hum Rack',effects=[dict(component_id=component,chunk_base64=chunk)])])
    c=C();manifest=folder/'ACCEPT_AU_Rack.auctl';native=folder/'ACCEPT_AU_Rack.sesx'
    result={'manifest':C.create_native_sdk_session(spec,manifest,confirm=True)}
    receipt=ROOT/'tests/receipts'/('phase11_rack_'+stamp+'.json')
    try:
        result['open_sdk']=c.open_document(str(manifest))
        result['save_native']=c._run_jsx('var d=app.activeDocument;if(d.displayName!="ACCEPT_AU_Native_Rack")throw "Wrong QA session";var r=d.saveAsDocument('+json.dumps(native.as_posix())+');for(var k in r)out(k,r[k]);','phase11_rack_save',40)
        root=E.parse(native).getroot()
        result['native_rack_slots']=[dict(slot.attrib,components=[dict(x.attrib) for x in slot.findall('component')]) for slot in root.findall('.//effectsRack/slot')]
        if not result['native_rack_slots']:raise RuntimeError('No Rack slot persisted by Au')
        result['close_saved_sdk']=c._run_jsx('var target='+json.dumps(native.as_posix())+';for(var i=0;i<app.documents.length;i++){var d=app.documents[i];if(d.reflect.name=="MultitrackDocument"&&String(d.path).replace(/\\\\/g,"/")==target){if(d.dirty)throw "Save still pending";d.activate();out("CLOSE",d.closeDocument());break;}}','phase11_rack_saved_close',30)
        result['open_native']=c.open_document(str(native))
        result['mixdown']=c.mixdown_production_session(native,folder/'native_rack_mix.wav',confirm=True)
        sr,audio=wavfile.read(result['mixdown']['output'])
        if audio.ndim>1:audio=audio.mean(axis=1)
        audio=audio.astype(float)
        if not np.max(np.abs(audio))>0:raise RuntimeError('Silent rack render')
        segment=audio[rate//2:rate*2]
        def amplitude(hz):
            wave=np.exp(-2j*np.pi*hz*np.arange(len(segment))/sr)
            return float(abs(np.dot(segment,wave))*2/len(segment))
        result['hum_to_tone_ratio']=amplitude(60)/max(amplitude(1000),1e-20)
        result['source_hum_to_tone_ratio']=.03/.05
        result['passed']=result['hum_to_tone_ratio']<.05
    finally:
        receipt.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
        print(json.dumps(result,ensure_ascii=False,indent=2));print('RECEIPT',receipt)
