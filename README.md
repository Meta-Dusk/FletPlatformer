# Fushi: The Beckoning

An attempt at making a real-time (such as combat) game in Flet.
As of now, I've included various buttons for testing some functionality that I have already implemented in the game.
Additionally, if you'd like to know what to expect of the game, I won't spoil what it will be in the end, so here's other information about it instead (refer to the "The Game" section).
All assets used are all free! I'll include all the licenses soon.

## The Game

So, what is the game even about?
It's a somewhat difficult side-scroller genre of a game (which is basically just a 2D action platformer).
There will be lore for the game as well, hence the official name; "**Fushi: The Beckoning**".

## Feature List

| Feature | Description | Version Implemented |
| ------- | ----------- | ------------------- |
| **Sounds** | There's music and various SFX implemented | v0.1.X |
| **Background Panning** | The background pans to the right or left if the player is at the edge of the screen. | v0.2.X |
| **Simple Enemy AI** | The current enemy (goblin) has this. | v0.3.X |
| **Various Entity States** | Entities such as the player and the goblin, can die, move, attack, etc. | v0.3.X |
| **Somewhat Intelligent "AI"** | Enemies such as the goblin are now a bit smarter, attempting to predict the player's moves. | v0.4.X |
| **Menus** | There's a main menu, settings menu, and a pause menu now. | v0.4.X |
| **Commands System** | There's an entire system for handling dev stuff now! | v0.5.X |

## Controls

Keybinds as of now are not yet possible to be rebinded.

### Player

The player can be controlled with the following mapped keys:

| Key | Action |
| --- | ------ |
| **A** | Move left. |
| **D** | Move right. |
| **V** | Attack. |
| **C** | Dash in a direction (left/right). Also can be held. |
| **Shift** | Press and hold this key while moving to **sprint**. |
| **Space** | Jump. |

### Game

| Key | Action |
| --- | ------ |
| **Escape** | Pauses the game, or closes a menu. |
| **F11** | Toggles the borderless fullscreen mode. |
| **/** | Toggles the developer console (you must enable it first in the settings menu). |

## Known Issues

| No. | Issue | Description | Solution |
| --- | ----- | ----------- | -------- |
| 1 | Audio blocks game updates when playing multiple sounds in a very short time span. | This issue always occurs, such as if you hover over the UI buttons rapidly, it will seem like the audio gets queued, and blocks UI interaction. | Applied a very simple solution as of `v0.5.8` and above that simply removes this `on_hover` callback. |
