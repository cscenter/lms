import binascii
from os import urandom as generate_bytes

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from django.utils import timezone

from api.models import Token
from api.settings import TOKEN_TTL, MIN_REFRESH_INTERVAL, \
    AUTH_TOKEN_CHARACTER_LENGTH, SECURE_HASH_ALGORITHM, TOKEN_KEY_LENGTH


def create_token_string():
    return binascii.hexlify(
        generate_bytes(int(AUTH_TOKEN_CHARACTER_LENGTH / 2))
    ).decode()


def hash_token(token):
    """
    Calculates the hash of a token.
    Input is unhexlified
    token must contain an even number of hex digits or
    a binascii.Error exception will be raised
    """
    digest = hashes.Hash(SECURE_HASH_ALGORITHM(), backend=default_backend())
    digest.update(binascii.unhexlify(token))
    return binascii.hexlify(digest.finalize()).decode()


class TokenService:
    @staticmethod
    def create(user, expire_at=None):
        token = create_token_string()
        digest = hash_token(token)

        instance = Token(access_key=token[:TOKEN_KEY_LENGTH],
                         digest=digest, user=user, expire_at=expire_at)
        instance.save()
        return instance, token

    @staticmethod
    def renew(token: Token):
        current_expiry = token.expire_at
        new_expiry = timezone.now() + TOKEN_TTL
        token.expire_at = new_expiry
        # Throttle refreshing of token to avoid db writes
        delta = (new_expiry - current_expiry).total_seconds()
        if delta > MIN_REFRESH_INTERVAL:
            token.save(update_fields=('expire_at',))

    @staticmethod
    def cleanup(token) -> bool:
        """
        Removes token if it's expired and returns True. False otherwise.
        """
        if token.expire_at is not None:
            if token.expire_at < timezone.now():
                token.delete()
                return True
        return False
