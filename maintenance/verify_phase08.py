"""Phase-08 release gate: immutable historical coverage plus current tests and media."""
from __future__ import annotations
import argparse
import ast
import hashlib
import inspect
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from audition_controller import AuditionController as C
API=ROOT/"api"
RECEIPTS=ROOT/"tests"/"receipts"


def digest(path:Path):
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for b in iter(lambda:stream.read(1<<20),b""):
            h.update(b)
    return h.hexdigest()


def check(*,full_tests=True,sdk=False):
    checks={}
    ledger=json.loads((API/"Audition_26_feature_ledger.json").read_text(encoding="utf-8"))
    historical=json.loads((API/"Audition_26_phase07_baseline_375.json").read_text(encoding="utf-8"))
    runtime=json.loads((API/"Audition_26_runtime_api.json").read_text(encoding="utf-8"))
    receipt=json.loads((RECEIPTS/"phase08_real_delivery.json").read_text(encoding="utf-8"))
    fault=json.loads((RECEIPTS/"phase08_transport_faults.json").read_text(encoding="utf-8"))
    methods={x for x in dir(C) if not x.startswith("_") and callable(getattr(C,x))}
    advertised={x["method"] for x in runtime["controller_methods"]}
    pending=[x for x in ledger["features"] if not x["status"].startswith("verified_")]
    checks["phase07_snapshot_375"]=historical["total"]==375
    checks["phase08_ledger_379"]=ledger["total"]==379 and len(ledger["features"])==379
    checks["unique_ids"]=len({x["id"] for x in ledger["features"]})==379
    checks["status_counts"]=sum(ledger["counts"].values())==379
    checks["unverified_118"]=len(pending)==118
    checks["public_methods_91"]=len(methods)==91 and methods==advertised
    checks["all_python_modules_parse"]=all(
        ast.parse(p.read_text(encoding="utf-8")) is not None for p in
        [ROOT/"audition_controller.py",*(ROOT/"controller_modules").glob("*.py")])
    checks["previous_phase07_acceptance"]=json.loads(
        (RECEIPTS/"phase07_final_acceptance.json").read_text(encoding="utf-8"))["checks_passed"]==41
    checks["real_ffmpeg_outputs"]=receipt["passed"] and len(receipt["outputs"])==3 and all(
        Path(x["path"]).is_file() and digest(Path(x["path"]))==x["sha256"] for x in receipt["outputs"])
    checks["source_immutability"]=receipt["source_unchanged"] and all(
        digest(Path(path))==sha for path,sha in receipt["inputs_sha256"].items())
    checks["real_failure_isolation"]=receipt["jobs_with_missing_source"]["failed"]==1 and (
        receipt["jobs_with_missing_source"]["passed"]==2)
    checks["failure_injection_tests"]=fault["passed"] and fault["count"]==12
    checks["uncured_host_blockers_still_listed"]=all(any(x["status"]==state for x in pending)
        for state in ("blocked_host_runtime","blocked_native_api","sdk_or_hardware_required"))
    checks["current_docs_present"]=all((API/name).exists() for name in
        ("Audition_26_API_接口目录.md","Audition_26_全功能开发矩阵.md",
         "Audition_26_未完成与依赖清单.md"))
    log=""
    tests_number=None
    if full_tests:
        run=subprocess.run([sys.executable,"-B","-m","unittest","discover","-s","tests","-q"],
            cwd=str(ROOT),capture_output=True,text=True,errors="replace",timeout=180)
        match=re.search(r"Ran (\d+) tests",run.stderr)
        tests_number=int(match.group(1)) if match else None
        checks["all_304_tests"]=run.returncode==0 and tests_number==304
        log=run.stderr[-1100:]
    host=None
    if sdk:
        ctl=C()
        host=ctl.status()
        checks["native_host_connected"]=host.get("APP")=="Audition" and host.get("VERSION")=="26.0.0"
        checks["native_session_is_clean"]=host.get("DOCUMENTS")=="0"
        try:
            ctl._run_jsx('throw "PHASE08_INJECTED_ERROR";',"phase08_live_error",timeout=25)
            checks["native_error_propagation"]=False
        except RuntimeError as err:
            checks["native_error_propagation"]="PHASE08_INJECTED_ERROR" in str(err)
    result={"phase":8,"passed":all(checks.values()),"check_count":len(checks),
            "checks_passed":sum(checks.values()),"checks":checks,
            "features":379,"methods":91,"pending":118,"tests":tests_number,
            "native_host":host,"native_error_test":sdk,
            "unresolved_native_cep":True,"unresolved_native_bus_remove":True,
            "test_log_tail":log}
    # Never downgrade the authoritative full release receipt with a quick check.
    if full_tests and sdk:
        (RECEIPTS/"phase08_final_acceptance.json").write_text(
             json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print("PHASE08_RELEASE",result["passed"],
          "CHECKS",result["checks_passed"],"/",result["check_count"],
          "TESTS",tests_number,"PENDING",118,
          "FAILED",[key for key,val in checks.items() if not val],flush=True)
    if not result["passed"]:
        raise SystemExit(1)
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--skip-tests",action="store_true")
    parser.add_argument("--sdk",action="store_true")
    args=parser.parse_args()
    check(full_tests=not args.skip_tests,sdk=args.sdk)
