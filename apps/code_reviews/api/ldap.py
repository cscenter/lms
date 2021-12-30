import base64
import logging
import platform
import sys
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

import ldap
from ldap.dn import escape_dn_chars
from ldap.ldapobject import LDAPObject
from ldap.modlist import addModlist

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

REQUIRED_SETTINGS = [
    "LDAP_CLIENT_URI",
    "LDAP_DB_SUFFIX",
    "LDAP_CLIENT_USERNAME",
    "LDAP_CLIENT_PASSWORD",
    "LDAP_TLS_TRUSTED_CA_CERT_FILE"
]

if not ldap.TLS_AVAIL:
    raise ImproperlyConfigured("python-ldap should be built with TLS support")

for attr in REQUIRED_SETTINGS:
    if not hasattr(settings, attr):
        raise ImproperlyConfigured(
            "Please add {0!r} to your settings module".format(attr))

ldapmodule_trace_level = 1
ldapmodule_trace_file = sys.stderr
# ldap.set_option(ldap.OPT_DEBUG_LEVEL, 255)
ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_DEMAND)
# XXX: On Mac OS add trusted CA to the keychain store.
if platform.system() != 'Darwin':
    ldap.set_option(ldap.OPT_X_TLS_CACERTFILE,
                    settings.LDAP_TLS_TRUSTED_CA_CERT_FILE)
if not getattr(settings, "LDAP_OVER_SSL_ENABLED", True):
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
    ldap.set_option(ldap.OPT_X_TLS_NEWCTX, 0)


class LDAPClient:
    """
    Client to the LDAP server.
    """

    def __init__(self, connection, domain_component: Optional[str] = None):
        self.connection = connection
        self._domain_component = domain_component or settings.LDAP_DB_SUFFIX

    def users(self):
        res = self.connection.search_s(f'ou=users,{self._domain_component}',
                                       ldap.SCOPE_SUBTREE)
        return res

    def search_users(self, uid) -> List[Tuple[str, Dict]]:
        return self.connection.search_s(f'ou=users,{self._domain_component}',
                                        ldap.SCOPE_ONELEVEL,
                                        f'(uid={uid})',
                                        ['displayName'])

    def add_entry(self, entry) -> Tuple:
        """Performs an LDAP synchronous add operation."""
        dn = entry.pop('dn')
        return self.connection.add_s(dn, addModlist(entry))

    def set_password(self, uid, *, new_password, old_password=None) -> bool:
        """
        Provide `old_password` if you are trying to change password not from
        rootdn user. Uses sync method version for changing password.
        """
        try:
            dn = f'uid={escape_dn_chars(uid)},ou=users,{self._domain_component}'
            self.connection.passwd_s(dn, old_password, new_password)
            return True
        except ldap.LDAPError as e:
            logger.info(f"Unable to change password for {uid}. {e}")
        return False

    def set_password_hash(self, uid, password_hash: bytes) -> bool:
        """
        Modify `userPassword` attribute in synchronous mode for provided user
        """
        try:
            dn = f'uid={escape_dn_chars(uid)},ou=users,{self._domain_component}'
            mod_list = [(ldap.MOD_REPLACE, 'userPassword', password_hash)]
            self.connection.modify_s(dn, modlist=mod_list)
            return True
        except ldap.LDAPError as e:
            logger.info(f"Unable to change password hash for {uid}. {e}")
        return False

    def modify_attribute(self, uid: str, name: str, value: bytes) -> bool:
        """Performs an LDAP modify operation on a user entry's attribute"""
        dn = f'uid={escape_dn_chars(uid)},ou=users,{self._domain_component}'
        mod_list = [(ldap.MOD_REPLACE, name, value)]
        try:
            self.connection.modify_s(dn, modlist=mod_list)
            return True
        except ldap.LDAPError as e:
            logger.error(f"Unable to change password for {uid}. {e}")
        return False


def init_ldap_connection(*, uri: str, dn: str, password: str,
                         timeout: Optional[int] = 5, **options: Any) -> LDAPObject:
    """Returns LDAP connection binded over TLS."""
    # Always check server certificate
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_DEMAND)
    try:
        connection = ldap.initialize(uri, **options)
        connection.protocol_version = ldap.VERSION3
        connection.network_timeout = timeout  # in seconds
        # Fail if TLS is not available.
        connection.start_tls_s()
    except ldap.LDAPError as e:
        logger.error(f"LDAP connection failed: {e}")
        raise
    try:
        connection.simple_bind_s(dn, password)
    except ldap.LDAPError as e:
        logger.error(f"LDAP simple bind failed: {e}")
        raise
    return connection


@contextmanager
def ldap_client(**options):
    """
    Starts a new connection to the LDAP server over StartTLS.
    """
    domain_component = settings.LDAP_DB_SUFFIX
    distinguished_name = f"cn={settings.LDAP_CLIENT_USERNAME},{domain_component}"

    options.setdefault("uri", settings.LDAP_CLIENT_URI)
    options.setdefault("dn", distinguished_name)
    options.setdefault("password", settings.LDAP_CLIENT_PASSWORD)

    try:
        connection = init_ldap_connection(**options)
    except ldap.LDAPError:
        yield None
        return

    logger.info("LDAP connect succeeded")

    try:
        yield LDAPClient(connection, domain_component)
    finally:
        connection.unbind_s()


def adapted_base64(data: bytes) -> bytes:
    """
    Adapted base64 encode is identical to general base64 encode except
    that it uses '.' instead of '+', and omits trailing padding '=' and
    whitespace.
    """
    encoded = base64.b64encode(data, altchars=b'./')
    return encoded.rstrip(b"=\n")
