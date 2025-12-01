import flet as ft


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