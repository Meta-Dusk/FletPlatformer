import asyncio, random
import flet as ft
from dataclasses import dataclass
from enum import Enum

from entities.entity import Entity, EntityStates, EntityStats, Factions
from images import Sprite
from audio.audio_manager import AudioManager
from audio.sfx_data import SFXLibrary
from utilities.tasks import attempt_cancel
from utilities.collisions import is_in_range

sfx = SFXLibrary()

@dataclass
class EnemyData:
    name: str = "Unknown Enemy"
    width: ft.Number = 150
    height: ft.Number = 150
    melee_range: int = 100

class EnemyType(Enum):
    """Available enemy types."""
    # TODO: Finish processing the other enemy assets
    # FLYING_EYE = EnemyData("Flying Eye")
    GOBLIN = EnemyData("Gobby")
    # MUSHROOM = EnemyData("Mushy")
    # SKELETON = EnemyData("Skelly")

# TODO: Finish the Enemy class
class Enemy(Entity):
    """Handles an enemy's actions and states."""
    def __init__(
        self, type: EnemyType, page: ft.Page,
        audio_manager: AudioManager, target: Entity = None,
        name: str = None, *, debug: bool = False
    ):
        """
        Important setup for the class. Starts setup with the
        parent class first before its internal setup.
        """
        # ? Entity inherited class setup
        self._enemy_name = type.name.lower()
        _sprite = Sprite(
            src=f"images/enemies/{self._enemy_name}/idle_0.png",
            width=type.value.width, height=type.value.height
        )
        self.name = type.value.name if name is None else name
        super().__init__(
            sprite=_sprite, name=self.name, page=page,
            audio_manager=audio_manager, faction=Factions.NONHUMAN,
            debug=debug, stats=EntityStats(movement_speed=12)
        )
        
        # ? Internal class setup
        self.type = type
        self.target = target
        self._handler_str = self.name
        self._attack_task: asyncio.Task = None
        self._take_hit_task: asyncio.Task = None
        self._animation_loop_task: asyncio.Task = None
        self.is_idling: bool = False
        self.melee_range: int = type.value.melee_range
        self._cached_player_stack = None
        self._damage_detection_task: asyncio.Task = None
        self._rnd_dx: int = 0
        self._make_atk_hitbox(
            p1_r_left=-15, p1_width=180, p1_height=100,
            p2_r_left=70, p2_width=140, p2_height=80
        )
        self._make_self_hitbox(width=70, height=75, r_left=40, bottom=0)
    
    # * === LOOPING ANIMATIONS ===
    async def _animation_loop(self):
        """Handles an enemy's different animation loops."""
        index: int = 0
        while not self.states.dead:
            # Give way to other animations
            if self.states.is_attacking or self.states.taking_damage or self.states.dead:
                await asyncio.sleep(0.1) # ? Important logic delay
                continue
            
            # Running animation
            if self.states.is_moving:
                if index > 7: index = 0
                await asyncio.sleep(0.075)
                self.sprite.change_src(self._get_spr_path("run", index))
                if index == 2: self._play_sfx(sfx.footsteps.footstep_grass_1, 0.2)
                if index == 5: self._play_sfx(sfx.footsteps.footstep_grass_1, 0.2)
             
             # Idle animation
            else:
                if index > 3: index = 0
                await asyncio.sleep(0.1)
                self.sprite.change_src(self._get_spr_path("idle", index))
            
            index += 1
    
    def _start_animation_loop(self):
        """Starts the animation loop and stores it in a variable."""
        self._animation_loop_task = self.page.run_task(self._animation_loop)
    
    # * === CUSTOM MOVEMENT LOOP ===
    async def _movement_loop(self):
        """Handles the enemy's movements."""
        await asyncio.sleep(0.1)
        self.stack.opacity = 1
        self._safe_update(self.stack)
        await asyncio.sleep(round(self.stack.animate_opacity.duration / 1000, 3))
        self.is_idling = True
        self._play_sfx(sfx.enemy.goblin_cackle)
        wait_time = round(random.randint(2000, 4000) / 1000, 3)
        self._debug_msg(f"Idling for {wait_time}")
        await asyncio.sleep(wait_time - 2.0)
        self.is_idling = False
        
        while not self.states.dead:
            if self.states.disable_movement or self.states.disable_movement:
                self.states.is_moving = False
                await asyncio.sleep(0.1)
                continue
            
            dx, dy = 0, 0
            
            if not self._is_player_in_range():
                if self.target and not self.target.states.dead: # ? Chase Player (if out of range)
                    self._debug_msg(f"Chasing {self.target.name}", end=" -> ")
                    if self.target.stack.left > self.stack.left: dx = self.stats.movement_speed
                    elif self.target.stack.left < self.stack.left: dx = -self.stats.movement_speed
                    self.is_idling = False
                else: self.is_idling = True
                
            else: # ? Attack Player (if in range)
                if self.target and not self.target.states.dead:
                    self._debug_msg("Attacking player")
                    self.attack()
                    await asyncio.sleep(1)
                    continue
                else: self.is_idling = True
            
            if self.is_idling:
                if self._rnd_dx == 0:
                    if random.randint(1, 10) > 9:
                        self._rnd_dx = random.randint(-1, 1) * self.stats.movement_speed
                else:
                    if random.randint(1, 10) > 7: self._rnd_dx = 0
                    else: dx += self._rnd_dx
            
            if dx != 0 or dy != 0:
                self.states.is_moving = True
                self._debug_msg(f"Moving with: ({dx}, {dy})")
                
                self.stack.left += dx
                self.stack.bottom += dy
                
                if self._flip_sprite_x(dx):
                    self._flip_atk_hb()
                    self._flip_self_hb()
            else: self.states.is_moving = False
            if self.states.is_moving:
                self.states.dealing_damage = False
                self._safe_update(self.stack)
            await asyncio.sleep(0.05)
        
    
    # * === ONE-SHOT ANIMATIONS ===
    async def _attack_anim(self):
        """Handles the enemy's attack animations with combos."""
        prefix = "attack-main" if self.states.attack_phase == 1 else "attack-secondary"
        for i in range(8):
            await asyncio.sleep(0.1)
            if self.states.attack_phase == 1:
                if i == 6: self._modify_self_hitbox(width=80, height=80, r_left=10)
            elif self.states.attack_phase == 2:
                if i == 0: self._modify_self_hitbox(r_left=30)
                elif i == 1: self._modify_self_hitbox(r_left=0)
                elif i == 2: self._modify_self_hitbox(r_left=-5, height=60)
                elif i == 5: self._modify_self_hitbox(r_left=50, height=60)
            if i == 5: self._play_sfx(sfx.enemy.boggart_hya)
            if i == 6:
                self.states.dealing_damage = True
                self._toggle_atk_hb_border()
            else:
                self.states.dealing_damage = False
                self._toggle_atk_hb_border()
            self.sprite.change_src(self._get_spr_path(prefix, i))
        self._modify_self_hitbox(reset=True)
        self.states.is_attacking = False
        self._attack_task = None
    
    async def _death_anim(self):
        """Handles the enemy's death animation."""
        if self.type == EnemyType.GOBLIN:
            self._play_sfx(sfx.enemy.goblin_scream)
            self._play_sfx(sfx.impacts.flesh_impact_2)
        for i in range(4):
            await asyncio.sleep(0.1)
            self.sprite.change_src(self._get_spr_path("death", i))
        self.states.revivable = True
    
    async def _take_hit_anim(self):
        """Handles the enemy's taking damage animation."""
        for i in range(4):
            await asyncio.sleep(0.1)
            self.sprite.change_src(self._get_spr_path("take-hit", i))
            if i == 1 and self.type == EnemyType.GOBLIN:
                self._play_sfx(sfx.enemy.goblin_hurt)
                if self.target.states.attack_phase == 1: self._play_sfx(sfx.impacts.flesh_impact_1)
                if self.target.states.attack_phase == 2: self._play_sfx(sfx.impacts.axe_hit_flesh)
            if i == 2: self._knockback_self(self.target)
        self.states.taking_damage = False
        self._take_hit_task = None
    
    # * === CLEANUP ===
    def remove_selves(self):
        """Removes `self` from `stage` and `_entity_list`."""
        stage = self._get_parent()
        
        self._debug_msg(f"Attempting to remove self from stage: {len(stage.controls)} -> ", end="")
        if self in stage.controls: stage.controls.remove(self.stack)
        self._debug_msg(len(stage.controls), include_handler=False)
        
        self._debug_msg(f"Attempting to remove self from _entity_list: {len(self._entity_list)} -> ", end="")
        if self._entity_list is not None and self in self._entity_list: self._entity_list.remove(self)
        self._debug_msg(len(self._entity_list), include_handler=False)
    
    # * === CALLABLE PLAYER ACTIONS/EVENTS ===
    def __call__(self, *, start_loops: bool = True, center_spawn: bool = True):
        if not center_spawn:
            new_left = random.randint(0, int(self.page.width))
            new_left -= self.sprite.width / 2
            self.stack.left = new_left
        if start_loops:
            self._start_animation_loop()
            self._start_movement_loop()
        return super().__call__()
    
    async def death(self):
        """Cancels all running tasks, and plays the death animation."""
        if not super().death(): return
        # ? Death states and stats
        self._reset_states(EntityStates(dead=True))
        self._reset_stats(EntityStats(health=0))
        self._debug_msg(f"{self.name} has died!")
        await self._update_health_bar()
        
        # ? Animation handling
        attempt_cancel(self._animation_loop_task)
        self._cancel_temp_tasks()
        await self._death_anim()
        self.states.revivable = True
        await asyncio.sleep(1) # A bit of delay before despawning
        
        # ? Despawn and cleanup
        self.states.revivable = False
        self.stack.opacity = 0
        self._safe_update(self.stack)
        await asyncio.sleep(self.stack.animate_opacity.duration / 1000)
        self._cancel_loop_tasks()
        self._cleanup_ready = True
        
    def attack(self):
        """
        Enemy attack. Melee combo cycles: 1 -> 2 -> 1.
        Ranged attack based on distance to player.
        """
        if not super().attack(): return
        self.states.attack_phase += 1
        if self.states.attack_phase > 2: self.states.attack_phase = 1
        self._debug_msg(f"Attacking! Phase: {self.states.attack_phase}")
        self.states.is_attacking = True
        self.states.dealing_damage = False
        self._attack_task = self.page.run_task(self._attack_anim)
    
    async def take_damage(self, damage_amount: float):
        """Decrease enemy's health with logic."""
        if not super().take_damage(): return
        self._toggle_atk_hb_border()
        self.stats.health -= damage_amount
        self._debug_msg(f"HP: {self.stats.health}/{self.stats.max_health}(-{damage_amount})")
        self.states.taking_damage = True
        self.states.dealing_damage = False
        self.states.is_moving = False
        if self.states.is_attacking:
            attempt_cancel(self._attack_task)
            self.states.is_attacking = False
            self._safe_update(self.stack)
        if self.stats.health <= 0: await self.death()
        else: self._take_hit_task = self.page.run_task(self._take_hit_anim)
        await self._update_health_bar()
    
    # * === OTHER HELPERS ===
    def _cancel_temp_tasks(self):
        """Cancels all running temporary tasks."""
        tasks = [
            self._attack_task,
            self._take_hit_task
        ]
        for task in tasks: attempt_cancel(task)
    
    def _cancel_loop_tasks(self):
        """Cancels all running looping tasks."""
        tasks = [
            self._movement_loop_task,
            self._damage_detection_task
        ]
        for task in tasks: attempt_cancel(task)
    
    def _is_player_in_range(self):
        """Checks if the specifically targeted player is in range."""
        if self.target is None: return False
        
        # We assume the target (Player) has a sprite and stack
        p_w = self.target.sprite.width
        p_h = self.target.sprite.height
        
        return is_in_range(
            entity1_stack=self.stack, 
            entity1_w=self.sprite.width, 
            entity1_h=self.sprite.height,
            entity2_stack=self.target.stack, 
            entity2_w=p_w, 
            entity2_h=p_h,
            threshold=self.melee_range
        )
        
    # * === COMPONENT METHODS ===
    def _make_stack(self):
        stack = super()._make_stack()
        stack.animate_opacity = ft.Animation(2000, ft.AnimationCurve.EASE_IN_OUT)
        stack.opacity = 0
        return stack


