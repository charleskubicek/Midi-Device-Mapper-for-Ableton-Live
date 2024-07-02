class GenError(Exception):
    def __init__(self, message, error_code:int):
        super().__init__(message)
        self.error_code = error_code

