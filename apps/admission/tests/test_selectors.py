import pytest

from django.db.models import Q

from admission.models import Acceptance
from admission.selectors import get_acceptance
from admission.tests.factories import AcceptanceFactory


@pytest.mark.django_db
def test_get_acceptance():
    acceptance = AcceptanceFactory(
        status=Acceptance.CONFIRMED, applicant__campaign__year=2011
    )
    assert get_acceptance(year=2011, access_key="wrong_key") is None
    assert get_acceptance(year=2011, access_key=acceptance.access_key) == acceptance
    assert get_acceptance(year=2012, access_key=acceptance.access_key) is None
    assert (
        get_acceptance(
            year=2011,
            access_key=acceptance.access_key,
            filters=[Q(status=Acceptance.WAITING)],
        )
        is None
    )
