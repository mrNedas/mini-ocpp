import asyncio
import json
import websockets
from datetime import datetime


class CentralSystem:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    async def process_message(self, websocket, message):
        try:
            message_id = message[1]
            action = message[2]
            payload = message[3]

            if action == "BootNotification":
                await self.process_boot_notification(websocket, message_id, payload)
            elif action == "Heartbeat":
                await self.process_heartbeat(websocket, message_id)
            else:
                print(f"Received unsupported action: {action}")
        except Exception as e:
            print(f"Error processing message: {e}")

    async def process_boot_notification(self, websocket, message_id, payload):
        print(f"Received BootNotification with payload: {payload}")
        response_payload = {
            "status": "Accepted",
            "currentTime": datetime.utcnow().isoformat() + "Z",  # Current time in ISO 8601 format
            "interval": 300  # Heartbeat interval in seconds, CP should set this value as heartbeat interval
        }
        response = [3, message_id, response_payload]
        response_json = json.dumps(response)
        await websocket.send(response_json)
        print(f"Sent: {response_json}")

    async def process_heartbeat(self, websocket, message_id):
        print("Received Heartbeat")
        response_payload = {
            "currentTime": datetime.utcnow().isoformat() + "Z"  # Current time in ISO 8601 format
        }
        response = [3, message_id, response_payload]
        response_json = json.dumps(response)
        await websocket.send(response_json)
        print(f"Sent: {response_json}")

    async def handle_connection(self, websocket, path):
        async for message in websocket:
            message = json.loads(message)
            await self.process_message(websocket, message)

    async def start_server(self):
        server = await websockets.serve(self.handle_connection, self.host, self.port)
        print(f"Server started at ws://{self.host}:{self.port}")
        await server.wait_closed()


if __name__ == "__main__":
    central_system = CentralSystem(host="localhost", port=9000)
    asyncio.run(central_system.start_server())
