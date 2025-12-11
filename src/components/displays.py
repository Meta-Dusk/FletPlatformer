import flet as ft

from entities.features.entity_data import EntityStats, ARMOR_SCALING_CONSTANT
from setup import FontStyles
from utilities.components import try_update

class StatsDisplay(ft.Container):
    def __init__(
        self, stats: EntityStats
    ) -> None:
        self._stats = stats
        
        self.health_row = ft.DataRow(
            cells=[
                ft.DataCell(self._make_text("Health")),
                ft.DataCell(self._make_text("")),
                ft.DataCell(self._make_text("")),
                ft.DataCell(self._make_text("")),
                ft.DataCell(self._make_text("")),
            ]
        )
        self.armor_row = ft.DataRow(
            cells=[
                ft.DataCell(self._make_text("Armor")),
                ft.DataCell(self._make_text("")),
                ft.DataCell(self._make_text("")),
                ft.DataCell(self._make_text("")),
                ft.DataCell(self._make_text("")),
            ]
        )
        self.stamina_row = ft.DataRow(
            cells=[
                ft.DataCell(self._make_text("Stamina")),
                ft.DataCell(self._make_text("")),
                ft.DataCell(self._make_text("")),
                ft.DataCell(self._make_text("")),
                ft.DataCell(self._make_text("")),
            ]
        )
        self.movement_row = ft.DataRow(
            cells=[
                ft.DataCell(self._make_text("Movement Speed")),
                ft.DataCell(self._make_text("")),
                ft.DataCell(self._make_text("")),
                ft.DataCell(self._make_text("")),
                ft.DataCell(self._make_text("")),
            ]
        )
        self.damage_row = ft.DataRow(
            cells=[
                ft.DataCell(self._make_text("Attack Damage")),
                ft.DataCell(self._make_text("")),
                ft.DataCell(self._make_text("")),
                ft.DataCell(self._make_text("")),
                ft.DataCell(self._make_text("")),
            ]
        )
        self.crit_row = ft.DataRow(
            cells=[
                ft.DataCell(self._make_text("Critical Strikes")),
                ft.DataCell(self._make_text("")),
                ft.DataCell(self._make_text("")),
                ft.DataCell(self._make_text("")),
                ft.DataCell(self._make_text("")),
            ]
        )
        self.dash_row = ft.DataRow(
            cells=[
                ft.DataCell(self._make_text("Dash")),
                ft.DataCell(self._make_text("")),
                ft.DataCell(self._make_text("")),
                ft.DataCell(self._make_text("")),
                ft.DataCell(self._make_text("")),
            ]
        )
        self.jump_row = ft.DataRow(
            cells=[
                ft.DataCell(self._make_text("Jump")),
                ft.DataCell(self._make_text("")),
                ft.DataCell(self._make_text("")),
                ft.DataCell(self._make_text("")),
                ft.DataCell(self._make_text("")),
            ]
        )
        
        self.data_table = ft.DataTable(
            columns=[
                ft.DataColumn(label=self._make_text("Statistic", size=30)),
                ft.DataColumn(label=self._make_text("Current Value", size=30)),
                ft.DataColumn(label=self._make_text("Max Value", size=30)),
                ft.DataColumn(label=self._make_text("Modifiers", size=30)),
                ft.DataColumn(label=self._make_text("Description", size=30)),
            ],
            rows=[
                self.health_row,
                self.armor_row,
                self.stamina_row,
                self.movement_row,
                self.damage_row,
                self.crit_row,
                self.dash_row,
                self.jump_row,
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
        def set_text(row: ft.DataRow, values: list[str], skip_idx: int = 0) -> None:
            """
            Sets text with each value in `values` (if there is `Text`)
            in each column of `row`.
            """
            # zip(row.cells[1:], ...) tells Python to start looking at the 2nd cell
            # It effectively skips index 0 (the label) entirely
            for cell, new_val in zip(row.cells[1:], values):
                content = cell.content
                if isinstance(content, ft.Text):
                    content.value = new_val
        
        # Health
        hp_regen = f"+{self._stats.health_regen} HP / {self._stats.hp_regen_tick}s"
        set_text(row=self.health_row, values=[
            f"{round(self._stats.health, 1)} HP",
            f"{self._stats.max_health} Max HP",
            f"{hp_regen}",
            f"Regen HP after not getting damaged for {self._stats.hp_regen_delay}s.",
        ])
        
        # Stamina
        st_regen = f"+{self._stats.stamina_regen} ST / {self._stats.st_regen_tick}s"
        set_text(row=self.stamina_row, values=[
            f"{round(self._stats.stamina, 1)} ST",
            f"{self._stats.max_stamina} Max ST",
            f"{st_regen}",
            f"Regen ST after not sprinting for {self._stats.hp_regen_delay}s.",
        ])
        
        # Armor
        dmg_received: float = round(ARMOR_SCALING_CONSTANT / (ARMOR_SCALING_CONSTANT + self._stats.armor), 1)
        dmg_reduction = abs(dmg_received - 1)
        set_text(row=self.armor_row, values=[
            f"{self._stats.armor} DEF",
            "-",
            f"{dmg_reduction * 100}% Damage reduction.",
            f"{dmg_received * 100}% of Damage received.",
        ])
        
        # Movement
        sprint_speed: int = int(self._stats.movement_speed * self._stats.sprint_mult)
        set_text(row=self.movement_row, values=[
            f"{self._stats.movement_speed}px (~{self._stats.movement_speed * 20}px/s)",
            f"{sprint_speed}px (~{sprint_speed * 20}px/s)",
            f"{self._stats.sprint_mult}x when sprinting",
            f"Movement speed is multiplied by '{self._stats.sprint_mult}' when sprinting.",
        ])
        
        # Attack
        max_dmg = self._stats.attack_damage * self._stats.crit_damage
        set_text(row=self.damage_row, values=[
            f"{self._stats.attack_damage} ATK",
            f"{max_dmg} ATK",
            f"Knockback: {self._stats.attack_knockback}px",
            f"Each frame duration of the attack is: {self._stats.attack_frame_delay}s.",
        ])
        
        # Crit
        set_text(row=self.crit_row, values=[
            f"{self._stats.crit_damage}x ATK",
            "-",
            f"{self._stats.crit_chance}% Crit Chance",
            "Critical strikes happen by chance, and multiplies the damage amount per strike.",
        ])
        
        # Dash
        max_dash_dx = self._stats.dash_distance * self._stats.dash_strength
        set_text(row=self.dash_row, values=[
            f"{self._stats.dash_distance}px",
            f"{max_dash_dx}px",
            f"{self._stats.dash_strength}x Multiplier",
            f"You can dash every {self._stats.dash_cooldown}s for {self._stats.dash_st_cost} ST. When dashing, you are invincible for {self._stats.dash_inv_time}s.",
        ])
        
        # Jump
        max_jump_dy = int(self._stats.jump_distance * self._stats.jump_strength)
        set_text(row=self.jump_row, values=[
            f"{self._stats.jump_distance}px",
            f"{max_jump_dy}px",
            f"{self._stats.jump_strength}x Multiplier",
            f"You can jump for {self._stats.jump_st_cost} ST, and remain in air for {self._stats.jump_air_time}s.",
        ])
    
        try_update(self.data_table)