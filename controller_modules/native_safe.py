"""Audition 26 native ExtendScript helpers with isolated-fixture guards.

These use the real Audition DOM; never execute an arbitrary generated
JS string as an exposed public API. Tests must reside under tests/fixtures.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

class AuditionNativeSafe:
    @staticmethod
    def _native_test_paths(source:str|Path,output:str|Path)->tuple[str,str]:
        from audition_controller import ROOT
        src=Path(source).resolve()
        dst=Path(output).resolve()
        fixture=(ROOT/'tests'/'fixtures').resolve()
        acceptance=(ROOT/'tests'/'native_outputs').resolve()
        # Windows path normalization and no symlink escapes.
        if fixture not in src.parents or acceptance not in dst.parents:
            raise PermissionError('Native destructive operations confined to owned fixtures and outputs')
        if not src.is_file() or src.suffix.lower() not in ('.wav','.mp3'):
            raise ValueError('Native source must be WAV or MP3 test fixture')
        if dst.suffix.lower()!='.wav' or dst.exists() or not dst.parent.is_dir():
            raise ValueError('Native destination must be new WAV in native_outputs')
        return src.as_posix(),dst.as_posix()

    def audition_command_probe(self,commands:list[str])->dict:
        """Read-only app.isCommandEnabled for named commands; does not invoke them."""
        if not isinstance(commands,list) or len(commands)>180 or any(
           not isinstance(x,str) or len(x)>100 or not x.replace('.','').replace('_','').isalnum()
           for x in commands):
            raise ValueError('Invalid Audition command names')
        arr=json.dumps(commands,ensure_ascii=False)
        return self._run_jsx('var commands='+arr+';\n'
            'for(var i=0;i<commands.length;i++){\n'
            ' try{out("CMD_"+commands[i],app.isCommandEnabled(commands[i]));}\n'
            ' catch(e){out("ERR_"+commands[i],e);}\n'
            '}',name='safe_command_probe',timeout=45)

    def audition_reflect(self,object_name:str='application')->dict:
        """Read-only ExtendScript reflection of known Audition objects."""
        choices={'application':'app','transport':'app.transport',
                 'active':'app.activeDocument','documents':'app.documents',
                 'local_preferences':'app.localPreferences'}
        if object_name not in choices:raise ValueError('Unsupported reflection object')
        expression=choices[object_name]
        body=('var object='+expression+';\n'
          'if(!object){out("NOT_AVAILABLE","true");}\n'
          'else{var refl=object.reflect,pr=[],me=[];\n'
          ' for(var i=0;i<refl.properties.length;i++)pr.push(String(refl.properties[i].name));\n'
          ' for(var j=0;j<refl.methods.length;j++)me.push(String(refl.methods[j].name));\n'
          ' out("CLASS",refl.name);out("PROPERTIES",pr.join("|"));out("METHODS",me.join("|"));}\n')
        return self._run_jsx(body,name='safe_reflect',timeout=35)

    def audition_native_marker_export(self,source:str|Path,output:str|Path,*,start_samples:int,
                                      duration_samples:int=0,name:str='QA Marker',
                                      confirm:bool=False)->dict:
        """Open only test fixture, add native marker, export to new WAV, close test document."""
        source,output=self._native_test_paths(source,output)
        if type(start_samples)!=int or type(duration_samples)!=int or start_samples<0 or duration_samples<0:
            raise ValueError('Nonnegative sample positions required')
        if len(name)>100:raise ValueError('Marker name too long')
        if not confirm:return {'dry_run':True,'source':source,'output':output}
        q=json.dumps
        body=('var doc=app.openDocument(new DocumentOpenParameter('+q(source)+'));\n'
              'if(!doc||String(doc.path)!='+q(source)+')throw "Fixture open failed";\n'
              'try{\n'
              ' out("MARKER_RESULT",doc.addMarker('+str(start_samples)+','+
              str(duration_samples)+','+q(name)+',"Cue","QA marker"));\n'
              ' out("MARKERS_COUNT",doc.markers.length);\n'
              ' out("SAVE",doc.saveAs('+q(output)+',true));\n'
              ' $.sleep(300);\n'
              ' out("EXISTS",new File('+q(output)+').exists);\n'
              '}finally{doc.closeDocument();}\n')
        r=self._run_jsx(body,name='safe_native_marker',timeout=40)
        return {'response':r,'output':output,'exists':Path(output).is_file(),
                'native_operation':True}

    def audition_native_favorite_export(self,source:str|Path,output:str|Path,*,favorite:str,
                                        confirm:bool=False)->dict:
        """Run a known Audition Favorite on only an isolated test WAV."""
        source,output=self._native_test_paths(source,output)
        # Favorites are user-configurable, so avoid arbitrary titles and require allowlist.
        allowed={'Normalize to -3 dB','Normalize to -0.1 dB','DeNoise','DeReverb',
                 'Remove 60 Hz Hum','Repair DC Offset'}
        if favorite not in allowed:raise ValueError('Favorite must be in explicit verified allowlist')
        if not confirm:return {'dry_run':True,'favorite':favorite,'source':source,'output':output}
        q=json.dumps
        body=('var doc=app.openDocument(new DocumentOpenParameter('+q(source)+'));\n'
              'if(!doc||String(doc.path)!='+q(source)+')throw "Fixture open failed";\n'
              'try{\n'
              ' out("FAVORITE_RESULT",doc.applyFavorite('+q(favorite)+'));\n'
              ' var i=0; while(doc.isBusy && i<900){$.sleep(50);i++;}\n'
              ' out("BUSY",doc.isBusy);\n'
              ' out("SAVE",doc.saveAs('+q(output)+',true));\n'
              ' $.sleep(250);out("EXISTS",new File('+q(output)+').exists);\n'
              '}finally{doc.closeDocument();}\n')
        r=self._run_jsx(body,name='safe_native_favorite',timeout=75)
        return {'response':r,'output':output,'exists':Path(output).is_file(),
                'native_operation':True,'favorite':favorite}

    def audition_native_resample_export(self,source:str|Path,output:str|Path,*,
                                        sample_rate:int=44100,bit_depth:int=24,
                                        confirm:bool=False)->dict:
        """Perform a real Audition SampleTypeConvertParameters save on test-only audio."""
        source,output=self._native_test_paths(source,output)
        if type(sample_rate)!=int or sample_rate not in (16000,22050,32000,44100,48000,96000):
            raise ValueError('Supported sample rate required')
        if type(bit_depth)!=int or bit_depth not in (16,24,32):
            raise ValueError('Bit depth 16, 24 or 32 required')
        if not confirm:return {'dry_run':True,'source':source,'output':output}
        q=json.dumps
        body=('var doc=app.openDocument(new DocumentOpenParameter('+q(source)+'));\n'
          'if(!doc||String(doc.path)!='+q(source)+')throw "Fixture open failed";\n'
          'try{\n'
          ' var sp=new WaveDocumentSaveAsParameters();\n'
          ' var cv=new SampleTypeConvertParameters();\n'
          ' cv.sampleRate='+str(sample_rate)+';\n'
          ' cv.bitDepth='+str(bit_depth)+';\n'
          ' cv.useDithering=false;\n'
          ' cv.resampleQuality=100;\n'
          ' sp.sampleTypeConversion=cv;\n'
          ' var r=doc.saveAsDocument('+q(output)+',sp);\n'
          ' out("INVALID_SETTINGS",r.invalidSettings);\n'
          ' out("INVALID_SAMPLE_TYPE",r.invalidSampleType);\n'
          ' out("INTERNAL_ERROR",r.internal);\n'
          ' $.sleep(300);out("EXISTS",new File('+q(output)+').exists);\n'
          '}finally{doc.closeDocument();}\n')
        r=self._run_jsx(body,'safe_native_resample',timeout=50)
        return {'response':r,'exists':Path(output).is_file(),
                'output':output,'sample_rate':sample_rate,'bit_depth':bit_depth,
                'native_operation':True}
