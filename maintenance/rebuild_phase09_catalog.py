"""Deterministic phase09 Audition catalog from immutable phase08 state and receipts."""
from __future__ import annotations
from pathlib import Path
from collections import Counter
import hashlib,inspect,json,re,subprocess,sys
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from audition_controller import AuditionController as C
if len([name for name in dir(C) if not name.startswith("_") and callable(getattr(C,name))]) != 96:
    raise SystemExit("Historical phase09 rebuild refused: current Controller differs from its frozen 96-method baseline")
A=R/"api";T=R/"tests/receipts"
old=A/"Audition_26_phase08_baseline_379.json"
old_runtime=A/"Audition_26_phase08_runtime_api.json"
assert old.is_file() and old_runtime.is_file()
def loaded(name):
    return json.loads((T/name).read_text(encoding="utf-8"))
native=loaded("phase09_native_acceptance.json")
batch=loaded("phase09_native_batch_acceptance.json")
marks=loaded("phase09_native_markers.json")
offline=loaded("phase09_offline_batch_acceptance.json")
phase08=loaded("phase08_real_delivery.json")
assert native["passed"] and all(native["checks"].values())
assert batch["passed"] and batch["favorite"]["passed"]==3 and batch["resample"]["passed"]==3
assert marks["passed"] and marks["verified_count"]==3 and marks["supports_distinct_type"]
assert offline["passed"] and offline["batch_master"]["passed"]==2 and offline["batch_mp3"]["passed"]==2
assert phase08["passed"] and phase08["jobs_with_missing_source"]["failed"]==1
def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for x in iter(lambda:f.read(1<<20),b""):h.update(x)
    return h.hexdigest()
for receipt in (native["resample"],native["favorite"]):
    assert sha(receipt["output"])==receipt["readback"]["sha256"] if "readback" in receipt else sha(receipt["output"])==receipt["output_sha256"]
for job in (batch["favorite"],batch["resample"]):
    for row in job["rows"]:
        assert row["status"]=="passed" and sha(row["output"])==row["sha256"]
for entry in marks["output"].splitlines()[:1]:
    assert sha(entry)==marks["output_sha256"]
for row in offline["batch_master"]["rows"]+offline["batch_mp3"]["jobs"]:
    if row["status"]=="passed":
        dst=row["output"] if "output" in row else row["destination"]
        assert sha(dst)==row["sha256"]
d=json.loads(old.read_text(encoding="utf-8"))
assert d["total"]==379
rows=d["features"]
by={item["id"]:item for item in rows}
up={
 "AU112":("verified_native_live","phase09_native_acceptance.json",
          "QA AudioTrack.armed true/false and restore from real native DOM; no recording/hardware"),
 "AU113":("verified_native_live","phase09_native_acceptance.json",
          "QA AudioTrack.visible false/true native host roundtrip"),
 "AU145":("verified_native_live","phase09_native_markers.json",
          "Cue point/range and Subclip marker type persisted and reopened; CD Track rejected by this host"),
 "AU157":("verified_native_live","phase09_native_batch_acceptance.json",
          "Three QA files: Normalize to -3 dB Favorite via Audition WaveDocument API; not arbitrary favorite presets"),
 "AU158":("verified_native_live","phase09_native_acceptance.json",
          "Three QA files sequential native open/inspect/close; not user-selected media in production"),
 "AU160":("verified_offline","phase09_offline_batch_acceptance.json",
          "Two real MP3 output files with verified FFprobe and hashes; WSL FFmpeg, not Audition Batch UI"),
 "AU161":("verified_offline","phase08_real_delivery.json",
          "Two FLAC media outputs by Debian FFmpeg with independent format probes"),
 "AU162":("verified_native_live","phase09_native_batch_acceptance.json",
          "Three files resampled to 32k 16-bit PCM by native Audition SaveAsDocument, decoded after export"),
 "AU163":("verified_offline","phase09_native_batch_acceptance.json",
          "Python-generated safe suffix names for six Audition-native WAV exports; not native Batch Rename UI"),
 "AU166":("verified_offline","phase08_real_delivery.json",
          "Deliberately missing media fails in isolated FFmpeg batch; two other outputs pass"),
 "AU167":("verified_offline","phase09_offline_batch_acceptance.json",
          "Two actual two-pass FFmpeg loudnorm masters with targets and validation, not Audition Match Loudness"),
}
for ident,(state,proof,note) in up.items():
    row=by[ident]
    assert not row["status"].startswith("verified_"),(ident,row["status"])
    row.update({"status":state,"evidence":"tests/receipts/"+proof,
                "qualification":note})
