from base64 import b64encode
from typing import Dict

import aiohttp
import socketio

from exceptions import GetFileException


class UlabApi:
    def __init__(self, url, token):
        self.url = url
        self.token = token
        self.socket = socketio.AsyncClient()

        self.session = aiohttp.ClientSession(headers={"Token": self.token})

    async def connect(self) -> None:
        await self.socket.connect(self.url, namespaces=['/pandora'], headers={"Token": self.token})

    async def update_status(self, spec) -> None:
        await self.socket.emit("update", spec, namespace='/pandora')


