"""Native Audition QA-only Favorites and sample-format batch acceptance.

Runs the installed Audition 26 DOM on fixture media, independently saves and
decodes outputs, refuses collisions and never touches arbitrary user files.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import re
from scipy.io import wavfile


def _sha256(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for part in iter(lambda:f.read(1<<20),b""):
            h.update(part)
    return h.hexdigest()


class AuditionNativeBatchProcessing:
    def native_batch_process_qa(self, sources, output_folder, *,
                                task="favorite", favorite="Normalize to -3 dB",
                                rate=44100, bit_depth=24,
                                suffix="_phase09_native",
                                stop_on_error=False,confirm=False):
        """Batch process 1..12 synthetic WAVs, with per-item native receipts."""
        from audition_controller import ROOT
        from controller_modules.native_safe import AuditionNativeSafe
        if task not in ("favorite","resample"):raise ValueError("Unknown native QA batch task")
        if not isinstance(sources,list) or not 1<=len(sources)<=12:
            raise ValueError("1..12 QA WAV inputs required")
        if not isinstance(suffix,str) or not re.fullmatch(r"_[a-zA-Z0-9_-]{1,40}",suffix):
            raise ValueError("Unsafe output suffix")
        if type(stop_on_error)!=bool or type(confirm)!=bool:
            raise ValueError("Expected Boolean flags")
        if task=="favorite" and favorite not in {
            "Normalize to -3 dB","Normalize to -0.1 dB","DeNoise","DeReverb",
            "Remove 60 Hz Hum","Repair DC Offset"}:
            raise ValueError("Favorite is not allowlisted")
        if task=="resample" and (type(rate)!=int or rate not in (16000,22050,32000,44100,48000,96000)
                                 or type(bit_depth)!=int or bit_depth not in (16,24,32)):
            raise ValueError("Bad sample format")
        allowed=(ROOT/"tests"/"native_outputs").resolve()
        outdir=Path(output_folder).resolve()
        if (allowed!=outdir and allowed not in outdir.parents) or not outdir.is_dir():
            raise PermissionError("Native outputs must be under the existing QA output folder")
        src=[Path(s).resolve() for s in sources]
        dst=[outdir/(s.stem+suffix+".wav") for s in src]
        if len(set(map(str,src)))!=len(src) or len(set(map(str,dst)))!=len(dst):
            raise ValueError("Duplicate QA source/output")
        for a,b in zip(src,dst):
            AuditionNativeSafe._native_test_paths(a,b)
        if not confirm:
            return {"dry_run":True,"task":task,"sources":[str(x) for x in src],
                    "outputs":[str(x) for x in dst]}
        rows=[];success=failed=skipped=0
        for i,(a,b) in enumerate(zip(src,dst)):
            item={"source":str(a),"output":str(b),"task":task}
            original=_sha256(a)
            try:
                if task=="favorite":
                    r=self.audition_native_favorite_export(a,b,favorite=favorite,confirm=True)
                    values=r["response"]
                    if values.get("FAVORITE_RESULT")!="true" or values.get("EXISTS")!="true" or values.get("BUSY")!="false":
                        raise RuntimeError("Audition Favorite failed or did not finish")
                else:
                    r=self.audition_native_resample_export(
                        a,b,sample_rate=rate,bit_depth=bit_depth,confirm=True)
                    values=r["response"]
                    if values.get("EXISTS")!="true" or any(values.get(x)!="false" for x in
                        ("INVALID_SETTINGS","INVALID_SAMPLE_TYPE","INTERNAL_ERROR")):
                        raise RuntimeError("Audition native conversion reported error")
                sr,payload=wavfile.read(b)
                if len(payload)<1:raise RuntimeError("Output cannot be decoded")
                if task=="resample" and (sr!=rate or
                   (bit_depth==16 and str(payload.dtype)!="int16") or
                   (bit_depth==24 and str(payload.dtype)!="int32")):
                    raise RuntimeError("Output sample type mismatch")
                if _sha256(a)!=original:raise RuntimeError("Source WAV changed")
                item.update({"status":"passed","sha256":_sha256(b),
                            "source_sha256":original,"rate":int(sr),
                            "frames":int(len(payload)),"dtype":str(payload.dtype),
                            "native_response":values})
                success+=1
            except Exception as e:
                item.update({"status":"failed","error":str(e)})
                failed+=1
            rows.append(item)
            # Native application must return to a clean state between items.
            try:self._qa_close_documents()
            except Exception as e:
                item["cleanup_error"]=repr(e)
                item["status"]="failed"
                if "sha256" in item: success-=1;failed+=1
                stop_on_error=True
            if item["status"]=="failed" and stop_on_error:
                for j in range(i+1,len(src)):
                    rows.append({"source":str(src[j]),"output":str(dst[j]),"status":"skipped"})
                    skipped+=1
                break
        return {"task":task,"total":len(src),"passed":success,
                "failed":failed,"skipped":skipped,
                "rows":rows,"native_audition_batch_qa":True}
