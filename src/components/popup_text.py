import flet as ft
import asyncio, random


class DamageText(ft.Text):
    def __init__(
        self, left: int = None, bottom: int = None,
        value: ft.Number = 0
    ):
        super().__init__(
            value=f"-{value}", size=15, left=left, bottom=bottom,
            animate_opacity=ft.Animation(200, ft.AnimationCurve.LINEAR),
            animate_position=ft.Animation(1000, ft.AnimationCurve.EASE_IN_OUT),
            text_align=ft.TextAlign.CENTER, opacity=0, style=ft.TextStyle(
                foreground=ft.Paint(
                    color=ft.Colors.RED,
                    stroke_width=1,
                    style=ft.PaintingStyle.STROKE
                )
            )
        )
    
    def try_update(self, control: ft.Control):
        try: control.update()
        except RuntimeError: pass
    
    def did_mount(self):
        if not isinstance(self.parent, ft.Stack):
            self.left = None
            self.bottom = None
        async def delete_self():
            await asyncio.sleep(0.05)
            self.opacity = 1
            self.try_update(self)
            
            parent = self.parent
            if isinstance(parent, ft.Stack):
                self.left += random.randint(-20, 20)
                self.bottom += 20
                self.try_update(self)
            
            await asyncio.sleep(1)
            self.opacity = 0
            self.try_update(parent)
            await asyncio.sleep(0.2)
            parent.controls.remove(self)
        self.page.run_task(delete_self)