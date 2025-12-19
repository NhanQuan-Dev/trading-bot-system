from typing import Any, Dict
import asyncio
import websockets
import json

class WebSocketClient:
    def __init__(self, url: str):
        self.url = url
        self.connection = None

    async def connect(self):
        self.connection = await websockets.connect(self.url)

    async def disconnect(self):
        if self.connection:
            await self.connection.close()

    async def listen(self, callback: Any):
        try:
            async for message in self.connection:
                data = json.loads(message)
                await callback(data)
        except Exception as e:
            print(f"Error while listening: {e}")

    async def send(self, message: Dict[str, Any]):
        if self.connection:
            await self.connection.send(json.dumps(message))