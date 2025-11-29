import flet as ft

def get_center(left: float, bottom: float, width: float, height: float) -> tuple[float, float]:
    """Returns the (x, y) center of an entity."""
    return (left + (width / 2), bottom + (height / 2))

def is_in_x_range(
    entity1_stack: ft.Stack, entity1_w: float,
    entity2_stack: ft.Stack, entity2_w: float,
    threshold: float
) -> bool:
    """
    Checks if two stacks are within a certain X-axis distance of each other,
    ignoring their vertical (Y) positions.
    Useful for triggering aggro even if the target is jumping or on a different platform.
    """
    # 1. Get Center X Points
    # Center X = Left + (Width / 2)
    c1_x = entity1_stack.left + (entity1_w / 2)
    c2_x = entity2_stack.left + (entity2_w / 2)

    # 2. Calculate Distance (Absolute difference)
    dx = abs(c1_x - c2_x)

    # 3. Compare
    return dx <= threshold

def is_in_range(
    entity1_stack: ft.Stack, entity1_w: float, entity1_h: float,
    entity2_stack: ft.Stack, entity2_w: float, entity2_h: float,
    threshold: float
) -> bool:
    """Checks if two stacks are within a certain distance (threshold) of each other."""
    # 1. Get Center Points
    c1_x, c1_y = get_center(entity1_stack.left, entity1_stack.bottom, entity1_w, entity1_h)
    c2_x, c2_y = get_center(entity2_stack.left, entity2_stack.bottom, entity2_w, entity2_h)

    # 2. Calculate Squared Euclidean Distance
    # (a^2 + b^2 = c^2)
    dx = c1_x - c2_x
    dy = c1_y - c2_y
    distance_squared = (dx * dx) + (dy * dy)

    # 3. Compare (Squared is faster than using sqrt)
    return distance_squared <= (threshold * threshold)

def check_collision(
    r1_left: float, r1_bottom: float, r1_w: float, r1_h: float,
    r2_left: float, r2_bottom: float, r2_w: float, r2_h: float
) -> bool:
    """
    Axis-Aligned Bounding Box (AABB) collision detection.
    Returns True if the two rectangles overlap.
    """
    # Calculate Edges
    r1_right = r1_left + r1_w
    r1_top = r1_bottom + r1_h
    
    r2_right = r2_left + r2_w
    r2_top = r2_bottom + r2_h

    # Check for NO overlap (The "Gap" Logic)
    # If one is too far to the left, right, above, or below, they aren't touching.
    if (r1_right < r2_left or   # R1 is to the left of R2
        r1_left > r2_right or   # R1 is to the right of R2
        r1_top < r2_bottom or   # R1 is below R2
        r1_bottom > r2_top):    # R1 is above R2
        return False

    return True