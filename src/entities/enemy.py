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
        audio_manager: AudioManager,
        target: Entity = None,
        *, debug: bool = False
    ):
        self.target = target
        self._enemy_name = type.name.lower()
        _sprite = Sprite(
            src=f"images/enemies/{self._enemy_name}/idle_0.png",
            width=type.value.width, height=type.value.height
        )
        self.name = type.value.name
        self._handler_str = self.name
        super().__init__(
            sprite=_sprite, name=self.name, page=page,
            audio_manager=audio_manager, faction=Factions.NONHUMAN,
            debug=debug
        )
        # ? No jump sprites available
        self._attack_task: asyncio.Task = None
        self._take_hit_task: asyncio.Task = None
        self._animation_loop_task: asyncio.Task = None
        self.is_idling: bool = False
        self.melee_range: int = type.value.melee_range
        self._cached_player_stack = None
    
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
            else: # Idle animation
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
        await asyncio.sleep(2)
        while not self.states.dead:
            if self.states.is_attacking or self.states.disable_movement:
                self.states.is_moving = False
                await asyncio.sleep(1)
                continue
            
            dx, dy = 0, 0
            if not self._is_player_in_range(): # ? Chase
                if self.target.stack.left > self.stack.left: dx = self.stats.movement_speed
                elif self.target.stack.left < self.stack.left: dx = -self.stats.movement_speed
            else: # ? Attack
                self._debug_msg("Attacking player")
                self.attack()
                await asyncio.sleep(1)
                continue
            self._debug_msg(f"Moving with: ({dx}, {dy})")
            self.stack.left += dx
            self.stack.bottom += dy
            
            if dx != 0 or dy != 0:
                self.states.is_moving = True
                # self.sprite.scale.scale_x = 2 if dx > 0 else -2
                if ( # ? Manages asset flip direction
                    (dx > 0 and self.sprite.scale.scale_x < 0) or
                    (dx < 0 and self.sprite.scale.scale_x > 0)
                ): self.sprite.flip_x()
            
            if self.states.is_moving or self.states.is_falling: self._safe_update(self.stack)
            await asyncio.sleep(0.1)
        
    
    # * === ONE-SHOT ANIMATIONS ===
    async def _attack_anim(self):
        """Handles the enemy's attack animations with combos."""
        prefix = "attack-main" if self.states.attack_phase == 1 else "attack-secondary"
        for i in range(8):
            await asyncio.sleep(0.1)
            self.sprite.change_src(self._get_spr_path(prefix, i))
        self.states.is_attacking = False
        self._attack_task = None
    
    async def _death_anim(self):
        """Handles the enemy's death animation."""
        for i in range(4):
            await asyncio.sleep(0.1)
            self.sprite.change_src(self._get_spr_path("death", i))
        self.states.revivable = True
    
    async def _take_hit_anim(self):
        """Handles the enemy's taking damage animation."""
        for i in range(4):
            await asyncio.sleep(0.1)
            self.sprite.change_src(self._get_spr_path("take-hit", i))
        self.states.taking_damage = False
        self._take_hit_task = None
    
    # * === CALLABLE PLAYER ACTIONS/EVENTS ===
    def __call__(self, start_loops: bool = True):
        if start_loops:
            self._start_animation_loop()
            self._start_movement_loop()
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
        self._debug_msg(f"Attempting to remove Gobby from stage: {len(stage.controls)} -> ", end="")
        stage.controls.remove(self.stack)
        self._safe_update(stage)
        self._debug_msg(len(stage.controls), include_handler=False)
        
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
    
    def _is_player_in_range(self):
        """Checks if the specifically targeted player is in range."""
        if self.target is None: return False
        if self.target.states.dead: return False
        
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
        stack.opacity = 1
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
    
    attack_btn = ft.Button("Attack", on_click=lambda _: enemy.attack())
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