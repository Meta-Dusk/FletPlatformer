import flet as ft
from dataclasses import dataclass, field, replace

from utilities.components import try_update
from entities.features.entity_data import Factions
from images import Sprite


@dataclass
class HitboxPos:
    """
    Each hitbox has coordinates, originating from the left and bottom.
    The prefixes `l_*` and `r_*` refer to them.\n
    These mean **orientation** when the entity faces either the right or the left.
    """
    l_left: int = 0
    l_bottom: int = 0
    r_left: int = 0
    r_bottom: int = 0

@dataclass
class Hitbox:
    """Attack hitboxes only support two as of now."""
    faction: Factions
    attack_phases: dict[int, HitboxPos] = field(default_factory=lambda: {
        1: HitboxPos(),
        2: HitboxPos()
    })
    current_atk_phase: int = 0

@dataclass
class SimpleHitbox:
    """Used with non-attack hitboxes."""
    positions: HitboxPos = field(default_factory=lambda: HitboxPos())

class DamageHitbox:
    def __init__(self) -> None:
        """
        Instantiates essential properties used by hitboxes:\n
        - `sprite`
        - `stack`
        - `_atk_hitboxes`
        - `_hitbox`
        """
        # Entity components references
        self.sprite: Sprite
        self.stack: ft.Stack
        self._atk_hitboxes: list[ft.Container]
        self._hitbox: ft.Container
    
    def _flip_atk_hb(self) -> None:
        """Updates attack hitbox positions based on facing direction."""
        if not self._atk_hitboxes: return

        # If scale.x > 0, facing RIGHT. If < 0, facing LEFT.
        is_facing_right = self.sprite.scale.scale_x > 0
        for i, hb in enumerate(self._atk_hitboxes):
            phase_id = i + 1 # Phase 1, Phase 2...
            data: Hitbox = hb.data
            
            # Get the position config for this specific phase
            pos_config: HitboxPos = data.attack_phases.get(phase_id)
            if not pos_config: continue

            if is_facing_right: hb.left = pos_config.r_left
                # hb.bottom = pos_config.r_bottom # ? If vertical changes needed
            else: hb.left = pos_config.l_left
                # hb.bottom = pos_config.l_bottom

        # Force visual update
        try_update(*self._atk_hitboxes)
    
    def _flip_self_hb(self) -> None:
        """Updates self hitbox positions based on facing direction."""
        if self._hitbox is None or self._hitbox.data is None: return

        # 1. Determine Direction
        current_scale = self.sprite.scale.scale_x if hasattr(self.sprite.scale, "scale_x") else self.sprite.scale
        is_facing_right = current_scale > 0
        
        # 2. Get Data
        data: SimpleHitbox = self._hitbox.data
        pos: HitboxPos = data.positions

        # 3. Apply Offset
        if is_facing_right:
            self._hitbox.left = pos.r_left
            self._hitbox.bottom = pos.r_bottom
        else:
            self._hitbox.left = pos.l_left
            self._hitbox.bottom = pos.l_bottom
        
        # 4. Visual Update
        try_update(self._hitbox)
    
    def _make_self_hitbox(
        self, width: int = None, height: int = None,
        r_left: int = 0, bottom: int = 0
    ) -> None:
        """Makes the target-able hitbox and saves defaults."""
        if width is None: width = self.sprite.width
        if height is None: height = self.sprite.height
        
        l_left = self.sprite.width - r_left - width
        
        # Create the Position Data
        pos_data = HitboxPos(
            l_left=l_left, l_bottom=bottom,
            r_left=r_left, r_bottom=bottom
        )
        
        hb_pos_data = SimpleHitbox(pos_data)
        
        # --- NEW: Save a Backup of the Defaults ---
        # We use 'replace' to create a separate copy in memory
        self._default_self_hb_pos = replace(pos_data)
        self._default_self_hb_dims = (width, height)
        # ------------------------------------------
        
        hitbox = ft.Container(
            width=width, height=height,
            left=r_left, bottom=bottom,
            data=hb_pos_data,
        )
        
        self._hitbox = hitbox
        self.stack.controls.append(self._hitbox)
        try_update(self.stack)
    
    def _make_atk_hitbox(
        self, p1_r_left: int, p1_width: int, p1_height: int,
        p2_r_left: int, p2_width: int, p2_height: int,
        bottom: int = 0
    ) -> None:
        """
        Makes the attack hitboxes for the various attack phases. Only supports two attack phases.\n
        There will be two hitboxes generated (p1, p2). Provide their local offsets with `*_r_left`.\n
        These are the offsets if the entity is facing to the right.\n
        Additionally, these offsets are _relative_ to the `self.stack`, which is where the hitboxes reside.\n
        These hitboxes must also have a `width` and a `height`.
        """
        hb_bottom = bottom
        p1_l_left = self.sprite.width - p1_r_left - p1_width # Phase 1 Config
        p2_l_left = self.sprite.width - p2_r_left - p2_width # Phase 2 Config
        
        hb_pos_data = {
            1: HitboxPos(
                l_left=p1_l_left, l_bottom=hb_bottom, 
                r_left=p1_r_left, r_bottom=hb_bottom
            ),
            2: HitboxPos(
                l_left=p2_l_left, l_bottom=hb_bottom, 
                r_left=p2_r_left, r_bottom=hb_bottom
            )
        }
        hb_data_1 = Hitbox(self.faction, hb_pos_data, 1)
        hb_data_2 = Hitbox(self.faction, hb_pos_data, 2)
        
        # Create Containers (Store them in self._atk_hitboxes)
        atk_hitbox_1 = ft.Container(
            width=p1_width, height=p1_height, 
            left=p1_r_left, bottom=hb_bottom,
            data=hb_data_1
        )
        
        atk_hitbox_2 = ft.Container(
            width=p2_width, height=p2_height, 
            left=p2_r_left, bottom=hb_bottom,
            data=hb_data_2
        )
        
        self._atk_hitboxes = [atk_hitbox_1, atk_hitbox_2]
        self.stack.controls.extend(self._atk_hitboxes)
        try_update(self.stack)
    
    def _toggle_atk_hb_border(self) -> None:
        """
        Toggles the border and attack frames of the attack hitboxes.
        Also shows the next attack hitbox in the attack sequence.
        """
        if not self._atk_hb_show: return
        
        hb_count = len(self._atk_hitboxes)
        hb_next: int = 1 if hb_count == self.states.attack_phase else 2
        bgcolor = ft.Colors.with_opacity(0.15, ft.Colors.RED)
        border = ft.Border.all(1, ft.Colors.with_opacity(0.5, ft.Colors.RED))
        
        for atk_hb in self._atk_hitboxes:
            if not atk_hb.data: continue
            data: Hitbox = atk_hb.data
            
            if self.states.dead:
                atk_hb.border = None
                atk_hb.bgcolor = None
                continue
            
            if self.states.is_attacking:
                if self.states.attack_phase == data.current_atk_phase:
                    atk_hb.border = border
                    if self.states.dealing_damage: atk_hb.bgcolor = bgcolor
                    else: atk_hb.bgcolor = None
            else:
                if data.current_atk_phase == hb_next: atk_hb.border = border
                else:
                    atk_hb.border = None
                    atk_hb.bgcolor = None
            try_update(atk_hb)
    
    def _modify_self_hitbox(
        self, width: int = None, height: int = None, 
        r_left: int = None, bottom: int = None,
        *, reset: bool = False
    ) -> None:
        """
        Temporarily resizes/moves the hurtbox.
        Pass `reset=True` to restore original defaults.
        """
        if self._hitbox is None or self._hitbox.data is None: return
        
        data: SimpleHitbox = self._hitbox.data
        pos: HitboxPos = data.positions
        
        # --- RESET LOGIC ---
        if reset:
            # Restore Dimensions
            width, height = self._default_self_hb_dims
            
            # Restore Positions (Copy the backup back to active data)
            # We must map the fields manually or use replace logic
            def_pos = self._default_self_hb_pos
            pos.l_left = def_pos.l_left
            pos.l_bottom = def_pos.l_bottom
            pos.r_left = def_pos.r_left
            pos.r_bottom = def_pos.r_bottom
            
            # Set local vars so visual update below works
            current_width = width
            current_height = height
            # We don't need r_left logic for reset, data is already restored
            
        else:
            # --- NORMAL LOGIC ---
            current_width = width if width is not None else self._hitbox.width
            current_height = height if height is not None else self._hitbox.height
            current_r_left = r_left if r_left is not None else pos.r_left
            current_bottom = bottom if bottom is not None else pos.r_bottom

            # Update Internal Math
            pos.r_left = current_r_left
            pos.l_left = self.sprite.width - current_r_left - current_width
            pos.r_bottom = current_bottom
            pos.l_bottom = current_bottom
        
        # --- VISUAL UPDATE ---
        self._hitbox.width = current_width
        self._hitbox.height = current_height
        
        # Apply based on facing
        current_scale = self.sprite.scale.scale_x if hasattr(self.sprite.scale, "scale_x") else self.sprite.scale
        is_facing_right = current_scale > 0
        
        if is_facing_right:
            self._hitbox.left = pos.r_left
            self._hitbox.bottom = pos.r_bottom
        else:
            self._hitbox.left = pos.l_left
            self._hitbox.bottom = pos.l_bottom
            
        try_update(self._hitbox)