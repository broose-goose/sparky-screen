
import pathlib
import os

from typing import Optional, List

import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk


FILE_PATH = pathlib.Path(__file__).parent.absolute()
GIF_PATH = os.path.join(FILE_PATH, 'data')

# 30hz
REFRESH_DELAY = 33

IS_PI = hasattr(os, 'uname') and os.uname()[4][:3] == 'arm'

TOGGLE_BUTTON = 21
POWER_BUTTON = 20

if IS_PI:
    from gpiozero import Button


class GifViewer(tk.Frame):

    def _LoadGifs(self):
        gif_list = [
            os.path.join(GIF_PATH, f)
            for f in os.listdir(GIF_PATH)
            if os.path.isfile(os.path.join(GIF_PATH, f))
        ]
        # didn't find any gifs...
        if len(gif_list) == 0:
            messagebox.showerror('EXTREME ERROR', 'AGHHHH, NO GIFFS D:\nClosing program in disgust')
            self.panicked_parent.PANIC()
            return
        
        for gif in gif_list:
            gif_image = Image.open(gif)
            gif_frames = []
            try:
                while True:
                    frame = ImageTk.PhotoImage(gif_image.copy())
                    gif_frames.append(frame)
                    gif_image.seek(len(gif_frames))
            except EOFError:
                pass
            self.gifs.append(gif_frames)

    def GetNextGif(self):
        self.current_frame = 0
        next_gif = self.current_gif + 1
        self.current_gif = next_gif if next_gif < len(self.gifs) else 0

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.panicked_parent: SparkyScreen = parent
        self.current_gif: int = 0
        self.current_frame: int = 0
        self.gifs: List[List[ImageTk]] = []
        self.screen_width = parent.winfo_screenwidth()
        self.screen_height = parent.winfo_screenheight()
        self._LoadGifs()
        blank_image = Image.new('RGB', (self.screen_width, self.screen_height), 'black')
        self.blank_image = ImageTk.PhotoImage(blank_image)
        self.image_label = tk.Label(self)
        self.image_label.pack(fill=tk.BOTH, expand=tk.YES)

    def _StepFrame(self):
        next_frame = self.current_frame + 1
        self.current_frame = next_frame if next_frame < len(self.gifs[self.current_gif]) else 0

    def UpdateImage(self):
        self.image_label.config(image=self.gifs[self.current_gif][self.current_frame])
        self._StepFrame()

    def DisplayBlack(self):
        self.image_label.config(image=self.blank_image)
        self._StepFrame()


class SparkyScreen(tk.Tk):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.wm_attributes('-fullscreen', 'true')
        self.resizable(width=False, height=False)
        self.gif_viewer: GifViewer = GifViewer(self)
        self.gif_viewer.pack(fill=tk.BOTH)
        self.toggle_flag = False
        self.last_toggle = False
        self.power_off_flag = False
        if not IS_PI:
            self.bind('<KeyPress>', self.Keydown)
            self.bind('<KeyRelease>', self.Keyup)
        else:
            self.toggle_button = Button(TOGGLE_BUTTON)
            self.toggle_button.when_pressed = self._ToggleButtonPushed
            self.toggle_button.when_released = self._ToggleButtonReleased
            self.power_button = Button(POWER_BUTTON)
            self.power_button.when_pressed = self._PowerButtonPushed
            self.power_button.when_released = self._PowerButtonReleased
        self.after(REFRESH_DELAY, self.DoUpdate)

    def Keydown(self, event):
        # spacebar, toggle
        if event.keycode == 32:
            self._ToggleButtonPushed()
        # left arrow, power
        elif event.keycode == 37:
            self._PowerButtonPushed()

    def Keyup(self, event):
        # spacebar, toggle
        if event.keycode == 32:
            self._ToggleButtonReleased()
        # left arrow, power
        if event.keycode == 37:
            self._PowerButtonReleased()

    def _ToggleButtonPushed(self):
        self.toggle_flag = True

    def _ToggleButtonReleased(self):
        self.toggle_flag = False

    def _PowerButtonPushed(self):
        self.power_off_flag = True

    def _PowerButtonReleased(self):
        self.power_off_flag = False

    def DoUpdate(self):

        # if its a new toggle
        if self.toggle_flag and self.toggle_flag != self.last_toggle:
            # get the next image
            self.gif_viewer.GetNextGif()
        # make sure holding down the button won't spam it
        self.last_toggle = self.toggle_flag

        # display black if "no power"
        if self.power_off_flag:
            self.gif_viewer.DisplayBlack()
        # otherwise, show the image
        else:
            self.gif_viewer.UpdateImage()

        # manually reset the counter
        self.after(REFRESH_DELAY, self.DoUpdate)

    def PANIC(self):
        self.destroy()


if __name__ == '__main__':
    app = SparkyScreen()
    app.mainloop()
