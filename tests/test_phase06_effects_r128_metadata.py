from __future__ import annotations
import json,sys,tempfile,unittest,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audition_controller import AuditionController as C
R=Path(__file__).resolve().parents[1]
FX=R/'tests/fixtures/accept_au_sine_48k_mono.wav'
BWF=R/'tests/native_outputs/phase06_tags_bwf.wav'
MP3=R/'tests/native_outputs/phase06_tags_id3.mp3'
VOICE=R/'tests/native_outputs/phase05_duck_podcast_master.wav'
EFFECT_RECEIPT=R/'tests/receipts/phase06_effects_batch.json'

class Phase06EffectsTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='phase06_test_',dir=str(R/'tests'))
  self.addCleanup(self.tmp.cleanup)
  self.dest=Path(self.tmp.name)/'out.wav'
 def test_all_declared_effects_compilable(self):
  specs=[
   {'effect':'highpass'},{'effect':'lowpass'},{'effect':'bandpass'},
   {'effect':'notch'},{'effect':'equalizer'},{'effect':'declick'},
   {'effect':'declip'},{'effect':'fft_denoise'},{'effect':'nlm_denoise'},
   {'effect':'deesser'},{'effect':'compressor'},{'effect':'gate'},
   {'effect':'limiter'},{'effect':'hum_50'},{'effect':'hum_60'},
   {'effect':'volume'},{'effect':'delay'},{'effect':'chorus'},
   {'effect':'flanger'},{'effect':'tempo'},{'effect':'pitch'},
   {'effect':'fade_in'},{'effect':'fade_out'},{'effect':'trim'},
   {'effect':'silence_trim'},{'effect':'reverse'},{'effect':'mono'},
   {'effect':'dc_remove'},{'effect':'dynaudnorm'}]
  for spec in specs:
   with self.subTest(spec=spec['effect']):
    self.assertTrue(C.effects_recipe_validate([spec])['graph'])
 def test_recipe_cap(self):
  with self.assertRaises(ValueError):
   C.effects_recipe_validate([{'effect':'highpass'}]*17)
 def test_effect_unknown(self):
  with self.assertRaises(ValueError):
   C.effects_recipe_validate([{'effect':'__execute','command':'rm -rf /'}])
 def test_effect_extra_params_rejected(self):
  with self.assertRaises(ValueError):
   C.effects_recipe_validate([{'effect':'highpass','hz':80,'cmd':'shell'}])
 def test_effect_nan_rejected(self):
  with self.assertRaises(ValueError):
   C.effects_recipe_validate([{'effect':'volume','db':float('nan')}])
 def test_effect_non_numeric_rejected(self):
  with self.assertRaises(ValueError):
   C.effects_recipe_validate([{'effect':'highpass','hz':'$(rm -rf /)'}])
 def test_effect_inf_rejected(self):
  with self.assertRaises(ValueError):
   C.effects_recipe_validate([{'effect':'equalizer','db':float('inf')}])
 def test_effect_bad_tempo(self):
  with self.assertRaises(ValueError):
   C.effects_recipe_validate([{'effect':'tempo','multiplier':10}])
 def test_effect_bad_pitch(self):
  with self.assertRaises(ValueError):
   C.effects_recipe_validate([{'effect':'pitch','semitones':100}])
 def test_effect_bad_limiter(self):
  with self.assertRaises(ValueError):
   C.effects_recipe_validate([{'effect':'limiter','ceiling_dbfs':1}])
 def test_effect_validate_dryrun(self):
  out=C.render_audio_effects(FX,self.dest,[{'effect':'highpass'}])
  self.assertTrue(out['dry_run'])
  self.assertFalse(self.dest.exists())
 def test_effect_existing_output_guard(self):
  self.dest.write_text('keep')
  with self.assertRaises(ValueError):
   C.render_audio_effects(FX,self.dest,[{'effect':'highpass'}],confirm=True)
  self.assertEqual(self.dest.read_text(),'keep')
 def test_effect_source_output_collision(self):
  with self.assertRaises(ValueError):
   C.render_audio_effects(FX,FX,[{'effect':'highpass'}],confirm=True)
 def test_effect_bad_sample_rate(self):
  with self.assertRaises(ValueError):
   C.render_audio_effects(FX,self.dest,[{'effect':'highpass'}],sample_rate=2000)
 def test_effect_batch_duplicates(self):
  job={'source':str(FX),'destination':str(self.dest),'effects':[{'effect':'highpass'}]}
  with self.assertRaises(ValueError):
   C.batch_effect_recipes([job,job],confirm=True)
 def test_effect_batch_dryrun(self):
  job={'source':str(FX),'destination':str(self.dest),'effects':[{'effect':'highpass'}]}
  data=C.batch_effect_recipes([job],confirm=False)
  self.assertTrue(data['dry_run'])
 def test_effect_batch_receipt(self):
  record=json.loads(EFFECT_RECEIPT.read_text(encoding='utf8'))
  self.assertEqual(record['results']['batch_size'],9)
  self.assertEqual(record['results']['passed_jobs'],9)
 def test_effect_audio_sha256(self):
  record=json.loads(EFFECT_RECEIPT.read_text(encoding='utf8'))
  for item in record['results']['results']:
   file=Path(item['output'])
   self.assertTrue(file.is_file())
   self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(),item['sha256'])
 def test_effect_different_duration(self):
  record=json.loads(EFFECT_RECEIPT.read_text(encoding='utf8'))
  table={Path(r['output']).stem:r['duration'] for r in record['results']['results']}
  self.assertLess(table['pitch_tempo'],table['speech_repair'])
  self.assertLess(table['fade_trim'],table['speech_repair'])
 def test_effect_readback_qa(self):
  record=json.loads(EFFECT_RECEIPT.read_text(encoding='utf8'))
  self.assertTrue(all(x['sample_peak_dbfs']<0.1 for x in record['results']['results']))
 def test_meter_preset_invalid(self):
  with self.assertRaises(ValueError):
   C.loudness_delivery_gate(VOICE,profile='UNSUPPORTED')
 def test_meter_resolution_bound(self):
  with self.assertRaises(ValueError):
   C.r128_loudness_timeline(VOICE,max_points=2)
 def test_meter_real_40_points(self):
  r=json.loads((R/'tests/receipts/phase06_r128_timeline.json').read_text(encoding='utf8'))
  self.assertEqual(r['readings_total'],40)
  self.assertEqual(r['readings_returned'],40)
  self.assertAlmostEqual(r['integrated_summary']['integrated_lufs'],-15.96,delta=.3)
 def test_meter_channels(self):
  r=json.loads((R/'tests/receipts/phase06_r128_timeline.json').read_text(encoding='utf8'))
  self.assertIn('momentary_lufs',r['time_series'][5])
  self.assertIn('short_term_lufs',r['time_series'][5])
 def test_tag_dryrun(self):
  self.assertTrue(C.tag_delivery_audio(FX,self.dest,{'title':'QA'},confirm=False)['dry_run'])
 def test_tag_invalid_key(self):
  with self.assertRaises(ValueError):
   C.tag_delivery_audio(FX,self.dest,{'bad_metadata':'anything'},confirm=True)
 def test_tag_injection(self):
  with self.assertRaises(ValueError):
   C.tag_delivery_audio(FX,self.dest,{'title':'line\ninjection'},confirm=True)
 def test_tag_bwf_wrong_type(self):
  with self.assertRaises(ValueError):
   C.tag_delivery_audio(MP3,self.dest.with_suffix('.mp3'),{'title':'A'},bwf=True,confirm=True)
 def test_tag_real_bwf(self):
  p=json.loads((R/'tests/receipts/phase06_tag_delivery.json').read_text(encoding='utf8'))
  a=p[0]
  self.assertTrue(a['passed'] and a['bwf'])
  self.assertEqual(a['metadata_readback']['description'],'Audition controlled workflow')
  self.assertEqual(hashlib.sha256(BWF.read_bytes()).hexdigest(),a['output_sha256'])
 def test_tag_real_mp3(self):
  p=json.loads((R/'tests/receipts/phase06_tag_delivery.json').read_text(encoding='utf8'))
  a=p[1]
  self.assertTrue(a['passed'])
  self.assertEqual(a['codec'],'mp3')
  self.assertEqual(hashlib.sha256(MP3.read_bytes()).hexdigest(),a['output_sha256'])
 def test_tag_no_overwrite(self):
  self.dest.write_bytes(b'keep')
  with self.assertRaises(ValueError):
   C.tag_delivery_audio(FX,self.dest,{'title':'Test'},confirm=True)
if __name__=='__main__':unittest.main()
