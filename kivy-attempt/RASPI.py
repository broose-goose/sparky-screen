
import os
from pathlib import Path
from typing import List, Callable
import re

import kivy
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import AsyncImage
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.config import Config

from screeninfo import get_monitors
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

Config.set('graphics', 'fullscreen', 'fake')
Config.write()

kivy.require('2.0.0')


GIF_PATH = os.path.join(Path.home(), '.config', 'gif-viewer')
IS_GIF = re.compile('.+?.gif$', re.IGNORECASE)

IS_PI = hasattr(os, 'uname') and os.uname()[4][:3] == 'arm'

TOGGLE_BUTTON = 21
POWER_BUTTON = 20

if IS_PI:
    from gpiozero import Button


class GifViewer(FloatLayout):

    def _LoadGifs(self):

        Path(GIF_PATH).mkdir(parents=True, exist_ok=True)

        gif_list = [
            os.path.join(GIF_PATH, f)
            for f in os.listdir(GIF_PATH)
            if os.path.isfile(os.path.join(GIF_PATH, f))
            and IS_GIF.match(f)
        ]
        # didn't find any gifs...
        if len(gif_list) == 0:
            popup = Popup(
                title='EXTREME ERROR',
                content=Label(text='AGHHHH, NO GIFFS D:\nClosing program in disgust'),
            )
            popup.bind(on_dismiss=App.get_running_app().stop)
            popup.open()
            return

        self._gifs = [
            AsyncImage(source=gif_path, size=Window.size, allow_stretch=True, keep_ratio=False)
            for gif_path in gif_list
        ]
        self.has_loaded = True

    def GetNextGif(self):
        if not self.has_loaded:
            return
        self.clear_widgets()
        next_gif = self._current_gif + 1
        self._current_gif = next_gif if next_gif < len(self._gifs) else 0
        self.add_widget(self._gifs[self._current_gif])

    def PowerOff(self):
        if not self.has_loaded:
            return
        self.clear_widgets()

    def PowerOn(self):
        if not self.has_loaded:
            return
        self.add_widget(self._gifs[self._current_gif])

    def __init__(self, **kwargs):
        super(GifViewer, self).__init__(**kwargs)
        self._current_gif: int = 0
        self._gifs: List[AsyncImage] = []
        self.has_loaded: bool = False
        self._LoadGifs()
        self.PowerOn()

    def ReloadGifs(self):
        if not self.has_loaded:
            return
        self.PowerOff()
        self._LoadGifs()
        self._current_gif = 0
        self.PowerOn()


class GifFolderWatcher:

    def __init__(self):
        self.observer = Observer()

    def start(self, viewer: GifViewer):
        event_handler = GifFolderHandler(viewer)
        self.observer.schedule(event_handler, GIF_PATH, recursive=False)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()


class GifFolderHandler(PatternMatchingEventHandler):

    def __init__(self, viewer: GifViewer):
        # Set the patterns for PatternMatchingEventHandler
        PatternMatchingEventHandler.__init__(self, patterns=['*.gif'], ignore_directories=True, case_sensitive=False)
        self.viewer = viewer

    def on_created(self, event):
        self.viewer.ReloadGifs()

    def on_modified(self, event):
        self.viewer.ReloadGifs()

    def on_deleted(self, event):
        self.viewer.ReloadGifs()


class SparkyScreen(App):

    def _keyboard_closed(self):
        self._keyboard.unbind(
            on_key_down=self.HandleKeydown,
            on_key_up=self.HandleKeyup
        )
        self._keyboard = None

    def HandleKeydown(self, keyboard, keycode, text, modifiers):
        # spacebar, power
        if keycode[0] == 32:
            self._PowerButtonPushed()
        # right arrow, toggle
        elif keycode[0] == 275:
            self._ToggleButtonPushed()

    def HandleKeyup(self, keyboard, keycode):
        # spacebar, power
        if keycode[0] == 32:
            self._PowerButtonReleased()
        # right arrow, toggle
        elif keycode[0] == 275:
            self._ToggleButtonReleased()

    def _ToggleButtonPushed(self):
        if self.toggle_flag is True:
            return
        self.toggle_flag = True
        self.gif_viewer.GetNextGif()

    def _ToggleButtonReleased(self):
        if self.toggle_flag is False:
            return
        self.toggle_flag = False

    def _PowerButtonPushed(self):
        if self.power_off_flag is True:
            return
        self.power_off_flag = True
        self.gif_viewer.PowerOff()

    def _PowerButtonReleased(self):
        if self.power_off_flag is False:
            return
        self.power_off_flag = False
        self.gif_viewer.PowerOn()

    def __init__(self, **kwargs):
        super(SparkyScreen, self).__init__(**kwargs)
        if not IS_PI:
            self._keyboard = Window.request_keyboard(self._keyboard_closed, self.root)
            self._keyboard.bind(
                on_key_down=self.HandleKeydown,
                on_key_up=self.HandleKeyup
            )
        else:
            self.toggle_button = Button(TOGGLE_BUTTON)
            self.toggle_button.when_pressed = self._ToggleButtonPushed
            self.toggle_button.when_released = self._ToggleButtonReleased
            self.power_button = Button(POWER_BUTTON)
            self.power_button.when_pressed = self._PowerButtonPushed
            self.power_button.when_released = self._PowerButtonReleased
        self.toggle_flag: bool = False
        self.power_off_flag: bool = False
        self.gif_viewer: GifViewer = GifViewer(size_hint=(None, None), size=Window.size)
        if not self.gif_viewer.has_loaded:
            return
        self.folder_watcher: GifFolderWatcher = GifFolderWatcher()
        self.folder_watcher.start(self.gif_viewer)

    def build(self):
        return self.gif_viewer

    def on_stop(self):
        if hasattr(self, 'folder_watcher'):
            self.folder_watcher.stop()


if __name__ == '__main__':
    Window.borderless = True
    monitors = get_monitors()
    main_monitor = monitors[0]
    Window.size = (main_monitor.width, main_monitor.height)
    Window.left = 0
    Window.top = 0
    SparkyScreen().run()
