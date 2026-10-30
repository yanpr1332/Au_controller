from __future__ import annotations
import sys,unittest,tempfile,json,hashlib
from pathlib import Path
from lxml import etree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audition_controller import AuditionController as C
R=Path(__file__).resolve().parents[1]
ROOT=R/'tests/native_outputs'
SRC=ROOT/'ACCEPT_AU_Phase03_native_092344.sesx'
PRUNED=ROOT/'ACCEPT_AU_Phase04_bus_pruned.sesx'
ROUTED=ROOT/'ACCEPT_AU_Phase03_routed.sesx'
BUNDLE=ROOT/'ACCEPT_AU_Phase04_portable_bundle'
EQWAV=ROOT/'phase04_eq_native_mix.wav'

class Phase04StrictUnitTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=ROOT,prefix='phase04_unit_')
  self.addCleanup(self.tmp.cleanup)
  self.dir=Path(self.tmp.name)
  self.out=self.dir/'ACCEPT_AU_UnitTest.sesx'

 def test_unused_bus_is_prunable(self):
  a=C.remove_unused_bus_sesx(SRC,self.out,bus_index=1,expected_name='QA Temporary Additional Bus',confirm=True)
  self.assertTrue(a['source_intact'])
  self.assertEqual(C.inspect_session_routes(self.out)['bus_tracks'],1)

 def test_used_bus_refused(self):
  with self.assertRaises(ValueError):
   C.remove_unused_bus_sesx(ROUTED,self.out,bus_index=0,expected_name='QA Phase03 Bus',confirm=True)

 def test_bus_label_guard(self):
  with self.assertRaises(PermissionError):
   C.remove_unused_bus_sesx(SRC,self.out,bus_index=1,expected_name='Not QA',confirm=True)

 def test_bus_missing(self):
  with self.assertRaises(IndexError):
   C.remove_unused_bus_sesx(SRC,self.out,bus_index=100,expected_name='QA Temporary Additional Bus')

 def test_bus_dryrun(self):
  r=C.remove_unused_bus_sesx(SRC,self.out,bus_index=1,expected_name='QA Temporary Additional Bus')
  self.assertTrue(r['dry_run']);self.assertFalse(self.out.exists())

 def test_bus_overwrite_guard(self):
  self.out.write_bytes(b'OLD')
  with self.assertRaises(ValueError):
   C.remove_unused_bus_sesx(SRC,self.out,bus_index=1,expected_name='QA Temporary Additional Bus',confirm=True)

 def test_native_bus_reopen_receipt(self):
  r=json.loads((R/'tests/receipts/phase04_native_bus_prune_reopen.json').read_text(encoding='utf8'))
  self.assertEqual(r['native_readback']['BUSES'],'1')
  self.assertEqual(r['native_readback']['MARKERS'],'2')

 def test_native_qa_package_verified(self):
  a=C.verify_qa_session_package(BUNDLE)
  self.assertTrue(a['all_present'])
  self.assertTrue(a['native_reopen_verified'])

 def test_package_dryrun(self):
  name=self.dir/'ACCEPT_AU_BundleTest'
  a=C.create_qa_session_package(PRUNED,name,confirm=False)
  self.assertTrue(a['dry_run']);self.assertFalse(name.exists())

 def test_package_real_source_hash(self):
  name=self.dir/'ACCEPT_AU_BundleTest'
  original=hashlib.sha256(PRUNED.read_bytes()).hexdigest()
  p=C.create_qa_session_package(PRUNED,name,confirm=True)
  self.assertTrue(C.verify_qa_session_package(name)['all_present'])
  self.assertTrue(p['source_intact'])
  self.assertEqual(original,hashlib.sha256(PRUNED.read_bytes()).hexdigest())
  self.assertFalse(C.verify_qa_session_package(name)['native_reopen_verified'])

 def test_package_existing_guard(self):
  name=self.dir/'ACCEPT_AU_BundleTest';name.mkdir()
  with self.assertRaises(PermissionError):
   C.create_qa_session_package(PRUNED,name,confirm=True)

 def test_package_name_guard(self):
  with self.assertRaises(ValueError):
   C.create_qa_session_package(PRUNED,self.dir/'notqa',confirm=True)

 def test_package_nonqa_source_guard(self):
  with self.assertRaises(PermissionError):
   C.create_qa_session_package(R/'README.md',self.dir/'ACCEPT_AU_NonQA',confirm=True)

 def test_eq_introspection(self):
  d=C.inspect_native_eq(PRUNED)
  self.assertEqual(d['powered'],'false')
  self.assertAlmostEqual(d['parameters']['EQ Band 3 Gain'],.5)

 def test_eq_valid_copy(self):
  settings={'EQ Band 3 Gain':.51,'EQ Band 3 Enable':True}
  result=C.patch_native_eq_normalized(PRUNED,self.out,settings,confirm=True)
  self.assertTrue(result['source_unmodified'])
  check=C.inspect_native_eq(self.out)
  self.assertEqual(check['powered'],'true')
  self.assertAlmostEqual(check['parameters']['EQ Band 3 Gain'],.51)

 def test_eq_unsafe_gain_blocked(self):
  with self.assertRaises(ValueError):
   C.patch_native_eq_normalized(PRUNED,self.out,{'EQ Band 3 Gain':.95},confirm=True)
  self.assertFalse(self.out.exists())

 def test_eq_invalid_parameter(self):
  with self.assertRaises(ValueError):
   C.patch_native_eq_normalized(PRUNED,self.out,{'Execute arbitrary':.51},confirm=True)

 def test_eq_boost_native_render_proof(self):
  p=json.loads((R/'tests/receipts/phase04_real_eq_render.json').read_text(encoding='utf8'))
  self.assertTrue(p['eq_audible_effect_verified'])
  self.assertLess(p['after']['peak_dbfs'],-1)
  self.assertAlmostEqual(p['peak_delta_db'],.8444,delta=.3)

 def test_rejected_unsafe_file_removed(self):
  p=json.loads((R/'tests/receipts/phase04_eq_unsafe_gain_rejected.json').read_text(encoding='utf8'))
  self.assertTrue(p['unsafe_artifacts_removed'])
  self.assertGreater(p['peak_dbfs'],0)

 def test_native_menu_registry(self):
  p=json.loads((R/'api/Audition_26_native_menu_registry.json').read_text(encoding='utf8'))
  self.assertGreater(p['count'],400)
  self.assertEqual(p['count'],len(p['commands']))
  self.assertEqual(len({c['id'] for c in p['commands']}),p['unique_ids'])

 def test_native_menu_lookup_argument(self):
  c=C()
  with self.assertRaises(ValueError):c.lookup_native_menu('',max_results=4)
  with self.assertRaises(ValueError):c.lookup_native_menu('Audio',max_results=0)

 def test_cep_staged(self):
  p=json.loads((R/'tests/receipts/phase04_cep_deployment.json').read_text(encoding='utf8'))
  self.assertTrue(p['copy_sha256_verified'])
  self.assertEqual(p['file_count'],3)

if __name__=='__main__':unittest.main()
