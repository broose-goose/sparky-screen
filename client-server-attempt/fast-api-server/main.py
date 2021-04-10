
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
    chrome_path = 'C:\Program Files (x86)\Google\Chrome\Application\chrome'


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

    @classmethod
    def disconnect(cls, websocket: WebSocket):
        # pretty sure i should tear this bitch down
        cls.active_connections.remove(websocket)

    @classmethod
    async def _broadcast(cls, message: Dict[str, Any]):
        for connection in cls.active_connections:
            await connection.send_json(message)

    @classmethod
    async def SendPowerOn(cls):
        await cls._broadcast({ "message": MessageTypes.POWER_ON.value })

    @classmethod
    async def SendPowerOff(cls):
        await cls._broadcast({ "message": MessageTypes.POWER_OFF.value })

    @classmethod
    async def SendToggleGif(cls):
        await cls._broadcast({"message": MessageTypes.TOGGLE_GIF.value})

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
            asyncio.create_task(cls._SendLoadGifs(gif_list))

    @classmethod
    async def _SendNoGifs(cls):
        await cls._broadcast({"message": MessageTypes.NO_GIFS.value})

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


app.mount("/gifs", StaticFiles(directory="gifs"), name="static")
app.mount("/", StaticFiles(directory="vanilla-js-client"), name="static")

folder_watcher: Optional[GifFolderWatcher] = None


@app.on_event("startup")
async def startup_event():
    global folder_watcher
    folder_watcher = GifFolderWatcher()
    folder_watcher.start()
    subprocess.Popen(f'"{chrome_path}" --start-fullscreen http://localhost:42069')


@app.on_event("shutdown")
def shutdown_event():
    global folder_watcher
    folder_watcher.stop()


if __name__ == '__main__':
    uvicorn.run("main:app", host="0.0.0.0", port=42069, log_level="info")
