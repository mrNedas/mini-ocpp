import asyncio
import argparse
import logging
from mini_ocpp import ChargingPoint

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Run ChargingPoint with specified parameters"
    )
    parser.add_argument("--uri", required=True, help="URI of the WebSocket server")
    parser.add_argument("--model", required=True, help="Model of the charging point")
    parser.add_argument("--vendor", required=True, help="Vendor of the charging point")
    parser.add_argument(
        "--serial_number", required=True, help="Serial number of the charging point"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()

    charging_point = ChargingPoint(
        uri=args.uri,
        model=args.model,
        vendor=args.vendor,
        serial_number=args.serial_number,
    )
    asyncio.run(charging_point.run())
