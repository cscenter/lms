import logging
import platform
import sys
from contextlib import contextmanager
from typing import Dict, List, Tuple

import ldap
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


class LDAPClient:
    """
    Client to the LDAP server.
    """

    def __init__(self, connection, suffix):
        self.connection = connection
        self._suffix = suffix

    def users(self):
        res = self.connection.search_s(f'ou=users,{self._suffix}',
                                       ldap.SCOPE_SUBTREE)
        return res

    def search_users(self, uid) -> List[Tuple[str, Dict]]:
        return self.connection.search_s(f'ou=users,{self._suffix}',
                                        ldap.SCOPE_ONELEVEL,
                                        f'(uid={uid})',
                                        ['displayName'])

    def add_entry(self, entry) -> Tuple:
        """Performs an LDAP synchronous add operation."""
        dn = entry.pop('dn')
        return self.connection.add_s(dn, addModlist(entry))

    def set_password(self, user, *, new_password, old_password=None) -> bool:
        """
        Provide `old_password` if you are trying to change password not from
        rootdn user. Uses sync method version for changing password.
        """
        try:
            dn = f'uid={user},ou=users,{self._suffix}'
            self.connection.passwd_s(dn, old_password, new_password)
            return True
        except ldap.LDAPError as e:
            logger.error(f"Unable to change password for {user}. {e}")
        return False

    def set_password_hash(self, uid, password_hash) -> bool:
        """
        Modify `userPassword` attribute in synchronous mode for provided user
        """
        try:
            dn = f'uid={uid},ou=users,{self._suffix}'
            mod_list = [(ldap.MOD_REPLACE, 'userPassword', password_hash)]
            self.connection.modify_s(dn, modlist=mod_list)
            return True
        except ldap.LDAPError as e:
            logger.error(f"Unable to change password for {uid}. {e}")
        return False


@contextmanager
def init_client(**kwargs):
    """
    Starts a new connection to the LDAP server over StartTLS.
    """
    client_uri = kwargs.pop("client_uri", settings.LDAP_CLIENT_URI)
    suffix = settings.LDAP_DB_SUFFIX
    username = kwargs.pop("username", settings.LDAP_CLIENT_USERNAME)
    login_dn = f"cn={username},{suffix}"
    password = kwargs.pop("password", settings.LDAP_CLIENT_PASSWORD)

    # Always check server certificate
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_DEMAND)
    try:
        connect = ldap.initialize(client_uri,
                            # trace_level=ldapmodule_trace_level,
                            # trace_file=ldapmodule_trace_file
                            )
        connect.protocol_version = ldap.VERSION3
        connect.network_timeout = 5  # in seconds
        # Fail if TLS is not available.
        connect.start_tls_s()
    except ldap.LDAPError as e:
        logger.warning(f"LDAP connect failed: {e}")
        yield None
        return

    try:
        connect.simple_bind_s(login_dn, password)
    except ldap.LDAPError as e:
        logger.warning(f"LDAP simple bind failed: {e}")
        yield None
        return
    logger.info("LDAP connect succeeded")
    try:
        yield LDAPClient(connect, suffix)
    finally:
        connect.unbind_s()
