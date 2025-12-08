import asyncio, inspect
from typing import Callable, Any

class SplashHandler:
    """Handles skippable animations and delays."""
    def __init__(self) -> None:
        self.skip_event: asyncio.Event = asyncio.Event()
        self.skip_triggered: bool = False
        self.active: bool = True  # Use this to disable future delays after cleanup
        self.on_cleanup: Callable[[None], None] = None
        
    def on_skip_event(self, _) -> None:
        """Call this to skip."""
        if not self.skip_triggered:
            self.skip_triggered = True
            self.skip_event.set()
            
    async def cleanup(self) -> None:
        """
        Resets self and calls an optional callable
        `on_cleanup` if provided.
        """
        self.active = False
        if self.on_cleanup is None: return
        result = self.on_cleanup()
        if inspect.isawaitable(result):
            await result
        
    async def skippable_delay(self, seconds: float) -> bool:
        """
        Skips the delay once `on_skip_event` gets called.
        
        Returns:
            bool: `False` if it has been skipped, else `True` if delay finished.
        """
        if not self.active:
            return False
        try:
            await asyncio.wait_for(self.skip_event.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            return True  # not skipped, delay finished
        await self.cleanup()
        return False     # was skipped
    
    async def force_skip(self) -> None:
        """Call this to force a skip."""
        self.skip_triggered = True
        self.skip_event.set()
        await self.cleanup()
    
    # * === DECORATORS ===
    def skippable_animation(self, auto_cleanup: bool = True):
        """Skips the animation once `on_skip_event` gets called."""
        def decorator(func: Callable[..., None]):
            async def wrapper(*args, **kwargs):
                animation_task = asyncio.create_task(func(*args, **kwargs))
                skip_task = asyncio.create_task(self.skip_event.wait())

                done, _ = await asyncio.wait(
                    [animation_task, skip_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                if skip_task in done:
                    animation_task.cancel()
                    if auto_cleanup:
                        await self.cleanup()
                    return False
                else:
                    skip_task.cancel()
                    if auto_cleanup:
                        await self.cleanup()
                    return True
            return wrapper
        return decorator
    
    def auto_cleanup(self):
        def decorator(func: Callable[..., Any]):
            async def wrapper(*args, **kwargs):
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    if self.active:
                        await self.cleanup()
            return wrapper
        return decorator
