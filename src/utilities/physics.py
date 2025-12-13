from dataclasses import dataclass

@dataclass
class Velocity:
    dx: float = 0.0
    dy: float = 0.0

def calculate_velocity_for_target(
    start_x: float, start_y: float,
    target_x: float, target_y: float,
    speed: float, gravity: float
) -> tuple[float, float, int]:
    """
    Calculates the physics values needed to hit a specific point.
    Returns: (vx, vy, direction)
    """
    dx = target_x - start_x
    dy = target_y - start_y
    
    # 1. Determine Direction
    direction = 1 if dx > 0 else -1
    
    # 2. Calculate Time to Impact (t = distance / speed)
    # Avoid division by zero if target is directly above/below
    if abs(dx) < 1.0: 
        time = 1.0 # Fallback time
    else:
        time = abs(dx) / speed

    # 3. Solve for Vertical Velocity (vy)
    # formula: vy = (dy + 0.5 * g * t^2) / t
    # Note: We use 'speed' as horizontal speed.
    # We add 0.5 * g * t because we need to counteract the gravity that will pull it down during flight.
    needed_vy = (dy + (0.5 * gravity * (time ** 2))) / time
    
    return speed, needed_vy, direction