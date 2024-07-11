import asyncio
import json
import websockets


class ChargingPoint:
    def __init__(self, uri, model, vendor):
        self.uri = uri
        self.model = model
        self.vendor = vendor

    def boot_notification_payload(self):
        return {"chargePointModel": self.model, "chargePointVendor": self.vendor}

    async def send_boot_notification(self):
        async with websockets.connect(self.uri) as websocket:
            # BootNotification message format as per OCPP 1.6
            message_id = "1"  # identifier for this message
            action = "BootNotification"
            payload = self.boot_notification_payload()
            request = [2, message_id, action, payload]

            request_json = json.dumps(request)

            await websocket.send(request_json)
            print(f"Sent: {request_json}")

            response = await websocket.recv()
            print(f"Received: {response}")


if __name__ == "__main__":
    uri = "ws://localhost:9000"
    model = "BestModel"
    vendor = "BestVendor"

    charging_point = ChargingPoint(uri=uri, model=model, vendor=vendor)
    asyncio.run(charging_point.send_boot_notification())
