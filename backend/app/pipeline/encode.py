"""
encode.py — all-intra encoding and its checks (vachan-plan.md §39.12, §64.8).

A browser can only *play* video forwards, but it can *seek* both ways. In a
normal H.264 stream a seek decodes from the previous keyframe, so a backward
scrub stutters. Encoding every frame as an I-frame makes each frame decodable
alone, which is what lets a finger drive `currentTime` backwards at 60 Hz.

  encode_all_intra()   libx264, GOP 1, no B-frames, yuv420p, faststart
  verify_all_intra()   every frame I, frame count == duration_s × fps
  join_psnr()          PSNR between a clip's first/last frame and a still —
                       the mechanical form of "no visible seam" (§64.8 #6)

ffmpeg comes from PATH, else from the `imageio-ffmpeg` wheel (a static build,
dev dependency), so the checks need no system install.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

ALL_INTRA_ARGS = [
    "-c:v", "libx264", "-preset", "medium", "-crf", "26",
    "-g", "1", "-keyint_min", "1", "-sc_threshold", "0", "-bf", "0",
    "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an",
]

# Below this the join is visible on a large screen; ~40 dB is visually lossless.
SEAM_PSNR_DB = 35.0


def ffmpeg_exe() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    import imageio_ffmpeg  # dev dependency; Cloud Run images install ffmpeg via apt

    return imageio_ffmpeg.get_ffmpeg_exe()


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([ffmpeg_exe(), "-hide_banner", *args], capture_output=True, text=True, check=True)


def encode_all_intra(input_args: list[str], out: Path, *, fps: int, frames: int, filters: str | None = None,
                     extra_args: list[str] | None = None) -> None:
    """Encode `frames` frames at `fps` from the given ffmpeg inputs as all-intra H.264."""
    out.parent.mkdir(parents=True, exist_ok=True)
    args = ["-y", "-loglevel", "error", *input_args]
    if filters:
        args += ["-filter_complex", filters]
    args += ["-frames:v", str(frames), "-r", str(fps), *(extra_args if extra_args is not None else ALL_INTRA_ARGS), str(out)]
    _run(args)


def frame_types(path: Path) -> list[str]:
    """Picture type of every decoded frame, in order (showinfo; no ffprobe needed)."""
    proc = _run(["-i", str(path), "-vf", "showinfo", "-f", "null", "-"])
    return re.findall(r"\bn:\s*\d+.*?\btype:([IPB])\b", proc.stderr)


def verify_all_intra(path: Path, *, fps: int, duration_s: float) -> dict:
    types = frame_types(path)
    expected = round(duration_s * fps)
    return {
        "frames": len(types),
        "expected_frames": expected,
        "non_intra": sum(t != "I" for t in types),
        "b_frames": types.count("B"),
        "ok": bool(types) and all(t == "I" for t in types) and len(types) == expected,
    }


def join_psnr(clip: Path, still: Path, which: str, frames: int) -> float:
    """PSNR (dB) between the clip's first or last frame and a still image."""
    index = 0 if which == "first" else frames - 1
    graph = (
        f"[0:v]trim=start_frame={index}:end_frame={index + 1},setpts=PTS-STARTPTS,format=yuv420p[a];"
        "[1:v]scale=1280:720,format=yuv420p[b];[a][b]psnr"
    )
    proc = _run(["-i", str(clip), "-i", str(still), "-filter_complex", graph, "-f", "null", "-"])
    match = re.search(r"average:(inf|[\d.]+)", proc.stderr)
    if not match:
        raise RuntimeError(f"psnr not reported for {clip}")
    return float("inf") if match.group(1) == "inf" else float(match.group(1))


def extract_frame(clip: Path, index: int, out: Path) -> None:
    """Write frame `index` as a PNG — how a derived plate is made from a clip's last frame (§39.3)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    _run(["-y", "-loglevel", "error", "-i", str(clip), "-vf", f"select=eq(n\\,{index})", "-frames:v", "1", str(out)])
