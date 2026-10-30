"""Read-only probe and bounded transcoding via WSL Debian FFmpeg/FFprobe.

These functions DO NOT drive native Audition export. They produce independently
validated media, without overwriting sources or existing outputs.
"""
from __future__ import annotations
import json,math,os,subprocess
from pathlib import Path,PureWindowsPath

class AuditionFFmpegLab:
    FORMATS={'wav':('pcm_s16le','pcm_s16le'),'flac':('flac','flac'),
             'mp3':('libmp3lame','mp3'),'m4a':('aac','aac'),
             'ogg':('libvorbis','vorbis'),'opus':('libopus','opus')}
    @staticmethod
    def _wsl_path(path:str|Path)->str:
        p=Path(path).resolve()
        if not p.is_absolute():raise ValueError('Absolute path required')
        pure=PureWindowsPath(str(p))
        if len(pure.drive)!=2 or pure.drive[1]!=':':raise ValueError('Local drive letter required')
        if any('\r' in x or '\n' in x for x in pure.parts):raise ValueError('Invalid path component')
        return '/mnt/'+pure.drive[0].lower()+'/'+'/'.join(pure.parts[1:])

    @classmethod
    def ffmpeg_environment(cls)->dict:
        results={}
        for name in ('ffmpeg','ffprobe'):
            result=subprocess.run(['wsl.exe','-d','Debian','--','/usr/bin/'+name,'-version'],
                capture_output=True,text=True,errors='replace',timeout=18)
            results[name]={'available':result.returncode==0,
                           'binary':'/usr/bin/'+name,
                           'version':result.stdout.splitlines()[0] if result.stdout else ''}
        return {'backend':'WSL Debian','all_available':all(x['available'] for x in results.values()),
                'programs':results}

    @classmethod
    def ffprobe_media(cls,path:str|Path)->dict:
        p=Path(path)
        if not p.is_file():raise FileNotFoundError(path)
        proc=subprocess.run(['wsl.exe','-d','Debian','--','/usr/bin/ffprobe','-v','error',
            '-show_entries','format=duration,size,format_name:stream=codec_name,codec_type,sample_rate,channels',
            '-of','json',cls._wsl_path(p)],capture_output=True,text=True,errors='replace',timeout=25)
        if proc.returncode:raise RuntimeError('ffprobe failed: '+proc.stderr[-350:])
        return json.loads(proc.stdout)

    @classmethod
    def transcode_audio(cls,source:str|Path,destination:str|Path,*,rate:int=48000,
                        channels:int=2,bitrate_kbps:int=192,confirm:bool=False)->dict:
        src=Path(source).resolve();dst=Path(destination).resolve()
        if not src.is_file() or src==dst or dst.exists() or not dst.parent.is_dir():
            raise ValueError('Source must exist and destination must be new')
        fmt=dst.suffix.lower().lstrip('.')
        if fmt not in cls.FORMATS:raise ValueError('Unsupported output type')
        if type(rate)!=int or rate not in (16000,22050,32000,44100,48000,96000):
            raise ValueError('Unsupported sample rate')
        if type(channels)!=int or channels not in (1,2):raise ValueError('Mono or stereo')
        if type(bitrate_kbps)!=int or bitrate_kbps not in (64,96,128,160,192,256,320):
            raise ValueError('Bitrate must be accepted preset')
        codec,expected=cls.FORMATS[fmt]
        if not confirm:return {'dry_run':True,'backend':'Debian WSL FFmpeg','source':str(src),
                               'destination':str(dst),'codec':codec}
        cmd=['wsl.exe','-d','Debian','--','/usr/bin/ffmpeg','-nostdin','-hide_banner',
             '-loglevel','error','-n','-i',cls._wsl_path(src),'-vn',
             '-ar',str(rate),'-ac',str(channels),'-c:a',codec]
        if fmt in ('mp3','m4a','ogg','opus'):cmd+=['-b:a',str(bitrate_kbps)+'k']
        cmd+=[cls._wsl_path(dst)]
        result=subprocess.run(cmd,capture_output=True,text=True,errors='replace',timeout=90)
        if result.returncode or not dst.is_file() or dst.stat().st_size<100:
            raise RuntimeError('Transcode failed: '+result.stderr[-400:])
        probe=cls.ffprobe_media(dst)
        streams=[x for x in probe.get('streams',[]) if x.get('codec_type')=='audio']
        if len(streams)!=1 or streams[0].get('codec_name')!=expected or int(streams[0].get('sample_rate',0))!=rate:
            raise RuntimeError('Output codec/sample-rate mismatch')
        if int(streams[0].get('channels',0))!=channels:
            raise RuntimeError('Output channel-count mismatch')
        import hashlib
        return {'backend':'Debian WSL FFmpeg','path':str(dst),
                'source':str(src),'bytes':dst.stat().st_size,
                'sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),
                'codec':streams[0]['codec_name'],'sample_rate':rate,'channels':channels,
                'duration':float(probe.get('format',{}).get('duration','0')),'native_audition_export':False}
