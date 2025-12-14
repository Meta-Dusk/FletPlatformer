import flet as ft
import random, asyncio
from typing import Literal

from entities.enemy import Enemy, EnemyType, get_inversely_scaling_stats
from entities.entity import Entity, EntityStats, AnimConfig
from entities.features.entity_data import SFXRegistry

from audio.audio_manager import AudioManager
from audio.sfx_data import SFXLibrary

sfx = SFXLibrary()

class Goblin(Enemy):
    def __init__(
        self,
        page: ft.Page = None,
        audio_manager: AudioManager = None,
        target: Enemy = None,
        name: str = None,
        entity_list: list[Entity] = None,
        *,
        debug: bool = False,
        simple_revive: bool = True
    ) -> None:
        if name is None: name = self.generate_rnd_name()
        
        rnd_health_range = (10, 20)
        min_mv_speed = 2.8
        rnd_health, rnd_mv_speed = get_inversely_scaling_stats(rnd_health_range, min_mv_speed)
        
        if name in {"Gerald", "Rin"}: rnd_health *= 2.0
            
        custom_stats = EntityStats(movement_speed=rnd_mv_speed, health=rnd_health, max_health=rnd_health)
        
        super().__init__(type=EnemyType.GOBLIN, page=page, audio_manager=audio_manager, target=target, name=name, entity_list=entity_list, debug=debug, stats=custom_stats, simple_revive=simple_revive)
        
        self.animations = {
            "idle": AnimConfig(frame_count=4, frame_duration=0.1),
            "run": AnimConfig(frame_count=7, frame_duration=0.1),
            "take-hit": AnimConfig(frame_count=4, frame_duration=0.1, loop=False),
            "death": AnimConfig(frame_count=4, frame_duration=0.1, loop=False),
            "attack-1": AnimConfig(frame_count=8, frame_duration=self.stats.attack_frame_delay, loop=False),
            "attack-2": AnimConfig(frame_count=8, frame_duration=self.stats.attack_frame_delay, loop=False),
        }
        
        self.sfx_registry = SFXRegistry()
        MV_VOLUME = 0.2
        self.sfx_registry.add("run", sfx.footsteps.footstep_grass_1, MV_VOLUME, frame=2)
        self.sfx_registry.add("run", sfx.footsteps.footstep_grass_2, MV_VOLUME, frame=5)
        self.sfx_registry.add("attack-1", sfx.enemy.boggart_hya, frame=5)
        self.sfx_registry.add("attack-2", sfx.enemy.boggart_hya, frame=5)
        self.sfx_registry.add("take-hit", sfx.enemy.goblin_hurt, frame=1)
        self.sfx_registry.add("death", sfx.enemy.goblin_scream, frame=0)
        self.sfx_registry.add("death", sfx.impacts.flesh_impact_2, frame=0)
        self.sfx_registry.add("revive", sfx.magic.strike, frame=3)
        
        self._make_atk_hitbox(p1_r_left=-15, p1_width=180, p1_height=100, p2_r_left=70, p2_width=140, p2_height=80)
        self._make_self_hitbox(width=70, height=75, r_left=40)
        
        self.ai_timer: float = 0.0
        self.ai_decision_delay: float = 0.5
        self.current_ai_goal: str | Literal["idle", "chase", "attack"] = "idle"
        
        self.attack_cooldown_timer: float = 0.0
        self.attack_cooldown_duration: float = 1.5
        
        self.wander_timer: float = 0.0
        self.wander_direction: int = 0
        self.target_dx: float = 0.0
        
        self._spawning_in: bool = True

    def generate_rnd_name(self) -> str:
        names = ["Gobby", "Gibby", "Geeb", "Goob", "Gerald", "Rin"]
        return random.choice(names)

    def tick_animation(self, dt: float) -> bool:
        if self._tick_simple_revive(dt): return True
        if self.states.is_reviving: return False
        
        new_state = "idle"
        if self.states.dead: new_state = "death"
        elif self.states.taking_damage: new_state = "take-hit"
        elif self.states.is_attacking:
            new_state = f"attack-{self.states.attack_phase}" if self.states.attack_phase > 0 else "attack-1"
        elif self.states.is_moving: new_state = "run"
            
        did_frame_change = False
        
        if new_state != self.current_anim_state:
            if "attack" in self.current_anim_state and "attack" not in new_state:
                self.states.is_attacking = False
                self.states.dealing_damage = False
                self._modify_self_hitbox(reset=True)
            self.current_anim_state = new_state
            self.current_frame = 0
            self.anim_timer = 0.0
            did_frame_change = True
        else:
            config = self.animations.get(self.current_anim_state)
            if config:
                self.anim_timer += dt
                if self.anim_timer >= config.frame_duration:
                    self.anim_timer = 0
                    self.current_frame += 1
                    if self.current_frame >= config.frame_count:
                        if config.loop: self.current_frame = 0
                        else: self.current_frame = config.frame_count - 1
                    did_frame_change = True
                    
        if did_frame_change:
            self._handle_specific_frames()
            events = self.sfx_registry.get(self.current_anim_state, self.current_frame)
            for e in events: self._play_sfx(e.sfx, e.volume)
            self._update_sprite_src()
            config = self.animations.get(self.current_anim_state)
            if config and not config.loop and self.current_frame >= config.frame_count - 1:
                self._on_animation_finish()
            return True
        return False

    def _handle_specific_frames(self) -> None:
        state = self.current_anim_state
        frame = self.current_frame
        match state:
            case "attack-1":
                match frame:
                    case 2:
                        if random.randint(1, 2) > 1:
                            self._apply_tint(ft.Colors.YELLOW)
                            self.states.stun_immune = True
                    case 5:
                        self._reset_tint()
                        self.states.stun_immune = False
                    case 6:
                        self._modify_self_hitbox(width=80, height=80, r_left=10)
                        self.states.dealing_damage = True
                        self._toggle_atk_hb_border()
                    case 7:
                        self.states.dealing_damage = False
                        self._toggle_atk_hb_border()
            case "attack-2":
                match frame:
                    case 0: self._modify_self_hitbox(r_left=30)
                    case 1: self._modify_self_hitbox(r_left=0)
                    case 2: self._modify_self_hitbox(r_left=-5, height=60)
                    case 5: self._modify_self_hitbox(r_left=50, height=60)
                    case 6:
                        self.states.dealing_damage = True
                        self._toggle_atk_hb_border()
                    case 7:
                        self.states.dealing_damage = False
                        self._toggle_atk_hb_border()
            case "take-hit":
                match frame:
                    case 1:
                        self._update_health_bar()
                        self._knockback_self(self.target)

    def _on_animation_finish(self) -> None:
        state = self.current_anim_state
        
        if state == "death":
            self.velocity.dx = 0
        
        if state == "revive":
            self.states.is_reviving = False
            self.states.dead = False
            self.states.revivable = False
            self._reset_states()
            self._full_heal()
            self._update_health_bar()
            self._reset_tint()
            self.current_anim_state = "idle"
            self.current_frame = 0
            self._update_sprite_src()
        
        elif state == "take-hit":
            self.states.taking_damage = False
            self.states.is_moving = False
            self.states.dealing_damage = False
            self.states.stunned = False
            self._reset_tint()
            self.ai_timer = 0
            self.velocity.dx = 0
            self.current_ai_goal = "chase"
            self._decide_next_move()
        
        elif "attack" in state:
            self.states.is_attacking = False
            self.states.dealing_damage = False
            self._modify_self_hitbox(reset=True)

    def tick_logic(self, dt: float) -> None:
        """Handles AI state machine."""
        # ALWAYS UPDATE TIMERS
        if self.attack_cooldown_timer > 0:
            self.attack_cooldown_timer -= dt
        
        self.ai_timer -= dt
        
        # BLOCKING STATES
        if (
            self.states.dead
            or self.states.is_attacking
            or self.states.disable_movement
            or self._spawning_in
        ):
            self.velocity.dx = 0
            return
            
        # AI DECISION
        if self.ai_timer <= 0:
            self.ai_timer = self.ai_decision_delay + (random.random() * 0.2)
            self._decide_next_move()
            
        # EXECUTE GOAL
        if self.current_ai_goal == "chase":
            self.velocity.dx = self.target_dx
            if self.velocity.dx != 0:
                self._flip_sprite_x(self.velocity.dx)
                self.states.is_moving = True
                
        elif self.current_ai_goal == "attack":
            self.velocity.dx = 0
            self.states.is_moving = False
            
            if self.attack_cooldown_timer <= 0 and not self.states.is_attacking:
                self.states.attack_phase = random.choice([1, 2])
                self.attack()
                self.attack_cooldown_timer = self.attack_cooldown_duration
                
        elif self.current_ai_goal == "idle":
            self.wander_timer -= dt
            if self.wander_timer <= 0:
                self.wander_timer = random.uniform(1.0, 3.0)
                rand_val = random.random()
                if rand_val < 0.6: self.wander_direction = 0
                elif rand_val < 0.8: self.wander_direction = -1
                else: self.wander_direction = 1
            
            self.velocity.dx = self.wander_direction * (self.stats.movement_speed * 0.5)
            if self.velocity.dx != 0:
                self._flip_sprite_x(self.velocity.dx)
                self.states.is_moving = True
            else:
                self.states.is_moving = False

    def _decide_next_move(self):
        """Simple State Machine logic."""
        if not self.target or self.target.states.dead:
            self.current_ai_goal = "idle"
            return

        dist = self._get_center_point(self.target) - self._get_center_point(self)
        abs_dist = abs(dist)
        
        if abs_dist <= self.melee_range:
            self.current_ai_goal = "attack"
            self._flip_sprite_x(1 if dist > 0 else -1)
        else:
            self.current_ai_goal = "chase"
            direction = 1 if dist > 0 else -1
            self.target_dx = direction * self.stats.movement_speed
            
            if self.target.states.dealing_damage:
                self.target_dx *= -1
                
    async def spawn_sequence(self) -> None:
        self._spawning_in = True
        await asyncio.sleep(0.5)
        self._play_sfx(sfx.enemy.goblin_cackle)
        await super().spawn_sequence()
        self._spawning_in = False