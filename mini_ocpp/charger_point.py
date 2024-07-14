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
        # TODO: update local clock

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
        if key in self.config:
            self.config[key] = value
            print(f"Changed configuration: {key} = {value}")
            response_payload = {"status": "Accepted"}
        else:
            response_payload = {"status": "Rejected"}

        response = [MessageType.CALL_RESULT.value, message_id, response_payload]
        return response

    def process_call_message(self, message):
        message_id = message[1]
        action = message[2]
        payload = message[3]

        if action == "GetConfiguration":
            response = self.process_get_configuration(message_id)
        elif action == "ChangeConfiguration":
            response = self.process_change_configuration(message_id, payload)
        else:
            print(f"Received unsupported action: {action}")

        return json.dumps(response)

    def process_call_result_message(self, message):
        message_id = message[1]
        if self.__sent_calls[message_id]:
            action = self.__sent_calls[message_id]
            payload = message[2]
            del self.__sent_calls[message_id]
        else:
            print("No call message was sent for this message.")
            return

        if action == "BootNotification":
            self.process_boot_notification(payload)
        elif action == "Heartbeat":
            self.process_heartbeat(payload)

    def handle_message(self, message):
        print(f"Received: {message}")

        message_type = message[0]
        if message_type == MessageType.CALL.value:
            return self.process_call_message(message)
        elif message_type == MessageType.CALL_RESULT.value:
            self.process_call_result_message(message)

    async def listen_for_messages(self, websocket):
        try:
            while True:
                message = await websocket.recv()
                message = json.loads(message)
                response = self.handle_message(message)
                if response:
                    await websocket.send(response)
                    print(f"Sent: {response}")
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed.")

    async def heartbeat_task(self, websocket):
        while True:
            await self.send_heartbeat(websocket)
            total_sleep_time = 0
            while total_sleep_time < self.config["HeartbeatInterval"]:
                await asyncio.sleep(1)
                total_sleep_time += 1

    async def run(self):
        async with websockets.connect(self.uri) as websocket:
            listen_task = asyncio.create_task(self.listen_for_messages(websocket))
            heartbeat_task = asyncio.create_task(self.heartbeat_task(websocket))

            await self.send_boot_notification(websocket)
            await asyncio.gather(listen_task, heartbeat_task)


if __name__ == "__main__":
    uri = "ws://localhost:9000"
    model = "BestModel"
    vendor = "BestVendor"
    serial_number = "100"

    charging_point = ChargingPoint(
        uri=uri, model=model, vendor=vendor, serial_number=serial_number
    )
    asyncio.run(charging_point.run())
