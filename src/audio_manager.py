import flet as ft
import flet_audio as fta
from dataclasses import dataclass
from enum import Enum


@dataclass
class AudioTrack:
    name: str
    src: str

class SFXList(Enum):
    BOOM = AudioTrack("Boom", "audio/sfx/boom.wav")
    ALARM = AudioTrack("Alarm", "audio/sfx/alarm.wav")

class MusicList(Enum):
    BOSSA_BRASIL = AudioTrack("Summer Samba - World Music Bossa Brasil", "audio/music/summer-samba_world-music-bossa-brasil.mp3")


class BaseAudioManager:
    """Base class for Audio Managers."""
    def __init__(
        self, volume: ft.Number, balance: ft.Number,
        namespace: str, debug: bool = True
    ):
        self.volume = volume
        self.balance = balance
        self.namespace = namespace
        self.debug = debug
    
    def _debug_msg(self, msg: str) -> None:
        if self.debug:
            print(f"[{self.namespace}] {msg}")

class MusicManager(BaseAudioManager):
    """Handles long audio playbacks."""
    def __init__(self, volume: ft.Number = 1, balance: ft.Number = 0):
        super().__init__(volume, balance, "MusicManager")
        self.music = None
    
    def _make_audio(self, audio_track: AudioTrack):
        return fta.Audio(
            src=audio_track.src, autoplay=True, volume=self.volume,
            balance=self.balance
        )
    
    async def play(self, music: MusicList):
        if self.music is None:
            self._debug_msg(f"Playing New Music: {music.value.name}")
            self.music = self._make_audio(music.value)
            return
        if self.music.src != music.value.src:
            self._debug_msg(f"Replacing Music to: {music.value.name}")
            await self.music.release(timeout=2)
            self.music = self._make_audio(music.value)
        else:
            self._debug_msg(f"Replaying Music: {music.value.name}")
            await self.music.play()
    
class SFXManager(BaseAudioManager):
    """Handles one-shot audio playback."""
    def __init__(self, volume: ft.Number = 1, balance: ft.Number = 0):
        super().__init__(volume, balance, "SFXManager")
        self.sfx_list: list[fta.Audio] = []
    
    def _make_audio(self, audio_track: AudioTrack):
        def on_state_change(e: fta.AudioStateChangeEvent):
            if e.state == fta.AudioState.COMPLETED:
                self._debug_msg(f"Finished playing: {audio_track.name} | Queue: {sfx.data}")
                self.sfx_list.remove(sfx)
        sfx = fta.Audio(
            src=audio_track.src, autoplay=True, volume=self.volume,
            balance=self.balance, data=len(self.sfx_list),
            on_state_change=on_state_change
        )
        return sfx
    
    async def play(self, sfx: SFXList, stack_same_audio: bool = False):
        target_src = sfx.value.src
        existing_sfx = next((a for a in self.sfx_list if a.src == target_src), None)
        
        if existing_sfx and not stack_same_audio:
            self._debug_msg(f"Replaying existing SFX: {sfx.value.name}")
            await existing_sfx.play()
            return
        
        self._debug_msg(f"Creating new SFX instance: {sfx.value.name}")
        self.sfx_list.append(self._make_audio(sfx.value))
    

# * Run this file for a test
def test(page: ft.Page):
    page.title = "Audio Manager Test"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    sfx_manager = SFXManager()
    music_manager = MusicManager()
    
    async def play_boom(_):
        await sfx_manager.play(SFXList.BOOM)
    
    async def play_alarm(_):
        await sfx_manager.play(SFXList.ALARM)
    
    async def on_play_music(_):
        await music_manager.play(MusicList.BOSSA_BRASIL)
    
    form = ft.Column(
        controls=[
            ft.Text("SFX"),
            ft.Row(
                controls=[
                    ft.Button("Play Boom", on_click=play_boom),
                    ft.Button("Play Alarm", on_click=play_alarm),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            ),
            ft.Container(width=10, height=30),
            ft.Text("Music"),
            ft.Row(
                controls=[
                    ft.Button("Play Music", on_click=on_play_music),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )
    page.add(form)
    
if __name__ == "__main__":
    ft.run(test)