
import pathlib
import os

from PIL import Image, ImageTk

import tkinter as tk

FILE_PATH = pathlib.Path(__file__).parent.absolute()
GIF_PATH = os.path.join(FILE_PATH, 'data')


def resize_gif(path, save_as=None, resize_to=None):
    """
    Resizes the GIF to a given length:

    Args:
        path: the path to the GIF file
        save_as (optional): Path of the resized gif. If not set, the original gif will be overwritten.
        resize_to (optional): new size of the gif. Format: (int, int). If not set, the original GIF will be resized to
                              half of its size.
    """
    all_frames = extract_and_resize_frames(path, resize_to)

    if not save_as:
        save_as = path

    if len(all_frames) == 1:
        print("Warning: only 1 frame found")
        all_frames[0].save(save_as, optimize=True)
    else:
        all_frames[0].save(save_as, optimize=True, save_all=True, append_images=all_frames[1:], loop=1000)


def extract_and_resize_frames(path, resize_to=None):
    """
    Iterate the GIF, extracting each frame and resizing them

    Returns:
        An array of all frames
    """

    im = Image.open(path)

    if not resize_to:
        resize_to = (im.size[0] * 2, im.size[1] * 2)

    i = 0
    p = im.getpalette()
    last_frame = im.convert('RGBA')

    all_frames = []

    try:
        while True:
            all_frames.append(im.copy())
            im.seek(len(all_frames))
    except EOFError:
        pass

    return [
        ImageTk.PhotoImage(frame.convert('RGBA').resize(resize_to))
        for frame in all_frames
    ]


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

    print('resizing to ' + str(screen_width) + 'x' + str(screen_height))

    for gif in gif_list:
        print(gif)
        resize_gif(gif, save_as=gif, resize_to=(screen_width, screen_height))

