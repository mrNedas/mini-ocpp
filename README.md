# mini-ocpp

## Overview

This project demonstrates communication between a Central System and multiple Charging Points using the OCPP (Open Charge Point Protocol) over WebSocket. The Central System manages and monitors multiple Charging Points, allowing for configuration changes and status updates.

### Components

- **Central System**: 
  - Acts as the central hub managing and monitoring multiple Charging Points.
  - Handles WebSocket communication with Charging Points using OCPP messages.
  - Provides a REST API for querying and updating Charging Point configurations.

- **Charging Point**:
  - Represents an Electric Vehicle (EV) Charging Point.
  - Connects to the Central System via WebSocket.
  - Sends BootNotification and Heartbeat messages to the Central System.
  - Supports receiving configuration updates and responding with status.

## Features

- **WebSocket Communication**: 
  - Central System and Charging Points communicate using the OCPP standard over WebSocket.
  - Messages include BootNotification, Heartbeat, GetConfiguration, and ChangeConfiguration.

- **REST API**:
  - Central System exposes REST endpoints for querying and updating Charging Point configurations.
  - Endpoints include:
    - `GET /charging_points/<charge_point_id>/configuration`: Retrieves current configuration of a Charging Point.
    - `POST /charging_points/<charge_point_id>/configuration`: Updates configuration settings of a Charging Point.

- **Configuration Management**:
  - Central System can send GetConfiguration requests to Charging Points to retrieve their current configuration.
  - Supports ChangeConfiguration requests to update settings on connected Charging Points.

## Usage

1. **Installation**:
   - Clone the repository.
   - Install dependencies using Poetry:
     ```
     poetry install
     ```

2. **Running Tests**:
   - To run tests using Poetry:
     ```
     poetry run pytest
     ```

3. **Running the Central System**:
   - Modify `demo_central_system.py` to configure host, WebSocket port, and HTTP port as needed.
   - Run the Central System using Poetry:
     ```
     poetry run python demo_central_system.py
     ```

4. **Running a Charging Point**:
   - Modify `demo_charging_point.py` to configure WebSocket URI, model, vendor, and serial number of the Charging Point.
   - Run the Charging Point using Poetry:
     ```
     poetry run python demo_cp.py --uri ws://localhost:9000 --model BestModel --vendor BestVendor --serial_number 100
     ```

5. **Interacting with the Central System**:
   - Use HTTP requests to interact with the Central System's REST API for querying and updating Charging Point configurations.

