import os
from enum import Enum


class SFXList(Enum):
    FAST_SWORD_WOOSH = os.path.join("assets", "audio", "sfx", "fast-sword-whoosh.wav")
    HEAVY_SWORD_HIT_METAL = os.path.join("assets", "audio", "sfx", "heavy-sword-smashes-metal.wav")
    JUMP_LANDING = os.path.join("assets", "audio", "sfx", "jump_landing.wav")
    ARMOR_RUSTLE = os.path.join("assets", "audio", "sfx", "armor_rustle.wav")
    SWORD_TING = os.path.join("assets", "audio", "sfx", "woosh_sword_ting.wav")
    ROUGH_CLOTH = os.path.join("assets", "audio", "sfx", "rough_cloth.wav")
    ARMOR_RUSTLE_2 = os.path.join("assets", "audio", "sfx", "armor_rustle_2.wav")
    ARMOR_RUSTLE_3 = os.path.join("assets", "audio", "sfx", "armor_rustle_3.wav")
    EXHALE = os.path.join("assets", "audio", "sfx", "exhale.wav")
    SMALL_GRUNT = os.path.join("assets", "audio", "sfx", "small_grunt.wav")
    GRUNT = os.path.join("assets", "audio", "sfx", "grunt.wav")
    INHALE_EXHALE_SHORT = os.path.join("assets", "audio", "sfx", "inhale_exhale_short.wav")
    