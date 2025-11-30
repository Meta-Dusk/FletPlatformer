import asyncio
import flet as ft

from setup import before_main_ui
from game_manager import GameManager
from utilities.events import silence_event_loop_closed

# * As of version >= 0.1.2, running the project in dev mode requires the following command:
# * uv pip install -e .
# ? It will fix the import complications

async def main(page: ft.Page):
    # Called here as supplying this in `ft.run` somehow doesn't work anymore
    before_main_ui(page)
    
    # Attach the typed handler to the running loop
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(silence_event_loop_closed)
    game = GameManager(page)
    await game()

ft.run(main)