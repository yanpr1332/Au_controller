"""Actual Au reopen/mixdown after old absolute media paths become unavailable."""
from pathlib import Path
import sys,json,shutil
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from audition_controller import AuditionController as C

if __name__=='__main__':
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    folder=(ROOT/'tests/native_outputs'/('ACCEPT_AU_Relocation_'+stamp)).resolve();folder.mkdir()
    source=ROOT/'tests/native_outputs/ACCEPT_AU_SDK_20261030T020334/ACCEPT_AU_SDK_Native.sesx'
    original=folder/'original_package';moved=folder/'moved_package';hidden=folder/'original_temporarily_unavailable'
    for path in (original,moved,hidden):
        if path.resolve().parent!=folder:raise RuntimeError('Unsafe QA relocation path')
    c=C();result={'package':C.package_production_session(source,original,confirm=True)}
    shutil.copytree(original,moved)
    original.rename(hidden)
    receipt=ROOT/'tests/receipts'/('phase11_relocation_'+stamp+'.json')
    try:
        result['original_absolute_paths_unavailable']=not original.exists()
        result['open']=c.open_document(str(moved/'session.sesx'))
        result['render']=c.mixdown_production_session(moved/'session.sesx',folder/'relocated_native_mix.wav',confirm=True)
        result['passed']=result['original_absolute_paths_unavailable'] and result['render']['frames']>0
    finally:
        hidden.rename(original)
        receipt.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
        print(json.dumps(result,ensure_ascii=False,indent=2));print('RECEIPT',receipt)
