import flet as ft
import base64, io, asyncio, inspect
from PIL import Image
from pathlib import Path

class NinePatchButton(ft.Container):
    """
    A button made with the 9-slicing technique.
    Animations need 4 frames, with the last frame being
    the resting state.
    """
    def __init__(
        self, src: str | Path, width: float, height: float,
        slice_size: int = 12, content: ft.Control = None,
        on_click: ft.ControlEventHandler[ft.Container] = None,
        frame_duration: float = 0.05, color: ft.ColorValue = None,
        color_blend_mode: ft.BlendMode = ft.BlendMode.MODULATE
    ):
        super().__init__(
            width=width, height=height, border_radius=8,
            # padding=2,
            # border=ft.Border.all(1, ft.Colors.with_opacity(0.2, color)),
            # bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.WHITE)
        )
        
        self.slice_size = slice_size
        self.user_on_click = on_click
        self.frame_duration = frame_duration
        self.color = color
        self.color_blend_mode = color_blend_mode
        
        # 1. Load All 4 Frames
        src_path = Path(src)
        stem_base = src_path.stem[:-1] # Removes the "4"
        suffix = src_path.suffix
        
        self.frames: dict[int, ft.Column] = {}
        
        for i in range(1, 5):
            frame_path = src_path.with_name(f"{stem_base}{i}{suffix}")
            if not frame_path.exists():
                print(f"Warning: Missing frame {frame_path}")
                continue
                
            parts = self._slice_image(frame_path, slice_size)
            grid = self._build_grid(parts)
            
            # Frame 4 (Normal) is visible by default
            grid.opacity = (1 if i == 4 else 0)
            self.frames[i] = grid
            
        # 2. Layer 1: The Background Stack (Holds the 9-patch grids)
        self.bg_stack = ft.Stack(
            controls=list(self.frames.values()),
            width=width, height=height,
            animate_opacity=ft.Animation(100, ft.AnimationCurve.LINEAR)
        )
        
        # 3. Layer 2: The Highlight/Tint Overlay
        self.tint_container = ft.Container(
            bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.WHITE),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.2, ft.Colors.WHITE)),
            animate=ft.Animation(self._get_duration(), ft.AnimationCurve.LINEAR),
            opacity=0, border_radius=10, width=width, height=height,
            offset=ft.Offset(0.0, 0.0), bottom=0
        )
        
        # 4. Layer 3: Content & Interaction
        self.content_container = ft.Container(
            content=content, alignment=ft.Alignment.CENTER,
            width=width, height=height, offset=ft.Offset(0.0, 0.0),
            animate_offset=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT_SINE),
            opacity=1
        )
        
        self.gesture_detector = ft.GestureDetector(
            content=self.content_container,
            on_tap_down=self._on_tap_down,
            on_tap_up=self._on_tap_up,
            on_tap_cancel=self._on_tap_up,
            on_tap=self._on_tap,
            on_enter=self._on_enter,
            on_exit=self._on_exit
        )
        
        # 5. Assign the Stack as the Container's content
        self.content = ft.Stack(
            controls=[self.bg_stack, self.tint_container, self.gesture_detector]
        )
        
        self._anim_task: asyncio.Task = None 
    
    def _get_duration(self): return int(self.frame_duration*1000)*4
    
    async def _play_animation(self, start: int, end: int):
        """Cycles through frames from start to end."""
        step = -1 if start > end else 1
        
        # Move text and tint container for "press" effect
        offset_y = 0.04 if step < 0 else 0.0
        self.content_container.offset = ft.Offset(0.0, offset_y)
        self.content_container.update()
        
        # Adjust highlight height slightly
        self.tint_container.height = self.height - 8 if step < 0 else self.height
        self.tint_container.update()
        
        sequence = list(range(start, end + step, step))
        
        for i in sequence:
            if i in self.frames:
                self.frames[i].opacity = 1
                self.frames[i].update()
            
            for frame_idx, grid in self.frames.items():
                if frame_idx != i:
                    grid.opacity = 0
                    grid.update()
            
            if i != end:
                await asyncio.sleep(self.frame_duration)
    
    def _on_enter(self, _):
        self.tint_container.opacity = 1
        self.tint_container.update()
    
    def _on_exit(self, _):
        self.tint_container.opacity = 0
        self.tint_container.update()
    
    def _on_tap_down(self, _):
        if self.page is None: return
        if self._anim_task: self._anim_task.cancel()
        self._anim_task = self.page.run_task(self._play_animation, 4, 1)
        
    def _on_tap_up(self, _):
        if self.page is None: return
        if self._anim_task: self._anim_task.cancel()
        self._anim_task = self.page.run_task(self._play_animation, 1, 4)
        
    def _on_tap(self, e: ft.ControlEvent):
        if self.user_on_click:
            resp = self.user_on_click(e)
            if inspect.isawaitable(resp):
                asyncio.create_task(self.user_on_click(e))
        
    def _build_grid(self, parts):
        slice_size = self.slice_size
        
        def slice_img(src, repeat=ft.ImageRepeat.NO_REPEAT, w=slice_size, h=slice_size):
            return ft.Image(
                src=src, width=w, height=h, fit=ft.BoxFit.FILL,
                repeat=repeat, filter_quality=ft.FilterQuality.NONE,
                gapless_playback=True, color=self.color,
                color_blend_mode=self.color_blend_mode
            )
            
        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        slice_img(src=parts[0]),
                        ft.Container(slice_img(src=parts[1], repeat=ft.ImageRepeat.REPEAT_X), expand=True, height=slice_size),
                        slice_img(src=parts[2]),
                    ], spacing=0,
                ),
                ft.Row(
                    controls=[
                        slice_img(src=parts[3], h=None),
                        ft.Container(slice_img(src=parts[4], repeat=ft.ImageRepeat.REPEAT), expand=True),
                        slice_img(src=parts[5], h=None),
                    ], spacing=0, expand=True, vertical_alignment=ft.CrossAxisAlignment.STRETCH
                ),
                ft.Row(
                    controls=[
                        slice_img(src=parts[6]),
                        ft.Container(slice_img(src=parts[7], repeat=ft.ImageRepeat.REPEAT_X), expand=True, height=slice_size),
                        slice_img(src=parts[8]),
                    ], spacing=0,
                )
            ],
            spacing=0, width=self.width, height=self.height,
        )
        
    def _slice_image(self, src, size):
        img = Image.open(src)
        w, h = img.size
        
        coords = [
            (0, 0, size, size),             (size, 0, w-size, size),             (w-size, 0, w, size),
            (0, size, size, h-size),        (size, size, w-size, h-size),        (w-size, size, w, h-size),
            (0, h-size, size, h),           (size, h-size, w-size, h),           (w-size, h-size, w, h)
        ]
        
        parts_b64 = []
        for box in coords:
            part = img.crop(box)
            buffered = io.BytesIO()
            part.save(buffered, format="PNG")
            b64_data = base64.b64encode(buffered.getvalue()).decode("utf-8")
            parts_b64.append(f"data:image/png;base64,{b64_data}")
        
        return parts_b64


# ? Example usage
from setup import FontStyles, FONT_STYLES

def main(page: ft.Page):
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.fonts = FONT_STYLES
    
    script_dir = Path(__file__).parent.parent.resolve()
    btn_img_path = script_dir / "assets" / "images" / "ui" / "buttons" / "UI_Flat_Button02a_4.png"
    
    pixel_btn_txt = ft.Text(
        value="START GAME", font_family=FontStyles.ADAPA,
        size=40, color=ft.Colors.BLACK
    )
    pixel_btn = NinePatchButton(
        src=btn_img_path, width=200, height=100,
        content=pixel_btn_txt,
        on_click=lambda _: print("Game Started!")
    )
    
    page.add(pixel_btn)
    
if __name__ == "__main__": ft.run(main, assets_dir="../assets")