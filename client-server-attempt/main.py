
import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from enum import Enum, unique
import re

import uvicorn
from fastapi import FastAPI, WebSocket
from starlette.endpoints import WebSocketEndpoint
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import asyncio

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

import janus
from functools import partial
from threading import Timer

from resize_gifs import try_and_resize_gifs, try_and_resize_all_gifs


DIR_PATH = os.path.dirname(os.path.realpath(__file__))
FRONTEND_PATH = os.path.join(DIR_PATH, 'vanilla-js-client')
INDEX_PATH = os.path.join(FRONTEND_PATH, 'index.html')

GIF_PATH = os.path.join(DIR_PATH, 'gifs')
IS_GIF = re.compile('.+?.gif$', re.IGNORECASE)


IS_PI = hasattr(os, 'uname') and os.uname()[4][:3] == 'arm'

TOGGLE_BUTTON = 21
POWER_BUTTON = 20

if IS_PI:
    from gpiozero import Button
    chrome_path = '/usr/bin/chromium-browser'
else:
    from pynput import keyboard
    chrome_path = 'C:\Program Files (x86)\Google\Chrome\Application\chrome'


class ButtonWatcher:

    _toggle_flag = False
    power_off_flag = False

    @classmethod
    def Startup(cls):
        if not IS_PI:
            queue = janus.Queue()
            bound_key_down = partial(cls._HandleKeydown, queue.sync_q)
            bound_key_up = partial(cls._HandleKeyup, queue.sync_q)
            listener = keyboard.Listener(
                on_press=bound_key_down,
                on_release=bound_key_up
            )
            listener.start()
            asyncio.create_task(cls._ProxyKeys(queue.async_q))
        else:
            queue = janus.Queue()

            cls.toggle_button = Button(TOGGLE_BUTTON)
            bound_toggle_pressed = partial(cls._ToggleButtonPushed, queue.sync_q)
            cls.toggle_button.when_pressed = bound_toggle_pressed
            bound_toggle_released = partial(cls._ToggleButtonReleased, queue.sync_q)
            cls.toggle_button.when_released = bound_toggle_released

            cls.power_button = Button(POWER_BUTTON)
            if cls.power_button.is_pressed:
                cls.power_off_flag = True

            bound_power_pressed = partial(cls._PowerButtonPushed, queue.sync_q)
            cls.power_button.when_pressed = bound_power_pressed
            bound_power_released = partial(cls._PowerButtonReleased, queue.sync_q)
            cls.power_button.when_released = bound_power_released

            asyncio.create_task(cls._ProxyButtons(queue.async_q))

    @classmethod
    def _HandleKeydown(cls, queue, key):
        queue.put(('DOWN', key))

    @classmethod
    def _HandleKeyup(cls, queue, key):
        queue.put(('UP', key))

    @classmethod
    async def _ProxyKeys(cls, queue):
        while True:
            direction, key = await queue.get()
            if direction == 'DOWN':
                cls._DoHandleKeydown(key)
            elif direction == 'UP':
                cls._DoHandleKeyup(key)

    @classmethod
    def _DoHandleKeydown(cls, key):
        if key == keyboard.Key.space:
            cls._DoPowerButtonPushed()
        # right arrow, toggle
        elif key == keyboard.Key.right:
            cls._DoToggleButtonPushed()

    @classmethod
    def _DoHandleKeyup(cls, key):
        if key == keyboard.Key.space:
            cls._DoPowerButtonReleased()
        # right arrow, toggle
        elif key == keyboard.Key.right:
            cls._DoToggleButtonReleased()

    @classmethod
    def _ToggleButtonPushed(cls, queue):
        queue.put('TOGGLE_PUSHED')

    @classmethod
    def _ToggleButtonReleased(cls, queue):
        queue.put('TOGGLE_RELEASED')

    @classmethod
    def _PowerButtonPushed(cls, queue):
        queue.put('POWER_PUSHED')

    @classmethod
    def _PowerButtonReleased(cls, queue):
        queue.put('POWER_RELEASED')

    @classmethod
    async def _ProxyButtons(cls, queue):
        while True:
            button_name_and_direciton = await queue.get()
            if button_name_and_direciton == 'TOGGLE_PUSHED':
                cls._DoToggleButtonPushed()
            elif button_name_and_direciton == 'TOGGLE_RELEASED':
                cls._DoToggleButtonReleased()
            elif button_name_and_direciton == 'POWER_PUSHED':
                cls._DoPowerButtonPushed()
            elif button_name_and_direciton == 'POWER_RELEASED':
                cls._DoPowerButtonReleased()

    @classmethod
    def _DoToggleButtonPushed(cls):
        if cls._toggle_flag is True:
            return
        cls._toggle_flag = True
        ConnectionManager.SendToggleGif()

    @classmethod
    def _DoToggleButtonReleased(cls):
        if cls._toggle_flag is False:
            return
        cls._toggle_flag = False

    @classmethod
    def _DoPowerButtonPushed(cls):
        if cls.power_off_flag is True:
            return
        cls.power_off_flag = True
        ConnectionManager.SendPowerOff()

    @classmethod
    def _DoPowerButtonReleased(cls):
        if cls.power_off_flag is False:
            return
        cls.power_off_flag = False
        ConnectionManager.SendPowerOn()


