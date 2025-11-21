import flet as ft
from player_test import test, before_test


async def main(page: ft.Page):
    await test(page)
    
def before_main(page: ft.Page):
    before_test(page)
    

if __name__ == "__main__":
    ft.run(main=main, before_main=before_main)