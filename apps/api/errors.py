from django.utils.translation import gettext_lazy as _
from rest_framework import status, exceptions


class TokenError(Exception):
    pass


class AuthenticationFailed(exceptions.AuthenticationFailed):
    pass


class InvalidToken(AuthenticationFailed):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = _('Token is invalid or expired')
    default_code = 'token_not_valid'
