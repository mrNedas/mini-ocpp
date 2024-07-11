import asyncio
import json
import websockets
from datetime import datetime


class CentralSystem:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.connected_charging_points = {}  # Store connected charging points

    async def process_message(self, websocket, message):
        try:
            message_id = message[1]
            action = message[2]
            payload = message[3]

            if action == "BootNotification":
                await self.process_boot_notification(websocket, message_id, payload)
            elif action == "Heartbeat":
                await self.process_heartbeat(websocket, message_id)
            elif action == "ChangeConfiguration":
                await self.process_change_configuration(websocket, message_id, payload)
            else:
                print(f"Received unsupported action: {action}")
        except Exception as e:
            print(f"Error processing message: {e}")

    async def process_boot_notification(self, websocket, message_id, payload):
        print(f"Received BootNotification with payload: {payload}")
        charge_point_id = payload.get("chargePointSerialNumber")
        if charge_point_id:
            self.connected_charging_points[charge_point_id] = websocket
            print(f"Charging point {charge_point_id} connected.")

        response_payload = {
            "status": "Accepted",
            "currentTime": datetime.utcnow().isoformat()
            + "Z",  # Current time in ISO 8601 format
            "interval": 5,
        }
        response = [3, message_id, response_payload]
        response_json = json.dumps(response)
        await websocket.send(response_json)
        print(f"Sent: {response_json}")

    async def process_heartbeat(self, websocket, message_id):
        print("Received Heartbeat")
        response_payload = {
            "currentTime": datetime.utcnow().isoformat()
            + "Z"  # Current time in ISO 8601 format
        }
        response = [3, message_id, response_payload]
        response_json = json.dumps(response)
        await websocket.send(response_json)
        print(f"Sent: {response_json}")

    async def process_change_configuration(self, websocket, message_id, payload):
        print(f"Processing ChangeConfiguration with payload: {payload}")

    async def handle_connection(self, websocket, path):
        try:
            async for message in websocket:
                message = json.loads(message)
                await self.process_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            for charge_point_id, ws in self.connected_charging_points.items():
                if ws == websocket:
                    print(f"Charging point {charge_point_id} disconnected.")
                    del self.connected_charging_points[charge_point_id]
                    break

    async def start_server(self):
        server = await websockets.serve(self.handle_connection, self.host, self.port)
        print(f"Server started at ws://{self.host}:{self.port}")
        await server.wait_closed()

    async def send_change_configuration(self, charge_point_id, key, value):
        if charge_point_id in self.connected_charging_points:
            websocket = self.connected_charging_points[charge_point_id]
            message_id = "3"
            action = "ChangeConfiguration"
            payload = {"key": key, "value": value}
            request = [2, message_id, action, payload]
            request_json = json.dumps(request)

            await websocket.send(request_json)
            print(f"Sent to {charge_point_id}: {request_json}")

            response = await websocket.recv()
            print(f"Received from {charge_point_id}: {response}")
        else:
            print(f"Charging point {charge_point_id} not connected")


if __name__ == "__main__":
    central_system = CentralSystem(host="localhost", port=9000)
    asyncio.run(central_system.start_server())
