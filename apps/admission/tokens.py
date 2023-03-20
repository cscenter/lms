from datetime import datetime, time
from typing import Optional

from django.conf import settings
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils.http import base36_to_int, int_to_base36

from admission.models import Applicant

VERIFICATION_CODE_TIMEOUT = 600  # in seconds


class EmailVerificationCodeGenerator:
    """
    Strategy object used to generate and check tokens for the password
    reset mechanism.
    """

    key_salt = "admission.tokens.EmailVerificationCodeGenerator"
    secret = settings.SECRET_KEY

    def __init__(self, algorithm: Optional[str] = None):
        self.algorithm = algorithm or "sha256"

    def make_token(self, email: str, applicant: Applicant) -> str:
        """
        Return a token that can be used once to verify email
        for the given participant.
        """
        return self._make_token_with_timestamp(
            email, applicant, self.num_seconds(self._now())
        )

    def _make_token_with_timestamp(
        self, email: str, applicant: Applicant, timestamp: int
    ) -> str:
        # timestamp is number of seconds since 2001-1-1. Converted to base 36,
        # this gives us a 6 digit string until about 2069.
        ts_b36 = int_to_base36(timestamp)
        hash_string = salted_hmac(
            self.key_salt,
            self._make_hash_value(email, applicant, timestamp),
            secret=self.secret,
            algorithm=self.algorithm,
        ).hexdigest()[
            ::2
        ]  # Limit to 20 characters to shorten the code.
        return "%s-%s" % (ts_b36, hash_string)

    def _make_hash_value(self, email: str, applicant: Applicant, timestamp: int) -> str:
        """
        Hash the primary key and some state that's sure to change
        after creating student profile to produce a token that invalidated
        when it's used:
        1. The `Applicant.modified` field will usually be updated very
            shortly after creating student profile.
        Failing those things or VERIFICATION_CODE_TIMEOUT eventually
        invalidates the token.

        Running this data through salted_hmac() prevents password cracking
        attempts using the reset token, provided the secret isn't compromised.
        """
        # Database should support microseconds
        modified_timestamp = applicant.modified.replace(tzinfo=None)
        return str(applicant.pk) + email + str(modified_timestamp) + str(timestamp)

    def check_token(self, email: str, applicant: Applicant, token: str) -> bool:
        """
        Checks that a email verification token is correct for a given participant.
        """
        if not (applicant and token and email):
            return False
        # Parse the token
        try:
            ts_b36, _ = token.split("-")
            timestamp = base36_to_int(ts_b36)
        except ValueError:
            return False

        # Check that the timestamp/uid has not been tampered with
        if not constant_time_compare(
            self._make_token_with_timestamp(email, applicant, timestamp), token
        ):
            return False

        # Check the timestamp is within limit
        if (self.num_seconds(self._now()) - timestamp) > VERIFICATION_CODE_TIMEOUT:
            return False

        return True

    @staticmethod
    def num_seconds(dt) -> int:
        """
        Returns number of seconds since 2001-1-1. Could be converted to base 36,
        this gives a 6 digit string until about 2069.
        """
        return int((dt - datetime(2001, 1, 1)).total_seconds())

    @staticmethod
    def _now() -> datetime:
        # Used for mocking in tests
        return datetime.now()


email_code_generator = EmailVerificationCodeGenerator()
