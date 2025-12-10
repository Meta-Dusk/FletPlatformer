import flet as ft

# * === CONSTANTS ===
IMG_WIDTH: int = 928
IMG_HEIGHT: int = 793
SCALE: float = 2
DEFAULT_DURATION: int = 1000
DEFAULT_ANIM_CURVE: ft.AnimationCurve = ft.AnimationCurve.EASE_IN_OUT
LIGHT_DURATION: ft.Duration = ft.Duration(minutes=5)

# ? Map index to specific durations (None = No animation)
LAYER_DURATIONS: dict[int, tuple[int, ft.AnimationCurve]] = {
    1: (2000, ft.AnimationCurve.EASE_IN_OUT),
    2: (1800, ft.AnimationCurve.EASE_IN_OUT),
    3: (LIGHT_DURATION.in_milliseconds, ft.AnimationCurve.LINEAR),   # ? Dynamic layer (Light)
    4: (1600, ft.AnimationCurve.EASE_IN_OUT),
    5: (1400, ft.AnimationCurve.EASE_IN_OUT),
    6: (LIGHT_DURATION.in_milliseconds, ft.AnimationCurve.LINEAR),   # ? Dynamic layer (Light)
    7: (1200, ft.AnimationCurve.EASE_IN_OUT),
}

# ? Layers that need to be wider (3 and 6)
WIDE_LAYERS: set[int] = {3, 6}

def bg_image_forest(index: int, page: ft.Page) -> ft.Image:
    """Returns an image configured for the background."""
    # Get duration from dict, default to the defaults if not found
    duration, anim_curve = LAYER_DURATIONS.get(index, (DEFAULT_DURATION, DEFAULT_ANIM_CURVE))
    
    # Create Animation Object
    if duration is None: anim = None
    else: anim = ft.Animation(duration, anim_curve)
    
    # If index is 3 or 6, use 4x width, otherwise 2x
    width_mult = 4 if index in WIDE_LAYERS else 2
    
    return ft.Image(
        # Setup
        src=f"images/backgrounds/night_forest/{index}.png",
        data=index,
        
        # Dimensions
        width=IMG_WIDTH * width_mult,
        height=IMG_HEIGHT * 2,
        scale=SCALE,
        
        # Placement
        left=page.width / 2,
        bottom=0,
        offset=ft.Offset(0, 0.05),
        
        # Rendering Quality
        filter_quality=ft.FilterQuality.NONE,
        gapless_playback=True,
        
        # Repetition Logic
        repeat=ft.ImageRepeat.REPEAT if index == 0 else ft.ImageRepeat.REPEAT_X,
        
        # Animation
        animate_position=anim,
        opacity=1
    )
    
def add_infinite_layer(stack: ft.Stack, index: int, page: ft.Page):
    # Determine Width
    # Layers 3 & 6 are 4x width (928*4), others are 2x (928*2)
    is_wide = index in [3, 6]
    base_width = 928 * (4 if is_wide else 2)
    
    # Spawn 3 copies (Left, Center, Right)
    for i in range(3):
        img = bg_image_forest(index, page)
        
        # Position: i=0 (Left), i=1 (Center), i=2 (Right)
        # Center the middle image on the screen
        start_x = (page.width / 2) + ((i - 1) * base_width) - (base_width / 2)
        
        img.left = start_x
        
        # Store Width for Wrapping Logic
        # We attach it to .data so the loop knows how wide this specific image is
        img.data = {"layer": index, "width": base_width}
        
        stack.controls.append(img)
        