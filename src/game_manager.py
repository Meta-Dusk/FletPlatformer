import flet as ft
import asyncio

from audio.audio_manager import AudioManager
from utilities.keyboard_manager import held_keys, start as km_start
from utilities.tasks import attempt_cancel
from entities.player import Player
from bg_loops import light_mv_loop, stage_panning_loop
from backgrounds import bg_image_forest


class GameManager:
    """Central hub for the game UI and states."""
    def __init__(self, page: ft.Page):
        # State Variables (References)
        self.page: ft.Page = page
        self.player: Player = None
        self.audio_manager: AudioManager = None
        self.background_stack: ft.Stack = None
        self.foreground_stack: ft.Stack = None
        
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
        km_start()
        await self._setup_ui()
        
        # --- Event Handlers ---
        self.page.on_keyboard_event = self._on_keyboard_event
        
        # --- Start Loops ---
        self.start_tasks()

    async def _setup_ui(self):
        """Initializes Player, Stacks, and HUD."""
        # Player
        self.player = Player(self.page, self.audio_manager, held_keys)
        
        # Stacks (BG/FG)
        self.background_stack = ft.Stack(expand=True)
        self.foreground_stack = ft.Stack(expand=True)
        
        def bg_forest(index: int): return bg_image_forest(index, self.page)
        
        for i in range(7): self.background_stack.controls.append(bg_forest(i))
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
        buttons_row = ft.Row(
            controls=[
                ft.Container(revive_btn, padding=16),
                ft.Container(death_btn, padding=16),
                ft.Container(damage_btn, padding=16),
                ft.Container(directional_audio_btn, padding=16),
            ], alignment=ft.MainAxisAlignment.CENTER, top=0, left=40
        )
        
        nametag = ft.Text(
            value="You", size=20, width=50,
            left=(self.player.sprite.width / 2) - 25,
            bottom=self.player.sprite.height - 30,
            text_align=ft.TextAlign.CENTER
        )
        health_bar = ft.ProgressBar(
            value=0, left=(self.player.sprite.width / 2) - 50,
            bottom=self.player.sprite.height - 50, width=100,
            bar_height=5, scale=ft.Scale(scale_x=-1, scale_y=1),
            color=ft.Colors.BLACK, bgcolor=ft.Colors.RED, border_radius=5
        )
        self.player.health_bar = health_bar
        self.player.stack.controls.extend([nametag, health_bar])
        
        # Composition
        stage = ft.Stack(
            controls=[
                self.background_stack,
                self.player(), # ? Call player to get the Stack control
                self.foreground_stack,
                buttons_row
            ], expand=True
        )
        
        await self.page.window.center()
        self.page.add(stage)
        
    # * --- Event Handlers ---
    def _da_btn_on_change(self, e: ft.ControlEvent): self.audio_manager.directional_sfx = e.data
    
    async def _player_die(self, _): await self.player.death()
    async def _player_revive(self, _): await self.player.revive()
    async def _player_damage(self, _): await self.player.take_damage(5)
    
    async def _on_keyboard_event(self, e: ft.KeyboardEvent):
        match e.key:
            case " ": self.player.jump()
            case "V": self.player.attack()
            case "Escape": await self.page.window.close()

    # * --- Task Management ---
    def start_tasks(self):
        """Starts background loops."""
        async def run_light(): await light_mv_loop(self.background_stack)
        async def run_pan():
            await stage_panning_loop(
                self.background_stack,
                self.foreground_stack,
                self.player,
                self.page
            )
            
        # Store tasks so we can cancel them later
        self.running_tasks.append(self.page.run_task(run_light))
        self.running_tasks.append(self.page.run_task(run_pan))

    def cleanup(self):
        """Call this when exiting or changing levels."""
        for task in self.running_tasks: attempt_cancel(task)
                