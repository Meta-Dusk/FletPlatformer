import flet as ft
import asyncio, random
from typing import Literal
from pynput import keyboard

from audio.audio_manager import global_audio_manager
from audio.music_data import MusicLibrary
from components.menus import MainMenu, PauseMenu, SettingsMenu
from components.tutorials import ControlsTutorial
from components.buttons import SimpleButton
from utilities.keyboard_manager import held_keys, start as km_start
from utilities.tasks import attempt_cancel
from entities.player import Player
from utilities.components import try_update
from utilities.commands.ui import DevConsole
from utilities.commands.parser import FloatArg, ArgType, CoordinateArg, IntArg, ChoiceArg, BoolArg
from utilities.performance_monitor import PerformanceMonitor
from entities.enemy import EnemyType, Enemy
from entities.entity import Entity
from entities.goblin import Goblin
from bg_loops import light_mv_loop, stage_panning_loop
from backgrounds import add_infinite_layer

music = MusicLibrary()
audio_manager = global_audio_manager

class GameManager:
    """Central hub for the game UI and states."""
    def __init__(self, page: ft.Page):
        # State Variables (References)
        self.page: ft.Page = page
        self.player: Player = None
        
        # UI Layers
        self.background_stack = ft.Stack(expand=True)
        self.foreground_stack = ft.Stack(expand=True)
        self.entity_stack = ft.Stack(expand=True)
        self.ui_stack = ft.Stack(expand=True)
        self.stage = ft.Stack(expand=True)
        self.game_stage = ft.Stack(expand=True)
        self.entity_list: list[Entity] = []
        self.console = DevConsole()
        
        # Task Management
        self.running_tasks: list[asyncio.Task] = []
        
        # World Configuration
        self.ground_level: int = 30
        self._kill_count: int = 0
        self._death_count: int = 0
        self.is_game_running: bool = False
        self.show_borders: bool = False
        self.finished_tutorial: bool = False
        self.tutorial_state: set[str] = set()
        
        # Scenes
        self.main_menu = None
        self.pause_menu = PauseMenu(
            on_resume=self.toggle_pause,
            on_settings=self.open_settings,
            on_quit=self.quit_to_menu
        )
        self.game_layer = ft.Container(
            opacity=0, animate_opacity=ft.Animation(1000, ft.AnimationCurve.LINEAR),
            visible=False
        )
        self.settings_menu = None
    
    # * === GAME PROPERTIES ===
    @property
    def kill_count(self) -> int:
        """Returns the current kills of the player."""
        return self._kill_count
    
    @kill_count.setter
    def kill_count(self, amount: int) -> None:
        """
        Increases the player's kill count by `amount` and
        updates the associated UI control.
        """
        self._kill_count = amount
        if hasattr(self, "kill_count_text"):
            self.kill_count_text.spans[1].text = self._kill_count
            try_update(self.kill_count_text)
    
    @property
    def death_count(self) -> int:
        """Returns the current deaths of the player."""
        return self._death_count
    
    @death_count.setter
    def death_count(self, amount: int) -> None:
        """
        Increases the player's death count by `amount` and
        updates the associated UI control.
        """
        self._death_count = amount
        if hasattr(self, "death_count_text"):
            self.death_count_text.spans[1].text = self._death_count
            try_update(self.death_count_text)
    
    # * === MENUS ===
    def _make_main_menu(self):
        async def exit(_): await self.page.window.close()
        self.main_menu = MainMenu(
            on_start=self.start_game,
            on_settings=self.open_settings,
            on_quit=exit
        )
        if not self.main_menu in self.stage.controls:
            self.stage.controls.insert(1, self.main_menu)
        try_update(self.stage)
    
    def _remove_main_menu(self):
        self.stage.controls.remove(self.main_menu)
        try_update(self.stage)
    
    # * === IMPORTANT METHODS ===
    async def __call__(self):
        """An alternative way to get the main entry point."""
        await self.initialize()
    
    async def initialize(self):
        """The entry point called by Flet."""
        # --- Setup ---
        audio_manager.play_music(music.loops.sketchbook.abstraction_2023_11_29)
        km_start()
        self.register_commands()
        
        # --- Event Handlers ---
        self.page.on_keyboard_event = self._on_keyboard_event
        self.page.window.on_event = self._win_on_event
        
        # Setup UI: Stack all layers
        self._make_main_menu()
        self.settings_menu = SettingsMenu(audio_manager, on_close=self.close_settings)
        self.stage.controls.extend([
            self.game_layer,
            self.pause_menu,
            self.settings_menu,
        ])
        
        # Post Setup for UI
        self.settings_menu.console_switch.switch.on_toggle = self._console_on_toggle
        self.perf_monitor = PerformanceMonitor()
        perf_toggles = self.settings_menu.perf_toggles
        perf_toggles.monitor_switch.switch.on_toggle = self._perf_monitor_toggle
        perf_toggles.ups_switch.switch.on_toggle = lambda b: self.perf_monitor.toggle_ups(b)
        perf_toggles.lag_switch.switch.on_toggle = lambda b: self.perf_monitor.toggle_latency(b)
        
        self.page.add(self.stage)
        await self.page.window.center()
    
    # * === OTHER HELPERS ===
    def _debug_msg(self, msg: str):
        print(f"[GameManager] {msg}")
    
    def _get_dur(self, control: ft.LayoutControl):
        """
        Returns the opacity animation duration in seconds.
        Assumes that the duration set is of type `int`.
        """
        return round(control.animate_opacity.duration / 1000, 3)
    
    async def _await_for_dur(self, control: ft.LayoutControl):
        """
        Awaits the duration of the animation.
        Assumes that the duration set is of type `int`.
        """
        await asyncio.sleep(self._get_dur(control))
    
    # * === HELPER: ENTITY RESOLUTION ===
    def _get_targets(
        self, identifier: str, count: int = 1, coords: tuple[int, bool] = None
    ) -> list[Entity]:
        """
        Resolves a string identifier into a list of actual Entity objects.
        
        Args:
            identifier (str): "player", "all", "goblin" (_type_), or "Bob" (_name_)
            count (int): Max number of targets to return (default 1, -1 for all)
            coords (tuple): _Optional_ `(x, is_relative)` to sort by proximity.
        """
        identifier = identifier.lower()
        
        # 1. Collect potential candidates
        if identifier == "player":
            return [self.player] if self.player else []
        
        if identifier == "all":
            candidates = self.entity_list.copy()
        else:
            # Check if it matches an EnemyType enum name (e.g. "goblin")
            is_type_search = any(t.name.lower() == identifier for t in EnemyType)
            
            candidates = []
            for e in self.entity_list:
                # Match by Type (e.g. all goblins)
                if is_type_search and isinstance(e, Enemy) and e.type.name.lower() == identifier:
                    candidates.append(e)
                # Match by Exact Name (e.g. specific boss name)
                elif e.name.lower().replace(" ", "_") == identifier:
                    candidates.append(e)
                    
        # 2. Sort by Proximity (if coords provided)
        if coords:
            target_x, is_rel = coords
            if is_rel: target_x += (self.page.width / 2)
            candidates.sort(key=lambda e: abs(((e.stack.left + e.stack.width) / 2 or 0) - target_x))
            
        # 3. Apply Count Limit
        if count > 0: return candidates[:count]
        return candidates
    
    # * === COMMANDS REGISTRY ===
    def register_commands(self) -> None:
        """Registers commands specifically for the `GameManager`."""
        # Dynamic Arguments
        entity_arg = EntitySelectorArg(self)
        coords_arg = CoordinateArg()
        
        # * --- HANDLERS ---
        # Helper to determine count defaults
        def resolve_count(target: str, user_count: int | None) -> int:
            """
            If user didn't specify a count:
            - target="all" -> Count is Infinite (-1)
            - target="goblin" -> Count is 1
            """
            if user_count is not None: 
                return user_count
            return -1 if target.lower() == "all" else 1
        
        def kill_handler(target: str, x: int = None, y: int = None, count: int = None) -> None:
            # Resolve count logic
            final_count = resolve_count(target, count)
            loc = x if x else None
            
            entities = self._get_targets(target, final_count, loc)
            print(f"target list size: {len(entities)}, entities: {[e.name for e in entities]}")
            
            if not entities:
                self.console.log(f"No targets found for '{target}'", ft.Colors.DEEP_PURPLE)
                return
            
            killed_count = 0
            for e in entities:
                if not e.states.dead:
                    self.page.run_task(e.death)
                    killed_count += 1
            
            if killed_count > 0:
                msg_count = "entity" if killed_count == 1 else "entities"
                self.console.log(f"Killed {killed_count} {msg_count}.", ft.Colors.DEEP_PURPLE)
            else:
                self.console.log("Targets are already dead.", ft.Colors.GREY)
                
        def damage_handler(target: str, amount: float, x: int = None, y: int = None, count: int = None) -> None:
            final_count = resolve_count(target, count)
            loc = x if x else None
            
            entities = self._get_targets(target, final_count, loc)
            
            if not entities:
                self.console.log("No targets found.", ft.Colors.PURPLE)
                return
            
            hit_count = 0
            for e in entities:
                if not e.states.dead:
                    self.page.run_task(e.take_damage, amount)
                    hit_count += 1
            
            if hit_count > 0:
                msg_count = "entity" if hit_count == 1 else "entities"
                self.console.log(f"Damaged {hit_count} {msg_count} for {amount}.", ft.Colors.PURPLE)
                
        def revive_handler(target: str, x: int = None, y: int = None, count: int = None) -> None:
            final_count = resolve_count(target, count)
            loc = x if x else None
            
            entities = self._get_targets(target, final_count, loc)
            
            revived_count = 0
            for e in entities:
                if e.states.dead and e.states.revivable:
                    # Player Logic
                    if isinstance(e, Player) or hasattr(e, "revive"):
                        self.page.run_task(e.revive)
                        revived_count += 1
                    else:
                        raise NotImplementedError("Revival only implemented for the player so far.")
            
            msg_count = "entity" if revived_count == 1 else "entities"
            self.console.log(f"Revived {revived_count} {msg_count}.", ft.Colors.GREEN)
        
        def summon_handler(enemy_type: str, x: tuple = None, y: tuple = None, count: int = 1) -> None:
            if not self.is_game_running:
                raise Exception("Can only summon entities when the game is running!")
            
            # ? Resolve Type
            try:
                # Convert string (i.e.; "goblin") to Enum (EnemyType.GOBLIN)
                e_enum = EnemyType[enemy_type.upper()]
            except KeyError:
                self.console.log(f"Invalid enemy type: {enemy_type}", ft.Colors.RED)
                return
            
            # ? Determine Spawn Logic
            # If X is provided, we spawn centered first, then move them manually.
            # If X is NOT provided, we let summon_enemy handle random/center logic.
            should_center_spawn = True if x is not None else False
            
            # ? Spawn
            new_entities = self.summon_enemy(e_enum, count, center_spawn=should_center_spawn)
            
            # ? Handle Coordinate Positioning
            if x is not None:
                target_x_val, is_rel = x
                
                # Calculate Base X
                final_x = target_x_val
                if is_rel:
                    # Relative to PLAYER if alive, otherwise relative to SCREEN CENTER
                    if self.player:
                        final_x += self.player.stack.left
                    else:
                        final_x += (self.page.width / 2)
                
                # Apply position to all new entities
                for e in new_entities:
                    # Apply a tiny random offset so they don't stack perfectly on top of each other
                    offset = random.randint(-20, 20) if count > 1 else 0
                    
                    e.stack.left = final_x + offset
                    try_update(e.stack)
                    
            msg_count = "entity" if len(new_entities) == 1 else "entities"
            self.console.log(f"Summoned {len(new_entities)} {msg_count} ({e_enum.name}).", ft.Colors.CYAN)
        
        def toggle_hb_show_handler(enabled: Literal["true", "false"]) -> None:
            _enabled = True if enabled == "true" else False
            self.console.log(f"Setting 'show_borders' to: {_enabled}", ft.Colors.BLUE)
            self.show_borders = _enabled
            for entity in self.entity_list:
                entity.toggle_show_border(_enabled)
                entity._atk_hb_show = _enabled
        
        def force_cleanup_handler() -> None:
            entitites_cleaned: int = 0
            self.console.log("Attempting a forced cleanup on 'entity_list'.")
            for entity in self.entity_list:
                if entity._cleanup_ready and isinstance(entity, Enemy):
                    enemy: Enemy = entity
                    enemy.remove_selves()
                    entitites_cleaned += 1
            self.console.log(f"Entities cleaned up: {entitites_cleaned}.", ft.Colors.ORANGE)
        
        def get_data_handler(var: str, data: str, filter: str) -> None:
            # Identify the Data Source
            source_items = []
            is_logic_entity = False # Flag to know if we can check .states
            
            if var == "entity_list":
                source_items = self.entity_list
                is_logic_entity = True
            elif var == "entity_stack":
                source_items = self.entity_stack.controls
                is_logic_entity = False
            
            # Apply Filtering
            filtered_items = []
            
            if filter == "all":
                filtered_items = source_items
            elif not is_logic_entity:
                # We cannot filter UI controls by "alive/dead" because they don't have states
                self.console.log(f"Warning: Cannot filter '{var}' by state. Returning all.", ft.Colors.ORANGE)
                filtered_items = source_items
            else:
                # Filter Logic Entities
                for e in source_items:
                    is_dead = e.states.dead
                    
                    if filter == "is_alive" and not is_dead:
                        filtered_items.append(e)
                    elif filter == "is_dead" and is_dead:
                        filtered_items.append(e)
                        
            # Format the Output
            output_msg = ""
            
            if data == "len":
                output_msg = f"Count: {len(filtered_items)}"
            
            elif data == "repr_list":
                if is_logic_entity:
                    # For entities, show their Names and IDs/Health as provided in the `__repr__`
                    names = [e for e in filtered_items]
                    output_msg = f"Items: {names}"
                else:
                    # For UI controls, just show their types
                    output_msg = f"Controls: {[type(c).__name__ for c in filtered_items]}"
                    
            # Print to Console
            self.console.log(f"[{var}] {filter} -> {output_msg}", ft.Colors.CYAN)
        
        def heal_handler(
            target: str, amount: float, overheal: Literal["true", "false"],
            x: int = None, y: int = None, count: int = None
        ) -> None:
            _overheal = True if overheal == "true" else False
            final_count = resolve_count(target, count)
            loc = x if x else None
            
            entities = self._get_targets(target, final_count, loc)
            
            if not entities:
                self.console.log("No targets found.", ft.Colors.GREEN)
                return
            
            heal_count = 0
            for e in entities:
                if not e.states.dead:
                    self.page.run_task(e.heal, amount, _overheal)
                    heal_count += 1
            
            if heal_count > 0:
                msg_count = "entities" if heal_count > 1 else "entity"
                self.console.log(f"Healed {heal_count} {msg_count} for {amount}.", ft.Colors.GREEN)
        
        # * --- REGISTRATION ---
        # ? KILL
        self.console.register_command(
            "kill <entity>", kill_handler, 
            {"entity": entity_arg},
            help_text="Kills specific entity or type."
        )
        self.console.register_command(
            "kill <entity> <x> <y> <count>", kill_handler,
            {"entity": entity_arg, "x": coords_arg, "y": coords_arg, "count": IntArg()},
            help_text="Kills <count> of the closest entities to <x> <y>."
        )
        
        # ? DAMAGE
        self.console.register_command(
            "damage <entity> <amount>", damage_handler,
            {"entity": entity_arg, "amount": FloatArg()},
            help_text="Damages target entity."
        )
        self.console.register_command(
            "damage <entity> <amount> <x> <y> <count>", damage_handler,
            {"entity": entity_arg, "amount": FloatArg(), "x": coords_arg, "y": coords_arg, "count": IntArg()},
            help_text="Damages <count> of the closest entities."
        )
        
        # ? REVIVE
        self.console.register_command(
            "revive <entity>", revive_handler,
            {"entity": entity_arg},
            help_text="Revives target."
        )
        self.console.register_command(
            "revive <entity> <x> <y> <count>", revive_handler,
            {"entity": entity_arg, "x": coords_arg, "y": coords_arg, "count": IntArg()},
            help_text="Revives closest targets."
        )
        
        # ? SUMMON
        self.console.register_command(
            "summon <enemy_type>", summon_handler,
            {"enemy_type": EnemyTypeArg()},
            help_text="Summons 1 enemy with random positioning."
        )
        
        self.console.register_command(
            "summon <enemy_type> <x> <y> <count>", summon_handler,
            {"enemy_type": EnemyTypeArg(), "x": coords_arg, "y": coords_arg, "count": IntArg()},
            help_text="Summons <count> enemies at specific coordinates."
        )
        
        # ? GET (Debug Data)
        self.console.register_command(
            "get <var> <data> <filter>", get_data_handler,
            {
                "var": ChoiceArg(["entity_list", "entity_stack"]),
                "data": ChoiceArg(["len", "repr_list"]),
                "filter": ChoiceArg(["all", "is_alive", "is_dead"]) 
            },
            help_text="Get debug data. Filter 'all' for total count."
        )
        
        # ? HEAL
        self.console.register_command(
            "heal <entity> <amount> <overheal>", heal_handler,
            {
                "entity": entity_arg, "amount": FloatArg(),
                "overheal": BoolArg()
            },
            help_text="Heals target entity."
        )
        self.console.register_command(
            "damage <entity> <amount> <overheal> <x> <y> <count>", heal_handler,
            {
                "entity": entity_arg,
                "amount": FloatArg(),
                "overheal": BoolArg(),
                "x": coords_arg, "y": coords_arg,
                "count": IntArg()
            },
            help_text="Heals <count> of the closest entities."
        )
        
        # ? Single Argument Commands
        self.console.register_command(
            "show_borders <enabled>", toggle_hb_show_handler,
            {"enabled": BoolArg()},
            help_text="If enabled, shows all the hitboxes that each entity use."
        )
        
        # ? No Arguments Commands
        self.console.register_command("quit", quit, help_text="Quits to the main menu.")
        self.console.register_command(
            "force_cleanup", force_cleanup_handler, help_text="Force cleanups entities that have despawned.")
        
    # * === UI SETUP ===
    def _setup_game_ui(self):
        """Initializes Player, Stacks, and HUD."""
        # Stacks/Layers
        def inf_layer(stack: ft.Stack, index: int):
            add_infinite_layer(stack=stack, index=index, page=self.page)
        
        for i in range(1, 8): inf_layer(self.background_stack, i)
        inf_layer(self.background_stack, 9)
        inf_layer(self.foreground_stack, 8)
        inf_layer(self.foreground_stack, 10)
        
        # Buttons / HUD
        self.controls_tutorial = ControlsTutorial()
        stats_btn = SimpleButton("Show Stats", right=200, top=10)
        if not self.finished_tutorial:
            self.ui_stack.controls.extend([self.controls_tutorial, stats_btn])
        
        self.kill_count_text = ft.Text(
            spans=[
                ft.TextSpan("Kills: "),
                ft.TextSpan(self.kill_count)
            ], size=20, text_align=ft.TextAlign.START
        )
        self.death_count_text = ft.Text(
            spans=[
                ft.TextSpan("Deaths: "),
                ft.TextSpan(self.death_count)
            ], size=20, text_align=ft.TextAlign.START
        )
        self.stats_view = ft.Column(
            controls=[self.kill_count_text, self.death_count_text],
            spacing=4,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.START,
            left=10, top=10
        )
        
        # Composition
        self.game_stage.controls.extend([
            self.background_stack,
            self.entity_stack,
            self.foreground_stack,
            self.ui_stack,
        ])
        
        form = ft.WindowDragArea(self.game_stage, expand=True, maximizable=False)
        
        # Player
        self.player = NewPlayer(self)
        return form
        
    # * === EVENT HANDLERS ===
    async def _on_keyboard_event(self, e: ft.KeyboardEvent):
        # Window and Dev keybinds
        match e.key:
            case "F11": self.page.window.maximized = not self.page.window.maximized
            case "/":
                if not self.console in self.page.overlay: return
                await self.console.toggle()
                self._update_ui_focus()
            case "Escape":
                if self.console.visible:
                    await self.console.toggle()
                    self._update_ui_focus()
                elif self.settings_menu.visible:
                    self.close_settings(e)
                else:
                    self.toggle_pause(e)
        await self.console.handle_keyboard(e)
        
        # Player Keybinds
        if not self.is_game_running or (self.player and self.player.states.disable_movement):
            return
        
        match e.key:
            case " ": self.player.jump()
            case "V": self.player.attack()
        
        # * --- Tutorial Check ---
        if self.finished_tutorial: return
        else:
            if len(self.tutorial_state) >= 10:
                self.finished_tutorial = True
                self._debug_msg("Finished tutorial!")
                self.ui_stack.controls.remove(self.controls_tutorial)
                self.ui_stack.controls.append(self.stats_view)
                self.ui_stack.update()
                return
        tutorial = self.controls_tutorial
        
        if 'a' in held_keys:
            tutorial.set_finish(tutorial.mv_key_a)
            self.tutorial_state.add("mv_key_a")
            
        if 'd' in held_keys:
            tutorial.set_finish(tutorial.mv_key_d)
            self.tutorial_state.add("mv_key_d")
            
        if self.player.states.is_sprinting:
            if ('a' or 'A') in held_keys:
                tutorial.set_finish(tutorial.sprint_key_a)
                self.tutorial_state.add("sprint_key_a")
            if ('d' or 'D') in held_keys:
                tutorial.set_finish(tutorial.sprint_key_d)
                self.tutorial_state.add("sprint_key_d")
            tutorial.set_finish(tutorial.sprint_shift)
            self.tutorial_state.add("sprint_shift")
            
        if 'c' in held_keys:
            if 'a' in held_keys:
                tutorial.set_finish(tutorial.dash_key_a)
                self.tutorial_state.add("dash_key_a")
            if 'd' in held_keys:
                tutorial.set_finish(tutorial.dash_key_d)
                self.tutorial_state.add("dash_key_d")
            tutorial.set_finish(tutorial.dash_key_c)
            self.tutorial_state.add("dash_key_c")
            
        if self.player.states.jumped:
            tutorial.set_finish(tutorial.jump_key)
            self.tutorial_state.add("jump_key")
            
        if self.player.states.is_attacking:
            tutorial.set_finish(tutorial.attack_key)
            self.tutorial_state.add("attack_key")
            
    
    def _win_on_event(self, e: ft.WindowEvent):
        match e.type:
            case ft.WindowEventType.MAXIMIZE | ft.WindowEventType.UNMAXIMIZE:
                self.settings_menu.fullscreen_toggle.update()
        self.settings_menu.win_on_update(e)
    
    def _console_on_toggle(self, enabled: bool) -> None:
        if enabled:
            self._debug_msg("Enabling dev console...")
            self.page.overlay.append(self.console)
        else:
            self._debug_msg("Disabling dev console... 1/2")
            if self.console in self.page.overlay:
                self.console.visible = False
                self.page.overlay.remove(self.console)
                self._debug_msg("Disabling dev console... 2/2")
        self.page.update()
        self._update_ui_focus()
    
    def _perf_monitor_toggle(self, enabled: bool) -> None:
        if enabled:
            self.page.overlay.insert(1, self.perf_monitor)
            self.page.update()
        else:
            self.page.overlay.remove(self.perf_monitor)
    
    # * === UI MANAGEMENT ===
    def _update_ui_focus(self):
        """
        Centralized logic to determine which UI layer should be interactive.
        Priority Order (Highest to Lowest):
        1. Dev Console
        2. Settings Menu
        3. Pause Menu
        4. Main Menu
        5. Game HUD (Entity movement / On-screen buttons)
        """
        # 1. Check Console (Top Priority)
        if self.console in self.page.overlay and self.console.visible:
            self._set_interactivity()
            return
        
        # 2. Check Settings (Can be opened from Main Menu OR Pause Menu)
        if self.settings_menu.visible:
            self._set_interactivity(settings=True)
            return
        
        # 3. Check Pause Menu (In-Game Overlay)
        if self.pause_menu.visible:
            self._set_interactivity(pause=True)
            return
        
        # 4. Check Main Menu (Start Screen)
        if self.main_menu in self.stage.controls and self.main_menu.visible:
            self._set_interactivity(main_menu=True)
            return
        
        # 5. Game Layer (Lowest Priority - only active if nothing else is)
        if self.is_game_running and self.game_layer.visible:
            self._set_interactivity(game_hud=True)
            return
        
    def _set_interactivity(
        self,
        settings: bool = False,
        pause: bool = False,
        main_menu: bool = False,
        game_hud: bool = False
    ):
        """Helper to apply disabled states based on the active flag."""
        
        # ? Console (Always interactive if visible, but we don't disable it via property)
        # ? We just act on the layers below it.
        
        # Settings
        self.settings_menu.disabled = not settings
        
        # Pause Menu
        self.pause_menu.disabled = not pause
        
        # Main Menu
        if self.main_menu:
            self.main_menu.disabled = not main_menu
            
        # Game HUD & Player Control
        self.ui_stack.disabled = not game_hud
        
        # Handle Player Movement Locking
        if self.player:
            # Player can move ONLY if the game HUD is the active focus
            self.player.states.disable_movement = not game_hud
    
    # * === MENU EVENTS ===
    async def start_game(self, _):
        """Switch from Menu to Game"""
        self.main_menu.opacity = 0
        try_update(self.main_menu)
        await self._await_for_dur(self.main_menu)
        self.main_menu.visible = False
        self.main_menu.stop_loop()
        self._remove_main_menu()
        
        self.game_layer.opacity = 0
        self.game_layer.visible = True
        self.ui_stack.disabled = False
        try_update(self.game_layer)
        await asyncio.sleep(0.1)
        self.game_layer.opacity = 1
        self.game_layer.content = self._setup_game_ui()
        try_update(self.game_layer)
        await self._await_for_dur(self.game_layer)
        
        audio_manager.play_music(music.loops.sketchbook.abstraction_2024_03_20_02)
        self.is_game_running = True
        self.start_tasks()
        self._update_ui_focus()
        self._debug_msg("Starting Game!")
        self.page.update()
    
    async def open_settings(self, _):
        if self.pause_menu.visible:
            self.pause_menu.visible = False
            self.settings_menu.visible = True
            self.settings_menu.subtitle.visible = True
        
        elif self.main_menu.visible:
            self.settings_menu.visible = True
            self.settings_menu.subtitle.visible = False
        
        self._update_ui_focus()
    
    def close_settings(self, _):
        if self.is_game_running:
            self.pause_menu.visible = True
            self.settings_menu.visible = False
        
        elif self.main_menu.visible:
            self.main_menu.disabled = False
            self.settings_menu.visible = False
        
        self._update_ui_focus()
    
    def toggle_pause(self, _):
        """Toggle Pause Overlay"""
        if not self.is_game_running or self.settings_menu.visible: return
        
        self.pause_menu.visible = not self.pause_menu.visible
        self._update_ui_focus()
        
        msg = "Game paused!" if self.pause_menu.visible else "Unpausing game!"
        self._debug_msg(msg)
        
    async def quit_to_menu(self, _):
        """Cleanup game and show menu"""
        self.is_game_running = False
        self.cleanup()
        
        self.game_layer.opacity = 0
        self.pause_menu.opacity = 0
        self.settings_menu.opacity = 0
        try_update(self.page)
        await self._await_for_dur(self.game_layer)
        self.game_layer.content = None
        self.game_layer.visible = False
        self.pause_menu.visible = False
        self.settings_menu.visible = False
        self.pause_menu.opacity = 1
        self.settings_menu.opacity = 1
        try_update(self.page)
        
        self.entity_stack.controls.clear()
        self.entity_list.clear()
        self.game_stage.controls.clear()
        self._debug_msg(f"""
Quitting to Main Menu! Clearing Entities...
entity_list: {len(self.entity_list)}
entity_stack: {len(self.entity_stack.controls)}
        """)
        
        self._make_main_menu()
        self.main_menu.opacity = 0
        self.main_menu.visible = True
        try_update(self.main_menu)
        await asyncio.sleep(0.1)
        audio_manager.play_music(music.loops.sketchbook.abstraction_2023_11_29)
        self.main_menu.opacity = 1
        try_update(self.main_menu)
        await self._await_for_dur(self.main_menu)
        self.main_menu.start_loop()
    
    # * === GAME EVENTS ===
    def summon_enemy(
        self, enemy_type: EnemyType = None,
        spawn_amount: int = None, center_spawn: bool = False
    ) -> list[Entity]:
        """Summons an enemy and returns the list of created instances."""
        
        if enemy_type is None:
            self._debug_msg("Provide an enemy type to summon.")
            return []
            
        if spawn_amount is None: spawn_amount = random.randint(1, 5)
        elif spawn_amount == 0: return []
        else: spawn_amount = abs(spawn_amount)
        
        created_entities = []
        
        self._debug_msg(f"Initial entity_stack size: {len(self.entity_stack.controls)}")
        
        for _ in range(spawn_amount):
            new_entity = None
            match enemy_type:
                # We assign to a variable to append it to our list
                case EnemyType.GOBLIN: 
                    new_entity = NewGoblin(game_manager=self, center_spawn=center_spawn)
                case _: 
                    raise NotImplementedError("Other enemy types are not yet implemented!")
            
            if new_entity:
                created_entities.append(new_entity)
                
        self._debug_msg(f"New entity_stack size: {len(self.entity_stack.controls)}")
        return created_entities
    
    # * === TASK MANAGEMENT ===
    def start_tasks(self):
        """Starts background loops."""
        async def run_light(): await light_mv_loop(self.background_stack)
        async def run_pan():
            def summon_gobby(): self.summon_enemy(EnemyType.GOBLIN)
            await stage_panning_loop(
                background_stack=self.background_stack,
                foreground_stack=self.foreground_stack,
                page=self.page,
                player=self.player,
                entity_list=self.entity_list,
                stage=self.stage,
                post_callback=summon_gobby
            )
            
        # Store tasks so we can cancel them later
        self.running_tasks.append(self.page.run_task(run_light))
        self.running_tasks.append(self.page.run_task(run_pan))
        
    def cleanup(self):
        """Call this when exiting or changing levels."""
        for task in self.running_tasks: attempt_cancel(task)
        for entity in self.entity_list:
            if isinstance(entity, Enemy):
                entity._cancel_loop_tasks()
                entity._cancel_temp_tasks()
        self.player._cancel_loop_tasks()
        self.player._cancel_temp_tasks()

