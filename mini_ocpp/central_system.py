import asyncio
import json
import websockets
import logging
import uuid
from datetime import datetime, timezone
from quart import Quart, jsonify, request
from .message_types import MessageType
from .message_validator import MessageValidator


class CentralSystem:
    """
    Represents a central system managing communication with multiple EV charging points.

    Attributes:
        host (str): The host address of the central system.
        ws_port (int): The WebSocket port for communication with charging points.
        http_port (int): The HTTP port for REST API interactions.
        connected_charging_points (dict): Dictionary to store connected charging points.
        pending_requests (dict): Dictionary to store pending requests and their futures.
    """

    def __init__(self, host, ws_port, http_port):
        """
        Initializes a CentralSystem instance.

        Args:
            host (str): The host address of the central system.
            ws_port (int): The WebSocket port for communication with charging points.
            http_port (int): The HTTP port for REST API interactions.
        """
        self.host = host
        self.ws_port = ws_port
        self.http_port = http_port
        self.connected_charging_points = {}  # Store connected charging points
        self.pending_requests = {}
        self.default_heartbeat_interval = 20
        self.__validator = MessageValidator(schema_dir="./schemas/json")

    async def process_call_message(self, websocket, message):
        """
        Processes incoming Call messages from charging points.

        Args:
            websocket: The WebSocket connection object.
            message (list): The incoming message from a charging point.
        """
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
        """
        Processes incoming CallResult messages from charging points.

        Args:
            message (list): The incoming CallResult message from a charging point.
        """
        message_id = message[1]
        payload = message[2]
        if message_id in self.pending_requests:
            future = self.pending_requests.pop(message_id)
            future.set_result(payload)

    async def process_message(self, websocket, message):
        """
        Processes incoming messages based on their type (Call or CallResult).

        Args:
            websocket: The WebSocket connection object.
            message (list): The incoming message from a charging point.
        """
        try:
            message_type = message[0]
            if message_type == MessageType.CALL.value:
                return await self.process_call_message(websocket, message)
            elif (
                message_type == MessageType.CALL_RESULT.value
                or message_type == MessageType.CALL_ERROR.value
            ):
                return self.process_call_result_message(message)
        except Exception as e:
            logging.error(f"Error processing message: {e}")

    async def process_boot_notification(self, websocket, message_id, payload):
        """
        Processes BootNotification message from a charging point.

        Args:
            websocket: The WebSocket connection object.
            message_id (str): The ID of the BootNotification message.
            payload (dict): The payload of the BootNotification message.
        """
        logging.info(f"Received BootNotification with payload: {payload}")
        is_valid = self.__validator.validate_message("BootNotification", payload)

        if is_valid:
            charge_point_id = payload.get("chargePointSerialNumber")
            if charge_point_id:
                self.connected_charging_points[charge_point_id] = websocket
                logging.info(f"Charging point {charge_point_id} connected.")
            message_type = MessageType.CALL_RESULT.value
            status = "Accepted"
        else:
            logging.error(f"Invalid BootNotification received from {charge_point_id}.")
            message_type = MessageType.CALL_RESULT.value
            status = "Accepted"

        response_payload = {
            "status": status,
            "currentTime": datetime.now(timezone.utc).isoformat(),
            "interval": self.default_heartbeat_interval,
        }
        response = [message_type, message_id, response_payload]
        response_json = json.dumps(response)
        await websocket.send(response_json)
        logging.debug(f"Sent: {response_json}")

    async def process_heartbeat(self, websocket, message_id):
        """
        Processes Heartbeat message from a charging point.

        Args:
            websocket: The WebSocket connection object.
            message_id (str): The ID of the Heartbeat message.
        """
        logging.info("Received Heartbeat")
        response_payload = {"currentTime": datetime.now(timezone.utc).isoformat()}
        response = [MessageType.CALL_RESULT.value, message_id, response_payload]
        response_json = json.dumps(response)
        await websocket.send(response_json)
        logging.debug(f"Sent: {response_json}")

    async def handle_connection(self, websocket):
        """
        Handles WebSocket connections from charging points.

        Args:
            websocket: The WebSocket connection object.
        """
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

    async def send_get_configuration(self, charge_point_id, payload):
        """
        Sends GetConfiguration request to a charging point and awaits response.

        Args:
            charge_point_id (str): The ID of the charging point.
            payload (dict): The payload of the GetConfiguration message.

        Returns:
            dict: The response payload from the charging point.
        """
        if charge_point_id in self.connected_charging_points:
            websocket = self.connected_charging_points[charge_point_id]
            message_id = str(uuid.uuid4())
            action = "GetConfiguration"
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

    async def send_change_configuration(self, charge_point_id, payload):
        """
        Sends ChangeConfiguration request to a charging point and awaits response.

        Args:
            charge_point_id (str): The ID of the charging point.
            key (str): The configuration key to change.
            payload (any): The new value for the configuration key.

        Returns:
            dict: The response payload from the charging point.
        """
        if charge_point_id in self.connected_charging_points:
            websocket = self.connected_charging_points[charge_point_id]
            message_id = str(uuid.uuid4())
            action = "ChangeConfiguration"
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
        """
        Runs the CentralSystem, starting WebSocket server and HTTP REST API.
        """
        app = Quart(__name__)

        @app.route("/charging_points/<charge_point_id>/configuration", methods=["GET"])
        async def get_charging_point_configuration(charge_point_id):
            data = await request.get_json()
            valid_body = self.__validator.validate_message("GetConfiguration", data)
            if valid_body:
                return await self.send_get_configuration(charge_point_id, data)
            else:
                return jsonify({"error": "Invalid body"}), 400

        @app.route("/charging_points/<charge_point_id>/configuration", methods=["POST"])
        async def change_charging_point_configuration(charge_point_id):
            data = await request.get_json()
            valid_body = self.__validator.validate_message("ChangeConfiguration", data)
            if valid_body:
                return await self.send_change_configuration(charge_point_id, data)
            else:
                return jsonify({"error": "Invalid body"}), 400

        server_task = asyncio.create_task(
            app.run_task(host=self.host, port=self.http_port)
        )
        logging.info(f"HTTP REST API started at http://{self.host}:{self.http_port}")

        async with websockets.serve(self.handle_connection, self.host, self.ws_port):
            await server_task
