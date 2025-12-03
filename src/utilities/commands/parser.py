from dataclasses import dataclass, field
from typing import Callable, List, Optional, Self
from abc import ABC, abstractmethod

# --- Types of Arguments ---
class ArgType(ABC):
    """Base class for argument types (String, Int, Float, Choice, etc.)"""
    @abstractmethod
    def parse(self, value: str) -> any:
        ...
    
    def get_suggestions(self, current_input: str) -> List[str]:
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

class ChoiceArg(ArgType):
    """Restricts input to a specific list of options (e.g., 'goblin', 'orc')"""
    def __init__(self, choices: List[str]) -> None:
        self.choices = choices

    def parse(self, value: str) -> str:
        if value not in self.choices:
            raise ValueError(f"'{value}' is not one of {self.choices}")
        return value

    def get_suggestions(self, current_input: str) -> List[str]:
        return [c for c in self.choices if c.startswith(current_input)]

# --- The Command Node Structure ---
@dataclass
class CommandNode:
    name: str
    arg_type: Optional[ArgType] = None
    children: dict[str, Self] = field(default_factory=dict)
    handler: Optional[Callable[..., any]] = None
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
        self, command_structure: str,
        handler: Callable[..., any],
        arg_types: Optional[dict[str, ArgType]] = None,
        help_text: str = "No description provided."
    ) -> None:
        """
        Register a command like "summon <entity> <count>".
        
        Args:
            command_structure (str): The syntax string.
            handler (Callable): The function to call when executed.
            arg_types (dict): Map of placeholder names to ArgType objects.
            help_text (str): A description of what the command does.
        """
        parts = command_structure.split()
        current = self.root
        
        for part in parts:
            is_arg = part.startswith("<") and part.endswith(">")
            name = part.strip("<>")
            
            # Check if this node already exists (for branching commands)
            found: Optional[CommandNode] = None
            for child in current.children.values():
                if child.name == name:
                    found = child
                    break
            
            if found:
                current = found
            else:
                # Create new node
                atype: Optional[ArgType] = None
                if is_arg and arg_types and name in arg_types:
                    atype = arg_types[name]
                elif is_arg:
                    atype = StringArg() # Default to string if not specified
                
                new_node = current.add_child(name, atype)
                current = new_node
        
        # The last node handles the execution
        current.handler = handler
        current.help_text = help_text
        
    def get_suggestions(self, full_text: str) -> List[str]:
        """Returns a list of valid next words based on incomplete input."""
        parts = full_text.split()
        if full_text.endswith(" "): parts.append("") 
        
        current = self.root
        
        # Traverse as deep as we can
        for _, part in enumerate(parts[:-1]):
            matched_arg = False
            
            # 1. Try literal match
            if part in current.children:
                current = current.children[part]
                matched_arg = True
            else:
                # 2. Try argument match
                for child in current.children.values():
                    if child.arg_type:
                        try:
                            child.arg_type.parse(part)
                            current = child
                            matched_arg = True
                            break
                        except ValueError: continue
            
            if not matched_arg: return []
            
        # We are at the cursor node. What are valid next options?
        current_input = parts[-1] if len(parts) > 0 else ""
        suggestions: List[str] = []
        
        for child in current.children.values():
            if child.arg_type:
                suggestions.extend(child.arg_type.get_suggestions(current_input))
            elif child.name.startswith(current_input):
                suggestions.append(child.name)
                
        return suggestions
    
    def get_syntax_hint(self, full_text: str) -> str:
        """
        Returns a string showing the current command structure with future arguments.
        Example: "summon <entity> <count>"
        """
        parts = full_text.split()
        is_trailing_space = full_text.endswith(" ")
        
        current = self.root
        path_str: List[str] = [] # Reconstructed valid path so far
        
        traverse_parts = parts if is_trailing_space else parts[:-1]
        
        for part in traverse_parts:
            found: Optional[CommandNode] = None
            # Literal match
            if part in current.children:
                found = current.children[part]
                path_str.append(found.name)
            else:
                # Arg match
                for child in current.children.values():
                    if child.arg_type:
                        try:
                            child.arg_type.parse(part)
                            found = child
                            path_str.append(part)
                            break
                        except ValueError: pass
            
            if found:
                current = found
            else:
                return "Unknown Command"
            
        # If we are in the middle of typing a word
        if not is_trailing_space and len(parts) > 0:
            last_token = parts[-1]
            best_match: Optional[CommandNode] = None
            
            for child in current.children.values():
                if child.name.startswith(last_token) or child.arg_type:
                    best_match = child
                    if not child.arg_type:
                        path_str.append(child.name) 
                    else:
                        path_str.append(f"<{child.name}>")
                    break
            
            if best_match:
                current = best_match
            else:
                return "Unknown Command"

        # Look ahead
        future_str: List[str] = []
        temp_node = current
        
        while temp_node.children:
            first_child = list(temp_node.children.values())[0]
            
            if first_child.arg_type:
                future_str.append(f"<{first_child.name}>")
            else:
                future_str.append(first_child.name)
            
            temp_node = first_child
            
        return " ".join(path_str + future_str)
    
    def execute(self, full_text: str) -> any:
        """Parses and runs the command handler."""
        parts = full_text.split()
        current = self.root
        args_collected: List[any] = []

        for part in parts:
            found_next = False
            
            if part in current.children:
                current = current.children[part]
                found_next = True
            else:
                for child in current.children.values():
                    if child.arg_type:
                        try:
                            val = child.arg_type.parse(part)
                            args_collected.append(val)
                            current = child
                            found_next = True
                            break
                        except ValueError: continue
            
            if not found_next:
                raise ValueError(f"Unknown command or argument: {part}")

        if current.handler:
            return current.handler(*args_collected)
        else:
            raise ValueError("Incomplete command.")

    def get_root_commands(self) -> List[str]:
        """Returns a list of all top-level command names."""
        return [child.name for child in self.root.children.values()]
    
    def get_command_help(self, command_name: str) -> str:
        """Retrieves the help text for a top-level command."""
        if command_name in self.root.children:
            node = self.root.children[command_name]
            # If the top level node handles logic, return its help
            # If it's a branching command, we might want to traverse down, 
            # but for now let's just return what is stored on the node.
            # We traverse to the leaf of the first branch to find some help if the root doesn't have it.
            
            if node.help_text: return node.help_text
            
            # Simple fallback: check the first child if it's a multi-stage command
            temp = node
            while temp.children and not temp.help_text:
                temp = list(temp.children.values())[0]
            
            return temp.help_text
            
        return "Command not found."