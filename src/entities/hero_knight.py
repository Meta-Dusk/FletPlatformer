import flet as ft
import asyncio, random

from audio.audio_manager import AudioManager
from audio.sfx_data import SFXLibrary
from entities.player import Player, PlayerType, SFXRegistry
from entities.entity import Entity, EntityStats
from utilities.keyboard_manager import held_keys_set
from images import Sprite

sfx = SFXLibrary()

class HeroKnight(Player):
    def __init__(
        self, page: ft.Page, audio_manager: AudioManager, held_keys: held_keys_set,
        entity_list: list[Entity] = None, *, debug: bool = False, verbose_stamina: bool = False
    ) -> None:
        sprite = Sprite(
            src="images/players/hero_knight/idle_0.png", width=180, height=180,
            offset=ft.Offset(0, 0.225)
        )
        stats = EntityStats(armor=100, crit_chance=10)
        
        super().__init__(
            page, audio_manager, sprite, held_keys, entity_list, debug=debug,
            verbose_stamina=verbose_stamina, type=PlayerType.HERO_KNIGHT, stats=stats
        )
        
        # Hitbox setup
        self._make_atk_hitbox(
            p1_r_left=60, p1_width=110, p1_height=130,
            p2_r_left=120, p2_width=140, p2_height=162
        )
        self._make_self_hitbox(width=95, height=110, r_left=55)
        
        # Other SFX setup
        self.landing_sfx_list = [
            sfx.player.jump_landing,
            sfx.player.exhale,
            sfx.impacts.landing_on_grass
        ]
        self.looking_away_sfx_list = [sfx.armor.rustle_1]
    
    # * === ONE-SHOT ANIMATIONS ===
    async def _revive_anim(self) -> None:
        """Handles the player's revival animation."""
        frame: int = 10
        self._play_sfx(sfx.magic.strike)
        
        while frame >= 0:
            await asyncio.sleep(0.1)
            if frame == 5: self._play_sfx(sfx.armor.rustle_3)
            self.sprite.change_src(self._get_spr_path("death", frame))
            frame -= 1
    
    async def _jump_anim(self) -> None:
        """Handles the player's jump animation."""
        FRAMES: int = 2
        self._play_sfx(sfx.cloth.rough_rustle)
        self._play_sfx(sfx.player.inhale_exhale_short)
        
        for frame in range(FRAMES + 1):
            await asyncio.sleep(self._LOGIC_DELAY)
            if self.states.is_attacking: continue # ? Skips animation if attacking mid-air
            self.sprite.change_src(self._get_spr_path("jump", frame))
            
        await asyncio.sleep(self.stats.jump_air_time)
        self.states.jumped = False
        self._jump_task = None
    
    async def _attack_anim(self) -> None:
        """Handles the player's attack animations with combos."""
        prefix = f"attack-{self.states.attack_phase}"
        FRAMES: int = 6
        
        for frame in range(FRAMES + 1):
            await asyncio.sleep(self.stats.attack_frame_delay)
            
            # ? Upward slash
            if self.states.attack_phase == 1:
                if frame == 0: self._modify_self_hitbox(r_left=45, width=85)
                if frame == 2:
                    self._play_sfx(sfx.sword.fast_woosh)
                    self._play_sfx(sfx.player.small_grunt)
            
            # ? Downward slash
            elif self.states.attack_phase == 2:
                if frame == 0: self._modify_self_hitbox(width=75, r_left=75)
                if frame == 1:
                    self._play_sfx(sfx.sword.ting)
                    self._play_sfx(sfx.player.grunt)
                elif frame == 3:
                    self._modify_self_hitbox(r_left=100)
                    self._play_sfx(sfx.impacts.landing_on_grass)
                    
            # ? Either attack
            if frame == 3:
                self.states.dealing_damage = True
                self._toggle_atk_hb_border()
            elif frame == 5:
                self.states.dealing_damage = False
                self._toggle_atk_hb_border()
            self.sprite.change_src(self._get_spr_path(prefix, frame))
            
        self._modify_self_hitbox(reset=True)
        self.states.is_attacking = False
        self._attack_task = None
        self._toggle_atk_hb_border()
    
    async def _death_anim(self) -> None:
        """Handles the player's death animation."""
        death_sfx = [sfx.player.death_1, sfx.player.death_2]
        FRAMES: int = 10
        
        for frame in range(FRAMES + 1):
            if frame == 1: continue
            await asyncio.sleep(self._LOGIC_DELAY)
            if frame == 3:
                self._play_sfx(random.choice(death_sfx))
                self._update_health_bar()
            if frame == 4: self._play_sfx(sfx.cloth.clothes_drop)
            if frame == 5: self._play_sfx(sfx.armor.hit_soft)
            if frame == 6:
                self._play_sfx(sfx.item.keys_drop)
                self._play_sfx(sfx.sword.blade_drop)
            self.sprite.change_src(self._get_spr_path("death", frame))
        self.states.revivable = True
    
    async def _take_hit_anim(self) -> None:
        """Handles the player's taking damage animation."""
        FRAMES: int = 3
        
        for frame in range(FRAMES + 1):
            if frame == 0: continue
            await asyncio.sleep(0.1)
            if frame == 1:
                self._play_sfx(sfx.player.grunt_hurt)
                self._update_health_bar()
            self.sprite.change_src(self._get_spr_path("take-hit", frame))
        self.states.taking_damage = False
        self.states.stunned = False
        self._take_hit_task = None
        self._reset_tint()
        self._start_hp_loop()
        
    # * === LOOPING ANIMATIONS ===
    async def _animation_loop(self):
        """Handles the `HeroKnight` animation loop."""
        MOVEMENT_VOLUME: float = 0.2
        
        sfx_map = SFXRegistry()
        sfx_map.add("moving", sfx.armor.rustle_2, MOVEMENT_VOLUME, frame=2)
        sfx_map.add("moving", sfx.footsteps.footstep_grass_1, MOVEMENT_VOLUME, frame=2)
        sfx_map.add("moving", sfx.armor.rustle_3, MOVEMENT_VOLUME, frame=5)
        sfx_map.add("moving", sfx.footsteps.footstep_grass_2, MOVEMENT_VOLUME, frame=5)
        
        await super()._animation_loop(
            falling_frames=2, movement_frames=7,
            idle_frames=10, sfx_map=sfx_map
        )