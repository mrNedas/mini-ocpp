import asyncio
import json
import websockets


class CentralSystem:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    async def process_message(self, websocket, message):
        try:
            message_id = message[1]
            action = message[2]
            payload = message[3]

            print(f"Received BootNotification with payload: {payload}")

            if action == "BootNotification":
                response_payload = {
                    "status": "Accepted",
                    "currentTime": "2024-07-09T12:00:00Z",  # TODO: set dynamically
                    "interval": 300,  # TODO: set dynamically
                }
                response = [3, message_id, response_payload]
                response_json = json.dumps(response)
                await websocket.send(response_json)
                print(f"Sent: {response_json}")
            else:
                print("Received unsupported action")
        except Exception as e:
            print(f"Error processing message: {e}")

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
