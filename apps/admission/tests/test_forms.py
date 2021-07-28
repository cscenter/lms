import datetime

import pytest

from admission.forms import ConfirmationForm
from admission.models import Acceptance
from admission.tests.factories import AcceptanceFactory, CampaignFactory
from admission.tokens import email_code_generator
from core.tests.factories import BranchFactory, SiteFactory
from core.timezone import get_now_utc
from users.constants import GenderTypes


@pytest.mark.django_db
def test_confirmation_form_validation(settings, test_image):
    future_dt = get_now_utc() + datetime.timedelta(days=5)
    campaign = CampaignFactory(year=2011,
                               branch=BranchFactory(site=SiteFactory(pk=settings.SITE_ID)),
                               confirmation_ends_at=future_dt)
    acceptance = AcceptanceFactory(status=Acceptance.WAITING, applicant__campaign=campaign)
    form = ConfirmationForm(acceptance=acceptance, data={})
    assert not form.is_valid()
    # Invalid email verification code
    form_data = {
        "authorization_code": acceptance.confirmation_code,
        "email": "test@example.com",
        "email_code": "wrong",
        "time_zone": "Europe/Moscow",
        "gender": GenderTypes.FEMALE,
        "birthday": datetime.date(2011, 1, 1),
        "phone": "+7",
    }
    files = {"photo": test_image(name='test.png')}
    form = ConfirmationForm(acceptance=acceptance, data=form_data, prefix=False, files=files)
    assert not form.is_valid()
    form_data['email_code'] = email_code_generator.make_token("test2@example.com", acceptance.applicant)
    form = ConfirmationForm(acceptance=acceptance, data=form_data, prefix=False, files=files)
    assert not form.is_valid()
    form_data['email_code'] = email_code_generator.make_token("test@example.com", acceptance.applicant)
    form = ConfirmationForm(acceptance=acceptance, data=form_data, prefix=False, files=files)
    assert form.is_valid()
