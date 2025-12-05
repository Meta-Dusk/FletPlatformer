import flet as ft
from typing import List
import inspect, asyncio

from utilities.commands.parser import CommandParser, CommandNameArg


class DevConsole(ft.Container):
    def __init__(self, visible: bool = False) -> None:
        self.parser = CommandParser()
        self._current_suggestions: List[str] = []
        
        # --- UI Components ---
        self.log_view = ft.ListView(scroll=ft.ScrollMode.ALWAYS, expand=True, auto_scroll=True)
        self.suggestion_view = ft.Row(wrap=True, spacing=5)
        
        self.syntax_hint = ft.Text(
            value="", 
            color=ft.Colors.WHITE_54,
            font_family="Consolas",
            italic=True,
            size=12
        )
        
        self.input_field = ft.TextField(
            hint_text="Type a command (try 'help')...",
            bgcolor=ft.Colors.BLACK_87,
            border_radius=0,
            text_style=ft.TextStyle(font_family="Consolas", color=ft.Colors.GREEN),
            on_change=self._on_input_change,
            on_submit=self._on_submit,
            autofocus=True,
            expand=True,
            content_padding=10
        )
        
        # --- Register Commands ---
        self._register_commands()
        
        # Main Layout
        main_container = ft.Container(
            bgcolor=ft.Colors.with_opacity(0.9, ft.Colors.BLACK),
            padding=10,
            content=ft.Column(
                controls=[
                    ft.Row([self.log_view], expand=True),
                    ft.Divider(color=ft.Colors.GREEN_900),
                    self.syntax_hint,
                    self.suggestion_view,
                    self.input_field
                ]
            )
        )
        super().__init__(
            bottom=0, left=0, right=0, content=main_container, visible=visible
        )
    
    def clear_log_view(self) -> None:
        self.log_view.controls.clear()
        self.log_view.update()
    
    def did_mount(self) -> None:
        self.log_view.height = self.page.height / 2
        self.log_view.update()
    
    async def toggle(self) -> None:
        self.visible = not self.visible
        self.update()
        if not self.visible: return
        await self.input_field.focus()
        self.input_field.value = ""
        self.syntax_hint.value = ""
        self.suggestion_view.controls.clear()
        self.update()
                
    def log(self, message: str, color: str = ft.Colors.WHITE) -> None:
        self.log_view.controls.append(ft.Text(message, color=color, font_family="Consolas"))
        self.update()
    
    def register_command(
        self, command_structure: str, handler: callable,
        arg_types: dict = None, help_text: str | list[str] = ""
    ) -> None:
        """
        Allows external scripts (like `main.py` or `GameManager` class) to register commands
        without creating circular imports.
        """
        self.parser.register(command_structure, handler, arg_types, help_text)
    
    def _register_commands(self) -> None:
        """Registers all internal commands and the help system."""
        # * Define Internal Handlers
        async def exit() -> None:
            self.log("Exiting the game...", ft.Colors.ORANGE)
            await asyncio.sleep(0.5)
            await self.page.window.close()
        
        def cls() -> None: self.clear_log_view()
        
        # * Register Some Internal Commands
        self.parser.register("exit", exit, help_text="Exits the game.")
        
        self.parser.register("cls", cls, help_text="Clears the logs in the dev console.")
        
        # * Implement Help System
        def print_all_help() -> None:
            """Handler for plain 'help'"""
            # Get the list FRESH every time this function runs
            current_cmds = self.parser.get_root_commands()
            
            cmds_str = ", ".join(sorted(current_cmds))
            self.log("--- Available Commands ---", ft.Colors.GREEN_ACCENT)
            self.log(cmds_str)
            self.log("Type 'help <command>' for details.", ft.Colors.GREY)
            
        def print_specific_help(cmd_name: str) -> None:
            """Handler for 'help <cmd>'"""
            desc = self.parser.get_command_help(cmd_name)
            self.log(f"Help: {cmd_name}", ft.Colors.GREEN_ACCENT)
            self.log(desc)
            
        # Register 'help'
        self.parser.register("help", print_all_help, help_text="Lists all available commands.")
        
        # Register 'help <command>' using the new DYNAMIC argument
        self.parser.register(
            "help <command_name>", print_specific_help,
            {"command_name": CommandNameArg(self.parser)},
            help_text="Shows detailed usage for a command."
        )
        
    def _on_input_change(self, _) -> None:
        full_text = self.input_field.value
        
        # Update Syntax Hint
        hint_text = self.parser.get_syntax_hint(full_text)
        self.syntax_hint.value = hint_text
        
        # Get Suggestions
        suggestions = self.parser.get_suggestions(full_text)
        self._current_suggestions = suggestions 
        
        # Update UI Chips
        self.suggestion_view.controls.clear()
        for s in suggestions:
            # This makes the suggestion focusable via Tab.
            # Pressing 'Enter' or Click on the button triggers on_click automatically.
            btn = ft.Button(
                content=ft.Text(s, font_family="Consolas", size=12),
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=5),
                    padding=ft.Padding.symmetric(horizontal=10, vertical=0),
                    color=ft.Colors.WHITE,
                    bgcolor=ft.Colors.GREEN_900,
                ),
                height=30,
                on_click=lambda _, val=s: self.page.run_task(self._apply_smart_suggestion, val)
            )
            self.suggestion_view.controls.append(btn)
        self.update()
        
    async def _apply_smart_suggestion(self, suggestion_value: str) -> None:
        current_text = self.input_field.value
        
        if current_text.endswith(" "):
            new_text = current_text + suggestion_value + " "
        else:
            parts = current_text.rsplit(' ', 1)
            if len(parts) > 1:
                new_text = parts[0] + " " + suggestion_value + " "
            else:
                new_text = suggestion_value + " "

        self.input_field.value = new_text
        await self.input_field.focus()
        self._on_input_change(None) 
        self.update()
        
    async def _on_submit(self, e: ft.ControlEvent) -> None:
        input_field: ft.TextField = e.control
        cmd = e.data
        if not cmd: return
        
        self.log(f"> {cmd}", ft.Colors.GREY_500)
        
        try:
            result = self.parser.execute(cmd)
            if inspect.isawaitable(result): await result
        except Exception as err:
            self.log(f"Error: {str(err)}", ft.Colors.RED)
            
        input_field.value = ""
        self.suggestion_view.controls.clear()
        self.syntax_hint.value = ""
        await input_field.focus()
        self.update()