class Symbol:
    def __init__(self, value: str):
        if not self.is_valid_symbol(value):
            raise ValueError(f"Invalid trading symbol: {value}")
        self._value = value

    @property
    def value(self) -> str:
        return self._value

    @staticmethod
    def is_valid_symbol(value: str) -> bool:
        # Add logic to validate the trading symbol format
        return isinstance(value, str) and len(value) > 0 and value.isalnum()