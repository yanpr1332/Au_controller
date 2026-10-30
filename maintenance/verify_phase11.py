"""Current software regression and scoped, real-host evidence verification."""
from pathlib import Path
import sys,io,json,ast,unittest,tempfile,inspect
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from audition_controller import AuditionController as C

def check(*,full_tests=False,sdk=False):
    receipts=ROOT/'tests/receipts'
    def read(name):return json.loads((receipts/name).read_text(encoding='utf8'))
    imported=read('phase11_native_20261030T015310.json')
    automation=read('phase11_automation_20261030T020936.json')
    rack=read('phase11_rack_20261030T021617.json')
    surround=read('phase11_rack_surround_20261030T022213.json')
    relocation=read('phase11_relocation_20261030T021109.json')
    favorite=read('phase11_native_favorite_ACCEPT_AU_Favorite_20261030T022612.json')
    microphone=read('phase11_microphone_20261030T023932.json')
    methods={name for name in dir(C) if not name.startswith('_') and callable(getattr(C,name))}
    baseline=json.loads((ROOT/'api/Audition_26_runtime_api.json').read_text(encoding='utf8'))
    checks=dict(original_96_methods_retained={r['method'] for r in baseline['controller_methods']}<=methods,
                syntax_valid=all(ast.parse(p.read_text(encoding='utf8')) is not None for p in [ROOT/'audition_controller.py',*(ROOT/'controller_modules').glob('*.py'),*(ROOT/'maintenance').glob('*.py')]),
                native_import_track_readback=imported['native_import_snapshot']['TRACKS']=='7',
                native_pan_left=automation['pan_left_isolated'],native_pan_right=automation['pan_right_isolated'],
                native_envelope=automation['envelope_changes_level'],native_send=automation['send_changes_level'],
                native_rack=rack['passed'],native_rack_preset=surround['preset_hum_to_tone_ratio']<.05,
                native_51_output=surround['passed'] and surround['surround_channels']==6,
                native_relocated_reopen=relocation['passed'],native_favorite=favorite['passed'],
                native_microphone=microphone['passed'] and microphone['audio_readback']['frames']>0,
                session_sdk_binary=(ROOT/'sdk/session_bridge/build/ControllerSessionBridge.ases').is_file(),
                amio_sample_binary=(ROOT/'sdk/AMIO_8.1x160/Amio/Windows Sample/AmioApe/Release/64/AmioApe.dll').is_file())
    outputs=[]
    def verify_outputs(obj):
        if isinstance(obj,dict):
            path=obj.get('output');digest=obj.get('sha256',obj.get('output_sha256'))
            if isinstance(path,str) and isinstance(digest,str):
                outputs.append(dict(path=path,valid=Path(path).is_file() and C._hash_file(path)==digest))
            for value in obj.values():verify_outputs(value)
        elif isinstance(obj,list):
            for value in obj:verify_outputs(value)
    for record in (imported,automation,rack,surround,relocation,favorite):verify_outputs(record)
    checks['native_output_hashes']=bool(outputs) and all(row['valid'] for row in outputs)
    count=None;errors=[]
    if full_tests:
        tempfile.tempdir=str(ROOT/'_runtime')
        result=unittest.TextTestRunner(stream=io.StringIO(),verbosity=0).run(unittest.defaultTestLoader.discover(str(ROOT/'tests')))
        count=result.testsRun;checks['full_regression']=result.wasSuccessful()
        errors=[dict(test=str(test),detail=detail) for test,detail in result.errors+result.failures]
    host=None
    if sdk:
        host=C().status();checks['live_host_26']=host.get('VERSION')=='26.0.0';checks['live_host_empty']=host.get('DOCUMENTS')=='0'
    report=dict(phase=11,passed=all(checks.values()),checks=checks,tests=count,public_methods=len(methods),
                verified_outputs=len(outputs),host=host,errors=errors,
                all_requested_development_complete=False,
                remaining=['CEP host panel/runtime','spectral brush/lasso GUI and locally selected Auto Heal',
                           'OMF GUI export and Premiere/video roundtrip','AAF native export unsupported by documented host routes',
                           'ASIO hardware/driver and MIDI control surface','certificate signing and distribution'],
                scope='Software regression plus explicitly evidenced native test cases; not a claim of all Au features')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    target=receipts/('phase11_verification_'+stamp+'.json')
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k!='errors'},ensure_ascii=False,indent=2));print('RECEIPT',target)
    if not report['passed']:raise SystemExit(1)
    return report

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--full-tests',action='store_true');parser.add_argument('--sdk',action='store_true');args=parser.parse_args()
    check(full_tests=args.full_tests,sdk=args.sdk)
