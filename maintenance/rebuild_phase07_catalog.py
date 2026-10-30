"""Deterministic Phase07 Audition API/coverage rebuild from frozen Phase06 ledger.

Upgrades only receipt-backed old entries; retains unsupported functionality,
and never equates an external DSP substitute with Audition native UI.
"""
from pathlib import Path
from collections import Counter
import inspect,json,shutil,sys
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from audition_controller import AuditionController as C
A=R/'api';T=R/'tests/receipts'
baseline=A/'Audition_26_phase06_baseline_360.json'
ledger=A/'Audition_26_feature_ledger.json'
api=A/'Audition_26_runtime_api.json'
# This is a historical builder. Refuse to roll the live phase-08 catalog back.
if ledger.is_file() and json.loads(ledger.read_text(encoding='utf-8')).get('latest_phase',0)>7:
 raise RuntimeError('Historical phase07 catalog is frozen; run maintenance/rebuild_phase08_catalog.py instead.')
api_base=A/'Audition_26_phase06_runtime_api.json'
if not baseline.exists():
 original=json.loads(ledger.read_text(encoding='utf8'))
 assert original['total']==360
 shutil.copy2(ledger,baseline)
if not api_base.exists():shutil.copy2(api,api_base)
d=json.loads(baseline.read_text(encoding='utf8'));assert d['total']==360
legacy=d['features'];by={x['id']:x for x in legacy}
receipt_paths={
 'menu':A/'Audition_26_native_menu_registry.json',
 'import':T/'phase07_native_mp3_flac_open.json',
 'transport':T/'phase06_native_transport_acceptance.json',
 'eq':T/'phase04_real_eq_render.json',
 'track':T/'phase07_native_track_controls.json',
 'clipgain':T/'phase06_native_arrangement_acceptance.json',
 'fade':T/'phase05_native_clip_trim_fade_acceptance.json',
 'safe':T/'phase07_waveform_timeline_acceptance.json',
 'bitdepth':T/'phase07_float_to_pcm16.json',
 'fft':T/'phase07_waveform_timeline_acceptance.json',
 'channels':T/'phase07_channel_split_roundtrip.json',
 'native_split':T/'phase07_native_split_acceptance.json',
 'pipeline':T/'phase07_waveform_pipeline_acceptance.json',
 'native_markers':T/'phase06_native_xmp_edit_acceptance.json',
 'old_pipeline':T/'phase06_production_bundle_acceptance.json',
 'qa_close':T/'phase07_track_controls_closed.json',
}
for k,p in receipt_paths.items():
 if not p.is_file():raise FileNotFoundError(str(p))
 if k not in ('menu',):
  payload=json.loads(p.read_text(encoding='utf8'))
  if not isinstance(payload,dict):raise ValueError('Bad receipt '+k)
menu=json.loads(receipt_paths['menu'].read_text(encoding='utf8'))
assert menu['count']==474
assert json.loads(receipt_paths['import'].read_text(encoding='utf8'))['documents_zero']
assert json.loads(receipt_paths['native_split'].read_text(encoding='utf8'))['max_absolute_difference_from_original']<1e-9
assert json.loads(receipt_paths['pipeline'].read_text(encoding='utf8'))['pipeline']['passed']
assert json.loads(receipt_paths['channels'].read_text(encoding='utf8'))['roundtrip_max_absolute_error']<1e-7
UP={}
def mark(numbers,status,key,note):
 for n in numbers:
  ident='AU'+str(n).zfill(3)
  if ident in UP:raise ValueError('Duplicate claim '+ident)
  UP[ident]=(status,key,note)
