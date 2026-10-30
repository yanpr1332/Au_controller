"""Source-preserving offline two-pass LUFS batch mastering for Audition pipelines.

Delegates each item to proven Debian FFmpeg loudnorm, not Audition's Match Loudness
panel; stages all outputs separately and uses exclusive write-once publication.
"""
from __future__ import annotations
import hashlib
import os
import re
import shutil
import tempfile
from pathlib import Path

def _digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as src:
        for block in iter(lambda:src.read(1<<20),b""):
            h.update(block)
    return h.hexdigest()


class AuditionBatchMastering:
    @classmethod
    def batch_loudness_master(cls,sources, output_folder, *,
                              target_lufs=-16.0,ceiling_dbtp=-1.5,
                              rate=48000,suffix="_loudness",
                              confirm=False,stop_on_error=False):
        if not isinstance(sources,list) or not 1<=len(sources)<=100:
            raise ValueError("Expected 1..100 audio sources")
        if not isinstance(suffix,str) or not re.fullmatch(r"_[A-Za-z0-9_-]{1,36}",suffix):
            raise ValueError("Unsafe file suffix")
        if type(confirm)!=bool or type(stop_on_error)!=bool:
            raise ValueError("Boolean flags required")
        level=cls._f(target_lufs,-36,-8,"target LUFS")
        tp=cls._f(ceiling_dbtp,-9,-.1,"true peak ceiling")
        if type(rate)!=int or rate not in (16000,32000,44100,48000,96000):
            raise ValueError("Unsupported sample rate")
        outdir=Path(output_folder).resolve()
        if not outdir.is_dir():raise ValueError("Existing output directory required")
        paths=[Path(x).resolve() for x in sources]
        targets=[outdir/(x.stem+suffix+".wav") for x in paths]
        if len(set(str(x).casefold() for x in paths))!=len(paths):
            raise ValueError("Duplicate input paths")
        if len(set(str(x).casefold() for x in targets))!=len(targets):
            raise ValueError("Duplicate output names")
        if any(dst.exists() or str(dst).casefold() in {str(src).casefold() for src in paths}
               for dst in targets):
            raise FileExistsError("Existing/colliding output")
        if not confirm:
            return {"dry_run":True,"outputs":[str(p) for p in targets],
                    "target_lufs":level,"true_peak_dbtp":tp,
                    "native_audition_loudness":False}
        rows=[];passed=failed=skipped=0
        for i,(src,dst) in enumerate(zip(paths,targets)):
            row={"source":str(src),"output":str(dst),"status":"failed"}
            published=False
            try:
                if not src.is_file():raise FileNotFoundError(src)
                original=_digest(src)
                with tempfile.TemporaryDirectory(prefix=".au_loudness_",dir=outdir) as td:
                    stage=Path(td)/dst.name
                    result=cls.master_loudness(src,stage,target_lufs=level,
                                               ceiling_dbtp=tp,rate=rate,confirm=True)
                    if not result.get("qa_passed"):
                        raise RuntimeError("Two-pass output did not meet stated loudness tolerance")
                    stage_hash=_digest(stage)
                    if result["sha256"]!=stage_hash:
                        raise RuntimeError("Two-pass output checksum mismatched")
                    # O_EXCL refuses to overwrite a file published concurrently.
                    with dst.open("xb") as f:
                        published=True
                        with stage.open("rb") as inp:
                            shutil.copyfileobj(inp,f,length=1<<20)
                        f.flush();os.fsync(f.fileno())
                    if _digest(dst)!=stage_hash:
                        raise RuntimeError("Output checksum differs from stage")
                if _digest(src)!=original:
                    raise RuntimeError("Audio input was modified")
                row.update({"status":"passed","sha256":stage_hash,
                            "source_sha256":original,"backend":result["backend"],
                            "measured_after":result["measured_after"]})
                passed+=1
            except Exception as error:
                if published:dst.unlink(missing_ok=True)
                row["error"]=type(error).__name__+": "+str(error)
                failed+=1
            rows.append(row)
            if row["status"]!="passed" and stop_on_error:
                for j in range(i+1,len(paths)):
                    rows.append({"source":str(paths[j]),"output":str(targets[j]),"status":"skipped"})
                    skipped+=1
                break
        return {"total":len(paths),"passed":passed,"failed":failed,"skipped":skipped,
                "rows":rows,"backend":"WSL Debian two-pass loudnorm",
                "native_audition_loudness":False}
