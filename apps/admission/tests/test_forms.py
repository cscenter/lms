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
def test_confirmation_form_validation(settings, get_test_image):
    future_dt = get_now_utc() + datetime.timedelta(days=5)
    campaign = CampaignFactory(
        year=2011,
        branch=BranchFactory(site=SiteFactory(pk=settings.SITE_ID)),
        confirmation_ends_at=future_dt,
    )
    acceptance = AcceptanceFactory(
        status=Acceptance.WAITING, applicant__campaign=campaign
    )
    form = ConfirmationForm(acceptance=acceptance, data={})
    assert not form.is_valid()
    # Invalid email verification code and not full data
    form_data = {
        "authorization_code": acceptance.confirmation_code,
        "email": "test@example.com",
        "email_code": "wrong",
        "birth_date": datetime.date(2000, 1, 1)
    }
    form = ConfirmationForm(
        acceptance=acceptance, data=form_data, prefix=False
    )
    assert not form.is_valid()
    form_data["email_code"] = email_code_generator.make_token(
        "test2@example.com", acceptance.applicant
    )
    form = ConfirmationForm(
        acceptance=acceptance, data=form_data, prefix=False
    )
    assert not form.is_valid()
    form_data["email_code"] = email_code_generator.make_token(
        "test@example.com", acceptance.applicant
    )
    assert not form.is_valid()
    error_fields = ["email_code", "living_place", "gender", "phone", "telegram_username", "offer_confirmation", "personal_data_confirmation"]
    assert set(form.errors) == set(error_fields)
    form_data["living_place"] = "living_place"
    form_data["gender"] = GenderTypes.MALE
    form_data["phone"] = "+71234567"
    form_data["telegram_username"] = "telegram_username"
    form_data["yandex_login"] = "yandex_login"
    form_data["offer_confirmation"] = True
    form_data["personal_data_confirmation"] = True
    form = ConfirmationForm(
        acceptance=acceptance, data=form_data, prefix=False
    )
    assert form.is_valid()
    form_data["telegram_username"] = "ab"  # too short
    form = ConfirmationForm(
        acceptance=acceptance, data=form_data, prefix=False
    )
    assert not form.is_valid()
    # if only one symbol then there is no Telegram account.
    form_data["telegram_username"] = "-"
    form = ConfirmationForm(
        acceptance=acceptance, data=form_data, prefix=False
    )
    assert form.is_valid()
    assert form.cleaned_data["telegram_username"] == ""
    form_data["telegram_username"] = "abcde"
    form = ConfirmationForm(
        acceptance=acceptance, data=form_data, prefix=False
    )
    assert form.is_valid()
    assert form.cleaned_data["telegram_username"] == "abcde"
