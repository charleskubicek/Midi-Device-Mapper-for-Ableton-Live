from enum import IntEnum


class ErrorCode(IntEnum):
    """Stable error codes for config problems surfaced to the user.

    Code 1 (CLASHING_MAPPINGS) predates this enum and is kept for back-compat.
    """
    CLASHING_MAPPINGS = 1
    COORD_SYNTAX = 2
    CONFIG_VALIDATION = 3
    SEMANTIC_VALIDATION = 4


class GenError(Exception):
    def __init__(self, message, error_code: int):
        super().__init__(message)
        self.error_code = int(error_code)

