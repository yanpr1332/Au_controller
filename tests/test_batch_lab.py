import tempfile,unittest,sys
from pathlib import Path
import numpy as np
from scipy.io import wavfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audition_controller import AuditionController
class BatchTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name)
  t=np.arange(48000)/48000
  for i in (1,2,3):
   v=np.zeros(48000,dtype=np.float32)
   v[2400:19000]=.08*i*np.sin(2*np.pi*(220*i)*t[2400:19000])
   v[28000:42000]=.06*i*np.sin(2*np.pi*440*t[28000:42000])
   wavfile.write(self.root/f'in{i}.wav',48000,v)
  self.output=self.root/'outputs';self.output.mkdir()
 def sources(self):return sorted(self.root.glob('in*.wav'))
 def test_activity_regions(self):
  r=AuditionController.activity_regions(self.sources()[0],threshold_dbfs=-34,window_ms=20)
  self.assertEqual(len(r['regions']),2)
  self.assertTrue(r['not_speech_recognition'])
 def test_batch_dryrun(self):
  r=AuditionController.batch_dsp(self.sources(),self.output,[{'type':'gain_db','db':-4}])
  self.assertTrue(r['dry_run'])
  self.assertEqual(r['job_count'],3)
 def test_batch_real(self):
  r=AuditionController.batch_dsp(self.sources(),self.output,[{'type':'gain_db','db':-3}],confirm=True)
  self.assertEqual(r['success'],3)
  self.assertTrue(all(x['source_intact'] for x in r['results']))
  self.assertTrue(all(x['quality']['passed'] for x in r['results']))
 def test_batch_overwrite(self):
  (self.output/'in1_audition_processed.wav').write_bytes(b'data')
  with self.assertRaises(FileExistsError):
   AuditionController.batch_dsp(self.sources(),self.output,[{'type':'gain_db','db':-3}],confirm=True)
 def test_batch_duplicate(self):
  x=self.sources()[0]
  with self.assertRaises(ValueError):
   AuditionController.batch_dsp([x,x],self.output,[{'type':'gain_db','db':-3}],confirm=True)
 def test_quality_clip(self):
  x=self.sources()[0]
  a=AuditionController.audio_quality_gate(x,max_peak_dbfs=-30)
  self.assertFalse(a['passed'])
if __name__=='__main__':unittest.main()
