from __future__ import annotations
import sys,unittest,tempfile,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audition_controller import AuditionController as C

ROOT=Path(__file__).resolve().parents[1]
NATIVE=ROOT/'tests/native_outputs/phase02_native_session/ACCEPT_AU_Phase02_214641.sesx'
FIXTURE=ROOT/'tests/fixtures/accept_au_sine_48k_mono.wav'

class NativeSessionSchemaTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.addCleanup(self.tmp.cleanup)
  self.out=Path(self.tmp.name)
 def test_native_schema(self):
  v=C.inspect_native_sesx(NATIVE)
  self.assertEqual(v['format_version'],'1.9')
  self.assertEqual(v['track_count'],6)
  self.assertEqual(v['clip_count'],1)
  self.assertTrue(v['all_media_present'])
 def test_patch_full_schema_and_source_immutable(self):
  orig=hashlib.sha256(NATIVE.read_bytes()).hexdigest()
  edits=[{'action':'name','value':'New Test Voice'},{'action':'mute','value':True},
    {'action':'solo','value':False},{'action':'arm','value':False},
    {'action':'track_gain','value':.8},{'action':'pan','value':-.35},
    {'action':'eq_enabled','value':True},{'action':'clip_gain','value':.6},
    {'action':'clip_start','value':48000},{'action':'fade_in_end','value':5000},
    {'action':'fade_out_start','value':100000}]
  dest=self.out/'test.sesx'
  r=C.patch_native_sesx(NATIVE,dest,edits,confirm=True)
  a=C.inspect_native_sesx(dest)
  first=a['tracks'][0];clip=first['clips'][0]
  self.assertTrue(r['media_integrity'])
  self.assertTrue(r['source_unchanged'])
  self.assertEqual(first['name'],'New Test Voice')
  self.assertEqual(first['solo'],'false')
  self.assertEqual(first['armed'],'false')
  self.assertEqual(first['gain_linear'],'0.8')
  self.assertEqual(first['pan'],'-0.35')
  self.assertEqual(first['eq_powered'],'true')
  self.assertEqual(clip['gain_linear'],.6)
  self.assertEqual(clip['start_samples'],48000)
  self.assertEqual(clip['end_samples'],163200)
  self.assertEqual(clip['fade']['fadeIn']['endPoint'],'5000')
  self.assertEqual(clip['fade']['fadeOut']['startPoint'],'100000')
  self.assertEqual(hashlib.sha256(NATIVE.read_bytes()).hexdigest(),orig)
 def test_dry_run_no_output(self):
  out=self.out/'none.sesx'
  d=C.patch_native_sesx(NATIVE,out,[{'action':'pan','value':0.0}])
  self.assertTrue(d['dry_run'])
  self.assertFalse(out.exists())
 def test_unknown_action_rejected(self):
  with self.assertRaises(ValueError):C.patch_native_sesx(NATIVE,self.out/'x.sesx',[{'action':'run','value':1}],confirm=True)
 def test_invalid_track(self):
  with self.assertRaises(IndexError):C.patch_native_sesx(NATIVE,self.out/'x.sesx',[{'track':99,'action':'name','value':'Bad'}],confirm=True)
 def test_refuse_same(self):
  with self.assertRaises(ValueError):C.patch_native_sesx(NATIVE,NATIVE,[{'action':'name','value':'Bad'}],confirm=True)
 def test_refuse_existing(self):
  out=self.out/'x.sesx';out.write_bytes(b'old')
  with self.assertRaises(ValueError):C.patch_native_sesx(NATIVE,out,[{'action':'name','value':'Bad'}],confirm=True)
 def test_invalid_pan(self):
  with self.assertRaises(ValueError):C.patch_native_sesx(NATIVE,self.out/'x.sesx',[{'action':'pan','value':2}],confirm=True)
 def test_invalid_time(self):
  with self.assertRaises(ValueError):C.patch_native_sesx(NATIVE,self.out/'x.sesx',[{'action':'clip_start','value':-1}],confirm=True)
 def test_clip_absent(self):
  with self.assertRaises(IndexError):C.patch_native_sesx(NATIVE,self.out/'x.sesx',[{'action':'clip_gain','clip':50,'value':1}],confirm=True)
 def test_native_qa_session_name_whitelist(self):
  with self.assertRaises(PermissionError):C._qa_session_name('Personal_Session')
  self.assertEqual(C._qa_session_name('ACCEPT_AU_Test_123'),'ACCEPT_AU_Test_123')
 def test_multitrack_edit_dry_run(self):
  c=C()
  self.assertTrue(c.native_multitrack_edit_qa('ACCEPT_AU_Test_123',0,name='QA',confirm=False)['dry_run'])
 def test_multitrack_clip_pair(self):
  with self.assertRaises(ValueError):
   C().native_multitrack_edit_qa('ACCEPT_AU_Test_123',0,clip_index=0,confirm=True)
 def test_multitrack_mute_bool_required(self):
  with self.assertRaises(ValueError):
   C().native_multitrack_edit_qa('ACCEPT_AU_Test_123',0,mute='yes',confirm=True)
 def test_mixdown_refuses_nonqa_output(self):
  with self.assertRaises(PermissionError):
   C().native_multitrack_mixdown_qa('ACCEPT_AU_Test_123',self.out/'danger.wav',confirm=True)
 def test_mastering_dry_run(self):
  self.assertTrue(C.master_loudness(FIXTURE,self.out/'loud.wav',confirm=False)['dry_run'])
 def test_mastering_guard(self):
  with self.assertRaises(ValueError):
   C.master_loudness(FIXTURE,self.out/'bad.wav',target_lufs=-999,confirm=True)
 def test_mix_reject_one(self):
  with self.assertRaises(ValueError):
   C.mix_audio_stems([{'source':str(FIXTURE)}],self.out/'mix.wav',confirm=True)
 def test_mix_reject_duplicate(self):
  with self.assertRaises(ValueError):
   C.mix_audio_stems([{'source':str(FIXTURE)},{'source':str(FIXTURE)}],self.out/'mix.wav',confirm=True)
 def test_speech_chain_dry_run(self):
  r=C.speech_cleanup(FIXTURE,self.out/'speech.wav',confirm=False)
  self.assertTrue(r['dry_run'])
  self.assertTrue(any('afftdn=' in x for x in r['filters']))
 def test_speech_chain_guard(self):
  with self.assertRaises(ValueError):C.speech_cleanup(FIXTURE,self.out/'speech.wav',denoise_db=100,confirm=True)
 def test_add_track_dry_run(self):
  self.assertTrue(C().native_add_track_qa('ACCEPT_AU_DryRun_001',confirm=False)['dry_run'])
 def test_add_track_label_guard(self):
  with self.assertRaises(ValueError):C().native_add_track_qa('ACCEPT_AU_DryRun_001',label='User Track',confirm=True)
 def test_remove_track_dry_run(self):
  self.assertTrue(C().native_remove_empty_track_qa('ACCEPT_AU_DryRun_001',1,confirm=False)['dry_run'])
 def test_move_clip_dry_run(self):
  self.assertTrue(C().native_move_clip_qa('ACCEPT_AU_DryRun_001',0,1,confirm=False)['dry_run'])
 def test_move_clip_same_track_rejected(self):
  with self.assertRaises(ValueError):C().native_move_clip_qa('ACCEPT_AU_DryRun_001',0,0,confirm=True)
 def test_move_clip_start_rejected(self):
  with self.assertRaises(ValueError):C().native_move_clip_qa('ACCEPT_AU_DryRun_001',0,1,start_samples=-5,confirm=True)
if __name__=='__main__':unittest.main()
