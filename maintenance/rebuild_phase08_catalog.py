"""Rebuild current phase-08 feature catalog from frozen phase-07 evidence.

The old phase-07 builder is retained strictly for historical reproduction.
Only fault-injected controller reliability is promoted; no native CEP/SDK claims.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import inspect
import json
import subprocess
import sys
import re

R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R))
from audition_controller import AuditionController as C
A=R/"api"
T=R/"tests"/"receipts"
# Historical rebuild: never overwrite a newer live feature catalog.
_live=A/"Audition_26_feature_ledger.json"
if _live.is_file() and json.loads(_live.read_text(encoding="utf-8")).get("latest_phase",0)>8:
    raise RuntimeError("Phase08 catalog frozen; use maintenance/rebuild_phase09_catalog.py")
baseline=A/"Audition_26_phase07_baseline_375.json"
runtime_base=A/"Audition_26_phase07_runtime_api.json"
delivery_path=T/"phase08_real_delivery.json"
fault_path=T/"phase08_transport_faults.json"
assert baseline.is_file() and runtime_base.is_file()
delivery=json.loads(delivery_path.read_text(encoding="utf-8"))
assert delivery["passed"] and delivery["source_unchanged"] and len(delivery["outputs"])==3
run=subprocess.run([sys.executable,"-B","-m","unittest","discover","-s","tests",
                    "-p","test_phase08_transport_batch.py","-q"],
                   cwd=str(R),capture_output=True,text=True,errors="replace",timeout=45)
match=re.search(r"Ran (\d+) tests?",run.stderr)
assert run.returncode==0 and match and int(match.group(1))==12,run.stderr[-1500:]
fault={"phase":8,"passed":True,"count":int(match.group(1)),
       "method":"mocked Audition -r launcher and controlled reply files",
       "real_host_timeout_proved":False,"host_failure_propagates":True,
       "timeout_cleanup_verified":True,"unique_task_names_verified":True,
       "output_collision_guard_verified":True,"batch_failure_isolation_verified":True,
       "unit_test_stdout":run.stderr[-450:]}
fault_path.write_text(json.dumps(fault,ensure_ascii=False,indent=2),encoding="utf-8")
d=json.loads(baseline.read_text(encoding="utf-8"))
assert d["total"]==375
rows=d["features"]
by={x["id"]:x for x in rows}
for key in ("AU012","AU258"):
    by[key].update({"status":"verified_offline",
                    "evidence":str(fault_path.relative_to(R)),
                    "qualification":"Mocked bounded controller timeout and cleanup; "
                    "does NOT prove real Audition-host cancellation or runtime recovery."})
extras=[
 ("Controller reliability","Unique request nonce and cleanup for JSX transport",
  "verified_offline",fault_path,"Mocked task replies and collision test, plus live status call"),
 ("Controller reliability","JSX error propagation and controlled timeout fault injection",
  "verified_offline",fault_path,"12 synthetic exception and guard tests; does not kill Audition"),
 ("External batch delivery","FLAC and MP3 batches with isolated failures",
  "verified_offline",delivery_path,"3 real FFmpeg/ffprobe files; not native Au batch favorites"),
 ("External batch delivery","Staged exclusive publish with codec, SHA256 and source immutability",
  "verified_offline",delivery_path,"O_EXCL write-once publish, stage rollback and content verification"),
]
for group,name,status,proof,note in extras:
    rows.append({"id":"AU"+str(len(rows)+1).zfill(3),"category":group,
                 "name":name,"status":status,"access_route":"Controller + external WSL/Python",
                 "evidence":str(proof.relative_to(R)),"qualification":note})
assert len(rows)==379 and len({x["id"] for x in rows})==379
d.update({"total":379,"counts":dict(sorted(Counter(x["status"] for x in rows).items())),
          "latest_phase":8,"as_of":"2026-10-10"})
(A/"Audition_26_feature_ledger.json").write_text(
    json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")
runtime=json.loads(runtime_base.read_text(encoding="utf-8"))
methods=[{"method":name,"signature":str(inspect.signature(getattr(C,name)))}
         for name in sorted(x for x in dir(C) if not x.startswith("_") and callable(getattr(C,x)))]
assert len(methods)==91,len(methods)
runtime.update({"controller_methods":methods,"features":379,"counts":d["counts"],
                "latest_phase":8,"as_of":"2026-10-10"})
(A/"Audition_26_runtime_api.json").write_text(
    json.dumps(runtime,ensure_ascii=False,indent=2),encoding="utf-8")
def md(file,lines):
    (A/file).write_text("\n".join(lines)+"\n",encoding="utf-8")
index=["# Audition 26 Controller 接口目录（第八轮）","",
       f"Controller 公开方法：{len(methods)}；功能审计：{len(rows)}；原生菜单快照：474。",
       "各条目必须区分 native_live / sesx_reopened / offline / unverified。",
       "完整运行时元数据：api/Audition_26_runtime_api.json。","",
       "## Controller 方法","","| 方法 | 签名 |","|---|---|"]
for method in methods:
    index.append("| "+method["method"]+" | "+method["signature"].replace("|","/")+" |")
md("Audition_26_API_接口目录.md",index)
matrix=["# Audition 26 全功能开发矩阵（第八轮）","",
        "第七轮冻结快照：api/Audition_26_phase07_baseline_375.json。",
        "第八轮新增 4 个经检验的能力条目；仅 2 个旧 P0 故障注入条目升级为离线验证。",
        "本轮新模块不等于 Audition 原生效果器/CEP SDK。","",
        "## 状态计数","","| 状态 | 数量 |","|---|---:|"]
matrix.extend("| "+k+" | "+str(v)+" |" for k,v in d["counts"].items())
matrix.extend(["","## 功能明细","","| ID | 类别 | 功能 | 状态 | 证据 |","|---|---|---|---|---|"])
for row in rows:
    matrix.append("| "+row["id"]+" | "+row["category"]+" | "+row["name"]+" | "+
                  row["status"]+" | "+row.get("evidence","")+" |")
md("Audition_26_全功能开发矩阵.md",matrix)
unverified=[row for row in rows if not row["status"].startswith("verified_")]
remaining=["# Audition 26 未完成与外部依赖清单（第八轮）","",
           f"当前 {len(rows)} 条中仍有 {len(unverified)} 条未完整验证。",
           "FFmpeg 外部批量能力不作为 Au 原生 Batch/Favorites 关闭证据。","",
           "| ID | 功能 | 状态 | 推荐处理 |","|---|---|---|---|"]
for item in unverified:
    status=item["status"]
    action=("继续隔离 CEP PlugPlugSetup 宿主故障" if "cep" in status or "host" in status else
            "等待 SDK/外部设备或真实媒体" if "sdk" in status else
            "Adobe Native API 缺陷，SESX 保留回避措施" if status=="blocked_native_api" else
            "需原生界面和真实输出回读" if status in ("ui_or_media_pending","partial_native_live") else
            "补隔离功能试验与收据")
    remaining.append("| "+item["id"]+" | "+item["name"]+" | "+status+" | "+action+" |")
md("Audition_26_未完成与依赖清单.md",remaining)
print("PHASE08_CATALOG",len(rows),"ITEMS",len(methods),"METHODS",
      len(unverified),"PENDING",fault["count"],"FAULT_TESTS",flush=True)
