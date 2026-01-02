import asyncio
import flet as ft
from typing import Optional, Literal

from setup import FontStyles

from components.buttons import SimpleButton
from components.volume_controls import VolumeControl, DirectionalVolumeToggle
from components.window_controls import FullscreenToggle
from components.game_controls import ConsoleToggle, PerfMonitorToggles, StaminaSettings

from backgrounds import add_infinite_layer
from bg_loops import LightMovementLoop

from utilities.components import try_update
from utilities.values import get_app_version

from audio.audio_manager import AudioManager

def new_button(
    text: str, width: ft.Number = 250, height: ft.Number = 50,
    on_click: ft.ControlEventHandler[ft.Button] = None,
):
    """Just a preset for making a `SimpleButton` instance."""
    return SimpleButton(
        content=ft.Text(value=text),
        width=width, height=height,
        on_click=on_click
    )

class Menu(ft.WindowDragArea):
    """Menu base class."""
    def __init__(
        self, content: ft.Control, visible: bool = True,
        opacity: ft.Number = 1
    ):
        super().__init__(
            content=content, maximizable=False, expand=True, visible=visible,
            animate_opacity=ft.Animation(1000, ft.AnimationCurve.LINEAR),
            opacity=opacity
        )

class MainMenu(Menu):
    """A control representing the Main Menu."""
    def __init__(
        self,
        on_start: Optional[ft.ControlEventHandler[ft.Button]] = None,
        on_quit: Optional[ft.ControlEventHandler[ft.Button]] = None,
        on_settings: Optional[ft.ControlEventHandler[ft.Button]] = None
    ):
        """Provide callbacks for the Main Menu buttons."""
        title = ft.Text("Fushi: The Beckoning", size=80, font_family=FontStyles.LIEF)
        version = ft.Text(
            value=f"v{get_app_version()}.dev", size=30,
            font_family=FontStyles.MEDODICA, offset=ft.Offset(0.0, -1.0)
        )
        
        self.bg_stack = ft.Stack(expand=True)
        bg_container = ft.Container(self.bg_stack, expand=True, alignment=ft.Alignment.CENTER)
        
        self.ui_elements = ft.Column(
            controls=[
                title,
                version,
                new_button("Start Game", on_click=on_start),
                new_button("Settings", on_click=on_settings),
                new_button("Quit", on_click=on_quit),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
        
        ui_stack = ft.Stack([bg_container, self.ui_elements], alignment=ft.Alignment.CENTER)
        main_container = ft.Container(
            content=ui_stack, expand=True, alignment=ft.Alignment.CENTER
        )
        
        super().__init__(content=main_container, opacity=0)
        
        self.light_mv_loop = LightMovementLoop(self.bg_stack)
        self.light_mv_task: asyncio.Task = None
    
    def stop_anim_loop(self):
        """Stops the looping animation for the background."""
        self.light_mv_loop.stop()
    
    async def _light_mv_loop(self) -> None:
        await self.light_mv_loop.start()
    
    def start_anim_loop(self):
        """Looping animation for the background."""
        # print("starting light_mv_loop")
        self.light_mv_task = self.page.run_task(self._light_mv_loop)
    
    async def start_up_anim(self):
        """Animation when starting up the game."""
        await asyncio.sleep(0.1)
        self.opacity = 1
        try_update(self)
    
    def did_mount(self):
        """Runs automatically once attached to a page control."""
        for i in range(1, 11):
            add_infinite_layer(self.bg_stack, i, self.page)
        self.bg_stack.controls.append(
            ft.Container(
                bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
                expand=True
            )
        )
        self.start_anim_loop()
        try_update(self.bg_stack)
        self.page.run_task(self.start_up_anim)

class PauseMenu(Menu):
    """A control representing the Pause Menu."""
    def __init__(
        self,
        on_resume: Optional[ft.ControlEventHandler[ft.Button]] = None,
        on_settings: Optional[ft.ControlEventHandler[ft.Button]] = None,
        on_quit: Optional[ft.ControlEventHandler[ft.Button]] = None
    ):
        """Provide callbacks for the Pause Menu buttons."""
        title = ft.Text("PAUSED", size=80, font_family=FontStyles.MEDODICA)
        subtitle = ft.Text(
            "Yes, it's actually paused.", size=20, font_family=FontStyles.LIEF,
            offset=ft.Offset(0.0, -1.0), color=ft.Colors.RED
        )
        
        main_container = ft.Container(
            expand=True,
            bgcolor=ft.Colors.with_opacity(0.65, ft.Colors.BLACK),
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                controls=[
                    title, subtitle,
                    new_button("Resume", on_click=on_resume),
                    new_button("Settings", on_click=on_settings),
                    new_button("Quit to Title", on_click=on_quit),
                ], alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
        )
        super().__init__(content=main_container, visible=False, opacity=1)
        
class SettingsMenu(Menu):
    """A control representing the Settings Menu."""
    def __init__(
        self, audio_manager: AudioManager,
        on_close: Optional[ft.ControlEventHandler[ft.Button]] = None
    ):
        """Provide callbacks for the Settings Menu buttons."""
        self.audio_manager = audio_manager
        
        title = ft.Text("SETTINGS", size=80, font_family=FontStyles.MEDODICA)
        self.subtitle = ft.Text(
            "Yes, it's actually paused.", size=20, font_family=FontStyles.LIEF,
            offset=ft.Offset(0.0, -1.0), color=ft.Colors.RED, visible=False
        )
        
        volume_column = ft.Column(
            controls=[
                self._section_text("Volume"),
                self._new_volume_control("music", "Music Volume"),
                self._new_volume_control("sfx", "SFX Volume"),
                DirectionalVolumeToggle(self.audio_manager),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
        volume_settings = ft.Container(
            content=volume_column, bgcolor=ft.Colors.GREY_900,
            alignment=ft.Alignment.CENTER
        )
        
        self.fullscreen_toggle = FullscreenToggle()
        self.window_column = ft.Column(
            controls=[
                self._section_text("Window"),
                self.fullscreen_toggle,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
        window_settings = ft.Container(
            content=self.window_column, bgcolor=ft.Colors.GREY_900,
            alignment=ft.Alignment.CENTER
        )
        
        self.console_switch = ConsoleToggle()
        self.perf_toggles = PerfMonitorToggles()
        self.stamina_toggles = StaminaSettings()
        game_column = ft.Column(
            controls=[
                self._section_text("Game"),
                self.console_switch,
                self.perf_toggles,
                self.stamina_toggles
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
        game_settings = ft.Container(
            content=game_column, bgcolor=ft.Colors.GREY_900,
            alignment=ft.Alignment.CENTER
        )
        
        self.settings_container = ft.Container(
            padding=8, offset=ft.Offset(0.0, -0.1),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        volume_settings,
                        window_settings,
                        game_settings,
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    scroll=ft.ScrollMode.ALWAYS
                ),
                padding=8, alignment=ft.Alignment.CENTER,
                bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
                border=ft.Border.all(1, ft.Colors.with_opacity(0.75, ft.Colors.BLACK))
            )
        )
        
        main_container = ft.Container(
            expand=True,
            bgcolor=ft.Colors.with_opacity(0.65, ft.Colors.BLACK),
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                controls=[
                    title,
                    self.subtitle,
                    self.settings_container,
                    new_button("Go Back", on_click=on_close),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
        )
        super().__init__(content=main_container, visible=False, opacity=1)
    
    def _new_volume_control(self, audio_type: Literal["music", "sfx"], label: str):
        return VolumeControl(self.audio_manager, audio_type, label)
    
    def did_mount(self):
        self.settings_container.height = self.page.height / 2
    
    def win_on_update(self, e: ft.WindowEvent):
        if e.type == ft.WindowEventType.RESIZED:
            self.settings_container.height = self.page.height / 2
            try_update(self.settings_container)
    
    def _section_text(self, text: str) -> None:
        return ft.Text(
            value=text, size=40, font_family=FontStyles.LIEF,
            color=ft.Colors.WHITE_54
        )