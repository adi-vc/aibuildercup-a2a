"""
placeholder_clips.py — stand-in transition clips until Veo is available (P6).

Veo (§37.3) generates an edge clip conditioned on hold A's final frame. Until
credentials exist, each clip here is a deterministic camera move over hold A's
plate, built with ffmpeg alone. Everything around the clip is the real thing:

  • continuity by construction (§39.3) — frame 0 *is* hold A's plate, and hold
    B's plate is extracted from the clip's last frame, so both joins are exact;
  • all-intra encoding (§39.12) and its verification (pipeline/encode.py);
  • content addressing (§32.1 rule 2) — the id hashes the recipe, the input
    plate bytes and the encoder settings, so a rerun with unchanged inputs
    encodes nothing, and swapping in a Veo clip later changes only bytes.

Run:  python -m app.pipeline.placeholder_clips
Writes media to frontend/public/assets/vault/ and the registry the planner
reads to backend/app/pipeline/placeholder_vault.json.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.pipeline import encode

REPO = Path(__file__).resolve().parents[3]
ASSETS = REPO / "frontend" / "public" / "assets"
VAULT_DIR = ASSETS / "vault"
VAULT_URI = "/assets/vault"
REGISTRY = Path(__file__).with_name("placeholder_vault.json")

PLATE_URI = "/assets/placeholder_flood_street.png"
FPS = 24  # Veo's native rate (§32.1 #7)
GENERATOR_VERSION = "placeholder-clips-v1"


def _ease(n: int) -> str:
    """Cosine ease-in-out over the clip, as an ffmpeg expression of output frame `on`."""
    return f"((1-cos(PI*on/{n - 1}))/2)"


def _flood_to_spec(frames: int) -> tuple[list[str], str]:
    """Camera pushes from the street to the waterline; water dims; measurement lines draw in."""
    e = _ease(frames)
    cx = f"(640+(330-640)*{e})"
    cy = f"(360+(560-360)*{e})"
    zoompan = (
        f"zoompan=z='1+0.8*{e}'"
        f":x='max(0,min(iw-iw/zoom,{cx}*4-iw/zoom/2))'"
        f":y='max(0,min(ih-ih/zoom,{cy}*4-ih/zoom/2))'"
        f":d=1:s=1280x720:fps={FPS}"
    )
    duration = frames / FPS
    steps = 12
    lines = ",".join(
        f"drawbox=x=120:y=470:w={int(80 + (1040 - 80) * (k + 1) / steps)}:h=4:color=white@0.85:t=fill"
        f":enable='gte(t,{duration * 0.55 + k * duration * 0.35 / steps:.3f})'"
        for k in range(steps)
    )
    tick = f"drawbox=x=120:y=330:w=4:h=144:color=white@0.85:t=fill:enable='gte(t,{duration * 0.6:.3f})'"
    graph = (
        # Upscale 4x before zoompan so sub-pixel camera moves don't jitter.
        f"[0:v]scale=5120:2880:flags=lanczos,{zoompan},"
        f"eq=brightness='-0.06*min(1,t/{duration:.3f})':eval=frame,{lines},{tick},format=yuv420p"
    )
    return [], graph


def _range_to_offer(frames: int) -> tuple[list[str], str]:
    """Road blurs into a neutral studio sweep; an abstract product block settles centre-frame (no text)."""
    duration = frames / FPS
    studio_src = f"color=c=0x34383f:s=1280x720:r={FPS}:d={duration:.3f}"
    product = (
        "drawbox=x=0:y=470:w=1280:h=250:color=0x1e2125:t=fill,"  # studio floor
        "drawbox=x=500:y=330:w=300:h=130:color=0xb4461f:t=fill,"
        "drawbox=x=470:y=300:w=120:h=40:color=0x2b2620:t=fill,"
        "drawbox=x=500:y=440:w=100:h=100:color=0x1b1b1b:t=fill,"
        "drawbox=x=700:y=440:w=100:h=100:color=0x1b1b1b:t=fill"
    )
    graph = (
        f"[0:v]scale=1280:720,fps={FPS},settb=AVTB,format=yuv420p,setsar=1[a];"
        f"[1:v]{product},fps={FPS},settb=AVTB,format=yuv420p,setsar=1[b];"
        f"[a][b]xfade=transition=hblur:duration={duration:.3f}:offset=0,format=yuv420p"
    )
    return ["-f", "lavfi", "-i", studio_src], graph


RECIPES = {
    "clip_flood_to_spec": {"duration_s": 3.0, "build": _flood_to_spec},
    "clip_range_to_offer": {"duration_s": 2.5, "build": _range_to_offer},
}


def _content_id(prefix: str, *parts: bytes | str) -> str:
    h = hashlib.sha1()
    for part in parts:
        h.update(part if isinstance(part, bytes) else part.encode("utf-8"))
        h.update(b"\x00")
    return f"{prefix}_{h.hexdigest()[:16]}"


def build(force: bool = False) -> dict:
    """Build (or reuse) every placeholder clip and its derived plate; return the registry."""
    plate_path = ASSETS / Path(PLATE_URI).name
    plate_bytes = plate_path.read_bytes()
    clips: dict[str, dict] = {}
    encoded = 0
    for name, recipe in RECIPES.items():
        frames = round(recipe["duration_s"] * FPS)
        extra_inputs, graph = recipe["build"](frames)
        clip_id = _content_id("clip", GENERATOR_VERSION, name, graph, json.dumps(extra_inputs),
                              json.dumps(encode.ALL_INTRA_ARGS), plate_bytes)
        clip_path = VAULT_DIR / f"{clip_id}.mp4"
        plate_id = _content_id("plate", clip_id, "last-frame")
        derived_path = VAULT_DIR / f"{plate_id}.png"
        if force or not clip_path.exists():
            inputs = ["-loop", "1", "-framerate", str(FPS), "-t", f"{recipe['duration_s']}", "-i", str(plate_path), *extra_inputs]
            encode.encode_all_intra(inputs, clip_path, fps=FPS, frames=frames, filters=graph)
            encoded += 1
        if force or not derived_path.exists():
            encode.extract_frame(clip_path, frames - 1, derived_path)
        clips[name] = {
            "asset_id": clip_id,
            "uri": f"{VAULT_URI}/{clip_path.name}",
            "fps": FPS,
            "duration_s": recipe["duration_s"],
            "frames": frames,
            "from_plate_uri": PLATE_URI,
            "derived_plate": {"asset_id": plate_id, "uri": f"{VAULT_URI}/{derived_path.name}"},
        }
    # Prune superseded outputs: the vault dir holds only what the registry references.
    keep = {Path(c["uri"]).name for c in clips.values()} | {Path(c["derived_plate"]["uri"]).name for c in clips.values()}
    for stale in VAULT_DIR.glob("*"):
        if stale.name not in keep:
            stale.unlink()
    registry = {"generator": GENERATOR_VERSION, "encoder_args": encode.ALL_INTRA_ARGS, "clips": clips}
    REGISTRY.write_text(json.dumps(registry, indent=2) + "\n")
    return {"encoded": encoded, **registry}


def load_registry() -> dict:
    """The committed registry; empty when placeholder clips were never built."""
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {"clips": {}}


if __name__ == "__main__":
    result = build()
    print(f"encoded {result['encoded']} clip(s); registry → {REGISTRY.relative_to(REPO)}")
    for name, clip in result["clips"].items():
        report = encode.verify_all_intra(VAULT_DIR / Path(clip["uri"]).name, fps=clip["fps"], duration_s=clip["duration_s"])
        print(f"  {name}: {clip['uri']}  frames={report['frames']}/{report['expected_frames']}  all-intra={report['ok']}")
