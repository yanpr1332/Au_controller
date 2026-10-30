from __future__ import annotations
import json,hashlib,tempfile,unittest,sys
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from lxml import etree as ET
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from audition_controller import AuditionController as C
WAV=R/'tests/fixtures/accept_au_sine_48k_mono.wav'
SESX=R/'tests/native_outputs/ACCEPT_AU_Phase04_bus_pruned.sesx'

class Phase07WaveAndNativeSplit(unittest.TestCase):
 def setUp(self):
  tmp=tempfile.TemporaryDirectory(prefix='phase07_wave_',dir=str(R/'tests'))
  self.addCleanup(tmp.cleanup);self.work=Path(tmp.name)
  self.dest=self.work/'new.wav';self.sesx=self.work/'ACCEPT_AU_split.sesx'
 def edit(self,ops,**kw):
  return C.edit_wav_timeline(WAV,self.dest,ops,confirm=True,**kw)
 def test_edit_source_gain_and_region(self):
  sr,old=wavfile.read(WAV)
  r=self.edit([{'action':'gain_region','start':30000,'end':30600,'db':-6}])
  rr,new=wavfile.read(self.dest)
  self.assertTrue(r['passed'])
  self.assertEqual(len(old),len(new));self.assertEqual(sr,rr)
  self.assertTrue(np.allclose(new[:150],old[:150],rtol=1e-5,atol=1e-6))
  self.assertGreater(np.max(np.abs(old[30100:30500])),0)
  self.assertTrue(np.max(np.abs(new[30100:30500]))<np.max(np.abs(old[30100:30500].astype(float)/32768)))
 def test_edit_delete_range(self):
  sr,data=wavfile.read(WAV)
  r=self.edit([{'action':'delete','start':0,'end':1000}])
  self.assertEqual(r['output_frames'],len(data)-1000)
 def test_edit_cut_alias(self):
  sr,data=wavfile.read(WAV)
  r=self.edit([{'action':'cut','start':100,'end':700}])
  self.assertEqual(r['output_frames'],len(data)-600)
 def test_insert_silence(self):
  sr,data=wavfile.read(WAV)
  r=self.edit([{'action':'insert_silence','at':200,'frames':350}])
  self.assertEqual(r['output_frames'],len(data)+350)
  rate,out=wavfile.read(self.dest)
  self.assertEqual(np.count_nonzero(out[200:550]),0)
 def test_region_silence(self):
  self.edit([{'action':'silence','start':400,'end':800}])
  sr,out=wavfile.read(self.dest)
  self.assertEqual(np.count_nonzero(out[400:800]),0)
 def test_copy_insert(self):
  sr,data=wavfile.read(WAV)
  r=self.edit([{'action':'copy_insert','at':0,'from_start':1000,'from_end':1500}])
  self.assertEqual(r['output_frames'],len(data)+500)
  sr,out=wavfile.read(self.dest)
  self.assertTrue(np.allclose(out[:500],data[1000:1500],atol=1e-7))
 def test_region_fade_in(self):
  self.edit([{'action':'fade_region','start':0,'end':2000,'edge':'in'}])
  sr,out=wavfile.read(self.dest)
  self.assertAlmostEqual(float(out[0]),0,places=7)
 def test_pcm16_dither_tpdf(self):
  r=self.edit([{'action':'silence','start':0,'end':2000}],format='pcm16',dither='tpdf')
  self.assertEqual(r['format'],'pcm16')
  sr,out=wavfile.read(self.dest)
  self.assertEqual(out.dtype,np.dtype('int16'))
 def test_pcm16_dither_feedback(self):
  r=self.edit([{'action':'silence','start':0,'end':2000}],format='pcm16',dither='tpdf_feedback')
  self.assertEqual(r['dither'],'tpdf_feedback')
  self.assertGreater(self.dest.stat().st_size,1000)
 def test_dither_repeatable_with_same_seed(self):
  op=[{'action':'silence','start':0,'end':5000}]
  first=self.edit(op,format='pcm16',dither='tpdf',seed=42)
  second=self.work/'second.wav'
  res=C.edit_wav_timeline(WAV,second,op,format='pcm16',dither='tpdf',seed=42,confirm=True)
  self.assertEqual(first['output_sha256'],res['output_sha256'])
 def test_dither_changes_seed(self):
  op=[{'action':'silence','start':0,'end':5000}]
  first=self.edit(op,format='pcm16',dither='tpdf',seed=1)
  second=C.edit_wav_timeline(WAV,self.work/'other.wav',op,format='pcm16',dither='tpdf',seed=2,confirm=True)
  self.assertNotEqual(first['output_sha256'],second['output_sha256'])
 def test_no_dither_for_float(self):
  with self.assertRaises(ValueError):
   C.edit_wav_timeline(WAV,self.dest,[{'action':'cut','start':0,'end':1}],dither='tpdf')
 def test_no_destination_override(self):
  self.dest.write_bytes(b'NO')
  with self.assertRaises(ValueError):
   self.edit([{'action':'cut','start':0,'end':1000}])
  self.assertEqual(self.dest.read_bytes(),b'NO')
 def test_invalid_fade_edge(self):
  with self.assertRaises(ValueError):
   self.edit([{'action':'fade_region','start':0,'end':100,'edge':'unsafe'}])
 def test_invalid_region_bound(self):
  with self.assertRaises(ValueError):
   self.edit([{'action':'delete','start':10,'end':99999999}])
  self.assertFalse(self.dest.exists())
 def test_dryrun_is_readonly(self):
  r=C.edit_wav_timeline(WAV,self.dest,[{'action':'cut','start':0,'end':10}])
  self.assertTrue(r['dry_run']);self.assertFalse(self.dest.exists())
 def test_fft_actual(self):
  outfile=self.work/'fft.json'
  r=C.export_fft_spectrum(WAV,outfile,confirm=True)
  self.assertGreater(r['bins'],200)
  self.assertLess(abs(r['dominant_frequency_hz']-440),10)
  self.assertEqual(hashlib.sha256(outfile.read_bytes()).hexdigest(),r['sha256'])
 def test_waveform_acceptance_receipt(self):
  r=json.loads((R/'tests/receipts/phase07_waveform_timeline_acceptance.json').read_text(encoding='utf8'))
  self.assertTrue(r['source_intact'] and r['different_dither_files'])
  self.assertEqual(len(r['results']),3)
 def test_split_dry_run(self):
  r=C.split_native_qa_clip(SESX,self.sesx,offset_samples=48000)
  self.assertTrue(r['dry_run']);self.assertFalse(self.sesx.exists())
 def test_split_new_sesx(self):
  origin=hashlib.sha256(SESX.read_bytes()).hexdigest()
  r=C.split_native_qa_clip(SESX,self.sesx,offset_samples=48000,confirm=True)
  self.assertEqual(r['new_clip_count'],2)
  self.assertEqual(hashlib.sha256(SESX.read_bytes()).hexdigest(),origin)
  clip=C.inspect_native_sesx(self.sesx)['tracks'][0]['clips']
  self.assertEqual([x['start_samples'] for x in clip],[24000,72000])
  self.assertEqual([x['end_samples'] for x in clip],[72000,139200])
 def test_split_no_overwrite(self):
  self.sesx.write_bytes(b'keep')
  with self.assertRaises(ValueError):
   C.split_native_qa_clip(SESX,self.sesx,offset_samples=48000,confirm=True)
  self.assertEqual(self.sesx.read_bytes(),b'keep')
 def test_split_outside_duration(self):
  with self.assertRaises(ValueError):
   C.split_native_qa_clip(SESX,self.sesx,offset_samples=115200,confirm=True)
 def test_split_nonqa_filename_rejected(self):
  with self.assertRaises(ValueError):
   C.split_native_qa_clip(SESX,self.work/'unsafe.sesx',offset_samples=48000,confirm=True)
 def test_split_looped_refused(self):
  t=ET.parse(str(SESX))
  t.find('.//audioClip').set('looped','true')
  inp=self.work/'ACCEPT_AU_loop.sesx';t.write(str(inp),encoding='utf8',xml_declaration=True)
  with self.assertRaises(PermissionError):
   C.split_native_qa_clip(inp,self.sesx,offset_samples=48000,confirm=True)
 def test_split_native_mixdown_receipt(self):
  r=json.loads((R/'tests/receipts/phase07_native_split_acceptance.json').read_text(encoding='utf8'))
  self.assertTrue(r['native_reopen_verified'])
  self.assertEqual(r['snapshot']['TRACK0_CLIPS'],'2')
  self.assertEqual(r['frames'],139200)
  self.assertLess(r['max_absolute_difference_from_original'],1e-9)
 def test_split_source_closure(self):
  self.assertTrue(json.loads((R/'tests/receipts/phase07_qa_closed.json').read_text(encoding='utf8'))['documents_zero'])

if __name__=='__main__':unittest.main()
