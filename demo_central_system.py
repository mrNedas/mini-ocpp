import asyncio
from mini_ocpp import CentralSystem
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


if __name__ == "__main__":
    central_system = CentralSystem(host="localhost", ws_port=9000, http_port=3000)
    asyncio.run(central_system.run())
