from datetime import datetime, timedelta

import pytest

from admission.constants import ApplicantStatuses
from admission.tests.factories import ApplicantFactory
from admission.tokens import EmailVerificationCodeGenerator


class MockedEmailVerificationCodeGenerator(EmailVerificationCodeGenerator):
    def __init__(self, now):
        self._now_val = now
        super().__init__()

    def _now(self):
        return self._now_val


@pytest.mark.django_db
def test_make_token():
    applicant = ApplicantFactory()
    g = EmailVerificationCodeGenerator()
    token1 = g.make_token("test1@example.com", applicant)
    token2 = g.make_token("test1@example.com", applicant)
    token3 = g.make_token("test2@example.com", applicant)
    assert token1 == token2
    assert token1 != token3
    assert g.check_token("test1@example.com", applicant, token1)


@pytest.mark.django_db
def test_token_updated_applicant():
    """Applicant model update invalidates the token"""
    applicant = ApplicantFactory()
    g = EmailVerificationCodeGenerator()
    token1 = g.make_token("test1@example.com", applicant)
    applicant.status = ApplicantStatuses.GOLDEN_TICKET
    applicant.save(update_fields=["status"])
    applicant.refresh_from_db()
    token2 = g.make_token("test1@example.com", applicant)
    assert token1 != token2


@pytest.mark.django_db
def test_token_timeout(mocker):
    timeout = 60
    email = "test1@example.com"
    mocked_timeout = mocker.patch("admission.tokens.VERIFICATION_CODE_TIMEOUT", timeout)
    applicant = ApplicantFactory()
    now = datetime.now()
    token = MockedEmailVerificationCodeGenerator(now).make_token(email, applicant)
    g1 = MockedEmailVerificationCodeGenerator(now + timedelta(seconds=timeout))
    g2 = MockedEmailVerificationCodeGenerator(now + timedelta(seconds=timeout + 1))
    assert g1.check_token(email, applicant, token)
    assert not g2.check_token(email, applicant, token)


@pytest.mark.django_db
def test_check_token_with_nonexistent_token_and_applicant():
    email = "test1@example.com"
    applicant = ApplicantFactory()
    g = EmailVerificationCodeGenerator()
    token = g.make_token(email, applicant)
    # Examples of wrong API usage
    assert not g.check_token(email, None, token)  # type: ignore
    assert not g.check_token(None, applicant, token)  # type: ignore
