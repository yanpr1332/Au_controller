import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from audition_controller import AuditionController as C, ROOT


class ProductionSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / '_runtime')
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.source = ROOT / 'tests/native_outputs/ACCEPT_AU_Phase06_multi_arrangement.sesx'
        self.output = self.folder / 'production.sesx'
        info = C.inspect_native_sesx(self.source)
        _, _, _, tracks = C._native_tree(self.source)
        self.track = next(t for t in tracks if t.findall('audioClip'))
        self.clip = self.track.find('audioClip')
        self.base = dict(track_id=self.track.get('id'), clip_id=self.clip.get('id'))
        self.before = hashlib.sha256(self.source.read_bytes()).hexdigest()

    def edit(self, action, **kw):
        return C.edit_production_session(self.source, self.output, [dict(self.base, action=action, **kw)], confirm=True)

    def test_copy_preserves_source(self):
        old = C.inspect_native_sesx(self.source)['clip_count']
        self.edit('copy', start_samples=500000)
        self.assertEqual(C.inspect_native_sesx(self.output)['clip_count'], old+1)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), self.before)

    def test_split_conserves_duration(self):
        self.edit('split', offset_samples=100)
        _, _, _, tracks = C._native_tree(self.output)
        track = next(t for t in tracks if t.get('id') == self.track.get('id'))
        original = int(self.clip.get('endPoint')) - int(self.clip.get('startPoint'))
        self.assertEqual(sum(int(c.get('endPoint'))-int(c.get('startPoint')) for c in track.findall('audioClip')), original)

    def test_move_exact_samples(self):
        self.edit('move', start_samples=123)
        clips = C.inspect_native_clips_advanced(self.output)['clips']
        self.assertEqual(next(c for c in clips if c['id'] == self.clip.get('id'))['start'], 123)

    def test_unknown_id_no_output(self):
        with self.assertRaises(ValueError):
            C.edit_production_session(self.source, self.output, [dict(self.base, action='delete', clip_id='missing')], confirm=True)
        self.assertFalse(self.output.exists())

    def test_invalid_split_no_output(self):
        with self.assertRaises(ValueError): self.edit('split', offset_samples=0)
        self.assertFalse(self.output.exists())

    def test_dry_run_no_output(self):
        result = C.edit_production_session(self.source, self.output, [dict(self.base, action='delete')])
        self.assertTrue(result['dry_run']); self.assertFalse(self.output.exists())

    def test_no_overwrite(self):
        self.output.write_text('keep', encoding='utf8')
        with self.assertRaises(ValueError): self.edit('delete')
        self.assertEqual(self.output.read_text(), 'keep')

    def test_relink_requires_matching_hash(self):
        with self.assertRaises(ValueError):
            C.relink_production_session(self.source, self.output, {'0': {'path': str(self.source), 'sha256': 'wrong'}}, confirm=True)
        self.assertFalse(self.output.exists())

    def test_overlap_report_read_only(self):
        self.assertIn('overlaps', C.session_overlap_report(self.source))
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), self.before)

    def test_queue_failure_and_retry(self):
        database = self.folder / 'queue.db'
        spec = {'inputs': {'voice': str(ROOT / 'tests/fixtures/accept_au_sine_48k_mono.wav')},
                'steps': [{'id': 'qc', 'kind': 'qc', 'source': 'voice', 'format': 'json', 'params': {}}]}
        job = C.enqueue_production_job(database, spec, self.folder)
        self.assertTrue(C.run_next_production_job(database)['dry_run'])
        with patch.object(C, 'run_production_jobs', side_effect=RuntimeError('fault')):
            self.assertEqual(C.run_next_production_job(database, confirm=True)['state'], 'failed')
        C.retry_production_job(database, job['job_id'], confirm=True)
        with patch.object(C, 'run_production_jobs', return_value={'passed': True}):
            self.assertEqual(C.run_next_production_job(database, confirm=True)['state'], 'complete')
        self.assertEqual(C.run_next_production_job(database, confirm=True)['state'], 'idle')

    def test_produced_reference_requires_prefix(self):
        spec = {'inputs': {'voice': str(ROOT / 'tests/fixtures/accept_au_sine_48k_mono.wav')},
                'steps': [{'id': 'first', 'kind': 'transcode', 'source': 'voice', 'format': 'wav', 'params': {}},
                          {'id': 'second', 'kind': 'qc', 'source': 'first', 'format': 'json', 'params': {}}]}
        with self.assertRaisesRegex(ValueError, '@ prefix'):
            C.production_job_plan(spec, self.folder)

    def test_component_inventory_and_patch(self):
        inventory = C.production_component_inventory(self.source)
        item = next(c for c in inventory['components'] if 'powered' in c['attributes'])
        C.patch_production_component(self.source, self.output, track_id=item['track_id'],
            component_id=item['attributes']['id'], powered=False, confirm=True)
        found = C.production_component_inventory(self.output)
        changed = next(c for c in found['components'] if c['track_id'] == item['track_id'] and c['attributes']['id'] == item['attributes']['id'])
        self.assertEqual(changed['attributes']['powered'], 'false')

    def test_production_package_media_and_source_integrity(self):
        output = self.folder / 'package'
        result = C.package_production_session(self.source, output, confirm=True)
        self.assertGreater(result['media_count'], 0)
        self.assertTrue(C.inspect_native_sesx(output/'session.sesx')['all_media_present'])
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), self.before)
        self.assertFalse(result['native_reopen_verified'])

    def test_crossfade_overlap_maps_to_source_samples(self):
        _, _, root, _ = C._native_tree(self.source)
        new_id = str(max(int(c.get('id')) for c in root.findall('.//audioClip'))+1)
        end = int(self.clip.get('endPoint'))
        C.edit_production_session(self.source, self.output,
            [dict(self.base, action='copy', start_samples=end-100),
             dict(self.base, action='crossfade', right_clip_id=new_id)], confirm=True)
        clips = C.inspect_native_clips_advanced(self.output)['clips']
        right = next(c for c in clips if c['id'] == new_id)
        self.assertEqual(int(right['fade_in']['endPoint'])-int(right['fade_in']['startPoint']), 100)

    def test_crossfade_rejects_missing_partner(self):
        with self.assertRaises(ValueError):
            self.edit('crossfade', right_clip_id='missing')
        self.assertFalse(self.output.exists())

    def test_component_rejects_nonfinite(self):
        item = C.production_component_inventory(self.source)['components'][0]
        with self.assertRaises(ValueError):
            C.patch_production_component(self.source, self.output, track_id=item['track_id'],
                component_id=item['attributes']['id'], normalized_parameters={'gain': float('nan')}, confirm=True)
        self.assertFalse(self.output.exists())

    def test_offline_envelope_preserves_frames(self):
        from scipy.io import wavfile
        source = ROOT / 'tests/fixtures/accept_au_sine_48k_mono.wav'
        output = self.folder / 'envelope.wav'
        result = C.render_gain_pan_envelope(source, output,
            [{'sample': 0, 'gain_db': -6, 'pan': -1}, {'sample': 100, 'gain_db': -6, 'pan': 1}], confirm=True)
        sr, samples = wavfile.read(output)
        self.assertEqual(samples.shape[1], 2)
        self.assertEqual(len(samples), result['frames'])
        self.assertFalse(result['native_audition_automation'])

    def test_native_export_dryrun_does_not_launch(self):
        controller = C()
        with patch.object(controller, '_run_jsx_unlocked') as host:
            result = controller.mixdown_production_session(self.source, self.folder/'mix.wav')
        self.assertTrue(result['dry_run']); host.assert_not_called()


if __name__ == '__main__':
    unittest.main()
