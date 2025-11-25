import flet as ft

# --- CONSTANTS ---
IMG_WIDTH = 928
IMG_HEIGHT = 793
SCALE = 2
DEFAULT_DURATION = 1000

# Map index to specific durations (None = No animation)
LAYER_DURATIONS = {
    0: None,       # ? Static layer
    1: 2000,
    2: 1800,
    3: 120000,      # ? Dynamic layer (Light)
    4: 1600,
    5: 1400,
    6: 120000,      # ? Dynamic layer (Light)
    7: 1200,
}

# Layers that need to be wider (3 and 6)
WIDE_LAYERS = {3, 6}

def bg_image_forest(index: int, page: ft.Page) -> ft.Image:
    """Returns an image configured for the background."""
    # Get duration from dict, default to 1000 if not found
    duration = LAYER_DURATIONS.get(index, DEFAULT_DURATION)
    
    # Create Animation Object
    if duration is None: anim = None
    else: anim = ft.Animation(duration, ft.AnimationCurve.EASE_IN_OUT)
    
    # If index is 3 or 6, use 4x width, otherwise 2x
    width_mult = 4 if index in WIDE_LAYERS else 2

    return ft.Image(
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
    )