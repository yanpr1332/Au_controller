"""Actual Au Favorite processing on private copies of production WAVs."""
from pathlib import Path
import json
import os
import shutil
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from scipy.io import wavfile
from controller_modules.host_lock import audition_host_lock


@contextmanager
def _private_input_stage(root):
    root=Path(root).resolve()
    directory=Path(tempfile.mkdtemp(prefix='favorite_input_',dir=root)).resolve()
    try:
        yield str(directory)
    except Exception as exc:
        exc.add_note('Owned native input retained at '+str(directory))
        raise
    else:
        if directory.parent!=root or not directory.name.startswith('favorite_input_'):
            raise RuntimeError('Unexpected cleanup path')
        shutil.rmtree(directory)


class AuditionNativeFavoriteProduction:
    @classmethod
    def native_favorite_inventory(cls):
        path=Path(os.environ['APPDATA'])/'Adobe/Audition/26.0/Favorites.xml'
        root=ET.parse(path).getroot();favorites=[]
        container=next(p.find('prop.list') for p in root.findall('.//prop.pair') if p.findtext('key')=='Favorites')
        for row in container.findall('prop.pair'):
            name=row.findtext('key');action=None
            kind=next((r.findtext('ustring') for r in row.findall('./prop.list/prop.pair') if r.findtext('key')=='Type'),None)
            for child in row.findall('.//prop.pair'):
                if child.findtext('key')=='ActionID':action=child.findtext('ustring')
            favorites.append(dict(name=name,action_id=action,supported_copy_processing=kind=='BatchActionFavorite' and action in ('AudioComponent','Normalize'),requires_explicit_selection=action=='AutoHeal'))
        return dict(profile=str(path),favorites=favorites,host_execution_verified=False)

    def native_apply_favorite_copy(self,source,destination,*,favorite,timeout=120,confirm=False):
        from audition_controller import ROOT
        src,dst=Path(source).resolve(),Path(destination).resolve()
        if not src.is_file() or src.suffix.lower()!='.wav' or dst.exists() or dst==src or dst.suffix.lower()!='.wav' or not dst.parent.is_dir():raise ValueError('Existing WAV source and new WAV destination required')
        if type(confirm) is not bool or type(timeout) not in (int,float) or not 1<=timeout<=600:raise ValueError('Invalid confirmation/timeout')
        names={r['name'] for r in self.native_favorite_inventory()['favorites'] if r['supported_copy_processing']}
        if favorite not in names:raise ValueError('Favorite must be an installed single audio processing action')
        before=self._hash_file(src)
        if not confirm:return dict(dry_run=True,source=str(src),output=str(dst),favorite=favorite)
        staged=dst.parent/('.au_favorite_'+uuid.uuid4().hex+'.wav')
        started=time.monotonic();created=False
        with _private_input_stage(ROOT/'_runtime') as directory:
            copied=Path(directory)/('accept_'+src.name);shutil.copy2(src,copied)
            with audition_host_lock(ROOT/'_runtime/locks',timeout):
                body='''
var d=app.openDocument(new DocumentOpenParameter(INPUT));
if(!d||d.reflect.name!="WaveDocument")throw "Private WAV did not open";
d.activate();app.invokeCommand("Edit.SelectAll");
out("FAVORITE",d.applyFavorite(FAVORITE_NAME));
'''.replace('INPUT',json.dumps(copied.as_posix())).replace('FAVORITE_NAME',json.dumps(favorite))
                result=self._run_jsx_unlocked(body,'production_favorite_apply',timeout)
                if result.get('FAVORITE')!='true':
                    raise RuntimeError('Au did not accept the Favorite: '+str(result))
                while time.monotonic()-started<timeout:
                    body='''
var owned=null;
for(var i=0;i<app.documents.length;i++){var d=app.documents[i],p=new File(String(d.path)).fsName.toLowerCase();if(p==new File(INPUT).fsName.toLowerCase()||p==new File(OUTPUT).fsName.toLowerCase())owned=d;}
if(!owned)throw "Owned Favorite document missing";
if(owned.isBusy)out("WAIT",true);
else if(new File(String(owned.path)).fsName.toLowerCase()==new File(INPUT).fsName.toLowerCase()){owned.activate();out("SAVE",owned.saveAs(OUTPUT,false));}
else {owned.activate();out("CLOSED",owned.closeDocument());}
'''.replace('INPUT',json.dumps(copied.as_posix())).replace('OUTPUT',json.dumps(staged.as_posix()))
                    state=self._run_jsx_unlocked(body,'production_favorite_finish',max(.1,timeout-(time.monotonic()-started)))
                    if state.get('CLOSED')=='true':break
                    time.sleep(.1)
                else:raise TimeoutError('Favorite completion not observed; inspect owned QA document')
            try:
                rate,audio=wavfile.read(staged)
                if not len(audio) or self._hash_file(src)!=before:raise RuntimeError('Empty output or source changed')
                digest=self._hash_file(staged)
                with dst.open('xb') as handle:
                    created=True
                    with staged.open('rb') as inp:shutil.copyfileobj(inp,handle)
                if self._hash_file(dst)!=digest:raise RuntimeError('Published output hash mismatch')
                return dict(output=str(dst),sha256=digest,source_sha256=before,frames=len(audio),sample_rate=rate,native_audition_favorite=True,favorite=favorite)
            except Exception:
                if created:dst.unlink(missing_ok=True)
                raise
            finally:
                try:staged.unlink(missing_ok=True)
                except OSError:pass
