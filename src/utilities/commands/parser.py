from dataclasses import dataclass, field
from typing import Callable, Optional, Self, Any
from abc import ABC, abstractmethod

# * --- Types of Arguments ---
class ArgType(ABC):
    """Base class for argument types (String, Int, Float, Choice, etc.)"""
    @abstractmethod
    def parse(self, value: str) -> Any:
        ...
    
    def get_suggestions(self, current_input: str) -> list[str]:
        return []

class StringArg(ArgType):
    def parse(self, value: str) -> str:
        return value

class IntArg(ArgType):
    def parse(self, value: str) -> int:
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"'{value}' is not a valid integer")
    
    def get_suggestions(self, current_input: str) -> list[str]:
        if current_input == "":
            return ["1", "2", "3"]
        return []

class FloatArg(ArgType):
    def parse(self, value: str) -> float:
        try:
            return float(value)
        except ValueError:
            raise ValueError(f"'{value}' is not a valid float")
    
    def get_suggestions(self, current_input: str) -> list[str]:
        if current_input == "":
            return ["1.0", "1.5", "2.0"]
        return []

class ChoiceArg(ArgType):
    """Restricts input to a specific list of options (e.g., 'goblin', 'orc')"""
    def __init__(self, choices: list[str]) -> None:
        self.choices = choices

    def parse(self, value: str) -> str:
        if value not in self.choices:
            raise ValueError(f"'{value}' is not one of {self.choices}")
        return value

    def get_suggestions(self, current_input: str) -> list[str]:
        return [c for c in self.choices if c.startswith(current_input)]

class BoolArg(ChoiceArg):
    """Restricts input to either 'true' or 'false'"""
    def __init__(self):
        super().__init__(["true", "false"])

class CoordinateArg(ArgType):
    """
    Parses a Minecraft-style coordinate.
    Returns a tuple: (`value`: int, `is_relative`: bool)
    \nExamples:\n
      "10"  -> (10, False)  (Absolute 10)
      "~"   -> (0, True)    (Relative +0)
      "~5"  -> (5, True)    (Relative +5)
      "~-5" -> (-5, True)   (Relative -5)
    """
    def parse(self, value: str) -> tuple[int, bool]:
        if value == "~": return (0, True)
        
        if value.startswith("~"):
            # It is relative, parse the rest as int
            try:
                # remove '~' and parse the rest
                rest = value[1:] 
                # Handle case like "~" which leaves "" -> 0
                number = int(rest) if rest else 0
                return (number, True)
            except ValueError:
                raise ValueError(f"Invalid relative coordinate: {value}")
        
        # Absolute coordinate
        try:
            return (int(value), False)
        except ValueError:
            raise ValueError(f"'{value}' is not a valid coordinate")

    def get_suggestions(self, current_input: str) -> list[str]:
        # Suggest tilde if they haven't started typing a number
        if current_input == "":
            return ["~", "~1", "~-1"]
        if current_input == "~":
            return ["~", "~1", "~-1"]
        return []

# * --- The Command Node Structure ---
@dataclass
class CommandNode:
    name: str
    arg_type: Optional[ArgType] = None
    children: dict[str, Self] = field(default_factory=dict)
    handler: Optional[Callable[..., Any]] = None
    help_text: str = ""

    def add_child(self, name: str, arg_type: Optional[ArgType] = None) -> Self:
        node = CommandNode(name, arg_type)
        self.children[name] = node
        return node