class GifFolderWatcher:

    def __init__(self):
        Path(GIF_PATH).mkdir(parents=True, exist_ok=True)
        self.observer = Observer()

    def start(self):
        event_handler = GifFolderHandler()
        self.observer.schedule(event_handler, GIF_PATH, recursive=False)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()


class GifFolderHandler(PatternMatchingEventHandler):

    def __init__(self):
        # Set the patterns for PatternMatchingEventHandler
        PatternMatchingEventHandler.__init__(self, patterns=['*.gif'], ignore_directories=True, case_sensitive=False)

    def on_created(self, event):
        ConnectionManager.TryLoadGifs()

    def on_modified(self, event):
        ConnectionManager.TryLoadGifs()

    def on_deleted(self, event):
        ConnectionManager.TryLoadGifs()


@unique
class MessageTypes(Enum):
    POWER_ON = 'POWER_ON'
    POWER_OFF = 'POWER_OFF'
    TOGGLE_GIF = 'TOGGLE_GIF'
    LOAD_GIFS = 'LOAD_GIFS'
    NO_GIFS = 'NO_GIFS'


class ConnectionManager:

    active_connections: List[WebSocket] = []

    @classmethod
    async def connect(cls, websocket: WebSocket):
        await websocket.accept()
        cls.active_connections.append(websocket)
        cls.TryLoadGifs()
        if ButtonWatcher.power_off_flag:
            cls.SendPowerOff()

    @classmethod
    def disconnect(cls, websocket: WebSocket):
        # pretty sure i should tear this bitch down
        cls.active_connections.remove(websocket)

    @classmethod
    async def _broadcast(cls, message: Dict[str, Any]):
        for connection in cls.active_connections:
            await connection.send_json(message)

    @classmethod
    def SendPowerOn(cls):
        asyncio.create_task(cls._broadcast({"message": MessageTypes.POWER_ON.value}))

    @classmethod
    def SendPowerOff(cls):
        asyncio.create_task(cls._broadcast({"message": MessageTypes.POWER_OFF.value}))

    @classmethod
    def SendToggleGif(cls):
        asyncio.create_task(cls._broadcast({"message": MessageTypes.TOGGLE_GIF.value}))

    @classmethod
    def TryLoadGifs(cls):
        gif_list = [
            os.path.join('gifs', f)
            for f in os.listdir(GIF_PATH)
            if os.path.isfile(os.path.join(GIF_PATH, f))
            and IS_GIF.match(f)
        ]
        if len(gif_list) == 0:
            asyncio.create_task(cls._SendNoGifs())
        else:
            asyncio.create_task(cls._ResizeAndSendGifs(gif_list))

    @classmethod
    async def _SendNoGifs(cls):
        await cls._broadcast({"message": MessageTypes.NO_GIFS.value})

    @classmethod
    async def _ResizeAndSendGifs(cls, gif_paths: List[str]):
        await try_and_resize_gifs(gif_paths)
        await cls._SendLoadGifs(gif_paths)


    @classmethod
    async def _SendLoadGifs(cls, gif_paths: List[str]):
        await cls._broadcast({
            "message": MessageTypes.LOAD_GIFS.value,
            "gifs": gif_paths
        })


app = FastAPI()


@app.websocket_route("/ws")
class CalibrationConnection(WebSocketEndpoint):
    encoding = 'text'

    async def on_connect(self, websocket: WebSocket) -> None:
        await ConnectionManager.connect(websocket)

    async def on_disconnect(self, websocket: WebSocket, close_code: int) -> None:
        ConnectionManager.disconnect(websocket)


@app.get("/")
async def root():
    with open(INDEX_PATH) as f:
        return HTMLResponse(content=f.read(), status_code=200)


app.mount("/gifs", StaticFiles(directory=GIF_PATH), name="static")
app.mount("/", StaticFiles(directory=FRONTEND_PATH), name="static")

folder_watcher: Optional[GifFolderWatcher] = None


@app.on_event("startup")
async def startup_event():
    await try_and_resize_all_gifs()
    global folder_watcher
    folder_watcher = GifFolderWatcher()
    folder_watcher.start()
    ButtonWatcher.Startup()

    def do_open_browser():
        subprocess.Popen([chrome_path, '--start-fullscreen', 'http://localhost:42069'])
    Timer(2.0, do_open_browser)


@app.on_event("shutdown")
def shutdown_event():
    global folder_watcher
    folder_watcher.stop()


if __name__ == '__main__':
    uvicorn.run("main:app", host="0.0.0.0", port=42069, log_level="info")
