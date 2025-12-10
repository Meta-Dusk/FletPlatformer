import flet as ft

from components.popups import SimpleNotification, SimpleDialog
from tests.test_templates import test_init

async def test(page: ft.Page) -> None:
    await test_init(page)
    
    def open_notif(_) -> None:
        notif = SimpleNotification("Test notification!", width=200)
        page.overlay.append(notif)
        print(f"Overlay len: {len(page.overlay)}")
    
    def open_dialog(_) -> None:
        dialog = SimpleDialog("Dialog Test", "I am a dialog test!")
        page.overlay.append(dialog)
        print(f"Overlay len: {len(page.overlay)}")
    
    page.add(
        ft.Button("Open Notification", on_click=open_notif),
        ft.Button("Open Dialog", on_click=open_dialog),
    )
    
ft.run(test, assets_dir="../assets")