# --- The Main Parser ---
class CommandParser:
    def __init__(self) -> None:
        self.root = CommandNode("root")
        
    def register(
        self,
        command_structure: str,
        handler: Callable[..., Any],
        arg_types: Optional[dict[str, ArgType]] = None,
        help_text: str | list[str] = "No description provided."
    ) -> None:
        """
        Register a command. 'help_text' can be a single string or a list of lines.
        """
        parts = command_structure.split()
        current = self.root
        
        for part in parts:
            is_arg = part.startswith("<") and part.endswith(">")
            name = part.strip("<>")
            
            found: Optional[CommandNode] = None
            for child in current.children.values():
                if child.name == name:
                    found = child
                    break
            
            if found:
                current = found
            else:
                atype: Optional[ArgType] = None
                if is_arg and arg_types and name in arg_types:
                    atype = arg_types[name]
                elif is_arg:
                    atype = StringArg()
                
                new_node = current.add_child(name, atype)
                current = new_node
        
        current.handler = handler
        
        # If it is a list, join it into a single string with newlines.
        # This makes it compatible with our existing hanging indent system.
        if isinstance(help_text, list):
            current.help_text = "\n".join(help_text)
        else:
            current.help_text = help_text
        
    def get_suggestions(self, full_text: str) -> list[str]:
        """
        Returns a list of valid next words based on incomplete input.
        Uses Backtracking to find ALL valid suggestions from ALL matching paths.
        """
        parts = full_text.split()
        # If the user typed a space at the end, they are looking for the NEXT word.
        # We represent this as an empty token at the end.
        if full_text.endswith(" "): 
            parts.append("")
            
        suggestions: set[str] = set()

        def collect(node: CommandNode, index: int) -> None:
            # BASE CASE: We are at the cursor (the last part of the input)
            if index >= len(parts) - 1:
                current_input = parts[index] if len(parts) > 0 else ""
                
                # Check all children of this valid path node
                for child in node.children.values():
                    # 1. Argument Suggestions (e.g. from ChoiceArg)
                    if child.arg_type:
                        for s in child.arg_type.get_suggestions(current_input):
                            suggestions.add(s)
                    # 2. Literal Matches (e.g. "help", "summon")
                    elif child.name.startswith(current_input):
                        suggestions.add(child.name)
                return

            # RECURSIVE STEP: We are still walking through the path
            token = parts[index]
            
            # 1. Try Literal Match
            if token in node.children:
                collect(node.children[token], index + 1)
            
            # 2. Try Argument Match
            for child in node.children.values():
                # Avoid duplicates if we already checked this child via literal match
                if child.name == token: 
                    continue
                
                if child.arg_type:
                    try:
                        # Check if this path is valid so far
                        child.arg_type.parse(token)
                        # If yes, continue down this rabbit hole
                        collect(child, index + 1)
                    except ValueError:
                        continue

        collect(self.root, 0)
        return sorted(list(suggestions))

    def get_syntax_hint(self, full_text: str) -> str:
        """
        Returns the longest/most complete syntax hint matching the input.
        Handles ambiguity (e.g. '5' could be count OR x) by showing the longest future.
        """
        parts = full_text.split()
        is_trailing_space = full_text.endswith(" ")
        
        # We only traverse up to the last COMPLETE word to build the "past" path.
        # If trailing space, all parts are complete.
        traverse_parts = parts if is_trailing_space else parts[:-1]
        
        valid_paths: list[str] = []

        def build_hint(node: CommandNode, index: int, path_str: list[str]):
            # BASE CASE: We consumed all user tokens. Now look at the FUTURE.
            if index >= len(traverse_parts):
                
                # 1. If we are in the middle of typing a word (no trailing space),
                #    we need to find which node matches that partial word.
                if not is_trailing_space and len(parts) > 0:
                    last_token = parts[-1]
                    matched = False
                    
                    # Look for best match among children
                    for child in node.children.values():
                        if child.name.startswith(last_token) or child.arg_type:
                            # We found a valid node for the cursor. 
                            # Continue one step deeper to find the "Future" after it.
                            
                            # For the hint display, we prefer showing the PLACEHOLDER <name>
                            # rather than the user's partial input, but usage varies.
                            # Let's show the user's input to keep context.
                            new_token = f"<{child.name}>" if child.arg_type else child.name
                            
                            # RECURSE: Build the future string from this child
                            future = self._get_best_future_path(child)
                            full_hint = " ".join(path_str + [new_token] + future)
                            valid_paths.append(full_hint)
                            matched = True
                            # We don't break here; we want to see if other children also match!
                    
                    if not matched: return

                else:
                    # Input is clean (ends in space or empty). Just append future.
                    future = self._get_best_future_path(node)
                    full_hint = " ".join(path_str + future)
                    valid_paths.append(full_hint)
                return

            # RECURSIVE STEP: Match current token
            token = traverse_parts[index]
            
            # Try Literal
            if token in node.children:
                # Add literal name to path
                build_hint(node.children[token], index + 1, path_str + [node.children[token].name])
            
            # Try Arguments
            for child in node.children.values():
                if child.name == token: continue
                if child.arg_type:
                    try:
                        child.arg_type.parse(token)
                        # For arguments, we usually keep the user's value in the hint to show progress
                        # e.g. "summon goblin 5"
                        build_hint(child, index + 1, path_str + [token])
                    except ValueError: continue

        build_hint(self.root, 0, [])

        if not valid_paths:
            return "Unknown Command"
        
        # Heuristic: Return the longest string. 
        # This solves the ambiguity: "summon goblin 5" -> prefers "<x> <y> <count>" over "<count>"
        return max(valid_paths, key=len)

    def _get_best_future_path(self, node: CommandNode) -> list[str]:
        """Helper to find one valid 'future' path from a node to a leaf."""
        future = []
        current = node
        while current.children:
            # Just grab the first child for the hint
            first_child = list(current.children.values())[0]
            if first_child.arg_type:
                future.append(f"<{first_child.name}>")
            else:
                future.append(first_child.name)
            current = first_child
        return future
    
    def execute(self, full_text: str) -> Any:
        """
        Parses and runs the command handler using Backtracking.
        Returns a tuple to correctly handle functions that return None.
        """
        parts = full_text.split()
        
        # Returns: (success: bool, return_value: Any)
        def attempt_parse(node: CommandNode, token_index: int, args_collected: list[Any]) -> tuple[bool, Any]:
            # BASE CASE: End of input
            if token_index >= len(parts):
                if node.handler:
                    # Execute and return TRUE for success, plus the result
                    return (True, node.handler(*args_collected))
                return (False, None)

            current_token = parts[token_index]
            
            # 1. Literal Matches
            if current_token in node.children:
                child = node.children[current_token]
                success, val = attempt_parse(child, token_index + 1, args_collected)
                if success:
                    return (True, val)

            # 2. Argument Matches
            for child in node.children.values():
                if child.name == current_token: continue
                if child.arg_type:
                    try:
                        parsed_val = child.arg_type.parse(current_token)
                        # Pass accumulated args down
                        success, val = attempt_parse(child, token_index + 1, args_collected + [parsed_val])
                        if success:
                            return (True, val)
                    except ValueError:
                        continue
            
            return (False, None)

        # Start recursion
        success, result = attempt_parse(self.root, 0, [])
        
        if success:
            return result
        else:
            raise ValueError(f"Unknown command or invalid arguments: '{full_text}'")

    def get_root_commands(self) -> list[str]:
        """Returns a list of all top-level command names."""
        return [child.name for child in self.root.children.values()]
    
    def get_command_help(self, command_name: str) -> str:
        """
        Recursively finds all valid usage patterns (overloads) for a command.
        Supports multi-line help text with hanging indentation.
        """
        if command_name not in self.root.children:
            return "Command not found."

        root_node = self.root.children[command_name]
        help_lines: list[str] = []

        def traverse(node: CommandNode, current_path: str) -> None:
            # 1. If this node is executable (has a handler), record its help
            if node.handler:
                desc = node.help_text or "No description."
                
                # --- HANGING INDENT LOGIC ---
                
                # 1. Prepare the prefix (e.g., "summon <entity> : ")
                prefix = f"{current_path} : "
                
                # 2. Split the help text into lines (handling \n)
                lines = desc.split('\n')
                
                # 3. Add the first line attached directly to the prefix
                formatted_entry = f"{prefix}{lines[0]}"
                
                # 4. Calculate the whitespace padding for subsequent lines
                #    We use the length of the prefix to align perfectly.
                indent_padding = " " * len(prefix)
                
                # 5. Append the rest of the lines with the padding
                for extra_line in lines[1:]:
                    formatted_entry += f"\n{indent_padding}{extra_line}"
                
                help_lines.append(formatted_entry)

            # 2. Recurse into all children
            for child in node.children.values():
                # Format the name: literal "word" or argument "<word>"
                if child.arg_type:
                    token = f"<{child.name}>"
                else:
                    token = child.name
                
                traverse(child, f"{current_path} {token}")

        # Start traversal from the root of the command
        traverse(root_node, command_name)

        if not help_lines:
            return "No usage details found."
        
        # Join all found variants with newlines
        return "\n".join(help_lines)
    

# * --- Dynamic Command Registry ---
class CommandNameArg(ArgType):
    """Dynamically checks for valid command names in the parser."""
    def __init__(self, parser: CommandParser):
        self.parser = parser

    def parse(self, value: str) -> str:
        # Check against the LIVE list of commands
        if value not in self.parser.root.children:
            raise ValueError(f"Unknown command: {value}")
        return value

    def get_suggestions(self, current_input: str) -> list[str]:
        # Generate suggestions from the LIVE list
        valid_cmds = self.parser.get_root_commands()
        return [c for c in valid_cmds if c.startswith(current_input)]