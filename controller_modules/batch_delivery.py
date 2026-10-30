"""Isolated, non-overwriting batch transcoding with readback and per-item receipts.

Only invokes Debian WSL FFmpeg. It is not Audition's native Batch Process.
"""
from __future__ import annotations
import hashlib
import os
import re
import shutil
import tempfile
from pathlib import Path

from controller_modules.ffmpeg_audio import AuditionFFmpegLab


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class AuditionBatchDelivery:
    @classmethod
    def batch_transcode_audio(
        cls, sources: list[str | Path], output_dir: str | Path, *,
        fmt: str = "flac", suffix: str = "_deliver",
        rate: int = 48000, channels: int = 2, bitrate_kbps: int = 192,
        stop_on_error: bool = False, confirm: bool = False,
    ) -> dict:
        """Convert up to 100 inputs, never overwrite, report failures separately.

        An item is published using O_EXCL; temporary files remain scoped to the
        output directory and are deleted even on converter exceptions.
        """
        if not isinstance(sources, list) or not 1 <= len(sources) <= 100:
            raise ValueError("Batch requires 1..100 paths")
        if not isinstance(fmt, str) or fmt.lower() not in AuditionFFmpegLab.FORMATS:
            raise ValueError("Unsupported delivery format")
        fmt = fmt.lower()
        if not isinstance(suffix, str) or not re.fullmatch(r"_[A-Za-z0-9_-]{1,28}", suffix):
            raise ValueError("Suffix must be safe and start with underscore")
        if type(stop_on_error) is not bool or type(confirm) is not bool:
            raise ValueError("Expected boolean flags")
        outdir = Path(output_dir).resolve()
        if not outdir.is_dir():
            raise ValueError("Output directory must already exist")
        srcs = [Path(p).resolve() for p in sources]
        targets = [outdir / (p.stem + suffix + "." + fmt) for p in srcs]
        casefold = [str(p).casefold() for p in srcs]
        targets_fold = [str(p).casefold() for p in targets]
        if len(set(casefold)) != len(srcs) or len(set(targets_fold)) != len(targets_fold):
            raise ValueError("Duplicate sources or target filenames")
        if any(str(dst).casefold() in casefold for dst in targets):
            raise ValueError("Input/output path collision")
        if any(p.exists() for p in targets):
            raise FileExistsError("At least one delivery file already exists")
        # Validate parameters even for a dry run; use FFmpeg's existing typed guard.
        if type(rate) is not int or rate not in (16000, 22050, 32000, 44100, 48000, 96000):
            raise ValueError("Unsupported sample rate")
        if type(channels) is not int or channels not in (1, 2):
            raise ValueError("Mono or stereo required")
        if type(bitrate_kbps) is not int or bitrate_kbps not in (64, 96, 128, 160, 192, 256, 320):
            raise ValueError("Unsupported bitrate")
        rows = [{"source": str(src), "destination": str(dst), "source_exists": src.is_file()}
                for src, dst in zip(srcs, targets)]
        if not confirm:
            return {"dry_run": True, "jobs": rows, "format": fmt,
                    "backend": "WSL Debian FFmpeg", "native_audition_export": False}
        success = failed = skipped = 0
        for src, dst, row in zip(srcs, targets, rows):
            row["status"] = "failed"
            owns_destination = False
            try:
                if not src.is_file():
                    raise FileNotFoundError(str(src))
                original_sha = _sha256(src)
                with tempfile.TemporaryDirectory(prefix=".audition_batch_", dir=outdir) as td:
                    staged = Path(td) / dst.name
                    conversion = AuditionFFmpegLab.transcode_audio(
                        src, staged, rate=rate, channels=channels,
                        bitrate_kbps=bitrate_kbps, confirm=True)
                    staged_sha = _sha256(staged)
                    # 'xb' is exclusive on Windows: parallel jobs cannot overwrite.
                    with dst.open("xb") as target:
                        owns_destination = True
                        with staged.open("rb") as item:
                            shutil.copyfileobj(item, target, length=1 << 20)
                        target.flush()
                        os.fsync(target.fileno())
                    if _sha256(dst) != staged_sha:
                        raise IOError("Published file differs from validated stage")
                if _sha256(src) != original_sha:
                    raise IOError("Input changed during transcoding")
                row.update({"status": "passed", "sha256": staged_sha,
                            "source_sha256": original_sha, "bytes": dst.stat().st_size,
                            "codec": conversion["codec"],
                            "sample_rate": conversion["sample_rate"],
                            "channels": conversion["channels"]})
                success += 1
            except Exception as exc:
                if owns_destination:
                    dst.unlink(missing_ok=True)
                row.update({"status": "failed", "error": type(exc).__name__ + ": " + str(exc)})
                failed += 1
                if stop_on_error:
                    for other in rows[success + failed:]:
                        other["status"] = "skipped"
                        skipped += 1
                    break
        return {"total": len(srcs), "passed": success, "failed": failed,
                "skipped": skipped, "jobs": rows,
                "backend": "WSL Debian FFmpeg", "native_audition_export": False}
