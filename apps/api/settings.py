from datetime import timedelta

from django.conf import settings
from django.utils.module_loading import import_string

TOKEN_KEY_LENGTH = 8
DIGEST_LENGTH = 128
TOKEN_TTL = timedelta(hours=10)
AUTH_HEADER = 'Token'
AUTH_TOKEN_CHARACTER_LENGTH = 64
AUTO_REFRESH = False
MIN_REFRESH_INTERVAL = 60  # seconds
SECURE_HASH_ALGORITHM = getattr(settings, 'SECURE_HASH_ALGORITHM',
                                'cryptography.hazmat.primitives.hashes.SHA512')

SECURE_HASH_ALGORITHM = import_string(SECURE_HASH_ALGORITHM)
