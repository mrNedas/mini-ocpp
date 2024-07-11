import asyncio
import json
import websockets


class ChargingPoint:
    def __init__(self, uri, model, vendor):
        self.uri = uri
        self.model = model
        self.vendor = vendor
        self.config = {"HeartbeatInterval": 5}

    def form_boot_notification_payload(self):
        return {"chargePointModel": self.model, "chargePointVendor": self.vendor}

    def process_boot_notification_payload(self, response):
        response_message = json.loads(response)
        if response_message[2].get("interval"):
            self.config["HeartbeatInterval"] = response_message[2]["interval"]
            print(
                f"Heartbeat interval set to: {self.config['HeartbeatInterval']} seconds"
            )

    async def send_boot_notification(self, websocket):
        # BootNotification message format as per OCPP 1.6
        message_id = "1"
        action = "BootNotification"
        payload = self.form_boot_notification_payload()
        request = [2, message_id, action, payload]

        request_json = json.dumps(request)

        await websocket.send(request_json)
        print(f"Sent: {request_json}")

        response = await websocket.recv()
        print(f"Received: {response}")
        self.process_boot_notification_payload(response)

    async def send_heartbeat(self, websocket):
        message_id = "2"
        action = "Heartbeat"
        request = [2, message_id, action, {}]
        request_json = json.dumps(request)

        await websocket.send(request_json)
        print(f"Sent: {request_json}")

        response = await websocket.recv()
        print(f"Received: {response}")

    async def process_change_configuration(self, message_id, payload):
        print(f"Processing ChangeConfiguration with payload: {payload}")
        key = payload["key"]
        value = payload["value"]
        print(f"Changing configuration: {key} = {value}")
        response_payload = {"status": "Accepted"}
        response = [3, message_id, response_payload]
        return response

    async def handle_incoming_message(self, websocket, message):
        message_id = message[1]
        action = message[2]
        payload = message[3]

        if action == "ChangeConfiguration":
            response = await self.process_change_configuration(message_id, payload)
            response_json = json.dumps(response)
            await websocket.send(response_json)
            print(f"Sent: {response_json}")

    async def listen_for_messages(self, websocket):
        async for message in websocket:
            message = json.loads(message)
            await self.handle_message(websocket, message)

    async def run(self):
        async with websockets.connect(self.uri) as websocket:
            await self.send_boot_notification(websocket)

            # For listening to incoming messages
            listen_task = asyncio.create_task(self.listen_for_messages(websocket))

            while True:
                await self.send_heartbeat(websocket)
                await asyncio.sleep(self.config["HeartbeatInterval"])
                await asyncio.wait([listen_task], timeout=0)


if __name__ == "__main__":
    uri = "ws://localhost:9000"
    model = "BestModel"
    vendor = "BestVendor"

    charging_point = ChargingPoint(uri=uri, model=model, vendor=vendor)
    asyncio.run(charging_point.run())
