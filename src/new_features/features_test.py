import flet as ft
from typing import Callable
from tests.test_templates import test_init

@ft.component
def CounterFunc():
    count: int # The current value
    set_count: Callable[[int], None] # The function to update the value
    count, set_count = ft.use_state(0)
    
    return ft.Row(
        controls=[
            ft.Text(f"Count: {count}"),
            ft.Button("Add", on_click=lambda _: set_count(count + 1))
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.CENTER
    )

async def main(page: ft.Page):
    await test_init(page)
    page.render(CounterFunc)
        
ft.run(main, assets_dir="../assets")