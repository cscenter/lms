import hashlib
from urllib.parse import quote

from django.utils.encoding import force_bytes

API_FRAGMENT_KEY_TEMPLATE = 'api.cache.%s.%s'


def make_api_fragment_key(fragment_name, vary_on=None):
    if vary_on is None:
        vary_on = ()
    key = ':'.join(quote(var) for var in vary_on)
    args = hashlib.md5(force_bytes(key))
    return API_FRAGMENT_KEY_TEMPLATE % (fragment_name, args.hexdigest())
