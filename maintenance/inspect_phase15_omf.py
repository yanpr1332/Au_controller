"""Read-only evidence for the GUI-exported QA OMF; no export or overwrite."""
from pathlib import Path
import hashlib
import json
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from audition_controller import AuditionController

if __name__ == '__main__':
    path = ROOT / 'tests/native_outputs/ACCEPT_AU_Phase06_multi_arrangement.omf'
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    evidence = {'path': str(path), 'bytes': path.stat().st_size,
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'gui_export_observed': True, 'roundtrip_verified': False,
                'format_warnings': ['Bus tracks ignored', 'Track EQ ignored', 'Empty tracks skipped']}
    c = AuditionController()
    try:
        evidence['host_file_visibility'] = c._run_jsx(
            'var f=new File(' + json.dumps(path.as_posix()) + ');'
            'out("EXISTS",f.exists);out("SIZE",f.length);', 'omf_visibility', 15)
        evidence['host'] = c.status()
    except Exception as exc:
        evidence['error'] = repr(exc)
    receipt = ROOT / 'tests/receipts' / ('phase15_omf_inspection_' + stamp + '.json')
    with receipt.open('x', encoding='utf8') as stream:
        json.dump(evidence, stream, ensure_ascii=False, indent=2)
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    print(receipt)
