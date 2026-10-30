"""Real FFmpeg sidechain dialog-over-music production and mastering receipts.
External Debian FFmpeg effect; never represented as an Audition native DSP effect.
Inputs remain immutable; outputs must not exist, and only WAV files are emitted.
"""
from __future__ import annotations
from pathlib import Path
import hashlib,math,json,tempfile
class AuditionPodcastAutomation:
    @classmethod
    def duck_music_under_dialogue(cls,dialogue,background,destination,*,
            music_gain_db=-9.0,voice_gain_db=0.0,
            threshold=0.025,ratio=8.0,attack_ms=15,release_ms=300,
            confirm=False):
        source=cls._qa_input(dialogue)
        music=cls._qa_input(background)
        dst=cls._qa_output(source,destination,suffixes=('.wav',))
        if len({source,music,dst})!=3:raise ValueError('All three paths must differ')
        mg=cls._f(music_gain_db,-50,6,'music gain')
        vg=cls._f(voice_gain_db,-24,12,'voice gain')
        t=cls._f(threshold,0.001,0.5,'duck threshold')
        r=cls._f(ratio,1.01,20,'duck ratio')
        a=cls._f(attack_ms,1,250,'attack milliseconds')
        rel=cls._f(release_ms,20,4000,'release milliseconds')
        graph=(f'[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,'
               f'volume={10**(mg/20):.8f}[bg];'
               f'[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,'
               f'volume={10**(vg/20):.8f},asplit=2[side][spoken];'
               f'[bg][side]sidechaincompress=threshold={t:.6f}:ratio={r:.5f}:'
               f'attack={a:.2f}:release={rel:.2f}[ducked];'
               f'[ducked][spoken]amix=inputs=2:duration=longest:normalize=0,'
               f'alimiter=limit=0.88:level=0[out]')
        if not confirm:
            return {'dry_run':True,'dialogue':str(source),'music':str(music),'output':str(dst),
                    'filter_graph':graph}
        sha={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (source,music)}
        cmd=['wsl.exe','-d','Debian','--exec','/usr/bin/ffmpeg','-hide_banner',
             '-nostdin','-loglevel','error','-n','-i',cls._wsl_path(music),
             '-i',cls._wsl_path(source),'-filter_complex',graph,
             '-map','[out]','-ar','48000','-c:a','pcm_f32le',cls._wsl_path(dst)]
        cls._run(cmd,120)
        probe=cls.ffprobe_media(dst)
        analysis=cls.audio_forensics(dst)
        input_preserved=all(hashlib.sha256(Path(s).read_bytes()).hexdigest()==h for s,h in sha.items())
        qa=analysis['peak_dbfs']<=0.001 and analysis['integer_or_float_clipping_samples']==0
        return {'backend':'Debian FFmpeg sidechaincompress+amix+alimiter',
                'native_audition_effect':False,'source_unchanged':input_preserved,
                'audio_quality_ok':qa,'codec':probe['streams'][0]['codec_name'],
                'channels':probe['streams'][0]['channels'],
                'sample_rate':probe['streams'][0]['sample_rate'],
                'duration':float(probe['format']['duration']),
                'peak_dbfs':analysis['peak_dbfs'],'output':str(dst),
                'sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),
                'settings':{'music_gain_db':mg,'voice_gain_db':vg,'threshold':t,
                            'ratio':r,'attack_ms':a,'release_ms':rel}}

    @classmethod
    def podcast_sidechain_delivery(cls,dialogue,music,destination,*,
       target_lufs=-16,ceiling_dbtp=-1.5,confirm=False):
        voice=cls._qa_input(dialogue)
        bg=cls._qa_input(music)
        dst=cls._qa_output(voice,destination,suffixes=('.wav','.mp3','.flac','.m4a'))
        if dst in (voice,bg):raise ValueError('Output collides with an input')
        if not confirm:return {'dry_run':True,'destination':str(dst),
                              'target_lufs':target_lufs}
        with tempfile.TemporaryDirectory(prefix='audition_duck_master_',dir=str(dst.parent)) as working:
            pre=Path(working)/'sidechain_mix.wav'
            duck=cls.duck_music_under_dialogue(voice,bg,pre,confirm=True)
            if not duck['audio_quality_ok'] or not duck['source_unchanged']:
                raise RuntimeError('Sidechain mix rejected by QC')
            master=cls.master_loudness(pre,dst,target_lufs=target_lufs,
                                       ceiling_dbtp=ceiling_dbtp,confirm=True)
            if not master['qa_passed']:raise RuntimeError('Mastered output loudness QC failure')
        return {'output':str(dst),'ducking':duck,'mastering':master,
                'passed':True,'native_audition_effect':False}
