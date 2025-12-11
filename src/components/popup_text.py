import flet as ft
import asyncio

from utilities.components import try_update

class HealthText(ft.Text):
    """A simple text display for the damage numbers."""
    def __init__(
        self, value: str = "", color: ft.ColorValue = None,
        left: ft.Number = None, right: ft.Number = None,
        top: ft.Number = None, bottom: ft.Number = None,
        *,
        anim_left: ft.Number = -20, anim_right: ft.Number = None,
        anim_top: ft.Number = None, anim_bottom: ft.Number = None
    ) -> None:
        """
        This control is expected to be in a stack, but it also supports
        non-stack layout controls.
        """
        self.anim_left = anim_left
        self.anim_right = anim_right
        self.anim_top = anim_top
        self.anim_bottom = anim_bottom
        super().__init__(
            value=value, size=18, color=color, opacity=0,
            animate_opacity=ft.Animation(200, ft.AnimationCurve.LINEAR),
            animate_position=ft.Animation(500, ft.AnimationCurve.EASE_IN_OUT),
            text_align=ft.TextAlign.CENTER,
            left=left, right=right, top=top, bottom=bottom
        )
        self.cleanup_ready: bool = False
    
    async def _animation(self) -> None:
        """Animation once self has been attached to a page."""
        parent = self.parent
        await asyncio.sleep(0.05)
        if isinstance(parent, ft.Stack):
            if self.anim_left is not None: self.left = self.anim_left
            if self.anim_right is not None: self.right = self.anim_right
            if self.anim_top is not None: self.top = self.anim_top
            if self.anim_bottom is not None: self.bottom = self.anim_bottom
        self.opacity = 1
        try_update(self)
        
        await asyncio.sleep(0.5)
        self.opacity = 0
        try_update(self)
        self.cleanup_ready = True
    
    def did_mount(self) -> None:
        """Runs automatically once attached to a page control."""
        self.page.run_task(self._animation)