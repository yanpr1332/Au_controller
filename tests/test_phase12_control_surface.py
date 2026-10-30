import unittest
from unittest.mock import patch
from audition_controller import AuditionController as C


class ControlSurfaceTests(unittest.TestCase):
    def test_cc_roundtrip(self):
        encoded=C.midi_control_message(16,127,64)
        decoded=C.decode_midi_message(encoded['packed'])
        self.assertEqual((decoded['type'],decoded['channel'],decoded['data1'],decoded['data2']),('control_change',16,127,64))

    def test_pitch_bend_14bit(self):
        self.assertEqual(C.decode_midi_message(0x7f7fe0)['pitch_bend'],16383)

    def test_invalid_values(self):
        for args in ((0,1,1),(1,128,1),(1,1,True)):
            with self.assertRaises(ValueError):C.midi_control_message(*args)
        with self.assertRaises(ValueError):C.decode_midi_message(0xff)

    def test_send_dry_run_never_opens_device(self):
        with patch.object(C,'_midi_devices',return_value=[{'id':0,'name':'Test'}]),patch('controller_modules.control_surface.ctypes.WinDLL') as loader:
            result=C.send_midi_control(0,channel=1,controller=7,value=100)
        self.assertTrue(result['dry_run']);loader.assert_not_called()

    def test_no_input_is_explicit(self):
        with patch.object(C,'_midi_devices',return_value=[]):
            with self.assertRaises(ValueError):C.listen_midi_controls(0,confirm=True)


if __name__=='__main__':unittest.main()
