import os
import json
import logging
from jsonschema import Draft202012Validator, exceptions


class MessageValidator:
    def __init__(self, schema_dir):
        self.schema_dir = schema_dir

    def validate_message(self, schema_name, message):
        schema_path = os.path.join(self.schema_dir, f"{schema_name}.json")
        try:
            with open(schema_path, "r") as schema_file:
                schema = json.load(schema_file)
            validator = Draft202012Validator(schema)
            validator.validate(message)
            logging.debug(f"Validation successful: {schema_name}")
            return True
        except FileNotFoundError:
            logging.error(f"Schema file not found: {schema_path}")
            return False
        except exceptions.ValidationError as e:
            logging.error(f"Validation error for {schema_name}: {e.message}")
            return False


# Example usage:
# validator = JSONValidator(schema_dir='./schemas/json')
# is_valid = validator.validate_message('Heartbeat', message)
