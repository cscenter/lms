# -*- coding: utf-8 -*-
import base64
import io

import ldif
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.utils.encoding import force_bytes

from users.models import CSCUser


# TODO: move to users model
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
    # Portable Filename Character Set (according to POSIX.1-2017) is used for
    # username since @ in username can be misleading when you connected
    # over ssh. `foo@localhost.ru@domain.ltd` really looks weird.
    uid = user.email.replace("@", ".")
    dn = f"uid={uid},ou=users,{settings.LDAP_DB_SUFFIX}"
    entry = {
        'objectClass': [b'inetOrgPerson', b'simpleSecurityObject'],
        'uid': [force_bytes(uid)],
        'employeeNumber': [force_bytes(user.pk)],
        'sn': [force_bytes(user.last_name or user.username)],
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