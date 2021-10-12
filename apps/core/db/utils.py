from decimal import Decimal
from typing import Optional, Union


def normalize_score(value: Optional[Decimal]) -> Optional[Decimal]:
    """
    Removes the exponent and trailing zeroes, losing significance,
    but keeping the value unchanged.

    For example, expressing 5.0E+3 as 5000 keeps the value constant but
    cannot show the original’s two-place significance.
    """
    if value is None:
        return value
    as_integral = value.to_integral_value()
    if value == as_integral:
        return as_integral.quantize(Decimal(1))
    return value.normalize()
