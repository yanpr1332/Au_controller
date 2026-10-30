from __future__ import annotations
import sys,unittest,tempfile
from pathlib import Path
import numpy as np
from scipy.io import wavfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audition_controller import AuditionController
class DSPTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.addCleanup(self.tmp.cleanup)
  self.dir=Path(self.tmp.name)
  self.src=self.dir/'in.wav'
  sr=48000
  t=np.arange(sr*2,dtype=np.float64)/sr
  x=(np.sin(2*np.pi*440*t)*.2).astype(np.float32)
  wavfile.write(self.src,sr,x)
  self.c=AuditionController
 def process(self,ops,name='out.wav',fmt='pcm16'):
  return self.c.process_wav(self.src,self.dir/name,ops,confirm=True,output_format=fmt)
 def test_spectral_report(self):
  d=self.c.audio_signal_report(self.src)
  self.assertAlmostEqual(d['dominant_hz'],440,delta=12)
  self.assertEqual(d['channels'],1)
 def test_gain_db(self):
  b=self.c.audio_signal_report(self.src)
  a=self.process([{'type':'gain_db','db':-6}])
  self.assertAlmostEqual(a['peak_dbfs']-b['peak_dbfs'],-6,delta=.1)
 def test_trim(self):
  r=self.process([{'type':'trim','start':.5,'end':1.25}])
  self.assertEqual(r['frames'],36000)
 def test_resample(self):
  r=self.process([{'type':'resample','rate':44100}])
  self.assertEqual(r['sample_rate'],44100)
  self.assertAlmostEqual(r['seconds'],2,delta=.003)
 def test_filters(self):
  r=self.process([{'type':'highpass','hz':80},{'type':'notch','hz':60},{'type':'lowpass','hz':4000}])
  self.assertEqual(r['frames'],96000)
 def test_fade_and_normalize(self):
  r=self.process([{'type':'peak_normalize','target_dbfs':-1},{'type':'fade','seconds':.05,'edge':'in'}])
  self.assertAlmostEqual(r['peak_dbfs'],-1,delta=.1)
 def test_reverse_and_padding(self):
  r=self.process([{'type':'reverse'},{'type':'pad_silence','side':'start','seconds':.25}])
  self.assertEqual(r['frames'],108000)
 def test_gate_compress_limit(self):
  r=self.process([{'type':'gate','threshold_dbfs':-40},{'type':'compress','threshold_dbfs':-25,'ratio':3},{'type':'limit','ceiling_dbfs':-6}])
  self.assertLessEqual(r['peak_dbfs'],-6+0.05)
 def test_output_float32(self):
  r=self.process([{'type':'gain_db','db':2}],fmt='float32')
  self.assertEqual(r['sample_format'],'float32')
 def test_new_file_only(self):
  with self.assertRaises(ValueError):self.c.process_wav(self.src,self.src,[{'type':'reverse'}],confirm=True)
 def test_dry_run(self):
  r=self.c.process_wav(self.src,self.dir/'dry.wav',[{'type':'gain_db','db':5}],confirm=False)
  self.assertTrue(r['dry_run'])
  self.assertFalse((self.dir/'dry.wav').exists())
 def test_bad_op_rejected(self):
  with self.assertRaises(ValueError):self.c.process_wav(self.src,self.dir/'new.wav',[{'type':'delete'}],confirm=True)
 def test_clip_guard(self):
  with self.assertRaises(ValueError):self.process([{'type':'gain_db','db':35}])
 def test_channel_balance_requires_stereo(self):
  with self.assertRaises(ValueError):self.process([{'type':'channel_balance','left_db':-3}])
 def test_make_stereo_and_balance(self):
  r=self.process([{'type':'stereo'},{'type':'channel_balance','left_db':-6,'right_db':0}])
  self.assertEqual(r['channels'],2)
 def test_dc_remove(self):
  d=self.dir/'dc.wav'
  sr,x=wavfile.read(self.src)
  wavfile.write(d,sr,x+.1)
  a=self.c.process_wav(d,self.dir/'dc_fixed.wav',[{'type':'dc_remove'}],confirm=True)
  self.assertLess(abs(a['dc_offset'][0]),1e-4)
if __name__=='__main__':unittest.main()
