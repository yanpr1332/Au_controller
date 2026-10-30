"""Development evidence only. Does not promote native/SDK/hardware capabilities."""
from pathlib import Path
import sys
import io
import ast
import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from audition_controller import AuditionController as C

if __name__ == '__main__':
    tempfile.tempdir = str(ROOT / '_runtime')
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)
    methods = {name for name in dir(C) if not name.startswith('_') and callable(getattr(C, name))}
    baseline = json.loads((ROOT/'api/Audition_26_runtime_api.json').read_text(encoding='utf8'))
    syntax = all(ast.parse(p.read_text(encoding='utf8')) is not None for p in
                 [ROOT/'audition_controller.py', *(ROOT/'controller_modules').glob('*.py')])
    receipt = dict(timestamp=datetime.now(timezone(timedelta(hours=8))).isoformat(),
                   status='development; native and external dependencies not accepted',
                   tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                   passed=result.wasSuccessful(), syntax_valid=syntax,
                   baseline_methods_preserved={x['method'] for x in baseline['controller_methods']} <= methods,
                   public_methods=len(methods),
                   new_methods=sorted(methods-{x['method'] for x in baseline['controller_methods']}),
                   error_details=[dict(test=str(test), detail=detail) for test, detail in result.errors+result.failures],
                   native_live_acceptance=False, sdk_hardware_acceptance=False)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    output = ROOT/'tests/receipts'/('phase10_development_'+stamp+'.json')
    with output.open('x', encoding='utf8') as handle:
        json.dump(receipt, handle, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in receipt.items() if k != 'error_details'}, ensure_ascii=False, indent=2))
    print('RECEIPT', output)
    sys.exit(0 if result.wasSuccessful() and syntax and receipt['baseline_methods_preserved'] else 1)
