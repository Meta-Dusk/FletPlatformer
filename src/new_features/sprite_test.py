import flet as ft
import asyncio
from dataclasses import dataclass, field
from typing import Literal

from tests.test_templates import test_init

SpriteStates = str | Literal["idle", "attack", "death", "fall", "jump", "run", "take-hit"]

@ft.observable
@dataclass
class Character:
    src: str
    name: str
    width: ft.Number
    height: ft.Number
    state: SpriteStates = "idle"
    frame: int = 0
    frame_count: int = 10

@ft.control(kw_only=True)
class Sprite(ft.Image):
    filter_quality: ft.FilterQuality = ft.FilterQuality.NONE
    fit: ft.BoxFit = ft.BoxFit.COVER
    gapless_playback: bool = True
    scale: ft.Scale = field(default_factory=lambda: ft.Scale(scale_x=2, scale_y=2))
    offset: ft.Offset = field(default_factory=lambda: ft.Offset(0, 0.225))
    rotate: ft.RotateValue = field(default_factory=lambda: ft.Rotate(0, ft.Alignment.CENTER))

@ft.component
def CharSprite(char_data: Character) -> ft.Control:
    # No use_effect or internal loops here! 
    # This component just reacts to char_data changes.
    
    base_path = char_data.src.rsplit("/", 1)[0]
    current_src = f"{base_path}/{char_data.state}_{char_data.frame}.png"
    
    return ft.Container(
        content=Sprite(
            src=current_src,
            width=char_data.width,
            height=char_data.height
        ),
        border=ft.Border.all(1, ft.Colors.WHITE)
    )

@ft.component
def GameView():
    char_data = ft.use_memo(lambda: Character(
        src="images/players/hero_knight/idle_0.png",
        name="Hero Knight",
        width=180, height=180
    ))

    # The Central Animation Loop
    def animation_manager():
        running = True
        async def loop():
            while running:
                # Increment frame externally
                char_data.frame = (char_data.frame + 1) % char_data.frame_count
                # No need to call update(); @ft.observable handles it!
                await asyncio.sleep(1 / 12)
        
        task = asyncio.create_task(loop())
        return lambda: task.cancel()
    
    # This loop runs once for the entire view, not per sprite
    ft.use_effect(animation_manager)
    
    def switch_state(state: SpriteStates, frame_count: int):
        nonlocal char_data
        char_data.state = state
        char_data.frame_count = frame_count
        char_data.frame = 0 # Reset frame on state change
    
    return ft.Column(
        controls=[
            CharSprite(char_data),
            ft.Row(
                controls=[
                    ft.Button("Idle", on_click=lambda _: switch_state("idle", 10)),
                    ft.Button("Run", on_click=lambda _: switch_state("run", 8)),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            )
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )

async def main(page: ft.Page):
    await test_init(page)
    page.render(GameView)

ft.run(main, assets_dir="../assets")