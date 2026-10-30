"""Native Au render comparisons for pan, fader automation and sends."""
from pathlib import Path
import sys,json
from datetime import datetime,timezone
from copy import deepcopy
import numpy as np
from scipy.io import wavfile
from lxml import etree as ET
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from audition_controller import AuditionController as C

if __name__=='__main__':
    source=ROOT/'tests/native_outputs/ACCEPT_AU_SDK_20261030T020334/ACCEPT_AU_SDK_Native.sesx'
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    folder=ROOT/'tests/native_outputs'/('ACCEPT_AU_Automation_'+stamp);folder.mkdir()
    root=ET.parse(str(source)).getroot()
    track=root.find('./session/tracks/audioTrack')
    volume=next(c for c in track.findall('./trackAudioParameters/component') if c.get('id')=='trackFader').find('parameter')
    volume.set('parameterValue','1')
    for child in list(volume):volume.remove(child)
    for send in track.findall('sendList'):track.remove(send)
    base=folder/'ACCEPT_AU_Base.sesx';base.write_bytes(ET.tostring(root,encoding='utf-8',xml_declaration=True))
    c=C();variants={'base':base}
    for label,value in (('left',-1),('right',1)):
        output=folder/('ACCEPT_AU_'+label+'.sesx')
        C.patch_native_pan_position(base,output,track_id='10001',position=value,confirm=True)
        variants[label]=output
    envelope=folder/'ACCEPT_AU_Envelope.sesx'
    C.patch_native_track_envelope(base,envelope,track_id='10001',points=[dict(sample=0,value=.15),dict(sample=96000,value=.7)],confirm=True)
    variants['envelope']=envelope
    send=folder/'ACCEPT_AU_Send.sesx'
    C.patch_native_send(base,send,track_id='10001',bus_id='10090',level=.25,confirm=True)
    variants['send']=send
    receipt=ROOT/'tests/receipts'/('phase11_automation_'+stamp+'.json')
    results=dict(folder=str(folder),renders={})
    try:
        for label,path in variants.items():
            c.open_document(str(path))
            render=c.mixdown_production_session(path,folder/(label+'.wav'),confirm=True)
            rate,audio=wavfile.read(render['output'])
            if audio.dtype.kind in 'iu':audio=audio.astype(float)/(2**(audio.dtype.itemsize*8-1))
            if audio.ndim==1:audio=audio[:,None]
            render['channel_rms']=np.sqrt(np.mean(audio.astype(float)**2,axis=0)).tolist()
            render['early_rms']=float(np.sqrt(np.mean(audio[4800:24000].astype(float)**2)))
            render['late_rms']=float(np.sqrt(np.mean(audio[96000:110400].astype(float)**2)))
            results['renders'][label]=render
            c._run_jsx('var path='+json.dumps(path.as_posix())+';for(var i=0;i<app.documents.length;i++){var d=app.documents[i];if(String(d.path).replace(/\\\\/g,"/")==path){if(d.dirty)throw "Unexpected dirty QA session";d.activate();out("CLOSE",d.closeDocument());break;}}','phase11_variant_close',30)
            receipt.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
        results['envelope_changes_level']=results['renders']['envelope']['late_rms']>results['renders']['envelope']['early_rms']*2
        results['pan_left_isolated']=results['renders']['left']['channel_rms'][1] < results['renders']['left']['channel_rms'][0]*.001
        results['pan_right_isolated']=results['renders']['right']['channel_rms'][0] < results['renders']['right']['channel_rms'][1]*.001
        results['send_changes_level']=results['renders']['send']['late_rms']>results['renders']['base']['late_rms']*1.01
    finally:
        receipt.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
        print(json.dumps(results,ensure_ascii=False,indent=2));print('RECEIPT',receipt)
