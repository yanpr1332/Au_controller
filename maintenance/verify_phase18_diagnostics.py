"""Verify durable evidence; does not claim GUI workflows beyond observations."""
import ast,gzip,hashlib,json
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    project=ROOT/'tests/native_outputs/ACCEPT_AU_Phase18_PR_Diagnostic.prproj'
    raw=project.read_bytes()
    xml=gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw
    handshake=(ROOT/'tests/receipts/phase18_cep_handshake.txt').read_text(encoding='utf8')
    backup=ROOT/'backups/phase18_pr_layouts'
    result={
      'project':str(project),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
      'premiere_saved_media_reference':b'delivery_verified.mp4' in xml,
      'original_layouts_preserved':all((backup/n).is_file() for n in ('UserWorkspace.xml','WorkspaceConfig.xml')),
      'cep_host_handshake':all(s in handshake for s in ('HOST=Audition','VERSION=26.0.0','DOCUMENTS=0','REFLECT_CLASS=Application')),
      'cep_visual_rendering_verified':False,'premiere_roundtrip_verified':False,
      'spectral_drag_verified':False,
      'scope':'Saved project/media reference and CEP host callback only; visual and drag limitations remain',
    }
    ast.parse((ROOT/'maintenance/diagnose_phase18_host.py').read_text(encoding='utf8'))
    path=ROOT/'tests/receipts'/('phase18_diagnostics_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'.json')
    with path.open('x',encoding='utf8') as f:json.dump(result,f,indent=2,ensure_ascii=False)
    print(json.dumps(result,indent=2,ensure_ascii=False));print(path)
