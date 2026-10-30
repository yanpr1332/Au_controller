from __future__ import annotations
import json,hashlib,subprocess,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audition_controller import AuditionController as C
R=Path(__file__).resolve().parents[1]
BASE=R/'tests/native_outputs/ACCEPT_AU_Phase04_bus_pruned.sesx'
NATIVE=R/'tests/native_outputs/ACCEPT_AU_Phase06_XMP_Revised.sesx'
ARR=R/'tests/native_outputs/ACCEPT_AU_Phase06_multi_arrangement.sesx'
class Phase06NativeXmpTransport(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='phase06_xmp_test_',dir=str(R/'tests'))
  self.addCleanup(self.temp.cleanup)
  self.dir=Path(self.temp.name)
  self.out=self.dir/'ACCEPT_AU_XMPNew.sesx'
 def test_xmp_real_native_reopen(self):
  rec=json.loads((R/'tests/receipts/phase06_native_xmp_edit_acceptance.json').read_text(encoding='utf8'))
  self.assertTrue(rec['native_reopened'])
  self.assertEqual(rec['native_inventory']['MARKERS'],'3')
 def test_xmp_real_native_times(self):
  r=json.loads((R/'tests/receipts/phase06_native_xmp_edit_acceptance.json').read_text(encoding='utf8'))
  self.assertEqual(r['native_marker_times'],
    {'QA Outro':107000,'QA Second Part':95000,'QA Section 1':52000})
 def test_xmp_add(self):
  x=C.patch_native_xmp_markers(BASE,self.out,[{'action':'add','name':'QA Extra','start_samples':3000,'duration_samples':2000}],confirm=True)
  self.assertEqual(x['after_count'],3)
 def test_xmp_rename(self):
  x=C.patch_native_xmp_markers(BASE,self.out,[{'action':'rename','name':'QA Section 1','new_name':'QA Intro'}],confirm=True)
  self.assertIn('QA Intro',[m['name'] for m in x['markers']])
 def test_xmp_move(self):
  x=C.patch_native_xmp_markers(BASE,self.out,[{'action':'move','name':'QA Section 1','start_samples':53000}],confirm=True)
  self.assertEqual(next(m['start_samples'] for m in x['markers'] if m['name']=='QA Section 1'),53000)
 def test_xmp_delete(self):
  x=C.patch_native_xmp_markers(BASE,self.out,[{'action':'remove','name':'QA Section 1'}],confirm=True)
  self.assertEqual(x['after_count'],1)
 def test_xmp_dryrun(self):
  x=C.patch_native_xmp_markers(BASE,self.out,[{'action':'remove','name':'QA Section 1'}])
  self.assertTrue(x['dry_run'])
  self.assertFalse(self.out.exists())
 def test_xmp_source_immutable(self):
  sha=hashlib.sha256(BASE.read_bytes()).hexdigest()
  C.patch_native_xmp_markers(BASE,self.out,[{'action':'move','name':'QA Section 1','start_samples':50000}],confirm=True)
  self.assertEqual(hashlib.sha256(BASE.read_bytes()).hexdigest(),sha)
 def test_xmp_duplicate_refused(self):
  with self.assertRaises(ValueError):
   C.patch_native_xmp_markers(BASE,self.out,[{'action':'add','name':'QA Section 1','start_samples':3,'duration_samples':5}],confirm=True)
 def test_xmp_bad_name(self):
  with self.assertRaises(ValueError):
   C.patch_native_xmp_markers(BASE,self.out,[{'action':'add','name':'../bad','start_samples':3,'duration_samples':5}],confirm=True)
 def test_xmp_remove_missing(self):
  with self.assertRaises(ValueError):
   C.patch_native_xmp_markers(BASE,self.out,[{'action':'remove','name':'QA Missing'}],confirm=True)
 def test_xmp_target_overwrite(self):
  self.out.write_bytes(b'keep')
  with self.assertRaises(ValueError):
   C.patch_native_xmp_markers(BASE,self.out,[{'action':'move','name':'QA Section 1','start_samples':40000}],confirm=True)
  self.assertEqual(self.out.read_bytes(),b'keep')
 def test_transport_native_receipt(self):
  r=json.loads((R/'tests/receipts/phase06_native_transport_acceptance.json').read_text(encoding='utf8'))
  self.assertEqual(r['test']['SEEK'],'14000')
  self.assertEqual(r['test']['STOP_OBSERVED'],'true')
  self.assertEqual(r['test']['RESTORED_LOOP'],r['before']['LOOP'])
 def test_transport_dryrun_no_sdk(self):
  v=C().native_qa_transport_accept('ACCEPT_AU_TEST_01',play_ms=80,confirm=False)
  self.assertTrue(v['dry_run'])
 def test_transport_invalid_seek(self):
  with self.assertRaises(ValueError):
   C().native_qa_transport_accept('ACCEPT_AU_TEST_01',seek_samples=-1,confirm=True)
 def test_transport_too_long(self):
  with self.assertRaises(ValueError):
   C().native_qa_transport_accept('ACCEPT_AU_TEST_01',play_ms=10000,confirm=True)
 def test_transport_nonqa_name(self):
  with self.assertRaises(PermissionError):
   C().native_qa_transport_accept('UserDocument',confirm=True)
 def test_audit_session_cli(self):
  task=subprocess.run([sys.executable,'-B',str(R/'audition_controller.py'),'audit-session',str(ARR)],
     capture_output=True,text=True,encoding='utf8',errors='replace',timeout=30)
  self.assertEqual(task.returncode,0,task.stderr)
  result=json.loads(task.stdout)
  self.assertTrue(result['passed'])
  self.assertEqual(result['checks']['clip_count'],4)
 def test_effects_cli_dryrun(self):
  file=self.dir/'effects.json'
  file.write_text(json.dumps([{'effect':'highpass','hz':80}]),encoding='utf8')
  task=subprocess.run([sys.executable,'-B',str(R/'audition_controller.py'),'effects',
     str(R/'tests/fixtures/accept_au_sine_48k_mono.wav'),
     str(self.dir/'out.wav'),str(file)],
     capture_output=True,text=True,encoding='utf8',errors='replace',timeout=30)
  self.assertEqual(task.returncode,0,task.stderr)
  self.assertTrue(json.loads(task.stdout)['dry_run'])
if __name__=='__main__':unittest.main()
