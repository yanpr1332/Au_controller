from __future__ import annotations
import argparse
import os
import ctypes
import ctypes.wintypes as wt
import json
import math
import re
import subprocess
import time
import uuid
import wave
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
AUDITION_EXE = Path(os.environ.get("AUDITION_EXE", str(ROOT.parent / "Adobe Audition 2026" / "Adobe Audition.exe")))
RUNTIME_DIR = ROOT / "_runtime"
SCRIPTS_DIR = ROOT / "scripts"

# Native Audition menu command IDs verified on Audition 26.0.0.
CMD_MIXDOWN_NEW_FILE_ENTIRE = 35169
CMD_EXPORT_MIXDOWN_ENTIRE = 35025
CMD_MATCH_LOUDNESS = 35419
CMD_TOGGLE_SPECTRAL = 35361
CMD_SPOT_HEALING_BRUSH = 35250


from controller_modules.audio_dsp import AuditionAudioLab
from controller_modules.native_safe import AuditionNativeSafe
from controller_modules.ffmpeg_audio import AuditionFFmpegLab
from controller_modules.sesx_lab import AuditionSessionLab
from controller_modules.batch_lab import AuditionBatchLab
from controller_modules.native_sesx import AuditionRealSession
from controller_modules.native_multitrack import AuditionNativeMultitrack
from controller_modules.ffmpeg_mastering import AuditionMasteringLab
from controller_modules.audio_forensics import AuditionAudioForensics
from controller_modules.delivery_pipeline import AuditionDeliveryPipeline
from controller_modules.native_sesx_bus import AuditionBusRouting
from controller_modules.native_menu_registry import AuditionNativeMenuRegistry
from controller_modules.native_sesx_portability import AuditionSessionPortability
from controller_modules.native_eq import AuditionNativeEQ
from controller_modules.native_clip_advanced import AuditionClipAdvanced
from controller_modules.podcast_automation import AuditionPodcastAutomation
from controller_modules.chapter_lab import AuditionChapterLab
from controller_modules.session_integrity import AuditionSessionIntegrity
from controller_modules.effect_recipes import AuditionEffectRecipes
from controller_modules.r128_timeline import AuditionR128Timeline
from controller_modules.metadata_delivery import AuditionMetadataDelivery
from controller_modules.xmp_marker_edit import AuditionXmpEditor
from controller_modules.native_transport_qa import AuditionNativeTransportQA
from controller_modules.native_arrangement import AuditionArrangementLab
from controller_modules.production_jobs import AuditionProductionJobs
from controller_modules.waveform_workbench import AuditionWaveformWorkbench
from controller_modules.native_clip_split import AuditionNativeClipSplit
from controller_modules.channel_tools import AuditionChannelTools
from controller_modules.batch_delivery import AuditionBatchDelivery
from controller_modules.native_qa_batch import AuditionNativeQABatch
from controller_modules.native_batch_processing import AuditionNativeBatchProcessing
from controller_modules.native_marker_kinds import AuditionMarkerKindsQA
from controller_modules.batch_mastering import AuditionBatchMastering


from controller_modules.production_session import AuditionProductionSession
from controller_modules.job_queue import AuditionJobQueue
from controller_modules.production_native import AuditionProductionNative
from controller_modules.production_audio import AuditionProductionAudio
from controller_modules.resumable_jobs import AuditionResumableJobs
from controller_modules.session_import import AuditionSessionImport
from controller_modules.media_search import AuditionMediaSearch
from controller_modules.native_sdk_session import AuditionNativeSDKSession
from controller_modules.native_automation import AuditionNativeAutomation
from controller_modules.native_rack import AuditionNativeRack
from controller_modules.native_favorite_production import AuditionNativeFavoriteProduction
from controller_modules.native_recording import AuditionNativeRecording
from controller_modules.control_surface import AuditionControlSurface
from controller_modules.video_delivery import AuditionVideoDelivery
from controller_modules.spectral_geometry import AuditionSpectralGeometry
from controller_modules.native_uia_inspection import AuditionUIAInspection
from controller_modules.host_lock import audition_host_lock


