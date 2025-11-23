from enum import Enum
from pathlib import Path

# Define the base directory once
_SFX_DIR = Path("assets") / "audio" / "sfx"

class SFXList(Enum):
    """A list of available SFXs."""
    FAST_SWORD_WOOSH = _SFX_DIR / "fast-sword-whoosh.wav"
    HEAVY_SWORD_HIT_METAL = _SFX_DIR / "heavy-sword-smashes-metal.wav"
    JUMP_LANDING = _SFX_DIR / "jump_landing.wav"
    ARMOR_RUSTLE = _SFX_DIR / "armor_rustle.wav"
    SWORD_TING = _SFX_DIR / "woosh_sword_ting.wav"
    ROUGH_CLOTH = _SFX_DIR / "rough_cloth.wav"
    ARMOR_RUSTLE_2 = _SFX_DIR / "armor_rustle_2.wav"
    ARMOR_RUSTLE_3 = _SFX_DIR / "armor_rustle_3.wav"
    EXHALE = _SFX_DIR / "exhale.wav"
    SMALL_GRUNT = _SFX_DIR / "small_grunt.wav"
    GRUNT = _SFX_DIR / "grunt.wav"
    INHALE_EXHALE_SHORT = _SFX_DIR / "inhale_exhale_short.wav"