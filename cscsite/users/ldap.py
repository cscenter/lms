# -*- coding: utf-8 -*-
import base64
import io
import logging
from contextlib import contextmanager

import ldap
import ldif
import sys
import platform

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import force_bytes

from core.utils import en_to_ru_mapping
from users.models import CSCUser

logger = logging.getLogger(__name__)

ldapmodule_trace_level = 1
ldapmodule_trace_file = sys.stderr
# ldap.set_option(ldap.OPT_DEBUG_LEVEL, 255)

REQUIRED_SETTINGS = [
    "LDAP_CLIENT_URI",
    "LDAP_DB_SUFFIX",
    "LDAP_CLIENT_USERNAME",
    "LDAP_CLIENT_PASSWORD",
    "LDAP_TLS_TRUSTED_CA_CERT_FILE"
]

for attr in REQUIRED_SETTINGS:
    if not hasattr(settings, attr):
        raise ImproperlyConfigured(
            "Please add {0!r} to your settings module".format(attr))

if not ldap.TLS_AVAIL:
    raise ImproperlyConfigured("python-ldap should be built with TLS support")

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

# TODO: move to utils


def password_ldap_compatible(encoded_password):
    algorithm, iterations, salt, hash = encoded_password.split('$', 3)
    if algorithm == "pbkdf2_sha256":
        ldap_hasher_code = "{PBKDF2-SHA256}"
    elif algorithm == "pbkdf2_sha512":
        ldap_hasher_code = "{PBKDF2-SHA512}"
    elif algorithm == "pbkdf2_sha1":
        ldap_hasher_code = "{PBKDF2-SHA1}"
    else:
        # TODO: set random plain-text password if we don't support hasher
        return make_password()
    # Works like passlib.utils.binary.ab64_encode except converting "+" to "."
    ab64_salt = base64.b64encode(salt.encode("utf-8")).rstrip(b"=\n")
    h = f"{ldap_hasher_code}{iterations}${ab64_salt.decode('utf-8')}${hash}"
    return force_bytes(h)


def user_to_ldif(user: CSCUser, redirect_to=None):
    out = redirect_to or io.StringIO()
    # Use only Portable Filename Character Set according to POSIX.1-2017
    # Since @ in username can be misleading when you connected over ssh
    # `foo@localhost.ru@domain.ltd` really looks weird.
    uid = user.email.replace("@", ".")
    dn = f"uid={uid},ou=users,{settings.LDAP_DB_SUFFIX}"
    entry = {
        'objectClass': [b'inetOrgPerson', b'simpleSecurityObject'],
        'uid': [force_bytes(uid)],
        'employeeNumber': [force_bytes(user.pk)],
        'sn': [force_bytes(user.last_name or user.username)],
        # FIXME: add groups?
        # CN used as a branch name
        'cn': [force_bytes(user.get_abbreviated_name_in_latin())],
        'displayName': [force_bytes(user.get_short_name())],
        'mail': [force_bytes(user.email)],
        'userPassword': [password_ldap_compatible(user.password)]
    }
    ldif_writer = ldif.LDIFWriter(out)
    ldif_writer.unparse(dn, entry)
    if not redirect_to:
        return out.getvalue()


"""
from users.ldap import *
with open('full.ldif', 'w') as f:
    for u in CSCUser.objects.filter(groups__in=[CSCUser.group.STUDENT_CENTER, CSCUser.group.VOLUNTEER, CSCUser.group.TEACHER_CENTER, CSCUser.group.GRADUATE_CENTER]):
        user_to_ldif(u, f)
"""