import flet as ft
import asyncio, random


class DamageText(ft.Text):
    def __init__(
        self, left: int = None, top: int = None,
        value: ft.Number = 0
    ):
        super().__init__(
            value=f"-{value}", size=18, left=left, top=top,
            animate_opacity=ft.Animation(200, ft.AnimationCurve.LINEAR),
            animate_position=ft.Animation(500, ft.AnimationCurve.EASE_IN_OUT),
            text_align=ft.TextAlign.CENTER, opacity=0, color=ft.Colors.RED
        )
        self.cleanup_ready: bool = False
    
    def try_update(self, control: ft.Control):
        try: control.update()
        except RuntimeError: pass
    
    def did_mount(self):
        async def animation():
            parent = self.parent
            await asyncio.sleep(0.05)
            self.opacity = 1
            if isinstance(parent, ft.Stack): self.left -= 20
            else:
                self.left = None
                self.top = None
            self.try_update(self)
            
            await asyncio.sleep(0.5)
            self.opacity = 0
            self.try_update(self)
            self.cleanup_ready = True
        self.page.run_task(animation)