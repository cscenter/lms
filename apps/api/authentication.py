import binascii
from hmac import compare_digest

from rest_framework.authentication import BaseAuthentication, get_authorization_header

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from api.errors import AuthenticationFailed, InvalidToken
from api.services import TokenService, hash_token
from api.settings import AUTH_HEADER, AUTO_REFRESH, TOKEN_KEY_LENGTH

UserModel = get_user_model()


class TokenAuthentication(BaseAuthentication):
    """
    Simple token based authentication.

    Clients should authenticate by passing the token key in the "Authorization"
    HTTP header, prepended with the string "Token ".  For example:

        Authorization: Token 401f7ac837da42b97f613d789819ff93537bee6a
    """

    keyword = AUTH_HEADER
    model = None

    def get_model(self):
        if self.model is not None:
            return self.model
        from .models import Token
        return Token

    def authenticate(self, request):
        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth) == 1:
            msg = _('Invalid token header. No credentials provided.')
            raise AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _('Invalid token header. Token string should not contain spaces.')
            raise AuthenticationFailed(msg)

        try:
            token = auth[1].decode()
        except UnicodeError:
            msg = _('Invalid token header. Token string should not contain invalid characters.')
            raise AuthenticationFailed(msg)

        return self.authenticate_credentials(token)

    def authenticate_credentials(self, secret_key):
        """
        Due to the random nature of hashing a value, this must inspect
        each auth_token individually to find the correct one.

        Tokens that have expired will be deleted and skipped
        """
        tokens = (self.get_model().objects
                  .filter(access_key=secret_key[:TOKEN_KEY_LENGTH])
                  .select_related('user'))
        for token in tokens:
            if TokenService.cleanup(token):
                continue

            try:
                digest = hash_token(secret_key)
            except (TypeError, binascii.Error):
                raise InvalidToken()
            if compare_digest(digest, token.digest):
                if AUTO_REFRESH and token.expire_at:
                    TokenService.renew(token)
                if not token.user.is_active:
                    raise AuthenticationFailed(_('User inactive or deleted.'))
                return token.user, token
        raise InvalidToken()

    def authenticate_header(self, request):
        return self.keyword
