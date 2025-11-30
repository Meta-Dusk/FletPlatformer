import flet as ft
import time, asyncio


class LupsCounter(ft.Text):
    """
    A plug-and-play component that automatically starts its internal loop
    once it has been added to the `page`'s controls. The term **LUPS** mean
    **Loop Updates per Second**, which refers to the logic updates in Python.
    """
    def __init__(
        self, left: int = None, right: int = None,
        top: int = None, bottom: int = None
    ):
        super().__init__(
            spans=[
                ft.TextSpan("LUPS: "),
                ft.TextSpan("0")
            ], color=ft.Colors.GREEN, size=12, weight=ft.FontWeight.BOLD,
            left=left, right=right, top=top, bottom=bottom
        )
        
        # Logic variables
        self._last_time = time.time()
        self._loop_count = 0
        self._update_interval = 0.5
        self._time_accumulator = 0.0
        self._running = True # Control flag

    def did_mount(self):
        """
        Called automatically when the control is added to the page.
        This is the safest place to access self.page.
        """
        self._running = True
        self.page.run_task(self._fps_loop)

    def will_unmount(self):
        """
        Called when the control is removed from the page.
        Stops the loop cleanly.
        """
        self._running = False

    async def _fps_loop(self):
        """Calculates and updates the LUPS counter."""
        while self._running:
            # ? Calculate Delta Time
            current_time = time.time()
            dt = current_time - self._last_time
            self._last_time = current_time
            
            # ? Accumulate
            self._loop_count += 1
            self._time_accumulator += dt
            
            # ? Check if it's time to update UI
            if self._time_accumulator >= self._update_interval:
                lups = self._loop_count / self._time_accumulator
                self.spans[1].text = int(lups)
                
                # Logic Thresholds
                if lups >= 60: self.color = ft.Colors.GREEN
                elif lups >= 30: self.color = ft.Colors.ORANGE
                else: self.color = ft.Colors.RED
                
                try: self.update()
                except Exception:
                    # ? If update fails (e.g. page closed), stop the loop
                    self._running = False
                    break
                
                self._loop_count = 0
                self._time_accumulator = 0.0
                
            await asyncio.sleep(0.001)