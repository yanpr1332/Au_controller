from __future__ import annotations
import tempfile,unittest,sys,json
from pathlib import Path
from lxml import etree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audition_controller import AuditionController as C
R=Path(__file__).resolve().parents[1]
SRC=R/'tests/native_outputs/ACCEPT_AU_Phase04_bus_pruned.sesx'
TRIM=R/'tests/native_outputs/ACCEPT_AU_Phase05_clip_trim_fade.sesx'
class Phase05NativeSessionIntegrity(unittest.TestCase):
 def setUp(self):
  self.obj=tempfile.TemporaryDirectory(dir=str(R/'tests'),prefix='phase05_audit_')
  self.addCleanup(self.obj.cleanup)
  self.out=Path(self.obj.name)
 def modified(self,change):
  t=ET.parse(str(SRC))
  change(t.getroot())
  path=self.out/'ACCEPT_AU_Damaged.sesx'
  t.write(str(path),xml_declaration=True,encoding='utf8')
  return path
 def test_reference_preflight(self):
  s=C.audit_native_session(SRC)
  self.assertTrue(s['passed'],s['errors'])
  self.assertEqual(s['checks']['native_markers'],2)
  self.assertEqual(s['checks']['file_count'],1)
 def test_trimmed_source_preflight(self):
  self.assertTrue(C.audit_native_session(TRIM)['passed'])
 def test_missing_media_rejected(self):
  p=self.modified(lambda root:root.find('./files/file').set('absolutePath',r'C:\not-real\clip.wav'))
  d=C.audit_native_session(p)
  self.assertFalse(d['passed'])
  self.assertTrue(any('Missing media' in x for x in d['errors']))
 def test_bad_source_ref_rejected(self):
  p=self.modified(lambda root:root.find('.//audioClip').set('fileID','no-such'))
  d=C.audit_native_session(p)
  self.assertFalse(d['passed'])
  self.assertTrue(any('fileID' in x for x in d['errors']))
 def test_invalid_duration_rejected(self):
  p=self.modified(lambda root:root.find('.//audioClip').set('endPoint','99999'))
  d=C.audit_native_session(p)
  self.assertFalse(d['passed'])
  self.assertTrue(any('duration mismatch' in x for x in d['errors']))
 def test_invalid_fade_rejected(self):
  p=self.modified(lambda root:root.find('.//audioClip/fadeIn').set('endPoint','999999'))
  d=C.audit_native_session(p)
  self.assertFalse(d['passed'])
  self.assertTrue(any('fadeIn' in x for x in d['errors']))
 def test_bus_cycle_rejected(self):
  def corrupt(root):
   bus=root.find('.//busTrack')
   bus.find('./trackAudioParameters/trackOutput').set('outputID',bus.get('id'))
  d=C.audit_native_session(self.modified(corrupt))
  self.assertFalse(d['passed'])
  self.assertTrue(any('Bus routing' in x for x in d['errors']))
 def test_unsafe_eq_rejected(self):
  def corrupt(root):
   t=root.find('.//audioTrack')
   eq=next(v for v in t.findall('./trackAudioParameters/component') if v.get('id')=='trackEQ')
   eq.set('powered','true')
   q=next(v for v in eq.findall('parameter') if v.get('name')=='EQ Band 3 Gain')
   q.set('parameterValue','.96')
  p=self.modified(corrupt)
  self.assertFalse(C.audit_native_session(p)['passed'])
  self.assertTrue(C.audit_native_session(p,reject_hot_eq=False)['passed'])
  self.assertTrue(C.audit_native_session(p,reject_hot_eq=False)['warnings'])
 def test_valid_audit_json(self):
  dest=self.out/'qa.json'
  v=C.write_native_session_audit(SRC,dest,confirm=True)
  self.assertTrue(v['passed'])
  self.assertTrue(dest.exists())
  self.assertTrue(json.loads(dest.read_text(encoding='utf8'))['passed'])
 def test_audit_no_overwrite(self):
  dest=self.out/'qa.json';dest.write_text('keep')
  with self.assertRaises(ValueError):C.write_native_session_audit(SRC,dest,confirm=True)
  self.assertEqual(dest.read_text(),'keep')
 def test_audit_dryrun(self):
  dest=self.out/'qa.json'
  a=C.write_native_session_audit(SRC,dest)
  self.assertTrue(a['dry_run'])
  self.assertFalse(dest.exists())
if __name__=='__main__':unittest.main()
