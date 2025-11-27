import flet as ft


class Sprite(ft.Image):
    """All sprites will have twice their scale for better visuals."""
    def __init__(
        self, src: str, width: ft.Number, height: ft.Number, *,
        filter_quality: ft.FilterQuality = ft.FilterQuality.NONE,
        fit: ft.BoxFit = ft.BoxFit.COVER, gapless_playback: bool = True,
        scale: ft.Scale = ft.Scale(scale_x=2, scale_y=2),
        offset: ft.Offset = ft.Offset(0, 0.15)
    ):
        super().__init__(
            src=src, width=width, height=height, filter_quality=filter_quality,
            fit=fit, gapless_playback=gapless_playback, scale=scale, offset=offset
        )
    
    def try_update(self):
        try: self.update()
        except RuntimeError: pass
    
    def change_src(self, new_src: str, update_ctrl: bool = True):
        """Swap the `src` and optionally update."""
        self.src = new_src
        if update_ctrl: self.try_update()
    
    def flip_x(self, direction: int, update_ctrl: bool = True):
        """Flip the image on the x-axis."""
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
        if src_count < 7: src_count += 1
        else: src_count = 0
        spr.change_src(f"images/enemies/goblin/attack-main_{src_count}.png")
    
    spr = Sprite(f"images/enemies/goblin/attack-main_{src_count}.png", 150, 150)
    page.add(
        spr,
        ft.Button("Flip (x-axis)", on_click=lambda _: spr.flip_x()),
        ft.Button("Update Source", on_click=update_src)
    )
    
if __name__ == "__main__":
    ft.run(test)