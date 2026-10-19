"""Section 1 placeholder: complete independently without AI assistance."""



from math import isfinite
from typing import Iterable


def sanitize_sensor_values(values: Iterable[object]) -> list[float]:
    """Convert valid sensor readings to floats, filter invalid values,
    discard negatives, and cap readings at 500.0.
    """
    cleaned: list[float] = []

    for value in values:
        if value is None:
            continue

        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            continue

        # Reject non-finite values and negative sensor readings.
        if not isfinite(number) or number < 0:
            continue

        # Cap valid readings at the maximum permitted value.
        cleaned.append(min(number, 500.0))

    return cleaned
