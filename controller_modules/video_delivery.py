"""Source-preserving offline video/audio muxing via WSL FFmpeg.

This is a delivery helper, not a Premiere or Audition native roundtrip.
"""
from pathlib import Path
import math
import os
import tempfile
import subprocess
import json


class AuditionVideoDelivery:
    @classmethod
    def _video_stream_times(cls,path):
        result=subprocess.run(['wsl.exe','-d','Debian','--','/usr/bin/ffprobe','-v','error',
            '-show_entries','stream=codec_type,start_time','-of','json',cls._wsl_path(path)],
            capture_output=True,text=True,errors='replace',timeout=25)
        if result.returncode:raise RuntimeError('Unable to inspect media timestamps')
        return json.loads(result.stdout).get('streams',[])

    @classmethod
    def mux_video_audio(cls, video, audio, destination, *, offset_seconds=0.0, bitrate_kbps=192, shortest=True, confirm=False):
        video,audio,destination=Path(video).resolve(),Path(audio).resolve(),Path(destination).resolve()
        if not video.is_file() or video.suffix.lower() not in ('.mp4','.mov','.m4v'):
            raise ValueError('Existing MP4/MOV video required')
        if not audio.is_file() or audio.suffix.lower() not in ('.wav','.flac','.mp3','.m4a','.ogg','.opus'):
            raise ValueError('Existing supported audio required')
        if destination in (video,audio) or destination.exists() or destination.suffix.lower() not in ('.mp4','.mov') or not destination.parent.is_dir():
            raise ValueError('New MP4/MOV destination required')
        if type(offset_seconds) not in (int,float) or not math.isfinite(offset_seconds) or not -600<=offset_seconds<=600:
            raise ValueError('Finite audio offset in -600..600 seconds required')
        if type(bitrate_kbps) is not int or bitrate_kbps not in (96,128,160,192,256,320) or type(shortest) is not bool or type(confirm) is not bool:
            raise ValueError('Invalid bitrate or flags')
        if not confirm:
            return dict(dry_run=True,video=str(video),audio=str(audio),destination=str(destination),offset_seconds=offset_seconds,
                        backend='WSL FFmpeg',native_audition_export=False,premiere_roundtrip_verified=False)
        hashes={str(path):cls._hash_file(path) for path in (video,audio)}
        video_streams=cls._video_stream_times(video);audio_streams=cls._video_stream_times(audio)
        def first_start(streams,kind):
            item=next((s for s in streams if s.get('codec_type')==kind),None)
            if item is None:raise ValueError('Missing '+kind+' source stream')
            value=item.get('start_time')
            return float(value) if value not in (None,'N/A') else 0.0
        expected_offset=first_start(audio_streams,'audio')-first_start(video_streams,'video')+float(offset_seconds)
        with tempfile.TemporaryDirectory(prefix='.au_video_',dir=destination.parent) as directory:
            stage=Path(directory)/destination.name
            cmd=['wsl.exe','-d','Debian','--','/usr/bin/ffmpeg','-nostdin','-hide_banner','-loglevel','error','-n',
                 '-i',cls._wsl_path(video),'-itsoffset',str(float(offset_seconds)),'-i',cls._wsl_path(audio),
                 '-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a',str(bitrate_kbps)+'k']
            if shortest:cmd.append('-shortest')
            cmd.append(cls._wsl_path(stage))
            process=subprocess.run(cmd,capture_output=True,text=True,errors='replace',timeout=600)
            if process.returncode or not stage.is_file() or not stage.stat().st_size:
                raise RuntimeError('FFmpeg video delivery failed: '+process.stderr[-500:])
            probe=cls.ffprobe_media(stage)
            streams=probe.get('streams',[])
            if len([s for s in streams if s.get('codec_type')=='video'])!=1 or len([s for s in streams if s.get('codec_type')=='audio'])!=1:
                raise RuntimeError('Expected one video and one audio stream')
            output_times=cls._video_stream_times(stage)
            actual_offset=first_start(output_times,'audio')-first_start(output_times,'video')
            if abs(actual_offset-expected_offset)>.06:
                raise RuntimeError('Output timestamps do not match requested audio offset')
            if any(cls._hash_file(p)!=hashes[str(p)] for p in (video,audio)):
                raise RuntimeError('Source changed during video delivery')
            digest=cls._hash_file(stage)
            os.link(stage,destination)
            try:
                if cls._hash_file(destination)!=digest:raise RuntimeError('Published video hash mismatch')
            except Exception:
                destination.unlink(missing_ok=True);raise
        return dict(output=str(destination),sha256=digest,source_sha256=hashes,offset_seconds=offset_seconds,
                    expected_relative_start_seconds=expected_offset,measured_relative_start_seconds=actual_offset,
                    streams=streams,backend='WSL FFmpeg',native_audition_export=False,premiere_roundtrip_verified=False)
