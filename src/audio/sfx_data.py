from pathlib import Path
from dataclasses import dataclass


_SFX_DIR = Path("assets") / "audio" / "sfx"

def sound_path(name: str, extension: str = ".wav"):
    return _SFX_DIR / f"{name}{extension}"

# * Sub Sound Libraries
@dataclass
class SwordSFX:
    fast_woosh = sound_path("fast-sword-whoosh")
    heavy_hit_metal = sound_path("heavy-sword-smashes-metal")
    ting = sound_path("woosh_sword_ting")
    blade_drop = sound_path("blade_drop")

@dataclass
class PlayerSFX:
    exhale = sound_path("exhale")
    small_grunt = sound_path("small_grunt")
    grunt = sound_path("grunt")
    inhale_exhale_short = sound_path("inhale_exhale_short")
    grunt_hurt = sound_path("grunt_hurt")
    death_1 = sound_path("death")
    death_2 = sound_path("death_2")
    jump_landing = sound_path("jump_landing")

@dataclass
class ArmorSFX:
    rustle_1 = sound_path("armor_rustle")
    rustle_2 = sound_path("armor_rustle_2")
    rustle_3 = sound_path("armor_rustle_3")
    hit_soft = sound_path("armor_hit_soft")

@dataclass
class ClothSFX:
    rough_rustle = sound_path("rough_cloth")
    clothes_drop = sound_path("clothes_drop")

@dataclass
class ItemsSFX:
    keys_drop = sound_path("drop_keys")

@dataclass
class MagicSFX:
    strike = sound_path("magic_strike")

@dataclass
class EffectsSFX:
    level_up_quirky = sound_path("level_up_quirky")
    riser_end_up_swell = sound_path("riser_end_up_swell")

@dataclass
class EnemySFX:
    boggart_hya = sound_path("boggart_hya")
    boggart_dies = sound_path("boggart_dies")
    boggart_woah = sound_path("boggart_woah")
    boggart_grumble = sound_path("boggart_grumble")
    goblin_cackle = sound_path("goblin_cackle")
    goblin_death = sound_path("goblin_death")
    goblin_hurt = sound_path("goblin_hurt")
    goblin_scream = sound_path("goblin_scream")

@dataclass
class FootstepsSFX:
    footstep_grass_1 = sound_path("footstep_grass_1")
    footstep_grass_2 = sound_path("footstep_grass_2")

@dataclass
class ImpactsSFX:
    flesh_impact_1 = sound_path("flesh_impact_1")
    flesh_impact_2 = sound_path("flesh_impact_2")
    axe_hit_flesh = sound_path("axe_hit_flesh")
    landing_on_grass = sound_path("landing_on_grass")

# * Main Sound Library
@dataclass
class SFXLibrary:
    """Dataclasses containing the `Path` for the SFX."""
    sword = SwordSFX()
    item = ItemsSFX()
    player = PlayerSFX()
    cloth = ClothSFX()
    armor = ArmorSFX()
    magic = MagicSFX()
    effects = EffectsSFX()
    enemy = EnemySFX()
    footsteps = FootstepsSFX()
    impacts = ImpactsSFX()
    