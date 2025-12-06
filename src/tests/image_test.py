import flet as ft

from images import Sprite
from tests.test_templates import test_init

async def test(page: ft.Page):
    await test_init
    
    src_count: int = 0
    
    def update_src(_):
        nonlocal src_count
        spr._debug_msg(f"Incrementing index: {src_count} -> ", end="")
        if src_count < 7: src_count += 1
        else: src_count = 0
        spr._debug_msg(src_count, include_handler=False)
        spr.change_src(f"images/enemies/goblin/attack-main_{src_count}.png")
    
    spr = Sprite(f"images/enemies/goblin/attack-main_{src_count}.png", 150, 150, debug=True)
    
    page.add(
        spr,
        ft.Button("Flip (x-axis)", on_click=lambda _: spr.flip_x()),
        ft.Button("Update Source", on_click=update_src)
    )
    
ft.run(test, assets_dir="../assets")