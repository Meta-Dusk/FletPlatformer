import asyncio, inspect
import flet as ft
from pynput import keyboard
from typing import Callable

from utilities.keyboard_manager import held_keys
from utilities.tasks import attempt_cancel
from components.tutorials import ControlsTutorial

class TutorialHandler:
    """The handler for a simple tutorial system."""
    def __init__(
        self, page: ft.Page,
        on_finish_tutorial: Callable[[None], None] = None, *,
        debug: bool = False
    ) -> None:
        """Provide the `page` instance for running the loop."""
        self.tutorial = ControlsTutorial()
        self.page = page
        self.debug = debug
        self._keyboard_check_task: asyncio.Task = None
        self.tutorial_state: set[str] = set()
        self._finished_tutorial: bool = False
        self.on_finish_tutorial = on_finish_tutorial
        self._has_initialized: bool = False
        self.input_check_delay: float = 0.1 # seconds
    
    @property
    def finished_tutorial(self) -> bool:
        return self._finished_tutorial
    
    @finished_tutorial.setter
    def finished_tutorial(self, enabled: bool) -> None:
        self._finished_tutorial = enabled
    
    def __call__(self) -> ControlsTutorial:
        """
        A shortcut for calling the `initialize()` method.
        Also returns the flet controls for the tutorial.
        """
        self.initialize()
        return self.tutorial
    
    def initialize(self) -> None:
        """Starts the loop for the keyboard input checking."""
        if not self._has_initialized:
            self._keyboard_check_task = self.page.run_task(self._keyboard_check_loop)
        self._has_initialized = True
    
    def _debug_msg(self, msg: str) -> None:
        if self.debug:
            print(f"[TutorialHandler] {msg}")
    
    async def _keyboard_check_loop(self) -> None:
        """Handles user input checking."""
        while not self.finished_tutorial:
            await asyncio.sleep(self.input_check_delay)
            is_shift_held = keyboard.Key.shift in held_keys
            
            # Jumping
            if keyboard.Key.space in held_keys:
                self.tutorial.set_finish(self.tutorial.jump_key)
                self.tutorial_state.add("jump_key")
            
            # Attacking
            if 'v' in held_keys:
                self.tutorial.set_finish(self.tutorial.attack_key)
                self.tutorial_state.add("attack_key")
            
            # Walking
            if 'a' in held_keys:
                self.tutorial.set_finish(self.tutorial.mv_key_a)
                self.tutorial_state.add("mv_key_a")
            if 'd' in held_keys:
                self.tutorial.set_finish(self.tutorial.mv_key_d)
                self.tutorial_state.add("mv_key_d")
            
            # Sprinting
            if is_shift_held:
                self.tutorial.set_finish(self.tutorial.sprint_shift)
                self.tutorial_state.add("sprint_shift")
                if 'a' in held_keys:
                    self.tutorial.set_finish(self.tutorial.sprint_key_a)
                    self.tutorial_state.add("sprint_key_a")
                if 'd' in held_keys:
                    self.tutorial.set_finish(self.tutorial.sprint_key_d)
                    self.tutorial_state.add("sprint_key_d")
            
            # Dashing
            if ('a' or 'd') and 'c' in held_keys:
                self.tutorial.set_finish(self.tutorial.dash_key_c)
                self.tutorial_state.add("dash_key_c")
                if 'a' in held_keys:
                    self.tutorial.set_finish(self.tutorial.dash_key_a)
                    self.tutorial_state.add("dash_key_a")
                if 'd' in held_keys:
                    self.tutorial.set_finish(self.tutorial.dash_key_d)
                    self.tutorial_state.add("dash_key_d")
                    
            # Check if finished
            self._debug_msg(f"Checking for inputs... Progress: {len(self.tutorial_state)}/{self.tutorial.total_keys}")
            if len(self.tutorial_state) >= self.tutorial.total_keys:
                self._debug_msg("Finished tutorial! 1/3 :: Ending loop")
                self.finished_tutorial = True
        
        # ? Executes if while loop condition becomes `False`
        else:
            self._debug_msg("Finished tutorial! 2/3 :: Cleaning up")
            attempt_cancel(self._keyboard_check_task)
            self._keyboard_check_task = None
            if self.on_finish_tutorial is not None:
                self._debug_msg("Finished tutorial! 3/3 :: Calling on_finish callable")
                result = self.on_finish_tutorial()
                if inspect.isawaitable(result): await result