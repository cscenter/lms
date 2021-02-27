from decimal import Decimal

from core.db.utils import normalize_score


def test_normalize_score():
    assert normalize_score(None) is None
    assert normalize_score(Decimal('5.0')) == 5
    assert normalize_score(Decimal('5.00')) == 5
    assert normalize_score(Decimal('5.1')) == Decimal('5.1')

