import asyncio
import flet as ft
from setup import before_main_ui
from game_manager import GameManager

# * As of version >= 0.1.2, running the project in dev mode requires the following command:
# * uv pip install -e .
# ? It will fix the import complications

def silence_event_loop_closed(loop: asyncio.AbstractEventLoop, context: dict[str, any]) -> None:
    """Custom exception handler to silence the specific 'WinError 64' on Windows shutdown."""
    exception = context.get("exception")
    
    # ? WinError 64: "The specified network name is no longer available"
    if isinstance(exception, OSError) and getattr(exception, "winerror", 0) == 64: return
    
    # ? ConnectionResetError: Often happens alongside the socket disconnect
    if isinstance(exception, ConnectionResetError): return

    # ? Pass everything else to the default handler
    loop.default_exception_handler(context)

async def main(page: ft.Page):
    # Attach the typed handler to the running loop
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(silence_event_loop_closed)
    game = GameManager(page)
    await game()
    
if __name__ == "__main__": ft.run(main=main, before_main=before_main_ui)