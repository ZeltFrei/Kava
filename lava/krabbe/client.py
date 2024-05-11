import json
import uuid
from asyncio import Future
from logging import getLogger
from typing import Optional, Dict, Callable, Any, Coroutine, TYPE_CHECKING, List

import websockets
from websockets import WebSocketClientProtocol

if TYPE_CHECKING:
    from lava.bot import Bot


class Request:
    def __init__(self, client: 'KavaClient', request_id: str, data: Dict[str, Any]):
        self.client = client
        self.id = request_id
        self.data = data

    async def respond(self, response_data: Dict[str, Any]) -> None:
        response = {
            "type": "response",
            "id": self.id,
            "data": response_data
        }

        await self.client.websocket.send(json.dumps(response))


class KavaClient:
    logger = getLogger("kava.client")

    def __init__(self, bot: "Bot", uri: str):
        self.bot: "Bot" = bot
        self.uri = uri
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.pending_requests: Dict[str, Future] = {}
        self.handlers: Dict[str, List[Callable[[Request, Any], Coroutine[Any, Any, None]]]] = {}

    async def _handle_messages(self) -> None:
        async for message in self.websocket:
            data = json.loads(message)

            if data['type'] == "request":
                _ = data.bot.loop.create_task(self._handle_request(data))
            elif data['type'] == "response":
                request_id = message.get('id')

                if request_id in self.pending_requests:
                    self.pending_requests[request_id].set_result(data['data'])
                    del self.pending_requests[request_id]

    async def _handle_request(self, request: Dict[str, Any]) -> None:
        self.logger.debug(f"Handling request {request}")

        request_id = request['id']
        endpoint = request['endpoint']
        data = request['data']

        request_obj = Request(self, request_id, data)

        if endpoint in self.handlers:
            for handler in self.handlers[endpoint]:
                _ = self.bot.loop.create_task(handler(request_obj, **data))
        else:
            await request_obj.respond({"status": "error", "message": "No handler for endpoint"})

    async def request(self, endpoint: str, **kwargs: Any) -> Any:
        request_id = str(uuid.uuid4())
        future = Future()

        self.pending_requests[request_id] = future

        message = {
            "type": "request",
            "id": request_id,
            "endpoint": endpoint,
            "data": kwargs
        }

        await self.websocket.send(json.dumps(message))

        return await future

    def add_handler(self, endpoint: str, handler: Callable[[Request, Any], Coroutine[Any, Any, None]]) -> None:
        """
        Add a handler for a specific endpoint.
        :param endpoint: The endpoint to add the handler for.
        :param handler: The handler to add.
        :return: None
        """
        self.logger.debug(f"Adding handler for endpoint {endpoint}")

        if endpoint not in self.handlers:
            self.handlers[endpoint] = []

        self.handlers[endpoint].append(handler)

    async def connect(self) -> None:
        self.logger.info("Connecting to Kava server...")

        if not self.websocket or self.websocket.closed:
            self.websocket = await websockets.connect(self.uri)
            _ = self.bot.loop.create_task(self._handle_messages())

    async def close(self) -> None:
        self.logger.info("Closing Kava client...")

        if self.websocket:
            await self.websocket.close()
            self.websocket = None
