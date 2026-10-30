from __future__ import annotations
import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from scipy.io import wavfile
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from audition_controller import AuditionController as C
STEREO=R/'tests/native_outputs/phase05_duck_mix.wav'
MONO=R/'tests/fixtures/accept_au_sine_48k_mono.wav'
class Phase07ChannelsAndCoverage(unittest.TestCase):
 def setUp(self):
  tmp=tempfile.TemporaryDirectory(prefix='phase07_channels_',dir=str(R/'tests'))
  self.addCleanup(tmp.cleanup);self.w=Path(tmp.name)
 def test_real_channel_roundtrip(self):
  r=json.loads((R/'tests/receipts/phase07_channel_split_roundtrip.json').read_text(encoding='utf8'))
  self.assertTrue(r['input_preserved'])
  self.assertLess(r['roundtrip_max_absolute_error'],1e-8)
 def test_channel_files_match_native(self):
  rr=json.loads((R/'tests/receipts/phase07_channel_split_roundtrip.json').read_text(encoding='utf8'))
  sr,x=wavfile.read(STEREO)
  _,l=wavfile.read(rr['split']['left']);_,r=wavfile.read(rr['split']['right'])
  self.assertEqual(x.shape[1],2)
  self.assertTrue(np.array_equal(x[:,0],l))
  self.assertTrue(np.array_equal(x[:,1],r))
 def test_split_stereo_dryrun(self):
  a=C.split_stereo_to_mono(STEREO,self.w/'left.wav',self.w/'right.wav')
  self.assertTrue(a['dry_run'])
  self.assertEqual(list(self.w.iterdir()),[])
 def test_split_stereo_mono_input_rejected(self):
  with self.assertRaises(ValueError):
   C.split_stereo_to_mono(MONO,self.w/'left.wav',self.w/'right.wav',confirm=True)
 def test_split_stereo_duplicate_output(self):
  target=self.w/'same.wav'
  with self.assertRaises(ValueError):
   C.split_stereo_to_mono(STEREO,target,target,confirm=True)
 def test_stereo_join_dryrun(self):
  rr=json.loads((R/'tests/receipts/phase07_channel_split_roundtrip.json').read_text(encoding='utf8'))
  a=C.combine_mono_to_stereo(rr['split']['left'],rr['split']['right'],self.w/'joined.wav')
  self.assertTrue(a['dry_run'])
 def test_stereo_join_mismatched_sample_rate(self):
  sr,data=wavfile.read(MONO)
  p=self.w/'other_rate.wav'
  wavfile.write(p,44100,data)
  with self.assertRaises(ValueError):
   C.combine_mono_to_stereo(MONO,p,self.w/'joined.wav',confirm=True)
 def test_native_mp3_flac_open(self):
  r=json.loads((R/'tests/receipts/phase07_native_mp3_flac_open.json').read_text(encoding='utf8'))
  self.assertTrue(r['documents_zero'])
  self.assertEqual(len(r['imports']),2)
  self.assertEqual({x['extension'] for x in r['imports']},{'.mp3','.flac'})
  self.assertTrue(all(x['open']['CLASS']=='WaveDocument' for x in r['imports']))
 def test_native_track_gain_audio_effect(self):
  r=json.loads((R/'tests/receipts/phase07_native_track_controls.json').read_text(encoding='utf8'))
  self.assertLess(r['audio']['peak_dbfs'],r['baseline_peak_dbfs']-.2)
  self.assertTrue(r['source_unchanged'])
 def test_float_to_pcm16_proof(self):
  r=json.loads((R/'tests/receipts/phase07_float_to_pcm16.json').read_text(encoding='utf8'))
  self.assertTrue(r['actual_pcm16_readback'])
  self.assertEqual(len(r['outputs']),2)
  for item in r['outputs'].values():
   sr,arr=wavfile.read(item['output'])
   self.assertEqual(arr.dtype,np.dtype('int16'))
   self.assertEqual(len(arr),192000)
 def test_waveform_four_step_pipeline(self):
  report=json.loads((R/'tests/receipts/phase07_waveform_pipeline_acceptance.json').read_text(encoding='utf8'))
  self.assertTrue(report['quality_passed'])
  self.assertEqual(report['pipeline']['steps'],4)
  self.assertGreater(report['spectral_dominant_hz'],400)
 def test_waveform_pipeline_manifest_hashes(self):
  out=R/'tests/native_outputs/phase07_waveform_production'
  d=json.loads((out/'audition_production_receipt.json').read_text(encoding='utf8'))
  self.assertEqual(d['step_count'],4)
  self.assertEqual({x['kind'] for x in d['steps']},{'wave_edit','fft','master','qc'})
  for item in d['steps']:
   p=out/item['output']
   self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),item['sha256'])
 def test_plan_rejects_fft_from_mp3(self):
  src=str(R/'tests/native_outputs/phase06_tags_id3.mp3')
  spec={'inputs':{'music':src},'steps':[
   {'id':'x','kind':'fft','source':'music','format':'json','params':{'window':4096}}]}
  with self.assertRaises(ValueError):
   C.production_job_plan(spec,self.w)
 def test_p0_31_item_mapping(self):
  file=R/'api/Audition_26_phase07_P0_evidence_crosswalk.json'
  a=json.loads(file.read_text(encoding='utf8'))
  self.assertEqual(len(a),31)
  self.assertEqual(len({x['id'] for x in a}),31)
  self.assertGreaterEqual(sum(x['new_status'].startswith('verified_') for x in a),20)
 def test_new_ledger_coverage(self):
  r=json.loads((R/'api/Audition_26_phase07_baseline_375.json').read_text(encoding='utf8'))
  self.assertEqual(r['total'],375)
  self.assertEqual(len(r['features']),375)
  self.assertEqual(len({x['id'] for x in r['features']}),375)
if __name__=='__main__':unittest.main()
