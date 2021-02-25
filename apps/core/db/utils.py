from decimal import Decimal
from typing import Optional, Union


def normalize_score(value: Optional[Decimal]) -> Optional[Union[int, Decimal]]:
    """
    This method used for humanizing score value - we want to show `5`
    instead of `5.00` when it's possible.

    When decimal is provided cast it to integer. If the result is exact
    as decimal value returns integer instead of the original decimal.
    """
    if value is None:
        return value
    decimal_as_int = value.to_integral_value()
    if value == decimal_as_int:
        return decimal_as_int
    return value.normalize()
