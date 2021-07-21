import binascii
import random
from os import urandom as generate_bytes
from typing import Tuple

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes

from django.utils import timezone
from django.utils.encoding import force_bytes

from api.models import Token
from api.settings import (
    AUTH_TOKEN_CHARACTER_LENGTH, MIN_REFRESH_INTERVAL, SECURE_HASH_ALGORITHM,
    TOKEN_KEY_LENGTH, TOKEN_TTL
)


def create_token_string() -> str:
    return binascii.hexlify(
        generate_bytes(int(AUTH_TOKEN_CHARACTER_LENGTH / 2))
    ).decode()


def hash_token(token) -> str:
    """
    Calculates the hash of a token.

    Token must contain an even number of hex digits or a binascii.Error
    will be raised.
    """
    return generate_hash(binascii.unhexlify(token), salt=False)


# TODO: move to core utils
def generate_hash(*bits: bytes, salt=True) -> str:
    """Use salt=False if key needs to be mapped 1 to 1"""
    digest = hashes.Hash(SECURE_HASH_ALGORITHM(), backend=default_backend())
    salt = force_bytes(str(random.random())[2:]) if salt else b''
    token = salt + b'#'.join(bits)
    digest.update(token)
    return binascii.hexlify(digest.finalize()).decode()


class TokenService:
    @staticmethod
    def create(user, expire_at=None) -> Tuple[Token, str]:
        token = create_token_string()
        digest = hash_token(token)

        instance = Token(access_key=token[:TOKEN_KEY_LENGTH],
                         digest=digest, user=user, expire_at=expire_at)
        instance.save()
        return instance, token

    @staticmethod
    def renew(token: Token) -> None:
        current_expiry = token.expire_at
        assert current_expiry is not None
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
