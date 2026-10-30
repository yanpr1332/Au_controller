"""Bounded native microphone QA; execution requires explicit user authorization."""
from pathlib import Path
import json
import math
from lxml import etree as ET
from scipy.io import wavfile


class AuditionNativeRecording:
    def native_record_input_qa(self,destination,*,seconds=1.0,confirm=False):
        from audition_controller import ROOT
        folder=Path(destination).resolve();allowed=(ROOT/'tests/native_outputs').resolve()
        if allowed not in folder.parents or folder.exists() or not folder.parent.is_dir() or not folder.name.startswith('ACCEPT_AU_'):
            raise ValueError('New ACCEPT_AU_ directory under tests/native_outputs required')
        if type(seconds) not in (int,float) or not math.isfinite(seconds) or not .1<=seconds<=3 or type(confirm) is not bool:
            raise ValueError('Recording duration .1..3 seconds and Boolean confirm required')
        if not confirm:return dict(dry_run=True,output=str(folder),seconds=seconds,input='Audition configured default input',actual_microphone_capture=True)
        if self.status().get('DOCUMENTS')!='0':raise RuntimeError('Recording QA requires zero pre-existing documents')
        template=ROOT/'tests/native_outputs/ACCEPT_AU_Phase06_multi_arrangement.sesx'
        source,tree,root,tracks=self._native_tree(template)
        for i,track in enumerate(tracks):
            for clip in track.findall('audioClip'):track.remove(clip)
            track.find('./trackParameters/name').text='QA Recording '+str(i)
            ap=track.find('trackAudioParameters');ap.set('recordArmed','false');ap.set('monitoring','false')
        root.find('session').set('duration','48000')
        folder.mkdir();session=folder/'ACCEPT_AU_Recording.sesx'
        session.write_bytes(ET.tostring(root,encoding='utf-8',xml_declaration=True))
        self.open_document(str(session))
        response=self._run_jsx('''
var path=PATH,doc=null;
for(var i=0;i<app.documents.length;i++){var d=app.documents[i];if(d.reflect.name=="MultitrackDocument"&&String(d.path).replace(/\\\\/g,"/")==path)doc=d;}
if(!doc)throw "Owned recording session absent";
if(app.transport.isPlaying||app.transport.isRecording)throw "Transport in use";
doc.activate();doc.playheadPosition=0;var track=doc.audioTracks.audioClipTracks[0];
try{
 track.mute=true;track.armed=true;
 if(!app.transport.isRecordEnabled)throw "Configured input is not record enabled";
 app.transport.record();out("RECORDING_OBSERVED",app.transport.isRecording);
 $.sleep(MILLISECONDS);
}finally{try{app.transport.stop();}finally{track.armed=false;}}
out("STOPPED",!app.transport.isRecording);out("ARMED",track.armed);
'''.replace('PATH',json.dumps(session.as_posix())).replace('MILLISECONDS',str(int(seconds*1000))),'phase11_microphone_capture',30)
        save=self._run_jsx('var path='+json.dumps(session.as_posix())+';for(var i=0;i<app.documents.length;i++){var d=app.documents[i];if(d.reflect.name=="MultitrackDocument"&&String(d.path).replace(/\\\\/g,"/")==path){d.activate();var r=d.saveDocument();for(var k in r)out(k,r[k]);out("CLIPS",d.audioTracks.audioClipTracks[0].audioClips.length);}}','phase11_microphone_save',30)
        report=self.inspect_native_sesx(session)
        if response.get('RECORDING_OBSERVED')!='true' or response.get('STOPPED')!='true' or response.get('ARMED')!='false' or report['clip_count']<1:
            raise RuntimeError('Recording did not produce verified native clips: '+str(response))
        readback=[]
        for media in report['media']:
            path=Path(media['absolute_path'])
            if not path.is_file():raise RuntimeError('Native recorded media missing')
            rate,audio=wavfile.read(path)
            if not len(audio):raise RuntimeError('Native recorded media is empty')
            readback.append(dict(path=str(path),rate=int(rate),frames=len(audio),seconds=len(audio)/rate,sha256=self._hash_file(path)))
        return dict(session=str(session),response=response,save=save,inspection=report,audio_readback=readback,native_recording=True)
