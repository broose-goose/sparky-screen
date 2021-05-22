import os
from PIL import Image
import asyncio

import re
from functools import partial
import concurrent.futures

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
GIF_PATH = os.path.join(DIR_PATH, 'gifs')
IS_GIF = re.compile('.+?.gif$', re.IGNORECASE)


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


def analyseImage(path):
    """
    Pre-process pass over the image to determine the mode (full or additive).
    Necessary as assessing single frames isn't reliable. Need to know the mode
    before processing all frames.
    """
    im = Image.open(path)
    results = {
        'size': im.size,
        'mode': 'full',
    }
    try:
        while True:
            if im.tile:
                tile = im.tile[0]
                update_region = tile[1]
                update_region_dimensions = update_region[2:]
                if update_region_dimensions != im.size:
                    results['mode'] = 'partial'
                    break
            im.seek(im.tell() + 1)
    except EOFError:
        pass
    return results


def extract_and_resize_frames(path, resize_to=None):

    """
    Iterate the GIF, extracting each frame and resizing them

    Returns:
        An array of all frames
    """
    mode = analyseImage(path)['mode']

    im = Image.open(path)

    if not resize_to:
        resize_to = (im.size[0] // 2, im.size[1] // 2)

    i = 0
    p = im.getpalette()
    last_frame = im.convert('RGBA')

    all_frames = []

    try:
        while True:

            '''
            If the GIF uses local colour tables, each frame will have its own palette.
            If not, we need to apply the global palette to the new frame.
            '''
            if not im.getpalette():
                im.putpalette(p)

            new_frame = Image.new('RGBA', im.size)

            '''
            Is this file a "partial"-mode GIF where frames update a region of a different size to the entire image?
            If so, we need to construct the new frame by pasting it on top of the preceding frames.
            '''
            if mode == 'partial':
                new_frame.paste(last_frame)

            new_frame.paste(im, (0, 0), im.convert('RGBA'))

            new_frame = new_frame.resize(size=resize_to, resample=Image.LANCZOS)
            all_frames.append(new_frame)

            i += 1
            last_frame = new_frame
            im.seek(im.tell() + 1)
    except EOFError:
        pass

    return all_frames


def try_and_resize_gif(screen_width, screen_height, gif):
    path = os.path.join(DIR_PATH, gif)
    check_image_size = Image.open(path).size
    if check_image_size[0] != screen_width or check_image_size[1] != screen_height:
        resize_gif(path, resize_to=(screen_width, screen_height))


async def try_and_resize_gifs(gif_list):

    screen_width = 1280
    screen_height = 1040

    loop = asyncio.get_running_loop()

    with concurrent.futures.ProcessPoolExecutor() as pool:
        resize_calls = [
            partial(try_and_resize_gif, screen_width, screen_height, gif)
            for gif in gif_list
        ]
        futures_list = [loop.run_in_executor(pool, resize_call) for resize_call in resize_calls]
        for coro in asyncio.as_completed(futures_list):
            await coro


async def try_and_resize_all_gifs():
    gif_list = [
        os.path.join('gifs', f)
        for f in os.listdir(GIF_PATH)
        if os.path.isfile(os.path.join(GIF_PATH, f))
        and IS_GIF.match(f)
    ]
    await try_and_resize_gifs(gif_list)


if __name__ == '__main__':
    asyncio.run(try_and_resize_all_gifs())
