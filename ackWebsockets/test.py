from ackWebsockets.baseSocket import Socket
import typing as T
import websockets
import asyncio

PORT = 5100


class TestRunner:
    received: T.List[str] = []
    exit_thread: bool = False

    async def launch_server(self):
        print("started server thread")

        async def handler(websocket: websockets.WebSocketServerProtocol, path: str):
            s = Socket(websocket, self.loop)
            s.on("test-event", lambda x: self.received.append(x))
            await s.run()

        await websockets.serve(handler, "0.0.0.0", PORT, loop=self.loop)
        print("listening on port", PORT)

    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    def terminate(self):
        pass

    async def connect_to_server(self):
        conn = await websockets.connect(f"ws://127.0.0.1:{PORT}")
        print("websocket connected")

        print("sending message and testing that it has been received", end="... ")

        await conn.send("test-event holi")
        await asyncio.sleep(0.2)
        assert "holi" in self.received
        print("correct")

        print("sending message and testing that it has not been received", end="... ")
        await conn.send("INCORRECT-test-event holi")
        await asyncio.sleep(0.2)
        assert "holaa" not in self.received
        print("correct")

        await conn.close()


async def main(loop: asyncio.AbstractEventLoop):
    runner = TestRunner(loop)
    await runner.launch_server()
    await asyncio.sleep(0.5)
    await runner.connect_to_server()
    runner.terminate()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))
