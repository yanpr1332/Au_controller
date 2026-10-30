"""Bounded native Audition transport verification on isolated QA multitrack sessions.

Playback is limited to <= 250 ms and is stopped in a finally block.
Restores original loop state and playhead so no user session is altered.
"""
from __future__ import annotations
import json
class AuditionNativeTransportQA:
    def native_transport_snapshot(self):
        """Real read-only ExtendScript Transport state."""
        return self._run_jsx(
            'out("PLAYING",app.transport.isPlaying);'
            'out("PAUSED",app.transport.isPaused);'
            'out("RECORDING",app.transport.isRecording);'
            'out("LOOP",app.transport.loop);'
            'out("PLAY_ENABLED",app.transport.isPlayEnabled);'
            'out("RECORD_ENABLED",app.transport.isRecordEnabled);'
            'out("ACTIVE",app.activeDocument?app.activeDocument.displayName:"");',
            'qa_transport_snapshot',timeout=25)

    def native_qa_transport_accept(self,session_name,*,seek_samples=0,
                                   play_ms=150,test_pause=True,confirm=False):
        """QA-only real seek + temporary loop + play/stop with state restore."""
        from audition_controller import AuditionController
        name=self._qa_session_name(session_name)
        if type(seek_samples)!=int or not 0<=seek_samples<=48_000_000:
            raise ValueError('Invalid seek position')
        if type(play_ms)!=int or not 25<=play_ms<=250:
            raise ValueError('25..250 ms playback duration')
        if type(test_pause)!=bool:raise ValueError('test_pause must be bool')
        if not confirm:return {'dry_run':True,'session':name,'seek':seek_samples,'ms':play_ms}
        q=json.dumps
        body=('var mt=null;for(var k=0;k<app.documents.length;k++){var d=app.documents[k];'
          'if(d.reflect.name=="MultitrackDocument"&&d.displayName=='+q(name)+')mt=d;'
          'else if(String(d.displayName).indexOf("accept_")!=0&&String(d.displayName).indexOf("0_accept_")!=0)'
          'throw "Unexpected non-QA document";}\n'
          'if(!mt)throw "QA session not open";'
          'if(app.transport.isPlaying||app.transport.isRecording)throw "Transport already in use";\n'
          'mt.activate();var prevPos=mt.playheadPosition,prevLoop=app.transport.loop;\n'
          'if('+str(seek_samples)+'>=mt.duration)throw "Seek exceeds native duration";\n'
          'try{mt.playheadPosition='+str(seek_samples)+';'
          'out("SEEK",mt.playheadPosition);'
          'app.transport.loop=true;out("LOOP_SET",app.transport.loop);'
          'app.transport.loop=false;out("LOOP_CLEAR",app.transport.loop);'
          'out("PLAY_ENABLED",app.transport.isPlayEnabled);'
          'if(!app.transport.isPlayEnabled)throw "Playback not enabled";'
          'app.transport.play();$.sleep('+str(play_ms)+');'
          'out("PLAY_OBSERVED",app.transport.isPlaying);'
          +('app.transport.pause();out("PAUSE_OBSERVED",app.transport.isPaused);' if test_pause else '')+
          'app.transport.stop();out("STOP_OBSERVED",!app.transport.isPlaying);'
          '}finally{try{app.transport.stop();}catch(e){}'
          'try{app.transport.loop=prevLoop;}catch(e){}'
          'try{mt.playheadPosition=prevPos;}catch(e){}'
          'out("RESTORED_POS",mt.playheadPosition);'
          'out("RESTORED_LOOP",app.transport.loop);}\n')
        return self._run_jsx(body,'native_qa_transport_live',timeout=30)
