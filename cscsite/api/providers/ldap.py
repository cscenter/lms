import logging
import platform
import sys
from contextlib import contextmanager

import ldap
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
# XXX: On Mac OS add trusted CA to keychain.
if platform.system() != 'Darwin':
    ldap.set_option(ldap.OPT_X_TLS_CACERTFILE,
                    settings.LDAP_TLS_TRUSTED_CA_CERT_FILE)


class Connection:
    """
    A connection to an LDAP server.
    """

    def __init__(self, connection, suffix):
        """
        Creates the LDAP connection.
        No need to call this manually, the `connection()` context
        manager handles initialization.
        """
        self._connection = connection
        self._suffix = suffix

    def users(self):
        res = self._connection.search_s(f'ou=users,{self._suffix}',
                                        ldap.SCOPE_SUBTREE)
        return res

    def set_password(self, user, *, new_password, old_password=None) -> bool:
        """
        Provide `old_password` if you are trying to change password not from
        rootdn user. Uses sync method version for changing password.
        """
        try:
            dn = f'uid={user},ou=users,{self._suffix}'
            self._connection.passwd_s(dn, old_password, new_password)
            return True
        except ldap.LDAPError as e:
            logger.warning(f"Unable to change password for {user}. {e}")
        return False

    def set_password_hash(self, user, password_hash) -> bool:
        """
        Modify `userPassword` attribute in synchronous mode for provided user
        """
        try:
            dn = f'uid={user},ou=users,{self._suffix}'
            mod_list = [(ldap.MOD_REPLACE, 'userPassword', password_hash)]
            self._connection.modify_s(dn, modlist=mod_list)
            return True
        except ldap.LDAPError as e:
            logger.warning(f"Unable to change password for {user}. {e}")
        return False


@contextmanager
def connection(**kwargs):
    """
    Creates and returns a connection to the LDAP server over StartTLS.
    """
    client_uri = kwargs.pop("client_uri", settings.LDAP_CLIENT_URI)
    suffix = settings.LDAP_DB_SUFFIX
    username = kwargs.pop("username", settings.LDAP_CLIENT_USERNAME)
    dn = f"cn={username},{suffix}"
    password = kwargs.pop("password", settings.LDAP_CLIENT_PASSWORD)

    # Always check server certificate
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_DEMAND)
    try:
        c = ldap.initialize(client_uri,
                            # trace_level=ldapmodule_trace_level,
                            # trace_file=ldapmodule_trace_file
                            )
        c.protocol_version = ldap.VERSION3
        c.network_timeout = 5  # in seconds
        # Fail if TLS is not available.
        c.start_tls_s()
    except ldap.LDAPError as e:
        logger.warning(f"LDAP connect failed: {e}")
        yield None
        return

    try:
        c.simple_bind_s(dn, password)
    except ldap.LDAPError as e:
        logger.warning(f"LDAP simple bind failed: {e}")
        yield None
        return
    logger.info("LDAP connect succeeded")
    try:
        yield Connection(c, suffix)
    finally:
        c.unbind_s()
