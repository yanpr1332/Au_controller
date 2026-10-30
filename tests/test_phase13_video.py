from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from audition_controller import AuditionController as C,ROOT


class VideoDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'_runtime');self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)
        self.video=self.folder/'video.mp4';self.video.write_bytes(b'fixture')
        self.audio=ROOT/'tests/fixtures/accept_au_sine_48k_mono.wav'
        self.output=self.folder/'output.mp4'

    def test_dry_run_has_no_processing(self):
        with patch('controller_modules.video_delivery.subprocess.run') as command:
            result=C.mux_video_audio(self.video,self.audio,self.output,offset_seconds=.25)
        command.assert_not_called();self.assertTrue(result['dry_run']);self.assertFalse(self.output.exists())
        self.assertFalse(result['premiere_roundtrip_verified'])

    def test_refuse_existing_destination(self):
        self.output.write_bytes(b'keep')
        with self.assertRaises(ValueError):C.mux_video_audio(self.video,self.audio,self.output,confirm=True)
        self.assertEqual(self.output.read_bytes(),b'keep')

    def test_bad_offset_rejected(self):
        for value in (True,float('nan'),float('inf'),601):
            with self.subTest(value=value),self.assertRaises(ValueError):
                C.mux_video_audio(self.video,self.audio,self.output,offset_seconds=value)


if __name__=='__main__':unittest.main()
