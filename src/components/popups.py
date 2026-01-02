import flet as ft
from typing import Optional

class SimpleNotification(ft.SnackBar):
    """A simple auto-closing notification popup."""
    def __init__(
        self, content: str, duration: int = 2000, *,
        is_error: bool = False, width: ft.Number = None
    ) -> None:
        bgcolor: ft.ColorValue = None
        
        text = ft.Text(value=content, size=20)
        container = ft.Container(
            content=text, alignment=ft.Alignment.CENTER
        )
        
        if is_error:
            text.color = ft.Colors.ERROR
            bgcolor = ft.Colors.ERROR_CONTAINER
            
        super().__init__(
            content=container, open=True, duration=duration,
            behavior=ft.SnackBarBehavior.FLOATING, bgcolor=bgcolor,
            width=width, elevation=10, padding=4
        )
    
    def did_mount(self):
        self.on_dismiss = self._on_dismiss
    
    def _on_dismiss(self, e: ft.ControlEvent) -> None:
        self.page.overlay.remove(e.control)

class SimpleDialog(ft.AlertDialog):
    """A simple non-blocking and auto-cleanup alert dialog popup."""
    def __init__(
        self, title: str, content: str | list[str],
        icon: Optional[ft.Control] = None,
        *, title_size: ft.Number = 30
    ) -> None:
        
        title_ctrl = ft.Container(
            content=ft.Text(value=title, size=title_size),
            alignment=ft.Alignment.CENTER
        )
        content_ctrl = ft.Container(
            content=ft.Text(value="text", size=title_size-10, spans=[]),
            alignment=ft.Alignment.CENTER
        )
        
        text_ctrl: ft.Text = content_ctrl.content
        if isinstance(content, str):
            text_ctrl.value = content
        elif isinstance(content, list) and isinstance(content[0], str):
            text_ctrl.value = ""
            for text in content:
                text_ctrl.spans.append(ft.TextSpan(text))
        else:
            raise ValueError("'content' must be of str or a list of str!")
        
        super().__init__(
            title=title_ctrl, icon=icon, content=content_ctrl,
            elevation=10, open=False, scrollable=True
        )
    
    def did_mount(self):
        self.on_dismiss = self._on_dismiss
        self.open = True
        self.update()
    
    def _on_dismiss(self, e: ft.ControlEvent) -> None:
        self.page.overlay.remove(e.control)
