import gzip
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from audition_controller import AuditionController as C


class CompletedDiagnosticsTests(unittest.TestCase):
    def test_snapshot_uses_live_readonly_dom(self):
        c=C()
        with patch.object(c,'_run_jsx',return_value={'DOCUMENTS':'0'}) as call:
            self.assertEqual(c.native_document_snapshot()['DOCUMENTS'],'0')
        self.assertIn('startTime',call.call_args.args[0])
        self.assertNotIn('closeDocument',call.call_args.args[0])

    def test_omf_hash_and_host_visibility_do_not_claim_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'test.omf';p.write_bytes(b'qa')
            c=C()
            with patch.object(c,'_run_jsx',return_value={'EXISTS':'true'}):r=c.inspect_native_omf(p)
            self.assertEqual(r['bytes'],2);self.assertFalse(r['roundtrip_verified'])

    def test_page_dimensions_and_invalid_receipts(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'page.json'
            for width,zero in [(0,True),(540,False)]:
                p.write_text(json.dumps(dict(stage='loaded',width=width,height=440)),encoding='utf8')
                self.assertEqual(C.inspect_cep_receipt(p)['zero_viewport'],zero)
            p.write_text('{"stage":"loaded","width":true,"height":440}',encoding='utf8')
            with self.assertRaises(ValueError):C.inspect_cep_receipt(p)

    def test_handshake_does_not_claim_visual_success(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'host.txt';p.write_text('HOST=Audition\nREFLECT_CLASS=Application\nVERSION=26.0.0',encoding='utf8')
            r=C.inspect_cep_receipt(p)
            self.assertTrue(r['host_callback_recorded']);self.assertFalse(r['visual_rendering_verified'])

    def test_compressed_project_reference(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'qa.prproj';p.write_bytes(gzip.compress(b'<Project>test.mp4</Project>'))
            r=C.inspect_premiere_project_reference(p,'test.mp4')
            self.assertTrue(r['media_reference_present']);self.assertFalse(r['premiere_roundtrip_verified'])
            self.assertFalse(C.inspect_premiere_project_reference(p,'missing.mp4')['media_reference_present'])
