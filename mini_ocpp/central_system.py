import asyncio
import json
import websockets
import uuid
from datetime import datetime
from quart import Quart, jsonify, request
from message_types import MessageType


class CentralSystem:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.connected_charging_points = {}  # Store connected charging points
        self.pending_requests = {}

    async def process_message(self, websocket, message):
        try:
            message_type = message[0]
            message_id = message[1]
            if message_type == MessageType.CALL_RESULT.value:
                payload = message[2]
            elif message_type == MessageType.CALL.value:
                action = message[2]
                payload = message[3]

            if message_type == MessageType.CALL_RESULT.value:
                if message_id in self.pending_requests:
                    future = self.pending_requests.pop(message_id)
                    future.set_result(payload)
                    return

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
            "currentTime": datetime.utcnow().isoformat() + "Z",
            "interval": 300,
        }
        response = [3, message_id, response_payload]
        response_json = json.dumps(response)
        await websocket.send(response_json)
        print(f"Sent: {response_json}")

    async def process_heartbeat(self, websocket, message_id):
        print("Received Heartbeat")
        response_payload = {"currentTime": datetime.utcnow().isoformat() + "Z"}
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

    async def send_get_configuration(self, charge_point_id):
        if charge_point_id in self.connected_charging_points:
            websocket = self.connected_charging_points[charge_point_id]
            message_id = str(uuid.uuid4())
            action = "GetConfiguration"
            request = [MessageType.CALL.value, message_id, action, {}]
            request_json = json.dumps(request)

            await websocket.send(request_json)
            print(f"Sent to {charge_point_id}: {request_json}")

            future = asyncio.get_event_loop().create_future()
            self.pending_requests[message_id] = future
            response = await future
            return response
        else:
            print(f"Charging point {charge_point_id} not connected")
            return jsonify({"error": "Charging point not connected"}), 404

    async def send_change_configuration(self, charge_point_id, key, value):
        if charge_point_id in self.connected_charging_points:
            websocket = self.connected_charging_points[charge_point_id]
            message_id = str(uuid.uuid4())
            action = "ChangeConfiguration"
            payload = {"key": key, "value": value}
            request = [MessageType.CALL.value, message_id, action, payload]
            request_json = json.dumps(request)

            await websocket.send(request_json)
            print(f"Sent to {charge_point_id}: {request_json}")

            future = asyncio.get_event_loop().create_future()
            self.pending_requests[message_id] = future
            response = await future
            return response
        else:
            print(f"Charging point {charge_point_id} not connected")
            return jsonify({"error": "Charging point not connected"}), 404

    async def run(self):
        app = Quart(__name__)

        @app.route("/charging_points/<charge_point_id>/configuration", methods=["GET"])
        async def get_charging_point_configuration(charge_point_id):
            return await self.send_get_configuration(charge_point_id)

        @app.route("/charging_points/<charge_point_id>/configuration", methods=["POST"])
        async def change_charging_point_configuration(charge_point_id):
            data = await request.get_json()
            key = data.get("key")
            value = data.get("value")
            return await self.send_change_configuration(charge_point_id, key, value)

        server_task = asyncio.create_task(app.run_task(host=self.host, port=3000))
        print(f"HTTP REST API started at http://{self.host}:{self.port}")

        async with websockets.serve(self.handle_connection, self.host, self.port):
            await server_task


if __name__ == "__main__":
    central_system = CentralSystem(host="localhost", port=9000)
    asyncio.run(central_system.run())
