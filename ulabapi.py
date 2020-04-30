import aiohttp
import socketio
from exceptions import GetFileException
from typing import Dict
from base64 import b64encode


class UlabApi:
    def __init__(self, url, user, password):
        self.url = url
        self.user = user
        self.password = password
        self.socket = socketio.AsyncClient()

        self.session = aiohttp.ClientSession(auth=aiohttp.BasicAuth(user, password))

    async def connect(self) -> None:
        await self.socket.connect(self.url, namespaces=['/pandora'], headers={"Authorization": "Basic "+b64encode((self.user+":"+self.password).encode()).decode()})

    async def update_status(self, spec) -> None:
        await self.socket.emit("update", spec, namespace='/pandora')

    async def get_file(self, _id: str) -> Dict:
        r = await self.session.get(self.url+'/files/get?id='+_id)
        if r.status == 404:
            raise GetFileException(r.status)
        elif r.status != 200:
            raise Exception("error requesting file "+str(r.status))
        return await r.json()

