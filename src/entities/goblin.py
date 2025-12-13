import flet as ft
import random, asyncio

from entities.enemy import Enemy, EnemyType, get_inversely_scaling_stats
from entities.entity import Entity, EntityStats, AnimConfig
from entities.features.entity_data import SFXRegistry

from audio.audio_manager import AudioManager
from audio.sfx_data import SFXLibrary

from utilities.components import try_update, await_for_dur

sfx = SFXLibrary()

# TODO: Attempt to implement a ranged attack
class Goblin(Enemy):
    """A preset `Enemy` class specifically for the Goblin enemy type."""
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
        """Makes a custom `Enemy` class specifically for making a goblin enemy."""
        if name is None: name = self.generate_rnd_name()
        
        # Random stats
        rnd_health_range = (10, 20)
        min_mv_speed = 3
        rnd_health, rnd_mv_speed = get_inversely_scaling_stats(rnd_health_range, min_mv_speed)
        
        if name in {"Gerald", "Rin"}:
            SPECIAL_FACTOR: float = 2.0
            rnd_mv_speed *= SPECIAL_FACTOR
            rnd_health *= SPECIAL_FACTOR
            
        custom_stats = EntityStats(
            movement_speed=rnd_mv_speed,
            health=rnd_health, max_health=rnd_health
        )
        
        super().__init__(
            type=EnemyType.GOBLIN, page=page, audio_manager=audio_manager, target=target,
            name=name, entity_list=entity_list, debug=debug, stats=custom_stats, simple_revive=simple_revive
        )
        
        # --- 1. DEFINE ANIMATIONS ---
        self.animations = {
            "idle": AnimConfig(frame_count=4, frame_duration=0.1),
            "run": AnimConfig(frame_count=7, frame_duration=0.1),
            "take-hit": AnimConfig(frame_count=4, frame_duration=0.1, loop=False),
            "death": AnimConfig(frame_count=4, frame_duration=0.1, loop=False),
            # Attack Phases
            "attack-1": AnimConfig(frame_count=8, frame_duration=self.stats.attack_frame_delay, loop=False),
            "attack-2": AnimConfig(frame_count=8, frame_duration=self.stats.attack_frame_delay, loop=False),
        }
        
        # --- 2. REGISTER SFX ---
        self.sfx_registry = SFXRegistry()
        
        # Movement SFX
        MV_VOLUME = 0.2
        self.sfx_registry.add("run", sfx.footsteps.footstep_grass_1, MV_VOLUME, frame=2)
        self.sfx_registry.add("run", sfx.footsteps.footstep_grass_2, MV_VOLUME, frame=5)
        
        # Attack SFX
        self.sfx_registry.add("attack-1", sfx.enemy.boggart_hya, frame=5)
        self.sfx_registry.add("attack-2", sfx.enemy.boggart_hya, frame=5)
        
        # Hit/Death SFX
        self.sfx_registry.add("take-hit", sfx.enemy.goblin_hurt, frame=1)
        self.sfx_registry.add("death", sfx.enemy.goblin_scream, frame=0)
        self.sfx_registry.add("death", sfx.impacts.flesh_impact_2, frame=0)
        
        # Revive SFX
        self.sfx_registry.add("revive", sfx.magic.strike, frame=3)
        
        # Hitboxes
        self._make_atk_hitbox(
            p1_r_left=-15, p1_width=180, p1_height=100,
            p2_r_left=70, p2_width=140, p2_height=80
        )
        self._make_self_hitbox(width=70, height=75, r_left=40)
        
        # Other setup
        self._rnd_dx: int = 0
    
    def generate_rnd_name(self) -> None:
        """Returns a random name from the list."""
        names = [
            "Gobby", "Gibby", "Geeb", "Goob", "Gubby", "Gebby", "Gub", "Gerald", "Gibby", "Gib",
            "Gob", "Gobber", "Gob Lin", "Gob Gob", "Geb Geb", "Gub Gub", "Gib Gib", "Gibba", "Gibber",
            "Gob Rin", "Gobrin", "Rin"
        ]
        return random.choice(names)
    
    # * === TICK ANIMATION (Replaces all async anim tasks) ===
    def tick_animation(self, dt: float) -> bool:
        if self._tick_simple_revive(dt): return True
        
        if self.states.is_reviving: return False
        
        # 1. Determine State
        new_state = "idle"
        
        if self.states.dead:
            new_state = "death"
        elif self.states.taking_damage:
            new_state = "take-hit"
        elif self.states.is_attacking:
            new_state = f"attack-{self.states.attack_phase}" if self.states.attack_phase > 0 else "attack-1"
        elif self.states.is_moving:
            new_state = "run"
            
        did_frame_change = False
        
        # --- A. STATE SWITCH ---
        if new_state != self.current_anim_state:
            # Safety Cleanup for Goblin
            if "attack" in self.current_anim_state and "attack" not in new_state:
                self.states.is_attacking = False
                self.states.dealing_damage = False
                self._modify_self_hitbox(reset=True)
                
            self.current_anim_state = new_state
            self.current_frame = 0
            self.anim_timer = 0.0
            did_frame_change = True # <--- Run logic for Frame 0
            
        # --- B. TIMER ---
        else:
            config = self.animations.get(self.current_anim_state)
            if config:
                self.anim_timer += dt
                if self.anim_timer >= config.frame_duration:
                    self.anim_timer = 0
                    self.current_frame += 1
                    
                    if self.current_frame >= config.frame_count:
                        if config.loop:
                            self.current_frame = 0
                        else:
                            self.current_frame = config.frame_count - 1
                    
                    did_frame_change = True
                    
        # --- C. PROCESS ---
        if did_frame_change:
            # 1. Specific Logic (Hitboxes, Parry colors)
            self._handle_specific_frames()
            
            # 2. SFX
            events = self.sfx_registry.get(self.current_anim_state, self.current_frame)
            for e in events: self._play_sfx(e.sfx, e.volume)
            
            # 3. Visuals
            self._update_sprite_src()
            
            # 4. Finish Check (Non-looping)
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
                    # Parry Chance
                    case 2:
                        if not random.randint(1, 2) > 1: return
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
            pass
        
        elif state == "revive":
            self.states.is_reviving = False
            self.states.dead = False
            self.states.revivable = False
            
            # Reset Stats
            self._reset_states()
            self._full_heal()
            self._update_health_bar()
            self._reset_tint()
            
            # Restart Inputs
            self._start_loops()
            
            # Switch to Idle
            self.current_anim_state = "idle"
            self.current_frame = 0
            self._update_sprite_src()
        
        elif state == "take-hit":
            self.states.taking_damage = False
            self._reset_tint()
        
        elif "attack" in state:
            self.states.is_attacking = False
            self.states.dealing_damage = False
            self._modify_self_hitbox(reset=True)
    
    # * === CUSTOM MOVEMENT LOOP ===
    async def _movement_loop(self) -> None:
        """Handles the goblin's simple AI."""
        MV_DELAY: float = 0.05
        ATK_DELAY: float = 1.0
        
        # Announce if goblin is spawned in the scene (sfx + fade in)
        await asyncio.sleep(0.5)
        self._play_sfx(sfx.enemy.goblin_cackle)
        self.stack.opacity = 1
        try_update(self.stack)
        await await_for_dur(self.stack.animate_opacity)
        
        while not self.states.dead:
            if self.states.disable_movement or self.states.taking_damage:
                if not self.states.taking_damage:
                    self.velocity.dx = 0
                await asyncio.sleep(self._LOGIC_DELAY)
                continue
            
            dx = 0
            
            # ? Chase Target
            if not self._is_target_in_range():
                if self.target and not self.target.states.dead:
                    # Move Left or Right based on target position
                    if self._get_center_point(self.target) > self._get_center_point(self):
                        dx = self.stats.movement_speed
                    else: 
                        dx = -self.stats.movement_speed
                    
                    # Retreat if target attacking (Basic AI)
                    if self.target.states.dealing_damage:
                        dx *= -1 
                        
                    self.is_idling = False
                else: 
                    self.is_idling = True
                
            else: # ? Attack Target
                if self.target and not self.target.states.dead:
                    self.velocity.dx = 0 # Stop to attack
                    
                    # Aim
                    direction = 1 if self.target.stack.left > self.stack.left else -1
                    self._flip_sprite_x(direction)
                    
                    # Decide Attack
                    self.states.attack_phase = random.choice([1, 2])
                    self.attack()
                    await asyncio.sleep(ATK_DELAY)
                    self._toggle_atk_hb_border()
                    continue
                else: 
                    self.is_idling = True
            
            # ? Simple idle mechanic
            if self.is_idling:
                if self._rnd_dx == 0:
                    if random.randint(1, 20) > 19:
                        self._rnd_dx = random.choice([-1, 1]) * self.stats.movement_speed
                else:
                    if random.randint(1, 20) > 15: self._rnd_dx = 0
                    else: dx += self._rnd_dx
            
            self._check_movement(dx)
            if dx != 0: self._flip_sprite_x(dx)
            await asyncio.sleep(MV_DELAY)