from pynput import keyboard
from typing import Callable

KeyType = str | keyboard.Key | keyboard.KeyCode
HeldKeys = set[KeyType]

# A set to keep track of what is currently pressed
held_keys: HeldKeys = set()

on_press_callback: Callable[[KeyType], None] = None

# Setup Pynput Listeners (Non-blocking)
def _get_key_id(key: KeyType) -> KeyType:
    """Standardizes key to lowercase char or Key object."""
    try:
        if hasattr(key, 'char') and key.char is not None:
            return key.char.lower()
    except AttributeError:
        pass
    return key

def on_press(key: KeyType) -> None:
    """Internal Pynput handler."""
    key_id = _get_key_id(key)
    
    # --- SPAM FILTER ---
    # If key is already held, the OS is spamming "press" events.
    # We ignore them to prevent lag and logic duplication.
    if key_id in held_keys: 
        return

    held_keys.add(key_id)
    
    # Trigger the Game Manager's handler
    if on_press_callback:
        on_press_callback(key_id)

def on_release(key: KeyType) -> None:
    """Internal Pynput handler."""
    key_id = _get_key_id(key)
    
    if key_id in held_keys:
        held_keys.remove(key_id)
    # We usually don't need a callback for release in this game style,
    # but you could add one here if needed.

def start() -> None:
    """Start the listener in a non-blocking way"""
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()