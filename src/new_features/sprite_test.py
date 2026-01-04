import flet as ft
import asyncio
from dataclasses import dataclass, field
from typing import Literal

from tests.test_templates import test_init

SpriteStates = str | Literal["idle", "attack", "death", "fall", "jump", "run", "take-hit"]

# --- DATA LAYER ---
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

# --- VIEW LAYER (Pure Controls) ---
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

# --- MANAGER LAYER (The View Logic) ---
@ft.component
def GameView() -> ft.Control:
    # 1. Persistent State
    char_data = ft.use_memo(lambda: Character(
        src="images/players/hero_knight/idle_0.png",
        name="Hero Knight",
        width=180, height=180
    ))
    # State for the ticker toggle
    is_playing, set_is_playing = ft.use_state(True)
    
    # 2. The Animation Ticker (The 'Manager' logic)
    def ticker_manager():
        # This flag is used to safely stop the loop
        running = {"active": True}
        
        async def loop():
            while running["active"]:
                if is_playing:
                    # Incrementing the observable triggers the UI diffing
                    char_data.frame = (char_data.frame + 1) % char_data.frame_count
                
                # Fixed tick rate (e.g., 12 FPS)
                await asyncio.sleep(1 / 12)
                
        # Offload the loop to Flet's internal task manager
        task = asyncio.create_task(loop(), name="ticker_manager :: loop")
        
        # Cleanup: Stops the ticker when the component is unmounted
        def cleanup():
            running["active"] = False
            task.cancel()
        
        return cleanup
    
    # Run the ticker once on mount
    # We include is_playing in dependencies if we want the loop to behave differently,
    # but here the loop itself checks the state inside the while.
    ft.use_effect(ticker_manager, [is_playing])
    
    # 3. Helpers for State Management
    def switch_state(state: str, count: int):
        char_data.state = state
        char_data.frame_count = count
        char_data.frame = 0 # Explicitly reset frame on state change
        
    return ft.Column(
        controls=[
            CharSprite(char_data),
            ft.Row([
                ft.Button("Idle", on_click=lambda _: switch_state("idle", 10)),
                ft.Button("Run", on_click=lambda _: switch_state("run", 8)),
                ft.Button("Attack 1", on_click=lambda _: switch_state("attack-1", 7)),
                ft.Button("Attack 2", on_click=lambda _: switch_state("attack-2", 7)),
                ft.Button("Death", on_click=lambda _: switch_state("death", 11)),
                ft.Button("Fall", on_click=lambda _: switch_state("fall", 3)),
                ft.Button("Take Hit", on_click=lambda _: switch_state("take-hit", 4)),
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Switch(
                label="Animations", value=is_playing,
                on_change=lambda e: set_is_playing(e.control.value)
            )
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

async def main(page: ft.Page):
    await test_init(page)
    page.render(GameView)

ft.run(main, assets_dir="../assets")