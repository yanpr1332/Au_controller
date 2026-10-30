"""Metadata tagging through Debian FFmpeg with actual ffprobe roundtrip.

This copies compressed packets when source/output container type is unchanged
and never modifies source files. WAV BEXT is optional, MP3 uses ID3v2.3.
It does NOT claim Audition's internal Metadata panel can be automated.
"""
from __future__ import annotations
import hashlib,re,json
from pathlib import Path
class AuditionMetadataDelivery:
    _tag_names=frozenset({'title','artist','album','comment','date','genre','copyright',
                          'description','publisher','track'})
    @classmethod
    def tag_delivery_audio(cls,source,destination,tags:dict,*,bwf=False,confirm=False):
        src=cls._qa_input(source)
        dest=cls._qa_output(src,destination,
             suffixes=('.wav','.flac','.mp3','.m4a'))
        if src.suffix.lower()!=dest.suffix.lower():
            raise ValueError('Metadata-only delivery must preserve source container')
        if type(bwf)!=bool or (bwf and dest.suffix.lower()!='.wav'):
            raise ValueError('BWF metadata only supported for WAV')
        if not isinstance(tags,dict) or not 1<=len(tags)<=10:
            raise ValueError('1..10 metadata key/value pairs')
        for key,value in tags.items():
            if key not in cls._tag_names or not isinstance(value,str) or not value.strip() or len(value)>250:
                raise ValueError('Unsupported/empty/oversized metadata value')
            if any(ord(c)<32 for c in value):
                raise ValueError('Control characters are not allowed in metadata')
        if not confirm:return {'dry_run':True,'source':str(src),'destination':str(dest),
                                'tags':tags,'bwf':bwf}
        source_hash=hashlib.sha256(src.read_bytes()).hexdigest()
        args=['wsl.exe','-d','Debian','--exec','/usr/bin/ffmpeg','-hide_banner',
              '-loglevel','error','-nostdin','-n','-i',cls._wsl_path(src),
              '-map','0:a:0','-c:a','copy','-map_metadata','-1']
        for key,value in tags.items():
            args+=['-metadata',key+'='+value]
        if dest.suffix.lower()=='.wav' and bwf:
            args+=['-write_bext','1']
        if dest.suffix.lower()=='.mp3':
            args+=['-id3v2_version','3']
        args.append(cls._wsl_path(dest))
        try:
            cls._run(args,90)
            if not dest.is_file():raise RuntimeError('No tagged output')
            probe_cmd=['wsl.exe','-d','Debian','--exec','/usr/bin/ffprobe',
                       '-v','error','-show_format','-show_streams','-of','json',cls._wsl_path(dest)]
            verify=json.loads(cls._run(probe_cmd,40).stdout)
            actual={str(k).casefold():str(v) for k,v in verify.get('format',{}).get('tags',{}).items()}
            # The WAV BEXT description field is surfaced as comment by FFprobe.
            def lookup(name):
                key='comment' if bwf and name=='description' else name
                return actual.get(key)
            present={name:lookup(name) for name in tags}
            matches={name:(present[name]==val) for name,val in tags.items()}
            if not all(matches.values()):
                raise RuntimeError('Metadata readback mismatched: '+str(matches))
            if hashlib.sha256(src.read_bytes()).hexdigest()!=source_hash:
                raise RuntimeError('Original media was modified')
            return {'source':str(src),'output':str(dest),'passed':True,'bwf':bwf,
                    'source_sha256':source_hash,
                    'output_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),
                    'codec':verify['streams'][0]['codec_name'],
                    'metadata_readback':present,'metadata_checks':matches,
                    'backend':'Debian FFmpeg, not native Audition metadata panel'}
        except Exception:
            if dest.is_file():dest.unlink()
            raise
