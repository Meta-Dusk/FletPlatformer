import flet as ft
from typing import Literal, Any
from dataclasses import dataclass

from utilities.components import try_update

@dataclass
class KeySpr:
    src: str
    width: ft.Number
    height: ft.Number

@dataclass
class Keys:
    a = KeySpr("images/keyboard/pxkw_a.png", 16, 16)
    c = KeySpr("images/keyboard/pxkw_c.png", 16, 16)
    d = KeySpr("images/keyboard/pxkw_d.png", 16, 16)
    v = KeySpr("images/keyboard/pxkw_v.png", 16, 16)
    enter = KeySpr("images/keyboard/pxkw_enter.png", 32, 16)
    f11 = KeySpr("images/keyboard/pxkw_f11.png", 16, 16)
    forwardslash = KeySpr("images/keyboard/pxkw_forwardslash.png", 16, 16)
    shift = KeySpr("images/keyboard/pxkw_shift_icon.png", 32, 16)
    space = KeySpr("images/keyboard/pxkw_space_2.png", 32, 16)
    tab = KeySpr("images/keyboard/pxkw_tab.png", 32, 16)

@dataclass
class SpriteList:
    keys = Keys()


class IconSprite(ft.Container):
    """Sprite for icons."""
    def __init__(
        self, src: KeySpr = None, *, str_src: str = None,
        width: ft.Number = None, height: ft.Number = None,
        filter_quality: ft.FilterQuality = ft.FilterQuality.NONE,
        fit: ft.BoxFit = ft.BoxFit.COVER, gapless_playback: bool = True,
        scale: ft.Scale = ft.Scale(scale_x=2, scale_y=2),
        padding: ft.PaddingValue = 8, data: Any = None
    ) -> None:
        if src is None:
            _src = str_src
            _width = width
            _height = height
        else:
            _src, _width, _height = src.src, src.width, src.height
        
        self.spr = ft.Image(
            src=_src, width=_width, height=_height, filter_quality=filter_quality,
            fit=fit, gapless_playback=gapless_playback, scale=scale,
            error_content=ft.Container(
                content=ft.Text("Error", ft.Colors.ON_ERROR_CONTAINER),
                bgcolor=ft.Colors.ERROR_CONTAINER, width=_width, height=_height
            ),
            color_blend_mode=ft.BlendMode.MODULATE
        )
        
        super().__init__(content=self.spr, padding=padding, alignment=ft.Alignment.CENTER, data=data)
    
    def set_tint(self, color: ft.ColorValue, opacity: float = 1.0) -> None:
        self.spr.color = ft.Colors.with_opacity(opacity, color)
        self.spr.update()

class Sprite(ft.Image):
    """All sprites will have twice their scale for better visuals."""
    def __init__(
        self, src: str, width: ft.Number, height: ft.Number, *,
        filter_quality: ft.FilterQuality = ft.FilterQuality.NONE,
        fit: ft.BoxFit = ft.BoxFit.COVER, gapless_playback: bool = True,
        scale: ft.Scale = ft.Scale(scale_x=2, scale_y=2),
        offset: ft.Offset = ft.Offset(0, 0.145), debug: bool = False
    ) -> None:
        super().__init__(
            src=src, width=width, height=height, filter_quality=filter_quality,
            fit=fit, gapless_playback=gapless_playback, scale=scale, offset=offset
        )
        self.debug = debug
        self._handler_str = "Sprite"
    
    def _debug_msg(self, msg: str, *, end: str = None, include_handler: bool = True) -> None:
        """A simple debug message for simple logging."""
        if self.debug:
            if include_handler: print(f"[{self._handler_str}] {msg}", end=end)
            else: print(msg, end=end)
    
    def change_src(self, new_src: str, update_ctrl: bool = True) -> None:
        """Swap the `src` and optionally update."""
        self.src = new_src
        if update_ctrl: try_update(self)
    
    def flip_x(self, direction: Literal[-1, 1] = None, update_ctrl: bool = True) -> None:
        """Flip the image on the x-axis."""
        if direction is None:
            self._debug_msg(f"No provided direction, using self as reference: ", end="")
            direction = -1 if self.scale.scale_x > 0 else 1
            self._debug_msg(direction, include_handler=False)
        new_scale = abs(self.scale.scale_x) * direction
        self.scale = ft.Scale(scale_x=new_scale, scale_y=self.scale.scale_y)
        if update_ctrl: try_update(self)
        