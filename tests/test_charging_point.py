import pytest
import json
from unittest.mock import AsyncMock
from mini_ocpp.charger_point import ChargingPoint


@pytest.fixture
def charging_point():
    return ChargingPoint("ws://localhost:9000", "TestModel", "TestVendor", "12345")


def describe_charging_point():

    def describe_send_boot_notification():

        @pytest.mark.asyncio
        async def with_valid_websocket(charging_point):
            mock_websocket = AsyncMock()
            await charging_point.send_boot_notification(mock_websocket)
            assert mock_websocket.send.call_count == 1
            sent_message = json.loads(mock_websocket.send.call_args[0][0])
            assert sent_message[2] == "BootNotification"

    def describe_send_heartbeat():

        @pytest.mark.asyncio
        async def with_valid_websocket(charging_point):
            mock_websocket = AsyncMock()
            await charging_point.send_heartbeat(mock_websocket)
            assert mock_websocket.send.call_count == 1
            sent_message = json.loads(mock_websocket.send.call_args[0][0])
            assert sent_message[2] == "Heartbeat"

    def describe_process_boot_notification():

        def with_valid_payload(charging_point):
            payload = {"interval": 45}
            charging_point.process_boot_notification(payload)
            assert charging_point.config["HeartbeatInterval"] == 45

    def describe_process_change_configuration():

        def accepts_valid_configuration(charging_point):
            message_id = "test_message_id"
            payload = {"key": "HeartbeatInterval", "value": "60"}
            response = charging_point.process_change_configuration(message_id, payload)
            assert charging_point.config["HeartbeatInterval"] == 60
            assert response[2]["status"] == "Accepted"

        def rejects_invalid_configuration(charging_point):
            message_id = "test_message_id"
            payload = {"key": "InvalidKey", "value": 60}
            response = charging_point.process_change_configuration(message_id, payload)
            assert response[2]["status"] == "Rejected"

    def describe_handle_message():

        def with_call_message(charging_point):
            message = [2, "123", "GetConfiguration", {"key": ["NoHeartbeatInterval"]}]
            response = charging_point.handle_message(message)
            assert (
                '{"configurationKey": [], "unknownKey": ["NoHeartbeatInterval"]}]'
                in response
            )

        def with_call_result_message(charging_point):
            charging_point._ChargingPoint__sent_calls["123"] = "BootNotification"
            message = [3, "123", {"interval": 60}]
            charging_point.handle_message(message)
            assert charging_point.config["HeartbeatInterval"] == 60
