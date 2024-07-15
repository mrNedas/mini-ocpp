### Notes

#### Data Structures

##### `self.__sent_calls`

- **Class**: `ChargingPoint`
  
- **Purpose**: 
  - This dictionary (`self.__sent_calls`) is used to keep track of messages (actions) sent to charging points along with their unique message IDs.
  
- **Usage**:
  - When a message (like BootNotification or Heartbeat) is sent from the `ChargingPoint` to the `CentralSystem`, its ID and action are stored in `self.__sent_calls`.
  - This allows the `ChargingPoint` to correlate incoming `CallResult` messages with the original `Call` messages it sent, enabling proper handling of responses and acknowledgments.

##### `self.connected_charging_points`

- **Class**: `CentralSystem`
  
- **Purpose**: 
  - This dictionary (`self.connected_charging_points`) serves as a registry or store for all currently connected ChargingPoints to the `CentralSystem`.
  
- **Usage**:
  - Each entry in this dictionary represents a unique ChargingPoint identified by its serial number or another identifier.
  - When a ChargingPoint establishes a WebSocket connection with the `CentralSystem` (via BootNotification), it is added to this dictionary.

##### `self.pending_requests`

- **Class**: `CentralSystem`
  
- **Purpose**: 
  - This dictionary (`self.pending_requests`) manages ongoing or pending requests and their associated futures or responses from ChargingPoints.
  
- **Usage**:
  - When the `CentralSystem` sends a request (like GetConfiguration or ChangeConfiguration) to a ChargingPoint, it creates a future and stores it in `self.pending_requests` along with a unique message ID.
  - Upon receiving a corresponding `CallResult` from the ChargingPoint, the future associated with the message ID is resolved or updated with the response payload.
  - This mechanism enables asynchronous handling of requests and responses, ensuring that the `CentralSystem` can await and process responses in an organized manner.

#### Future Considerations

1. **Extensive Pytests**:
    - More pytests should be added to cover a wide range of scenarios and edge cases.
    - Tests should ensure that all data structures, message flows, and interactions between `ChargingPoint` and `CentralSystem` function correctly.

2. **Message Validation**:
    - All messages, both sent and received, should be validated to ensure they conform to expected formats and contain correct data.
    - Validation should include checking message structure, required fields, data types, and value ranges.
