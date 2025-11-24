from pynput import keyboard

# A set to keep track of what is currently pressed
held_keys: set[str | keyboard.KeyCode] = set()

# Setup Pynput Listeners (Non-blocking)
def on_press(key: keyboard.KeyCode):
    """Registers pressed keys in the `held_keys` set."""
    try:
        # Handle standard keys (a, b, c)
        held_keys.add(key.char.lower())
    except AttributeError:
        # Handle special keys (space, enter, arrow keys)
        held_keys.add(key)
        
def on_release(key: keyboard.KeyCode):
    """Removes released keys in the `held_keys` set."""
    try:
        if hasattr(key, 'char') and key.char.lower() in held_keys:
            held_keys.remove(key.char.lower())
        elif key in held_keys:
            held_keys.remove(key)
    except KeyError:
        pass # Key was already removed or never added

def start():
    """Start the listener in a non-blocking way"""
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()