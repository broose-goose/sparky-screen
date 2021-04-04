
import pathlib
import os
import pickle

from PIL import Image, ImageTk

import tkinter as tk

FILE_PATH = pathlib.Path(__file__).parent.absolute()
GIF_PATH = os.path.join(FILE_PATH, 'data')
PICKLE_FILE = os.path.join(FILE_PATH, 'gif_pickle.dat')


if __name__ == '__main__':

    gif_list = [
        os.path.join(GIF_PATH, f)
        for f in os.listdir(GIF_PATH)
        if os.path.isfile(os.path.join(GIF_PATH, f))
    ]

    if len(gif_list) == 0:
        print('wtf, no gifs bruh')
        quit()

    root = tk.Tk()

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    print('pickling gifs')
    gifs = []

    for gif in gif_list:
        gif_image = Image.open(gif)
        gif_frames = []
        try:
            while True:
                frame = ImageTk.PhotoImage(gif_image.copy())
                print(frame)
                quit()
                gif_frames.append(frame)
                gif_image.seek(len(gif_frames))
        except EOFError:
            pass
        gifs.append(gif_frames)

    pickle_file = open(PICKLE_FILE, 'wb')
    pickle.dump(gifs, pkl_file, protocol=pickle.HIGHEST_PROTOCOL)
