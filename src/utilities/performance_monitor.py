import asyncio, time
import flet as ft

from setup import FontStyles


class PerformanceMonitor(ft.Text):
    """
    Tracks 'System Load' (UPS) and 'Logic Lag' (Latency).
    Replaces LupsCounter with a more accurate performance metric.
    """
    def __init__(
        self,
        show_ups: bool = True,
        show_latency: bool = True,
        update_interval: float = 0.5,
        left: int = None, right: int = 20,
        top: int = 20, bottom: int = None,
        visible: bool = True
    ):
        super().__init__(
            value="",
            color=ft.Colors.GREEN, 
            size=12,
            weight=ft.FontWeight.BOLD,
            font_family=FontStyles.ADAPA,
            left=left, right=right, top=top, bottom=bottom, visible=visible,
            bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
            spans=[
                ft.TextSpan("Initializing"),
                ft.TextSpan("...")
            ],
            text_align=ft.TextAlign.RIGHT
        )
        
        # Configuration
        self.show_ups = show_ups
        self.show_latency = show_latency
        self.update_interval = update_interval
        
        # State
        self._running = True
        self._update_count = 0
        self._last_calc_time = time.perf_counter()
        self._original_update = None

    def did_mount(self):
        """Setup hooks when added to page."""
        self._running = True
        
        # 1. Hook page.update to count Server Refreshes
        self._original_update = self.page.update
        self.page.update = self._hooked_update
        
        # 2. Start reporting loop
        self.page.run_task(self._monitor_loop)

    def will_unmount(self):
        """Cleanup hooks when removed."""
        self._running = False
        # Restore the original update method to prevent errors
        if self._original_update:
            self.page.update = self._original_update

    def toggle_ups(self, enabled: bool = None):
        """Runtime toggle for UPS display."""
        if enabled is not None:
            self.show_ups = enabled
            return
        self.show_ups = not self.show_ups
        
    def toggle_latency(self, enabled: bool = None):
        """Runtime toggle for Latency display."""
        if enabled is not None:
            self.show_latency = enabled
            return
        self.show_latency = not self.show_latency

    def _hooked_update(self, *args, **kwargs):
        """Counts updates without blocking execution."""
        self._update_count += 1
        if self._original_update:
            self._original_update(*args, **kwargs)

    async def _monitor_loop(self):
        while self._running:
            # * --- Measure Event Loop Latency ---
            # We yield to the loop and see how long it takes to return.
            t0 = time.perf_counter()
            await asyncio.sleep(0)
            t1 = time.perf_counter()
            latency_ms = (t1 - t0) * 1000
            
            # * --- Calculate UPS ---
            current_time = time.perf_counter()
            elapsed = current_time - self._last_calc_time
            
            if elapsed >= self.update_interval:
                ups = self._update_count / elapsed
                
                # * --- Build Modular Text ---
                if self.show_ups:
                    self.spans[0].text = f"UPS: {int(ups)}"
                elif not self.show_ups and not self.show_latency:
                    self.spans[0].text = "I've got nothing to show :("
                else:
                    self.spans[0].text = ""
                
                if self.show_latency and self.show_ups:
                    self.spans[1].text = f"\nLatency: {int(latency_ms)}ms"
                elif self.show_latency and not self.show_ups:
                    self.spans[1].text = f"Latency: {int(latency_ms)}ms"
                else:
                    self.spans[1].text = ""
                
                # * --- Color Logic ---
                # ? Prioritize showing RED if Latency is bad (Logic Lag is worse than Frame drops)
                if self.show_latency and latency_ms > 20:
                    self.color = ft.Colors.RED
                elif self.show_latency and latency_ms > 10:
                    self.color = ft.Colors.ORANGE
                
                # ? Low UPS Logic
                elif self.show_ups and ups < 30:
                    # If UPS is low BUT Latency is also super low (< 5ms),
                    # it means we are just IDLE (Menu/Pause), which is GOOD.
                    if latency_ms < 5:
                        self.color = ft.Colors.BLUE_200 # or CYAN, indicating "Sleep/Idle"
                    else:
                        # Low UPS + High Latency = Actual Lag
                        self.color = ft.Colors.ORANGE
                else:
                    self.color = ft.Colors.GREEN

                # * --- Safe Update ---
                try: self.update()
                except Exception:
                    self._running = False
                    break
                
                # Reset counters
                self._update_count = 0
                self._last_calc_time = current_time
            
            # Sleep slightly to avoid hogging CPU
            await asyncio.sleep(0.1)