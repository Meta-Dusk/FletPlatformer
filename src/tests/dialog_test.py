import flet as ft

from audio.audio_manager import global_audio_manager
from tests.test_templates import test_init
from components.dialog import DialogBox
from images import SpriteList, IconSprite

spr = SpriteList()

async def test(page: ft.Page):
    await test_init(page)
    
    row_1 = ft.Row(
        controls=[
            ft.Text("Move:", size=20),
            IconSprite(spr.keys.a),
            ft.Text("/", size=30),
            IconSprite(spr.keys.d),
        ],
        spacing=8,
        alignment=ft.MainAxisAlignment.START,
        vertical_alignment=ft.CrossAxisAlignment.CENTER
    )
    row_2 = ft.Row(
        controls=[
            ft.Text("Jump:", size=20),
            IconSprite(spr.keys.space, padding=ft.Padding.symmetric(horizontal=16)),
        ],
        spacing=8,
        alignment=ft.MainAxisAlignment.START,
        vertical_alignment=ft.CrossAxisAlignment.CENTER
    )
    row_3 = ft.Row(
        controls=[
            ft.Text("Sprint:", size=20),
            IconSprite(spr.keys.shift, padding=ft.Padding.symmetric(horizontal=16)),
            ft.Text("+", size=50, text_align=ft.TextAlign.CENTER, offset=ft.Offset(0.0, 0.05)),
            IconSprite(spr.keys.a),
            ft.Text("/", size=30),
            IconSprite(spr.keys.d),
        ],
        spacing=8,
        alignment=ft.MainAxisAlignment.START,
        vertical_alignment=ft.CrossAxisAlignment.CENTER
    )
    row_4 = ft.Row(
        controls=[
            ft.Text("Attack:", size=20),
            IconSprite(spr.keys.v),
        ],
        spacing=8,
        alignment=ft.MainAxisAlignment.START,
        vertical_alignment=ft.CrossAxisAlignment.CENTER
    )
    row_5 = ft.Row(
        controls=[
            ft.Text("Dash:", size=20),
            IconSprite(spr.keys.a),
            ft.Text("/", size=30),
            IconSprite(spr.keys.d),
            ft.Text("+", size=50, text_align=ft.TextAlign.CENTER, offset=ft.Offset(0.0, 0.05)),
            IconSprite(spr.keys.c),
        ],
        spacing=8,
        alignment=ft.MainAxisAlignment.START,
        vertical_alignment=ft.CrossAxisAlignment.CENTER
    )
    
    col = ft.Column(
        controls=[
            row_1,
            row_2,
            row_3,
            row_4,
            row_5
        ],
        alignment=ft.MainAxisAlignment.START,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        tight=True
    )
    
    main_cont = ft.Container(
        content=col, alignment=ft.Alignment.CENTER, width=200
    )
    
    page.add(main_cont)
    
    
ft.run(test, assets_dir="../assets")