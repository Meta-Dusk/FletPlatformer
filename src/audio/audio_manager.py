import pygame, os, time
from pathlib import Path

from utilities.file_management import get_asset_path
from utilities.values import clamp


class AudioManager:
    """Handles all the audio playbacks (both Music and SFX)."""
    def __init__(
        self, music_volume: float = 0.3,
        sfx_volume: float = 0.5,
        directional_sfx: bool = True,
        *, debug: bool = True
    ):
        self._music_volume = music_volume
        self._sfx_volume = sfx_volume
        self.directional_sfx = directional_sfx
        self.debug = debug
        
        # Optimization: Cache loaded sounds so we don't read from disk every time
        # Key: Path (The exact argument passed), Value: pygame.mixer.Sound
        self._sfx_cache: dict[Path, pygame.mixer.Sound] = {}
        
        # Optimization: Cooldowns to prevent audio spam (Phasing/Distortion)
        self._sfx_cooldowns: dict[Path, float] = {}
    
    @property
    def sfx_volume(self) -> float:
        """SFX volume between 0.0 and 1.0."""
        return self._sfx_volume
    
    @sfx_volume.setter
    def sfx_volume(self, volume: float):
        """Automatically clamps volume for sfx between 0.0 and 1.0."""
        self._sfx_volume = round(clamp(volume), 1)
        # if len(self._sfx_cache) <= 0: return
        # for _, sfx in self._sfx_cache.items():
        #     sfx.set_volume(self._sfx_volume)
    
    @property
    def music_volume(self) -> float:
        """Music volume between 0.0 and 1.0."""
        return self._music_volume
    
    @music_volume.setter
    def music_volume(self, volume: float):
        """Automatically clamps volume for music between 0.0 and 1.0."""
        self._music_volume = round(clamp(volume), 1)
        pygame.mixer.music.set_volume(self._music_volume)
    
    def _debug_msg(self, msg: str):
        if self.debug: print(f"[AudioManager] {msg}")
    
    def initialize(self):
        """Initializes `pygame.mixer`. Required to play sounds."""
        # * Force Windows to use the older DirectSound driver
        os.environ['SDL_AUDIODRIVER'] = 'directsound'
        
        try:
            pygame.mixer.pre_init(channels=2)
            pygame.mixer.init()
            pygame.mixer.set_num_channels(32)
            
            freq, size, channels = pygame.mixer.get_init()
            self._debug_msg(f"MIXER STATUS: Frequency={freq}, Size={size}, Channels={channels}")
            
            pygame.mixer.music.set_volume(self.music_volume)
            self._debug_msg("Successfully initialized pygame.mixer")
        except Exception as e:
            self._debug_msg(f"Error initializing pygame.mixer: {e}")
    
    def play_music(self, music_path: Path):
        """Plays music that is on loop."""
        try:
            # Note: We don't cache music because it streams from disk
            resolved_path = get_asset_path(music_path)
            self._debug_msg(f"Playing music: {resolved_path}")
            pygame.mixer.music.load(resolved_path)
            pygame.mixer.music.play(-1, fade_ms=1000)
        except Exception as e:
            self._debug_msg(f"Error playing music: {e}")
    
    def play_sfx(
        self, sfx_path: Path,
        left_volume: float = None,
        right_volume: float = None,
        base_volume: float = None
    ):
        """
        Use the `SFXLibrary` dataclass for supplying the `sfx_path`.
        Includes Culling (distance check) and Cooldowns (spam check).
        """
        try:
            # OPTIMIZATION 1: Distance Culling
            # If the calculated volume is virtually silent, don't bother playing it.
            if self.directional_sfx and left_volume is not None and right_volume is not None:
                if left_volume < 0.01 and right_volume < 0.01: return

            # OPTIMIZATION 2: Spam Prevention (Cooldown)
            # If this exact sound played less than 50ms ago, skip it.
            current_time = time.time()
            last_played = self._sfx_cooldowns.get(sfx_path, 0)
            
            # 0.05s = 50ms cooldown. Adjust this if you want more overlap.
            if current_time - last_played < 0.05: return
            
            self._sfx_cooldowns[sfx_path] = current_time
            
            # Load Sound
            if sfx_path not in self._sfx_cache:
                resolved_path = get_asset_path(sfx_path.as_posix())
                self._sfx_cache[sfx_path] = pygame.mixer.Sound(resolved_path)
            
            sound = self._sfx_cache[sfx_path]
            
            # Apply Master Volume
            # Use specific base_volume if provided, else use global sfx_volume
            vol = self.sfx_volume if base_volume is None else clamp(base_volume) * self.sfx_volume
            sound.set_volume(vol)
            
            # Play to get a Channel
            channel = sound.play()
            if not channel: return
            
            # Apply Panning (If requested)
            if left_volume is not None and right_volume is not None and self.directional_sfx:
                clamped_vol_r = clamp(right_volume)
                clamped_vol_l = clamp(left_volume)
                channel.set_volume(clamped_vol_l, clamped_vol_r)
                self._debug_msg(f"Played SFX (Pan): L={clamped_vol_l:.1f} R={clamped_vol_r:.1f}")
            else:
                # Force full volume on this channel if centered (overrides previous settings)
                channel.set_volume(1.0, 1.0)
                self._debug_msg(f"Played SFX (Center)")
                    
        except Exception as e:
            self._debug_msg(f"Failed to play SFX: {e}")

global_audio_manager = AudioManager(debug=False)