import typing as T
import time
import asyncio
import websockets
from ackWebsockets.SocketMessage import SocketMessage, IncorrectSocketMessage, parseIncomingMessage
from ackWebsockets.SocketMessageResponse import SocketMessageResponse


class Socket:
    conn: T.Union[websockets.WebSocketClientProtocol, websockets.WebSocketServerProtocol]
    send: T.List[SocketMessage] = []
    ignoreListeners: T.Dict[str, T.Callable[[str], None]] = {}
    waitListeners: T.Dict[str, T.Callable[[str], SocketMessageResponse]] = {}

    def __init__(self, conn: T.Union[websockets.WebSocketClientProtocol, websockets.WebSocketServerProtocol], loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()):
        self.conn = conn
        self.label: str = "server" if isinstance(conn, websockets.WebSocketServerProtocol) else "client"

    async def run(self):
        await asyncio.wait([self.readPump()])

    def on_sync(self, event: str, handler: T.Callable[[str], SocketMessageResponse]):
        self.waitListeners[event] = handler

    def on(self, event: str, handler: T.Callable[[str], None]):
        self.ignoreListeners[event] = handler

    async def readPump(self):
        while True:
            try:
                msg = await self.conn.recv()
                print("message:", msg)
            except websockets.ConnectionClosedOK:
                print(f"{self.label} - connection close detected in read pump")
                break
            except websockets.ConnectionClosedError:
                print(f"{self.label} Warning - unexpected connection close")
                break

            try:
                incoming_message = parseIncomingMessage(msg)
            except IncorrectSocketMessage as e:
                print(f"{self.label} Warning - incorrect socket message", e)
                continue

            if incoming_message.event in self.waitListeners:
                socket_message_response = self.waitListeners[incoming_message.event](incoming_message.data)
                if len(incoming_message.id):
                    await self.conn.send(socket_message_response.encode())
            elif incoming_message.event in self.ignoreListeners:
                self.ignoreListeners[incoming_message.event](incoming_message.data)
            else:
                print(f"{self.label} Warning - no callback for event", incoming_message.event)

    async def writePump(self):
        last_ping = time.time()
        while True:
            if self.exit_write_pump:
                break
            for msg in self.send:
                await self.conn.send(msg.encode())
                last_ping = time.time()
            if time.time() - last_ping > 10:
                await self.conn.send("")  # todo: ping message
            await asyncio.sleep(0.001)

    async def emit(self, event: str, data: str):
        await self.conn.send(SocketMessage(event, "", data).encode())

    async def wait_close(self):
        self.conn
