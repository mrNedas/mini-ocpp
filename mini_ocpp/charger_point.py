import asyncio
import json
import websockets
import uuid
from message_types import MessageType


class ChargingPoint:
    def __init__(self, uri, model, vendor, serial_number):
        self.uri = uri
        self.model = model
        self.vendor = vendor
        self.serial_number = serial_number
        self.config = {"HeartbeatInterval": 30}
        self.__sent_calls = {}

    def form_boot_notification_payload(self):
        return {
            "chargePointModel": self.model,
            "chargePointVendor": self.vendor,
            "chargePointSerialNumber": self.serial_number,
        }

    def process_boot_notification(self, payload):
        self.config["HeartbeatInterval"] = payload["interval"]
        print(f"Heartbeat interval set to: {self.config['HeartbeatInterval']} seconds")

    def process_heartbeat(self, response):
        print("Process heartbeat")

    async def send_boot_notification(self, websocket):
        message_id = str(uuid.uuid4())
        action = "BootNotification"
        payload = self.form_boot_notification_payload()
        request = [MessageType.CALL.value, message_id, action, payload]

        request_json = json.dumps(request)

        await websocket.send(request_json)
        print(f"Sent: {request_json}")
        self.__sent_calls[message_id] = action

    async def send_heartbeat(self, websocket):
        message_id = str(uuid.uuid4())
        action = "Heartbeat"
        request = [MessageType.CALL.value, message_id, action, {}]
        request_json = json.dumps(request)

        await websocket.send(request_json)
        print(f"Sent: {request_json}")
        self.__sent_calls[message_id] = action

    def process_get_configuration(self, message_id):
        print("Processing GetConfiguration request")
        payload = {"configuration": self.config}
        response = [MessageType.CALL_RESULT.value, message_id, payload]
        return response

    def process_change_configuration(self, message_id, payload):
        print(f"Processing ChangeConfiguration with payload: {payload}")
        key = payload["key"]
        value = payload["value"]
        self.config[key] = value
        print(f"Changed configuration: {key} = {value}")
        response_payload = {"status": "Accepted"}
        response = [MessageType.CALL_RESULT.value, message_id, response_payload]
        return response

    def handle_message(self, websocket, message):
        print(f"Received: {message}")

        message_type = message[0]
        message_id = message[1]
        if message_type == MessageType.CALL_RESULT.value:
            if self.__sent_calls[message_id]:
                action = self.__sent_calls[message_id]
                payload = message[2]
                del self.__sent_calls[message_id]
            else:
                print("No call message was sent for this message.")
        elif message_type == MessageType.CALL.value:
            action = message[2]
            payload = message[3]

        if action == "BootNotification":
            response = self.process_boot_notification(payload)
        elif action == "GetConfiguration":
            response = self.process_get_configuration(message_id)
        elif action == "Heartbeat":
            response = self.process_heartbeat(payload)
        elif action == "ChangeConfiguration":
            response = self.process_change_configuration(message_id, payload)
        else:
            print(f"Received unsupported action: {action}")

        if message_type == MessageType.CALL.value:
            return json.dumps(response)

    async def listen_for_messages(self, websocket):
        try:
            while True:
                message = await websocket.recv()
                message = json.loads(message)
                response = self.handle_message(websocket, message)
                if response:
                    await websocket.send(response)
                    print(f"Sent: {response}")
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed.")

    async def run(self):
        async with websockets.connect(self.uri) as websocket:
            # For listening to incoming messages
            asyncio.create_task(self.listen_for_messages(websocket))
            await self.send_boot_notification(websocket)
            while True:
                await self.send_heartbeat(websocket)
                await asyncio.sleep(self.config["HeartbeatInterval"])


if __name__ == "__main__":
    uri = "ws://localhost:9000"
    model = "BestModel"
    vendor = "BestVendor"
    serial_number = "100"

    charging_point = ChargingPoint(
        uri=uri, model=model, vendor=vendor, serial_number=serial_number
    )
    asyncio.run(charging_point.run())
