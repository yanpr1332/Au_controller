"""Phase09 regression: safety and real-media receipts without mutating host."""
from __future__ import annotations
import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from audition_controller import AuditionController as C


class Phase09QA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=ROOT/"tests/fixtures/accept_au_sine_48k_mono.wav"
        cls.fixture2=ROOT/"tests/fixtures/accept_batch_source_1.wav"
        cls.session=ROOT/"tests/native_outputs/ACCEPT_AU_Phase09D_state_roundtrip.sesx"
        cls.qa_out=ROOT/"tests/native_outputs"

    def test_track_dryrun(self):
        self.assertTrue(C().native_track_state_roundtrip_qa(self.session)["dry_run"])
    def test_track_bad_index(self):
        with self.assertRaises(ValueError):
            C().native_track_state_roundtrip_qa(self.session,track_index=True)
    def test_track_arm_bool(self):
        with self.assertRaises(ValueError):
            C().native_track_state_roundtrip_qa(self.session,armed=1)
    def test_track_source_guard(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/"ACCEPT_AU_other.sesx"
            src.write_bytes(self.session.read_bytes())
            with self.assertRaises(PermissionError):
                C().native_track_state_roundtrip_qa(src)
    def test_native_batch_import_dryrun(self):
        self.assertEqual(C().native_batch_open_qa([self.fixture,self.fixture2])["count"],2)
    def test_native_batch_import_duplicates(self):
        with self.assertRaises(PermissionError):
            C().native_batch_open_qa([self.fixture,self.fixture])
    def test_native_batch_import_scope(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/"source.wav"
            src.write_bytes(self.fixture.read_bytes())
            with self.assertRaises(PermissionError):
                C().native_batch_open_qa([src])
    def test_native_batch_favorite_plan(self):
        v=C().native_batch_process_qa([self.fixture,self.fixture2],self.qa_out)
        self.assertTrue(v["dry_run"])
        self.assertEqual(len(v["outputs"]),2)
    def test_native_batch_bad_favorite(self):
        with self.assertRaises(ValueError):
            C().native_batch_process_qa([self.fixture],self.qa_out,favorite="Run Arbitrary")
    def test_native_batch_bad_suffix(self):
        with self.assertRaises(ValueError):
            C().native_batch_process_qa([self.fixture],self.qa_out,suffix="../foo")
    def test_native_batch_duplicate_sources(self):
        with self.assertRaises(ValueError):
            C().native_batch_process_qa([self.fixture,self.fixture],self.qa_out)
    def test_native_batch_bad_format(self):
        with self.assertRaises(ValueError):
            C().native_batch_process_qa([self.fixture],self.qa_out,task="resample",rate=123)
    def test_marker_dryrun(self):
        output=self.qa_out/"phase09_DRYRUN_TEST.wav"
        self.assertTrue(C().native_wave_markers_qa(self.fixture,output)["dry_run"])
        self.assertFalse(output.exists())
    def test_marker_guard(self):
        with self.assertRaises((ValueError,PermissionError)):
            C().native_wave_markers_qa(self.fixture,self.fixture)
    def test_batch_loudness_dryrun(self):
        with tempfile.TemporaryDirectory() as d:
            x=C.batch_loudness_master([self.fixture],d)
            self.assertTrue(x["dry_run"])
            self.assertFalse(list(Path(d).iterdir()))
    def test_batch_loudness_invalid_level(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                C.batch_loudness_master([self.fixture],d,target_lufs=-4)
    def test_batch_loudness_duplicate_sources(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                C.batch_loudness_master([self.fixture,self.fixture],d)
    def test_batch_loudness_collision(self):
        with tempfile.TemporaryDirectory() as d:
            dst=Path(d)/(self.fixture.stem+"_loudness.wav")
            dst.write_bytes(b"guard")
            with self.assertRaises(FileExistsError):
                C.batch_loudness_master([self.fixture],d,confirm=True)
            self.assertEqual(dst.read_bytes(),b"guard")
    def test_real_track_and_import_receipt(self):
        a=json.loads((ROOT/"tests/receipts/phase09_native_acceptance.json").read_text(encoding="utf-8"))
        self.assertTrue(a["passed"])
        self.assertTrue(a["checks"]["native_armed_toggle"])
        self.assertTrue(a["checks"]["native_visible_toggle"])
        self.assertTrue(a["checks"]["native_batch_import"])
    def test_real_native_batch_receipt(self):
        r=json.loads((ROOT/"tests/receipts/phase09_native_batch_acceptance.json").read_text(encoding="utf-8"))
        self.assertTrue(r["passed"])
        self.assertEqual(r["favorite"]["passed"],3)
        self.assertEqual(r["resample"]["passed"],3)
    def test_real_marker_types_receipt(self):
        r=json.loads((ROOT/"tests/receipts/phase09_native_markers.json").read_text(encoding="utf-8"))
        self.assertTrue(r["passed"])
        self.assertEqual(r["verified_count"],3)
        self.assertTrue(r["supports_distinct_type"])
        self.assertEqual(r["first_save"]["ERROR_cd"],"Error: Invalid marker type.")
    def test_real_offline_batch_receipt(self):
        r=json.loads((ROOT/"tests/receipts/phase09_offline_batch_acceptance.json").read_text(encoding="utf-8"))
        self.assertTrue(r["passed"])
        self.assertEqual(r["batch_master"]["passed"],2)
        self.assertEqual(r["batch_master"]["failed"],1)
        self.assertEqual(r["batch_mp3"]["passed"],2)


if __name__=="__main__":
    unittest.main()
