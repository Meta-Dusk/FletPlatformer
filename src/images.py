import flet as ft
from typing import Literal


class Sprite(ft.Image):
    """All sprites will have twice their scale for better visuals."""
    def __init__(
        self, src: str, width: ft.Number, height: ft.Number, *,
        filter_quality: ft.FilterQuality = ft.FilterQuality.NONE,
        fit: ft.BoxFit = ft.BoxFit.COVER, gapless_playback: bool = True,
        scale: ft.Scale = ft.Scale(scale_x=2, scale_y=2),
        offset: ft.Offset = ft.Offset(0, 0.145), debug: bool = False
    ):
        super().__init__(
            src=src, width=width, height=height, filter_quality=filter_quality,
            fit=fit, gapless_playback=gapless_playback, scale=scale, offset=offset
        )
        self.debug = debug
        self._handler_str = "Sprite"
    
    def _debug_msg(self, msg: str, *, end: str = None, include_handler: bool = True):
        """A simple debug message for simple logging."""
        if self.debug:
            if include_handler: print(f"[{self._handler_str}] {msg}", end=end)
            else: print(msg, end=end)
    
    def try_update(self):
        try: self.update()
        except RuntimeError: pass
    
    def change_src(self, new_src: str, update_ctrl: bool = True):
        """Swap the `src` and optionally update."""
        self.src = new_src
        if update_ctrl: self.try_update()
    
    def flip_x(self, direction: Literal[-1, 1] = None, update_ctrl: bool = True):
        """Flip the image on the x-axis."""
        if direction is None:
            self._debug_msg(f"No provided direction, using self as reference: ", end="")
            direction = -1 if self.scale.scale_x > 0 else 1
            self._debug_msg(direction, include_handler=False)
        new_scale = abs(self.scale.scale_x) * direction
        self.scale = ft.Scale(scale_x=new_scale, scale_y=self.scale.scale_y)
        if update_ctrl: self.try_update()
            
            
# * Test for the Sprite class; a simple implementation
# ? You can run this directly with file paths such as:
# ? uv run py .\src\images.py
def test(page: ft.Page):
    page.title = "Sprite Class Test"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    src_count: int = 0
    
    def update_src(_):
        nonlocal src_count
        spr._debug_msg(f"Incrementing index: {src_count} -> ", end="")
        if src_count < 7: src_count += 1
        else: src_count = 0
        spr._debug_msg(src_count, include_handler=False)
        spr.change_src(f"images/enemies/goblin/attack-main_{src_count}.png")
    
    spr = Sprite(f"images/enemies/goblin/attack-main_{src_count}.png", 150, 150, debug=True)
    
    async def on_keyboard_event(e: ft.KeyboardEvent):
        """Fast exit with key: `[Escape]`."""
        if e.key == "Escape": await page.window.close()
    
    page.on_keyboard_event = on_keyboard_event
    page.add(
        spr,
        ft.Button("Flip (x-axis)", on_click=lambda _: spr.flip_x()),
        ft.Button("Update Source", on_click=update_src)
    )
    
if __name__ == "__main__": ft.run(test)