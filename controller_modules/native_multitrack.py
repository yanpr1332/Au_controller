"""Guarded Audition 26 native MultitrackDocument DOM operations and audio mixdown.

All mutating entrypoints require an isolated ACCEPT_AU_ session name,
explicit confirm=True, and test-only clip/track constraints.
"""
from __future__ import annotations
import json
import re
import time
from pathlib import Path

class AuditionNativeMultitrack:
    @staticmethod
    def _qa_session_name(name):
        if not isinstance(name,str) or not re.fullmatch(r'ACCEPT_AU_[A-Za-z0-9_]{3,70}',name):
            raise PermissionError('Native multi-track writes restricted to ACCEPT_AU_ test sessions')
        return name

    def native_multitrack_snapshot(self,session_name:str):
        name=self._qa_session_name(session_name)
        js=('var mt=null;for(var i=0;i<app.documents.length;i++) {var d=app.documents[i];'
            'if(d.reflect.name=="MultitrackDocument"&&String(d.displayName)=='+json.dumps(name)+')mt=d;}\n'
            'if(!mt)throw "QA Session not found";\n'
            'out("SESSION_NAME",mt.displayName);out("PATH",mt.path);out("SAMPLE_RATE",mt.sampleRate);\n'
            'out("TRACKS",mt.audioTracks.audioClipTracks.length);\n'
            'for(var j=0;j<mt.audioTracks.audioClipTracks.length;j++){\n'
            'var tr=mt.audioTracks.audioClipTracks[j];\n'
            'out("TRACK"+j+"_NAME",tr.name);out("TRACK"+j+"_MUTE",tr.mute);\n'
            'out("TRACK"+j+"_SOLO",tr.solo);out("TRACK"+j+"_CLIPS",tr.audioClips.length);\n'
            'for(var k=0;k<tr.audioClips.length;k++){\n'
            'var cl=tr.audioClips[k];out("TRACK"+j+"_CLIP"+k+"_NAME",cl.name);\n'
            'out("TRACK"+j+"_CLIP"+k+"_START",cl.startTime);\n'
            'out("TRACK"+j+"_CLIP"+k+"_DURATION",cl.duration);}}\n')
        return self._run_jsx(js,'native_mt_snapshot',timeout=40)

    def native_multitrack_edit_qa(self,session_name:str,track_index:int,*,
                                   name:str|None=None,mute:bool|None=None,
                                   solo:bool|None=None,clip_index:int|None=None,
                                   clip_start_samples:int|None=None,
                                   confirm:bool=False)->dict:
        session=self._qa_session_name(session_name)
        if type(track_index)!=int or not 0<=track_index<=64:raise ValueError('Invalid track index')
        if name is None and mute is None and solo is None and clip_index is None:
            raise ValueError('No requested edit')
        if name is not None and (not isinstance(name,str) or not 1<=len(name)<=96):
            raise ValueError('Invalid track label')
        if mute is not None and type(mute)!=bool:raise ValueError('Mute must be bool')
        if solo is not None and type(solo)!=bool:raise ValueError('Solo must be bool')
        if (clip_index is None)!=(clip_start_samples is None):
            raise ValueError('Clip index and start must be provided together')
        if clip_index is not None and (type(clip_index)!=int or not 0<=clip_index<128 or
                                       type(clip_start_samples)!=int or not 0<=clip_start_samples<=48_000_000):
            raise ValueError('Invalid clip position')
        if not confirm:return {'dry_run':True,'session':session,'track':track_index}
        js=('var mt=null;for(var i=0;i<app.documents.length;i++){var d=app.documents[i];'
            'if(d.reflect.name=="MultitrackDocument"&&String(d.displayName)=='+json.dumps(session)+')mt=d;}\n'
            'if(!mt)throw "QA session absent";\n'
            'if(mt.audioTracks.audioClipTracks.length<='+str(track_index)+')throw "Track absent";\n'
            'var tr=mt.audioTracks.audioClipTracks['+str(track_index)+'];\n')
        if name is not None:js+='tr.name='+json.dumps(name)+';\n'
        if mute is not None:js+='tr.mute='+str(mute).lower()+';\n'
        if solo is not None:js+='tr.solo='+str(solo).lower()+';\n'
        if clip_index is not None:
            js+=('if(tr.audioClips.length<='+str(clip_index)+')throw "Clip absent";\n'
                 'if(String(tr.audioClips['+str(clip_index)+'].name).indexOf("accept_")!=0)throw "Clip not QA media";\n'
                 'tr.audioClips['+str(clip_index)+'].startTime='+str(clip_start_samples)+';\n'
                 'out("CLIP_START",tr.audioClips['+str(clip_index)+'].startTime);\n')
        js+=('out("TRACK_NAME",tr.name);out("MUTE",tr.mute);out("SOLO",tr.solo);\n'
             'var saved=mt.saveDocument();out("SAVE",saved);\n'
             'out("FILE_PATH",mt.path);\n')
        return self._run_jsx(js,'native_mt_edit',timeout=40)

    def native_multitrack_mixdown_qa(self,session_name:str,output:str|Path,*,confirm:bool=False,
                                      poll_seconds:float=3.0):
        from audition_controller import ROOT,CMD_MIXDOWN_NEW_FILE_ENTIRE
        name=self._qa_session_name(session_name)
        p=Path(output).resolve()
        qa=(ROOT/'tests'/'native_outputs').resolve()
        if qa not in p.parents or p.suffix.lower()!='.wav' or p.exists() or not p.parent.is_dir():
            raise PermissionError('Mixdown output must be a new QA WAV in tests/native_outputs')
        if not confirm:return {'dry_run':True,'session':name,'output':str(p)}
        before=self.native_multitrack_snapshot(name)
        if 'ERROR' in before or before.get('SESSION_NAME')!=name:raise RuntimeError('QA session snapshot failed')
        activ=('var mt=null;for(var i=0;i<app.documents.length;i++){var d=app.documents[i];'
               'if(d.reflect.name=="MultitrackDocument"&&String(d.displayName)=='+json.dumps(name)+')mt=d;}\n'
               'if(!mt)throw "Missing test session";mt.activate();'
               'out("SESSION",mt.displayName);')
        armed=self._run_jsx(activ,'native_mt_activate',timeout=30)
        if armed.get('SESSION')!=name:raise RuntimeError('Session activation not confirmed')
        self.send_menu_command(CMD_MIXDOWN_NEW_FILE_ENTIRE)
        time.sleep(max(1.0,min(float(poll_seconds),5.0)))
        target=json.dumps(p.as_posix())
        js=('var wave=null;for(var i=0;i<app.documents.length;i++){var d=app.documents[i];'
            'if(d.reflect.name=="WaveDocument"&&String(d.displayName).indexOf("Mixdown")>=0)wave=d;}\n'
            'if(!wave)throw "No native mixdown wave document found";\n'
            'wave.activate();out("NAME",wave.displayName);\n'
            'out("DURATION",wave.duration);\n'
            'out("SAVE",wave.saveAs('+target+',true));\n'
            '$.sleep(250);out("EXISTS",new File('+target+').exists);\n')
        result=self._run_jsx(js,'native_mt_mixdown',timeout=50)
        return {'session':name,'output':str(p),'exists':p.is_file(),'native_result':result,
                'native_audition_mixdown':True,'snapshot_before':before}

    def native_add_track_qa(self,session_name:str,*,label:str="QA Added Track",
                            confirm:bool=False):
        """Add a native Audition audio track of the session's existing channel layout."""
        name=self._qa_session_name(session_name)
        if not isinstance(label,str) or not label.startswith('QA ') or len(label)>80:
            raise ValueError('New QA track label must start QA ')
        if not confirm:return {'dry_run':True,'session':name,'track_label':label}
        q=json.dumps
        js=('var mt=null;for(var i=0;i<app.documents.length;i++){var d=app.documents[i];'
            'if(d.reflect.name=="MultitrackDocument"&&d.displayName=='+q(name)+')mt=d;}\n'
            'if(!mt)throw "QA session missing";'
            'var t=mt.audioTracks.audioClipTracks,n=t.length;\n'
            'if(n<1||n>60)throw "Unexpected track count";\n'
            'var newTrack=t.add(t[0].audioFormat.channelLayout);\n'
            'if(t.length!=n+1)throw "Native add did not grow track count";\n'
            'newTrack.name='+q(label)+';\n'
            'var actualIndex=-1;for(var idx=0;idx<t.length;idx++){if(t[idx].id==newTrack.id)actualIndex=idx;}\n'
            'out("TRACK",newTrack.name);out("TRACK_INDEX",actualIndex);out("TRACK_COUNT",t.length);\n'
            'out("SAVE",mt.saveDocument());')
        return self._run_jsx(js,'native_mt_add_track',timeout=40)

    def native_remove_empty_track_qa(self,session_name:str,track_index:int,*,confirm:bool=False):
        """Remove ONLY an empty track with a QA prefix in a QA session."""
        name=self._qa_session_name(session_name)
        if type(track_index)!=int or not 0<=track_index<=63:
            raise ValueError('Invalid track index')
        if not confirm:return {'dry_run':True,'session':name,'track_index':track_index}
        q=json.dumps
        js=('var mt=null;for(var i=0;i<app.documents.length;i++){var d=app.documents[i];'
            'if(d.reflect.name=="MultitrackDocument"&&d.displayName=='+q(name)+')mt=d;}\n'
            'if(!mt)throw "QA session missing";var tracks=mt.audioTracks.audioClipTracks;\n'
            'var index='+str(track_index)+';if(index>=tracks.length)throw "Track absent";\n'
            'var tr=tracks[index];if(String(tr.name).indexOf("QA ")!=0)throw "Track not QA-labelled";\n'
            'if(tr.audioClips.length!=0)throw "Cannot remove nonempty track";\n'
            'var n=tracks.length;out("TRACK",tr.name);\n'
            'out("REMOVE",String(tracks.remove(tr)));\n'
            'out("COUNT",tracks.length);\n'
            'if(tracks.length!=n-1)throw "Track removal did not change count";\n'
            'out("SAVE",mt.saveDocument());\n')
        return self._run_jsx(js,'native_mt_remove_empty',timeout=40)

    def native_move_clip_qa(self,session_name:str,from_track:int,to_track:int,*,clip_index:int=0,
                            start_samples:int|None=None,confirm:bool=False):
        """Move an existing QA clip between tracks while preserving start time by default."""
        name=self._qa_session_name(session_name)
        if any(type(v)!=int or not 0<=v<64 for v in (from_track,to_track,clip_index)):
            raise ValueError('Invalid track/clip index')
        if from_track==to_track:raise ValueError('Source and target tracks must differ')
        if start_samples is not None and (type(start_samples)!=int or not 0<=start_samples<=48_000_000):
            raise ValueError('Invalid target clip start')
        if not confirm:return {'dry_run':True,'session':name,'from_track':from_track,'to_track':to_track}
        q=json.dumps
        js=('var mt=null;for(var i=0;i<app.documents.length;i++){var d=app.documents[i];'
            'if(d.reflect.name=="MultitrackDocument"&&d.displayName=='+q(name)+')mt=d;}\n'
            'if(!mt)throw "QA session missing";var tracks=mt.audioTracks.audioClipTracks;\n'
            'if(tracks.length<='+str(max(from_track,to_track))+')throw "Track missing";\n'
            'var source=tracks['+str(from_track)+'],target=tracks['+str(to_track)+'];\n'
            'if(source.audioClips.length<='+str(clip_index)+')throw "Clip absent";\n'
            'if(target.audioClips.length)throw "Target QA track must be empty";\n'
            'var clip=source.audioClips['+str(clip_index)+'];\n'
            'if(String(clip.name).indexOf("accept_")!=0)throw "Refusing non-fixture clip";\n'
            'var oldStart=clip.startTime,oldCount=source.audioClips.length;\n'
            'var moved=target.audioClips.add(clip,clip.sourceChannelRouting);\n'
            'if(source.audioClips.length!=oldCount-1||target.audioClips.length!=1)throw "Native move failed";\n'
            'var newClip=target.audioClips[0];\n'
            'newClip.startTime='+('oldStart' if start_samples is None else str(start_samples))+';\n'
            'out("CLIP",newClip.name);out("OLD_START",oldStart);out("NEW_START",newClip.startTime);\n'
            'out("SOURCE_CLIPS",source.audioClips.length);\n'
            'out("TARGET_CLIPS",target.audioClips.length);\n'
            'out("SAVE",mt.saveDocument());\n')
        return self._run_jsx(js,'native_mt_move_clip',timeout=40)

    def native_multitrack_add_bus_qa(self,session_name:str,bus_name:str,*,confirm:bool=False):
        """Create a real native Audition bus (QA session only) with same channel layout."""
        name=self._qa_session_name(session_name)
        if not isinstance(bus_name,str) or not bus_name.startswith('QA ') or len(bus_name)>80:
            raise ValueError('QA bus label must start QA ')
        if not confirm:return {'dry_run':True,'session':name,'bus_name':bus_name}
        q=json.dumps
        js=('var mt=null;for(var i=0;i<app.documents.length;i++){var d=app.documents[i];'
            'if(d.reflect.name=="MultitrackDocument"&&d.displayName=='+q(name)+')mt=d;}\n'
            'if(!mt)throw "QA session missing";var buses=mt.audioTracks.audioBusTracks;'
            'var tracks=mt.audioTracks.audioClipTracks;\n'
            'if(!tracks.length||buses.length>32)throw "Unexpected track configuration";\n'
            'var count=buses.length;var bus=buses.add(tracks[0].audioFormat.channelLayout);\n'
            'if(buses.length!=count+1)throw "Bus creation failed";bus.name='+q(bus_name)+';\n'
            'var position=-1;for(var j=0;j<buses.length;j++){if(buses[j].id==bus.id)position=j;}\n'
            'out("BUS_NAME",bus.name);out("BUS_INDEX",position);out("BUS_ID",bus.id);\n'
            'out("BUS_COUNT",buses.length);out("SAVE",mt.saveDocument());\n')
        return self._run_jsx(js,'native_mt_add_bus',timeout=40)

    def native_multitrack_remove_bus_qa(self,session_name:str,bus_index:int,*,confirm:bool=False):
        """Remove one bus only if its label starts QA and it contains no clips."""
        name=self._qa_session_name(session_name)
        if type(bus_index)!=int or not 0<=bus_index<=32:raise ValueError('Invalid bus index')
        if not confirm:return {'dry_run':True,'session':name,'bus_index':bus_index}
        q=json.dumps
        js=('var mt=null;for(var i=0;i<app.documents.length;i++){var d=app.documents[i];'
            'if(d.reflect.name=="MultitrackDocument"&&d.displayName=='+q(name)+')mt=d;}\n'
            'if(!mt)throw "QA session missing";var buses=mt.audioTracks.audioBusTracks;\n'
            'if(buses.length<='+str(bus_index)+')throw "Bus missing";var bus=buses['+str(bus_index)+'];\n'
            'if(String(bus.name).indexOf("QA ")!=0||bus.audioClips.length)throw "Unsafe bus removal";\n'
            'var n=buses.length;out("BUS_NAME",bus.name);out("REMOVE",buses.remove(bus));\n'
            'out("BUS_COUNT",buses.length);\n'
            'if(buses.length!=n-1)throw "Bus remove failed";out("SAVE",mt.saveDocument());\n')
        return self._run_jsx(js,'native_mt_remove_bus',timeout=40)

    def native_multitrack_marker_qa(self,session_name:str,*,start_samples:int,
                                    duration_samples:int=0,label:str='QA Marker',
                                    description:str='Audition QA',
                                    confirm:bool=False):
        """Add marker to Audition multitrack session using native DOM."""
        name=self._qa_session_name(session_name)
        if type(start_samples)!=int or not 0<=start_samples<=48_000_000:
            raise ValueError('Invalid marker start')
        if type(duration_samples)!=int or not 0<=duration_samples<=48_000_000:
            raise ValueError('Invalid marker duration')
        if not isinstance(label,str) or not label.startswith('QA ') or len(label)>80:
            raise ValueError('QA marker label expected')
        if not isinstance(description,str) or len(description)>200:
            raise ValueError('Description too long')
        if not confirm:return {'dry_run':True,'session':name,'start':start_samples,'duration':duration_samples}
        q=json.dumps
        js=('var mt=null;for(var i=0;i<app.documents.length;i++){var d=app.documents[i];'
            'if(d.reflect.name=="MultitrackDocument"&&d.displayName=='+q(name)+')mt=d;}\n'
            'if(!mt)throw "QA session missing";'
            'var n=mt.markers.length;\n'
            'out("ADD",mt.addMarker('+str(start_samples)+','+str(duration_samples)+','+
              q(label)+',"Cue",'+q(description)+'));\n'
            'out("MARKERS",mt.markers.length);\n'
            'if(mt.markers.length!=n+1)throw "Marker not added";'
            'out("LAST_NAME",mt.markers[mt.markers.length-1].name);\n'
            'out("LAST_START",mt.markers[mt.markers.length-1].start);\n'
            'out("SAVE",mt.saveDocument());\n')
        return self._run_jsx(js,'native_mt_add_marker',timeout=40)

    def native_multitrack_bus_marker_inventory(self,session_name:str):
        """Read-only track, bus and marker inventory from actual Audition DOM."""
        name=self._qa_session_name(session_name)
        q=json.dumps
        js=('var mt=null;for(var i=0;i<app.documents.length;i++){var d=app.documents[i];'
            'if(d.reflect.name=="MultitrackDocument"&&d.displayName=='+q(name)+')mt=d;}\n'
            'if(!mt)throw "QA session missing";out("SESSION",mt.displayName);\n'
            'out("TRACKS",mt.audioTracks.audioClipTracks.length);\n'
            'out("BUSES",mt.audioTracks.audioBusTracks.length);\n'
            'for(var j=0;j<mt.audioTracks.audioBusTracks.length;j++){'
            'out("BUS"+j+"_NAME",mt.audioTracks.audioBusTracks[j].name);'
            'out("BUS"+j+"_ID",mt.audioTracks.audioBusTracks[j].id);}\n'
            'out("MARKERS",mt.markers.length);\n'
            'for(var k=0;k<mt.markers.length;k++){'
            'out("MARKER"+k+"_NAME",mt.markers[k].name);'
            'out("MARKER"+k+"_START",mt.markers[k].start);}\n')
        return self._run_jsx(js,'native_mt_marker_bus_list',timeout=40)
