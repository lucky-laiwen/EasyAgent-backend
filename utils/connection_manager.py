
from typing import Dict
from fastapi import WebSocket,Depends

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        self.active_connections.pop(user_id, None)

    async def send_private_message(self, to_user_id: int, message: dict):
        websocket = self.active_connections.get(to_user_id)
        if websocket:
            await websocket.send_json(message)

manager = ConnectionManager()
