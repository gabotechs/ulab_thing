import aiohttp
import socketio


class UlabApi:
    def __init__(self, url_socket: str, url_backend: str, token: str):
        self.url_socket = url_socket
        self.url_backend = url_backend
        self.token = token
        self.socket = socketio.AsyncClient()

        self.session = aiohttp.ClientSession(headers={"Token": self.token})

    async def download(self, file: str) -> aiohttp.ClientResponse:
        url = self.url_backend + '/gcodes/get?id=' + file
        r = await self.session.get(url)
        return r

    async def connect(self) -> None:
        path = '/'.join(self.url_socket.split("/")[3:]) + '/socket.io'
        await self.socket.connect(self.url_socket, namespaces=['/pandora'], headers={"Token": self.token}, socketio_path=path)

    async def update_status(self, spec: dict) -> None:
        await self.socket.emit("update", spec, namespace='/pandora')


