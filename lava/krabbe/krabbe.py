from typing import Optional, TYPE_CHECKING

from websockets import WebSocketClientProtocol, connect, Data, ConnectionClosed

if TYPE_CHECKING:
    from lava.bot import Bot


class Krabbe:
    def __init__(self, bot: "Bot"):
        self.bot: "Bot" = bot
        self.websocket: Optional[WebSocketClientProtocol] = None

    async def on_websocket_message(self, message: Data):
        pass

    async def message_handler(self):
        try:
            async for message in self.websocket:
                _ = self.bot.loop.create_task(self.on_websocket_message(message))
        except ConnectionClosed:
            pass
        finally:
            pass

    async def connect(self, uri: str):
        """
        Connects to the given URI.
        :param uri: The URI to connect to.
        """
        self.websocket = await connect(uri)

    def close(self):
        if self.websocket:
            self.websocket.close()
            self.websocket = None
