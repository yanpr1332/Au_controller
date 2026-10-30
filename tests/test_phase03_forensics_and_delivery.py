from __future__ import annotations
import sys,unittest,tempfile
from pathlib import Path
import numpy as np
from scipy.io import wavfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audition_controller import AuditionController as C

class Phase03ForensicsAndDelivery(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d=Path(self.tmp.name)
        self.inputs=self.d/'inputs';self.inputs.mkdir()
        self.output=self.d/'out';self.output.mkdir()
        sr=48000;t=np.arange(sr*2,dtype=float)/sr
        x=.13*np.sin(2*np.pi*440*t)
        x[:int(sr*.3)]=0
        x[-int(sr*.3):]=0
        self.mono=self.inputs/'tone.wav';wavfile.write(self.mono,sr,x.astype(np.float32))
        self.stereo=self.inputs/'stereo.wav'
        wavfile.write(self.stereo,sr,np.column_stack((x,-x)).astype(np.float32))
    def test_tone_forensics(self):
        a=C.audio_forensics(self.mono)
        self.assertEqual(a['sample_rate'],48000)
        self.assertAlmostEqual(a['duration_seconds'],2)
        self.assertGreater(a['speech_presence_band_share'],.5)
        self.assertEqual(a['true_peak_factor'],4)
        self.assertLess(a['peak_dbfs'],-10)
    def test_silence_windows(self):
        a=C.audio_forensics(self.mono,window_ms=100)
        self.assertGreaterEqual(len(a['near_silence_regions_seconds']),2)
        self.assertGreater(a['near_silence_fraction'],.2)
    def test_antiphase_detection(self):
        a=C.audio_forensics(self.stereo)
        self.assertTrue(a['stereo']['anti_phase_warning'])
        self.assertLess(a['stereo']['correlation'],-.9)
        self.assertLess(a['stereo']['mono_fold_down_peak_dbfs'],-100)
    def test_crest(self):
        a=C.audio_forensics(self.mono)
        self.assertGreater(a['crest_db'],1)
    def test_invalid_window(self):
        with self.assertRaises(ValueError):C.audio_forensics(self.mono,window_ms=0)
    def test_invalid_truepeak(self):
        with self.assertRaises(ValueError):C.audio_forensics(self.mono,true_peak_factor=10)
    def test_profile_podcast(self):
        r=C.qc_audio_profile(self.mono,'podcast')
        self.assertTrue(r['passed'],r['checks'])
        self.assertFalse(r['broadcast_loudness_verified'])
    def test_profile_broadcast(self):
        r=C.qc_audio_profile(self.mono,'broadcast')
        self.assertTrue(r['passed'])
    def test_profile_invalid(self):
        with self.assertRaises(ValueError):C.qc_audio_profile(self.mono,'cinema')
    def test_custom_threshold(self):
        r=C.qc_audio_profile(self.mono,profile_override={'max_sample_peak_dbfs':-30})
        self.assertFalse(r['checks']['sample_peak_headroom'])
    def test_custom_profile_unknown_key(self):
        with self.assertRaises(ValueError):
            C.qc_audio_profile(self.mono,profile_override={'delete_input':1})
    def test_export_qc(self):
        d=self.output/'qa.json'
        a=C.export_audio_qc_report(self.mono,d,confirm=True)
        self.assertTrue(d.is_file());self.assertTrue(a['passed'])
    def test_export_qc_no_overwrite(self):
        d=self.output/'qa.json';d.write_text('old')
        with self.assertRaises(ValueError):C.export_audio_qc_report(self.mono,d,confirm=True)
    def test_export_dryrun(self):
        d=self.output/'qa.json'
        r=C.export_audio_qc_report(self.mono,d)
        self.assertTrue(r['dry_run']);self.assertFalse(d.exists())
    def test_delivery_dryrun(self):
        x=C.deliver_audio_batch([self.mono],self.output,formats=('wav','mp3'),confirm=False)
        self.assertEqual(x['jobs'][0]['files'].__len__(),2)
    def test_delivery_invalid_format(self):
        with self.assertRaises(ValueError):
            C.deliver_audio_batch([self.mono],self.output,formats=('wav','exe'))
    def test_delivery_invalid_preset(self):
        with self.assertRaises(ValueError):
            C.deliver_audio_batch([self.mono],self.output,preset='music_999')
    def test_delivery_duplicate_sources(self):
        with self.assertRaises(ValueError):
            C.deliver_audio_batch([self.mono,self.mono],self.output)
    def test_delivery_collision(self):
        (self.output/'tone_podcast_16.wav').write_bytes(b'x')
        with self.assertRaises(FileExistsError):
            C.deliver_audio_batch([self.mono],self.output)
    def test_delivery_reject_same_directory(self):
        with self.assertRaises(ValueError):
            C.deliver_audio_batch([self.mono],self.inputs)
    def test_delivery_wrong_denoise_type(self):
        with self.assertRaises(ValueError):
            C.deliver_audio_batch([self.mono],self.output,denoise='yes')
    def test_native_bus_marker_guard(self):
        c=C()
        with self.assertRaises(PermissionError):
            c.native_multitrack_marker_qa('user_session',start_samples=0,confirm=True)
        with self.assertRaises(ValueError):
            c.native_multitrack_marker_qa('ACCEPT_AU_TEST_001',start_samples=-1,confirm=True)
    def test_native_bus_guard(self):
        c=C()
        with self.assertRaises(ValueError):
            c.native_multitrack_add_bus_qa('ACCEPT_AU_TEST_001','unsafe',confirm=True)
        self.assertTrue(c.native_multitrack_add_bus_qa('ACCEPT_AU_TEST_001','QA Bus',confirm=False)['dry_run'])
        self.assertTrue(c.native_multitrack_remove_bus_qa('ACCEPT_AU_TEST_001',0,confirm=False)['dry_run'])
if __name__=='__main__':unittest.main()
