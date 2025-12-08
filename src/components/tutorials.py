import flet as ft

from images import IconSprite, SpriteList

spr = SpriteList

class ControlsTutorial(ft.Container):
    def __init__(self):
        self.mv_key_a = IconSprite(spr.keys.a)
        self.mv_key_d = IconSprite(spr.keys.d)
        movement_row = ft.Row(
            controls=[
                ft.Text("Move:", size=20),
                self.mv_key_a,
                ft.Text("/", size=30),
                self.mv_key_d,
            ],
            spacing=8,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )
        
        self.jump_key = IconSprite(spr.keys.space, padding=ft.Padding.symmetric(horizontal=16))
        jump_row = ft.Row(
            controls=[
                ft.Text("Jump:", size=20),
                self.jump_key,
            ],
            spacing=8,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )
        
        self.sprint_shift = IconSprite(spr.keys.shift, padding=ft.Padding.symmetric(horizontal=16))
        self.sprint_key_a = IconSprite(spr.keys.a)
        self.sprint_key_d = IconSprite(spr.keys.d)
        sprint_row = ft.Row(
            controls=[
                ft.Text("Sprint:", size=20),
                self.sprint_shift,
                ft.Text("+", size=50, text_align=ft.TextAlign.CENTER, offset=ft.Offset(0.0, 0.05)),
                self.sprint_key_a,
                ft.Text("/", size=30),
                self.sprint_key_d,
            ],
            spacing=8,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )
        
        self.attack_key = IconSprite(spr.keys.v)
        attack_row = ft.Row(
            controls=[
                ft.Text("Attack:", size=20),
                self.attack_key,
            ],
            spacing=8,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )
        
        self.dash_key_a = IconSprite(spr.keys.a)
        self.dash_key_d = IconSprite(spr.keys.d)
        self.dash_key_c = IconSprite(spr.keys.c)
        dash_row = ft.Row(
            controls=[
                ft.Text("Dash:", size=20),
                self.dash_key_a,
                ft.Text("/", size=30),
                self.dash_key_d,
                ft.Text("+", size=50, text_align=ft.TextAlign.CENTER, offset=ft.Offset(0.0, 0.05)),
                self.dash_key_c,
            ],
            spacing=8,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )
        
        column = ft.Column(
            controls=[
                movement_row,
                jump_row,
                sprint_row,
                attack_row,
                dash_row
            ],
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True
        )
        
        super().__init__(
            content=column, alignment=ft.Alignment.CENTER,
            width=200, top=20, left=20
        )
    
    def set_finish(self, icon_sprite: IconSprite):
        if icon_sprite.data is None or icon_sprite.data:
            icon_sprite.set_tint(ft.Colors.GREEN, 0.5)
            icon_sprite.data = True