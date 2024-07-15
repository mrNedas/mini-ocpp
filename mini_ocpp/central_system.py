import asyncio
import json
import websockets
import logging
import uuid
from datetime import datetime
from quart import Quart, jsonify, request
from .message_types import MessageType


class CentralSystem:
    def __init__(self, host, ws_port, http_port):
        self.host = host
        self.ws_port = ws_port
        self.http_port = http_port
        self.connected_charging_points = {}  # Store connected charging points
        self.pending_requests = {}

    async def process_call_message(self, websocket, message):
        message_id = message[1]
        action = message[2]
        payload = message[3]
        if action == "BootNotification":
            await self.process_boot_notification(websocket, message_id, payload)
        elif action == "Heartbeat":
            await self.process_heartbeat(websocket, message_id)
        else:
            logging.warning(f"Received unsupported action: {action}")

    def process_call_result_message(self, message):
        message_id = message[1]
        payload = message[2]
        if message_id in self.pending_requests:
            future = self.pending_requests.pop(message_id)
            future.set_result(payload)

    async def process_message(self, websocket, message):
        try:
            message_type = message[0]
            if message_type == MessageType.CALL.value:
                return await self.process_call_message(websocket, message)
            elif message_type == MessageType.CALL_RESULT.value:
                return self.process_call_result_message(message)
        except Exception as e:
            logging.error(f"Error processing message: {e}")

    async def process_boot_notification(self, websocket, message_id, payload):
        logging.info(f"Received BootNotification with payload: {payload}")
        charge_point_id = payload.get("chargePointSerialNumber")
        if charge_point_id:
            self.connected_charging_points[charge_point_id] = websocket
            logging.info(f"Charging point {charge_point_id} connected.")

        response_payload = {
            "status": "Accepted",
            "currentTime": datetime.utcnow().isoformat() + "Z",
            "interval": 300,
        }
        response = [3, message_id, response_payload]
        response_json = json.dumps(response)
        await websocket.send(response_json)
        logging.debug(f"Sent: {response_json}")

    async def process_heartbeat(self, websocket, message_id):
        logging.info("Received Heartbeat")
        response_payload = {"currentTime": datetime.utcnow().isoformat() + "Z"}
        response = [3, message_id, response_payload]
        response_json = json.dumps(response)
        await websocket.send(response_json)
        logging.debug(f"Sent: {response_json}")

    async def handle_connection(self, websocket):
        try:
            async for message in websocket:
                message = json.loads(message)
                await self.process_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            for charge_point_id, ws in self.connected_charging_points.items():
                if ws == websocket:
                    logging.info(f"Charging point {charge_point_id} disconnected.")
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
            logging.debug(f"Sent to {charge_point_id}: {request_json}")

            future = asyncio.get_event_loop().create_future()
            self.pending_requests[message_id] = future
            response = await future
            return response
        else:
            logging.error(f"Charging point {charge_point_id} not connected")
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
            logging.debug(f"Sent to {charge_point_id}: {request_json}")

            future = asyncio.get_event_loop().create_future()
            self.pending_requests[message_id] = future
            response = await future
            return response
        else:
            logging.error(f"Charging point {charge_point_id} not connected")
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

        server_task = asyncio.create_task(
            app.run_task(host=self.host, port=self.http_port)
        )
        logging.info(f"HTTP REST API started at http://{self.host}:{self.http_port}")

        async with websockets.serve(self.handle_connection, self.host, self.ws_port):
            await server_task