extras=[
 ("Native QA DOM","Track arm and visibility native live toggle, restore and QA-only cleanup",
  "verified_native_live","phase09_native_acceptance.json"),
 ("Native Batch","Three-item QA native Favorites batch with output validation",
  "verified_native_live","phase09_native_batch_acceptance.json"),
 ("Native Batch","Three-item QA native sample-rate/bit-depth batch",
  "verified_native_live","phase09_native_batch_acceptance.json"),
 ("Native Markers","Cue and Subclip point/range native WAV persisted-reopen",
  "verified_native_live","phase09_native_markers.json"),
 ("Offline Batch","Two-pass normalized LUFS batch with independent failure isolation",
  "verified_offline","phase09_offline_batch_acceptance.json"),
]
for cat,name,status,proof in extras:
    rows.append({"id":"AU"+str(len(rows)+1).zfill(3),"category":cat,
                 "name":name,"status":status,
                 "access_route":"Audition native DOM" if status=="verified_native_live" else "WSL FFmpeg",
                 "evidence":"tests/receipts/"+proof,
                 "qualification":"Only QA-scoped evidence; inspect receipts for parameters"})
assert len(rows)==384 and len({x["id"] for x in rows})==384
counts=dict(sorted(Counter(x["status"] for x in rows).items()))
d.update({"total":384,"counts":counts,"latest_phase":9,"as_of":"2026-10-10"})
(A/"Audition_26_feature_ledger.json").write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")
runtime=json.loads(old_runtime.read_text(encoding="utf-8"))
methods=[{"method":key,"signature":str(inspect.signature(getattr(C,key)))}
         for key in sorted(x for x in dir(C) if not x.startswith("_") and callable(getattr(C,x)))]
assert len(methods)==96,len(methods)
runtime.update({"controller_methods":methods,"features":384,"counts":counts,
                "latest_phase":9,"as_of":"2026-10-10"})
(A/"Audition_26_runtime_api.json").write_text(json.dumps(runtime,ensure_ascii=False,indent=2),encoding="utf-8")
def doc(name,lines):
    (A/name).write_text("\n".join(lines)+"\n",encoding="utf-8")
index=["# Audition 26 Controller API 与接口目录（第九轮）","",
       "本机 Audition 26.0.0；384 个审计条目；96 个公开 Controller 方法。",
       "脚本方法与 GUI 菜单/CEP SDK 不是同一回事。","",
       "## Controller 公开签名","","| 方法 | 签名 |","|---|---|"]
index += ["| "+m["method"]+" | "+m["signature"].replace("|","/")+" |" for m in methods]
doc("Audition_26_API_接口目录.md",index)
matrix=["# Audition 26 全功能开发矩阵（第九轮）","",
        "上一轮冻结基线：api/Audition_26_phase08_baseline_379.json。",
        "本轮旧问题仅依证据升级，故障未解决的 CEP/Bus/SDK 状态保留。","",
        "| 状态 | 数量 |","|---|---:|"]
matrix+=["| "+k+" | "+str(v)+" |" for k,v in counts.items()]
matrix+=["","| ID | 功能 | 状态 | 证据 |","|---|---|---|---|"]
matrix+=["| "+x["id"]+" | "+x["name"]+" | "+x["status"]+" | "+x.get("evidence","")+" |" for x in rows]
doc("Audition_26_全功能开发矩阵.md",matrix)
remaining=[x for x in rows if not x["status"].startswith("verified_")]
assert len(remaining)==107,len(remaining)
todo=["# Audition 26 未完成与依赖清单（第九轮）","",
      f"384 个审计条目中仍有 {len(remaining)} 项未完整验证。",
      "QA 通过不能自动证明录音硬件/自定义 CEP/AMIO/ASIO/视频往返能力。","",
      "| ID | 功能 | 当前状态 |","|---|---|---|"]
todo+=["| "+x["id"]+" | "+x["name"]+" | "+x["status"]+" |" for x in remaining]
doc("Audition_26_未完成与依赖清单.md",todo)
cross=[{"id":key,"name":by[key]["name"],"status":val[0],
        "evidence":"tests/receipts/"+val[1],"qualification":val[2]} for key,val in up.items()]
(A/"Audition_26_phase09_evidence_crosswalk.json").write_text(
    json.dumps(cross,ensure_ascii=False,indent=2),encoding="utf-8")
print("PHASE09_CATALOG",len(rows),"METHODS",len(methods),"REMAINING",len(remaining),
      "UPGRADES",len(up),"ADDED",len(extras),flush=True)
