import flet as ft
import flet_audio as fta
import time
from typing import Optional

from utilities.values import clamp
from tests.test_templates import test_init

class AudioManager:
    """Handles all Flet-based audio playbacks with culling and cooldowns."""
    def __init__(
        self, 
        music_volume: float = 0.3,
        sfx_volume: float = 0.5,
        directional_sfx: bool = True,
        *, debug: bool = False
    ) -> None:
        self._music_volume = music_volume
        self._sfx_volume = sfx_volume
        self.directional_sfx = directional_sfx
        self.debug = debug
        
        # Performance & Logic tracking
        self._sfx_cooldowns: dict[str, float] = {}
        self._sfx_instances: list[fta.Audio] = []
        self.music_instance: Optional[fta.Audio] = None
    
    @property
    def sfx_volume(self) -> float:
        return self._sfx_volume
    
    @sfx_volume.setter
    def sfx_volume(self, volume: float) -> None:
        self._sfx_volume = round(clamp(volume), 1)
    
    @property
    def music_volume(self) -> float:
        return self._music_volume
    
    @music_volume.setter
    def music_volume(self, volume: float) -> None:
        self._music_volume = round(clamp(volume), 1)
        if self.music_instance:
            self.music_instance.volume = self._music_volume
            self.music_instance.update()
            
    def _debug_msg(self, msg: str) -> None:
        if self.debug: print(f"[AudioManager] {msg}")
        
    def play_music(self, music_src: str) -> None:
        """Plays music on a loop. Replaces current music if it exists."""
        try:
            if self.music_instance is None:
                self.music_instance = fta.Audio(
                    src=music_src,
                    autoplay=True,
                    volume=self.music_volume,
                    release_mode=fta.ReleaseMode.LOOP
                )
            else:
                self.music_instance.src = music_src
                self.music_instance.update()
        except Exception as e:
            self._debug_msg(f"Music Error: {e}")
            
    def play_sfx(
        self, sfx_src: str,
        left_volume: float = None,
        right_volume: float = None,
        base_volume: float = None
    ) -> None:
        """Plays a sound effect with panning and spam prevention."""
        try:
            # Distance Culling
            if self.directional_sfx and left_volume is not None and right_volume is not None:
                if left_volume < 0.01 and right_volume < 0.01: return
                
            # Spam Prevention (50ms Cooldown)
            curr_time: float = time.time()
            if curr_time - self._sfx_cooldowns.get(sfx_src, 0) < 0.05: return
            self._sfx_cooldowns[sfx_src] = curr_time
            
            # Calculate Balance (Panning)
            # Flet Balance: -1.0 (Left) to 1.0 (Right)
            calc_balance: float = 0.0
            if left_volume is not None and right_volume is not None:
                calc_balance = clamp(right_volume - left_volume, -1.0, 1.0)
                
            # Final Volume
            final_vol = self.sfx_volume if base_volume is None else clamp(base_volume) * self.sfx_volume
            
            # Create 'Fire and Forget' instance with auto-cleanup
            def on_state_change(e: fta.AudioStateChangeEvent):
                if e.data == "completed":
                    new_sfx.release() # Frees underlying platform resources
            
            new_sfx = fta.Audio(
                src=sfx_src,
                volume=final_vol,
                balance=calc_balance,
                autoplay=True,
                on_state_change=on_state_change
            )
            
        except Exception as e:
            self._debug_msg(f"SFX Error: {e}")

global_audio_manager = AudioManager()

# * Testing for the new audio manager
async def main(page: ft.Page) -> None:
    await test_init(page)
    
    audio_manager = AudioManager(
        music_volume=1.0,
        sfx_volume=1.0,
        debug=True
    )
    
    async def play_music() -> None:
        audio_manager.play_music("audio/music/forest_ambience.mp3")
    
    @ft.component
    def AudioControls() -> ft.Control:
        return ft.Column(
            controls=[
                ft.Button("Play Music", on_click=lambda _: page.run_task(play_music)),
                ft.Button("Pause Music", on_click=lambda _: page.run_task(audio_manager.music_instance.pause)),
                ft.Button("Resume Music", on_click=lambda _: page.run_task(audio_manager.music_instance.resume)),
                ft.Button("Play SFX (Center)", on_click=lambda _: audio_manager.play_sfx("audio/sfx/alarm.wav")),
                ft.Button("Play SFX (Pan Left)", on_click=lambda _: audio_manager.play_sfx("audio/sfx/alarm.wav", left_volume=1.0, right_volume=0.0)),
                ft.Button("Play SFX (Pan Right)", on_click=lambda _: audio_manager.play_sfx("audio/sfx/alarm.wav", left_volume=0.0, right_volume=1.0)),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
    
    page.render(AudioControls)

if __name__ == "__main__":
    ft.run(main, assets_dir="../assets")