# * Test for the Enemy class; a simple implementation
# ? Run with: uv run py -m src.entities.enemy
def test(page: ft.Page):
    page.title = "Enemy Class Test"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 0
    
    audio_manager = AudioManager()
    audio_manager.initialize()
    
    async def on_death(_): await enemy.death()
    async def on_damage(_): await enemy.take_damage(5)
    def on_player(_): dummy_player.states.dead = not dummy_player.states.dead
    
    attack_btn = ft.Button("Attack", on_click=lambda _: enemy.attack())
    death_btn = ft.Button("Death", on_click=on_death)
    damage_btn = ft.Button("Take Damage", on_click=on_damage)
    toggle_player_btn = ft.Button("Toggle Player", on_click=on_player)
    buttons_row = ft.Row(
        controls=[attack_btn, death_btn, damage_btn, toggle_player_btn],
        left=60, top=30
    )
    
    player_spr = Sprite("images/player/idle_0.png", width=180, height=180)
    dummy_player = Entity(player_spr, "Hero", page, audio_manager, Factions.HUMAN)
    dummy_player.stack.left += 200
    enemy = Enemy(EnemyType.GOBLIN, page, audio_manager, dummy_player, debug=True)
    enemy.toggle_show_border(True)
    enemy._atk_hb_show = True
    
    stage = ft.Stack(
        controls=[
            dummy_player(),
            enemy(),
            buttons_row
        ],
        expand=True
    )
    # dummy_player._start_movement_loop()
    
    page.add(stage)
    
if __name__ == "__main__":
    ft.run(test, assets_dir="../assets")