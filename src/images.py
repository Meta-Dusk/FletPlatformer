import flet as ft


class Sprite(ft.Image):
    """All sprites will have twice their scale for better visuals."""
    def __init__(
        self, src: str, width: ft.Number, height: ft.Number, *,
        filter_quality: ft.FilterQuality = ft.FilterQuality.NONE,
        fit: ft.BoxFit = ft.BoxFit.COVER, gapless_playback: bool = True,
        scale: ft.Scale = ft.Scale(scale_x=2, scale_y=2),
        offset: ft.Offset = ft.Offset(0, 0)
    ):
        super().__init__(
            src=src, width=width, height=height, filter_quality=filter_quality,
            fit=fit, gapless_playback=gapless_playback, scale=scale, offset=offset
        )
        
    def change_src(self, new_src: str, update_ctrl: bool = True):
        """Swap the `src` and optionally update."""
        self.src = new_src
        if update_ctrl and self.page:
            self.update()
    
    def flip_x(self, update_ctrl: bool = True):
        """Flip the image on the x-axis."""
        if (
            self.scale.scale_x > 0 or self.scale.scale_x < 0
        ): self.scale.scale_x *= -1
        if update_ctrl and self.page:
            self.update()
            
            
# * Test for the Sprite class
def test(page: ft.Page):
    page.title = "Sprite Class Test"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    spr = Sprite("images/enemies/goblin/attack-main_0.png", 150, 150)
    page.add(
        spr, ft.Button("Flip (x-axis)", on_click=lambda _: spr.flip_x())
    )
    
if __name__ == "__main__":
    ft.run(test)