"""
Bible — Beat → Layout + Media Directive Mapping

This module defines how each beat in a manifest maps to visual layouts and media
requirements. In a full production system, this would:
- Map semantic beat types (hook, spec, offer) to layout templates
- Define which assets each beat needs (plate, depth, audio, patches)
- Specify composition rules (Ken Burns vs parallax, text positioning)

For the hackathon demo, this is a SCAFFOLD showing the architecture. The planner
directly emits vault URIs; this module proves how the system would scale to
multiple verticals and beat types.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class MediaDirective(BaseModel):
    """What media assets a beat requires."""
    plate: str  # e.g. "urban_flood_dramatic"
    depth_map: bool = True
    audio_phrases: List[str] = []  # phrase IDs for TTS
    patches: List[str] = []  # badge/button asset IDs
    composition_style: str = "parallax"  # "parallax" | "ken_burns" | "still"


class BeatLayout(BaseModel):
    """How a beat should be laid out visually."""
    layout_type: str  # "full_plate" | "split" | "overlay"
    text_position: str  # "bottom_third" | "center" | "top"
    emphasis: str = "normal"  # "normal" | "dramatic" | "technical"


class BibleEntry(BaseModel):
    """Complete specification for how to render a beat."""
    beat_type: str  # "hook" | "flood" | "spec" | "warranty" | "range" | "offer"
    layout: BeatLayout
    media: MediaDirective


def get_bible_entry(beat_type: str, facts: Optional[List[str]] = None) -> BibleEntry:
    """
    Given a beat type and its facts, return the complete rendering specification.
    
    This is the core of the Bible: turning semantic beat types into concrete
    visual and audio requirements.
    
    In production, this would:
    - Query a database of proven layouts per vertical
    - Choose composition style based on device tier
    - Select audio phrasing based on locale and formality
    - Pick patches based on brand guidelines
    
    For the demo, this returns hardcoded specs showing the pattern.
    """
    
    # Example entries for Vega V1 ad beats
    bible: Dict[str, BibleEntry] = {
        "hook": BibleEntry(
            beat_type="hook",
            layout=BeatLayout(
                layout_type="full_plate",
                text_position="center",
                emphasis="dramatic"
            ),
            media=MediaDirective(
                plate="vega_reveal_sunset",
                depth_map=True,
                audio_phrases=["hook_tagline"],
                composition_style="parallax"
            )
        ),
        "flood": BibleEntry(
            beat_type="flood",
            layout=BeatLayout(
                layout_type="full_plate",
                text_position="bottom_third",
                emphasis="dramatic"
            ),
            media=MediaDirective(
                plate="vega_flood_urban",
                depth_map=True,
                audio_phrases=["wading_depth"],
                composition_style="parallax"
            )
        ),
        "spec": BibleEntry(
            beat_type="spec",
            layout=BeatLayout(
                layout_type="overlay",
                text_position="center",
                emphasis="technical"
            ),
            media=MediaDirective(
                plate="vega_tech_dashboard",
                depth_map=True,
                audio_phrases=["clearance", "charge_time", "range"],
                patches=["specs_badge"],
                composition_style="ken_burns"
            )
        ),
        "warranty": BibleEntry(
            beat_type="warranty",
            layout=BeatLayout(
                layout_type="split",
                text_position="bottom_third",
                emphasis="normal"
            ),
            media=MediaDirective(
                plate="vega_battery_closeup",
                depth_map=True,
                audio_phrases=["warranty_years"],
                patches=["warranty_badge"],
                composition_style="parallax"
            )
        ),
        "range": BibleEntry(
            beat_type="range",
            layout=BeatLayout(
                layout_type="full_plate",
                text_position="bottom_third",
                emphasis="normal"
            ),
            media=MediaDirective(
                plate="vega_highway_long_road",
                depth_map=True,
                audio_phrases=["range_km"],
                composition_style="parallax"
            )
        ),
        "offer": BibleEntry(
            beat_type="offer",
            layout=BeatLayout(
                layout_type="full_plate",
                text_position="bottom_third",
                emphasis="normal"
            ),
            media=MediaDirective(
                plate="vega_showroom_lifestyle",
                depth_map=True,
                audio_phrases=["offer_city_price"],
                patches=["price_badge"],
                composition_style="parallax"
            )
        ),
    }
    
    return bible.get(beat_type, bible["hook"])  # fallback to hook


# Example usage (not called in current demo flow)
if __name__ == "__main__":
    entry = get_bible_entry("flood", facts=["f_wading_depth"])
    print(f"Flood beat requires plate: {entry.media.plate}")
    print(f"Layout: {entry.layout.layout_type} with {entry.layout.emphasis} emphasis")
    print(f"Audio phrases: {entry.media.audio_phrases}")
