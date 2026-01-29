import asyncio
import flet as ft
from typing import Optional, Callable

from setup import FontStyles
from components.buttons import SimpleButton
from components.volume_controls import VolumeControlComponent, DirectionalVolumeToggleComponent
from components.window_controls import FullscreenToggleComponent
from components.game_controls import NewConsoleToggle, NewPerfToggles, NewStaminaToggle

from backgrounds import add_infinite_layer
from bg_loops import LightMovementLoop
from audio.audio_manager import AudioManager
from utilities.values import get_app_version

OptionalCallback = Optional[Callable[[None], None]]

# * --- Base Menu Configuration ---
@ft.control(kw_only=True)
class Menu(ft.WindowDragArea):
    """Configuration class for menus."""
    def init(self):
        self.maximizable = False
        self.expand = True
        self.animate_opacity = ft.Animation(1000, ft.AnimationCurve.LINEAR)


# * --- Main Menu ---
class MainMenu(Menu):
    """Data object for the Main Menu state and callbacks."""
    def __init__(
        self,
        on_start: OptionalCallback = None,
        on_quit: OptionalCallback = None,
        on_settings: OptionalCallback = None
    ) -> None:
        super().__init__(opacity=0)
        self.on_start = on_start
        self.on_quit = on_quit
        self.on_settings = on_settings

@ft.component
def MainMenuComponent(control: MainMenu) -> ft.Control:
    # 1. Background Logic via Hook
    bg_stack = ft.use_memo(lambda: ft.Stack(expand=True))
    
    def handle_background():
        # Add layers once on mount
        for i in range(1, 11):
            add_infinite_layer(bg_stack, i, control.page)
        
        bg_stack.controls.append(
            ft.Container(bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK), expand=True)
        )
        
        # Start the animation loop
        loop = LightMovementLoop(bg_stack)
        task = asyncio.create_task(loop.start())
        
        # Entrance animation
        async def fade_in():
            await asyncio.sleep(0.1)
            control.opacity = 1
            control.update() # Declarative update for opacity property
            
        fade_task = asyncio.create_task(fade_in())
        
        # Cleanup: Stop all tasks when menu is unmounted
        return lambda: (task.cancel(), fade_task.cancel())

    ft.use_effect(handle_background, [])

    # 2. UI Layout
    version_text = f"v{get_app_version()}.dev"
    
    return ft.Container(
        content=ft.Stack([
            ft.Container(content=bg_stack, expand=True),
            ft.Column(
                controls=[
                    ft.Text("Fushi: The Beckoning", size=80, font_family=FontStyles.LIEF),
                    ft.Text(version_text, size=30, font_family=FontStyles.MEDODICA, offset=ft.Offset(0, -1)),
                    SimpleButton(content=ft.Text("Start Game"), on_click=control.on_start),
                    SimpleButton(content=ft.Text("Settings"), on_click=control.on_settings),
                    SimpleButton(content=ft.Text("Quit"), on_click=control.on_quit),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
        ], alignment=ft.Alignment.CENTER),
        expand=True
    )

def NewMainMenu(
    on_start: OptionalCallback,
    on_quit: OptionalCallback,
    on_settings: OptionalCallback
) -> MainMenu:
    return MainMenuComponent(
        MainMenu(
            on_start=on_start,
            on_quit=on_quit,
            on_settings=on_settings
        )
    )


# * --- Settings Menu ---
class SettingsMenu(Menu):
    def __init__(self, audio_manager: AudioManager, on_close: OptionalCallback = None):
        super().__init__(content=None, visible=False, opacity=1)
        self.audio_manager = audio_manager
        self.on_close = on_close
        # References for sub-components
        self.fullscreen_toggle = None

@ft.component
def SettingsMenuComponent(control: SettingsMenu) -> ft.Control:
    # 1. Responsive State
    scroll_height, set_scroll_height = ft.use_state(300)

    # 2. Window Event Handling via Effect
    # Use a reference for the toggle to ensure it's tracked correctly
    fullscreen_toggle_ref = ft.use_ref()
    
    def setup_window_sync():
        # GUARD: Ensure page exists before doing anything
        if not control.page:
            return

        def on_win_event(e: ft.WindowEvent):
            if e.type == ft.WindowEventType.RESIZED:
                # Page is guaranteed to exist inside an event handler
                set_scroll_height(control.page.height / 2)
                
                # Check if the ref has been assigned before calling sync_ui
                print({fullscreen_toggle_ref})
                if fullscreen_toggle_ref.current:
                    fullscreen_toggle_ref.current.sync_ui()
                    
        # Initial calculation
        set_scroll_height(control.page.height / 2)
        
        # Save previous handler to restore it on cleanup
        old_handler = control.page.on_window_event
        control.page.on_window_event = on_win_event
        
        return lambda: setattr(control.page, "on_window_event", old_handler)
    
    # This effect now depends on 'control.page' being populated
    ft.use_effect(setup_window_sync, [control.page])
    
    # 3. Sections
    def section(text: str):
        return ft.Text(text, size=40, font_family=FontStyles.LIEF, color=ft.Colors.WHITE_54)
    
    # Instantiate nested reactive components
    control.fullscreen_toggle = FullscreenToggleComponent(False)
    
    return ft.Container(
        expand=True,
        bgcolor=ft.Colors.with_opacity(0.65, ft.Colors.BLACK),
        alignment=ft.Alignment.CENTER,
        content=ft.Column(
            controls=[
                ft.Text("SETTINGS", size=80, font_family=FontStyles.MEDODICA),
                ft.Container(
                    height=scroll_height,
                    padding=8,
                    bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
                    content=ft.Column([
                        section("Volume"),
                        VolumeControlComponent(control.audio_manager, "music", "Music Volume"),
                        VolumeControlComponent(control.audio_manager, "sfx", "SFX Volume"),
                        DirectionalVolumeToggleComponent(control.audio_manager),
                        section("Window"),
                        control.fullscreen_toggle,
                        section("Game"),
                        NewConsoleToggle(),
                        NewPerfToggles(),
                        NewStaminaToggle(),
                    ], scroll=ft.ScrollMode.ALWAYS, alignment=ft.MainAxisAlignment.CENTER)
                ),
                SimpleButton(content=ft.Text("Go Back"), on_click=control.on_close),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
    )

def NewSettingsMenu(
    audio_manager: AudioManager,
    on_close: OptionalCallback
) -> SettingsMenu:
    return SettingsMenuComponent(
        SettingsMenu(
            audio_manager=audio_manager,
            on_close=on_close
        )
    )