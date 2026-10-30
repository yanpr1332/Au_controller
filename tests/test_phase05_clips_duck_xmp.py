from __future__ import annotations
import sys,unittest,tempfile,hashlib,json
from pathlib import Path
from scipy.io import wavfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audition_controller import AuditionController as C
R=Path(__file__).resolve().parents[1]
SE=R/'tests/native_outputs/ACCEPT_AU_Phase04_bus_pruned.sesx'
MIX=R/'tests/native_outputs/phase04_portable_native_mix.wav'
VOICE=R/'tests/fixtures/accept_phase05_duck_voice.wav'
MUSIC=R/'tests/fixtures/accept_phase05_duck_music.wav'

class Phase05AdvancedTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(prefix='phase05_unit_',dir=str(R/'tests'))
        self.addCleanup(self.t.cleanup)
        self.folder=Path(self.t.name)
        self.dst=self.folder/'ACCEPT_AU_NewSession.sesx'
    def edit(self,action,value,**extras):
        v={'track':0,'clip':0,'action':action,'value':value}
        v.update(extras)
        return C.patch_native_clip_advanced(SE,self.dst,[v],confirm=True)
    def test_native_clip_inventory(self):
        a=C.inspect_native_clips_advanced(SE)
        self.assertEqual(a['clip_count'],1)
        self.assertEqual(a['clips'][0]['start'],24000)
        self.assertEqual(a['clips'][0]['source_out'],115200)
    def test_native_clip_move(self):
        self.edit('move',48000)
        a=C.inspect_native_clips_advanced(self.dst)['clips'][0]
        self.assertEqual(a['start'],48000)
        self.assertEqual(a['end'],163200)
    def test_native_clip_trim(self):
        self.edit('trim_source',{'in_samples':2000,'out_samples':80000})
        a=C.inspect_native_clips_advanced(self.dst)['clips'][0]
        self.assertEqual(a['source_in'],2000)
        self.assertEqual(a['source_out'],80000)
        self.assertEqual(a['end'],102000)
    def test_native_clip_mute(self):
        self.edit('mute',True)
        self.assertTrue(C.inspect_native_clips_advanced(self.dst)['clips'][0]['muted'])
    def test_native_clip_lock(self):
        self.edit('lock',True)
        self.assertTrue(C.inspect_native_clips_advanced(self.dst)['clips'][0]['locked_in_time'])
    def test_native_clip_loop_flag(self):
        self.edit('loop',True)
        self.assertTrue(C.inspect_native_clips_advanced(self.dst)['clips'][0]['looped'])
    def test_native_clip_fadein(self):
        self.edit('fade',{'edge':'in','length_samples':5000})
        f=C.inspect_native_clips_advanced(self.dst)['clips'][0]['fade_in']
        self.assertEqual(f['endPoint'],'5000')
    def test_native_clip_fadeout(self):
        self.edit('fade',{'edge':'out','length_samples':2500})
        f=C.inspect_native_clips_advanced(self.dst)['clips'][0]['fade_out']
        self.assertEqual(f['startPoint'],'112700')
    def test_native_clip_patch_dryrun(self):
        x=C.patch_native_clip_advanced(SE,self.dst,[{'track':0,'clip':0,'action':'move','value':42}])
        self.assertTrue(x['dry_run'])
        self.assertFalse(self.dst.exists())
    def test_native_clip_no_overwrite(self):
        self.dst.write_text('do not touch')
        with self.assertRaises(ValueError):
            self.edit('mute',True)
        self.assertEqual(self.dst.read_text(),'do not touch')
    def test_native_clip_trim_expansion_rejected(self):
        with self.assertRaises(ValueError):
            self.edit('trim_source',{'in_samples':0,'out_samples':115300})
    def test_native_clip_bad_fade(self):
        with self.assertRaises(ValueError):
            self.edit('fade',{'edge':'in','length_samples':1000000})
    def test_native_clip_bad_muted_type(self):
        with self.assertRaises(ValueError):
            self.edit('mute','true')
    def test_native_clip_invalid_operation(self):
        with self.assertRaises(ValueError):
            self.edit('create_vst',True)
    def test_native_clip_source_preserved(self):
        digest=hashlib.sha256(SE.read_bytes()).hexdigest()
        self.edit('lock',True)
        self.assertEqual(hashlib.sha256(SE.read_bytes()).hexdigest(),digest)
    def test_native_clip_real_acceptance(self):
        p=json.loads((R/'tests/receipts/phase05_native_clip_trim_fade_acceptance.json').read_text(encoding='utf8'))
        self.assertEqual(p['live']['TRACK0_CLIP0_START'],'48000')
        self.assertEqual(p['live']['TRACK0_CLIP0_DURATION'],'78000')
        self.assertEqual(p['audio']['clipped_samples'],0)
        self.assertEqual(p['audio']['frames'],126000)
    def test_xmp_markers(self):
        markers=C.native_sesx_markers_xmp(SE)
        self.assertEqual(markers['count'],2)
        self.assertEqual(markers['sample_rate'],48000)
        self.assertEqual(markers['markers'][0]['start_samples'],48000)
    def test_xmp_order(self):
        markers=C.native_sesx_markers_xmp(SE)['markers']
        self.assertLess(markers[0]['start_samples'],markers[1]['start_samples'])
    def test_chapter_dryrun(self):
        v=C.export_native_marker_chapters(SE,MIX,self.folder)
        self.assertEqual(len(v['regions']),2)
        self.assertFalse(any(self.folder.glob('QA_CHAPTER_*.wav')))
    def test_chapter_real_export(self):
        a=C.export_native_marker_chapters(SE,MIX,self.folder,confirm=True)
        self.assertEqual(a['count'],2)
        self.assertTrue(a['source_unchanged'])
        self.assertEqual(a['chapters'][0]['frames'],48000)
        self.assertEqual(a['chapters'][1]['frames'],10000)
    def test_chapter_overwrite_guard(self):
        (self.folder/'QA_CHAPTER_01_QA_Section_1.wav').write_bytes(b'NO')
        with self.assertRaises(FileExistsError):
            C.export_native_marker_chapters(SE,MIX,self.folder,confirm=True)
    def test_chapter_invalid_fade(self):
        with self.assertRaises(ValueError):
            C.export_native_marker_chapters(SE,MIX,self.folder,fade_ms=100,confirm=True)
    def test_chapter_receipt(self):
        p=json.loads((R/'tests/receipts/phase05_xmp_chapter_acceptance.json').read_text(encoding='utf8'))
        self.assertEqual(p['export']['count'],2)
    def test_duck_dryrun(self):
        a=C.duck_music_under_dialogue(VOICE,MUSIC,self.folder/'mix.wav')
        self.assertTrue(a['dry_run'])
        self.assertIn('sidechaincompress',a['filter_graph'])
    def test_duck_invalid_threshold(self):
        with self.assertRaises(ValueError):
            C.duck_music_under_dialogue(VOICE,MUSIC,self.folder/'mix.wav',threshold=-1,confirm=True)
    def test_duck_destination_collides(self):
        with self.assertRaises(ValueError):
            C.duck_music_under_dialogue(VOICE,MUSIC,MUSIC,confirm=True)
    def test_duck_proof(self):
        p=json.loads((R/'tests/receipts/phase05_ducking_and_mastering.json').read_text(encoding='utf8'))
        self.assertLess(p['music_suppression_db'],-5)
        self.assertTrue(p['duck']['audio_quality_ok'])
        self.assertTrue(p['master']['passed'])
    def test_duck_master_dryrun(self):
        p=C.podcast_sidechain_delivery(VOICE,MUSIC,self.folder/'master.wav',confirm=False)
        self.assertTrue(p['dry_run'])
    def test_cep_manifest_cep12_compatible(self):
        from lxml import etree as ET
        m=ET.parse(str(R/'cep/com.openai.audition.inspector/CSXS/manifest.xml'))
        host=m.find('.//Host')
        self.assertEqual(host.get('Name'),'AUDT')
        self.assertEqual(host.get('Version'),'[25.0,99.9]')
    def test_cep_not_improperly_certified(self):
        p=json.loads((R/'tests/receipts/phase05_cep_manifest_correction.json').read_text(encoding='utf8'))
        self.assertFalse(p['host_launched'])

if __name__=='__main__':unittest.main()
