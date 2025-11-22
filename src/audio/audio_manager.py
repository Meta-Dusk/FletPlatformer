import pygame
from audio.music_data import MusicList
from audio.sfx_data import SFXList
from utilities.file_management import get_asset_path


class AudioManager:
    def __init__(
        self, music_volume: float = 0.3,
        sfx_volume: float = 0.5,
        debug: bool = True
    ):
        self.music_volume = music_volume
        self.sfx_volume = sfx_volume
        self.debug = debug
    
    def _debug_msg(self, msg: str):
        if self.debug:
            print(f"[AudioManager] {msg}")
    
    def initialize(self):
        try:
            pygame.mixer.init()
            pygame.mixer.music.set_volume(self.music_volume)
            self._debug_msg("Successfully initialized pygame.mixer")
        except Exception as e:
            self._debug_msg(f"Error initializing pygame.mixer: {e}")
    
    def play_music(self, music: MusicList):
        try:
            music_path = get_asset_path(music.value)
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.play()
        except Exception as e:
            self._debug_msg(f"Error playing music: {e}")
    
    def play_sfx(self, sfx: SFXList):
        try:
            sfx_path = get_asset_path(sfx.value)
            sound = pygame.mixer.Sound(sfx_path)
            sound.set_volume(self.sfx_volume)
            sound.play()
            self._debug_msg("Played SFX")
        except Exception as e:
            self._debug_msg(f"Failed to play SFX: {e}")