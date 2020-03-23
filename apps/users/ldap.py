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
    username since @ in a username can be misleading when you are connecting
    over ssh. `foo@localhost.ru@domain.ltd` really looks weird.
    """
    return user.email.replace("@", ".")


def user_to_ldif(user: User, domain_component, redirect_to=None):
    uid = user.ldap_username
    users_dn = f"uid={uid},ou=users,{domain_component}"
    out = redirect_to or io.StringIO()
    password_hash = user.password_hash_ldap or make_password(password=None)
    entry = {
        'objectClass': [b'inetOrgPerson', b'simpleSecurityObject'],
        'uid': [force_bytes(uid)],
        'employeeNumber': [force_bytes(user.pk)],
        'sn': [force_bytes(user.last_name or user.username)],
        # Common name (or CN) is used as a branch name in a project git repo
        'cn': [force_bytes(user.get_abbreviated_name_in_latin())],
        'displayName': [force_bytes(user.get_short_name())],
        'mail': [force_bytes(user.email)],
        'userPassword': [password_hash]
    }
    ldif_writer = ldif.LDIFWriter(out)
    ldif_writer.unparse(users_dn, entry)
    if not redirect_to:
        return out.getvalue()


def export(file_path, domain_component=None):
    """
    Exports account data in a LDIF format for users having at least one
    of the **GROUPS_IMPORT_TO_GERRIT** groups.
    Example:
        export("230320.ldif", domain_component="dc=example,dc=com")
    Customize **domain_component** for the users distinguished name.
    """
    dc = domain_component or settings.LDAP_DB_SUFFIX
    with open(file_path, 'w') as f:
        for u in User.objects.has_role(*GROUPS_IMPORT_TO_GERRIT).distinct():
            user_to_ldif(user=u, domain_component=dc, redirect_to=f)
