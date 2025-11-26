import asyncio, random
import flet as ft
from dataclasses import dataclass
from enum import Enum

from entities.entity import Entity, EntityStates, EntityStats, Factions
from images import Sprite
from audio.audio_manager import AudioManager
from audio.sfx_data import SFXLibrary
from utilities.tasks import attempt_cancel
from utilities.collisions import is_in_range, check_collision

sfx = SFXLibrary()

@dataclass
class EnemyData:
    name: str
    width: ft.Number
    height: ft.Number
    melee_range: int = 100

class EnemyType(Enum):
    """Available enemy types."""
    # TODO: Finish processing the other enemy assets
    # FLYING_EYE = EnemyData("Flying Eye", 150, 150)
    GOBLIN = EnemyData("Gobby", 150, 150)
    # MUSHROOM = EnemyData("Mushy", 150, 150)
    # SKELETON = EnemyData("Skelly", 150, 150)

# TODO: Finish the Enemy class
class Enemy(Entity):
    """Handles an enemy's actions and states."""
    def __init__(
        self, type: EnemyType, page: ft.Page,
        audio_manager: AudioManager, target: Entity = None,
        *, debug: bool = False
    ):
        self._enemy_name = type.name.lower()
        _sprite = Sprite(
            src=f"images/enemies/{self._enemy_name}/idle_0.png",
            width=type.value.width, height=type.value.height
        )
        self.name = type.value.name
        super().__init__(
            sprite=_sprite, name=self.name, page=page,
            audio_manager=audio_manager, faction=Factions.NONHUMAN,
            debug=debug, stats=EntityStats(movement_speed=12)
        )
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
    
    # * === DAMAGE DETECTION ===
    async def _detect_damage(self):
        """Handles the looping for check for taking damage."""
        while not self.states.dead:
            if self.target and self.target.states.dealing_damage:
                if check_collision(
                    self.stack.left, self.stack.bottom, self.sprite.width, self.sprite.height,
                    self.target.stack.left, self.target.stack.bottom, self.target.sprite.width, self.target.sprite.height
                ): await self.take_damage(self.target.stats.attack_damage)
            await asyncio.sleep(0.1)
    
    def _start_damage_detection_loop(self):
        """Starts the loop for detecting damage."""
        self._damage_detection_task = self.page.run_task(self._detect_damage)
    
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
        # await asyncio.sleep(1)
        while not self.states.dead:
            if self.states.disable_movement or self.states.disable_movement:
                self.states.is_moving = False
                await asyncio.sleep(0.1)
                continue
            
            current_scale_x = self.sprite.scale.scale_x if hasattr(self.sprite.scale, "scale_x") else self.sprite.scale
            start_facing_sign = 1 if current_scale_x > 0 else -1
            dx, dy = 0, 0
            
            if not self._is_player_in_range():
                if self.target and not self.target.states.dead: # ? Chase
                    self._debug_msg(f"Chasing {self.target.name}", end=" -> ")
                    if self.target.stack.left > self.stack.left: dx = self.stats.movement_speed
                    elif self.target.stack.left < self.stack.left: dx = -self.stats.movement_speed
                    self.is_idling = False
                else: self.is_idling = True
                
            else: # ? Attack
                if self.target and not self.target.states.dead:
                    self._debug_msg("Attacking player")
                    self.attack()
                    await asyncio.sleep(1)
                    continue
                else: self.is_idling = True
            
            if dx != 0 or dy != 0:
                self._debug_msg(f"Moving with: ({dx}, {dy})")
                self.stack.left += dx
                self.stack.bottom += dy
                
                self.states.is_moving = True
                desired_sign = start_facing_sign
                if dx > 0: desired_sign = 1
                elif dx < 0: desired_sign = -1
                
                has_flipped = False
                if desired_sign != start_facing_sign:
                    new_scale = abs(current_scale_x) * desired_sign
                    self.sprite.scale = ft.Scale(scale_x=new_scale, scale_y=self.sprite.scale.scale_y)
                    has_flipped = True
                
                if has_flipped: self.sprite.try_update()
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
            self.sprite.change_src(self._get_spr_path(prefix, i))
            if i == 5 and self.type == EnemyType.GOBLIN: self._play_sfx(sfx.enemy.boggart_hya)
            if i == 6: self.states.dealing_damage = True
            else: self.states.dealing_damage = False
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
        self.states.taking_damage = False
        self._take_hit_task = None
    
    # * === CALLABLE PLAYER ACTIONS/EVENTS ===
    def __call__(self, *, start_loops: bool = True, center_spawn: bool = True):
        if not center_spawn:
            new_left = random.randint(0, int(self.page.width))
            new_left -= self.sprite.width / 2
            self.stack.left = new_left
        if start_loops:
            self._start_animation_loop()
            self._start_movement_loop()
            self._start_damage_detection_loop()
        return super().__call__()
    
    async def death(self):
        """Cancels all running tasks, and plays the death animation."""
        if not super().death(): return
        # ? Death states and stats
        self._debug_msg(f"{self.name} has died!")
        self._reset_states(EntityStates(dead=True))
        self._reset_stats(EntityStats(health=0))
        await self._update_health_bar()
        
        # ? Animation handling
        attempt_cancel(self._animation_loop_task)
        self._cancel_temp_tasks()
        await self._death_anim()
        await asyncio.sleep(1) # A bit of delay before despawning
        
        # ? Despawn and cleanup
        self.stack.opacity = 0
        self._safe_update(self.stack)
        await asyncio.sleep(self.stack.animate_opacity.duration / 1000)
        stage = self._get_parent()
        
        self._debug_msg(f"Attempting to remove self from stage: {len(stage.controls)} -> ", end="")
        stage.controls.remove(self.stack)
        self._debug_msg(len(stage.controls), include_handler=False)
        
        self._debug_msg(f"Attempting to remove self from _entity_list: {len(self._entity_list)} -> ", end="")
        if self._entity_list is not None: self._entity_list.remove(self)
        self._debug_msg(len(self._entity_list), include_handler=False)
        
        self._safe_update(stage)
        self._reset_states()
        self._reset_stats()
        self._cancel_loop_tasks()
        
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
        self._attack_task = self.page.run_task(self._attack_anim)
    
    async def take_damage(self, damage_amount: float):
        """Decrease enemy's health with logic."""
        if not super().take_damage(): return
        self._debug_msg(f"Took damage: {damage_amount}, health is now: {self.stats.health} -> ", end="")
        self.stats.health -= damage_amount
        self._debug_msg(self.stats.health, include_handler=False)
        self.states.taking_damage = True
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
    
    def _get_parent(self):
        """Returns the stack's parent, and assumes it's also a `Stack`."""
        parent: ft.Stack = self.stack.parent
        return parent