# * === ARGUMENT TYPES ===
class EntitySelectorArg(ArgType):
    """
    Dynamically allows selection of:
    1. The player instance '**player**'
    2. Specific Enemy Types (i.e.; '**goblin**')
    3. Specific Entity Names (i.e.; '**Gobby**')
    """
    def __init__(self, game_manager: GameManager):
        self.gm = game_manager

    def get_suggestions(self, current_input: str) -> list[str]:
        # Always available
        options = {"player", "all"}
        
        # Add Enemy Types (i.e.; "goblin")
        options.update(e.name.lower() for e in EnemyType)
        
        # Add Active Entity Names (i.e.; "Gobby")
        # We filter for active entities to avoid suggesting dead/despawned ones
        if self.gm.entity_list:
            options.update(e.name.replace(" ", "_") for e in self.gm.entity_list)
            
        return [opt for opt in options if opt.lower().startswith(current_input.lower())]

    def parse(self, value: str) -> str:
        # We just pass the string through; the logic handler will resolve it to objects.
        return value

class EnemyTypeArg(ArgType):
    """Strictly selects available EnemyTypes (i.e.; 'goblin')."""
    def get_suggestions(self, current_input: str) -> list[str]:
        return [
            e.name.lower() 
            for e in EnemyType 
            if e.name.lower().startswith(current_input.lower())
        ]
        
    def parse(self, value: str) -> str:
        # Validate that the input is actually a valid enum
        if not any(e.name.lower() == value.lower() for e in EnemyType):
            raise ValueError(f"'{value}' is not a valid Entity Type.")
        return value
    
