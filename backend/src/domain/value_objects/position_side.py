class PositionSide:
    LONG = "LONG"
    SHORT = "SHORT"

    def __init__(self, side: str):
        if side not in (self.LONG, self.SHORT):
            raise ValueError(f"Invalid position side: {side}")
        self._side = side

    def __str__(self):
        return self._side

    def __eq__(self, other):
        if isinstance(other, PositionSide):
            return self._side == other._side
        return False

    def __repr__(self):
        return f"PositionSide({self._side})"