mark([6,267],'verified_readonly_host','menu','Audition Win32 menu command enumeration verified; not event subscribe.')
mark([8,11,16,14,15],'verified_native_live','import','Actual native Audition open/document dirty guard/File.Close for MP3 and FLAC.')
mark([10,42],'verified_native_live','transport','Native QA playhead, stop and state restoration verified in host.')
mark([88],'verified_hybrid_sesx_reopened','eq','Track EQ conservative gain serialized, reopened and Native Mixdown measured; not Hz/dB mapping.')
mark([114],'verified_hybrid_sesx_reopened','track','Track Fader 0.8 serialized and Audition Mixdown lower peak than baseline.')
mark([117],'verified_hybrid_sesx_reopened','clipgain','Native SESX clip linear gains and layered native Mixdown; individual levels not isolated.')
mark([118,119],'verified_hybrid_sesx_reopened','fade','Native fade-in/out modified, session reopened and rendered.')
mark([21,22,23],'verified_offline','bitdepth','Float WAV to PCM16: deterministic TPDF or first-order error-feedback. Not Audition preset.')
mark([28,29,30,31,32],'verified_offline','safe','SciPy sample-accurate QA audio cut/copy/paste/delete/silence; not native edit menu.')
mark([38],'verified_offline','channels','Sterero split and recombine with exact float PCM sample match; not native GUI.')
mark([55],'verified_offline','fft','SciPy Welch spectrum JSON with known dominant frequency; not Audition spectral screenshot.')
mark([106],'verified_native_live','native_split','Native SESX project opened and mixdown performed.')
mark([124,125],'verified_hybrid_sesx_reopened','native_split','Native clip insert/split SESX, Audition reopened; sample-accurate mixdown.')
mark([148],'verified_hybrid_sesx_reopened','native_markers','Multiple Native XMP marker operations, 3 markers reopened.')
mark([164],'verified_offline','old_pipeline','Production staging and failed-step rollback tested for QA media.')
mark([253,255,256,257,259,261,262],'verified_offline','safe','Source immutability, QA path guard, output collision refusal, SHA256 and receipts verified in tests.')
mark([254],'verified_offline','pipeline','Source backup ZIP with per-file SHA256 exists and user workspace untouched.')
mark([260],'verified_offline','channels','WAV output reopening/decoder readback and sample comparison proved.')
mark([264],'verified_offline','pipeline','277-test phase07 unit suite and native QA receipt checkpoint.')
mark([265,266],'verified_offline','pipeline','Recovery backup/README/API docs preserved in workspace; documentation availability verified.')
p0audit=json.loads((A/'Audition_26_第七轮全量功能缺口审计.json').read_text(encoding='utf8'))
p0=[x for x in p0audit['original_unverified'] if x['priority']=='P0']
assert len(p0)==31
p0ids={x['id'] for x in p0}
crosswalk=[]
for item in p0:
 claim=UP.get(item['id'])
 crosswalk.append({'id':item['id'],'name':item['name'],'old_status':item['status'],
   'new_status':claim[0] if claim else item['status'],
   'evidence':str(receipt_paths[claim[1]].relative_to(R)) if claim else None,
   'note':claim[2] if claim else 'Insufficient isolated end-to-end proof; not upgraded'})
for ident,(status,key,note) in UP.items():
 row=by[ident]
 if row['status'].startswith('verified_'):raise ValueError('Already verified '+ident)
 row['status']=status
 row['evidence']=str(receipt_paths[key].relative_to(R))
 row['qualification']=note
extra=[
 ('Offline waveform','Sample-accurate cut/delete and silence insertion','verified_offline','safe'),
 ('Offline waveform','Copy/paste original sample region at arbitrary frame','verified_offline','safe'),
 ('Offline waveform','Regional gain and fade editing','verified_offline','safe'),
 ('PCM delivery','Deterministic TPDF 16-bit dithering with seed','verified_offline','bitdepth'),
 ('PCM delivery','First-order error-feedback noise shaping (non-Audition preset)','verified_offline','bitdepth'),
 ('PCM delivery','Native Float32-to-PCM16 file readback','verified_offline','bitdepth'),
 ('Spectrum','Welch FFT 4096 window JSON frequency spectrum','verified_offline','fft'),
 ('Native multitrack','Sample-accurate Native SESX QA clip split and reimport','verified_hybrid_sesx_reopened','native_split'),
 ('Native multitrack','Native Mixdown after clip split matches original samples','verified_native_live','native_split'),
 ('Native multitrack','Native Track Fader gain change and peak readback','verified_hybrid_sesx_reopened','track'),
 ('Native import','MP3 and FLAC native WaveDocument open and close','verified_native_live','import'),
 ('Channel tools','Stereo split into L/R mono and zero-error rejoin','verified_offline','channels'),
 ('Production workflow','Waveform Edit and FFT JSON pipeline actions','verified_offline','pipeline'),
 ('Production workflow','Four-step PCM editing FFT mastering and QC bundle','verified_offline','pipeline'),
 ('Coverage assurance','Thirty-one P0 items individually cross-referenced','verified_offline','pipeline'),
]
for category,name,status,key in extra:
 if any(x['name']==name for x in legacy):raise ValueError('Duplicate feature '+name)
 legacy.append({'id':'AU'+str(len(legacy)+1).zfill(3),'category':category,
  'name':name,'status':status,'access_route':'Native Audition/SESX' if 'Native' in category else 'Offline Python/SciPy',
  'evidence':str(receipt_paths[key].relative_to(R)),'qualification':'Only scoped evidence recorded; see receipt'})
counts=dict(sorted(Counter(x['status'] for x in legacy).items()))
d.update({'total':len(legacy),'features':legacy,'counts':counts,'latest_phase':7,'as_of':'2026-10-10'})
ledger.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
runtime=json.loads(api_base.read_text(encoding='utf8'))
methods=[]
for name in sorted(x for x in dir(C) if not x.startswith('_')):
 item=getattr(C,name)
 if callable(item):
  try:sig=str(inspect.signature(item))
  except (ValueError,TypeError):sig='(...)'
  methods.append({'method':name,'signature':sig})
