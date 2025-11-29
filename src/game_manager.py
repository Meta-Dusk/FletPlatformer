import flet as ft
import asyncio, random

from audio.audio_manager import AudioManager
from audio.music_data import MusicLibrary
from components.lups_counter import LupsCounter
from utilities.keyboard_manager import held_keys, start as km_start
from utilities.tasks import attempt_cancel
from entities.player import Player
from entities.enemy import Enemy, EnemyType
from entities.entity import Entity
from bg_loops import light_mv_loop, stage_panning_loop
from backgrounds import bg_image_forest

music = MusicLibrary()

class GameManager:
    """Central hub for the game UI and states."""
    def __init__(self, page: ft.Page):
        # State Variables (References)
        self.page: ft.Page = page
        self.player: Player = None
        self.audio_manager: AudioManager = None
        self.background_stack: ft.Stack = None
        self.foreground_stack: ft.Stack = None
        self.stage: ft.Stack = None
        self.entity_list: list[Entity] = []
        
        # Task Management
        self.running_tasks: list[asyncio.Task] = []
        
        # World Configuration
        self.ground_level: int = 30
        self.kill_count: int = 0
        self.death_count: int = 0
        self.time: float = 7
    
    async def __call__(self):
        """An alternative way to get the main entry point."""
        await self.initialize()
    
    async def initialize(self):
        """The entry point called by Flet."""
        # --- Setup ---
        self.audio_manager = AudioManager(debug=False)
        self.audio_manager.initialize()
        self.audio_manager.play_music(music.ambience.forest)
        km_start()
        await self._setup_ui()
        
        # --- Event Handlers ---
        self.page.on_keyboard_event = self._on_keyboard_event
        
        # --- Start Loops ---
        self.start_tasks()
    
    def _safe_update(self, ctrl: ft.Control):
        try: ctrl.update()
        except RuntimeError: pass
    
    async def _setup_ui(self):
        """Initializes Player, Stacks, and HUD."""
        # Stacks/Layers
        self.background_stack = ft.Stack(expand=True)
        self.foreground_stack = ft.Stack(expand=True)
        self.entity_stack = ft.Stack(expand=True)
        self.ui_stack = ft.Stack(expand=True)
        self.day_night_overlay = ft.Container(
            bgcolor=ft.Colors.with_opacity(0.0, ft.Colors.BLACK), expand=True,
            animate=ft.Animation(5000, ft.AnimationCurve.LINEAR)
        )
        
        def bg_forest(index: int): return bg_image_forest(index, self.page)
        
        for i in range(1, 7): self.background_stack.controls.append(bg_forest(i))
        self.background_stack.controls.append(bg_forest(9))
        self.foreground_stack.controls.extend([bg_forest(8), bg_forest(10)])
        
        # Buttons / HUD
        death_btn = ft.Button("KYS", ft.Icons.PERSON_OFF, on_click=self._player_die)
        damage_btn = ft.Button("Take Damage", ft.Icons.PERSONAL_INJURY, on_click=self._player_damage)
        revive_btn = ft.Button("Revive", ft.Icons.PERSON_OUTLINE, on_click=self._player_revive)
        directional_audio_btn = ft.Switch(
            adaptive=True, label="Directional Audio",
            value=self.audio_manager.directional_sfx,
            on_change=self._da_btn_on_change
        )
        self.show_border_sw = ft.Switch(
            adaptive=True, label="Show Bounding Boxes",
            value=False, on_change=self._sb_btn_on_change
        )
        spawn_gobby_btn = ft.Button("Spawn Gobby", ft.Icons.PERSON_ADD, on_click=lambda _: self.summon_gobby(1))
        buttons_row = ft.Row(
            controls=[
                ft.Container(revive_btn, padding=16),
                ft.Container(death_btn, padding=16),
                ft.Container(damage_btn, padding=16),
                ft.Container(directional_audio_btn, padding=16),
                ft.Container(self.show_border_sw, padding=16),
                ft.Container(spawn_gobby_btn, padding=16),
            ], alignment=ft.MainAxisAlignment.CENTER, top=0, left=40
        )
        
        self.ui_stack.controls.extend([buttons_row, LupsCounter(top=10, right=10)])
        
        # Composition
        self.stage = ft.Stack(
            controls=[
                self.background_stack,
                self.entity_stack,
                self.foreground_stack,
                ft.TransparentPointer(self.day_night_overlay),
                self.ui_stack,
            ], expand=True
        )
        
        # Player
        self.player = NewPlayer(self)
        
        await self.page.window.center()
        self.page.add(self.stage)
        
    # * === Event Handlers ===
    def _da_btn_on_change(self, e: ft.ControlEvent): self.audio_manager.directional_sfx = e.data
    def _sb_btn_on_change(self, e: ft.ControlEvent):
        for entity in self.entity_list:
            entity.toggle_show_border(e.data)
            entity._atk_hb_show = e.data
    
    async def _player_die(self, _): await self.player.death()
    async def _player_revive(self, _): await self.player.revive()
    async def _player_damage(self, _): await self.player.take_damage(5)
    
    async def _on_keyboard_event(self, e: ft.KeyboardEvent):
        match e.key:
            case " ": self.player.jump()
            case "V": self.player.attack()
            case "Escape": await self.page.window.close()
            case "`":
                self.time += 1
                print(f"Time is now: {self.time}")
                await self.set_time_of_day(self.time)
    
    # * === EVENTS ===
    async def set_time_of_day(self, hour: float):
        TIME_SENSITIVE_LAYERS = {5, 7}
        LIGHT_LAYERS = {3, 6}
        
        # 1. Determine Target State based on Hour
        if 6 <= hour <= 18:
            is_day = True
            target_overlay_opacity = 0.0 # Clear
            overlay_color = ft.Colors.INDIGO_900
        else:
            is_day = False
            target_overlay_opacity = 0.6 # Dark
            overlay_color = ft.Colors.BLACK
            
        # 2. "The Curtain" - Fade to full darkness to hide the asset swap
        # We temporarily change the animation speed to be faster for the transition
        self.day_night_overlay.animate = ft.Animation(1500, ft.AnimationCurve.EASE_IN)
        self.day_night_overlay.bgcolor = ft.Colors.with_opacity(1.0, ft.Colors.BLACK)
        self.day_night_overlay.update()

        # Wait for the darkness to fully cover the screen
        await asyncio.sleep(1.6)

        # 3. Swap Assets (Hidden behind the curtain)
        for bg in self.background_stack.controls:
            if not isinstance(bg, ft.Image): continue

            # Swap Trees (Texture Change)
            if bg.data in TIME_SENSITIVE_LAYERS:
                if is_day:
                    # Switch to Day variant
                    bg.src = f"images/backgrounds/night_forest/{bg.data}.png"
                else:
                    # Switch to Night variant
                    if "-dark" not in bg.src:
                        bg.src = f"images/backgrounds/night_forest/{bg.data}-dark.png"
                bg.update()
            
            # Toggle Lights (Opacity Change)
            # Since we added 'animate_opacity' in Step 1, this will fade nicely
            elif bg.data in LIGHT_LAYERS:
                bg.opacity = 1 if is_day else 0
                bg.update()

        # 4. Fade to Target (Reveal the new world)
        # Slow down the animation for a gentle reveal
        self.day_night_overlay.animate = ft.Animation(3000, ft.AnimationCurve.EASE_OUT)
        self.day_night_overlay.bgcolor = ft.Colors.with_opacity(target_overlay_opacity, overlay_color)
        self.day_night_overlay.update()
    
    def summon_gobby(self, spawn_amount: int = None, center_spawn: bool = False):
        """Summons a random gobby."""
        def rnd_name():
            names = ["Gobby", "Gibby", "Geeb", "Goob", "Gubby", "Gebby", "Gub", "Gerald", "Gibby", "Gib",
                     "Gob", "Gobber", "Gob Lin", "Gob Gob", "Geb Geb", "Gub Gub", "Gib Gib", "Gibba", "Gibber"]
            return random.choice(names)
        
        if spawn_amount is None: spawn_amount = random.randint(1, 5)
        elif spawn_amount == 0: return
        else: spawn_amount = abs(spawn_amount)
        for _ in range(spawn_amount): NewGoblin(game_manager=self, name=rnd_name(), center_spawn=center_spawn)
    
    # * === TASK MANAGEMENT ===
    def start_tasks(self):
        """Starts background loops."""
        async def run_light(): await light_mv_loop(self.background_stack)
        async def run_pan():
            await stage_panning_loop(
                self.background_stack,
                self.foreground_stack,
                self.page,
                self.player,
                self.entity_list,
                self.stage,
                self.summon_gobby
            )
            
        # Store tasks so we can cancel them later
        self.running_tasks.append(self.page.run_task(run_light))
        self.running_tasks.append(self.page.run_task(run_pan))
        
    def cleanup(self):
        """Call this when exiting or changing levels."""
        for task in self.running_tasks: attempt_cancel(task)

