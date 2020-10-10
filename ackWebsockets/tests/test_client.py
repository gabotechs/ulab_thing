from ackWebsockets.baseSocket import Socket
from ackWebsockets.SocketMessageResponse import SocketMessageResponse
from ackWebsockets.tests.constants import *
from ackWebsockets.tests.test_server import TestServer
import typing as T
import websockets
import asyncio

PORT = 5100


class TestRunner:
    received: T.List[str] = []
    disconnections: T.List[int] = []
    exit_thread: bool = False

    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    def terminate(self):
        pass

    async def connection(self):
        server = TestServer(self.loop)
        await server.start()

        await asyncio.sleep(0.2)
        conn = await websockets.connect(f"ws://127.0.0.1:{PORT}")
        s = Socket(conn)
        self.loop.create_task(s.run())
        print("websocket connected")

        async def on_disconnect():
            self.disconnections.append(1)
        s.onDisconnect(on_disconnect)

        print("testing disconnection", end="... ")
        await server.terminate_all()
        await asyncio.sleep(0.2)
        assert len(self.disconnections) == 1
        print("correct")

        print("testing reconnection", end="... ")
        conn = await websockets.connect(f"ws://127.0.0.1:{PORT}")
        s = Socket(conn)
        await s.emit("test-event", "none")
        print("correct")

    async def message_sending(self):
        server = TestServer(self.loop)
        await server.start()

        await asyncio.sleep(0.2)
        conn = await websockets.connect(f"ws://127.0.0.1:{PORT}")
        s = Socket(conn)
        self.loop.create_task(s.run())
        print("websocket connected")
        await asyncio.sleep(0.5)

        print("stablishing callbacks", end="... ")
        async def h1(x): self.received.append(x)
        async def h2(x): return SocketMessageResponse(0, x)
        [s.on("test-event", h1) for s in server.s]
        [s.on_sync("test-event-sync", h2) for s in server.s]
        print("correct")

        print("sending message and testing that it has been received", end="... ")
        await s.emit("test-event", "holi")
        await asyncio.sleep(0.2)
        assert "holi" in self.received
        print("correct")

        print("sending message and testing that it has not been received", end="... ")
        await s.emit("INCORRECT-test-event", "holaa")
        await asyncio.sleep(0.2)
        assert "holaa" not in self.received
        print("correct")

        print("sending sync message and waiting for response", end="... ")
        r = await s.emitSync("test-event-sync", "holi")
        assert r.status == 0
        assert r.message == "holi"
        print("correct")

        await conn.close()
        await server.close()


async def main(loop: asyncio.AbstractEventLoop):
    runner = TestRunner(loop)
    await runner.message_sending()
    await runner.connection()
    runner.terminate()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))
