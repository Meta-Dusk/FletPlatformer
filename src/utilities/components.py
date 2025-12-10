import flet as ft
import asyncio

def try_update(*controls: ft.Control):
    """
    Updates multiple controls safely.\n
    As of Flet version `0.70.0.dev6787`, accessing the `.page` property
    will raise a `RuntimeError` exception.
    """
    for control in controls:
        if control is None: continue
        try: control.update()
        except RuntimeError: pass

def get_dur(animation_property: ft.AnimationValue) -> float:
    """Returns the amount of seconds the animation's duration has."""
    if isinstance(animation_property.duration, int):
        seconds = round(animation_property.duration / 1000, 3)
    elif isinstance(animation_property.duration, ft.Duration):
        seconds = animation_property.duration.in_milliseconds
    else:
        raise ValueError("'duration' of 'animation_property' is neither 'int' or 'Duration'.")
    return seconds

async def await_for_dur(animation_property: ft.AnimationValue) -> None:
    """Awaits the duration of the provided animation."""
    await asyncio.sleep(get_dur(animation_property))