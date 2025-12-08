import flet as ft

from tests.test_templates import test_init
from components.displays import StatsDisplay
from entities.features.entity_data import EntityStats

async def test(page: ft.Page):
    await test_init(page)
    
    sample_stats = EntityStats()
    stats_display = StatsDisplay(sample_stats)
    stats_display.visible = True
    
    page.add(stats_display)

ft.run(test, assets_dir="../assets")