"""Phase09 current release gate: 326 regressions, native Audition and real media."""
from pathlib import Path
import argparse,ast,hashlib,inspect,json,re,subprocess,sys
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from audition_controller import AuditionController as C
A=R/"api";T=R/"tests/receipts"
def load(path):return json.loads(path.read_text(encoding="utf-8"))
def digest(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as file:
        for x in iter(lambda:file.read(1<<20),b""):h.update(x)
    return h.hexdigest()
def check(*,full_tests=True,sdk=False):
    controls={}
    d=load(A/"Audition_26_feature_ledger.json")
    runtime=load(A/"Audition_26_runtime_api.json")
    baseline=load(A/"Audition_26_phase08_baseline_379.json")
    pending=[x for x in d["features"] if not x["status"].startswith("verified_")]
    controls["phase08_baseline_379"]=baseline["total"]==379
    controls["phase09_feature_384"]=d["total"]==384 and len(d["features"])==384
    controls["unique_ids"]=len({x["id"] for x in d["features"]})==384
    controls["counts_match"]=sum(d["counts"].values())==384
    controls["remaining_107"]=len(pending)==107
    methods={x for x in dir(C) if not x.startswith("_") and callable(getattr(C,x))}
    controls["controller_96_methods"]=len(methods)==96 and methods=={x["method"] for x in runtime["controller_methods"]}
    controls["python_ast_parses"]=all(ast.parse(p.read_text(encoding="utf-8")) is not None for p in
       [R/"audition_controller.py",*(R/"controller_modules").glob("*.py"),*(R/"maintenance").glob("*.py")])
    native=load(T/"phase09_native_acceptance.json")
    controls["track_armed_and_visible_real"]=native["passed"] and all(native["checks"][k] for k in (
         "native_armed_toggle","native_visible_toggle","live_session_closed","no_record_action"))
    controls["batch_open_native_three"]=native["imports"]["count"]==3 and native["imports"]["sources_unchanged"]
    controls["native_44k24"]=native["resample"]["readback"]["rate"]==44100 and (
         digest(native["resample"]["output"])==native["resample"]["readback"]["sha256"])
    controls["favorite_single_true"]=native["favorite"]["response"]["FAVORITE_RESULT"]=="true"
    batch=load(T/"phase09_native_batch_acceptance.json")
    controls["native_batch_six"]=batch["passed"] and all(batch[name]["passed"]==3 for name in ("favorite","resample"))
    controls["native_batch_output_hashes"]=all(
         digest(row["output"])==row["sha256"] for name in ("favorite","resample") for row in batch[name]["rows"])
    controls["native_host_documents_closed"]=batch["host"]["DOCUMENTS"]=="0"
    marks=load(T/"phase09_native_markers.json")
    controls["native_marker_type_reopen"]=marks["passed"] and marks["supports_distinct_type"] and (
         marks["verified_count"]==3)
    controls["marker_output_hash"]=digest(marks["output"])==marks["output_sha256"]
    offline=load(T/"phase09_offline_batch_acceptance.json")
    controls["offline_two_loudnorm"]=offline["passed"] and offline["batch_master"]["passed"]==2 and (
         offline["batch_master"]["failed"]==1)
    controls["offline_two_mp3"]=offline["batch_mp3"]["passed"]==2
    controls["offline_all_output_hashes"]=all(
         digest(row["output"] if "output" in row else row["destination"])==row["sha256"] for row in
         offline["batch_master"]["rows"]+offline["batch_mp3"]["jobs"] if row["status"]=="passed")
    cross=load(A/"Audition_26_phase09_evidence_crosswalk.json")
    controls["11_evidence_promotions"]=len(cross)==11 and all(
          (R/row["evidence"]).is_file() for row in cross)
    controls["CEP_BUS_SDK_unresolved"]=all(any(x["status"]==s for x in pending) for s in (
         "blocked_host_runtime","blocked_native_api","sdk_or_hardware_required"))
    controls["remaining_file_present"]=(A/"Audition_26_未完成与依赖清单.md").is_file()
    log=None;num=None
    if full_tests:
        p=subprocess.run([sys.executable,"-B","-m","unittest","discover","-s","tests","-q"],
             cwd=str(R),capture_output=True,text=True,errors="replace",timeout=220)
        ma=re.search(r"Ran (\d+) tests",p.stderr)
        num=int(ma.group(1)) if ma else None
        controls["326_tests"]=p.returncode==0 and num==326
        log=p.stderr[-1800:]
    status=None
    if sdk:
        status=C().status()
        controls["native_host_26"]=status.get("APP")=="Audition" and status.get("VERSION")=="26.0.0"
        controls["native_documents_zero"]=status.get("DOCUMENTS")=="0"
    receipt={"phase":9,"passed":all(controls.values()),"tests":num,
             "check_count":len(controls),"checks_passed":sum(controls.values()),
             "checks":controls,"controller_methods":96,"features":384,
             "remaining":107,"live_host":status,"log":log,
             "real_native_batch":True,"real_marker_type":True,
             "CEP_host_loaded":False,"Native_bus_remove_fixed":False}
    if full_tests and sdk:
        (T/"phase09_final_acceptance.json").write_text(
             json.dumps(receipt,ensure_ascii=False,indent=2),encoding="utf-8")
    print("PHASE09_RELEASE",receipt["passed"],"CHECKS",sum(controls.values()),"/",
          len(controls),"TESTS",num,"METHODS",96,"FEATURES",384,
          "PENDING",107,"FAILED",[k for k,v in controls.items() if not v],flush=True)
    if not receipt["passed"]:raise SystemExit(1)
    return receipt
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--sdk",action="store_true")
    p.add_argument("--skip-tests",action="store_true")
    args=p.parse_args()
    check(full_tests=not args.skip_tests,sdk=args.sdk)
