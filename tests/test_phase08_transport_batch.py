"""Phase 08: deterministic transport failure tests and fault-isolated batch delivery."""
from __future__ import annotations
import hashlib
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from audition_controller import AuditionController as C


class TransportBoundaryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="phase08_transport_", dir=ROOT / "tests")
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.controller = C()
        self.task_paths = []
        host_pid = patch.object(C, "_audition_pid", return_value=1234)
        host_pid.start()
        self.addCleanup(host_pid.stop)

    def fake_host(self, response: str | None):
        def launch(command, **kwargs):
            path = Path(command[-1])
            self.task_paths.append(path)
            script = path.read_text(encoding="utf-8-sig")
            marker = re.search(r'new File\("([^"]+)"\)', script)
            if marker is None:
                raise AssertionError("Missing JSX result file")
            if response is not None:
                Path(marker.group(1)).write_text(response, encoding="utf-8")
            return object()
        return launch

    def test_reply_error_is_exception_and_cleaned(self):
        with patch("audition_controller.RUNTIME_DIR", self.folder), \
             patch("audition_controller.subprocess.Popen", side_effect=self.fake_host("ERROR=Simulated host failure\n__DONE__=1\n")):
            with self.assertRaisesRegex(RuntimeError, "Simulated host failure"):
                self.controller._run_jsx('out("TEST","1");', "error_qa", .4)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_timeout_is_bounded_and_cleaned(self):
        with patch("audition_controller.RUNTIME_DIR", self.folder), \
             patch("audition_controller.subprocess.Popen", side_effect=self.fake_host(None)):
            with self.assertRaises(TimeoutError):
                self.controller._run_jsx('out("TEST","1");', "timeout_qa", .02)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_two_calls_distinct_paths(self):
        with patch("audition_controller.RUNTIME_DIR", self.folder), \
             patch("audition_controller.subprocess.Popen", side_effect=self.fake_host("VALUE=a=b\n__DONE__=1\n")):
            one = self.controller._run_jsx('out("VALUE","a=b");', "same", .4)
            two = self.controller._run_jsx('out("VALUE","a=b");', "same", .4)
        self.assertEqual(one["VALUE"], "a=b")
        self.assertEqual(two["VALUE"], "a=b")
        self.assertNotEqual(self.task_paths[0], self.task_paths[1])
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_invalid_timeout_and_name_rejected_before_spawn(self):
        with patch("audition_controller.subprocess.Popen") as spawn:
            for value in (0, -1, float("nan"), 601, True):
                with self.subTest(timeout=value), self.assertRaises(ValueError):
                    self.controller._run_jsx("out('X',1)", "task", value)
            with self.assertRaises(ValueError):
                self.controller._run_jsx("out('X',1)", "../path", 1)
            spawn.assert_not_called()


class BatchDeliveryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="phase08_batch_", dir=ROOT / "tests")
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name)
        self.source = ROOT / "tests/fixtures/accept_au_sine_48k_mono.wav"

    def test_dryrun_writes_nothing(self):
        result = C.batch_transcode_audio([self.source], self.dir, fmt="flac")
        self.assertTrue(result["dry_run"])
        self.assertFalse(list(self.dir.iterdir()))

    def test_rejects_existing_output(self):
        p = self.dir / (self.source.stem + "_deliver.flac")
        p.write_bytes(b"do not touch")
        with self.assertRaises(FileExistsError):
            C.batch_transcode_audio([self.source], self.dir, confirm=True)
        self.assertEqual(p.read_bytes(), b"do not touch")

    def test_rejects_duplicate_inputs(self):
        with self.assertRaises(ValueError):
            C.batch_transcode_audio([self.source, self.source], self.dir)

    def test_rejects_unsafe_suffix(self):
        with self.assertRaises(ValueError):
            C.batch_transcode_audio([self.source], self.dir, suffix="../../x")

    def test_validates_audio_arguments_in_dryrun(self):
        with self.assertRaises(ValueError):
            C.batch_transcode_audio([self.source], self.dir, rate=12)

    def test_failure_isolation_and_success_hash(self):
        missing = self.dir / "missing.wav"
        h = hashlib.sha256(self.source.read_bytes()).hexdigest()

        def fake_convert(src, dst, **kwargs):
            Path(dst).write_bytes(b"fLaC" + b"test-media" * 128)
            return {"codec": "flac", "sample_rate": 48000, "channels": 2}

        with patch("controller_modules.batch_delivery.AuditionFFmpegLab.transcode_audio", side_effect=fake_convert):
            r = C.batch_transcode_audio([missing, self.source], self.dir, confirm=True)
        self.assertEqual((r["passed"], r["failed"], r["skipped"]), (1, 1, 0))
        self.assertEqual(r["jobs"][0]["status"], "failed")
        self.assertEqual(r["jobs"][1]["status"], "passed")
        self.assertEqual(r["jobs"][1]["source_sha256"], h)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), h)
        self.assertEqual(sorted(x.name for x in self.dir.iterdir()),
                         [self.source.stem + "_deliver.flac"])

    def test_stop_on_error_skips_remaining(self):
        missing = self.dir / "missing.wav"
        r = C.batch_transcode_audio([missing, self.source], self.dir,
                                    confirm=True, stop_on_error=True)
        self.assertEqual((r["passed"], r["failed"], r["skipped"]), (0, 1, 1))
        self.assertEqual(r["jobs"][1]["status"], "skipped")
        self.assertFalse(list(self.dir.glob("*.flac")))

    def test_transcode_exception_leaves_no_partial(self):
        def bad_convert(src, dst, **kwargs):
            Path(dst).write_bytes(b"partial")
            raise RuntimeError("simulated conversion failure")
        with patch("controller_modules.batch_delivery.AuditionFFmpegLab.transcode_audio", side_effect=bad_convert):
            r = C.batch_transcode_audio([self.source], self.dir, confirm=True)
        self.assertEqual(r["failed"], 1)
        self.assertEqual(list(self.dir.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
