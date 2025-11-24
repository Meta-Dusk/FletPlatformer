import flet as ft
from audio.audio_manager import AudioManager
from utilities.keyboard_manager import held_keys, start as km_start
from entities.player import Player

# TODO: Add a background

async def main_ui(page: ft.Page):
    page.title = "Player Class Test"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    audio_manager = AudioManager(debug=True)
    audio_manager.initialize()
    km_start()
    
    async def player_die(_): await player.death()
    async def player_damage(_): await player.take_damage(5)
    def da_btn_on_change(e: ft.ControlEvent): audio_manager.directional_sfx = e.data
    
    player = Player(page, audio_manager, held_keys)
    death_btn = ft.Button(content="Die", on_click=player_die, width=80, height=30)
    damage_btn = ft.Button(content="Take Damage", on_click=player_damage, width=160, height=30)
    directional_audio_btn = ft.Switch(
        adaptive=True, label="Directional Audio", width=200, height=40,
        value=audio_manager.directional_sfx, on_change=da_btn_on_change
    )
    buttons_row = ft.Row(
        controls=[
            ft.Container(content=death_btn, padding=16),
            ft.Container(content=damage_btn, padding=16),
            ft.Container(content=directional_audio_btn, padding=16),
        ], alignment=ft.MainAxisAlignment.CENTER, top=0,
        left=(page.width / 2) - ((damage_btn.width / 2) + (death_btn.width / 2) + (directional_audio_btn.width / 2))
    )
    nametag = ft.Text(
        value="You", size=20,
        left=(player.sprite.width / 2) - 25,
        bottom=player.sprite.height - 30,
        text_align=ft.TextAlign.CENTER,
        width=50
    )
    health_bar = ft.ProgressBar(
        value=0,
        left=(player.sprite.width / 2) - 50,
        bottom=player.sprite.height - 50,
        width=100, bar_height=5,
        scale=ft.Scale(scale_x=-1, scale_y=1),
        color=ft.Colors.BLACK,
        bgcolor=ft.Colors.RED,
        border_radius=5
    )
    player.health_bar = health_bar
    player.stack.controls.extend([nametag, health_bar])
    stage = ft.Stack(controls=[player(), buttons_row], expand=True)
    
    async def on_keyboard_event(e: ft.KeyboardEvent):
        """Handles 'on-press' events for the player."""
        match e.key:
            case " ": player.jump()
            case "V": player.attack()
            case "Escape": await page.window.close()
    
    await page.window.center()
    
    page.add(stage)
    page.on_keyboard_event = on_keyboard_event