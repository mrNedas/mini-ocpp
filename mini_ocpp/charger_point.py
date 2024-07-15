import asyncio
import json
import websockets
import logging
import uuid
from .message_types import MessageType
from .message_validator import MessageValidator


class ChargingPoint:
    """
    Represents an EV Charging Point, handling communication and configuration with the Central System.

    Attributes:
        uri (str): The WebSocket URI of the central system.
        model (str): The model of the charging point.
        vendor (str): The vendor of the charging point.
        serial_number (str): The serial number of the charging point.
        config (dict): The configuration of the charging point.
        __sent_calls (dict): A dictionary to keep track of sent calls and their IDs.
    """

    def __init__(self, uri, model, vendor, serial_number):
        """
        Initialize a ChargingPoint instance.

        Args:
            uri (str): The WebSocket URI of the central system.
            model (str): The model of the charging point.
            vendor (str): The vendor of the charging point.
            serial_number (str): The serial number of the charging point.
        """
        self.uri = uri
        self.model = model
        self.vendor = vendor
        self.serial_number = serial_number
        self.config = {"HeartbeatInterval": 30}
        self.__sent_calls = {}
        self.__validator = MessageValidator(schema_dir="./schemas/json")

    def form_boot_notification_payload(self):
        """
        Forms the payload for the BootNotification message.

        Returns:
            dict: The payload dictionary containing charge point model, vendor, and serial number.
        """
        return {
            "chargePointModel": self.model,
            "chargePointVendor": self.vendor,
            "chargePointSerialNumber": self.serial_number,
        }

    def process_boot_notification(self, payload):
        """
        Processes the BootNotification response and updates the configuration.

        Args:
            payload (dict): The payload received in the BootNotification response.
        """
        self.config["HeartbeatInterval"] = payload["interval"]
        logging.info(
            f"Heartbeat interval set to: {self.config['HeartbeatInterval']} seconds"
        )

    def process_heartbeat(self, payload):
        """
        Processes the Heartbeat message.

        Args:
            payload (dict): The payload received in the Heartbeat message.
        """
        logging.info("Process heartbeat")
        # TODO: update CP's local clock

    async def send_boot_notification(self, websocket):
        """
        Sends the BootNotification message to the central system.

        Args:
            websocket: The WebSocket connection object.
        """
        message_id = str(uuid.uuid4())
        action = "BootNotification"
        payload = self.form_boot_notification_payload()
        request = [MessageType.CALL.value, message_id, action, payload]
        request_json = json.dumps(request)

        await websocket.send(request_json)
        logging.debug(f"Sent: {request_json}")
        self.__sent_calls[message_id] = action

    async def send_heartbeat(self, websocket):
        """
        Sends the Heartbeat message to the central system.

        Args:
            websocket: The WebSocket connection object.
        """
        message_id = str(uuid.uuid4())
        action = "Heartbeat"
        request = [MessageType.CALL.value, message_id, action, {}]
        request_json = json.dumps(request)

        await websocket.send(request_json)
        logging.debug(f"Sent: {request_json}")
        self.__sent_calls[message_id] = action

    def process_get_configuration(self, message_id, payload):
        """
        Processes the GetConfiguration request and returns the current configuration.

        Args:
            message_id (str): The ID of the incoming message.

        Returns:
            list: The CallResult message containing the current configuration.
        """
        logging.info("Processing GetConfiguration request")
        is_valid = self.__validator.validate_message("GetConfiguration", payload)
        if is_valid:
            requested_config = []
            unknown_keys = []
            for key in payload.get("key"):
                if key in self.config:
                    requested_config.append(
                        {
                            "key": key,
                            "readonly": False,
                            "value": self.config[key],
                        }
                    )
                else:
                    unknown_keys.append(key)

            message_type = MessageType.CALL_RESULT.value
            response_payload = {
                "configurationKey": requested_config,
                "unknownKey": unknown_keys,
            }
        else:
            logging.error(f"Validation error: invalid GetConfiguration payload")
            message_type = MessageType.CALL_ERROR.value
            response_payload = {"status": "Rejected"}

        response = [message_type, message_id, response_payload]
        return response

    def process_change_configuration(self, message_id, payload):
        """
        Processes the ChangeConfiguration request and updates the configuration.

        Args:
            message_id (str): The ID of the incoming message.
            payload (dict): The payload containing the configuration change request.

        Returns:
            list: The CallResult message indicating whether the configuration change was accepted.
        """
        logging.info(f"Processing ChangeConfiguration with payload: {payload}")
        is_valid = self.__validator.validate_message("ChangeConfiguration", payload)
        key = payload["key"]
        if key in self.config and is_valid:
            value = payload["value"]
            self.config[key] = int(value)
            logging.info(f"Changed configuration: {key} = {value}")
            message_type = MessageType.CALL_RESULT.value
            response_payload = {"status": "Accepted"}
        else:
            logging.error(f"Rejected configuration change: unknown key {key}")
            message_type = MessageType.CALL_ERROR.value
            response_payload = {"status": "Rejected"}

        response = [message_type, message_id, response_payload]
        return response

    def process_call_message(self, message):
        """
        Processes a Call message and invokes corresponding handlers.

        Args:
            message (list): The incoming Call message.

        Returns:
            str: JSON-encoded string of the CallResult message, if any.
        """
        message_id = message[1]
        action = message[2]
        payload = message[3]

        if action == "GetConfiguration":
            response = self.process_get_configuration(message_id, payload)
        elif action == "ChangeConfiguration":
            response = self.process_change_configuration(message_id, payload)
        else:
            logging.warning(f"Received unsupported action: {action}")

        return json.dumps(response)

    def process_call_result_message(self, message):
        """
        Processes a CallResult message and invokes corresponding handlers.

        Args:
            message (list): The incoming CallResult message.
        """
        message_id = message[1]
        if self.__sent_calls[message_id]:
            action = self.__sent_calls[message_id]
            payload = message[2]
            del self.__sent_calls[message_id]
        else:
            logging.warning("No call message was sent for this message.")
            return

        if action == "BootNotification":
            self.process_boot_notification(payload)
        elif action == "Heartbeat":
            self.process_heartbeat(payload)

    def handle_message(self, message):
        """
        Handles incoming messages based on their type (Call or CallResult).

        Args:
            message (list): The incoming message.

        Returns:
            str: JSON-encoded string of the CallResult message, if any.
        """
        logging.info(f"Received: {message}")

        message_type = message[0]
        if message_type == MessageType.CALL.value:
            return self.process_call_message(message)
        elif message_type == MessageType.CALL_RESULT.value:
            self.process_call_result_message(message)
        else:
            logging.error(f"Received call error: {message}")

    async def listen_for_messages(self, websocket):
        """
        Listens for incoming messages from the central system.

        Args:
            websocket: The WebSocket connection object.
        """
        try:
            while True:
                message = await websocket.recv()
                message = json.loads(message)
                response = self.handle_message(message)
                if response:
                    await websocket.send(response)
                    logging.debug(f"Sent: {response}")
        except websockets.exceptions.ConnectionClosed:
            logging.info("WebSocket connection closed.")

    async def heartbeat_task(self, websocket):
        """
        Sends periodic Heartbeat messages to the central system.

        Args:
            websocket: The WebSocket connection object.
        """
        while True:
            await self.send_heartbeat(websocket)
            total_sleep_time = 0
            while total_sleep_time < self.config["HeartbeatInterval"]:
                await asyncio.sleep(1)
                total_sleep_time += 1

    async def run(self):
        """
        Runs the ChargingPoint, establishing connection, sending BootNotification,
        and managing message exchange with the central system.
        """
        async with websockets.connect(self.uri) as websocket:
            listen_task = asyncio.create_task(self.listen_for_messages(websocket))
            heartbeat_task = asyncio.create_task(self.heartbeat_task(websocket))

            await self.send_boot_notification(websocket)
            await asyncio.gather(listen_task, heartbeat_task)
