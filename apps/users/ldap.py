# -*- coding: utf-8 -*-
import io

import ldif
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.utils.encoding import force_bytes

from users.models import User
from users.constants import GROUPS_IMPORT_TO_GERRIT


def get_ldap_username(user: User):
    """
    Portable Filename Character Set (according to POSIX.1-2017) is used for
    username since @ in username can be misleading when you connect
    over ssh. `foo@localhost.ru@domain.ltd` really looks weird.
    """
    return user.email.replace("@", ".")


def user_to_ldif(user: User, redirect_to=None):
    out = redirect_to or io.StringIO()
    uid = user.ldap_username
    dn = f"uid={uid},ou=users,{settings.LDAP_DB_SUFFIX}"
    password_hash = user.password_hash_ldap or make_password(password=None)
    entry = {
        'objectClass': [b'inetOrgPerson', b'simpleSecurityObject'],
        'uid': [force_bytes(uid)],
        'employeeNumber': [force_bytes(user.pk)],
        'sn': [force_bytes(user.last_name or user.username)],
        # CN used as a branch name in git repo
        'cn': [force_bytes(user.get_abbreviated_name_in_latin())],
        'displayName': [force_bytes(user.get_short_name())],
        'mail': [force_bytes(user.email)],
        'userPassword': [password_hash]
    }
    ldif_writer = ldif.LDIFWriter(out)
    ldif_writer.unparse(dn, entry)
    if not redirect_to:
        return out.getvalue()


def export(path):
    """Generates users data in LDIF"""
    with open(path, 'w') as f:
        # FIXME: remove duplicates
        for u in User.objects.filter(groups__in=GROUPS_IMPORT_TO_GERRIT):
            user_to_ldif(u, f)
