import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from lxml import etree as ET
from audition_controller import AuditionController as C, ROOT


class Phase11ProductionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'_runtime')
        self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)
        self.template=ROOT/'tests/native_outputs/ACCEPT_AU_Phase06_multi_arrangement.sesx'
        self.wav=ROOT/'tests/fixtures/accept_au_sine_48k_mono.wav'

    def test_import_new_track_before_master_and_source_intact(self):
        out=self.folder/'import.sesx';before=C._hash_file(self.template)
        result=C.import_production_wavs(self.template,out,[dict(source=str(self.wav),new_track_name='Imported',start_samples=500)],confirm=True)
        root=ET.parse(str(out)).getroot();tracks=root.find('./session/tracks')
        self.assertEqual(tracks[-1].tag,'masterTrack')
        self.assertEqual(C._hash_file(self.template),before)
        ids=[x.get('id') for x in tracks]
        self.assertEqual(len(ids),len(set(ids)))
        new=next(t for t in tracks if t.get('id')==result['changes'][0]['track_id'])
        self.assertEqual(new.find('audioClip').get('startPoint'),'500')
        self.assertFalse(result['native_reopen_verified'])

    def test_import_unknown_track_no_output(self):
        out=self.folder/'import.sesx'
        with self.assertRaises(ValueError):
            C.import_production_wavs(self.template,out,[dict(source=str(self.wav),track_id='missing')],confirm=True)
        self.assertFalse(out.exists())

    def test_import_rejects_conflicting_target_fields(self):
        with self.assertRaises(ValueError):
            C.import_production_wavs(self.template,self.folder/'import.sesx',[dict(source=str(self.wav),track_id='10001',new_track_name='Both')])

    def test_search_ambiguity_does_not_relink(self):
        source=self.folder/'missing.sesx';tree=ET.parse(str(self.template))
        node=tree.getroot().find('.//files/file');node.set('absolutePath','Z:/missing/voice.wav');node.attrib.pop('relativePath',None)
        tree.write(str(source),encoding='utf-8')
        for name in ('one','two'):
            (self.folder/name).mkdir();shutil.copy2(self.wav,self.folder/name/'voice.wav')
        before=C._hash_file(source)
        result=C.search_session_media(source,[str(self.folder)])
        self.assertEqual(len(result['missing_media'][0]['candidates']),2)
        self.assertTrue(result['missing_media'][0]['ambiguous'])
        self.assertEqual(before,C._hash_file(source))

    def test_checkpoint_resume_skips_completed_step(self):
        output=self.folder/'out';output.mkdir();cache=self.folder/'cache'
        spec={'inputs':{'voice':str(self.wav)},'steps':[
            dict(id='one',kind='transcode',source='voice',format='wav',params={}),
            dict(id='two',kind='transcode',source='@one',format='wav',params={})]}
        calls=[]
        def fail_second(step,inputs,staged,stage):
            calls.append(step['id'])
            if step['id']=='two':raise RuntimeError('injected interruption')
            target=stage/(step['id']+'.wav');shutil.copy2(self.wav,target);return target,{}
        with patch.object(C,'_execute_production_step',side_effect=fail_second):
            with self.assertRaisesRegex(RuntimeError,'interruption'):
                C.run_resumable_production(spec,output,cache,confirm=True)
        self.assertEqual(list(output.iterdir()),[])
        self.assertEqual(len(json.loads((cache/'state.json').read_text())['steps']),1)
        calls=[]
        def finish(step,inputs,staged,stage):
            calls.append(step['id']);target=stage/(step['id']+'.wav');shutil.copy2(self.wav,target);return target,{}
        with patch.object(C,'_execute_production_step',side_effect=finish):
            result=C.run_resumable_production(spec,output,cache,confirm=True)
        self.assertEqual(calls,['two']);self.assertEqual(result['resumed_steps'],1)
        self.assertTrue(C.run_resumable_production(spec,output,cache,confirm=True)['already_complete'])

    def test_checkpoint_corruption_rejected(self):
        output=self.folder/'out';output.mkdir();cache=self.folder/'cache'
        spec={'inputs':{'voice':str(self.wav)},'steps':[dict(id='one',kind='transcode',source='voice',format='wav',params={}),dict(id='two',kind='transcode',source='@one',format='wav',params={})]}
        def execute(step,inputs,staged,stage):
            if step['id']=='two':raise RuntimeError('stop')
            target=stage/'one.wav';shutil.copy2(self.wav,target);return target,{}
        with patch.object(C,'_execute_production_step',side_effect=execute):
            with self.assertRaises(RuntimeError):C.run_resumable_production(spec,output,cache,confirm=True)
        (cache/'one.wav').write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError,'changed'):
            C.run_resumable_production(spec,output,cache,confirm=True)

    def test_native_envelope_serializes_ordered_keyframes(self):
        out=self.folder/'envelope.sesx'
        C.patch_native_track_envelope(self.template,out,track_id='10001',points=[dict(sample=0,value=.2),dict(sample=48000,value=.6,hold=True)],confirm=True)
        root=ET.parse(str(out)).getroot()
        keys=root.findall('.//parameterKeyframe')
        self.assertEqual([k.get('sampleOffset') for k in keys],['0','48000'])
        self.assertEqual(keys[-1].get('type'),'hold')

    def test_native_envelope_rejects_unordered_points(self):
        with self.assertRaises(ValueError):
            C.patch_native_track_envelope(self.template,self.folder/'x.sesx',track_id='10001',points=[dict(sample=10,value=.2),dict(sample=0,value=.6)],confirm=True)

    def test_native_send_preserves_route(self):
        out=self.folder/'send.sesx'
        C.patch_native_send(self.template,out,track_id='10001',bus_id='10007',level=.25,confirm=True)
        root=ET.parse(str(out)).getroot();send=root.find('.//audioTrack/sendList/sendSlot')
        self.assertEqual(send.get('sendOutputID'),'10007')
        self.assertEqual(send.get('preFader'),'false')

    def test_native_send_feedback_rejected(self):
        source=self.folder/'feedback.sesx';root=ET.parse(str(self.template))
        root.find('.//busTrack/trackAudioParameters/trackOutput').set('outputID','10001')
        root.write(str(source),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'feedback'):
            C.patch_native_send(source,self.folder/'send.sesx',track_id='10001',bus_id='10007',confirm=True)

    def test_pan_normalized_maps_to_native_percent(self):
        out=self.folder/'pan.sesx'
        C.patch_native_pan_position(self.template,out,track_id='10001',position=-1,confirm=True)
        root=ET.parse(str(out)).getroot()
        pan=next(c for c in root.find('.//audioTrack').findall('./trackAudioParameters/component') if c.get('id')=='trackPan')
        self.assertEqual(float(pan.find('parameter').get('parameterValue')),-100)

    def test_sdk_manifest_native_values_and_unicode(self):
        out=self.folder/'session.auctl'
        result=C.create_native_sdk_session({'name':'测试会话','tracks':[dict(source=str(self.wav),points=[dict(sample=0,value=.2)])]},out,confirm=True)
        self.assertIn('测试会话',out.read_text(encoding='utf-16'))
        self.assertFalse(result['native_open_verified'])

    def test_sdk_manifest_rejects_ini_injection(self):
        with self.assertRaises(ValueError):
            C.create_native_sdk_session({'name':'bad\n[session]','tracks':[dict(source=str(self.wav))]},self.folder/'bad.auctl',confirm=True)

    def test_sdk_effect_chunk_validation(self):
        with self.assertRaises(ValueError):
            C.create_native_sdk_session({'tracks':[dict(source=str(self.wav),effects=[dict(component_id='known',chunk_base64='invalid!!!')])]},self.folder/'bad.auctl',confirm=True)

    def test_missing_host_never_implicitly_launches(self):
        controller=C()
        with patch.object(controller,'_audition_pid',side_effect=RuntimeError('not running')),patch('audition_controller.subprocess.Popen') as launch:
            with self.assertRaises(ConnectionError):controller._run_jsx('out("X",1);','missing_host',1)
        launch.assert_not_called()

    def test_native_rack_preset_roundtrip(self):
        source=ROOT/'tests/fixtures/accept_native_rack_reference.sesx'
        preset=self.folder/'rack.json';output=self.folder/'rack.sesx'
        C.export_native_rack_preset(source,preset,track_id='10001',confirm=True)
        C.apply_native_rack_preset(source,output,preset,track_id='10001',confirm=True)
        before=ET.parse(str(source)).find('.//effectsRack/slot/component')
        after=ET.parse(str(output)).find('.//effectsRack/slot/component')
        self.assertEqual(before.get('componentID'),after.get('componentID'))
        self.assertNotEqual(before.get('componentGuid'),after.get('componentGuid'))

    def test_native_rack_reorder_and_bypass(self):
        source=ROOT/'tests/fixtures/accept_native_rack_reference.sesx';output=self.folder/'rack.sesx'
        C.edit_native_rack(source,output,track_id='10001',operations=[
            dict(action='copy_slot',template_session=str(source),template_track_id='10001',template_slot=0,slot=1),
            dict(action='reorder',order=[1,0]),dict(action='power',slot=1,enabled=False)],confirm=True)
        slots=ET.parse(str(output)).findall('.//effectsRack/slot')
        self.assertEqual([s.get('slotIndex') for s in slots],['0','1'])
        self.assertEqual(slots[1].get('powered'),'false')

    def test_rack_preset_rejects_checksum_mismatch(self):
        source=ROOT/'tests/fixtures/accept_native_rack_reference.sesx';preset=self.folder/'rack.json'
        C.export_native_rack_preset(source,preset,track_id='10001',confirm=True)
        data=json.loads(preset.read_text());data['rack_xml']+='tamper';preset.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'checksum'):
            C.apply_native_rack_preset(source,self.folder/'out.sesx',preset,track_id='10001',confirm=True)

    def test_autoheal_not_permitted_as_whole_file_favorite(self):
        c=C()
        with self.assertRaises(ValueError):
            c.native_apply_favorite_copy(self.wav,self.folder/'healed.wav',favorite='Auto Heal')

    def test_native_favorite_dry_run_writes_nothing(self):
        c=C();out=self.folder/'normalized.wav'
        with patch.object(c,'_run_jsx_unlocked') as host:
            r=c.native_apply_favorite_copy(self.wav,out,favorite='Normalize to -3 dB')
        host.assert_not_called();self.assertTrue(r['dry_run']);self.assertFalse(out.exists())

    def test_recording_dryrun_never_captures(self):
        c=C();folder=ROOT/'tests/native_outputs'/('ACCEPT_AU_DryRun_'+self.folder.name)
        with patch.object(c,'_run_jsx') as host:
            r=c.native_record_input_qa(folder)
        host.assert_not_called();self.assertTrue(r['dry_run']);self.assertFalse(folder.exists())

    def test_recording_rejects_unbounded_duration(self):
        c=C();folder=ROOT/'tests/native_outputs'/('ACCEPT_AU_DryRun_'+self.folder.name)
        with self.assertRaises(ValueError):c.native_record_input_qa(folder,seconds=10,confirm=True)
        self.assertFalse(folder.exists())


if __name__=='__main__':unittest.main()
