from __future__ import annotations
import hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audition_controller import AuditionController as C
R=Path(__file__).resolve().parents[1]
SESX=R/'tests/native_outputs/ACCEPT_AU_Phase04_bus_pruned.sesx'
VOICE=R/'tests/fixtures/accept_au_sine_48k_mono.wav'
MUSIC=R/'tests/fixtures/accept_phase05_duck_music.wav'
def placement(to=1,start=48000,gain=.5):
 return {'source_track':0,'source_clip':0,'target_track':to,
         'start_samples':start,'gain_linear':gain}
def spec(steps=None,inputs=None):
 return {'inputs':inputs or {'voice':str(VOICE)},
         'steps':steps or [{'id':'fx','kind':'effects','source':'voice','format':'wav','params':{'effects':[{'effect':'highpass','hz':90}]}}]}

class Phase06ArrangementAndProduction(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='phase06_new_',dir=str(R/'tests'))
  self.addCleanup(self.tmp.cleanup)
  self.folder=Path(self.tmp.name)
  self.out=self.folder/'ACCEPT_AU_arranged.sesx'
 def test_native_arrangement_snapshot(self):
  a=C.inspect_native_sesx(R/'tests/native_outputs/ACCEPT_AU_Phase06_multi_arrangement.sesx')
  self.assertEqual(a['clip_count'],4)
  self.assertTrue(a['all_media_present'])
 def test_native_real_receipt(self):
  a=json.loads((R/'tests/receipts/phase06_native_arrangement_acceptance.json').read_text(encoding='utf8'))
  self.assertEqual(a['wav_stats']['frames'],199200)
  self.assertTrue(a['native_mixdown']['exists'])
  self.assertLess(a['wav_stats']['peak_dbfs'],-1)
 def test_arrangement_dry_run(self):
  a=C.arrange_native_qa_clips(SESX,self.out,[placement()])
  self.assertTrue(a['dry_run'])
  self.assertFalse(self.out.exists())
 def test_arrange_real_copy(self):
  digest=hashlib.sha256(SESX.read_bytes()).hexdigest()
  a=C.arrange_native_qa_clips(SESX,self.out,[placement()],confirm=True)
  self.assertEqual(a['clip_count'],2)
  self.assertEqual(hashlib.sha256(SESX.read_bytes()).hexdigest(),digest)
  self.assertEqual(C.inspect_native_sesx(self.out)['clip_count'],2)
 def test_arrange_unique_ids(self):
  a=C.arrange_native_qa_clips(SESX,self.out,[placement(1),placement(2)],confirm=True)
  self.assertEqual(len({x['new_id'] for x in a['placements']}),2)
 def test_arrange_existing_target(self):
  with self.assertRaises(ValueError):
   C.arrange_native_qa_clips(SESX,self.out,[placement(0)],confirm=True)
 def test_arrange_duplicate_destination(self):
  with self.assertRaises(ValueError):
   C.arrange_native_qa_clips(SESX,self.out,[placement(1),placement(1)],confirm=True)
 def test_arrange_gain_above_one(self):
  with self.assertRaises(ValueError):
   C.arrange_native_qa_clips(SESX,self.out,[placement(gain=1.4)],confirm=True)
 def test_arrange_gain_bool(self):
  with self.assertRaises(ValueError):
   C.arrange_native_qa_clips(SESX,self.out,[placement(gain=True)],confirm=True)
 def test_arrange_invalid_track(self):
  with self.assertRaises(IndexError):
   C.arrange_native_qa_clips(SESX,self.out,[placement(999)],confirm=True)
 def test_arrange_invalid_clip_index(self):
  data=placement();data['source_clip']=100
  with self.assertRaises(IndexError):
   C.arrange_native_qa_clips(SESX,self.out,[data],confirm=True)
 def test_arrange_bad_start(self):
  with self.assertRaises(ValueError):
   C.arrange_native_qa_clips(SESX,self.out,[placement(start=-2)],confirm=True)
 def test_arrange_overwrite_protection(self):
  self.out.write_bytes(b'keep me')
  with self.assertRaises(ValueError):
   C.arrange_native_qa_clips(SESX,self.out,[placement()],confirm=True)
  self.assertEqual(self.out.read_bytes(),b'keep me')
 def test_arrange_offline_clip_refused(self):
  from lxml import etree as ET
  tree=ET.parse(str(SESX))
  tree.getroot().find('.//audioClip').set('offline','true')
  offline=self.folder/'ACCEPT_AU_offline.sesx'
  tree.write(str(offline),encoding='utf8',xml_declaration=True)
  with self.assertRaises(ValueError):
   C.arrange_native_qa_clips(offline,self.out,[placement()],confirm=True)
  self.assertFalse(self.out.exists())
 def test_arrange_no_source_mutation(self):
  original=hashlib.sha256(SESX.read_bytes()).hexdigest()
  C.arrange_native_qa_clips(SESX,self.out,[placement()],confirm=True)
  self.assertEqual(hashlib.sha256(SESX.read_bytes()).hexdigest(),original)
 def test_production_plan(self):
  result=C.production_job_plan(spec(),self.folder)
  self.assertTrue(result['dry_run'])
  self.assertEqual(len(result['steps']),1)
  self.assertFalse((self.folder/'fx.wav').exists())
 def test_production_cannot_override_receipt(self):
  (self.folder/'audition_production_receipt.json').write_bytes(b'USER DATA')
  with self.assertRaises(FileExistsError):
   C.production_job_plan(spec(),self.folder)
 def test_production_duplicate_step_ids(self):
  step=spec()['steps'][0]
  with self.assertRaises(ValueError):
   C.production_job_plan(spec([step,step]),self.folder)
 def test_production_forward_reference(self):
  bad={'id':'fx','kind':'effects','source':'@later','format':'wav','params':{'effects':[{'effect':'highpass'}]}}
  with self.assertRaises(ValueError):
   C.production_job_plan(spec([bad]),self.folder)
 def test_production_arbitrary_methods_refused(self):
  bad={'id':'unsafe','kind':'shell','source':'voice','format':'wav','params':{}}
  with self.assertRaises(ValueError):
   C.production_job_plan(spec([bad]),self.folder)
 def test_production_path_traversal_refused(self):
  bad={'id':'../escape','kind':'effects','source':'voice','format':'wav','params':{'effects':[{'effect':'highpass'}]}}
  with self.assertRaises(ValueError):
   C.production_job_plan(spec([bad]),self.folder)
 def test_production_metadata_format_mismatch(self):
  bad={'id':'tags','kind':'metadata','source':'voice','format':'mp3','params':{'tags':{'title':'Test'}}}
  with self.assertRaises(ValueError):
   C.production_job_plan(spec([bad]),self.folder)
 def test_production_duplicate_inputs(self):
  inputs={'voice':str(VOICE),'voice2':str(VOICE)}
  a=C.production_job_plan(spec(inputs=inputs),self.folder)
  self.assertIn('voice2',a['inputs'])
 def test_production_background_alias_guard(self):
  bad={'id':'duck','kind':'duck','source':'voice','format':'wav','params':{'background':'missing'}}
  with self.assertRaises(ValueError):
   C.production_job_plan(spec([bad]),self.folder)
 def test_production_bad_effect_rejected(self):
  bad={'id':'fx','kind':'effects','source':'voice','format':'wav','params':{'effects':[{'effect':'exec'}]}}
  with self.assertRaises(ValueError):
   C.production_job_plan(spec([bad]),self.folder)
 def test_production_existing_output_refused(self):
  (self.folder/'fx.wav').write_bytes(b'keep')
  with self.assertRaises(FileExistsError):
   C.production_job_plan(spec(),self.folder)
 def test_production_returned_dryrun(self):
  r=C.run_production_jobs(spec(),self.folder)
  self.assertTrue(r['dry_run'])
  self.assertFalse((self.folder/'fx.wav').exists())
 def test_full_10_step_receipt(self):
  p=R/'tests/native_outputs/phase06_production_bundle/audition_production_receipt.json'
  manifest=json.loads(p.read_text(encoding='utf8'))
  self.assertEqual(manifest['step_count'],10)
  self.assertEqual(len({x['id'] for x in manifest['steps']}),10)
  for item in manifest['steps']:
   q=p.parent/item['output']
   self.assertEqual(C._hash_file(q),item['sha256'])
 def test_full_workflow_qc_files(self):
  out=R/'tests/native_outputs/phase06_production_bundle'
  for name in ('qcvoice.json','qcduck.json'):
   self.assertTrue(json.loads((out/name).read_text(encoding='utf8'))['passed'])
 def test_full_workflow_r128(self):
  out=R/'tests/native_outputs/phase06_production_bundle'
  self.assertGreaterEqual(json.loads((out/'meter.json').read_text(encoding='utf8'))['readings_returned'],20)
 def test_production_manifest_hash(self):
  d=json.loads((R/'tests/receipts/phase06_production_bundle_acceptance.json').read_text(encoding='utf8'))
  p=R/'tests/native_outputs/phase06_production_bundle/audition_production_receipt.json'
  self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),d['manifest_sha256'])
 def test_production_rollback_on_failure(self):
  steps=[
   {'id':'a','kind':'effects','source':'voice','format':'wav',
    'params':{'effects':[{'effect':'highpass','hz':75}]}},
   {'id':'b','kind':'metadata','source':'@a','format':'wav',
    'params':{'tags':{}}}
  ]
  with self.assertRaises(ValueError):
   C.run_production_jobs(spec(steps),self.folder,confirm=True)
  self.assertEqual(list(self.folder.iterdir()),[])
 def test_production_session_preflight(self):
  d=spec([{'id':'audit','kind':'session_audit','source':'project','format':'json','params':{}}],
         {'project':str(SESX)})
  output=C.run_production_jobs(d,self.folder,confirm=True)
  self.assertTrue(output['passed'])
  self.assertTrue(json.loads((self.folder/'audit.json').read_text(encoding='utf8'))['passed'])
 def test_production_cli_dryrun(self):
  config=self.folder/'spec.json'
  config.write_text(json.dumps(spec()),encoding='utf8')
  task=subprocess.run([sys.executable,'-B',str(R/'audition_controller.py'),'production',
                      str(config),str(self.folder)],
        capture_output=True,text=True,encoding='utf8',errors='replace',timeout=30)
  self.assertEqual(task.returncode,0,task.stderr)
  self.assertTrue(json.loads(task.stdout)['dry_run'])
 def test_arrangement_cli_dryrun(self):
  config=self.folder/'placements.json'
  config.write_text(json.dumps([placement()]),encoding='utf8')
  task=subprocess.run([sys.executable,'-B',str(R/'audition_controller.py'),'arrange-session',
                     str(SESX),str(self.out),str(config)],
        capture_output=True,text=True,encoding='utf8',errors='replace',timeout=30)
  self.assertEqual(task.returncode,0,task.stderr)
  self.assertTrue(json.loads(task.stdout)['dry_run'])
if __name__=='__main__':unittest.main()
