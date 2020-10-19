import typing as T
import asyncio
import aiohttp
import json
import ackWebsockets
import websockets


class UlabApi:
    def __init__(self, url_socket: str, url_backend: str, token: str):
        self.url_socket: str = url_socket
        self.url_backend: str = url_backend
        self.token: str = token
        self.socket: T.Union[None, ackWebsockets.Socket] = None
        self.session = aiohttp.ClientSession(headers={"Token": self.token})
        async def dummy(data: T.Optional[T.Union[str, Exception]] = ""): return
        self.on_connect: T.Callable[[], T.Awaitable[None]] = dummy
        self.on_init: T.Callable[[str], T.Awaitable[None]] = dummy
        self.on_unauthorized: T.Callable[[str], T.Awaitable[None]] = dummy
        self.on_disconnect: T.Callable[[], T.Awaitable[None]] = dummy
        self.on_error: T.Callable[[Exception], T.Awaitable[None]] = dummy
        self.on_stop: T.Callable[[str], T.Awaitable[None]] = dummy
        self.on_instruction: T.Callable[[str], T.Awaitable[ackWebsockets.SocketMessageResponse]] = dummy

    async def download(self, file: str) -> aiohttp.ClientResponse:
        url = self.url_backend + '/gcodes/get?id=' + file
        r = await self.session.get(url)
        return r

    async def reconnect(self):
        self.socket = None
        await asyncio.sleep(10)
        await self.connect()

    async def connect(self, loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()) -> None:
        while True:
            try:
                conn = await websockets.connect(self.url_socket, extra_headers={"Token": self.token})
                self.socket = ackWebsockets.Socket(conn)
                await self.on_connect()

                async def on_disconnect():
                    await self.on_disconnect()
                    await self.reconnect()
                self.socket.onDisconnect(on_disconnect)

                async def on_error(ex: Exception):
                    await self.on_error(ex)
                    await self.reconnect()
                self.socket.onError(on_error)
                self.socket.on("init", self.on_init)
                self.socket.on("stop", self.on_stop)
                self.socket.on_sync("instruction", self.on_instruction)
                loop.create_task(self.socket.run())
                break

            except Exception as e:  # todo: catch concrete exceptions
                await self.on_error(e)
                self.socket = None
                await asyncio.sleep(10)

    async def update_status(self, spec: dict) -> None:
        await self.socket.emit("update", json.dumps({"pandora": spec}))
