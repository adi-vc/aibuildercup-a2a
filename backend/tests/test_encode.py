"""T7 / P6 §64.8 criteria 1–3 and 6 on the committed placeholder clips, plus content addressing."""

from pathlib import Path

import pytest

from app.pipeline import encode, placeholder_clips

REGISTRY = placeholder_clips.load_registry()
CLIPS = REGISTRY["clips"]
VAULT = placeholder_clips.VAULT_DIR


def _path(uri: str) -> Path:
    return VAULT / Path(uri).name


def test_at_least_two_clips_exist():
    """Criterion 1 — the floor §65 protects."""
    assert len(CLIPS) >= 2
    for clip in CLIPS.values():
        assert _path(clip["uri"]).exists()


@pytest.mark.parametrize("name", sorted(CLIPS))
def test_every_frame_is_intra_and_frame_count_matches(name):
    """Criteria 2–3 — every frame I, zero B; duration_s × fps == frame_count."""
    clip = CLIPS[name]
    report = encode.verify_all_intra(_path(clip["uri"]), fps=clip["fps"], duration_s=clip["duration_s"])
    assert report["non_intra"] == 0 and report["b_frames"] == 0
    assert report["frames"] == report["expected_frames"] == clip["frames"]
    assert report["ok"]


@pytest.mark.parametrize("name", sorted(CLIPS))
def test_no_seam_at_either_join(name):
    """Criterion 6, mechanically: frame 0 ≈ hold A's plate; last frame ≈ hold B's derived plate."""
    clip = CLIPS[name]
    path = _path(clip["uri"])
    plate_a = placeholder_clips.ASSETS / Path(clip["from_plate_uri"]).name
    plate_b = _path(clip["derived_plate"]["uri"])
    assert encode.join_psnr(path, plate_a, "first", clip["frames"]) >= encode.SEAM_PSNR_DB
    assert encode.join_psnr(path, plate_b, "last", clip["frames"]) >= encode.SEAM_PSNR_DB


def test_checker_detects_a_normal_gop_encode(tmp_path):
    """The verifier must fail an ordinary (P/B-frame) encode, or it proves nothing."""
    src = placeholder_clips.ASSETS / "placeholder_flood_street.png"
    out = tmp_path / "gop.mp4"
    encode.encode_all_intra(
        ["-loop", "1", "-framerate", "24", "-i", str(src)], out, fps=24, frames=48,
        filters="[0:v]zoompan=z='1+0.002*on':d=1:s=1280x720:fps=24,format=yuv420p",
        extra_args=["-c:v", "libx264", "-g", "48", "-bf", "2", "-pix_fmt", "yuv420p", "-an"],
    )
    report = encode.verify_all_intra(out, fps=24, duration_s=2.0)
    assert not report["ok"] and report["non_intra"] > 0


def test_rebuild_with_unchanged_inputs_encodes_nothing():
    """Content addressing (§32.1 rule 2): a rerun is free."""
    assert placeholder_clips.build()["encoded"] == 0
    assert placeholder_clips.load_registry()["clips"] == CLIPS
