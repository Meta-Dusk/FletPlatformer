import flet as ft


class DialogBox(ft.Container):
    def __init__(
        self
    ) -> None:
        self.dialog_text: str = "Insert message"
        self.speaker_name: str = "Insert name"
        
        super().__init__(
            
        )
    
    def add_dialogue(self, msg: str) -> None:
        pass
    