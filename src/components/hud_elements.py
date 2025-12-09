import flet as ft


class NameTag(ft.Stack):
    def __init__(
        self, text: str
    ) -> None:
        """A common nametag for each `Entity`."""
        self.outline_text = ft.Text(
            value=text, size=20,
            style=ft.TextStyle(
                foreground=ft.Paint(
                    color=ft.Colors.BLACK,
                    stroke_width=4,
                    style=ft.PaintingStyle.STROKE
                )
            )
        )
        self.solid_text = ft.Text(value=text, size=20, color=ft.Colors.WHITE)
        
        super().__init__(
            controls=[self.outline_text, self.solid_text],
            clip_behavior=ft.ClipBehavior.NONE,
            alignment=ft.Alignment.CENTER
        )