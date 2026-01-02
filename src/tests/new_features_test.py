import flet as ft
from tests.test_templates import test_init

@ft.component
def Counter():
    # count: the current value
    # set_count: the function to update the value
    count, set_count = ft.use_state(0)
    
    return ft.Row(
        controls=[
            ft.Text(f"Count: {count}"),
            ft.ElevatedButton("Add", on_click=lambda _: set_count(count + 1))
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.CENTER
    )

async def main(page: ft.Page):
    await test_init(page)
    
    page.render(Counter)
        
ft.run(main, assets_dir="../assets")