import asyncio, time
import flet as ft

from entities.entity import Entity

from managers.physics import PhysicsManager
from managers.projectiles import ProjectileManager
from managers.enemy_manager import EnemyManager

from audio.audio_manager import AudioManager

class GameLoop:
    def __init__(
        self,
        page: ft.Page,
        entity_list: list[Entity],
        audio_manager: AudioManager,
        *,
        is_paused: bool = False,
        ground_level: int = 0,
        debug: bool = False
    ) -> None:
        self.page = page
        self.entity_list = entity_list
        self._is_paused = is_paused
        self.is_running: bool = False
        self._target_fps: float = 60
        self._tick_rate: float = 1 / self._target_fps
        self.debug = debug
        
        self.physics_manager = PhysicsManager(page, entity_list)
        self.projectile_manager = ProjectileManager(
            page, audio_manager, entity_list, ground_level, debug=self.debug
        )
        self.enemy_manager = EnemyManager()
    
    @property
    def tick_rate(self) -> float:
        return round(self._tick_rate, 3)
    
    @tick_rate.setter
    def tick_rate(self, target_fps: float) -> None:
        self._target_fps = target_fps
        self._tick_rate = 1 / self._target_fps
    
    @property
    def is_paused(self) -> bool:
        """Pauses the loop if enabled."""
        return self._is_paused
    
    @is_paused.setter
    def is_paused(self, is_paused: bool) -> None:
        self._is_paused = is_paused
    
    def _debug_msg(self, msg: str) -> None:
        print(f"[GameLoop] {msg}")
    
    def start(self):
        """Starts the game loop."""
        if not self.is_running:
            self.is_running = True
            self.page.run_task(self._main_loop)
            self._debug_msg("Starting the main loop!")
            
    def stop(self):
        """Stops the game loop."""
        self.is_running = False
        self._debug_msg("Attempting to stop the game loop.")
        
    async def _main_loop(self):
        """Handles all the ticking logic with delta time."""
        last_time = time.time()
        
        while self.is_running:
            # Calculate Delta Time
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time
            
            # Cap dt (Lag prevention)
            if dt > 0.05: dt = 0.05
            dt = round(dt, 3)
            
            # Check Pause State
            if self.is_paused:
                await asyncio.sleep(0.1)
                last_time = time.time() # Prevent dt spike when unpausing
                continue
            
            # * TICK EVERYTHING (The "Update" Phase)
            # Animations are also handled by the entity's update method
            for entity in self.entity_list[:]:
                entity.update(dt)
            
            # Physics (Move Entities and Player)
            if self.physics_manager:
                self.physics_manager.update(dt)
                
            # Projectiles (Move Bullets and Check Hits)
            if self.projectile_manager:
                self.projectile_manager.update(dt)
            
            await asyncio.sleep(self.tick_rate)
        
        else: # ? This only gets called if the loop stopped naturally
            self._debug_msg("Successfully stopped the game loop!")