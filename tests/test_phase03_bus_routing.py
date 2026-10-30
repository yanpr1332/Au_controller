import json,sys,tempfile,unittest,hashlib
from pathlib import Path
from lxml import etree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audition_controller import AuditionController as C

ROOT=Path(__file__).resolve().parents[1]
ORIG=ROOT/'tests/native_outputs/ACCEPT_AU_Phase03_native_092344.sesx'
ROUTED=ROOT/'tests/native_outputs/ACCEPT_AU_Phase03_routed.sesx'
MIX=ROOT/'tests/native_outputs/phase03_bus_routed_native_mix.wav'

class Phase03BusRoutingTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.addCleanup(self.tmp.cleanup)
  self.dest=Path(self.tmp.name)/'new.sesx'
 def test_real_bus_topology(self):
  a=C.inspect_session_routes(ORIG)
  self.assertEqual(a['bus_tracks'],2)
  self.assertTrue(a['valid_topology'])
 def test_real_bus_name_and_id(self):
  a=C.inspect_session_routes(ORIG)
  self.assertEqual(a['routes'][6]['name'],'QA Phase03 Bus')
  self.assertEqual(a['routes'][6]['track_id'],'10007')
 def test_patch_route_and_save(self):
  before=hashlib.sha256(ORIG.read_bytes()).hexdigest()
  result=C.patch_session_bus_route(ORIG,self.dest,track_index=0,bus_index=0,confirm=True)
  q=C.inspect_session_routes(self.dest)
  self.assertTrue(result['topology_valid'])
  self.assertEqual(q['routes'][0]['output_id'],'10007')
  self.assertTrue(q['valid_topology'])
  self.assertEqual(before,hashlib.sha256(ORIG.read_bytes()).hexdigest())
 def test_dryrun(self):
  out=C.patch_session_bus_route(ORIG,self.dest)
  self.assertTrue(out['dry_run'])
  self.assertFalse(self.dest.exists())
 def test_no_override(self):
  self.dest.write_bytes(b'old')
  with self.assertRaises(ValueError):C.patch_session_bus_route(ORIG,self.dest,confirm=True)
 def test_invalid_bus_index(self):
  with self.assertRaises(IndexError):C.patch_session_bus_route(ORIG,self.dest,bus_index=100,confirm=True)
 def test_invalid_track_index(self):
  with self.assertRaises(IndexError):C.patch_session_bus_route(ORIG,self.dest,track_index=100,confirm=True)
 def test_refuse_unlabeled(self):
  with self.assertRaises(PermissionError):
   C.patch_session_bus_route(ORIG,self.dest,track_index=1,confirm=True)
 def test_routed_native_artifact(self):
  self.assertEqual(C.inspect_session_routes(ROUTED)['routes'][0]['output_id'],'10007')
 def test_native_mixdown_wav(self):
  d=C.audio_signal_report(MIX)
  self.assertEqual(d['sample_rate'],48000)
  self.assertEqual(d['frames'],139200)
  self.assertGreater(d['peak_dbfs'],-50)
 def test_known_cycle_detection(self):
  t=ET.parse(str(ORIG))
  bus=t.getroot().find('.//busTrack')
  bus.find('./trackAudioParameters/trackOutput').set('outputID',bus.get('id'))
  t.write(str(self.dest),encoding='utf8',xml_declaration=True)
  p=C.inspect_session_routes(self.dest)
  self.assertFalse(p['valid_topology'])
  self.assertTrue(p['cycles'])
 def test_unresolved_output_detection(self):
  t=ET.parse(str(ORIG))
  track=t.getroot().find('.//audioTrack')
  track.find('./trackAudioParameters/trackOutput').set('outputID','999999999')
  t.write(str(self.dest),encoding='utf8',xml_declaration=True)
  p=C.inspect_session_routes(self.dest)
  self.assertFalse(p['valid_topology'])
  self.assertEqual(len(p['dangling_routes']),1)
 def test_bus_add_dryrun(self):
  x=C().native_multitrack_add_bus_qa('ACCEPT_AU_Test_001','QA Group',confirm=False)
  self.assertTrue(x['dry_run'])
 def test_bus_remove_dryrun(self):
  x=C().native_multitrack_remove_bus_qa('ACCEPT_AU_Test_001',0,confirm=False)
  self.assertTrue(x['dry_run'])
 def test_bus_marker_dryrun(self):
  x=C().native_multitrack_marker_qa('ACCEPT_AU_Test_001',start_samples=123,confirm=False)
  self.assertTrue(x['dry_run'])
 def test_bad_marker_name(self):
  with self.assertRaises(ValueError):
   C().native_multitrack_marker_qa('ACCEPT_AU_Test_001',start_samples=0,label='unsafe',confirm=True)
 def test_existing_delivery_receipt(self):
  rec=json.loads((ROOT/'tests/receipts/phase03_forensics_delivery_acceptance.json').read_text(encoding='utf8'))
  self.assertTrue(rec['pass'])
  self.assertEqual(rec['podcast']['passed_jobs'],1)
  self.assertEqual(rec['broadcast']['passed_jobs'],1)
 def test_native_bus_marker_receipt(self):
  rec=json.loads((ROOT/'tests/receipts/phase03_marker_final.json').read_text(encoding='utf8'))
  self.assertEqual(rec['after']['MARKERS'],'2')
  self.assertFalse(rec['bus_remove_supported'])
if __name__=='__main__':unittest.main()
