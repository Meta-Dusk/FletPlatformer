import flet as ft

from components.custom_switches import TextAndToggle


class ConsoleToggle(TextAndToggle):
    def __init__(self):
        super().__init__(
            label_text="Enable Dev Console"
        )

class PerfMonitorToggles(ft.Container):
    def __init__(self):
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