class AuditionController(AuditionUIAInspection, AuditionSpectralGeometry, AuditionVideoDelivery, AuditionControlSurface, AuditionNativeRecording, AuditionNativeFavoriteProduction, AuditionNativeRack, AuditionNativeAutomation, AuditionNativeSDKSession, AuditionMediaSearch, AuditionResumableJobs, AuditionSessionImport, AuditionProductionAudio, AuditionProductionNative, AuditionJobQueue, AuditionProductionSession, AuditionBatchMastering, AuditionMarkerKindsQA, AuditionNativeBatchProcessing, AuditionNativeQABatch, AuditionBatchDelivery, AuditionChannelTools, AuditionNativeClipSplit, AuditionWaveformWorkbench, AuditionProductionJobs, AuditionArrangementLab, AuditionNativeTransportQA, AuditionXmpEditor, AuditionMetadataDelivery, AuditionR128Timeline, AuditionEffectRecipes, AuditionSessionIntegrity, AuditionChapterLab, AuditionPodcastAutomation, AuditionClipAdvanced, AuditionNativeEQ, AuditionSessionPortability, AuditionNativeMenuRegistry, AuditionBusRouting, AuditionDeliveryPipeline, AuditionAudioForensics, AuditionMasteringLab, AuditionNativeMultitrack, AuditionRealSession, AuditionBatchLab, AuditionSessionLab, AuditionNativeSafe, AuditionFFmpegLab, AuditionAudioLab):
    """Modular controller for Adobe Audition 2026.

    Layers:
      1) ExtendScript DOM for WaveDocument / Multitrack basics.
      2) Win32 UI command helpers for features not exposed by ExtendScript.
      3) Offline .sesx XML editing for deep multitrack parameters.
    """

    def __init__(self, audition_exe: Path = AUDITION_EXE):
        self.audition_exe = Path(audition_exe)
        if not self.audition_exe.exists():
            raise FileNotFoundError(self.audition_exe)
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    def _run_jsx(self, body: str, name: str = "task", timeout: float = 60.0) -> dict[str, str]:
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= 600:
            raise ValueError("Timeout must be finite and in (0, 600] seconds")
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        with audition_host_lock(ROOT / '_runtime' / 'locks', timeout):
            return self._run_jsx_unlocked(body, name, timeout)

    def _run_jsx_unlocked(self, body: str, name: str = "task", timeout: float = 60.0) -> dict[str, str]:
        """Run a bounded Audition ExtendScript request without sharing temporary names.

        A completed JSX reply may contain ERROR; that is a failed task, not success.
        Timeout does not terminate the Audition host or any user document.
        """
        if not isinstance(body, str) or not body.strip():
            raise ValueError("Non-empty JSX body required")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,48}", name):
            raise ValueError("Invalid task label")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= 600:
            raise ValueError("Timeout must be finite and in (0, 600] seconds")
        # -r is an IPC request to a running desktop host. Using it as an implicit
        # startup path can collide with startup/recovery and spawn error dialogs.
        try:
            self._audition_pid()
        except RuntimeError as exc:
            raise ConnectionError("Audition is not running. Start it once and finish startup before sending controller requests.") from exc
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        task_id = f"{name}_{time.time_ns()}_{uuid.uuid4().hex[:10]}"
        jsx_path = RUNTIME_DIR / f"{task_id}.jsx"
        result_path = RUNTIME_DIR / f"{task_id}.txt"
        rp = result_path.as_posix()
        wrapped = f'''#target audition
(function(){{
 var __f=new File("{rp}");
 __f.encoding="UTF8";
 if(!__f.open("w")) throw "Cannot open task reply";
 function out(k,v){{__f.writeln(k+"="+String(v));}}
 try{{
{body}
 }}catch(e){{out("ERROR",e);}}
 out("__DONE__","1");
 __f.close();
}})();
'''
        deadline = time.monotonic() + timeout
        try:
            jsx_path.write_text(wrapped, encoding="utf-8-sig")
            subprocess.Popen(
                [str(self.audition_exe), "-r", str(jsx_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            raw = ""
            while time.monotonic() < deadline:
                if result_path.exists():
                    try:
                        raw = result_path.read_text(encoding="utf-8-sig", errors="replace")
                    except OSError:
                        raw = ""
                    if any(line == "__DONE__=1" for line in raw.splitlines()):
                        break
                time.sleep(min(0.10, max(0.001, deadline - time.monotonic())))
            else:
                raise TimeoutError(f"Audition task timed out: {name}")
            result: dict[str, str] = {}
            for line in raw.splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    result[k] = v
            if result.get("__DONE__") != "1":
                raise RuntimeError(f"Audition reply incomplete: {name}")
            if "ERROR" in result:
                raise RuntimeError(f"Audition ExtendScript failed [{name}]: {result['ERROR']}")
            return result
        finally:
            # Clean only artifacts belonging to this task. Never kill Audition on timeout.
            for temporary in (jsx_path, result_path):
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass


    def status(self) -> dict[str, str]:
        return self._run_jsx(r'''
 out("APP",app.name);
 out("VERSION",app.version);
 out("DOCUMENTS",app.documents.length);
 var active=null;
 if(app.documents.length>0){try{active=app.activeDocument;var valid=active.reflect.name;}catch(e){active=null;}}
 out("ACTIVE_CLASS",active?active.reflect.name:"");
 out("ACTIVE_NAME",active?active.displayName:"");
 out("ACTIVE_PATH",active?active.path:"");
''', "status")

    def open_document(self, path: str) -> dict[str, str]:
        p = Path(path).resolve().as_posix()
        return self._run_jsx(f'''
 var d=app.openDocument(new DocumentOpenParameter({json.dumps(p)}));
 out("OPEN",d);
 out("CLASS",app.activeDocument?app.activeDocument.reflect.name:"");
 out("NAME",app.activeDocument?app.activeDocument.displayName:"");
 out("PATH",app.activeDocument?app.activeDocument.path:"");
''', "open_document")

    def add_marker(self, start_samples: int, duration_samples: int = 0,
                   name: str = "", marker_type: str = "Cue",
                   description: str = "") -> dict[str, str]:
        return self._run_jsx(f'''
 var d=app.activeDocument;
 if(!d || d.reflect.name!="WaveDocument") throw "Active document is not WaveDocument";
 out("RESULT",d.addMarker({int(start_samples)},{int(duration_samples)},
   {json.dumps(name)},{json.dumps(marker_type)},{json.dumps(description)}));
 out("MARKERS",d.markers.length);
''', "add_marker")

    def set_playhead(self, samples: int) -> dict[str, str]:
        return self._run_jsx(f'''
 var d=app.activeDocument;
 if(!d) throw "No active document";
 d.playheadPosition={int(samples)};
 out("PLAYHEAD",d.playheadPosition);
''', "set_playhead")

    def transport(self, action: str) -> dict[str, str]:
        if action not in {"play", "pause", "stop"}:
            raise ValueError("action must be play, pause, or stop")
        return self._run_jsx(f'''
 app.transport.{action}();
 out("IS_PLAYING",app.transport.isPlaying);
 out("IS_PAUSED",app.transport.isPaused);
''', f"transport_{action}")

    def apply_favorite(self, name: str, output_path: str | None = None,
                       timeout: float = 30.0) -> dict[str, str]:
        save_code = ""
        if output_path:
            op = Path(output_path).resolve().as_posix()
            save_code = f'''
 out("SAVE",d.saveAs({json.dumps(op)},true));
 var sw=0; while(!new File({json.dumps(op)}).exists && sw<200){{$.sleep(50);sw++;}}
 out("EXISTS",new File({json.dumps(op)}).exists);
'''
        return self._run_jsx(f'''
 var d=app.activeDocument;
 if(!d || d.reflect.name!="WaveDocument") throw "Active document is not WaveDocument";
 out("FAVORITE",d.applyFavorite({json.dumps(name)}));
 var n=0; while(d.isBusy && n<1000){{$.sleep(40);n++;}}
 out("WAIT_MS",n*40);
 out("BUSY",d.isBusy);
{save_code}
''', "favorite", timeout=max(timeout, 60.0))

    def save_as(self, path: str) -> dict[str, str]:
        p = Path(path).resolve().as_posix()
        return self._run_jsx(f'''
 var d=app.activeDocument;
 if(!d || d.reflect.name!="WaveDocument") throw "Active document is not WaveDocument";
 out("SAVE",d.saveAs({json.dumps(p)},true));
 $.sleep(500);
 out("EXISTS",new File({json.dumps(p)}).exists);
''', "save_as")


    def save_wave_converted(self, path: str, sample_rate: int | None = None,
                            bit_depth: int | None = None,
                            dither: bool = True,
                            resample_quality: int = 100) -> dict[str, str]:
        p = Path(path).resolve().as_posix()
        sr = -1 if sample_rate is None else int(sample_rate)
        bd = -1 if bit_depth is None else int(bit_depth)
        return self._run_jsx(f'''
 var d=app.activeDocument;
 if(!d || d.reflect.name!="WaveDocument") throw "Active document is not WaveDocument";
 var sp=new WaveDocumentSaveAsParameters();
 var cv=new SampleTypeConvertParameters();
 cv.sampleRate={sr};
 cv.bitDepth={bd};
 cv.useDithering={"true" if dither else "false"};
 cv.resampleQuality={int(resample_quality)};
 sp.sampleTypeConversion=cv;
 var r=d.saveAsDocument({json.dumps(p)},sp);
 out("RESULT",r);
 if(r){{
   for(var k in r){{try{{out("R_"+k,r[k]);}}catch(e){{}}}}
 }}
 $.sleep(500);
 out("EXISTS",new File({json.dumps(p)}).exists);
''', "save_wave_converted")

    def batch_favorite(self, paths: list[str], favorite: str, output_dir: str,
                       suffix: str = "_processed") -> dict[str, str]:
        ins = [Path(p).resolve().as_posix() for p in paths]
        outdir = Path(output_dir).resolve().as_posix()
        arr = json.dumps(ins, ensure_ascii=False)
        return self._run_jsx(f'''
 var files={arr};
 var outDir=new Folder({json.dumps(outdir)}); if(!outDir.exists) outDir.create();
 var ok=0;
 for(var i=0;i<files.length;i++){{
   try{{
     app.openDocument(new DocumentOpenParameter(files[i]));
     var d=app.activeDocument;
     if(!d.applyFavorite({json.dumps(favorite)})) throw "Favorite failed";
     var n=0; while(d.isBusy && n<1000){{$.sleep(40);n++;}}
     var src=new File(files[i]);
     var base=src.name.replace(/\\.[^.]+$/,"");
     var outPath=outDir.fsName+"/"+base+{json.dumps(suffix)}+".wav";
     d.saveAs(outPath,true);
     var sw=0; while(!new File(outPath).exists && sw<200){{$.sleep(50);sw++;}}
     $.sleep(300);
     d.closeDocument(); $.sleep(250);
     ok++;
   }}catch(e){{out("ITEM_ERROR_"+i,e);}}
 }}
 out("PROCESSED",ok);
 out("TOTAL",files.length);
''', "batch_favorite", timeout=max(90.0, len(paths) * 20.0))

    @staticmethod
    def wav_stats(path: str) -> dict[str, float | int | str]:
        import numpy as np
        from scipy.io import wavfile

        rate, data = wavfile.read(str(Path(path)))
        x = np.asarray(data)
        channels = 1 if x.ndim == 1 else x.shape[1]
        frames = x.shape[0]

        if np.issubdtype(x.dtype, np.floating):
            xf = x.astype(np.float64)
            peak = float(np.max(np.abs(xf))) if xf.size else 0.0
            rms = float(np.sqrt(np.mean(xf * xf))) if xf.size else 0.0
            peak_dbfs = 20 * math.log10(max(peak, 1e-12))
            rms_dbfs = 20 * math.log10(max(rms, 1e-12))
            sample_format = str(x.dtype)
        elif np.issubdtype(x.dtype, np.integer):
            info = np.iinfo(x.dtype)
            scale = float(max(abs(info.min), info.max))
            xf = x.astype(np.float64) / scale
            peak = float(np.max(np.abs(xf))) if xf.size else 0.0
            rms = float(np.sqrt(np.mean(xf * xf))) if xf.size else 0.0
            peak_dbfs = 20 * math.log10(max(peak, 1e-12))
            rms_dbfs = 20 * math.log10(max(rms, 1e-12))
            sample_format = str(x.dtype)
        else:
            raise TypeError(f"Unsupported WAV dtype: {x.dtype}")

        return {
            "sample_rate": int(rate),
            "channels": int(channels),
            "frames": int(frames),
            "sample_format": sample_format,
            "peak_dbfs": peak_dbfs,
            "rms_dbfs": rms_dbfs,
        }


    @staticmethod
    def _audio_to_float(data):
        import numpy as np
        x = np.asarray(data)
        if np.issubdtype(x.dtype, np.floating):
            return x.astype(np.float64)
        if np.issubdtype(x.dtype, np.integer):
            info = np.iinfo(x.dtype)
            scale = float(max(abs(info.min), info.max))
            return x.astype(np.float64) / scale
        raise TypeError(f"Unsupported audio dtype: {x.dtype}")

    @staticmethod
    def _k_weight(data, sample_rate: int):
        import numpy as np
        from scipy.signal import lfilter

        x = np.asarray(data, dtype=np.float64)
        if x.ndim == 1:
            x = x[:, None]

        def high_shelf(fc, q, gain_db):
            A = 10 ** (gain_db / 40.0)
            w0 = 2 * math.pi * fc / sample_rate
            cw, sw = math.cos(w0), math.sin(w0)
            alpha = sw / (2 * q)
            sqA = math.sqrt(A)
            b0 = A * ((A + 1) + (A - 1) * cw + 2 * sqA * alpha)
            b1 = -2 * A * ((A - 1) + (A + 1) * cw)
            b2 = A * ((A + 1) + (A - 1) * cw - 2 * sqA * alpha)
            a0 = (A + 1) - (A - 1) * cw + 2 * sqA * alpha
            a1 = 2 * ((A - 1) - (A + 1) * cw)
            a2 = (A + 1) - (A - 1) * cw - 2 * sqA * alpha
            return [b0/a0, b1/a0, b2/a0], [1.0, a1/a0, a2/a0]

        def high_pass(fc, q):
            w0 = 2 * math.pi * fc / sample_rate
            cw, sw = math.cos(w0), math.sin(w0)
            alpha = sw / (2 * q)
            b0 = (1 + cw) / 2
            b1 = -(1 + cw)
            b2 = (1 + cw) / 2
            a0 = 1 + alpha
            a1 = -2 * cw
            a2 = 1 - alpha
            return [b0/a0, b1/a0, b2/a0], [1.0, a1/a0, a2/a0]

        b1, a1 = high_shelf(1681.974450955533, 1 / math.sqrt(2), 4.0)
        b2, a2 = high_pass(38.13547087602444, 0.5003270373238773)
        y = lfilter(b1, a1, x, axis=0)
        y = lfilter(b2, a2, y, axis=0)
        return y

    @classmethod
    def measure_lufs(cls, path: str) -> dict[str, float | int]:
        import numpy as np
        from scipy.io import wavfile
        from scipy.signal import resample_poly

        rate, data = wavfile.read(str(Path(path)))
        x = cls._audio_to_float(data)
        if x.ndim == 1:
            x = x[:, None]
        y = cls._k_weight(x, int(rate))

        block = max(1, int(round(0.400 * rate)))
        hop = max(1, int(round(0.100 * rate)))
        energies = []
        loudness = []
        for start in range(0, max(1, len(y) - block + 1), hop):
            seg = y[start:start + block]
            if len(seg) < block:
                break
            e = float(np.sum(np.mean(seg * seg, axis=0)))
            energies.append(e)
            loudness.append(-0.691 + 10 * math.log10(max(e, 1e-20)))

        if not energies:
            e = float(np.sum(np.mean(y * y, axis=0)))
            integrated = -0.691 + 10 * math.log10(max(e, 1e-20))
        else:
            E = np.asarray(energies)
            L = np.asarray(loudness)
            abs_mask = L > -70.0
            if not np.any(abs_mask):
                integrated = -70.0
            else:
                prelim_e = float(np.mean(E[abs_mask]))
                prelim_l = -0.691 + 10 * math.log10(max(prelim_e, 1e-20))
                rel_gate = prelim_l - 10.0
                mask = abs_mask & (L > rel_gate)
                final_e = float(np.mean(E[mask])) if np.any(mask) else prelim_e
                integrated = -0.691 + 10 * math.log10(max(final_e, 1e-20))

        up = resample_poly(x, 4, 1, axis=0)
        tp = float(np.max(np.abs(up))) if up.size else 0.0
        true_peak = 20 * math.log10(max(tp, 1e-12))
        return {
            "sample_rate": int(rate),
            "channels": int(x.shape[1]),
            "integrated_lufs": integrated,
            "true_peak_dbtp": true_peak,
        }

    @classmethod
    def normalize_lufs_fallback(cls, input_path: str, output_path: str,
                                target_lufs: float = -16.0,
                                true_peak_limit: float = -1.0) -> dict[str, float | str]:
        import numpy as np
        from scipy.io import wavfile
        from scipy.signal import resample_poly

        rate, data = wavfile.read(str(Path(input_path)))
        x = cls._audio_to_float(data)
        measured = cls.measure_lufs(input_path)
        gain_db = float(target_lufs) - float(measured["integrated_lufs"])
        gain = 10 ** (gain_db / 20.0)
        y = x * gain

        up = resample_poly(y, 4, 1, axis=0)
        peak = float(np.max(np.abs(up))) if up.size else 0.0
        peak_db = 20 * math.log10(max(peak, 1e-12))
        if peak_db > true_peak_limit:
            reduction_db = float(true_peak_limit) - peak_db
            y *= 10 ** (reduction_db / 20.0)
            gain_db += reduction_db

        wavfile.write(str(Path(output_path)), int(rate), y.astype(np.float32))
        final = cls.measure_lufs(output_path)
        return {
            "output": str(Path(output_path)),
            "gain_db": gain_db,
            "integrated_lufs": float(final["integrated_lufs"]),
            "true_peak_dbtp": float(final["true_peak_dbtp"]),
        }

    # ---------- Multitrack DOM ----------
    def multitrack_track_edit(self, track_index: int = 0, *,
                              name: str | None = None,
                              mute: bool | None = None,
                              solo: bool | None = None,
                              armed: bool | None = None,
                              visible: bool | None = None,
                              clip_index: int | None = None,
                              clip_start_samples: int | None = None,
                              session_path: str | None = None, save: bool = False) -> dict[str, str]:
        if type(save) is not bool:
            raise ValueError("save must be Boolean")
        selector = json.dumps(Path(session_path).resolve().as_posix()) if session_path else 'null'
        ops = []
        if name is not None: ops.append(f'tr.name={json.dumps(name)};')
        if mute is not None: ops.append(f'tr.mute={"true" if mute else "false"};')
        if solo is not None: ops.append(f'tr.solo={"true" if solo else "false"};')
        if armed is not None: ops.append(f'tr.armed={"true" if armed else "false"};')
        if visible is not None: ops.append(f'tr.visible={"true" if visible else "false"};')
        if clip_index is not None and clip_start_samples is not None:
            ops.append(f'tr.audioClips[{int(clip_index)}].startTime={int(clip_start_samples)};')
        code = "\n ".join(ops)
        return self._run_jsx(f'''
 var mt=null, matches=0, requested={selector};
 for(var i=0;i<app.documents.length;i++){{
 var candidate=app.documents[i];
 if(candidate.reflect.name=="MultitrackDocument" &&
 (!requested || new File(String(candidate.path)).fsName.toLowerCase()==new File(requested).fsName.toLowerCase())){{mt=candidate;matches++;}}
 }}
 if(matches>1)throw "Ambiguous session; supply session_path";
 if(!mt) throw "No MultitrackDocument";
 mt.activate();
 var tr=mt.audioTracks[{int(track_index)}];
 {code}
 out("TRACK_NAME",tr.name);
 out("MUTE",tr.mute); out("SOLO",tr.solo); out("ARMED",tr.armed); out("VISIBLE",tr.visible);
 out("DIRTY",mt.dirty);
 out("SAVE",{ "mt.saveDocument()" if save else "false" });
''', "multitrack_track_edit")

    def _audition_pid(self) -> int:
        p = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Adobe Audition.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, errors="replace"
        )
        m = re.search(r'"Adobe Audition.exe","(\d+)"', p.stdout)
        if not m:
            raise RuntimeError("Audition is not running")
        return int(m.group(1))

    def _main_window(self) -> int:
        pid0 = self._audition_pid()
        u = ctypes.windll.user32
        found: list[int] = []
        @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
        def cb(hwnd, lparam):
            pid = wt.DWORD()
            u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == pid0 and u.IsWindowVisible(hwnd):
                cls = ctypes.create_unicode_buffer(256)
                u.GetClassNameW(hwnd, cls, 256)
                n = u.GetWindowTextLengthW(hwnd)
                b = ctypes.create_unicode_buffer(n + 1)
                u.GetWindowTextW(hwnd, b, n + 1)
                if cls.value.startswith("audition") and b.value:
                    found.append(int(hwnd))
            return True
        u.EnumWindows(cb, 0)
        if not found:
            raise RuntimeError("Audition main window not found")
        return found[0]

    def send_menu_command(self, command_id: int) -> None:
        hwnd = self._main_window()
        ctypes.windll.user32.SendMessageW(hwnd, 0x0111, int(command_id), 0)


    def create_multitrack_from_current(self, session_name: str,
                                       timeout: float = 10.0) -> None:
        self._run_jsx(r'''
 out("ENABLED",app.isCommandEnabled("Edit.InsertIntoNewSession"));
 out("INVOKE",app.invokeCommand("Edit.InsertIntoNewSession"));
''', "new_multitrack")
        pid0 = self._audition_pid()
        u = ctypes.windll.user32
        deadline = time.time() + timeout
        dialog = None
        while time.time() < deadline and dialog is None:
            candidates: list[int] = []
            @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
            def top(hwnd, lparam):
                pid = wt.DWORD()
                u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value == pid0 and u.IsWindowVisible(hwnd):
                    n = u.GetWindowTextLengthW(hwnd)
                    b = ctypes.create_unicode_buffer(n + 1)
                    u.GetWindowTextW(hwnd, b, n + 1)
                    if b.value == "New Multitrack Session":
                        candidates.append(int(hwnd))
                return True
            u.EnumWindows(top, 0)
            if candidates:
                dialog = candidates[0]
                break
            time.sleep(0.1)
        if dialog is None:
            raise TimeoutError("New Multitrack Session dialog not found")

        edits: list[int] = []
        @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
        def child(hwnd, lparam):
            cls = ctypes.create_unicode_buffer(256)
            u.GetClassNameW(hwnd, cls, 256)
            if cls.value == "Edit":
                edits.append(int(hwnd))
            return True
        u.EnumChildWindows(dialog, child, 0)
        if not edits:
            raise RuntimeError("Session name edit control not found")
        u.SendMessageW(edits[0], 0x000C, 0, session_name)
        u.SetForegroundWindow(dialog)
        u.PostMessageW(dialog, 0x0100, 0x0D, 0)
        u.PostMessageW(dialog, 0x0101, 0x0D, 0)

    def mixdown_to_wave(self, output_path: str, wait_seconds: float = 1.2) -> dict[str, str]:
        self._run_jsx(r'''
 var mt=null;
 for(var i=0;i<app.documents.length;i++) if(app.documents[i].reflect.name=="MultitrackDocument"){mt=app.documents[i];break;}
 if(!mt) throw "No MultitrackDocument";
 mt.activate(); out("ACTIVE",mt.displayName);
''', "activate_multitrack")
        self.send_menu_command(CMD_MIXDOWN_NEW_FILE_ENTIRE)
        time.sleep(wait_seconds)
        p = Path(output_path).resolve().as_posix()
        return self._run_jsx(f'''
 var m=null;
 for(var i=0;i<app.documents.length;i++){{
   var d=app.documents[i];
   if(d.reflect.name=="WaveDocument" && String(d.displayName).indexOf("Mixdown")>=0) m=d;
 }}
 if(!m) throw "Mixdown WaveDocument not found";
 m.activate();
 out("NAME",m.displayName); out("DURATION",m.duration);
 out("SAVE",m.saveAs({json.dumps(p)},true));
 $.sleep(500);
 out("EXISTS",new File({json.dumps(p)}).exists);
''', "save_mixdown")


    # ---------- UI-assisted features ----------
    def open_match_loudness_panel(self) -> None:
        self.send_menu_command(CMD_MATCH_LOUDNESS)

    def toggle_spectral_display(self) -> None:
        self.send_menu_command(CMD_TOGGLE_SPECTRAL)

    def select_spot_healing_brush(self) -> None:
        self.send_menu_command(CMD_SPOT_HEALING_BRUSH)

    # ---------- Offline .sesx editing ----------
    @staticmethod
    def edit_sesx(session_path: str, *, output_path: str | None = None,
                  track_index: int = 0,
                  track_volume: float | None = None,
                  pan: float | None = None,
                  clip_index: int = 0,
                  clip_gain: float | None = None,
                  fade_in_samples: int | None = None,
                  fade_out_start_samples: int | None = None,
                  eq_band3_gain: float | None = None,
                  enable_eq: bool | None = None) -> str:
        src = Path(session_path)
        dst = Path(output_path) if output_path else src
        tree = ET.parse(src)
        root = tree.getroot()
        tracks = root.findall(".//audioTrack")
        tr = tracks[track_index]

        for comp in tr.findall("./trackAudioParameters/component"):
            cid = comp.get("id")
            if cid == "trackFader" and track_volume is not None:
                for p in comp.findall("parameter"):
                    if p.get("name") == "volume":
                        p.set("parameterValue", str(float(track_volume)))
            elif cid == "trackPan" and pan is not None:
                for p in comp.findall("parameter"):
                    if p.get("name") == "Pan":
                        p.set("parameterValue", str(float(pan)))
            elif cid == "trackEQ":
                if enable_eq is not None:
                    comp.set("powered", "true" if enable_eq else "false")
                if eq_band3_gain is not None:
                    for p in comp.findall("parameter"):
                        if p.get("name") == "EQ Band 3 Gain":
                            p.set("parameterValue", str(float(eq_band3_gain)))

        clips = tr.findall("audioClip")
        if clips:
            cl = clips[clip_index]
            if clip_gain is not None:
                for comp in cl.findall("component"):
                    if comp.get("id") == "clipGain":
                        for p in comp.findall("parameter"):
                            if p.get("name") == "volume":
                                p.set("parameterValue", str(float(clip_gain)))
            if fade_in_samples is not None:
                fi = cl.find("fadeIn")
                if fi is not None:
                    fi.set("startPoint", "0")
                    fi.set("endPoint", str(int(fade_in_samples)))
            if fade_out_start_samples is not None:
                fo = cl.find("fadeOut")
                if fo is not None:
                    fo.set("startPoint", str(int(fade_out_start_samples)))

        tree.write(dst, encoding="UTF-8", xml_declaration=True)
        return str(dst)


def main() -> None:
    p = argparse.ArgumentParser(description="Adobe Audition 2026 modular controller")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    o = sub.add_parser("open"); o.add_argument("path")
    f = sub.add_parser("favorite"); f.add_argument("name"); f.add_argument("--output")
    s = sub.add_parser("stats"); s.add_argument("path")
    m = sub.add_parser("mixdown"); m.add_argument("output")
    l = sub.add_parser("lufs"); l.add_argument("path")
    nl = sub.add_parser("normalize-lufs"); nl.add_argument("input"); nl.add_argument("output")
    nl.add_argument("--target", type=float, default=-16.0)
    nl.add_argument("--true-peak", type=float, default=-1.0)
    pr = sub.add_parser("production", help="Validate or run a JSON production recipe")
    pr.add_argument("config", help="JSON file containing inputs and steps")
    pr.add_argument("output_directory")
    pr.add_argument("--confirm", action="store_true", help="Actually publish new outputs")
    ar = sub.add_parser("arrange-session", help="Clone QA clips into empty native SESX tracks")
    ar.add_argument("source"); ar.add_argument("output"); ar.add_argument("placements_json")
    ar.add_argument("--confirm", action="store_true")
    au = sub.add_parser("audit-session", help="Read-only structural preflight of native SESX")
    au.add_argument("source"); au.add_argument("--output")
    au.add_argument("--confirm", action="store_true", help="Create new JSON report when output given")
    er = sub.add_parser("effects", help="Render a typed JSON list of audio effects")
    er.add_argument("source"); er.add_argument("output"); er.add_argument("recipe_json")
    er.add_argument("--confirm", action="store_true")
    for command in ("edit-production-session", "relink-session", "automation-audio", "repair-review", "import-wavs", "native-edit"):
        parser = sub.add_parser(command)
        parser.add_argument("source"); parser.add_argument("output"); parser.add_argument("config")
        parser.add_argument("--confirm", action="store_true")
    parser = sub.add_parser("overlaps"); parser.add_argument("source")
    parser = sub.add_parser("production-mixdown")
    parser.add_argument("source"); parser.add_argument("output")
    parser.add_argument("--confirm", action="store_true")
    parser = sub.add_parser("sdk-session")
    parser.add_argument("config"); parser.add_argument("output"); parser.add_argument("--confirm", action="store_true")
    parser = sub.add_parser("resume-production")
    parser.add_argument("config"); parser.add_argument("output"); parser.add_argument("checkpoint"); parser.add_argument("--confirm", action="store_true")
    parser = sub.add_parser("media-search")
    parser.add_argument("source"); parser.add_argument("roots", nargs="+")
    parser = sub.add_parser("native-favorite")
    parser.add_argument("source"); parser.add_argument("output"); parser.add_argument("favorite"); parser.add_argument("--confirm", action="store_true")
    parser = sub.add_parser("rack-export")
    parser.add_argument("source"); parser.add_argument("output"); parser.add_argument("--track-id", required=True); parser.add_argument("--confirm", action="store_true")
    parser = sub.add_parser("record-qa", help="Actual bounded recording on the configured input; needs explicit consent")
    parser.add_argument("output"); parser.add_argument("--seconds", type=float, default=1.0); parser.add_argument("--confirm", action="store_true")
    sub.add_parser("control-devices", help="List MIDI and ASIO devices")
    mux=sub.add_parser("mux-video", help="Offline video/audio delivery")
    mux.add_argument("video"); mux.add_argument("audio"); mux.add_argument("output")
    mux.add_argument("--offset", type=float, default=0.0); mux.add_argument("--confirm", action="store_true")
    inspector=sub.add_parser("uia-inspect", help="Read-only Audition UI Automation snapshot")
    inspector.add_argument("--title", default=""); inspector.add_argument("--max-controls", type=int, default=200)
    inspector.add_argument("--max-depth", type=int, default=5); inspector.add_argument("--timeout", type=float, default=15)
    sub.add_parser("document-snapshot", help="Read-only live document and clip timing snapshot")
    parser=sub.add_parser("omf-inspect", help="Hash existing OMF and check live host visibility")
    parser.add_argument("path")
    parser=sub.add_parser("cep-receipt", help="Read saved CEP health evidence; no GUI actions")
    parser.add_argument("path")
    parser=sub.add_parser("premiere-reference", help="Inspect saved PR project media reference offline")
    parser.add_argument("path");parser.add_argument("media_name")
    args = p.parse_args()

    ctl = AuditionController()
    if args.cmd == "document-snapshot":
        result = ctl.native_document_snapshot()
    elif args.cmd == "omf-inspect":
        result = ctl.inspect_native_omf(args.path)
    elif args.cmd == "cep-receipt":
        result = ctl.inspect_cep_receipt(args.path)
    elif args.cmd == "premiere-reference":
        result = ctl.inspect_premiere_project_reference(args.path, args.media_name)
    elif args.cmd == "uia-inspect":
        result = ctl.inspect_audition_controls(title_contains=args.title, max_controls=args.max_controls, max_depth=args.max_depth, timeout=args.timeout)
    elif args.cmd == "mux-video":
        result = ctl.mux_video_audio(args.video, args.audio, args.output, offset_seconds=args.offset, confirm=args.confirm)
    elif args.cmd == "control-devices":
        result = ctl.control_surface_devices()
    elif args.cmd == "record-qa":
        result = ctl.native_record_input_qa(args.output, seconds=args.seconds, confirm=args.confirm)
    elif args.cmd == "native-edit":
        config = json.loads(Path(args.config).read_text(encoding="utf8"))
        operations = {"envelope": ctl.patch_native_track_envelope, "send": ctl.patch_native_send,
                      "pan": ctl.patch_native_pan_position, "rack": ctl.edit_native_rack,
                      "rack-preset": ctl.apply_native_rack_preset}
        if not isinstance(config, dict) or set(config) != {"kind", "params"} or config["kind"] not in operations or not isinstance(config["params"], dict):
            raise ValueError("Native edit needs known kind and parameter object")
        if set(config["params"]) & {"source", "destination", "confirm"}:
            raise ValueError("Paths and confirmation must come from command arguments")
        result = operations[config["kind"]](args.source, args.output, **config["params"], confirm=args.confirm)
    elif args.cmd in ("edit-production-session", "relink-session", "automation-audio", "repair-review", "import-wavs"):
        config = json.loads(Path(args.config).read_text(encoding="utf8"))
        operation = {"edit-production-session": ctl.edit_production_session,
                     "relink-session": ctl.relink_production_session,
                     "automation-audio": ctl.render_gain_pan_envelope,
                     "repair-review": ctl.repair_review_bundle,
                     "import-wavs": ctl.import_production_wavs}[args.cmd]
        result = operation(args.source, args.output, config, confirm=args.confirm)
    elif args.cmd == "sdk-session":
        result = ctl.create_native_sdk_session(json.loads(Path(args.config).read_text(encoding="utf8")), args.output, confirm=args.confirm)
    elif args.cmd == "resume-production":
        result = ctl.run_resumable_production(json.loads(Path(args.config).read_text(encoding="utf8")), args.output, args.checkpoint, confirm=args.confirm)
    elif args.cmd == "media-search":
        result = ctl.search_session_media(args.source, args.roots)
    elif args.cmd == "native-favorite":
        result = ctl.native_apply_favorite_copy(args.source, args.output, favorite=args.favorite, confirm=args.confirm)
    elif args.cmd == "rack-export":
        result = ctl.export_native_rack_preset(args.source, args.output, track_id=args.track_id, confirm=args.confirm)
    elif args.cmd == "overlaps":
        result = ctl.session_overlap_report(args.source)
    elif args.cmd == "production-mixdown":
        result = ctl.mixdown_production_session(args.source, args.output, confirm=args.confirm)
    elif args.cmd == "status":
        result = ctl.status()
    elif args.cmd == "open":
        result = ctl.open_document(args.path)
    elif args.cmd == "favorite":
        result = ctl.apply_favorite(args.name, args.output)
    elif args.cmd == "stats":
        result = ctl.wav_stats(args.path)
    elif args.cmd == "mixdown":
        result = ctl.mixdown_to_wave(args.output)
    elif args.cmd == "lufs":
        result = ctl.measure_lufs(args.path)
    elif args.cmd == "normalize-lufs":
        result = ctl.normalize_lufs_fallback(
            args.input, args.output, args.target, args.true_peak
        )
    elif args.cmd == "production":
        spec = json.loads(Path(args.config).read_text(encoding="utf-8"))
        result = ctl.run_production_jobs(spec, args.output_directory, confirm=args.confirm)
    elif args.cmd == "arrange-session":
        placements = json.loads(Path(args.placements_json).read_text(encoding="utf-8"))
        result = ctl.arrange_native_qa_clips(args.source, args.output, placements,
                                             confirm=args.confirm)
    elif args.cmd == "audit-session":
        result = (ctl.write_native_session_audit(args.source, args.output, confirm=args.confirm)
                  if args.output else ctl.audit_native_session(args.source))
    elif args.cmd == "effects":
        recipe = json.loads(Path(args.recipe_json).read_text(encoding="utf-8"))
        result = ctl.render_audio_effects(args.source, args.output, recipe,
                                          confirm=args.confirm)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
