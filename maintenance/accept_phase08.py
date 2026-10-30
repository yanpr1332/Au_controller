"""Phase 08 one-shot acceptance of actual Debian FFmpeg batch conversions."""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from audition_controller import AuditionController as C

def digest(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1<<20),b""):
            h.update(block)
    return h.hexdigest()

def main():
    tests=ROOT/"tests"
    out=tests/"native_outputs"/"phase08_delivery"
    out.mkdir(parents=True,exist_ok=True)
    a=tests/"fixtures"/"accept_au_sine_48k_mono.wav"
    b=tests/"fixtures"/"accept_batch_source_1.wav"
    missing=tests/"fixtures"/"accept_phase08_missing.wav"
    if missing.exists():raise RuntimeError("Fault injection file unexpectedly exists")
    inputs={str(x):digest(x) for x in (a,b)}
    phase1=C.batch_transcode_audio([missing,a,b],out,fmt="flac",confirm=True)
    assert (phase1["passed"],phase1["failed"],phase1["skipped"])==(2,1,0),phase1
    phase2=C.batch_transcode_audio([a],out,fmt="mp3",bitrate_kbps=192,confirm=True)
    assert (phase2["passed"],phase2["failed"],phase2["skipped"])==(1,0,0),phase2
    artifacts=[]
    for row in phase1["jobs"]+phase2["jobs"]:
        if row["status"]!="passed":continue
        path=Path(row["destination"])
        probe=C.ffprobe_media(path)
        streams=[s for s in probe["streams"] if s.get("codec_type")=="audio"]
        assert len(streams)==1 and int(streams[0]["sample_rate"])==48000,probe
        assert int(streams[0]["channels"])==2,probe
        assert row["sha256"]==digest(path)
        artifacts.append({"path":str(path),"sha256":row["sha256"],
                          "codec":streams[0]["codec_name"],
                          "bytes":row["bytes"],"rate":int(streams[0]["sample_rate"]),
                          "channels":int(streams[0]["channels"])})
    assert len(artifacts)==3
    assert all(digest(Path(name))==sha for name,sha in inputs.items())
    assert not any(x.name.startswith(".audition_batch_") for x in out.iterdir())
    receipt={"phase":8,"passed":True,"host":"Windows 11 + Debian WSL FFmpeg",
             "native_audition_export":False,
             "jobs_with_missing_source":phase1,"mp3_jobs":phase2,
             "inputs_sha256":inputs,"source_unchanged":True,
             "outputs":artifacts,"no_stage_files":True}
    path=tests/"receipts"/"phase08_real_delivery.json"
    path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding="utf-8")
    print("PHASE08_REAL_BATCH",len(artifacts),"ARTIFACTS",phase1["failed"],"ISOLATED_FAILURE",
          "INPUTS_IMMUTABLE",receipt["source_unchanged"],flush=True)

if __name__=="__main__":
    main()