# * Test for the Enemy class; a simple implementation
# ? Run with: uv run py -m src.entities.enemy
def test(page: ft.Page):
    page.title = "Enemy Class Test"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 0
    
    audio_manager = AudioManager()
    
    async def on_death(_): await enemy.death()
    async def on_damage(_): await enemy.take_damage(5)
    async def on_attack(_): enemy.attack()
    
    attack_btn = ft.Button("Attack", on_click=on_attack)
    death_btn = ft.Button("Death", on_click=on_death)
    damage_btn = ft.Button("Take Damage", on_click=on_damage)
    buttons_row = ft.Row(controls=[attack_btn, death_btn, damage_btn], left=60, top=30)
    
    player_spr = Sprite("images/player/idle_0.png", width=180, height=180)
    dummy_player = Entity(player_spr, "Hero", page, audio_manager)
    dummy_player.faction = Factions.HUMAN
    dummy_player.stack.left += 150
    enemy = Enemy(EnemyType.GOBLIN, page, audio_manager, dummy_player, debug=True)
    
    stage = ft.Stack(controls=[dummy_player(), enemy(), buttons_row], expand=True)
    dummy_player._start_movement_loop()
    
    page.add(stage)
    
if __name__ == "__main__":
    ft.run(test, assets_dir="../assets")