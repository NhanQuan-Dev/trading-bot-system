class Price:
    def __init__(self, value: float):
        if value < 0:
            raise ValueError("Price cannot be negative.")
        self._value = value

    @property
    def value(self) -> float:
        return self._value

    def __str__(self) -> str:
        return f"{self._value:.2f}"

    def __eq__(self, other) -> bool:
        if isinstance(other, Price):
            return self._value == other.value
        return False

    def __lt__(self, other) -> bool:
        if isinstance(other, Price):
            return self._value < other.value
        return NotImplemented

    def __le__(self, other) -> bool:
        if isinstance(other, Price):
            return self._value <= other.value
        return NotImplemented

    def __gt__(self, other) -> bool:
        if isinstance(other, Price):
            return self._value > other.value
        return NotImplemented

    def __ge__(self, other) -> bool:
        if isinstance(other, Price):
            return self._value >= other.value
        return NotImplemented

    def __add__(self, other) -> 'Price':
        if isinstance(other, Price):
            return Price(self._value + other.value)
        return NotImplemented

    def __sub__(self, other) -> 'Price':
        if isinstance(other, Price):
            return Price(self._value - other.value)
        return NotImplemented

    def __repr__(self) -> str:
        return f"Price(value={self._value})"