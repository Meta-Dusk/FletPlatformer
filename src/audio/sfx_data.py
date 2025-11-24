from pathlib import Path
from dataclasses import dataclass


_SFX_DIR = Path("assets") / "audio" / "sfx"

@dataclass
class SwordSFX:
    fast_woosh = _SFX_DIR / "fast-sword-whoosh.wav"
    heavy_hit_metal = _SFX_DIR / "heavy-sword-smashes-metal.wav"
    ting = _SFX_DIR / "woosh_sword_ting.wav"
    blade_drop = _SFX_DIR / "blade_drop.wav"

@dataclass
class PlayerSFX:
    exhale = _SFX_DIR / "exhale.wav"
    small_grunt = _SFX_DIR / "small_grunt.wav"
    grunt = _SFX_DIR / "grunt.wav"
    inhale_exhale_short = _SFX_DIR / "inhale_exhale_short.wav"
    grunt_hurt = _SFX_DIR / "grunt_hurt.wav"
    death_1 = _SFX_DIR / "death.wav"
    death_2 = _SFX_DIR / "death_2.wav"
    jump_landing = _SFX_DIR / "jump_landing.wav"

@dataclass
class ArmorSFX:
    rustle_1 = _SFX_DIR / "armor_rustle.wav"
    rustle_2 = _SFX_DIR / "armor_rustle_2.wav"
    rustle_3 = _SFX_DIR / "armor_rustle_3.wav"
    hit_soft = _SFX_DIR / "armor_hit_soft.wav"

@dataclass
class ClothSFX:
    rough_rustle = _SFX_DIR / "rough_cloth.wav"
    clothes_drop = _SFX_DIR / "clothes_drop.wav"

@dataclass
class ItemsSFX:
    keys_drop = _SFX_DIR / "drop_keys.wav"

@dataclass
class SFXLibrary:
    """Dataclasses containing the `Path` for the SFX."""
    sword = SwordSFX()
    item = ItemsSFX()
    player = PlayerSFX()
    cloth = ClothSFX()
    armor = ArmorSFX()
    