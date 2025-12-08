import flet as ft

from entities.features.entity_data import EntityStats, ARMOR_SCALING_CONSTANT
from setup import FontStyles

class StatsDisplay(ft.Container):
    def __init__(
        self, stats: EntityStats
    ) -> None:
        self._stats = stats
        
        self.data_table = ft.DataTable(
            columns=[
                ft.DataColumn(label=self._make_text("Statistic", size=30)),
                ft.DataColumn(label=self._make_text("Current Value", size=30)),
                ft.DataColumn(label=self._make_text("Max Value", size=30)),
                ft.DataColumn(label=self._make_text("Modifiers", size=30)),
                ft.DataColumn(label=self._make_text("Description", size=30)),
            ],
            rows=[
                ft.DataRow(
                    cells=[
                        ft.DataCell(self._make_text("Health")),
                        ft.DataCell(self._make_text("")),
                        ft.DataCell(self._make_text("")),
                        ft.DataCell(self._make_text("")),
                        ft.DataCell(self._make_text("")),
                    ]
                ),
                ft.DataRow(
                    cells=[
                        ft.DataCell(self._make_text("Armor")),
                        ft.DataCell(self._make_text("")),
                        ft.DataCell(self._make_text("")),
                        ft.DataCell(self._make_text("")),
                        ft.DataCell(self._make_text("")),
                    ]
                ),
                ft.DataRow(
                    cells=[
                        ft.DataCell(self._make_text("Stamina")),
                        ft.DataCell(self._make_text("")),
                        ft.DataCell(self._make_text("")),
                        ft.DataCell(self._make_text("")),
                        ft.DataCell(self._make_text("")),
                    ]
                ),
                ft.DataRow(
                    cells=[
                        ft.DataCell(self._make_text("Movement Speed")),
                        ft.DataCell(self._make_text("")),
                        ft.DataCell(self._make_text("")),
                        ft.DataCell(self._make_text("")),
                        ft.DataCell(self._make_text("")),
                    ]
                ),
                ft.DataRow(
                    cells=[
                        ft.DataCell(self._make_text("Attack Damage")),
                        ft.DataCell(self._make_text("")),
                        ft.DataCell(self._make_text("")),
                        ft.DataCell(self._make_text("")),
                        ft.DataCell(self._make_text("")),
                    ]
                ),
                ft.DataRow(
                    cells=[
                        ft.DataCell(self._make_text("Critical Strikes")),
                        ft.DataCell(self._make_text("")),
                        ft.DataCell(self._make_text("")),
                        ft.DataCell(self._make_text("")),
                        ft.DataCell(self._make_text("")),
                    ]
                ),
            ],
            border_radius=8,
            bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
            border=ft.Border.all(1, ft.Colors.BLACK)
        )
        
        self._update_texts()
        super().__init__(content=self.data_table, alignment=ft.Alignment.CENTER, visible=False)
    
    def _make_text(
        self, text: str, size: ft.Number = 16,
        font_family: FontStyles = FontStyles.MEDODICA
    ) -> ft.Text:
        return ft.Text(value=text, size=size, font_family=font_family)
    
    def did_mount(self):
        if isinstance(self.parent, ft.Stack):
            self.top = 50
            self.update()
    
    def _update_texts(self) -> None:
        """Updates the display texts."""
        dt_hp = self.data_table.rows[0]
        dt_ar = self.data_table.rows[1]
        dt_st = self.data_table.rows[2]
        dt_mv = self.data_table.rows[3]
        dt_atk = self.data_table.rows[4]
        dt_cs = self.data_table.rows[5]
        
        # Health
        hp_regen = f"+{self._stats.health_regen} HP / {self._stats.hp_regen_tick}s"
        dt_hp.cells[1].content.value = f"{round(self._stats.health, 1)} HP"
        dt_hp.cells[2].content.value = f"{self._stats.max_health} Max HP"
        dt_hp.cells[3].content.value = f"{hp_regen}"
        dt_hp.cells[4].content.value = f"Regen HP after not getting damaged for {self._stats.hp_regen_delay}s."
        
        # Stamina
        st_regen = f"+{self._stats.stamina_regen} ST / {self._stats.st_regen_tick}s"
        dt_st.cells[1].content.value = f"{round(self._stats.stamina, 1)} ST"
        dt_st.cells[2].content.value = f"{self._stats.max_stamina} Max ST"
        dt_st.cells[3].content.value = f"{st_regen}"
        dt_st.cells[4].content.value = f"Regen ST after not sprinting for {self._stats.hp_regen_delay}s."
        
        # Armor
        dmg_reduction: float = round(ARMOR_SCALING_CONSTANT / (ARMOR_SCALING_CONSTANT + self._stats.armor), 1)
        dt_ar.cells[1].content.value = f"{self._stats.armor} DEF"
        dt_ar.cells[2].content.value = "-"
        dt_ar.cells[3].content.value = "-"
        dt_ar.cells[4].content.value = f"{dmg_reduction * 100}% of Damage received."
        
        # Movement
        sprint_speed: int = int(self._stats.movement_speed * self._stats.sprint_mult)
        dt_mv.cells[1].content.value = f"{self._stats.movement_speed}px (~{self._stats.movement_speed * 20}px/s)"
        dt_mv.cells[2].content.value = f"{sprint_speed}px (~{sprint_speed * 20}px/s)"
        dt_mv.cells[3].content.value = f"{self._stats.sprint_mult}x when sprinting"
        dt_mv.cells[4].content.value = f"Movement speed is multiplied by '{self._stats.sprint_mult}' when sprinting."
        
        # Attack
        max_dmg = self._stats.attack_damage * self._stats.crit_damage
        dt_atk.cells[1].content.value = f"{self._stats.attack_damage} ATK"
        dt_atk.cells[2].content.value = f"{max_dmg} ATK"
        dt_atk.cells[3].content.value = "-"
        dt_atk.cells[4].content.value = f"Each frame duration of the attack is: {self._stats.attack_frame_delay}s."
        
        # Crit
        dt_cs.cells[1].content.value = f"{self._stats.crit_damage}x ATK"
        dt_cs.cells[2].content.value = "-"
        dt_cs.cells[3].content.value = f"{self._stats.crit_chance}%"
        dt_cs.cells[4].content.value = "Critical strikes happen by chance, and multiplies the damage amount per strike."
        