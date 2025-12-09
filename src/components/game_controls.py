import flet as ft

from components.custom_switches import TextAndToggle

class StaminaSettings(TextAndToggle):
    def __init__(self) -> None:
        super().__init__(
            label_text="Verbose Stamina Bar",
            spacer_width=50
        )

class ConsoleToggle(TextAndToggle):
    def __init__(self) -> None:
        super().__init__(
            label_text="Enable Dev Console"
        )

class PerfMonitorToggles(ft.Container):
    def __init__(self) -> None:
        self.monitor_switch = TextAndToggle(
            label_text="Performance Monitor",
            spacer_width=50
        )
        self.ups_switch = TextAndToggle(
            label_text="Show UPS",
            spacer_width=185,
            switch_value=True
        )
        self.lag_switch = TextAndToggle(
            label_text="Show Latency",
            spacer_width=130,
            switch_value=True
        )
        
        main_column = ft.Column(
            controls=[
                self.monitor_switch,
                self.ups_switch,
                self.lag_switch
            ],
            alignment=ft.Alignment.CENTER
        )
        
        super().__init__(
            content=main_column, alignment=ft.Alignment.CENTER,
            padding=4, expand=True
        )
        
class BackgroundToggles(ft.Container):
    def __init__(self) -> None:
        self.parallax_bg_switch = TextAndToggle(
            label_text="Allow Parallax Movement",
            spacer_width=10,
            switch_value=True
        )
        self.animated_bg_switch = TextAndToggle(
            label_text="Allow Animated Layers",
            spacer_width=35,
            switch_value=True
        )
        
        main_column = ft.Column(
            controls=[
                self.parallax_bg_switch,
                self.animated_bg_switch
            ],
            alignment=ft.Alignment.CENTER
        )
        
        super().__init__(
            content=main_column, alignment=ft.Alignment.CENTER,
            padding=4, expand=True, disabled=True
        )