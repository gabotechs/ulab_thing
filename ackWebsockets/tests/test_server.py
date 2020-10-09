import typing as T
from ackWebsockets.baseSocket import Socket
from ackWebsockets.tests.constants import *
import websockets
import asyncio


class TestServer:
    s: T.Set[Socket] = set()
    server: T.Union[None, websockets.WebSocketServer] = None

    async def start(self):

        async def handler(websocket: websockets.WebSocketServerProtocol, path: str):
            s = Socket(websocket)
            self.s.add(s)
            await s.run()
        self.server = await websockets.serve(handler, "0.0.0.0", PORT, loop=self.loop)
        print("listening on port", PORT)

    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    async def terminate_all(self):
        for s in self.s:
            await s.close(1000, "disconnection")

    async def close(self):
        if self.server:
            await self.server._close()


async def main(loop: asyncio.AbstractEventLoop):
    runner = TestServer(loop)
    await runner.start()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))
    loop.run_forever()
