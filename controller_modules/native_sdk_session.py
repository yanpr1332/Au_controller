"""Validated manifests for the compiled native Adobe Session SDK importer."""
from pathlib import Path
import configparser
import math
import base64


class AuditionNativeSDKSession:
    @classmethod
    def create_native_sdk_session(cls, spec, destination, *, confirm=False):
        """Create .auctl; open in Au with ControllerSessionBridge.ases installed.

        Gain points are native normalized 0..1, pan -1..1, positions are project samples.
        SDK importer creates actual Au fader keyframes and a post-fader send bus.
        """
        dst=Path(destination).resolve()
        if dst.exists() or dst.suffix.lower()!='.auctl' or not dst.parent.is_dir() or type(confirm) is not bool:
            raise ValueError('New .auctl destination and Boolean confirm required')
        if not isinstance(spec,dict) or set(spec)-{'name','sample_rate','channels','tracks'}:
            raise ValueError('Unknown session fields')
        tracks=spec.get('tracks');rate=spec.get('sample_rate',48000);channels=spec.get('channels',2)
        if type(rate) is not int or rate not in (16000,22050,32000,44100,48000,96000,192000):raise ValueError('Unsupported sample rate')
        if type(channels) is not int or channels not in (1,2,6):raise ValueError('1,2,6 session channels required')
        if not isinstance(tracks,list) or not 1<=len(tracks)<=64:raise ValueError('1..64 tracks required')
        def name(value):
            if not isinstance(value,str) or not 1<=len(value)<=200 or any(c in value for c in '\r\n\0'):raise ValueError('Invalid text field')
            return value
        def numeric(value,low,high):
            if type(value) not in (int,float) or not math.isfinite(value) or not low<=value<=high:raise ValueError('Numeric field outside bounds')
            return value
        ini=configparser.ConfigParser(interpolation=None)
        ini['session']=dict(format='AU_CONTROLLER_1',name=name(spec.get('name','Controller Session')),tracks=str(len(tracks)),rate=str(rate),channels=str(channels))
        hashes={}
        for i,track in enumerate(tracks):
            if not isinstance(track,dict) or set(track)-{'source','name','start_samples','gain','pan','send','points','effects'}:raise ValueError('Unknown track fields')
            path=Path(track['source']).resolve();name(str(path))
            sr,audio,meta=cls._read_wav(path)
            if sr!=rate or not len(audio):raise ValueError('Nonempty WAV matching session rate required')
            start=track.get('start_samples',0)
            if type(start) is not int or not 0<=start<10**12:raise ValueError('Integer start required')
            points=track.get('points',[])
            if not isinstance(points,list) or len(points)>4096:raise ValueError('At most 4096 points')
            section='track'+str(i)
            ini[section]=dict(path=str(path),name=name(track.get('name',path.stem)),frames=str(len(audio)),start=str(start),channels=str(audio.shape[1]),
                gain=str(numeric(track.get('gain',1),0,1)),pan=str(numeric(track.get('pan',0),-1,1)),send=str(numeric(track.get('send',0),0,1)),points=str(len(points)))
            previous=-1
            for j,p in enumerate(points):
                if not isinstance(p,dict) or set(p)!={'sample','value'} or type(p['sample']) is not int or not previous<p['sample']<=start+len(audio):raise ValueError('Ordered sample/value keyframes required')
                previous=p['sample'];ini[section+'_point'+str(j)]=dict(sample=str(p['sample']),value=str(numeric(p['value'],0,1)))
            effects=track.get('effects',[])
            if not isinstance(effects,list) or len(effects)>16:raise ValueError('At most 16 native effects')
            ini[section]['effects']=str(len(effects))
            for j,effect in enumerate(effects):
                if not isinstance(effect,dict) or set(effect)!={'component_id','chunk_base64'}:raise ValueError('Effect requires component_id and chunk_base64')
                component=name(effect['component_id'])
                if not isinstance(effect['chunk_base64'],str):raise ValueError('Base64 preset chunk required')
                chunk=base64.b64decode(effect['chunk_base64'],validate=True)
                if len(chunk)>2047:raise ValueError('Native SDK INI bridge accepts preset chunks up to 2047 bytes')
                ini[section+'_effect'+str(j)]=dict(component_id=component,chunk_hex=chunk.hex())
            hashes[str(path)]=cls._hash_file(path)
        if confirm:
            with dst.open('x',encoding='utf-16') as handle:ini.write(handle)
        return dict(dry_run=not confirm,output=str(dst),source_sha256=hashes,tracks=len(tracks),channels=channels,
                    backend='Adobe native Session SDK importer',native_open_verified=False)
