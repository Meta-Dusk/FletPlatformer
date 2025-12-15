import flet as ft
import math, random
from typing import Literal

from entities.enemy import Enemy, EnemyType, get_inversely_scaling_stats
from entities.entity import Entity, EntityStats, AnimConfig
from entities.projectile import ProjectileStats
from utilities.physics import Velocity
from utilities.components import try_update

from audio.sfx_data import SFXLibrary

sfx = SFXLibrary()

GoalStates = Literal["hover", "idle", "prep_melee", "prep_dash", "prep_ranged"]

class FlyingEye(Enemy):
    def __init__(
        self,
        page: ft.Page = None,
        audio_manager = None,
        target: Entity = None,
        name: str = None,
        entity_list: list[Entity] = None,
        projectile_manager = None,
        enemy_manager = None,
        *,
        debug: bool = False,
        simple_revive: bool = True
    ) -> None:
        if name is None: name = self.generate_rnd_name()
        
        rnd_health_range = (10, 30)
        min_mv_speed = 2.5
        rnd_health, rnd_mv_speed = get_inversely_scaling_stats(rnd_health_range, min_mv_speed)
        
        if name in {"Vision", "Eye-saac", "Peepers", "Iris", "Watcher"}:
            rnd_health *= 2.0
            rnd_mv_speed *= 1.5
        
        custom_stats = EntityStats(health=rnd_health, max_health=rnd_health, movement_speed=rnd_mv_speed)
        
        super().__init__(
            type=EnemyType.FLYING_EYE, page=page, audio_manager=audio_manager,
            target=target, name=name, entity_list=entity_list,
            projectile_manager=projectile_manager, enemy_manager=enemy_manager,
            debug=debug, stats=custom_stats, simple_revive=simple_revive
        )
        
        # Animation Config
        self.animations = {
            "flight": AnimConfig(frame_count=8, frame_duration=0.1),
            "take-hit": AnimConfig(frame_count=4, frame_duration=0.1, loop=False),
            "death": AnimConfig(frame_count=4, frame_duration=0.1, loop=False),
            
            # Attacks
            "attack-1": AnimConfig(8, 0.1, loop=False), # Melee Bite
            "attack-2": AnimConfig(8, 0.1, loop=False), # Dash
            "attack-3": AnimConfig(6, 0.1, loop=False), # Ranged
        }
        
        # Hitboxes
        self._make_self_hitbox(width=85, height=60, r_left=40, bottom=20)
        self._make_atk_hitbox(
            p1_r_left=80, p1_width=45, p1_height=35,
            p2_r_left=40, p2_width=85, p2_height=85,
            p1_bottom=20, p2_bottom=0
        )
        
        # Flight AI Variables
        self.hover_height = 150
        self.bob_timer: float = 0.0
        self.bob_speed: float = 2.0
        self.bob_amplitude: float = 20.0
        self.attack_cooldown_timer = 2.0
        
        # State Tracking
        self.current_ai_goal: GoalStates = "hover"
        self.attack_angle: float = 0.0
        
        # Ranges
        self.ranged_ideal_dist = 150
        self.dash_retreat_dist = 200
    
    def generate_rnd_name(self) -> str:
        names = [ # Total: 33
            # The "Cute" ones
            "Peepers", "Blinky", "Winky", "Squinty", "Looky", "Gawker",
            
            # The Puns
            "Seymour", "See-more", "Eye-van", "Eye-gor", "Eye-saac", "Eye-leen",
            
            # The Anatomy/Science ones
            "Iris", "Pupil", "Cornea", "Retina", "Sclera", "Lens", "Optic",
            
            # The "Action" ones
            "Gazer", "Watcher", "Stare", "Glare", "Ogle", "Scope", "Spy", "Peek",
            
            # The Weird ones
            "Clops", "Mono", "Orb", "Sphere", "Vis", "Vision"
        ]
        return random.choice(names)
    
    def tick_animation(self, dt: float) -> bool:
        """Override to handle 'flight' as the default state."""
        if self._tick_simple_revive(dt): return True
        if self.states.is_reviving: return False
        
        new_state = "flight"
        
        if self.states.dead: 
            new_state = "death"
        elif self.states.stunned: 
            new_state = "take-hit"
        elif self.states.is_attacking:
            new_state = f"attack-{self.states.attack_phase}"
        
        if new_state != self.current_anim_state:
            # Safety Valve for Attack Soft Lock
            if "attack" in self.current_anim_state and "attack" not in new_state:
                self.states.is_attacking = False
                self.states.dealing_damage = False
                self._modify_self_hitbox(reset=True)
                self.sprite.rotate.angle = 0 
                try_update(self.sprite)

            self.current_anim_state = new_state
            self.current_frame = 0
            self.anim_timer = 0.0
            self._update_sprite_src()
            self._handle_specific_frames()
            return True
            
        else:
            # ... (Standard timer logic) ...
            config = self.animations.get(self.current_anim_state)
            if config:
                self.anim_timer += dt
                if self.anim_timer >= config.frame_duration:
                    self.anim_timer = 0
                    self.current_frame += 1
                    if self.current_frame >= config.frame_count:
                        if config.loop: self.current_frame = 0
                        else: 
                            self.current_frame = config.frame_count - 1
                            self._on_animation_finish()
                    self._update_sprite_src()
                    self._handle_specific_frames()
                    return True
        return False

    def _handle_specific_frames(self):
        state = self.current_anim_state
        frame = self.current_frame
        
        match state:
            case "attack-1": # Melee Bite
                match frame:
                    case 5:
                        self.velocity.dx *= 0.8
                    case 6:
                        self.states.dealing_damage = True
                        self._toggle_atk_hb_border()
                    
            case "attack-2": # Dash Attack
                match frame:
                    case 0:
                        self.velocity.dx = 0
                        self.velocity.dy = 0
                        self._aim_at_target()
                    case 2:
                        speed = 12.0
                        angle = self.attack_angle
                        self.velocity.dx = math.cos(angle) * speed
                        self.velocity.dy = math.sin(angle) * speed
                        self._modify_self_hitbox(width=40, height=40, r_left=60, bottom=20)
                    case 5:
                        self.states.dealing_damage = True
                        self._toggle_atk_hb_border()
                    
            case "attack-3": # Ranged Shot
                match frame:
                    case 0:
                        self._aim_at_target()
                        self.velocity.dx = 0
                        self.velocity.dy = 0
                    case 3:
                        self.attack_ranged()
            
            case "take-hit":
                match frame:
                    case 1:
                        self._update_health_bar()
                        self._knockback_self(self.target)

    def _aim_at_target(self):
        """Rotates the sprite to look at the player."""
        if not self.target: return
        
        # 1. Calculate Offsets
        # Center points for accuracy
        self_x = self.stack.left + (self.stack.width / 2)
        self_y = self.stack.bottom + (self.stack.height / 2)
        
        target_x = self.target.stack.left + (self.target.stack.width / 2)
        target_y = self.target.stack.bottom + (self.target.stack.height / 2) + 65
        
        dx = target_x - self_x
        dy = target_y - self_y
        
        # 2. Calculate True Angle (Radians)
        # Standard Cartesian: 0 is Right, PI/2 is Up
        self.attack_angle = math.atan2(dy, dx)
        
        # 3. Handle Visuals (Flip + Rotate)
        # If target is to the LEFT (abs(angle) > 90 degrees)
        if abs(self.attack_angle) > (math.pi / 2):
            self._flip_sprite_x(-1) # Face Left
            
            # Compensation:
            # Since we flipped the sprite, we must adjust the rotation.
            # 1. Subtract PI to make the angle relative to "Left" being 0.
            # 2. Invert sign because flipping X inverts rotation direction (CW -> CCW).
            adjusted_angle = -1 * (self.attack_angle - math.pi)
            
            # Flet's Up is Positive, but rotate property is usually CW positive.
            # We negate it to match visual expectations.
            self.sprite.rotate.angle = -adjusted_angle 
            
        else:
            self._flip_sprite_x(1) # Face Right
            # Normal rotation
            self.sprite.rotate.angle = -self.attack_angle
        
        try_update(self.sprite)
    
    def attack_ranged(self):
        """Testing for projectile: 'Banshee Blast'."""
        angle = self.attack_angle
        
        proj_stats = ProjectileStats(
            velocity=Velocity(dx=10.0, dy=10.0),
            gravity=0,
            lifespan=3.0,
            damage=15,
            impact_damage=True,
            is_parryable=True,
            width=48, height=48,
            fly_anim=AnimConfig(3, 0.1),
            explode_anim=AnimConfig(8, 0.1, start_frame=3)
        )
        
        # Spawn
        super().attack_ranged(
            start_x=self.stack.left + (self.stack.width / 2) - (proj_stats.width / 2),
            start_y=self.stack.bottom + (self.stack.height / 2) - (proj_stats.height / 2) - 20,
            stats=proj_stats,
            src="images/enemies/flying_eye/projectile_0.png",
            sfx_upon_spawn=(sfx.explosions.sparkler_ignite, 0.5)
        )
        # Override velocity with precise angle
        # Access the last spawned projectile (a bit hacky but works)
        proj = self.projectile_manager.active_projectiles[-1]
        proj.dx = math.cos(angle) * proj_stats.velocity.dx
        proj.dy = math.sin(angle) * proj_stats.velocity.dy

    def tick_logic(self, dt: float) -> None:
        self.attack_cooldown_timer -= dt
        
        if self.states.dead or self.states.is_attacking or self.states.stunned:
            return
        
        self.bob_timer += dt
        bob_pixel_offset = math.sin(self.bob_timer * self.bob_speed) * self.bob_amplitude
        
        # --- IDLE STATE LOGIC ---
        # If target is missing or dead, force Idle
        if not self.target or self.target.states.dead:
            self.current_ai_goal = "idle"
        # If target is Alive but we are Idle, Wake up!
        elif self.current_ai_goal == "idle":
            self.current_ai_goal = "hover"
            
        if self.current_ai_goal == "idle":
            self.velocity.dx = 0
            
            # Hover relative to GROUND when idle
            base_hover_y = self.ground_level + 200
            target_y = base_hover_y + bob_pixel_offset
            
            diff_y = target_y - self.stack.bottom
            
            self.velocity.dy = diff_y * 0.1
            return # Stop here
        
        # --- COMBAT LOGIC ---
        # Only reached if we have a live target
        
        target_x = self.target.stack.left
        target_y = self.target.stack.bottom
        self_x = self.stack.left
        self_y = self.stack.bottom
        
        dist_x = target_x - self_x
        abs_dist_x = abs(dist_x)
        speed = self.stats.movement_speed
        
        # >>> GOAL: HOVER <<<
        if self.current_ai_goal == "hover":
            # Hover relative to PLAYER
            hover_y = target_y + self.hover_height
            
            # Apply Bobbing to the target height
            final_hover_y = hover_y + bob_pixel_offset
            
            # X Movement
            if abs_dist_x > 150: 
                self.velocity.dx = (1 if dist_x > 0 else -1) * speed
            else: 
                self.velocity.dx = 0
            
            # Y Movement (Spring to target)
            dist_y = final_hover_y - self_y
            self.velocity.dy = dist_y * 0.1
            
            self._flip_sprite_x(1 if dist_x > 0 else -1)

            if self.attack_cooldown_timer <= 0:
                self._pick_attack()

        # >>> GOAL: PREP MELEE (Get in face) <<<
        elif self.current_ai_goal == "prep_melee":
            # Define a strict "Biting Distance" (e.g., 10px overlap)
            # This is much smaller than the 'melee_range' used to TRIGGER the strategy
            biting_distance = 10
            
            # Target specific body parts
            target_head_y = target_y + 50 
            
            # Check Distances
            is_x_close = abs_dist_x <= biting_distance
            is_y_aligned = abs(self_y - target_head_y) <= 10
            
            if not is_x_close or not is_y_aligned:
                # 1. Close X Gap
                if not is_x_close:
                    self.velocity.dx = (1 if dist_x > 0 else -1) * (speed * 1.5) # Rush in fast
                else:
                    self.velocity.dx = 0
                
                # 2. Align Y (Dive/Rise)
                if not is_y_aligned:
                    self.velocity.dy = (1 if target_head_y > self_y else -1) * speed
                else:
                    self.velocity.dy = 0
            else:
                # We are close enough -> BITE!
                self._execute_attack(1)

        # >>> GOAL: PREP DASH (Back off) <<<
        elif self.current_ai_goal == "prep_dash":
            # Move AWAY until far enough
            if abs_dist_x < self.dash_retreat_dist:
                self.velocity.dx = (-1 if dist_x > 0 else 1) * speed # Reverse direction
                # Rise up high for the dive
                target_ceiling = target_y + 200
                if self_y < target_ceiling: self.velocity.dy = speed
            else:
                # We are far/high enough -> DASH!
                self._execute_attack(2)

        # >>> GOAL: PREP RANGED (Space out) <<<
        elif self.current_ai_goal == "prep_ranged":
            # Find the sweet spot (Goldilocks zone)
            if abs_dist_x < (self.ranged_ideal_dist - 50):
                # Too close, back up
                self.velocity.dx = (-1 if dist_x > 0 else 1) * speed
            elif abs_dist_x > (self.ranged_ideal_dist + 50):
                # Too far, move in
                self.velocity.dx = (1 if dist_x > 0 else -1) * speed
            else:
                # Just right -> SHOOT!
                self._execute_attack(3)
                
            # Align Y with player for a clear shot
            target_center_y = target_y + 60
            if abs(self_y - target_center_y) > 20:
                self.velocity.dy = (1 if target_center_y > self_y else -1) * speed

            self._flip_sprite_x(1 if dist_x > 0 else -1)

    def _execute_attack(self, phase: int):
        """Helper to transition from Prep to Action."""
        self.velocity.dx = 0 # Stop moving before starting anim
        self.velocity.dy = 0
        self.states.attack_phase = phase
        self.states.is_attacking = True
        self.attack_cooldown_timer = 2.0 + random.random()
        # Rotation reset is handled in _aim_at_target during the attack start
                
    def _pick_attack(self):
        """
        Choose a Strategy based on proximity + randomness:
        - Close? -> Melee
        - Far? -> Dash
        - Mid? -> Ranged
        """
        dist = abs(self._get_center_point() - self.target._get_center_point())
        
        if dist < self.type.value.melee_range:
            strategy = "melee"
        elif dist >= self.type.value.ranged_range:
            strategy = "dash"
        else:
            strategy = random.choice(["ranged", "dash"])

        # 2. Set the Intermediate Goal (The Prep Phase)
        if strategy == "melee":
            self.current_ai_goal = "prep_melee"
            
        elif strategy == "dash":
            self.current_ai_goal = "prep_dash"
            
        elif strategy == "ranged":
            self.current_ai_goal = "prep_ranged"
        
    def _on_animation_finish(self) -> None:
        """Called when a non-looping animation reaches the end."""
        state = self.current_anim_state
        
        if state == "death":
            self.velocity.dx = 0
            self.velocity.dy = 0
        
        elif state == "revive":
            self.states.is_reviving = False
            self.states.dead = False
            self.states.revivable = False
            self._reset_states()
            self._full_heal()
            self._update_health_bar()
            self._reset_tint()
            self.current_anim_state = "idle"
            self.current_frame = 0
            self._update_sprite_src()
            
        elif state == "take-hit":
            self.states.taking_damage = False
            self.states.is_moving = False
            self.states.dealing_damage = False
            self.states.stunned = False
            self._reset_tint()
            self._pick_attack()
            
        elif "attack" in state:
            # --- A. Unlock the State Machine ---
            self.states.is_attacking = False
            self.states.dealing_damage = False
            self._toggle_atk_hb_border()
            self._modify_self_hitbox(reset=True)
            
            # --- B. Reset Flying Specifics ---
            self.current_ai_goal = "hover"
            self.sprite.rotate.angle = 0
            try_update(self.sprite)
            
            # Stop momentum from dash attacks
            self.velocity.dx = 0
            self.velocity.dy = 0
            