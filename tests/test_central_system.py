import pytest
import asyncio
import json
import uuid
from unittest.mock import AsyncMock, patch
from datetime import datetime
from mini_ocpp.central_system import CentralSystem
from mini_ocpp.message_types import MessageType


@pytest.fixture
def central_system():
    return CentralSystem("localhost", 9000, 8080)


def describe_central_system():

    def describe_boot_notification():

        @pytest.mark.asyncio
        async def it_registers_charging_point(central_system):
            mock_websocket = AsyncMock()
            message_id = str(uuid.uuid4())
            payload = {
                "chargePointModel": "TestModel",
                "chargePointVendor": "TestVendor",
                "chargePointSerialNumber": "12345",
            }
            message = [MessageType.CALL.value, message_id, "BootNotification", payload]

            await central_system.process_call_message(mock_websocket, message)
            assert "12345" in central_system.connected_charging_points

    def describe_heartbeat():

        @pytest.mark.asyncio
        async def it_sends_current_time_on_heartbeat(central_system):
            mock_websocket = AsyncMock()
            message_id = str(uuid.uuid4())
            message = [MessageType.CALL.value, message_id, "Heartbeat", {}]

            await central_system.process_call_message(mock_websocket, message)
            mock_websocket.send.assert_called_once()
            response = json.loads(mock_websocket.send.call_args[0][0])
            assert response[2]["currentTime"]
