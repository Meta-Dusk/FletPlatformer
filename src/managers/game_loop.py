import asyncio, time
import flet as ft

from entities.entity import Entity
from managers.physics import PhysicsManager
from managers.projectiles import ProjectileManager
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
        self.is_running = False
        self._target_fps = 60
        self._tick_rate = 1 / self._target_fps
        self.debug = debug
        
        self.physics_manager = PhysicsManager(page, entity_list)
        self.projectile_manager = ProjectileManager(
            page, audio_manager, entity_list, ground_level, debug=self.debug
        )
    
    @property
    def is_paused(self) -> bool:
        return self._is_paused
    
    @is_paused.setter
    def is_paused(self, is_paused: bool) -> None:
        self._is_paused = is_paused
    
    def start(self):
        if not self.is_running:
            self.is_running = True
            self.page.run_task(self._main_loop)
            
    def stop(self):
        self.is_running = False
        
    async def _main_loop(self):
        last_time = time.time()
        
        while self.is_running:
            # 1. Calculate Delta Time
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time
            
            # Cap dt (Lag prevention)
            if dt > 0.05: dt = 0.05
            
            # 2. Check Pause State
            if self.is_paused:
                await asyncio.sleep(0.1)
                last_time = time.time() # Prevent dt spike when unpausing
                continue
            
            # 3. TICK EVERYTHING (The "Update" Phase)
            
            for entity in self.entity_list[:]:
                entity.update(dt)
            
            # A. Physics (Move Entities & Player)
            if self.physics_manager:
                self.physics_manager.update(dt)
                
            # B. Projectiles (Move Bullets & Check Hits)
            if self.projectile_manager:
                self.projectile_manager.update(dt)
            
            await asyncio.sleep(self._tick_rate)