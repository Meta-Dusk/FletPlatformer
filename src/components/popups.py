import flet as ft
from typing import Optional

class SimpleNotification(ft.SnackBar):
    def __init__(
        self, content: str, duration: int = 2000, *,
        is_error: bool = False
    ) -> None:
        bgcolor: ft.ColorValue = None
        text = ft.Text(value=content, size=20)
        
        if is_error:
            text.color = ft.Colors.ERROR
            bgcolor = ft.Colors.ERROR_CONTAINER
            
        super().__init__(
            content=text, open=True, duration=duration,
            behavior=ft.SnackBarBehavior.FLOATING, bgcolor=bgcolor
        )
    
    def did_mount(self):
        self.on_dismiss = self._on_dismiss
    
    def _on_dismiss(self, e: ft.ControlEvent) -> None:
        self.page.overlay.remove(e.control)

class SimpleDialog(ft.AlertDialog):
    def __init__(
        self, title: str, content: str, icon: Optional[ft.Control] = None,
        *, title_size: ft.Number = 30
    ) -> None:
        super().__init__(
            title=ft.Text(value=title, size=title_size), icon=icon,
            content=ft.Text(value=content, size=title_size-10),
            elevation=10, open=False, scrollable=True
        )
    
    def did_mount(self):
        self.on_dismiss = self._on_dismiss
        self.open = True
        self.update()
    
    def _on_dismiss(self, e: ft.ControlEvent) -> None:
        self.page.overlay.remove(e.control)
