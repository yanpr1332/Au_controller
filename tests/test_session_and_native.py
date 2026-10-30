import sys,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audition_controller import AuditionController
class SessionAndNativeTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory()
  self.addCleanup(self.temp.cleanup)
  self.folder=Path(self.temp.name)
  self.source=self.folder/'fixture.sesx'
  self.source.write_text('<?xml version="1.0" encoding="utf-8"?><sesx version="1.1"><session><tracks>'
   '<audioTrack name="Voice"><trackAudioParameters>'
   '<component id="trackFader"><parameter name="volume" parameterValue="1"/></component>'
   '<component id="trackPan"><parameter name="Pan" parameterValue="0"/></component>'
   '<component id="trackEQ" powered="false"><parameter name="EQ Band 3 Gain" parameterValue="0"/></component>'
   '</trackAudioParameters>'
   '<audioClip name="clip" startTime="0"><component id="clipGain"><parameter name="volume" parameterValue="1"/></component>'
   '<fadeIn startPoint="0" endPoint="0"/><fadeOut startPoint="999"/></audioClip>'
   '</audioTrack></tracks></session></sesx>',encoding='utf8')
 def test_inspect_sesx(self):
  a=AuditionController.inspect_sesx(self.source)
  self.assertEqual(a['track_count'],1)
  self.assertEqual(a['tracks'][0]['clip_count'],1)
 def test_patch_sesx_full(self):
  edits=[{'action':'track_name','value':'Narration'},
         {'action':'track_volume','value':.7},
         {'action':'track_pan','value':-.3},
         {'action':'eq_enabled','value':True},
         {'action':'eq_band3_gain','value':-4},
         {'action':'clip_gain','value':.8},
         {'action':'clip_start_samples','value':480},
         {'action':'fade_in_samples','value':250},
         {'action':'fade_out_start_samples','value':900}]
  result=AuditionController.patch_sesx(self.source,self.folder/'changed.sesx',edits,confirm=True)
  self.assertEqual(result['changes'],9)
  a=AuditionController.inspect_sesx(self.folder/'changed.sesx')
  self.assertEqual(a['tracks'][0]['name'],'Narration')
  self.assertEqual(a['tracks'][0]['components']['trackPan']['params']['Pan'],'-0.3')
  self.assertEqual(a['tracks'][0]['clips'][0]['fade_in']['endPoint'],'250')
  self.assertEqual(a['tracks'][0]['clips'][0]['attrib']['startTime'],'480')
  self.assertFalse(result['native_audition_session_opened'])
 def test_patch_dry_run(self):
  out=self.folder/'none.sesx'
  r=AuditionController.patch_sesx(self.source,out,[{'action':'track_name','value':'QA'}])
  self.assertTrue(r['dry_run']);self.assertFalse(out.exists())
 def test_patch_overwrite_refused(self):
  with self.assertRaises(ValueError):
   AuditionController.patch_sesx(self.source,self.source,[{'action':'track_name','value':'QA'}],confirm=True)
 def test_reject_invalid_track(self):
  with self.assertRaises(IndexError):
   AuditionController.patch_sesx(self.source,self.folder/'out.sesx',
     [{'track':12,'action':'track_name','value':'QA'}],confirm=True)
 def test_reject_numeric_bounds(self):
  with self.assertRaises(ValueError):
   AuditionController.patch_sesx(self.source,self.folder/'out.sesx',
     [{'action':'track_volume','value':-99}],confirm=True)
 def test_reject_unsafe_operation(self):
  with self.assertRaises(ValueError):
   AuditionController.patch_sesx(self.source,self.folder/'out.sesx',
     [{'action':'runShellCommand','value':'bad'}],confirm=True)
 def test_native_guard_source(self):
  with self.assertRaises(PermissionError):
   AuditionController().audition_native_marker_export(self.source,self.folder/'out.wav',start_samples=0,confirm=True)
 def test_native_guard_favorite(self):
  fixture=Path(__file__).resolve().parent/'fixtures'/'accept_au_sine_48k_mono.wav'
  output=Path(__file__).resolve().parent/'native_outputs'/'test_fake.wav'
  ctl=AuditionController()
  with self.assertRaises(ValueError):
   ctl.audition_native_favorite_export(fixture,output,favorite='ExecuteArbitrary',confirm=True)
 def test_command_bad_expression(self):
  ctl=AuditionController()
  with self.assertRaises(ValueError):ctl.audition_command_probe(['File.Save;app.quit()'])
 def test_command_reflect_whitelist(self):
  ctl=AuditionController()
  with self.assertRaises(ValueError):ctl.audition_reflect('eval')
 def test_ffmpeg_unknown_format(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'in.wav';p.write_bytes(b'RIFF')
   with self.assertRaises(ValueError):AuditionController.transcode_audio(p,Path(d)/'out.avi')
 def test_ffmpeg_no_overwrite(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'in.wav';p.write_bytes(b'RIFF')
   with self.assertRaises(ValueError):AuditionController.transcode_audio(p,p,confirm=True)
if __name__=='__main__':unittest.main()
