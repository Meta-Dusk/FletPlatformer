import flet as ft

from components.custom_switches import NewTextAndToggle

@ft.component
def FullscreenToggleComponent(initial_state: bool) -> ft.Control:
    """
    A standalone reactive component for window fullscreen toggling.
    Follows the single-function pattern from volume_controls.py.
    """
    is_maximized, set_is_maximized = ft.use_state(initial_state)
    
    def on_state_change() -> None:
        if ctrl.page:
            ctrl.page.window.maximized = is_maximized
            ctrl.page.update()
            
    ft.use_effect(on_state_change, [is_maximized])
    
    def handle_toggle(val: bool) -> None: set_is_maximized(val)
            
    ctrl = ft.Container(
        alignment=ft.Alignment.CENTER,
        padding=4,
        expand=True,
        content=ft.Row(
            controls=[
                NewTextAndToggle(
                    "Borderless Fullscreen",
                    switch_value=is_maximized,
                    on_toggle=handle_toggle,
                    spacer_width=30,
                    label_offset=ft.Offset(-0.1, 0.0)
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )
    )
    return ctrl


# * Window Controls Test
from tests.test_templates import test_init

async def test(page: ft.Page) -> None:
    await test_init(page)
    
    @ft.component
    def TestView() -> ft.Control:
        return ft.Column(
            controls=[
                ft.Text("Window Controls", size=30),
                FullscreenToggleComponent(page.window.maximized)
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
    
    page.render(TestView)

if __name__ == "__main__": ft.run(test, assets_dir="../assets")