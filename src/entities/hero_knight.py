import flet as ft

from entities.player import Player, PlayerType
from entities.entity import Entity, EntityStats, AnimConfig, EntityStates
from audio.audio_manager import AudioManager
from audio.sfx_data import SFXLibrary
from utilities.keyboard_manager import HeldKeys
from images import Sprite

sfx = SFXLibrary()

class HeroKnight(Player):
    def __init__(
        self,
        page: ft.Page,
        audio_manager: AudioManager,
        held_keys: HeldKeys,
        entity_list: list[Entity] = None,
        *,
        debug: bool = False,
        verbose_stamina: bool = False,
        simple_revive: bool = True
    ) -> None:
        
        sprite = Sprite(
            src="images/players/hero_knight/idle_0.png", width=180, height=180,
            offset=ft.Offset(0, 0.225)
        )
        stats = EntityStats(armor=100, crit_chance=10, knockback_resistance=0.5)
        
        super().__init__(
            page, audio_manager, sprite, held_keys, entity_list, debug=debug,
            verbose_stamina=verbose_stamina, type=PlayerType.HERO_KNIGHT, stats=stats,
            simple_revive=simple_revive
        )
        
        # --- 1. DEFINE ANIMATIONS ---
        # Replace the arguments you used to pass to _animation_loop
        self.animations = {
            "idle": AnimConfig(frame_count=11, frame_duration=0.075),
            "run": AnimConfig(frame_count=8, frame_duration=0.075),
            "jump": AnimConfig(frame_count=3, frame_duration=0.1, loop=False),
            "fall": AnimConfig(frame_count=3, frame_duration=0.1),
            "death": AnimConfig(frame_count=11, frame_duration=0.1, loop=False),
            "take-hit": AnimConfig(frame_count=4, frame_duration=0.1, loop=False),
            # Attacks
            "attack-1": AnimConfig(frame_count=7, frame_duration=self.stats.attack_frame_delay, loop=False),
            "attack-2": AnimConfig(frame_count=7, frame_duration=self.stats.attack_frame_delay, loop=False),
        }
        
        # --- 2. REGISTER SFX ---
        MV_VOLUME = 0.2
        self.sfx_registry.add("run", sfx.armor.rustle_2, MV_VOLUME, frame=2)
        self.sfx_registry.add("run", sfx.footsteps.footstep_grass_1, MV_VOLUME, frame=2)
        self.sfx_registry.add("run", sfx.armor.rustle_3, MV_VOLUME, frame=5)
        self.sfx_registry.add("run", sfx.footsteps.footstep_grass_2, MV_VOLUME, frame=5)
        
        # Jump / Land
        self.sfx_registry.add("jump", sfx.cloth.rough_rustle, frame=0)
        
        # Attacks
        self.sfx_registry.add("attack-1", sfx.sword.fast_woosh, frame=2)
        self.sfx_registry.add("attack-1", sfx.player.small_grunt, frame=2)
        self.sfx_registry.add("attack-2", sfx.sword.ting, frame=1)
        self.sfx_registry.add("attack-2", sfx.player.grunt, frame=1)
        self.sfx_registry.add("attack-2", sfx.impacts.landing_on_grass, frame=3)
        
        # Take Hit
        self.sfx_registry.add("take-hit", sfx.player.grunt_hurt, frame=1)
        
        # Death
        self.sfx_registry.add("death", sfx.player.death_1, frame=3)
        self.sfx_registry.add("death", sfx.cloth.clothes_drop, frame=4)
        self.sfx_registry.add("death", sfx.armor.hit_soft, frame=5)
        self.sfx_registry.add("death", sfx.item.keys_drop, frame=6)
        self.sfx_registry.add("death", sfx.sword.blade_drop, frame=6)
        
        # Revive
        self.sfx_registry.add("revive", sfx.magic.strike, frame=10)
        
        # Hitbox setup
        self._make_atk_hitbox(
            p1_r_left=60, p1_width=110, p1_height=130,
            p2_r_left=120, p2_width=140, p2_height=162
        )
        self._make_self_hitbox(width=95, height=110, r_left=55)

        self.landing_sfx_list = [sfx.player.jump_landing, sfx.impacts.landing_on_grass]

    def tick_animation(self, dt: float) -> bool:
        """
        Overrides base logic to handle HeroKnight specific Hitboxes and State Logic.
        """
        did_change = super().tick_animation(dt)

        # --- CUSTOM FRAME LOGIC ---
        if did_change:
            self._handle_specific_frames()

        # --- ANIMATION END CLEANUP ---
        if self._is_anim_finished():
            self._on_animation_finish()

        return did_change

    def _handle_specific_frames(self):
        """Replaces the logic that was inside your async loops."""
        state = self.current_anim_state
        frame = self.current_frame
        
        match state:
            case "attack-1":
                match frame:
                    case 0:
                        self._modify_self_hitbox(r_left=45, width=85)
                    case 3:
                        self.states.dealing_damage = True
                        self._toggle_atk_hb_border()
                    case 5:
                        self.states.dealing_damage = False
                        self._toggle_atk_hb_border()
            
            case "attack-2":
                match frame:
                    case 0:
                        self._modify_self_hitbox(width=75, r_left=75)
                    case 3:
                        self._modify_self_hitbox(r_left=100)
                        self.states.dealing_damage = True
                        self._toggle_atk_hb_border()
                    case 5:
                        self.states.dealing_damage = False
                        self._toggle_atk_hb_border()
            
            case "take-hit":
                match frame:
                    case 1:
                        self._update_health_bar()
                        self.velocity.dx = 0
            
            case "death":
                match frame:
                    case 3: self._update_health_bar()
                
    def _on_animation_finish(self) -> None:
        """Called when a non-looping animation reaches the end."""
        state = self.current_anim_state
        
        if state == "death":
            self.states.revivable = True
        
        elif state == "revive":
            self.states.is_reviving = False
            self.states.dead = False
            self.states.revivable = False
            
            # Reset Stats
            self._reset_states(EntityStates(restrict_movement=True))
            self._full_heal()
            self._update_health_bar()
            self._reset_tint()
            
            # Switch to Idle
            self.current_anim_state = "idle"
            self.current_frame = 0
            self._update_sprite_src()
        
        elif state == "take-hit":
            self.states.taking_damage = False
            self.states.stunned = False
            self._reset_tint()
        
        elif "attack" in state:
            # 1. Unlock State
            self.states.is_attacking = False
            self.states.dealing_damage = False
            
            # 2. Cleanup Hitboxes
            self._modify_self_hitbox(reset=True)
            self._toggle_atk_hb_border()
            
        elif state == "jump":
            self.states.jumped = False

    def _is_anim_finished(self) -> bool:
        """Helper to check if current non-looping animation is done."""
        config = self.animations.get(self.current_anim_state)
        if not config or config.loop: return False
        return self.current_frame >= config.frame_count - 1