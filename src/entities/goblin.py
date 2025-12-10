import flet as ft
import random, asyncio

from entities.enemy import Enemy, EnemyType, get_inversely_scaling_stats
from entities.entity import Entity, EntityStats
from audio.audio_manager import AudioManager
from audio.sfx_data import SFXLibrary
from utilities.components import try_update, await_for_dur

sfx = SFXLibrary()

class Goblin(Enemy):
    """A preset `Enemy` class specifically for the Goblin enemy type."""
    def __init__(
        self, page: ft.Page = None, audio_manager: AudioManager = None,
        target: Enemy = None, name: str = None, entity_list: list[Entity] = None,
        *, debug: bool = False
    ) -> None:
        if name is None: name = self.generate_rnd_name()
        
        # Random stats
        rnd_health_range = (10, 20)
        min_mv_speed = 10
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
            name=name, entity_list=entity_list, debug=debug, stats=custom_stats
        )
        
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
        names = ["Gobby", "Gibby", "Geeb", "Goob", "Gubby", "Gebby", "Gub", "Gerald", "Gibby", "Gib",
                "Gob", "Gobber", "Gob Lin", "Gob Gob", "Geb Geb", "Gub Gub", "Gib Gib", "Gibba", "Gibber",
                "Gob Rin", "Gobrin", "Rin"]
        return random.choice(names)
    
    # * === ONE-SHOT ANIMATIONS ===
    async def _attack_anim(self) -> None:
        """Handles the enemy's attack animations with combos."""
        prefix = f"attack-{self.states.attack_phase}"
        mod_atk_delay = self.stats.attack_frame_delay * 1.5
        FRAMES = 7
        
        for frame in range(FRAMES + 1):
            await asyncio.sleep(mod_atk_delay if self.states.stun_immune else self.stats.attack_frame_delay)
            if self.states.attack_phase == 1:
                # 50% chance of parry
                if frame == 2 and random.randint(1, 2) > 1:
                    self._apply_tint(ft.Colors.YELLOW)
                    self.states.stun_immune = True
                elif frame == 5:
                    self._reset_tint()
                    self.states.stun_immune = False
                elif frame == 6:
                    self._modify_self_hitbox(width=80, height=80, r_left=10)
            elif self.states.attack_phase == 2:
                if frame == 0: self._modify_self_hitbox(r_left=30)
                elif frame == 1: self._modify_self_hitbox(r_left=0)
                elif frame == 2: self._modify_self_hitbox(r_left=-5, height=60)
                elif frame in {2, 3, 4}:
                    if self.target.states.is_attacking: await asyncio.sleep(0.05)
                elif frame == 5: self._modify_self_hitbox(r_left=50, height=60)
                
            if frame == 5: self._play_sfx(sfx.enemy.boggart_hya)
            elif frame == 6:
                self.states.dealing_damage = True
                self._toggle_atk_hb_border()
            elif frame == 7:
                self.states.dealing_damage = False
                self._toggle_atk_hb_border()
            self.sprite.change_src(self._get_spr_path(prefix, frame))
            
        self._modify_self_hitbox(reset=True)
        self.states.is_attacking = False
        self._attack_task = None
        self._toggle_atk_hb_border()
    
    async def _death_anim(self) -> None:
        """Handles the enemy's death animation."""
        FRAMES = 3
        self._update_health_bar()
        self._play_sfx(sfx.enemy.goblin_scream)
        self._play_sfx(sfx.impacts.flesh_impact_2)
        
        for frame in range(FRAMES + 1):
            await asyncio.sleep(self._LOGIC_DELAY)
            self.sprite.change_src(self._get_spr_path("death", frame))
    
    async def _take_hit_anim(self, play_animation: bool = True) -> None:
        """Handles the enemy's taking damage animation."""
        FRAMES: int = 3
        
        for frame in range(FRAMES + 1):
            await asyncio.sleep(self._LOGIC_DELAY)
            if play_animation: self.sprite.change_src(self._get_spr_path("take-hit", frame))
            if frame == 1:
                self._update_health_bar()
                self._play_sfx(sfx.enemy.goblin_hurt)
                if self.target.states.attack_phase == 1: self._play_sfx(sfx.impacts.flesh_impact_1)
                elif self.target.states.attack_phase == 2: self._play_sfx(sfx.impacts.axe_hit_flesh)
            if frame == 2: self._knockback_self(self.target)
            
        self.states.taking_damage = False
        self._take_hit_task = None
        self._reset_tint()
    
    async def _revive_anim(self) -> None:
        """Handles the goblin's revival animation."""
        frame: int = 3
        FRAME_DURATION: float = 0.25
        self._play_sfx(sfx.magic.strike)
        
        while frame >= 0:
            await asyncio.sleep(FRAME_DURATION)
            self.sprite.change_src(self._get_spr_path("death", frame))
            frame -= 1
    
    # * === CUSTOM MOVEMENT LOOP ===
    async def _movement_loop(self) -> None:
        """Handles the goblin's simple AI."""
        # Announce if goblin is spawned in the scene (sfx + fade in)
        await asyncio.sleep(self._LOGIC_DELAY)
        self._play_sfx(sfx.enemy.goblin_cackle)
        self.stack.opacity = 1
        try_update(self.stack)
        await await_for_dur(self.stack.animate_opacity)
        
        while not self.states.dead:
            if self.states.disable_movement:
                self.states.is_moving = False
                await asyncio.sleep(self._LOGIC_DELAY)
                continue
            
            dx, dy = 0, 0
            
            # ? Chase Target (if out of range)
            if not self._is_target_in_range():
                if self.target and not self.target.states.dead:
                    self._debug_msg(f"Chasing {self.target.name}", end=" -> ", debug_handler=self._debug_logs.movement)
                    if self._get_center_point(self.target) > self._get_center_point(self):
                        if self.target.states.dealing_damage:
                            dx = -self.stats.movement_speed
                        else: dx = self.stats.movement_speed
                    elif self._get_center_point(self.target) < self._get_center_point(self):
                        if self.target.states.dealing_damage:
                            dx = self.stats.movement_speed
                        else: dx = -self.stats.movement_speed
                    self.is_idling = False
                else: self.is_idling = True
                
            else: # ? Attack Target (if in range)
                if self.target and not self.target.states.dead:
                    self._debug_msg("Attacking target", debug_handler=self._debug_logs.attack)
                    
                    # Predict target if target is jumping
                    if self.target.states.jumped:
                        if self.target.states.is_attacking:
                            self.states.attack_phase = 0
                        else: self.states.attack_phase = 1
                        if (
                            self._get_center_point(self.target) > self._get_center_point(self) or
                            self._get_center_point(self.target) < self._get_center_point(self)
                        ):
                            self._flip_char(dx)
                    
                    self.attack()
                    await asyncio.sleep(1)
                    continue
                else: self.is_idling = True
            
            # ? Simple idle mechanic
            if self.is_idling:
                if self._rnd_dx == 0:
                    # 10% chance of attempting random movement when idle
                    if random.randint(1, 10) > 9:
                        self._rnd_dx = random.randint(-1, 1) * self.stats.movement_speed
                else:
                    # 30% chance of staying still when idle
                    if random.randint(1, 10) > 7: self._rnd_dx = 0
                    else: dx += self._rnd_dx
            
            self._check_movement(dx, dy)
            if self.states.is_moving:
                self.states.dealing_damage = False
                try_update(self.stack)
            await asyncio.sleep(self._LOGIC_DELAY)
    
    # * === LOOPING ANIMATIONS ===
    async def _animation_loop(self):
        """Handles the goblin's different animation loops."""
        await super()._animation_loop(
            running_frames=7, running_frames_duration=0.075,
            idle_frames=3
        )