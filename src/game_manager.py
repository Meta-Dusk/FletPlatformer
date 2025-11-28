import flet as ft
import asyncio, random

from audio.audio_manager import AudioManager
from audio.music_data import MusicLibrary
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
        # Player
        self.player = Player(self.page, self.audio_manager, held_keys)
        self.player._entity_list = self.entity_list
        self.entity_list.append(self.player)
        
        # Stacks (BG/FG)
        self.background_stack = ft.Stack(expand=True)
        self.foreground_stack = ft.Stack(expand=True)
        self.entity_stack = ft.Stack(expand=True)
        self.entity_stack.controls.append(self.player())
        
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
        
        # Composition
        self.stage = ft.Stack(
            controls=[
                self.background_stack,
                self.entity_stack,
                self.foreground_stack,
                buttons_row
            ], expand=True
        )
        
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
    
    # * === EVENTS ===
    def summon_gobby(self, spawn_amount: int = None, center_spawn: bool = False):
        """Summons a random gobby."""
        def rnd_name():
            names = ["Gobby", "Gibby", "Geeb", "Goob", "Gubby", "Gebby", "Gub", "Gerald", "Gibby", "Gib",
                     "Gob", "Gobber", "Gob Lin", "Gob Gob", "Geb Geb", "Gub Gub", "Gib Gib", "Gibba", "Gibber"]
            return random.choice(names)
        
        if spawn_amount is None: spawn_amount = random.randint(1, 5)
        elif spawn_amount == 0: return
        else: spawn_amount = abs(spawn_amount)
        for _ in range(spawn_amount):
            new_gobby = Goblin(game_manager=self, name=rnd_name())
            new_gobby._entity_list = self.entity_list
            new_gobby.toggle_show_border(self.show_border_sw.value)
            new_gobby._atk_hb_show = self.show_border_sw.value
            self.entity_list.append(new_gobby)
            self.entity_stack.controls.append(new_gobby(center_spawn=center_spawn))
    
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
        
class Goblin(Enemy):
    """Wrapped `Enemy` class to be used in the `GameMaker` class."""
    def __init__(self, game_manager: GameManager, name: str, *, debug = False):
        super().__init__(
            type=EnemyType.GOBLIN,
            page=game_manager.page,
            audio_manager=game_manager.audio_manager,
            target=game_manager.player,
            name=name,
            debug=debug
        )
        