# * === MIXINS ===
class GameManagerMixin:
    """Mixin to bridge GameManager data into Entities."""
    def _configure_from_manager(self: Entity, game_manager: GameManager):
        """Run this **BEFORE** `super().__init__()` to setup attributes."""
        self.game_manager = game_manager
        self._atk_hb_show = self.game_manager.show_borders
        self._entity_list = self.game_manager.entity_list
    
    @property
    def ground_level(self) -> int: return self.game_manager.ground_level
    
    def _get_base_kwargs(self, debug: bool):
        """
        Helper for common init arguments. Currently returns the following:
        \n`page`, `audio_manager`, `entity_list`, `debug`.
        """
        return {
            "page": self.game_manager.page,
            "audio_manager": audio_manager,
            "entity_list": self.game_manager.entity_list,
            "debug": debug
        }
        
    def _spawn_into_scene(self: Entity, **call_kwargs):
        """
        Run this **AFTER** `super().__init__()` to add to the game world.
        
        Args:
            **call_kwargs: Arguments passed to `self.__call__()` (i.e., `center_spawn=True`)
        """
        if not isinstance(self, Entity):
            self._debug_msg("Class instance is not an Entity!")
            return
        
        # Apply visual settings that required the stack to exist
        self.toggle_show_border(self.game_manager.show_borders)
        self._atk_hb_show = self.game_manager.show_borders
        
        # Add to Logic List (if not already there)
        if self not in self.game_manager.entity_list: self.game_manager.entity_list.append(self)
        
        # Add to Visual Stack
        # ? This calls self.__call__(**kwargs), getting the control and starting loops
        self.game_manager.entity_stack.controls.append(self.__call__(**call_kwargs))
        
class NewGoblin(Goblin, GameManagerMixin):
    """
    Wrapped `Enemy` class to be used in the `GameMaker` class.
    Automatically spawns into the scene once called.
    """
    def __init__(
        self, game_manager: GameManager, name: str = None,
        *, center_spawn: bool = True, debug = False
    ):
        self._configure_from_manager(game_manager)
        super().__init__(
            target=game_manager.player,
            name=name,
            **self._get_base_kwargs(debug)
        )
        self._spawn_into_scene(center_spawn=center_spawn)

class NewPlayer(Player, GameManagerMixin):
    """
    Wrapped `Player` class to be used in the `GameMaker` class.
    Automatically spawns into the scene once called.
    """
    def __init__(
        self, game_manager: GameManager, *, debug = False
    ):
        self._configure_from_manager(game_manager)
        super().__init__(
            held_keys=held_keys,
            **self._get_base_kwargs(debug)
        )
        self._spawn_into_scene()