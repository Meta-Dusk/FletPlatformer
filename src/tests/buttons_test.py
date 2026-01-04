import flet as ft

from components.buttons import SimpleButton
from tests.test_templates import test_init

@ft.component
def TestView() -> ft.Control:
    buttons_column = ft.Column(
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )
    for i in range(5):
        buttons_column.controls.append(
            SimpleButton(ft.Text(f"Button {i}", size=20), width=200, height=100)
        )
    return buttons_column

async def test(page: ft.Page):
    await test_init(page)
    page.render(TestView)

ft.run(test, assets_dir="../assets")