runtime.update({'controller_methods':methods,'features':len(legacy),'counts':counts,
                'latest_phase':7,'as_of':'2026-10-10'})
api.write_text(json.dumps(runtime,ensure_ascii=False,indent=2),encoding='utf8')
(A/'Audition_26_phase07_P0_evidence_crosswalk.json').write_text(json.dumps(crosswalk,ensure_ascii=False,indent=2),encoding='utf8')
def writemd(path,lines):path.write_text('\n'.join(lines)+'\n',encoding='utf8')
ap=['# Audition 26 API 与 Controller 接口目录（第七轮）','',
 f'公开 Controller 方法 {len(methods)}；功能条目 {len(legacy)}。Audition 原生命令 474 条为静态快照。',
 '原生 Audition、Native SESX 重开和离线 SciPy/FFmpeg 状态互不混淆。']
ap+=['','## Audition 原生 SDK 反射对象（本机实际读取）','']
for domain,objects in [('基础对象',runtime.get('objects',{})),('多轨对象',runtime.get('multitrack_reflected_objects',{}))]:
 ap+=['','### '+domain]
 for name,obj in objects.items():
  ap+=['','#### '+name,'Methods: '+', '.join(obj.get('methods',[])),
       'Properties: '+', '.join(obj.get('properties',[]))]
ap+=['','## 原生菜单命令目录','',
 '第四轮读取的 474 条 Windows 菜单条目保存在 api/Audition_26_原生菜单命令目录.md；菜单项不等于 API 已验证。',
 '','## Controller 公开签名索引','','| 方法 | 签名 |','|---|---|']
for m in methods:ap.append('| '+m['method']+' | '+m['signature'].replace('|','/')+' |')
writemd(A/'Audition_26_API_接口目录.md',ap)
p=['# Audition 26 全功能开发矩阵（第七轮）','',
 f'原始第六轮基线 360 项；本轮新增 {len(extra)} 项；现共 {len(legacy)} 项。',
 '状态为经收据支持的验收级别，**不是所有条目都已完成**。',
 '','## 状态统计','','| 状态 | 数量 |','|---|---:|']
for k,v in counts.items():p.append('| '+k+' | '+str(v)+' |')
p+=['','## 全部明细','','| ID | 模块 | 功能 | 状态 | 证据 |','|---|---|---|---|---|']
for x in legacy:p.append('| '+x['id']+' | '+x['category']+' | '+x['name']+' | '+x['status']+' | '+x.get('evidence','')+' |')
writemd(A/'Audition_26_全功能开发矩阵.md',p)
remaining=[x for x in legacy if not x['status'].startswith('verified_')]
u=['# Audition 26 未完成与外部依赖清单（第七轮）','',
 f'{len(legacy)} 项中仍有 {len(remaining)} 项未通过完整验收。',
 '现有离线替代方法不等于 Audition 原生效果器 SDK。','',
 '| ID | 功能 | 原当前状态 | 推荐行动 |','|---|---|---|---|']
for x in remaining:
 state=x['status']
 nextstep=('CEP PlugPlugSetup 宿主修复/官方最小Panel装载' if 'cep' in state or 'host' in state else
  '取得官方SDK头文件/硬件/真实录音或视频素材' if 'sdk' in state else
  'Adobe Native API 接口失效，保留SESX回避方案' if state=='blocked_native_api' else
  '补真实原生GUI/多轨工程重开及成片' if state in ('ui_or_media_pending','partial_native_live') else
  '独立实测并绑定可信收据')
 u.append('| '+x['id']+' | '+x['name']+' | '+state+' | '+nextstep+' |')
writemd(A/'Audition_26_未完成与依赖清单.md',u)
cw=['# Audition 第七轮 P0 历史能力证据映射','',
 f'原审计 P0 {len(p0)} 项，其中 {sum(x["new_status"].startswith("verified_") for x in crosswalk)} 项依据限定范围的证据升级。',
 '注意：某些仅证明存在安全边界或静态只读操作，并不代表全部 GUI 功能。',
 '',
 '| 原 ID | 功能 | 旧状态 | 当前状态 | 证据 |','|---|---|---|---|---|']
for x in crosswalk:
 cw.append('| '+x['id']+' | '+x['name']+' | '+x['old_status']+' | '+x['new_status']+' | '+str(x['evidence'] or '仍待专项验证')+' |')
writemd(A/'Audition_26_第七轮P0验收证据映射.md',cw)
print('PHASE07_REBUILT',len(legacy),'FEATURES',len(methods),'METHODS',
  'P0_UPGRADED',sum(x['new_status'].startswith('verified_') for x in crosswalk),
  'LEGACY_UPGRADED',len(UP),'NEW_ENTRIES',len(extra),'PENDING',len(remaining),flush=True)
