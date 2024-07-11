from enum import Enum


class MessageType(Enum):
    CALL = 2
    CALL_RESULT = 3
    CALL_ERROR = 4