class GameManagerMixin:
    """Mixin to bridge GameManager data into Entities."""
    def _configure_from_manager(self: Entity, game_manager: GameManager):
        """Run this **BEFORE** `super().__init__()` to setup attributes."""
        self.game_manager = game_manager
        self._atk_hb_show = self.game_manager.show_border_sw.value
        self._entity_list = self.game_manager.entity_list
    
    @property
    def ground_level(self) -> int: return self.game_manager.ground_level
    
    def _get_base_kwargs(self, debug: bool):
        """Helper for common init arguments."""
        return {
            "page": self.game_manager.page,
            "audio_manager": self.game_manager.audio_manager,
            "entity_list": self.game_manager.entity_list,
            "debug": debug
        }
        
    def _spawn_into_scene(self: Entity, **call_kwargs):
        """
        Run this **AFTER** `super().__init__()` to add to the game world.
        
        Args:
            game_manager: The `GameManager` instance.
            **call_kwargs: Arguments passed to `self.__call__()` (i.e., `center_spawn=True`)
        """
        if not isinstance(self, Entity):
            print("Class instance is not an Entity!")
            return
        
        # Apply visual settings that required the stack to exist
        self.toggle_show_border(self.game_manager.show_border_sw.value)
        self._atk_hb_show = self.game_manager.show_border_sw.value
        
        # Add to Logic List (if not already there)
        if self not in self.game_manager.entity_list: self.game_manager.entity_list.append(self)
        
        # Add to Visual Stack
        # ? This calls self.__call__(**kwargs), getting the control and starting loops
        self.game_manager.entity_stack.controls.append(self.__call__(**call_kwargs))
        
class NewGoblin(Enemy, GameManagerMixin):
    """Wrapped `Enemy` class to be used in the `GameMaker` class."""
    def __init__(
        self, game_manager: GameManager, name: str,
        *, center_spawn: bool = True, debug = False
    ):
        self._configure_from_manager(game_manager)
        super().__init__(
            type=EnemyType.GOBLIN,
            target=game_manager.player,
            name=name,
            **self._get_base_kwargs(debug)
        )
        self._spawn_into_scene(center_spawn=center_spawn)

class NewPlayer(Player, GameManagerMixin):
    """Wrapped `Player` class to be used in the `GameMaker` class."""
    def __init__(
        self, game_manager: GameManager, *, debug = False
    ):
        self._configure_from_manager(game_manager)
        super().__init__(
            held_keys=held_keys,
            **self._get_base_kwargs(debug)
        )
        self._spawn_into_scene()