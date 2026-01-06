import flet as ft
from components.custom_switches import NewTextAndToggle

# * --- Stamina & Console Toggles ---
def NewStaminaToggle() -> ft.Control:
    return NewTextAndToggle("Verbose Stamina", spacer_width=50)

def NewConsoleToggle() -> ft.Control:
    return NewTextAndToggle("Enable Dev Console")


# * --- Performance Monitor Toggles ---
class PerfMonitorToggles(ft.Container):
    """Configuration class for Performance Monitor grouping."""
    def __init__(self, monitor_val: bool = False, ups_val: bool = True, lag_val: bool = True) -> None:
        super().__init__()
        # We instantiate the config classes so GameManager can still access .switch
        self.monitor_switch = NewTextAndToggle(label_text="Performance Monitor", spacer_width=50, switch_value=monitor_val)
        self.ups_switch = NewTextAndToggle(label_text="Show UPS", spacer_width=185, switch_value=ups_val)
        self.lag_switch = NewTextAndToggle(label_text="Show Latency", spacer_width=130, switch_value=lag_val)

@ft.component
def PerfMonitorTogglesComponent(control: PerfMonitorToggles):
    # This component simply nests our previously refactored TextAndToggle components
    return ft.Container(
        alignment=ft.Alignment.CENTER,
        padding=4,
        expand=True,
        content=ft.Column(
            controls=[
                # We reuse the helper functions from custom_switches.py
                control.monitor_switch,
                control.ups_switch,
                control.lag_switch
            ],
            alignment=ft.MainAxisAlignment.CENTER
        )
    )


# * --- Background Toggles ---
class BackgroundToggles(ft.Container):
    """Configuration class for Background effect grouping."""
    def __init__(self, parallax_val: bool = True, animated_val: bool = True) -> None:
        # Initializing as disabled as per original script
        super().__init__(disabled=True) 
        self.parallax_bg_switch = NewTextAndToggle(label_text="Allow Parallax Movement", spacer_width=10, switch_value=parallax_val)
        self.animated_bg_switch = NewTextAndToggle(label_text="Allow Animated Layers", spacer_width=35, switch_value=animated_val)

@ft.component
def BackgroundTogglesComponent(control: BackgroundToggles):
    return ft.Container(
        alignment=ft.Alignment.CENTER,
        padding=4,
        expand=True,
        disabled=control.disabled,
        content=ft.Column(
            controls=[
                control.parallax_bg_switch,
                control.animated_bg_switch
            ],
            alignment=ft.MainAxisAlignment.CENTER
        )
    )


# * --- Helpers ---
def NewPerfToggles(monitor_val: bool = False, ups_val: bool = True, lag_val: bool = True) -> PerfMonitorToggles:
    return PerfMonitorTogglesComponent(PerfMonitorToggles(monitor_val, ups_val, lag_val))

def NewBackgroundToggles(parallax_val: bool = True, animated_val: bool = True) -> BackgroundToggles:
    return BackgroundTogglesComponent(BackgroundToggles(parallax_val, animated_val))