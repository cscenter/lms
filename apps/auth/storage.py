from social_core.storage import BaseStorage

from django.db import IntegrityError

from auth.models import (
    ConnectedAuthService, EmailValidationCode, OpenIDAssociation, OpenIDNonce, Partial
)


class SocialServiceStorage(BaseStorage):
    user = ConnectedAuthService
    nonce = OpenIDNonce
    association = OpenIDAssociation
    code = EmailValidationCode
    partial = Partial

    @classmethod
    def is_integrity_error(cls, exception):
        return exception.__class__ is IntegrityError
