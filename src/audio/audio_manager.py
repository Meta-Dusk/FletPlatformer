from audio.music_data import MusicList
from audio.sfx_data import SFXList
from utilities.file_management import get_asset_path
from utilities.values import clamp

import pygame, os


# TODO: Add more features for the AudioManager class
class AudioManager:
    """Handles all the audio playbacks (both Music and SFX)."""
    def __init__(
        self, music_volume: float = 0.3,
        sfx_volume: float = 0.5,
        directional_sfx: bool = True,
        *, debug: bool = True
    ):
        self.music_volume = music_volume
        self.sfx_volume = sfx_volume
        self.directional_sfx = directional_sfx
        self.debug = debug
        
        # Optimization: Cache loaded sounds so we don't read from disk every time
        self._sfx_cache = {} 
    
    def _debug_msg(self, msg: str):
        if self.debug:
            print(f"[AudioManager] {msg}")
    
    def initialize(self):
        """Initializes `pygame.mixer`. Required to play sounds."""
        # * Force Windows to use the older DirectSound driver
        # This driver is more likely to respect the 'channels=2' request
        os.environ['SDL_AUDIODRIVER'] = 'directsound'
        # ? If 'directsound' fails, try 'winmm'
        try:
            pygame.mixer.pre_init(channels=2)
            pygame.mixer.init()
            freq, size, channels = pygame.mixer.get_init()
            self._debug_msg(f"MIXER STATUS: Frequency={freq}, Size={size}, Channels={channels}")
            pygame.mixer.music.set_volume(self.music_volume)
            self._debug_msg("Successfully initialized pygame.mixer")
        except Exception as e:
            self._debug_msg(f"Error initializing pygame.mixer: {e}")
    
    def play_music(self, music: MusicList):
        """Plays music that is on loop."""
        try:
            music_path = get_asset_path(music.value)
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.play(-1) # -1 usually means loop forever
        except Exception as e:
            self._debug_msg(f"Error playing music: {e}")
    
    def play_sfx(
        self, sfx: SFXList,
        left_volume: float = None,
        right_volume: float = None
    ):
        """
        If `directional_sfx` is `True`, then audio panning will work.\n
        Audio panning will only work if `left_volume` and `right_volume` is provided.
        """
        try:
            # Load Sound (with basic caching)
            if sfx not in self._sfx_cache:
                sfx_path = get_asset_path(sfx.value)
                self._sfx_cache[sfx] = pygame.mixer.Sound(sfx_path)
            
            sound = self._sfx_cache[sfx]
            
            # Apply Master Volume
            # We set this on the sound object itself so it scales appropriately
            sound.set_volume(self.sfx_volume)
            
            # Play to get a Channel
            channel = sound.play()
            if not channel: return
            
            # Apply Panning (If requested)
            if left_volume is not None and right_volume is not None and self.directional_sfx:
                clamped_vol_r = clamp(right_volume)
                clamped_vol_l = clamp(left_volume)
                channel.set_volume(clamped_vol_l, clamped_vol_r)
                self._debug_msg(f"Played SFX panned: L={clamped_vol_l:.2f} R={clamped_vol_r:.2f}")
            else:
                self._debug_msg(f"Played SFX (Center)")
                    
        except Exception as e:
            self._debug_msg(f"Failed to play SFX: {e}")